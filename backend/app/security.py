"""Password hashing and JWT creation/validation."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from pydantic import SecretStr

from app.config import get_settings

_token_types = Literal["access", "refresh"]

# Every token is bound to this issuer/audience pair and decode enforces both,
# so tokens minted for (or by) another system never validate here (AR-025).
_JWT_ISSUER = "pragatishala"
_JWT_AUDIENCE = "pragatishala-clients"


class TokenError(Exception):
    """Raised when a token is missing, invalid, expired, or of the wrong type."""


_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a plaintext password with Argon2id."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True when *plain* matches *hashed*."""
    try:
        return _hasher.verify(hashed, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _create_token(
    subject: str,
    token_type: _token_types,
    expires_delta: timedelta,
    secret: SecretStr,
    algorithm: str,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iss": _JWT_ISSUER,
        "aud": _JWT_AUDIENCE,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret.get_secret_value(), algorithm=algorithm)


def create_access_token(subject: str) -> str:
    """Create a short-lived access token for *subject* (user id as string)."""
    settings = get_settings()
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.access_token_expire_minutes),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token for *subject*."""
    settings = get_settings()
    return _create_token(
        subject,
        "refresh",
        timedelta(minutes=settings.refresh_token_expire_minutes),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
    )


def decode_token(token: str, expected_type: _token_types) -> str:
    """Validate *token* and return its subject.

    Raises:
        TokenError: when the token is malformed, expired, signed with another
            key, minted for another issuer/audience, or not of the expected
            type.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=_JWT_AUDIENCE,
            issuer=_JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "jti", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as exc:
        msg = "token has expired"
        raise TokenError(msg) from exc
    except jwt.InvalidTokenError as exc:
        msg = "token is invalid"
        raise TokenError(msg) from exc

    if payload.get("type") != expected_type:
        msg = f"expected a {expected_type} token"
        raise TokenError(msg)

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        msg = "token subject is missing"
        raise TokenError(msg)
    return subject
