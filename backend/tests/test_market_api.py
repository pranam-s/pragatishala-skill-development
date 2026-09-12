"""End-to-end tests for market analysis endpoints."""

from app.config import get_settings

from tests.conftest import login_headers, register_user


async def test_market_requires_auth(client) -> None:
    assert (
        await client.get("/api/v1/market/insights", params={"role": "Data Analyst"})
    ).status_code == 401


async def test_market_fresh_then_cached(client) -> None:
    await register_user(client)
    headers = await login_headers(client)

    first = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
    )
    assert first.status_code == 200
    body = first.json()
    assert body["cached"] is False
    assert body["engine_used"] == "rule_based"
    assert body["role"] == "Data Analyst"
    insights = body["insights"]
    assert insights["demand_level"] in {"low", "moderate", "high", "very high"}
    assert insights["top_skills"]
    assert insights["advice"]

    second = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "  data analyst "}
    )
    assert second.status_code == 200
    assert second.json()["cached"] is True


async def test_market_refresh_flag_invalidates_cache(client) -> None:
    await register_user(client)
    headers = await login_headers(client)

    await client.get("/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"})
    refreshed = await client.get(
        "/api/v1/market/insights",
        headers=headers,
        params={"role": "Data Analyst", "refresh": "true"},
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["cached"] is False  # AR2-014: refresh bypasses the fresh cache
    assert body["model_used"] is None  # rule-based engine names no model

    after = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
    )
    assert after.json()["cached"] is True  # the refresh overwrote the cache


async def test_market_cache_disabled_refreshes(client, monkeypatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_MARKET_CACHE_MINUTES", "0")
    get_settings.cache_clear()
    await register_user(client)
    headers = await login_headers(client)

    first = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
    )
    assert first.status_code == 200
    assert first.json()["cached"] is False

    second = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
    )
    assert second.status_code == 200
    assert second.json()["cached"] is False  # zero-minute cache always refreshes


async def test_market_refresh_budget_is_per_user(client, monkeypatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_MARKET_REFRESH_PER_HOUR", "1")
    get_settings.cache_clear()
    await register_user(client)
    first_headers = await login_headers(client)
    await register_user(client, email="user2@example.com")
    second_headers = await login_headers(client, email="user2@example.com")

    first = await client.get(
        "/api/v1/market/insights",
        headers=first_headers,
        params={"role": "Data Analyst", "refresh": "true"},
    )
    assert first.status_code == 200

    exhausted = await client.get(
        "/api/v1/market/insights",
        headers=first_headers,
        params={"role": "Data Analyst", "refresh": "true"},
    )
    assert exhausted.status_code == 429  # AR3-006: the cache must bound LLM spend
    assert int(exhausted.headers["Retry-After"]) >= 1

    other = await client.get(
        "/api/v1/market/insights",
        headers=second_headers,
        params={"role": "Data Analyst", "refresh": "true"},
    )
    assert other.status_code == 200  # the budget is per user, not global


async def test_market_refresh_can_be_disabled(client, monkeypatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_MARKET_REFRESH_PER_HOUR", "0")
    get_settings.cache_clear()
    await register_user(client)
    headers = await login_headers(client)

    response = await client.get(
        "/api/v1/market/insights",
        headers=headers,
        params={"role": "Data Analyst", "refresh": "true"},
    )
    assert response.status_code == 403

    normal = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
    )
    assert normal.status_code == 200  # non-refresh reads are unaffected


async def test_market_unknown_role_uses_fallback(client) -> None:
    await register_user(client)
    headers = await login_headers(client)
    response = await client.get(
        "/api/v1/market/insights", headers=headers, params={"role": "Quantum Pet Groomer"}
    )
    assert response.status_code == 200
    assert response.json()["insights"]["demand_level"] in {
        "low",
        "moderate",
        "high",
        "very high",
    }


async def test_market_query_validation(client) -> None:
    headers = await login_headers(client)
    response = await client.get("/api/v1/market/insights", headers=headers, params={"role": "x"})
    assert response.status_code == 422
