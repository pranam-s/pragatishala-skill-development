"""Business services bridging routers, the database, and the AI engine."""

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import RULE_BASED, SkillEngine
from app.config import get_settings
from app.deps import get_user_by_email
from app.events import EventBus
from app.models import Assessment, LearningPath, MarketReport, Resume, User
from app.schemas import (
    AssessmentCreate,
    AssessmentResult,
    LearningPathContent,
    LearningPathCreate,
    MarketInsights,
    PlatformEvent,
    RegisterRequest,
    ResumeContent,
    ResumeGenerateRequest,
    UserUpdate,
)
from app.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class AlreadyRegisteredError(Exception):
    """Raised when registering an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match."""


class NotFoundError(Exception):
    """Raised when a requested resource does not exist or is not owned."""


# ---------------------------------------------------------------------------
# Auth & users
# ---------------------------------------------------------------------------


async def register_user(session: AsyncSession, payload: RegisterRequest) -> User:
    """Create a new user; raises :class:`AlreadyRegisteredError` on duplicates."""
    email = payload.email.lower()
    if await get_user_by_email(session, email) is not None:
        msg = f"an account with {email} already exists"
        raise AlreadyRegisteredError(msg)

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        target_role=payload.target_role,
        experience_level=payload.experience_level,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    """Verify credentials; raises :class:`InvalidCredentialsError` on failure."""
    user = await get_user_by_email(session, email)
    if user is None:
        # Burn comparable time to avoid leaking account existence via timing.
        verify_password(password, hash_password("dummy-password"))
        raise InvalidCredentialsError("incorrect email or password")
    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("incorrect email or password")
    return user


def apply_profile_update(user: User, payload: UserUpdate) -> User:
    """Apply non-null profile updates (caller commits)."""
    changes = payload.model_dump(exclude_unset=True)
    for field_name, value in changes.items():
        setattr(user, field_name, value)
    return user


# ---------------------------------------------------------------------------
# Assessments
# ---------------------------------------------------------------------------


async def run_assessment(
    session: AsyncSession,
    bus: EventBus,
    engine: SkillEngine,
    user: User,
    payload: AssessmentCreate,
) -> Assessment:
    """Analyze a user's skills narrative and persist the assessment."""
    target_role = payload.target_role or user.target_role
    outcome = await engine.analyze_skills(payload.input_text, target_role)
    result = outcome.value
    if not isinstance(result, AssessmentResult):  # pragma: no cover - defensive
        result = AssessmentResult.model_validate(result.model_dump())

    assessment = Assessment(
        user_id=user.id,
        input_text=payload.input_text,
        target_role=target_role,
        result=result.model_dump(),
        engine_used=outcome.engine_used,
    )
    session.add(assessment)
    await session.commit()
    await session.refresh(assessment)

    await bus.publish(
        user.id,
        PlatformEvent(
            type="assessment.completed",
            message=f"Skill assessment #{assessment.id} completed",
            payload={"assessment_id": assessment.id, "readiness_score": result.readiness_score},
        ).model_dump(),
    )
    return assessment


async def list_assessments(session: AsyncSession, user_id: int) -> list[Assessment]:
    """All assessments owned by *user_id*, newest first."""
    result = await session.execute(
        select(Assessment)
        .where(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc(), Assessment.id.desc())
    )
    return list(result.scalars().all())


async def get_assessment(session: AsyncSession, user_id: int, assessment_id: int) -> Assessment:
    """Fetch one owned assessment or raise :class:`NotFoundError`."""
    assessment = await session.get(Assessment, assessment_id)
    if assessment is None or assessment.user_id != user_id:
        raise NotFoundError("assessment not found")
    return assessment


# ---------------------------------------------------------------------------
# Learning paths
# ---------------------------------------------------------------------------


async def generate_learning_path(
    session: AsyncSession,
    bus: EventBus,
    engine: SkillEngine,
    user: User,
    payload: LearningPathCreate,
) -> LearningPath:
    """Generate a roadmap from an owned assessment (latest if omitted)."""
    if payload.assessment_id is not None:
        assessment = await get_assessment(session, user.id, payload.assessment_id)
    else:
        existing = await list_assessments(session, user.id)
        if not existing:
            msg = "run a skill assessment first or provide an assessment_id"
            raise NotFoundError(msg)
        assessment = existing[0]

    if assessment.result is None:  # pragma: no cover - legacy rows only
        msg = "assessment has no result to build a path from"
        raise NotFoundError(msg)
    assessment_result = AssessmentResult.model_validate(assessment.result)
    target_role = payload.target_role or assessment.target_role

    outcome = await engine.build_learning_path(assessment_result, target_role)
    generated = outcome.value
    if not isinstance(generated, LearningPathContent):  # pragma: no cover - defensive
        generated = LearningPathContent.model_validate(generated.model_dump())
    path = LearningPath(
        user_id=user.id,
        assessment_id=assessment.id,
        target_role=target_role,
        content=generated.model_dump(),
        engine_used=outcome.engine_used,
    )
    session.add(path)
    await session.commit()
    await session.refresh(path)

    await bus.publish(
        user.id,
        PlatformEvent(
            type="learning_path.completed",
            message=f"Learning path #{path.id} generated",
            payload={
                "learning_path_id": path.id,
                "modules": len(generated.modules),
            },
        ).model_dump(),
    )
    return path


