"""Tests for app.security (password hashing + JWT)."""

from datetime import timedelta

import jwt
import pytest
from app.config import Settings, get_settings
from app.deps import user_id_from_subject
from app.security import (
    _JWT_AUDIENCE,
    _JWT_ISSUER,
    TokenError,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "Qk7wR2tY9uP5mJ3nV8cX4bZ6dF8gH2sL"


def test_password_roundtrip() -> None:
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_verify_garbage_hash_is_false() -> None:
    assert not verify_password("whatever", "not-a-hash")


def test_access_token_roundtrip() -> None:
    token = create_access_token("42")
    assert decode_token(token, expected_type="access") == "42"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token("7")
    assert decode_token(token, expected_type="refresh") == "7"


def test_wrong_token_type_rejected() -> None:
    access = create_access_token("42")
    with pytest.raises(TokenError, match="expected a refresh token"):
        decode_token(access, expected_type="refresh")


def test_expired_token_rejected() -> None:
    settings = get_settings()
    token = _create_token(
        "42",
        "access",
        timedelta(minutes=-1),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
    )
    with pytest.raises(TokenError, match="expired"):
        decode_token(token, expected_type="access")


def test_malformed_token_rejected() -> None:
    with pytest.raises(TokenError, match="invalid"):
        decode_token("not.a.jwt", expected_type="access")


def test_wrong_signature_rejected() -> None:
    token = jwt.encode(
        {"sub": "1", "type": "access", "exp": 4102444800},
        "another-secret-0123456789abcdef-unit-test",
    )
    with pytest.raises(TokenError, match="invalid"):
        decode_token(token, expected_type="access")


def test_missing_subject_rejected() -> None:
    settings = get_settings()
    token = _create_token(
        "",
        "access",
        timedelta(minutes=5),
        settings.jwt_secret_key,
        settings.jwt_algorithm,
    )
    with pytest.raises(TokenError, match="subject is missing"):
        decode_token(token, expected_type="access")


def test_non_string_subject_rejected() -> None:
    """Non-string sub is invalid per RFC 7519; PyJWT 2.14 enforces it."""
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": 42,
            "type": "access",
            "exp": 4102444800,
            "iat": 1700000000,
            "jti": "crafted",
            "iss": _JWT_ISSUER,
            "aud": _JWT_AUDIENCE,
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(TokenError, match="invalid"):
        decode_token(token, expected_type="access")


def test_foreign_audience_rejected() -> None:
    """A token minted for another audience must not validate (AR-025)."""
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": "42",
            "type": "access",
            "exp": 4102444800,
            "iss": _JWT_ISSUER,
            "aud": "someone-else",
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(TokenError, match="invalid"):
        decode_token(token, expected_type="access")


def test_token_without_claims_rejected() -> None:
    """Required claims (iss/aud/iat/exp/jti) missing means invalid (AR-025)."""
    settings = get_settings()
    token = jwt.encode(
        {"sub": "42", "type": "access", "exp": 4102444800},
        settings.jwt_secret_key.get_secret_value(),
        algorithm="HS256",
    )
    with pytest.raises(TokenError, match="invalid"):
        decode_token(token, expected_type="access")


def test_jwt_algorithm_locked_to_hs_family() -> None:
    with pytest.raises(ValueError, match="Input should be"):
        Settings(jwt_secret_key=SECRET, jwt_algorithm="none")
    with pytest.raises(ValueError, match="Input should be"):
        Settings(jwt_secret_key=SECRET, jwt_algorithm="RS256")


# --- JWT subject parsing: malformed subjects degrade to None, never crash ---


def test_subject_parsing_accepts_decimal_ids() -> None:
    assert user_id_from_subject("42") == 42
    assert user_id_from_subject("0") == 0


@pytest.mark.parametrize("subject", ["", " 12", "+1", "-1", "4 2", "²", "١٢", "abc"])
def test_subject_parsing_rejects_malformed_subjects(subject: str) -> None:
    # Non-ASCII digit characters ("²") pass str.isdigit but int() rejects them;
    # the parser must return None instead of raising (a 500 where 401 belongs).
    assert user_id_from_subject(subject) is None
