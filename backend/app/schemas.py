"""Pydantic API schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=200)
    target_role: str | None = Field(default=None, max_length=120)
    experience_level: Literal["fresher", "student", "junior", "mid", "senior"] | None = None


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    target_role: str | None
    experience_level: str | None
    created_at: datetime


class TokenPair(BaseModel):
    """Access + refresh token response."""

    token_type: Literal["bearer"] = "bearer"  # noqa: S105  (token *type*, not a secret)
    access_token: str
    refresh_token: str
    expires_in: int


class RefreshRequest(BaseModel):
    """Payload for the refresh endpoint."""

    refresh_token: str


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------


class UserUpdate(BaseModel):
    """Editable profile fields."""

    full_name: str | None = Field(default=None, max_length=200)
    target_role: str | None = Field(default=None, max_length=120)
    experience_level: Literal["fresher", "student", "junior", "mid", "senior"] | None = None


# --------------------------------------------------------------------------
# Assessments
# --------------------------------------------------------------------------


class SkillScore(BaseModel):
    """A single detected skill with an estimated proficiency."""

    name: str
    category: str
    level: Literal["beginner", "intermediate", "advanced", "expert"]
    evidence: str = ""


class AssessmentResult(BaseModel):
    """Structured outcome of a skill assessment."""

    summary: str
    skills: list[SkillScore]
    strengths: list[str]
    gaps: list[str]
    recommended_roles: list[str]
    readiness_score: int = Field(ge=0, le=100)


class AssessmentCreate(BaseModel):
    """Payload to run a skill assessment."""

    input_text: str = Field(min_length=20, max_length=8000)
    target_role: str | None = Field(default=None, max_length=120)


class AssessmentRead(BaseModel):
    """Assessment as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    target_role: str | None
    result: AssessmentResult | None
    engine_used: str
    created_at: datetime


# --------------------------------------------------------------------------
# Learning paths
# --------------------------------------------------------------------------


class LearningModule(BaseModel):
    """One step of a learning path."""

    title: str
    description: str
    skills_covered: list[str]
    estimated_hours: int = Field(ge=1, le=500)
    resources: list[str] = []
    milestone: str


class LearningPathContent(BaseModel):
    """Full generated learning path."""

    headline: str
    target_role: str | None
    total_estimated_hours: int
    modules: list[LearningModule]
    next_steps: list[str]


class LearningPathCreate(BaseModel):
    """Payload to generate a learning path."""

    assessment_id: int | None = None
    target_role: str | None = Field(default=None, max_length=120)


class LearningPathRead(BaseModel):
    """Learning path as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int | None
    target_role: str | None
    content: LearningPathContent | None
    engine_used: str
    created_at: datetime


# --------------------------------------------------------------------------
# Resumes
# --------------------------------------------------------------------------


class ResumeContent(BaseModel):
    """Structured resume document."""

    headline: str
    professional_summary: str
    skills: list[str]
    experience: list[dict[str, str]]
    education: list[dict[str, str]]
    projects: list[dict[str, str]] = []


class ResumeGenerateRequest(BaseModel):
    """Payload to draft a resume with AI assistance."""

    title: str = Field(default="My resume", max_length=200)
    target_role: str = Field(max_length=120)
    skills: list[str] = Field(default_factory=list, max_length=30)
    experience_text: str = Field(default="", max_length=8000)
    education_text: str = Field(default="", max_length=2000)
    projects_text: str = Field(default="", max_length=4000)


class ResumeUpdate(BaseModel):
    """Editable resume fields."""

    title: str | None = Field(default=None, max_length=200)
    content: ResumeContent | None = None


class ResumeRead(BaseModel):
    """Resume as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target_role: str | None
    content: ResumeContent | None
    engine_used: str
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------
# Market analysis
# --------------------------------------------------------------------------


class MarketInsights(BaseModel):
    """Structured market analysis for a role."""

    role: str
    demand_level: Literal["low", "moderate", "high", "very high"]
    median_salary_range_inr: str
    growth_outlook: str
    top_skills: list[str]
    trending_skills: list[str]
    typical_employers: list[str]
    recommended_certifications: list[str]
    advice: list[str]


class MarketInsightsRead(BaseModel):
    """Market analysis response including cache metadata."""

    role: str
    insights: MarketInsights
    engine_used: str
    refreshed_at: datetime
    cached: bool


# --------------------------------------------------------------------------
# Events (SSE)
# --------------------------------------------------------------------------


class PlatformEvent(BaseModel):
    """A real-time event pushed to the owning user over SSE."""

    type: str
    message: str
    payload: dict[str, Any] = {}
