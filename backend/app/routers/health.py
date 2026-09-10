"""Health and metadata endpoints."""

from fastapi import APIRouter, Request

from app import __version__
from app.ai.engine import SkillEngine
from app.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/healthz")
async def healthz(request: Request) -> dict[str, str]:
    """Liveness probe (public, unauthenticated)."""
    settings = get_settings()
    engine: SkillEngine | None = getattr(request.app.state, "skill_engine", None)
    return {
        "status": "ok",
        "version": __version__,
        "ai_provider": engine.provider_name if engine is not None else "uninitialized",
        "debug": str(settings.debug).lower(),
    }
