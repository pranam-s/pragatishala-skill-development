"""Tests for app.security (password hashing + JWT)."""

from datetime import timedelta

import jwt
import pytest
from app.config import get_settings
from app.security import (
    TokenError,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


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
    settings = get_settings()
    secret = settings.jwt_secret_key.get_secret_value()
    token = jwt.encode({"sub": 42, "type": "access", "exp": 4102444800}, secret, algorithm="HS256")
    with pytest.raises(TokenError, match="invalid"):
        decode_token(token, expected_type="access")
