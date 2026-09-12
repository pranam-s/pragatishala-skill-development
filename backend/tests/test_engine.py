"""Tests for the rule-based skill engine and its AI fallback contract."""

import pytest
from app.ai.engine import RULE_BASED, SkillEngine, _bullets_from, _rule_based_assessment
from app.ai.provider import AIError
from app.schemas import AssessmentResult, LearningPathContent, MarketInsights, ResumeContent

NARRATIVE = (
    "I have 5 years of experience with Python and I am proficient in SQL. "
    "I know a bit of Docker and I am learning Kubernetes for deployments."
)


def test_assessment_detects_skills_and_levels() -> None:
    result = _rule_based_assessment(NARRATIVE, "Backend Developer")
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "expert"  # 5 years
    assert by_name["SQL"].level == "advanced"  # proficient
    assert by_name["Docker"].level == "beginner"  # single mention
    assert by_name["Kubernetes"].level == "beginner"  # learning
    assert result.readiness_score <= 100
    assert result.summary


def test_assessment_no_target_role() -> None:
    result = _rule_based_assessment(NARRATIVE, None)
    assert "exploring directions" in result.summary


def test_assessment_repeated_mentions_raise_level() -> None:
    text = "I use Python. Python is great. I code Python every day."
    result = _rule_based_assessment(text, None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "advanced"  # 3 mentions
    assert "3x" in by_name["Python"].evidence


def test_assessment_unknown_role_still_scores() -> None:
    result = _rule_based_assessment("I know Python and Excel.", "Xenoastronomy Consultant")
    assert result.skills
    assert 0 <= result.readiness_score <= 100


def test_recommended_skills_raise_readiness_monotonically() -> None:
    # Data Analyst: required = SQL/Excel/Data Analysis/Data Viz/Statistics,
    # recommended = Python/Pandas/Communication.
    base = _rule_based_assessment("I know SQL, Excel, and Data Analysis.", "Data Analyst")
    assert base.readiness_score == 60  # 3 of 5 required skills, no recommended
    enriched = _rule_based_assessment(
        "I know SQL, Excel, and Data Analysis. I use Python and Pandas daily.", "Data Analyst"
    )
    assert enriched.readiness_score == base.readiness_score + 10  # +5 per recommended, capped at 2
    assert enriched.readiness_score == 70
    assert set(enriched.gaps) == {"Data Visualization", "Statistics", "Communication"}


def test_assessment_empty_text_is_safe() -> None:
    result = _rule_based_assessment("Nothing here matches any known skill taxonomy entry.", None)
    assert isinstance(result, AssessmentResult)


def test_bullets_from_polishes_weak_verbs() -> None:
    polished = _bullets_from("- worked on tickets\ndid reports\nShipped the feature")
    assert "- Drove on tickets" in polished
    assert "- Drove reports" in polished
    assert "- Shipped the feature." in polished


def test_bullets_from_empty_text() -> None:
    assert _bullets_from("") == "- Delivered assigned outcomes."


class _StubProvider:
    """Provider double returning a canned result."""

    name = "stub-llm"
    model = "stub-1"

    def __init__(self, response: object | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def complete_json(self, system: str, user: str, schema: type) -> object:
        del system, user, schema
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


class _WrongShapeProvider(_StubProvider):
    async def complete_json(self, system: str, user: str, schema: type) -> object:
        del system, user
        return object()  # not an instance of any expected schema


@pytest.fixture
def ai_result() -> AssessmentResult:
    return AssessmentResult(
        summary="AI summary",
        skills=[],
        strengths=["Python"],
        gaps=["SQL"],
        recommended_roles=["Backend Developer"],
        readiness_score=55,
    )


async def test_engine_uses_provider_result(ai_result: AssessmentResult) -> None:
    engine = SkillEngine(_StubProvider(ai_result))  # type: ignore[arg-type]
    outcome = await engine.analyze_skills(NARRATIVE, None)
    assert outcome.value.summary == "AI summary"
    assert outcome.engine_used == "stub-llm"


async def test_engine_falls_back_on_provider_error(ai_result: AssessmentResult) -> None:
    engine = SkillEngine(_StubProvider(error=AIError("boom")))  # type: ignore[arg-type]
    outcome = await engine.analyze_skills(NARRATIVE, None)
    assert outcome.engine_used == RULE_BASED
    assert outcome.value.skills  # deterministic fallback produced content


async def test_engine_falls_back_on_wrong_shape() -> None:
    engine = SkillEngine(_WrongShapeProvider())  # type: ignore[arg-type]
    outcome = await engine.analyze_skills(NARRATIVE, None)
    assert outcome.engine_used == RULE_BASED


async def test_engine_without_provider_is_offline() -> None:
    engine = SkillEngine(None)
    assert engine.provider_name == RULE_BASED
    outcome = await engine.analyze_skills(NARRATIVE, None)
    assert outcome.engine_used == RULE_BASED


async def test_engine_learning_path_via_provider() -> None:
    result = _rule_based_assessment(NARRATIVE, "Backend Developer")
    ai_content = LearningPathContent(
        headline="AI path",
        target_role="Backend Developer",
        total_estimated_hours=10,
        modules=[
            {
                "title": "SQL",
                "description": "Learn SQL",
                "skills_covered": ["SQL"],
                "estimated_hours": 10,
                "resources": [],
                "milestone": "Query like a pro",
            }
        ],
        next_steps=["Practice"],
    )
    engine = SkillEngine(_StubProvider(ai_content))  # type: ignore[arg-type]
    outcome = await engine.build_learning_path(result, "Backend Developer")
    assert outcome.value.headline == "AI path"


async def test_engine_resume_via_provider() -> None:
    ai_content = ResumeContent(
        headline="AI resume",
        professional_summary="Great engineer.",
        skills=["Python"],
        experience=[],
        education=[],
        projects=[],
    )
    engine = SkillEngine(_StubProvider(ai_content))  # type: ignore[arg-type]
    outcome = await engine.generate_resume("Asha", "Backend Developer", [], "", "", "")
    assert outcome.value.headline == "AI resume"


async def test_engine_market_via_provider() -> None:
    ai_content = MarketInsights(
        role="Backend Developer",
        demand_level="high",
        median_salary_range_inr="₹6-30 LPA",
        growth_outlook="Strong",
        top_skills=["Python"],
        trending_skills=["FastAPI"],
        typical_employers=["IT services"],
        recommended_certifications=["AWS DVA"],
        advice=["Build projects"],
    )
    engine = SkillEngine(_StubProvider(ai_content))  # type: ignore[arg-type]
    outcome = await engine.market_insights("Backend Developer")
    assert outcome.value.median_salary_range_inr == "₹6-30 LPA"


async def test_rule_based_learning_path_cap_and_order() -> None:
    result = _rule_based_assessment(NARRATIVE, "Backend Developer")
    engine = SkillEngine(None)
    outcome = await engine.build_learning_path(result, "Backend Developer")
    content = outcome.value
    assert isinstance(content, LearningPathContent)
    assert 1 <= len(content.modules) <= 8
    assert content.total_estimated_hours == sum(
        module.estimated_hours for module in content.modules
    )


async def test_rule_based_learning_path_empty_result() -> None:
    empty = AssessmentResult(
        summary="", skills=[], strengths=[], gaps=[], recommended_roles=[], readiness_score=0
    )
    engine = SkillEngine(None)
    outcome = await engine.build_learning_path(empty, None)
    assert outcome.value.modules  # default modules applied


async def test_rule_based_resume_fresh_graduate() -> None:
    engine = SkillEngine(None)
    outcome = await engine.generate_resume("", "Backend Developer", [], "", "", "")
    content = outcome.value
    assert isinstance(content, ResumeContent)
    assert "Your Name" in content.headline
    assert content.skills  # falls back to role requirements


async def test_rule_based_market_known_and_unknown_role() -> None:
    engine = SkillEngine(None)
    known = await engine.market_insights("Data Analyst")
    assert isinstance(known.value, MarketInsights)
    unknown = await engine.market_insights("Chief Memelord")
    assert unknown.value.role == "Technology Professional"  # fallback profile


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I have 6 years of experience with Docker.", "expert"),
        ("I have 4 years of experience with Docker.", "advanced"),
        ("I have 1 year of experience with Docker.", "intermediate"),
        ("I have 0 years of experience with Docker.", "beginner"),
        ("I have 6 months of exposure with Docker.", "beginner"),
    ],
)
def test_assessment_experience_quantifies_level(phrase: str, expected: str) -> None:
    result = _rule_based_assessment(phrase, None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Docker"].level == expected


def test_multi_alias_skill_keeps_best_level_and_winning_evidence() -> None:
    text = "I do advanced Python3. My py scripts are everywhere."
    result = _rule_based_assessment(text, None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "advanced"
    assert "1x" in by_name["Python"].evidence  # winning alias: python3


# --- AR-029: proficiency evidence must not cross clause/sentence boundaries ---


def test_level_word_does_not_leak_across_sentences() -> None:
    result = _rule_based_assessment("I do advanced Python. Also SQL.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "advanced"
    assert by_name["SQL"].level == "beginner"


def test_years_do_not_leak_across_clauses() -> None:
    result = _rule_based_assessment("After 4 years of SQL, I touched Python yesterday.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["SQL"].level == "advanced"
    assert by_name["Python"].level == "beginner"


def test_level_between_skills_binds_to_the_left_mention() -> None:
    result = _rule_based_assessment("I know Python well beyond advanced. SQL too.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "advanced"
    assert by_name["SQL"].level == "beginner"


# --- AR-030: ambiguous aliases must not invent skills from everyday phrases ---


@pytest.mark.parametrize(
    "phrase",
    [
        "We are ready to go home.",
        "I also fix LED lights on weekends.",
        "My teacher gave me grade A B C.",
        "Let the traffic light go green.",
        "The display has LED backlight.",
        "Vitamin C is important.",
    ],
)
def test_everyday_phrases_do_not_invent_skills(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    names = {skill.name for skill in result.skills}
    assert not names & {"Go", "Leadership", "C"}


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I know Go and use it daily.", {"Go"}),
        ("I led a team of engineers.", {"Leadership"}),
        ("C programming was my first language.", {"C"}),
        ("I write embedded code in C language.", {"C"}),
    ],
)
def test_ambiguous_skills_detected_with_skill_context(phrase: str, expected: set[str]) -> None:
    result = _rule_based_assessment(phrase, None)
    names = {skill.name for skill in result.skills}
    assert expected <= names


# --- AR2-001: context words must not match as prefixes of unrelated words ---


@pytest.mark.parametrize(
    "phrase",
    [
        "The knowledge base article led to a fix.",
        "They stacked the boxes while I watched the LED display.",
        "He catalogued every toolset before the LED panel arrived.",
    ],
)
def test_embedded_context_words_do_not_invent_skills(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


# --- AR2-003: the ambiguity gate is alias-proximate, not sentence-global ---


@pytest.mark.parametrize(
    "phrase",
    [
        "At the coding bootcamp I was ready to go.",
        "I studied programming at a bootcamp before I had to go home.",
    ],
)
def test_distant_context_words_do_not_gate_ambiguous_alias(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("Built a payments service using Go.", {"Go"}),
        ("I led a team of five.", {"Leadership"}),
        ("Leading a Go team at a startup.", {"Go"}),
        ("I know Go and use it daily.", {"Go"}),
        ("I led a team of engineers.", {"Leadership"}),
    ],
)
def test_proximate_claims_still_flag_ambiguous_aliases(phrase: str, expected: set[str]) -> None:
    result = _rule_based_assessment(phrase, None)
    names = {skill.name for skill in result.skills}
    assert expected <= names


# --- AR2-002: remaining homograph aliases must be gated like c/go/led ---


@pytest.mark.parametrize(
    "phrase",
    [
        "Each node in the graph holds a value.",
        "I listen to Taylor Swift on repeat.",
        "Our .net profit doubled this year.",
        "My CV is attached for your review.",
        "In calculus, a lambda defines an anonymous function.",
    ],
)
def test_homograph_aliases_do_not_invent_skills(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I build REST APIs with Node and Express at work.", {"Node.js", "REST APIs"}),
        ("I ship mobile apps using Swift every day.", {"iOS Development"}),
        ("I maintain .NET services at a fintech.", {"C#"}),
        ("I use CV techniques in my vision startup.", {"Computer Vision"}),
        ("I deploy AWS Lambda functions in production.", {"AWS"}),
    ],
)
def test_homograph_claims_still_land(phrase: str, expected: set[str]) -> None:
    result = _rule_based_assessment(phrase, None)
    names = {skill.name for skill in result.skills}
    assert expected <= names


# --- AR2-004: abbreviation dots must not split skill sentences ---


@pytest.mark.parametrize(
    "phrase",
    [
        "Expert in web technologies, e.g. Python and SQL.",
        "Expert in backend languages, i.e. Python and SQL.",
    ],
)
def test_abbreviation_dots_keep_level_words_in_scope(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    by_name = {skill.name: skill for skill in result.skills}
    # The level word stays in the sentence; AR-029 clause binding ties it to
    # the nearest mention (Python) instead of losing it to a bogus split.
    assert by_name["Python"].level == "expert"
    assert by_name["SQL"].level == "beginner"


# --- AR2-006: experience figures must not leak across domains in a clause ---


def test_years_in_another_domain_do_not_bind() -> None:
    result = _rule_based_assessment(
        "I spent 3 years in support, then moved to Python development.", None
    )
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "beginner"


def test_years_following_the_mention_still_bind() -> None:
    result = _rule_based_assessment("Python developer with 3 years of craft.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "advanced"
