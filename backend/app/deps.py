"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import SkillEngine
from app.database import get_session
from app.events import EventBus, get_event_bus
from app.models import User
from app.security import TokenError, decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
BusDep = Annotated[EventBus, Depends(get_event_bus)]


def get_skill_engine(request: Request) -> SkillEngine:
    """Return the engine configured at startup (AI provider or offline)."""
    engine: SkillEngine = request.app.state.skill_engine
    return engine


EngineDep = Annotated[SkillEngine, Depends(get_skill_engine)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    """Resolve the authenticated user from a bearer access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        subject = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise credentials_exception from exc

    user_id = user_id_from_subject(subject)
    if user_id is None:
        raise credentials_exception

    user = await session.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def user_id_from_subject(subject: str) -> int | None:
    """Parse a JWT subject into a user id, or None when malformed.

    ASCII digits only: ``str.isdigit`` also accepts characters like "²" that
    ``int()`` rejects, which would turn this defensive path into a 500.
    """
    return int(subject) if subject.isascii() and subject.isdigit() else None


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Fetch a user by lowercased email, or None."""
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()
