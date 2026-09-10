"""SQLAlchemy ORM models."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class User(Base):
    """Registered platform user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experience_level: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    learning_paths: Mapped[list["LearningPath"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Assessment(Base):
    """A skill assessment run over free-form user input."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    engine_used: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_based")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="assessments")


class LearningPath(Base):
    """A generated, personalized learning roadmap."""

    __tablename__ = "learning_paths"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    assessment_id: Mapped[int | None] = mapped_column(ForeignKey("assessments.id"), nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    engine_used: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_based")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="learning_paths")


class Resume(Base):
    """An AI-drafted resume owned by a user."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="My resume")
    target_role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    content: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    engine_used: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_based")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    user: Mapped[User] = relationship(back_populates="resumes")


class MarketReport(Base):
    """Cached market analysis for a role."""

    __tablename__ = "market_reports"
    __table_args__ = (UniqueConstraint("role", name="uq_market_reports_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    engine_used: Mapped[str] = mapped_column(String(40), nullable=False, default="rule_based")
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
