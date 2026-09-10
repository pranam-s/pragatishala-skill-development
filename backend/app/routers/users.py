"""User profile endpoints."""

from fastapi import APIRouter

from app.deps import CurrentUser, SessionDep
from app.schemas import UserRead, UserUpdate
from app.services import apply_profile_update

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_profile(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
async def update_profile(
    payload: UserUpdate, current_user: CurrentUser, session: SessionDep
) -> UserRead:
    """Update editable profile fields (unset fields are left unchanged)."""
    user = apply_profile_update(current_user, payload)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)
