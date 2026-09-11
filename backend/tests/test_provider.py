"""Tests for LLM providers: JSON extraction, validation, HTTP paths, selection."""

from typing import Any

import httpx
import pytest
from app.ai.provider import (
    AIError,
    AnthropicProvider,
    OpenAICompatibleProvider,
    _extract_json_object,
    _validate,
    build_provider,
)
from app.config import Settings
from pydantic import BaseModel, SecretStr

SECRET = "Qk7wR2tY9uP5mJ3nV8cX4bZ6dF8gH2sL"


class _Box(BaseModel):
    summary: str


def _settings(**overrides: Any) -> Settings:
    return Settings(jwt_secret_key=SECRET, **overrides)


def _patch_http(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    def factory(**kwargs: Any) -> httpx.AsyncClient:
        kwargs.pop("transport", None)
        return original(transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


def test_extract_plain_json() -> None:
    assert _extract_json_object('{"a": 1}') == {"a": 1}


def test_extract_fenced_json() -> None:
    text = '```json\n{"a": 1}\n```'
    assert _extract_json_object(text) == {"a": 1}


def test_extract_json_with_prose() -> None:
    text = 'Sure! Here is the answer: {"a": 1} hope that helps.'
    assert _extract_json_object(text) == {"a": 1}


def test_extract_missing_braces_raises() -> None:
    with pytest.raises(AIError, match="did not contain a JSON object"):
        _extract_json_object("no json at all")


def test_extract_malformed_json_raises() -> None:
    with pytest.raises(AIError, match="malformed JSON"):
        _extract_json_object('{"a": 1, "b": [}')


def test_extract_array_raises() -> None:
    with pytest.raises(AIError, match="did not contain a JSON object"):
        _extract_json_object("[1, 2, 3]")


def test_extract_fenced_without_newline() -> None:
    assert _extract_json_object('```{"a": 1}```') == {"a": 1}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validate_schema_failure_raises() -> None:
    with pytest.raises(AIError, match="schema validation"):
        _validate(_Box, {"summary": 123}, "openai")


# ---------------------------------------------------------------------------
# OpenAI-compatible provider over HTTP
# ---------------------------------------------------------------------------


def _openai_provider(**overrides: Any) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        name="openai",
        api_key=SecretStr(SECRET),
        base_url="https://llm.example.com/v1",
        model="test-model",
        timeout=5.0,
        **overrides,
    )


async def test_openai_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = request.read()
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"summary": "hello"}'}}]},
        )

    _patch_http(monkeypatch, handler)
    provider = _openai_provider()
    result = await provider.complete_json("sys", "usr", _Box)
    assert isinstance(result, _Box)
    assert result.summary == "hello"
    assert captured["url"] == "https://llm.example.com/v1/chat/completions"
    assert captured["auth"] == f"Bearer {SECRET}"
    assert b'"model":"test-model"' in captured["body"].replace(b" ", b"")


async def test_openai_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(500, json={"error": "kaboom"})

    _patch_http(monkeypatch, handler)
    with pytest.raises(AIError, match="request failed"):
        await _openai_provider().complete_json("sys", "usr", _Box)


async def test_openai_unexpected_body(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, lambda request: httpx.Response(200, json={"nope": True}))
    with pytest.raises(AIError, match="unexpected body"):
        await _openai_provider().complete_json("sys", "usr", _Box)


async def test_openai_bad_json_content(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(
        monkeypatch,
        lambda request: httpx.Response(200, json={"choices": [{"message": {"content": "nah"}}]}),
    )
    with pytest.raises(AIError, match="did not contain a JSON object"):
        await _openai_provider().complete_json("sys", "usr", _Box)


# ---------------------------------------------------------------------------
# Anthropic provider over HTTP
# ---------------------------------------------------------------------------


def _anthropic_provider() -> AnthropicProvider:
    return AnthropicProvider(
        api_key=SecretStr(SECRET),
        base_url="https://anthropic.example.com",
        model="test-model",
        timeout=5.0,
    )


async def test_anthropic_success(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["key"] = request.headers["x-api-key"]
        captured["version"] = request.headers["anthropic-version"]
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": '{"summary": "bonjour"}'}]},
        )

    _patch_http(monkeypatch, handler)
    result = await _anthropic_provider().complete_json("sys", "usr", _Box)
    assert isinstance(result, _Box)
    assert result.summary == "bonjour"
    assert captured["url"] == "https://anthropic.example.com/v1/messages"
    assert captured["key"] == SECRET
    assert captured["version"] == AnthropicProvider.API_VERSION


async def test_anthropic_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, lambda request: httpx.Response(429, json={"error": "slow down"}))
    with pytest.raises(AIError, match="request failed"):
        await _anthropic_provider().complete_json("sys", "usr", _Box)


async def test_anthropic_unexpected_body(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_http(monkeypatch, lambda request: httpx.Response(200, json={"content": "flat"}))
    with pytest.raises(AIError, match="unexpected body"):
        await _anthropic_provider().complete_json("sys", "usr", _Box)


# ---------------------------------------------------------------------------
# Provider selection from the environment
# ---------------------------------------------------------------------------


def test_build_provider_rule_based() -> None:
    assert build_provider(_settings(ai_provider="rule_based")) is None


def test_build_provider_auto_without_keys_is_offline() -> None:
    assert build_provider(_settings()) is None


def test_build_provider_auto_prefers_openai() -> None:
    provider = build_provider(_settings(openai_api_key=SECRET, anthropic_api_key=SECRET))
    assert provider is not None and provider.name == "openai"


def test_build_provider_auto_falls_back_to_anthropic() -> None:
    provider = build_provider(_settings(anthropic_api_key=SECRET))
    assert provider is not None and provider.name == "anthropic"


def test_build_provider_explicit_openai_requires_key() -> None:
    with pytest.raises(AIError, match="PRAGATISHALA_OPENAI_API_KEY"):
        build_provider(_settings(ai_provider="openai"))


def test_build_provider_explicit_anthropic_requires_key() -> None:
    with pytest.raises(AIError, match="PRAGATISHALA_ANTHROPIC_API_KEY"):
        build_provider(_settings(ai_provider="anthropic"))


def test_build_provider_explicit_openai() -> None:
    provider = build_provider(
        _settings(
            ai_provider="openai",
            openai_api_key=SECRET,
            openai_base_url="https://gateway.example.com/v1/",
        )
    )
    assert provider is not None
    assert provider.model == "gpt-4o-mini"
    assert provider.name == "openai"


def test_build_provider_explicit_anthropic() -> None:
    provider = build_provider(_settings(ai_provider="anthropic", anthropic_api_key=SECRET))
    assert provider is not None and provider.name == "anthropic"


async def test_openai_timeout_raises_ai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider timeouts surface as AIError (engine then falls back)."""

    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ReadTimeout("timed out")

    _patch_http(monkeypatch, handler)
    with pytest.raises(AIError, match="request failed"):
        await _openai_provider().complete_json("sys", "usr", _Box)


async def test_anthropic_timeout_raises_ai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.ReadTimeout("timed out")

    _patch_http(monkeypatch, handler)
    with pytest.raises(AIError, match="request failed"):
        await _anthropic_provider().complete_json("sys", "usr", _Box)
