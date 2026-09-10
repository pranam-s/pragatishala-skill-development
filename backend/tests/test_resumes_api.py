"""End-to-end tests for resume endpoints."""

from tests.conftest import login_headers, register_user

GENERATE = {
    "target_role": "Data Analyst",
    "skills": ["Python", "SQL", "Excel"],
    "experience_text": (
        "Data Intern, Acme Ltd\n- worked on monthly sales reports\nBuilt dashboards in Excel"
    ),
    "education_text": "B.Sc. Statistics, Pune University (2024)",
    "projects_text": "Retail demand forecast\n- used pandas and matplotlib",
}


async def test_generate_resume(client) -> None:
    await register_user(client, full_name="Asha Verma")
    headers = await login_headers(client, full_name="Asha Verma")

    response = await client.post("/api/v1/resumes/generate", headers=headers, json=GENERATE)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "My resume"
    assert body["engine_used"] == "rule_based"
    content = body["content"]
    assert content["headline"] == "Asha Verma - Data Analyst"
    assert content["professional_summary"]
    assert content["skills"] == ["Python", "SQL", "Excel"]
    assert content["experience"][0]["title"] == "Data Intern, Acme Ltd"
    assert content["education"][0]["institution"].startswith("B.Sc. Statistics")
    assert "- Drove on monthly sales reports." in content["experience"][0]["summary"]
    assert content["projects"][0]["name"] == "Retail demand forecast"


async def test_generate_resume_requires_auth(client) -> None:
    response = await client.post("/api/v1/resumes/generate", json=GENERATE)
    assert response.status_code == 401


async def test_generate_resume_validation(client) -> None:
    headers = await login_headers(client)
    response = await client.post("/api/v1/resumes/generate", headers=headers, json={})
    assert response.status_code == 422  # target_role required


async def test_list_and_get_resumes(client) -> None:
    headers = await login_headers(client)
    created = (await client.post("/api/v1/resumes/generate", headers=headers, json=GENERATE)).json()

    listed = await client.get("/api/v1/resumes", headers=headers)
    assert listed.status_code == 200
    assert [row["id"] for row in listed.json()] == [created["id"]]

    single = await client.get(f"/api/v1/resumes/{created['id']}", headers=headers)
    assert single.status_code == 200
    assert single.json()["id"] == created["id"]


async def test_get_missing_resume_404(client) -> None:
    headers = await login_headers(client)
    assert (await client.get("/api/v1/resumes/1234", headers=headers)).status_code == 404


async def test_patch_resume_title_and_content(client) -> None:
    headers = await login_headers(client)
    created = (await client.post("/api/v1/resumes/generate", headers=headers, json=GENERATE)).json()

    title_only = await client.patch(
        f"/api/v1/resumes/{created['id']}", headers=headers, json={"title": "Analytics CV"}
    )
    assert title_only.status_code == 200
    assert title_only.json()["title"] == "Analytics CV"
    assert title_only.json()["content"] == created["content"]  # untouched


async def test_patch_resume_content_only(client) -> None:
    headers = await login_headers(client)
    created = (await client.post("/api/v1/resumes/generate", headers=headers, json=GENERATE)).json()

    new_content = {
        "headline": "Asha - Analytics Engineer",
        "professional_summary": "Updated summary.",
        "skills": ["SQL"],
        "experience": [],
        "education": [],
        "projects": [],
    }
    response = await client.patch(
        f"/api/v1/resumes/{created['id']}", headers=headers, json={"content": new_content}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == created["title"]  # untouched
    assert body["content"]["headline"] == "Asha - Analytics Engineer"


async def test_patch_foreign_resume_404(client) -> None:
    owner = await login_headers(client, email="owner@example.com")
    created = (await client.post("/api/v1/resumes/generate", headers=owner, json=GENERATE)).json()

    other = await login_headers(client, email="other@example.com")
    response = await client.patch(
        f"/api/v1/resumes/{created['id']}", headers=other, json={"title": "Hijacked"}
    )
    assert response.status_code == 404
