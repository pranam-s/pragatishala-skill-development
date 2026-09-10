"""End-to-end tests for skill assessment endpoints."""

from tests.conftest import login_headers, register_user

NARRATIVE = (
    "I have 3 years of experience building REST APIs with Python and FastAPI, "
    "I use Docker daily, and I am comfortable with SQL and Git."
)


async def _make_user(client, email: str = "user1@example.com") -> dict[str, str]:
    await register_user(client, email=email)
    return await login_headers(client, email=email)


async def test_assessment_requires_auth(client) -> None:
    response = await client.post("/api/v1/assessments", json={"input_text": NARRATIVE})
    assert response.status_code == 401
    assert (await client.get("/api/v1/assessments")).status_code == 401


async def test_create_assessment(client) -> None:
    headers = await _make_user(client)
    response = await client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"input_text": NARRATIVE, "target_role": "Backend Developer"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["engine_used"] == "rule_based"
    result = body["result"]
    names = {skill["name"] for skill in result["skills"]}
    assert {"Python", "FastAPI", "SQL", "Docker", "Git"} <= names
    assert 0 <= result["readiness_score"] <= 100
    assert result["strengths"]
    assert result["recommended_roles"]


async def test_create_assessment_falls_back_to_profile_role(client) -> None:
    await register_user(client, target_role="Data Analyst")
    headers = await login_headers(client, target_role="Data Analyst")
    response = await client.post(
        "/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE}
    )
    assert response.status_code == 201
    assert response.json()["target_role"] == "Data Analyst"


async def test_create_assessment_validation(client) -> None:
    headers = await _make_user(client)
    short = await client.post("/api/v1/assessments", headers=headers, json={"input_text": "hi"})
    assert short.status_code == 422
    long = await client.post(
        "/api/v1/assessments", headers=headers, json={"input_text": "x" * 8001}
    )
    assert long.status_code == 422


async def test_list_assessments_newest_first(client) -> None:
    headers = await _make_user(client)
    for _ in range(2):
        await client.post("/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE})
    response = await client.get("/api/v1/assessments", headers=headers)
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 2
    assert rows[0]["id"] > rows[1]["id"]


async def test_get_single_assessment(client) -> None:
    headers = await _make_user(client)
    created = (
        await client.post("/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE})
    ).json()
    response = await client.get(f"/api/v1/assessments/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_get_missing_assessment_404(client) -> None:
    headers = await _make_user(client)
    response = await client.get("/api/v1/assessments/424242", headers=headers)
    assert response.status_code == 404


async def test_other_users_assessment_is_404(client) -> None:
    first = await _make_user(client, email="first@example.com")
    created = (
        await client.post("/api/v1/assessments", headers=first, json={"input_text": NARRATIVE})
    ).json()

    second = await _make_user(client, email="second@example.com")
    response = await client.get(f"/api/v1/assessments/{created['id']}", headers=second)
    assert response.status_code == 404


async def test_invalid_assessment_id(client) -> None:
    headers = await _make_user(client)
    response = await client.get("/api/v1/assessments/not-an-int", headers=headers)
    assert response.status_code == 422
