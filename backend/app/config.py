"""Application settings.

All secrets are read from the environment (optionally via a local ``.env`` file
that is git-ignored). There are no hardcoded keys anywhere in the codebase.

Every environment variable is prefixed with ``PRAGATISHALA_`` (for example
``PRAGATISHALA_JWT_SECRET_KEY``).
"""

import math
from collections import Counter
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Secrets that are publicly known (committed examples, framework defaults).
# Copying any of them into a real deployment would let anyone forge JWTs, so
# the settings validator refuses to boot when one appears *inside* the
# supplied secret (case-insensitive): an exact-match list alone would accept
# decorated placeholders like "1<placeholder>2345678".
_KNOWN_PLACEHOLDER_SECRETS: frozenset[str] = frozenset(
    {
        "change-me-at-least-32-bytes-long",
        "change-me-generate-a-real-secret-with-secrets-token-urlsafe",
        "changeme-changeme-changeme-changeme",
        "your-256-bit-secret-your-256-bit-secret",
        "super-secret-key-super-secret-key-123",
        "my-secret-key-my-secret-key-123456",
        "dummy-signing-key-for-local-development-only",
    }
)

# HS256 requires >= 32 bytes (RFC 7518 section 3.2). Length alone is not
# sufficient: a key drawn from a handful of distinct characters is brute-
# forceable regardless of length, so a basic entropy floor applies too.
_MIN_SECRET_BYTES = 32
_MIN_SECRET_DISTINCT_CHARS = 12
_MIN_SECRET_ENTROPY_BITS = 3.0


class Settings(BaseSettings):
    """Runtime configuration sourced from the environment."""

    model_config = SettingsConfigDict(
        env_prefix="PRAGATISHALA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "PragatiShala API"
    app_version: str = "0.1.0"
    debug: bool = False

    # --- Database ---
    # Default to a local SQLite database for development. For production set a
    # MySQL URL such as: mysql+aiomysql://user:pass@host:3306/pragatishala
    database_url: str = "sqlite+aiosqlite:///./pragatishala.db"

    # --- Auth ---
    jwt_secret_key: SecretStr
    # HMAC-SHA-2 family only: a free-text algorithm name would let a stray
    # "none" (or an RS/HS confusion pair) reach jwt.encode/decode (AR-025).
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 7 * 24 * 60

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- AI integration (Phase 2) ---
    # "auto" picks the first provider whose API key is present in the
    # environment; "rule_based" forces the deterministic offline engine.
    ai_provider: Literal["auto", "openai", "anthropic", "rule_based"] = "auto"
    openai_api_key: SecretStr | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: SecretStr | None = None
    anthropic_base_url: str = "https://api.anthropic.com"
    anthropic_model: str = "claude-sonnet-4-5"
    ai_timeout_seconds: float = 30.0

    # --- Market analysis cache ---
    market_cache_minutes: int = 24 * 60
    # Per-user hourly budget for refresh=true cache purges; without it the
    # cache stops bounding LLM spend for any authenticated user (AR3-006).
    # 0 disables refresh entirely.
    market_refresh_per_hour: int = 6

    # --- Server-Sent Events ---
    sse_keepalive_seconds: float = 15.0

    # --- Rate limiting (requests per minute per client; 0 disables a bucket) ---
    auth_rate_limit_per_minute: int = 10
    generation_rate_limit_per_minute: int = 15

    @field_validator("auth_rate_limit_per_minute", "generation_rate_limit_per_minute")
    @classmethod
    def _non_negative_limit(cls, value: int) -> int:
        if value < 0:
            msg = "rate limits must be zero or positive"
            raise ValueError(msg)
        return value

    @field_validator("jwt_secret_key")
    @classmethod
    def _strong_secret(cls, value: SecretStr) -> SecretStr:
        """Reject publicly-known placeholders and low-entropy signing keys.

        Length alone cannot catch a secret copied from a committed example
        (a known key lets anyone forge tokens for any user), so validation
        also refuses placeholder literals and degenerate character sets.
        """
        secret = value.get_secret_value()
        stripped = secret.strip().casefold()
        if any(placeholder in stripped for placeholder in _KNOWN_PLACEHOLDER_SECRETS):
            msg = (
                "PRAGATISHALA_JWT_SECRET_KEY is a publicly-known placeholder; "
                'generate a real secret, e.g. python -c "import secrets; '
                'print(secrets.token_urlsafe(48))"'
            )
            raise ValueError(msg)
        if len(secret.encode()) < _MIN_SECRET_BYTES:
            msg = "PRAGATISHALA_JWT_SECRET_KEY must be at least 32 bytes long"
            raise ValueError(msg)
        distinct = len(set(secret))
        entropy = cls._entropy_bits(secret)
        if distinct < _MIN_SECRET_DISTINCT_CHARS or entropy < _MIN_SECRET_ENTROPY_BITS:
            detail = (
                "too few distinct characters"
                if distinct < _MIN_SECRET_DISTINCT_CHARS
                else "character distribution too flat (too repetitive)"
            )
            msg = (
                f"PRAGATISHALA_JWT_SECRET_KEY looks low-entropy ({detail}); "
                "generate a random secret with the secrets module"
            )
            raise ValueError(msg)
        return value

    @staticmethod
    def _entropy_bits(value: str) -> float:
        """Shannon entropy of *value* in bits per character (max ~log2 of alphabet)."""
        total = len(value)
        return -sum((n / total) * math.log2(n / total) for n in Counter(value).values())

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        """Allow a comma-separated string (common for env vars)."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("access_token_expire_minutes", "refresh_token_expire_minutes")
    @classmethod
    def _positive_ttl(cls, value: int) -> int:
        if value <= 0:
            msg = "token expiry must be positive"
            raise ValueError(msg)
        return value

    @field_validator("market_cache_minutes", "market_refresh_per_hour")
    @classmethod
    def _non_negative_market_setting(cls, value: int) -> int:
        if value < 0:
            msg = "market settings must be zero or positive"
            raise ValueError(msg)
        return value


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""
    # Required fields (e.g. the JWT secret) are provided via environment variables.
    return Settings()
