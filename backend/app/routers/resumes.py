"""Resume endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.deps import BusDep, CurrentUser, EngineDep, SessionDep
from app.schemas import (
    ResumeGenerateRequest,
    ResumeRead,
    ResumeUpdate,
)
from app.services import (
    NotFoundError,
    generate_resume,
    get_resume,
    list_resumes,
    update_resume,
)

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/generate", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def generate(
    payload: ResumeGenerateRequest,
    current_user: CurrentUser,
    session: SessionDep,
    bus: BusDep,
    engine: EngineDep,
) -> ResumeRead:
    """Draft a structured resume with AI assistance (offline fallback available)."""
    resume = await generate_resume(session, bus, engine, current_user, payload)
    return ResumeRead.model_validate(resume)


@router.get("", response_model=list[ResumeRead])
async def read_resumes(current_user: CurrentUser, session: SessionDep) -> list[ResumeRead]:
    """List the authenticated user's resumes, newest first."""
    rows = await list_resumes(session, current_user.id)
    return [ResumeRead.model_validate(row) for row in rows]


@router.get("/{resume_id}", response_model=ResumeRead)
async def read_resume(resume_id: int, current_user: CurrentUser, session: SessionDep) -> ResumeRead:
    """Fetch one resume by id (ownership enforced)."""
    try:
        row = await get_resume(session, current_user.id, resume_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResumeRead.model_validate(row)


@router.patch("/{resume_id}", response_model=ResumeRead)
async def patch_resume(
    resume_id: int,
    payload: ResumeUpdate,
    current_user: CurrentUser,
    session: SessionDep,
) -> ResumeRead:
    """Update an owned resume's title and/or content."""
    try:
        row = await update_resume(session, current_user, resume_id, payload.title, payload.content)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ResumeRead.model_validate(row)
