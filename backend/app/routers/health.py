"""Health and metadata endpoints."""

from fastapi import APIRouter, Request

from app import __version__
from app.ai.engine import SkillEngine
from app.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/healthz")
async def healthz(request: Request) -> dict[str, str]:
    """Liveness probe (public, unauthenticated).

    Minimal by default: an unauthenticated surface must not disclose the
    active AI provider, version, or debug posture (AR-027). Diagnostics are
    opt-in via ``PRAGATISHALA_DEBUG``.
    """
    if not get_settings().debug:
        return {"status": "ok"}
    engine: SkillEngine | None = getattr(request.app.state, "skill_engine", None)
    return {
        "status": "ok",
        "version": __version__,
        "ai_provider": engine.provider_name if engine is not None else "uninitialized",
        "debug": "true",
    }