async def list_learning_paths(session: AsyncSession, user_id: int) -> list[LearningPath]:
    """All learning paths owned by *user_id*, newest first."""
    result = await session.execute(
        select(LearningPath)
        .where(LearningPath.user_id == user_id)
        .order_by(LearningPath.created_at.desc(), LearningPath.id.desc())
    )
    return list(result.scalars().all())


async def get_learning_path(session: AsyncSession, user_id: int, path_id: int) -> LearningPath:
    """Fetch one owned learning path or raise :class:`NotFoundError`."""
    path = await session.get(LearningPath, path_id)
    if path is None or path.user_id != user_id:
        raise NotFoundError("learning path not found")
    return path


# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------


async def generate_resume(
    session: AsyncSession,
    bus: EventBus,
    engine: SkillEngine,
    user: User,
    payload: ResumeGenerateRequest,
) -> Resume:
    """Draft a structured resume and persist it."""
    outcome = await engine.generate_resume(
        full_name=user.full_name,
        target_role=payload.target_role,
        skills=payload.skills,
        experience_text=payload.experience_text,
        education_text=payload.education_text,
        projects_text=payload.projects_text,
    )
    resume = Resume(
        user_id=user.id,
        title=payload.title.strip() or "My resume",
        target_role=payload.target_role,
        content=outcome.value.model_dump(),
        engine_used=outcome.engine_used,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)

    await bus.publish(
        user.id,
        PlatformEvent(
            type="resume.completed",
            message=f"Resume #{resume.id} drafted",
            payload={"resume_id": resume.id},
        ).model_dump(),
    )
    return resume


async def list_resumes(session: AsyncSession, user_id: int) -> list[Resume]:
    """All resumes owned by *user_id*, newest first."""
    result = await session.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc(), Resume.id.desc())
    )
    return list(result.scalars().all())


async def get_resume(session: AsyncSession, user_id: int, resume_id: int) -> Resume:
    """Fetch one owned resume or raise :class:`NotFoundError`."""
    resume = await session.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        raise NotFoundError("resume not found")
    return resume


async def update_resume(
    session: AsyncSession,
    user: User,
    resume_id: int,
    title: str | None,
    content: ResumeContent | None,
) -> Resume:
    """Apply partial updates to an owned resume."""
    resume = await get_resume(session, user.id, resume_id)
    if title is not None:
        resume.title = title.strip() or resume.title
    if content is not None:
        resume.content = content.model_dump()
    await session.commit()
    await session.refresh(resume)
    return resume


# ---------------------------------------------------------------------------
# Market analysis
# ---------------------------------------------------------------------------


def _normalize_role(role: str) -> str:
    return " ".join(role.lower().split())


async def get_market_insights(
    session: AsyncSession, engine: SkillEngine, role: str, refresh: bool = False
) -> tuple[MarketInsights, str, datetime, bool, str | None]:
    """Return insights for *role*, using the cache when fresh.

    Returns ``(insights, engine_used, refreshed_at, was_cached, model_used)``.
    ``refresh`` bypasses the TTL so a bad cached report can be invalidated
    without direct database access.
    """
    role_key = _normalize_role(role)
    now = datetime.now(UTC)

    report = (
        await session.execute(select(MarketReport).where(MarketReport.role == role_key))
    ).scalar_one_or_none()

    settings = get_settings()
    if report is not None and not refresh:
        age_minutes = (now - _aware(report.refreshed_at)).total_seconds() / 60
        if age_minutes <= settings.market_cache_minutes:
            insights = MarketInsights.model_validate(report.content)
            return (
                insights,
                report.engine_used,
                _aware(report.refreshed_at),
                True,
                report.model_used,
            )

    outcome = await engine.market_insights(role_key)
    value = outcome.value
    insights = (
        value
        if isinstance(value, MarketInsights)
        else MarketInsights.model_validate(value.model_dump())
    )

    if report is None:
        report = MarketReport(role=role_key, content=insights.model_dump())
        session.add(report)
    else:
        report.content = insights.model_dump()
        report.refreshed_at = now
    report.engine_used = outcome.engine_used
    report.model_used = outcome.model
    try:
        await session.commit()
    except IntegrityError:
        # Cold-start race: a concurrent request inserted the same role first.
        # The winner's row is a valid fresh report - serve it instead of 500.
        await session.rollback()
        winner = (
            await session.execute(select(MarketReport).where(MarketReport.role == role_key))
        ).scalar_one()
        return (
            MarketInsights.model_validate(winner.content),
            winner.engine_used,
            _aware(winner.refreshed_at),
            True,
            winner.model_used,
        )
    await session.refresh(report)
    return insights, outcome.engine_used, _aware(report.refreshed_at), False, outcome.model


def _aware(value: datetime) -> datetime:
    """SQLite may return naive datetimes; normalize to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


__all__ = [
    "RULE_BASED",
    "AlreadyRegisteredError",
    "InvalidCredentialsError",
    "NotFoundError",
    "apply_profile_update",
    "authenticate_user",
    "generate_learning_path",
    "generate_resume",
    "get_assessment",
    "get_learning_path",
    "get_market_insights",
    "get_resume",
    "list_assessments",
    "list_learning_paths",
    "list_resumes",
    "register_user",
    "run_assessment",
    "update_resume",
]
