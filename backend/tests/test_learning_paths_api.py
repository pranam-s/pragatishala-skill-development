"""End-to-end tests for learning path endpoints."""

from tests.conftest import login_headers, register_user

NARRATIVE = (
    "I know basic HTML, CSS, and a little JavaScript. I want to become a "
    "front-end developer and learn React properly."
)


async def test_generate_requires_auth_and_assessment(client) -> None:
    assert (await client.post("/api/v1/learning-paths/generate", json={})).status_code == 401

    headers = await login_headers(client)
    response = await client.post("/api/v1/learning-paths/generate", headers=headers, json={})
    assert response.status_code == 404
    assert "assessment" in response.json()["detail"]


async def test_generate_from_latest_assessment(client) -> None:
    await register_user(client)
    headers = await login_headers(client)
    await client.post("/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE})

    response = await client.post("/api/v1/learning-paths/generate", headers=headers, json={})
    assert response.status_code == 201
    content = response.json()["content"]
    assert content["modules"]
    assert content["total_estimated_hours"] > 0
    assert content["next_steps"]
    assert content["headline"]


async def test_generate_with_explicit_assessment_id(client) -> None:
    headers = await login_headers(client)
    created = (
        await client.post("/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE})
    ).json()

    response = await client.post(
        "/api/v1/learning-paths/generate",
        headers=headers,
        json={"assessment_id": created["id"], "target_role": "Frontend Developer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["assessment_id"] == created["id"]
    assert body["target_role"] == "Frontend Developer"


async def test_generate_with_foreign_assessment_id_404(client) -> None:
    owner = await login_headers(client, email="owner@example.com")
    created = (
        await client.post("/api/v1/assessments", headers=owner, json={"input_text": NARRATIVE})
    ).json()

    attacker = await login_headers(client, email="attacker@example.com")
    response = await client.post(
        "/api/v1/learning-paths/generate",
        headers=attacker,
        json={"assessment_id": created["id"]},
    )
    assert response.status_code == 404


async def test_list_and_get_paths(client) -> None:
    headers = await login_headers(client)
    await client.post("/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE})
    created = (
        await client.post("/api/v1/learning-paths/generate", headers=headers, json={})
    ).json()

    listed = await client.get("/api/v1/learning-paths", headers=headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [created["id"]]

    single = await client.get(f"/api/v1/learning-paths/{created['id']}", headers=headers)
    assert single.status_code == 200

    missing = await client.get("/api/v1/learning-paths/999", headers=headers)
    assert missing.status_code == 404
