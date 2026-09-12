"""Market analysis endpoints (Phase 2)."""

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import get_settings
from app.deps import CurrentUser, EngineDep, SessionDep
from app.ratelimit import SlidingWindowLimiter
from app.schemas import MarketInsightsRead
from app.services import get_market_insights

router = APIRouter(prefix="/market", tags=["market"])

# A refresh purge triggers a billable LLM call, so it draws from a per-user
# hourly budget instead of being bounded only by the per-IP generation limit
# (AR3-006).
_REFRESH_WINDOW_SECONDS = 3600.0


@router.get("/insights", response_model=MarketInsightsRead)
async def insights(
    request: Request,
    current_user: CurrentUser,
    session: SessionDep,
    engine: EngineDep,
    role: str = Query(min_length=2, max_length=120),
    refresh: bool = Query(
        False,
        description="Bypass the cache and regenerate the analysis for this role.",
    ),
) -> MarketInsightsRead:
    """Return (cached) market analysis for a role family.

    ``refresh=true`` invalidates the cached report for the role: the next
    response is regenerated and overwrites the cache entry. It draws from a
    per-user hourly budget (``PRAGATISHALA_MARKET_REFRESH_PER_HOUR``; 0
    disables it) so the cache keeps bounding LLM spend.
    """
    if refresh:
        _check_refresh_budget(request, current_user.id)
    insights, engine_used, refreshed_at, cached, model_used = await get_market_insights(
        session, engine, role, refresh=refresh
    )
    return MarketInsightsRead(
        role=insights.role,
        insights=insights,
        engine_used=engine_used,
        model_used=model_used,
        refreshed_at=refreshed_at,
        cached=cached,
    )


def _check_refresh_budget(request: Request, user_id: int) -> None:
    budget = get_settings().market_refresh_per_hour
    if budget <= 0:
        raise HTTPException(status_code=403, detail="Market refresh is disabled on this deployment")
    limiter: SlidingWindowLimiter = request.app.state.rate_limiter
    allowed, retry_after = limiter.check(
        f"market-refresh:{user_id}", budget, window=_REFRESH_WINDOW_SECONDS
    )
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Market refresh budget exhausted; try again later",
            headers={"Retry-After": str(retry_after)},
        )
