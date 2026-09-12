"""Tests for service-layer business logic and app-level behaviour."""

from pathlib import Path

import app.security as security_module
import httpx
import pytest
from app.ai.engine import RULE_BASED
from app.config import get_settings
from app.database import get_session_factory
from app.main import API_PREFIX, app, create_app
from app.schemas import RegisterRequest, UserUpdate
from app.services import (
    AlreadyRegisteredError,
    InvalidCredentialsError,
    apply_profile_update,
    authenticate_user,
    register_user,
)
from argon2 import PasswordHasher

from tests.conftest import TEST_SECRET, login_headers

_FAST_HASHER = PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)


async def test_register_user_duplicate_raises(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security_module, "_hasher", _FAST_HASHER)
    payload = RegisterRequest(email="dupe@example.com", password="super-secret-pass-123")
    async with get_session_factory()() as session:
        await register_user(session, payload)
        with pytest.raises(AlreadyRegisteredError):
            await register_user(session, payload)


async def test_authenticate_wrong_password_raises(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security_module, "_hasher", _FAST_HASHER)
    async with get_session_factory()() as session:
        await register_user(
            session, RegisterRequest(email="pw@example.com", password="super-secret-pass-123")
        )
        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(session, "pw@example.com", "wrong-password")


async def test_authenticate_unknown_user_burns_time(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(security_module, "_hasher", _FAST_HASHER)
    async with get_session_factory()() as session:
        with pytest.raises(InvalidCredentialsError):
            await authenticate_user(session, "nobody@example.com", "whatever-pass")


def test_apply_profile_update_excludes_unset() -> None:
    class FakeUser:  # minimal stand-in with assignable attributes
        full_name = "before"
        target_role = "old role"
        experience_level = "fresher"

    user = FakeUser()
    updated = apply_profile_update(user, UserUpdate(full_name="after"))
    assert updated.full_name == "after"
    assert updated.target_role == "old role"


def test_api_prefix() -> None:
    assert API_PREFIX == "/api/v1"


async def test_healthz_reports_engine(client) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ai_provider"] == RULE_BASED
    assert body["debug"] == "false"


async def test_healthz_before_lifespan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setenv(
        "PRAGATISHALA_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    )
    get_settings.cache_clear()
    try:
        fresh = create_app()  # no lifespan run: engine not attached
        transport = httpx.ASGITransport(app=fresh)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            body = (await http.get("/healthz")).json()
    finally:
        get_settings.cache_clear()
    assert body["ai_provider"] == "uninitialized"


async def test_cors_allows_configured_origin(client) -> None:
    response = await client.get("/healthz", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


async def test_cors_blocks_unknown_origin(client) -> None:
    response = await client.get("/healthz", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


async def test_openapi_schema_available(client) -> None:
    response = await client.get("/api/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert f"{API_PREFIX}/auth/register" in paths
    assert f"{API_PREFIX}/events" in paths


async def test_login_headers_helper_roundtrip(client) -> None:
    headers = await login_headers(client, email="helper@example.com")
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200


def test_aware_normalizes_naive_datetimes() -> None:
    from datetime import UTC, datetime

    from app.services import _aware

    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert _aware(naive).tzinfo is UTC
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    assert _aware(aware) is aware


async def test_lifespan_configures_engine_and_tables(client) -> None:
    from app.ai.engine import SkillEngine as _SkillEngine

    async with app.router.lifespan_context(app):
        assert isinstance(app.state.skill_engine, _SkillEngine)
        assert app.state.skill_engine.provider_name == RULE_BASED


async def test_market_cold_start_race_serves_winner_row(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two concurrent cold-cache requests must not 500 on the unique role.

    The loser of the insert race re-reads the winner's row and serves it
    (AR-028).
    """
    from datetime import UTC, datetime

    from app.ai.engine import SkillEngine
    from app.models import MarketReport
    from app.schemas import MarketInsights
    from app.services import get_market_insights

    insights_payload = MarketInsights(
        role="Data Analyst",
        demand_level="high",
        median_salary_range_inr="₹4-14 LPA",
        growth_outlook="Steady.",
        top_skills=["SQL"],
        trending_skills=["Python"],
        typical_employers=["Banks"],
        recommended_certifications=["PL-300"],
        advice=["Master SQL."],
    ).model_dump()

    factory = get_session_factory()
    async with factory() as session, factory() as sneaky:
        original_commit = session.commit

        async def racing_commit() -> None:
            sneaky.add(
                MarketReport(
                    role="data analyst",
                    content=insights_payload,
                    engine_used="rule_based",
                    refreshed_at=datetime.now(UTC),
                )
            )
            await sneaky.commit()
            await original_commit()

        monkeypatch.setattr(session, "commit", racing_commit)
        insights, engine_used, refreshed_at, was_cached, model_used = await get_market_insights(
            session, SkillEngine(None), "Data Analyst"
        )

    assert was_cached is True
    assert engine_used == "rule_based"
    assert model_used is None  # rule-based winner row carries no model
    assert insights.demand_level == "high"
    assert refreshed_at.tzinfo is not None


async def test_market_refresh_bypasses_fresh_cache(client) -> None:
    """refresh=true must regenerate even when the cached row is within TTL (AR2-014)."""
    from app.ai.engine import SkillEngine
    from app.services import get_market_insights

    factory = get_session_factory()
    async with factory() as session:
        engine = SkillEngine(None)
        await get_market_insights(session, engine, "Data Analyst")
        _first, _used, _at, cached, _model = await get_market_insights(
            session, engine, "Data Analyst"
        )
        assert cached is True
        _fresh, _used, _at, cached_after, _model = await get_market_insights(
            session, engine, "Data Analyst", refresh=True
        )
        assert cached_after is False
