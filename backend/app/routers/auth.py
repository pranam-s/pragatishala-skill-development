"""Authentication endpoints: register, login (OAuth2 password flow), refresh."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.schemas import RefreshRequest, RegisterRequest, TokenPair, UserRead
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services import (
    AlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(user_id: int) -> TokenPair:
    settings = get_settings()
    return TokenPair(
        access_token=create_access_token(str(user_id)),
        refresh_token=create_refresh_token(str(user_id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: SessionDep) -> UserRead:
    """Create a new account."""
    try:
        user = await register_user(session, payload)
    except AlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> TokenPair:
    """Exchange email + password for a token pair (OAuth2 password flow)."""
    try:
        user = await authenticate_user(session, form.username, form.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return _token_pair(user.id)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest) -> TokenPair:
    """Exchange a valid refresh token for a fresh token pair."""
    try:
        subject = decode_token(payload.refresh_token, expected_type="refresh")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired refresh token",
        ) from exc
    return _token_pair(int(subject))


@router.get("/me", response_model=UserRead)
async def whoami(current_user: CurrentUser) -> UserRead:
    """Return the authenticated user (sanity endpoint for clients)."""
    return UserRead.model_validate(current_user)
