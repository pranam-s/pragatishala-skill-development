"""Tests for app.config."""

import pytest
from app.config import Settings, get_settings
from pydantic import SecretStr, ValidationError

VALID = {"jwt_secret_key": "x" * 32}


def test_defaults() -> None:
    settings = Settings(**VALID)
    assert settings.app_name == "PragatiShala API"
    assert settings.database_url.startswith("sqlite+aiosqlite")
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_expire_minutes == 30
    assert settings.refresh_token_expire_minutes == 7 * 24 * 60
    assert settings.cors_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]
    assert settings.ai_provider == "auto"
    assert settings.openai_api_key is None
    assert settings.anthropic_api_key is None
    assert settings.market_cache_minutes == 24 * 60
    assert settings.sse_keepalive_seconds == 15.0
    assert settings.debug is False


def test_missing_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PRAGATISHALA_JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError, match="jwt_secret_key"):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_weak_secret_rejected() -> None:
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(jwt_secret_key="short")


def test_cors_origins_split_from_string() -> None:
    settings = Settings(**VALID, cors_origins="http://a.com, http://b.com ,,")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("access_token_expire_minutes", 0),
        ("access_token_expire_minutes", -5),
        ("refresh_token_expire_minutes", 0),
    ],
)
def test_token_ttl_must_be_positive(field: str, value: int) -> None:
    with pytest.raises(ValidationError, match="token expiry must be positive"):
        Settings(**VALID, **{field: value})


def test_market_cache_must_be_non_negative() -> None:
    with pytest.raises(ValidationError, match="zero or positive"):
        Settings(**VALID, market_cache_minutes=-1)


def test_secret_is_secret() -> None:
    settings = Settings(**VALID)
    assert isinstance(settings.jwt_secret_key, SecretStr)
    assert "x" * 32 not in str(settings)


def test_get_settings_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_JWT_SECRET_KEY", "x" * 40)
    get_settings.cache_clear()
    first = get_settings()
    assert get_settings() is first
    get_settings.cache_clear()
