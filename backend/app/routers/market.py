"""Market analysis endpoints (Phase 2)."""

from fastapi import APIRouter, Query

from app.deps import CurrentUser, EngineDep, SessionDep
from app.schemas import MarketInsightsRead
from app.services import get_market_insights

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/insights", response_model=MarketInsightsRead)
async def insights(
    current_user: CurrentUser,
    session: SessionDep,
    engine: EngineDep,
    role: str = Query(min_length=2, max_length=120),
) -> MarketInsightsRead:
    """Return (cached) market analysis for a role family."""
    insights, engine_used, refreshed_at, cached = await get_market_insights(session, engine, role)
    return MarketInsightsRead(
        role=insights.role,
        insights=insights,
        engine_used=engine_used,
        refreshed_at=refreshed_at,
        cached=cached,
    )
