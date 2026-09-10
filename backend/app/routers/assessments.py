"""Skill assessment endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.deps import BusDep, CurrentUser, EngineDep, SessionDep
from app.schemas import AssessmentCreate, AssessmentRead
from app.services import NotFoundError, get_assessment, list_assessments, run_assessment

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.post("", response_model=AssessmentRead, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreate,
    current_user: CurrentUser,
    session: SessionDep,
    bus: BusDep,
    engine: EngineDep,
) -> AssessmentRead:
    """Analyze a free-form skills narrative (AI-enhanced, offline fallback)."""
    assessment = await run_assessment(session, bus, engine, current_user, payload)
    return AssessmentRead.model_validate(assessment)


@router.get("", response_model=list[AssessmentRead])
async def read_assessments(current_user: CurrentUser, session: SessionDep) -> list[AssessmentRead]:
    """List the authenticated user's assessments, newest first."""
    rows = await list_assessments(session, current_user.id)
    return [AssessmentRead.model_validate(row) for row in rows]


@router.get("/{assessment_id}", response_model=AssessmentRead)
async def read_assessment(
    assessment_id: int, current_user: CurrentUser, session: SessionDep
) -> AssessmentRead:
    """Fetch one assessment by id (ownership enforced)."""
    try:
        row = await get_assessment(session, current_user.id, assessment_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return AssessmentRead.model_validate(row)
