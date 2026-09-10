"""LLM providers reachable over HTTP.

Only OpenAI-compatible APIs and the Anthropic Messages API are supported; both
cover OpenAI, Azure OpenAI gateways, Gemini's OpenAI-compatible endpoint,
Groq, OpenRouter, Ollama, and vLLM through ``base_url`` overrides.

API keys come exclusively from the environment (``PRAGATISHALA_OPENAI_API_KEY``
or ``PRAGATISHALA_ANTHROPIC_API_KEY``) — never from code.
"""

import json
import logging
from typing import Any, Literal, Protocol, cast

import httpx
from pydantic import BaseModel, SecretStr, ValidationError

from app.config import Settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised when an LLM call fails or returns unusable output."""


class LLMProvider(Protocol):
    """Protocol implemented by every remote provider."""

    name: str
    model: str

    async def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        """Run a completion and validate the JSON answer against *schema*."""
        ...  # pragma: no cover


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse the first JSON object found in *text*.

    Models occasionally wrap JSON in markdown fences or prose; this tolerates
    both instead of failing the whole request.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        msg = "response did not contain a JSON object"
        raise AIError(msg)
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        msg = "response contained malformed JSON"
        raise AIError(msg) from exc
    # A successful parse of a {...} substring is always a dict.
    return cast(dict[str, Any], parsed)


class OpenAICompatibleProvider:
    """Provider for any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        *,
        name: str,
        api_key: SecretStr,
        base_url: str,
        model: str,
        timeout: float,
    ) -> None:
        self.name = name
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key.get_secret_value()}"}
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            msg = f"{self.name} request failed: {exc}"
            raise AIError(msg) from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            msg = f"{self.name} returned an unexpected body"
            raise AIError(msg) from exc

        return _validate(schema, _extract_json_object(content), self.name)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"{type(self).__name__}(name={self.name!r}, model={self.model!r})"


class AnthropicProvider:
    """Provider for the Anthropic Messages API."""

    API_VERSION = "2023-06-01"

    def __init__(self, *, api_key: SecretStr, base_url: str, model: str, timeout: float) -> None:
        self.name = "anthropic"
        self.model = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def complete_json(self, system: str, user: str, schema: type[BaseModel]) -> BaseModel:
        url = f"{self._base_url}/v1/messages"
        headers = {
            "x-api-key": self._api_key.get_secret_value(),
            "anthropic-version": self.API_VERSION,
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 2000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            msg = f"{self.name} request failed: {exc}"
            raise AIError(msg) from exc

        try:
            content = body["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            msg = f"{self.name} returned an unexpected body"
            raise AIError(msg) from exc

        return _validate(schema, _extract_json_object(content), self.name)


def _validate(schema: type[BaseModel], data: dict[str, Any], provider_name: str) -> BaseModel:
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        logger.warning("%s returned JSON failing schema validation: %s", provider_name, exc)
        msg = f"{provider_name} output failed schema validation"
        raise AIError(msg) from exc


def build_provider(settings: Settings) -> LLMProvider | None:
    """Pick a provider from the environment, or None for offline mode.

    Resolution order for ``ai_provider="auto"``: OpenAI-compatible first, then
    Anthropic. Explicit selections require their key to be present.
    """
    selection: Literal["auto", "openai", "anthropic", "rule_based"] = settings.ai_provider

    if selection == "rule_based":
        return None

    openai_key = settings.openai_api_key
    anthropic_key = settings.anthropic_api_key

    if selection == "openai":
        if openai_key is None:
            msg = "PRAGATISHALA_OPENAI_API_KEY is required for ai_provider='openai'"
            raise AIError(msg)
        return OpenAICompatibleProvider(
            name="openai",
            api_key=openai_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout=settings.ai_timeout_seconds,
        )

    if selection == "anthropic":
        if anthropic_key is None:
            msg = "PRAGATISHALA_ANTHROPIC_API_KEY is required for ai_provider='anthropic'"
            raise AIError(msg)
        return AnthropicProvider(
            api_key=anthropic_key,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
            timeout=settings.ai_timeout_seconds,
        )

    # auto
    if openai_key is not None:
        return OpenAICompatibleProvider(
            name="openai",
            api_key=openai_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            timeout=settings.ai_timeout_seconds,
        )
    if anthropic_key is not None:
        return AnthropicProvider(
            api_key=anthropic_key,
            base_url=settings.anthropic_base_url,
            model=settings.anthropic_model,
            timeout=settings.ai_timeout_seconds,
        )
    return None
