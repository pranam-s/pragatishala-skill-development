"""Tests for app.config."""

import secrets

import pytest
from app.config import Settings, get_settings
from pydantic import SecretStr, ValidationError

# Random-looking 32+ char secrets (single repeated characters are rejected as
# low-entropy, so tests must use realistic keys).
VALID = {"jwt_secret_key": "Zk9xQ2wR7tY5uJ8mN3vP6bC4dF7gH1sL"}
PLACEHOLDERS = [
    "change-me-at-least-32-bytes-long",
    "change-me-generate-a-real-secret-with-secrets-token-urlsafe",
    "changeme-changeme-changeme-changeme",
    "your-256-bit-secret-your-256-bit-secret",
    "super-secret-key-super-secret-key-123",
    "my-secret-key-my-secret-key-123456",
    "dummy-signing-key-for-local-development-only",
]


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


@pytest.mark.parametrize("placeholder", PLACEHOLDERS)
def test_placeholder_secret_rejected(placeholder: str) -> None:
    """A copied example value must never validate: it is publicly known."""
    with pytest.raises(ValidationError, match="publicly-known placeholder"):
        Settings(jwt_secret_key=placeholder)


def test_placeholder_with_different_case_or_padding_rejected() -> None:
    for variant in ("  CHANGE-ME-AT-LEAST-32-BYTES-LONG", "Change-Me-At-Least-32-Bytes-Long\n"):
        with pytest.raises(ValidationError, match="publicly-known placeholder"):
            Settings(jwt_secret_key=variant)


def test_decorated_placeholder_rejected() -> None:
    """Placeholders buried inside longer keys must still trip the denylist."""
    decorated = "1change-me-at-least-32-bytes-long2345678"
    assert len(decorated.encode()) >= 32
    with pytest.raises(ValidationError, match="publicly-known placeholder"):
        Settings(jwt_secret_key=decorated)


def test_random_32_byte_secrets_accepted() -> None:
    for generated in (secrets.token_urlsafe(32), secrets.token_hex(32), secrets.token_hex(16)):
        settings = Settings(jwt_secret_key=generated)
        assert isinstance(settings.jwt_secret_key, SecretStr)


@pytest.mark.parametrize(
    "weak",
    [
        "x" * 32,
        "a" * 64,
        "ab" * 20,
        "passwordpasswordpasswordpasswordpassword",
    ],
)
def test_low_entropy_secret_rejected(weak: str) -> None:
    with pytest.raises(ValidationError, match="low-entropy"):
        Settings(jwt_secret_key=weak)


def test_low_entropy_message_names_the_failing_condition() -> None:
    # 13 distinct chars (passes the distinct floor) but a flat a-heavy
    # distribution (entropy ~2.3 bits/char): only the entropy branch fires.
    flat = "a" * 20 + "bcdefghijklm"
    with pytest.raises(ValidationError, match="too repetitive"):
        Settings(jwt_secret_key=flat)
    with pytest.raises(ValidationError, match="too few distinct characters"):
        Settings(jwt_secret_key="x" * 40)


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
    monkeypatch.setenv("PRAGATISHALA_JWT_SECRET_KEY", VALID["jwt_secret_key"])
    get_settings.cache_clear()
    first = get_settings()
    assert get_settings() is first
    get_settings.cache_clear()
