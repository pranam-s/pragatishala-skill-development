"""End-to-end tests for user profile endpoints."""

from tests.conftest import login_headers, register_user


async def test_profile_requires_auth(client) -> None:
    assert (await client.get("/api/v1/users/me")).status_code == 401
    patch = await client.patch("/api/v1/users/me", json={"full_name": "X"})
    assert patch.status_code == 401


async def test_read_profile(client) -> None:
    await register_user(client, full_name="Asha", target_role="Data Analyst")
    headers = await login_headers(client, full_name="Asha", target_role="Data Analyst")
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Asha"


async def test_update_profile_partial(client) -> None:
    await register_user(client, full_name="Asha", target_role="Data Analyst")
    headers = await login_headers(client, full_name="Asha", target_role="Data Analyst")

    response = await client.patch(
        "/api/v1/users/me", headers=headers, json={"full_name": "Asha V."}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Asha V."
    assert body["target_role"] == "Data Analyst"  # unchanged


async def test_update_profile_all_fields(client) -> None:
    headers = await login_headers(client)
    response = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={
            "full_name": "New Name",
            "target_role": "Backend Developer",
            "experience_level": "junior",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "New Name"
    assert body["target_role"] == "Backend Developer"
    assert body["experience_level"] == "junior"


async def test_update_profile_validation(client) -> None:
    headers = await login_headers(client)
    response = await client.patch(
        "/api/v1/users/me", headers=headers, json={"experience_level": "guru"}
    )
    assert response.status_code == 422


async def test_update_profile_empty_patch(client) -> None:
    headers = await login_headers(client, full_name="Unchanged")
    response = await client.patch("/api/v1/users/me", headers=headers, json={})
    assert response.status_code == 200
    assert response.json()["full_name"] == "Unchanged"
