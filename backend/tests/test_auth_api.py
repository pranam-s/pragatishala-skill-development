"""End-to-end tests for auth endpoints."""

from datetime import timedelta

from app.config import get_settings
from app.security import _create_token, create_access_token

from tests.conftest import login_headers, register_user


async def test_register_creates_user(client) -> None:
    response = await register_user(
        client,
        email="asha@example.com",
        full_name="Asha Verma",
        target_role="Data Analyst",
        experience_level="fresher",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "asha@example.com"
    assert body["full_name"] == "Asha Verma"
    assert body["target_role"] == "Data Analyst"
    assert body["experience_level"] == "fresher"
    assert body["id"] >= 1
    assert "password" not in body


async def test_register_normalizes_email(client) -> None:
    response = await register_user(client, email="UPPER@Example.COM")
    assert response.status_code == 201
    assert response.json()["email"] == "upper@example.com"


async def test_register_duplicate_conflict(client) -> None:
    await register_user(client, email="dupe@example.com")
    response = await register_user(client, email="dupe@example.com")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


async def test_register_invalid_email(client) -> None:
    response = await register_user(client, email="not-an-email")
    assert response.status_code == 422


async def test_register_short_password(client) -> None:
    response = await register_user(client, password="short")
    assert response.status_code == 422


async def test_register_overlong_password(client) -> None:
    response = await register_user(client, password="x" * 129)
    assert response.status_code == 422


async def test_register_invalid_experience_level(client) -> None:
    response = await register_user(client, experience_level="wizard")
    assert response.status_code == 422


async def test_login_success_returns_pair(client) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "super-secret-pass-123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60
    assert body["access_token"] and body["refresh_token"]


async def test_login_wrong_password(client) -> None:
    await register_user(client)
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "incorrect email or password"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_login_unknown_user(client) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost@example.com", "password": "whatever-pass"},
    )
    assert response.status_code == 401


async def test_refresh_flow(client) -> None:
    await register_user(client)
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": "user1@example.com", "password": "super-secret-pass-123"},
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    pair = refreshed.json()
    assert pair["access_token"] and pair["refresh_token"]


async def test_refresh_rejects_access_token(client) -> None:
    await register_user(client)
    headers = await login_headers(client)
    access_token = headers["Authorization"].removeprefix("Bearer ")
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


async def test_refresh_rejects_garbage(client) -> None:
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert response.status_code == 401


async def test_auth_me_roundtrip(client) -> None:
    await register_user(client, full_name="Asha")
    headers = await login_headers(client)
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha"


async def test_auth_me_without_token(client) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_auth_me_with_garbage_token(client) -> None:
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 401


async def test_auth_me_token_for_missing_user(client) -> None:
    token = create_access_token("999999")
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_auth_me_token_with_non_numeric_subject(client) -> None:
    settings = get_settings()
    token = _create_token(
        "admin", "access", timedelta(minutes=5), settings.jwt_secret_key, settings.jwt_algorithm
    )
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
