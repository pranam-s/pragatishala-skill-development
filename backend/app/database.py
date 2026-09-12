"""Async database engine and session management."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import sqlalchemy
from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


@dataclass(frozen=True)
class SchemaUpgrade:
    """One idempotent, versioned step applied to older databases at startup.

    ``create_all`` never alters existing tables, so additive column changes
    need an explicit upgrade step (AR3-007). Alembic stays deferred to the
    first destructive schema change or the first production deployment
    (ADR 0003); this is the bridge until then (ADR 0008).
    """

    version: str
    table: str
    column: str
    ddl: str


SCHEMA_UPGRADES: tuple[SchemaUpgrade, ...] = (
    SchemaUpgrade(
        version="0002-market-reports-model-used",
        table="market_reports",
        column="model_used",
        ddl="ALTER TABLE market_reports ADD COLUMN model_used VARCHAR(120)",
    ),
)

_SCHEMA_UPGRADES_TABLE = text(
    "CREATE TABLE IF NOT EXISTS schema_upgrades (version VARCHAR(64) PRIMARY KEY)"
)


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


def _apply_schema_upgrades(connection: Connection) -> None:
    """Bring a database created by an older version up to the current schema.

    Each upgrade runs when its column is missing and is then recorded in
    ``schema_upgrades``; a database that already conforms is stamped so the
    column check is paid once.
    """
    connection.execute(_SCHEMA_UPGRADES_TABLE)
    inspector = sqlalchemy.inspect(connection)
    for upgrade in SCHEMA_UPGRADES:
        recorded = connection.execute(
            text("SELECT 1 FROM schema_upgrades WHERE version = :version"),
            {"version": upgrade.version},
        ).first()
        if recorded is not None:
            continue
        columns = {column["name"] for column in inspector.get_columns(upgrade.table)}
        if upgrade.column not in columns:
            connection.execute(text(upgrade.ddl))
            inspector.clear_cache()  # later upgrades must re-read altered tables
        connection.execute(
            text("INSERT INTO schema_upgrades (version) VALUES (:version)"),
            {"version": upgrade.version},
        )


async def init_db() -> None:
    """Create all tables and apply pending schema upgrades.

    Dev/MVP strategy: ``create_all`` on startup (see docs/adr/0003) plus
    idempotent, versioned column upgrades for tables created by older
    versions (ADR 0008) - ``create_all`` never alters existing tables.
    Idempotent and safe for SQLite and MySQL alike.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_schema_upgrades)


async def dispose_engine() -> None:
    """Dispose the engine (used on shutdown and between tests)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
