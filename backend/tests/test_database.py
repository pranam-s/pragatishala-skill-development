"""Tests for database engine/session lifecycle."""

from pathlib import Path

import pytest
from app.config import get_settings
from app.database import (
    Base,
    dispose_engine,
    get_engine,
    get_session,
    get_session_factory,
    init_db,
)
from app.models import User
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


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
