"""Shared fixtures: isolated database, fast Argon2, authenticated API clients."""

import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

# ``app.main`` builds the FastAPI app at import time and settings require a
# JWT secret, so bootstrap safe defaults before any application import.
os.environ.setdefault("PRAGATISHALA_JWT_SECRET_KEY", "unit-test-secret-0123456789abcdef")
os.environ.setdefault("PRAGATISHALA_DATABASE_URL", "sqlite+aiosqlite:///./bootstrap.db")

import app.security as security_module
import httpx
import pytest
from app.ai.engine import SkillEngine
from app.config import get_settings
from app.database import dispose_engine, init_db
from app.deps import get_event_bus
from app.events import EventBus
from app.main import app
from argon2 import PasswordHasher

TEST_SECRET = "unit-test-secret-0123456789abcdef-unit-test-secret"
_FAST_HASHER = PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)


@pytest.fixture(autouse=True)
async def _isolated_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> AsyncIterator[None]:
    """Fresh settings + database per test; fast Argon2 parameters."""
    monkeypatch.setenv("PRAGATISHALA_JWT_SECRET_KEY", TEST_SECRET)
    monkeypatch.setenv(
        "PRAGATISHALA_DATABASE_URL", f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    )
    # Generous rate limits so only the dedicated rate-limit tests trip them;
    # the limiter state is reset for cross-test isolation.
    monkeypatch.setenv("PRAGATISHALA_AUTH_RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("PRAGATISHALA_GENERATION_RATE_LIMIT_PER_MINUTE", "1000")
    for var in (
        "PRAGATISHALA_MARKET_CACHE_MINUTES",
        "PRAGATISHALA_SSE_KEEPALIVE_SECONDS",
        "PRAGATISHALA_AI_PROVIDER",
        "PRAGATISHALA_DEBUG",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(security_module, "_hasher", _FAST_HASHER)
    get_settings.cache_clear()
    app.state.rate_limiter.reset()
    await dispose_engine()
    yield
    await dispose_engine()
    get_settings.cache_clear()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """HTTP client bound to the app with an initialized (offline) database."""
    app.state.skill_engine = SkillEngine(None)
    await init_db()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.fixture
async def bus_client() -> AsyncIterator[tuple[httpx.AsyncClient, EventBus]]:
    """Client whose event bus is a per-test instance (event-loop safe)."""
    bus = EventBus()
    app.dependency_overrides[get_event_bus] = lambda: bus
    try:
        app.state.skill_engine = SkillEngine(None)
        await init_db()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            yield http, bus
    finally:
        app.dependency_overrides.pop(get_event_bus, None)


async def register_user(
    client: httpx.AsyncClient,
    email: str = "user1@example.com",
    password: str = "super-secret-pass-123",
    **extra: Any,
) -> httpx.Response:
    """Register a user via the API."""
    payload: dict[str, Any] = {"email": email, "password": password, **extra}
    return await client.post("/api/v1/auth/register", json=payload)


async def login_headers(
    client: httpx.AsyncClient,
    email: str = "user1@example.com",
    password: str = "super-secret-pass-123",
    **register_extra: Any,
) -> dict[str, str]:
    """Register (tolerates an existing account) and return bearer auth headers."""
    await register_user(client, email=email, password=password, **register_extra)
    login = await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token: str = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
