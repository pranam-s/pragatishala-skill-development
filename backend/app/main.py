"""FastAPI application factory and ASGI entrypoint.

Run locally with either of::

    uv run uvicorn app.main:app --reload
    uv run uvicorn main:app --reload   # ``main.py`` re-exports this app
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.ai.engine import SkillEngine
from app.ai.provider import build_provider
from app.config import get_settings
from app.database import dispose_engine, init_db
from app.ratelimit import (
    AUTH_BUCKET,
    GENERATION_BUCKET,
    RateLimitMiddleware,
    SlidingWindowLimiter,
)
from app.routers import assessments, auth, events, health, learning_paths, market, resumes, users

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start up: configure the AI engine and create tables; dispose on shutdown."""
    settings = get_settings()
    app.state.skill_engine = SkillEngine(build_provider(settings))
    await init_db()
    yield
    await dispose_engine()


def _rate_limits() -> dict[str, int]:
    """Current per-bucket limits (resolved per request so env changes apply)."""
    settings = get_settings()
    return {
        AUTH_BUCKET: settings.auth_rate_limit_per_minute,
        GENERATION_BUCKET: settings.generation_rate_limit_per_minute,
    }


def create_app() -> FastAPI:
    """Build the configured application instance."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    # Rate limiting sits inside CORS so 429 responses still carry CORS
    # headers and the SPA can surface the detail message.
    app.state.rate_limiter = SlidingWindowLimiter()
    app.add_middleware(
        RateLimitMiddleware,
        limiter=app.state.rate_limiter,
        limits=_rate_limits,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    for module in (auth, users, assessments, learning_paths, resumes, market, events):
        app.include_router(module.router, prefix=API_PREFIX)
    return app


app = create_app()
