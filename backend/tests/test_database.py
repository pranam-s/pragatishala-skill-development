"""Tests for database engine/session lifecycle."""

import sqlite3
from pathlib import Path

import httpx
import pytest
from app.ai.engine import SkillEngine
from app.config import get_settings
from app.database import (
    Base,
    dispose_engine,
    get_engine,
    get_session,
    get_session_factory,
    init_db,
)
from app.main import app
from app.models import User
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import login_headers, register_user


def _database_path() -> str:
    url = get_settings().database_url
    prefix = "sqlite+aiosqlite:///"
    assert url.startswith(prefix)
    return url.removeprefix(prefix)


def _create_legacy_market_reports(path: str) -> None:
    """Reproduce the pre-`model_used` schema (the AR3-007 probe)."""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE market_reports ("
        "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
        "role VARCHAR(120) NOT NULL, "
        "content JSON NOT NULL, "
        "engine_used VARCHAR(40) NOT NULL, "
        "refreshed_at DATETIME, "
        "created_at DATETIME)"
    )
    conn.commit()
    conn.close()


async def _market_reports_columns() -> set[str]:
    async with get_engine().connect() as conn:
        return await conn.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("market_reports")
            }
        )


async def _applied_upgrade_versions() -> list[str]:
    async with get_engine().connect() as conn:
        return list((await conn.execute(text("SELECT version FROM schema_upgrades"))).scalars())


def test_engine_is_cached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "PRAGATISHALA_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'x.db').as_posix()}"
    )
    get_settings.cache_clear()
    engine = get_engine()
    assert get_engine() is engine
    get_settings.cache_clear()


async def test_session_factory_is_cached(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "PRAGATISHALA_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'y.db').as_posix()}"
    )
    get_settings.cache_clear()
    factory = get_session_factory()
    assert get_session_factory() is factory
    get_settings.cache_clear()


async def test_init_db_is_idempotent(client) -> None:
    await init_db()
    await init_db()  # second run must not fail
    async with get_engine().connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: (
                set(Base.metadata.tables) & set(sync_conn.dialect.get_table_names(sync_conn))
            )
        )
    assert {"users", "assessments", "learning_paths", "resumes", "market_reports"} <= tables


async def test_get_session_yields_working_session(client) -> None:
    agen = get_session()
    try:
        session = await agen.__anext__()
        assert isinstance(session, AsyncSession)
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    finally:
        await agen.aclose()


async def test_dispose_engine_resets_singletons(client) -> None:
    engine = get_engine()
    await dispose_engine()
    assert get_engine() is not engine


async def test_user_defaults(client) -> None:
    await init_db()
    async with get_session_factory()() as session:
        user = User(email="defaults@example.com", hashed_password="h")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        assert user.full_name == ""
        assert user.target_role is None
        assert user.created_at is not None
        assert user.updated_at is not None


# --- AR3-007: create_all never alters existing tables; startup upgrades do ---


async def test_init_db_upgrades_legacy_market_reports() -> None:
    _create_legacy_market_reports(_database_path())
    await init_db()
    await init_db()  # second run: the recorded upgrade must not re-run
    assert "model_used" in await _market_reports_columns()
    assert await _applied_upgrade_versions() == ["0002-market-reports-model-used"]


async def test_fresh_database_is_stamped_without_alter() -> None:
    await init_db()
    assert "model_used" in await _market_reports_columns()  # create_all made it
    assert await _applied_upgrade_versions() == ["0002-market-reports-model-used"]


async def test_market_endpoint_works_on_a_pre_upgrade_database() -> None:
    _create_legacy_market_reports(_database_path())
    app.state.skill_engine = SkillEngine(None)
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        await register_user(http)
        headers = await login_headers(http)
        response = await http.get(
            "/api/v1/market/insights", headers=headers, params={"role": "Data Analyst"}
        )
    assert response.status_code == 200  # was a 500 before the startup upgrade
