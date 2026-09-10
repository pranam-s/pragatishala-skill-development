"""Learning path endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.deps import BusDep, CurrentUser, EngineDep, SessionDep
from app.schemas import LearningPathCreate, LearningPathRead
from app.services import (
    NotFoundError,
    generate_learning_path,
    get_learning_path,
    list_learning_paths,
)

router = APIRouter(prefix="/learning-paths", tags=["learning-paths"])


@router.post("/generate", response_model=LearningPathRead, status_code=status.HTTP_201_CREATED)
async def generate(
    payload: LearningPathCreate,
    current_user: CurrentUser,
    session: SessionDep,
    bus: BusDep,
    engine: EngineDep,
) -> LearningPathRead:
    """Generate a personalized roadmap from an owned assessment."""
    try:
        path = await generate_learning_path(session, bus, engine, current_user, payload)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LearningPathRead.model_validate(path)


@router.get("", response_model=list[LearningPathRead])
async def read_paths(current_user: CurrentUser, session: SessionDep) -> list[LearningPathRead]:
    """List the authenticated user's learning paths, newest first."""
    rows = await list_learning_paths(session, current_user.id)
    return [LearningPathRead.model_validate(row) for row in rows]


@router.get("/{path_id}", response_model=LearningPathRead)
async def read_path(
    path_id: int, current_user: CurrentUser, session: SessionDep
) -> LearningPathRead:
    """Fetch one learning path by id (ownership enforced)."""
    try:
        row = await get_learning_path(session, current_user.id, path_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return LearningPathRead.model_validate(row)
