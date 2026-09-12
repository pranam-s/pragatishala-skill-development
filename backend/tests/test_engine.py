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


# --- AR3-001: lowercase "led" is the dominant leadership claim; only the
# all-caps acronym "LED" stays gated. X01 is a true AR2 regression (round 1
# scored it Leadership=expert; the AR2-003 gate dropped Leadership entirely).
# L01-L04 were under-detected in round 1 too - the gate cemented that. L05-L06
# are the narrow phrasings the gate kept working; they must stay detected.


@pytest.mark.parametrize(
    ("repro_id", "phrase"),
    [
        ("X01", "I led the migration and I am an expert in Python."),
        ("L01", "I led multiple projects end to end."),
        ("L02", "I led the rollout of our CI pipeline and mentored interns."),
        ("L03", "I led the initiative at my company."),
        ("L04", "I led the migration of our platform to Kubernetes."),
        ("L05", "I led a team of five."),
        ("L06", "I led the development of the payments platform."),
    ],
)
def test_lowercase_led_is_a_leadership_claim(repro_id: str, phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    names = {skill.name for skill in result.skills}
    assert "Leadership" in names, repro_id


def test_led_migration_regression_scores_both_skills() -> None:
    result = _rule_based_assessment("I led the migration and I am an expert in Python.", None)
    by_name = {skill.name: skill for skill in result.skills}
    # Round-1 parity for the level: the scope mechanics hand the co-sentence
    # level word to both mentions (limitations #5); the regression was the
    # missing detection, which both assertions pin down.
    assert by_name["Leadership"].level == "expert"
    assert by_name["Python"].level == "expert"


@pytest.mark.parametrize(
    "phrase",
    [
        "I replaced the LED lights in the studio.",
        "The LED at the stadium flickered all night.",
        "The knowledge base article led to a fix.",  # causative "led to" (AR2-001)
        "Reading led me to believe otherwise.",  # causative "led me to"
    ],
)
def test_led_acronym_and_causative_stay_silent(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


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


# --- AR3-002: decimal years are one figure, not their fraction digits ---


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I have 3.5 years of Python experience.", "advanced"),
        ("0.5 years with Python so far.", "beginner"),
        ("1.5 yrs using Python at work.", "intermediate"),
    ],
)
def test_decimal_years_score_as_one_figure(phrase: str, expected: str) -> None:
    result = _rule_based_assessment(phrase, None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == expected


# --- AR3-005: discourse boundaries void years binding; the no-boundary
# token budget widens to six ---


def test_years_before_a_discourse_boundary_do_not_bind() -> None:
    result = _rule_based_assessment("3 years in support, then Python.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "beginner"  # support's tenure, not Python's


def test_long_gap_without_boundary_still_binds() -> None:
    result = _rule_based_assessment(
        "10 years designing and building data pipelines in Python.", None
    )
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "expert"


def test_trailing_figure_after_comma_still_binds() -> None:
    result = _rule_based_assessment("Python, 6 years.", None)
    by_name = {skill.name: skill for skill in result.skills}
    assert by_name["Python"].level == "expert"


# --- AR3-011: ASP.NET is invisible to the leading-dot lookbehind ---


def test_asp_dot_net_is_detected_as_csharp() -> None:
    result = _rule_based_assessment("I build enterprise apps with ASP.NET.", None)
    names = {skill.name for skill in result.skills}
    assert names == {"C#"}  # the .net alias cannot double-count inside asp.net


# --- AR3-008: bare prepositions before an alias are not usage evidence ---


@pytest.mark.parametrize(
    "phrase",
    [
        "I believe in Go.",
        "There's money in Go.",
        "I trust my gut in Go.",
    ],
)
def test_bare_preceder_prepositions_do_not_vouch(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


def test_weak_preceder_counts_with_a_nearby_skill_mention() -> None:
    result = _rule_based_assessment("I build REST APIs with Node and Express at work.", None)
    names = {skill.name for skill in result.skills}
    assert {"Node.js", "REST APIs"} <= names


# --- AR3-004: homograph fabrications that survived proximity gating ---


@pytest.mark.parametrize(
    "phrase",
    [
        "I'm the go-to person for databases.",
        "The swift development of the feature impressed everyone.",
        "Updated my CV with new skills.",
        "I wrote a lambda expression in my code.",
        "A node in the database cluster failed.",
        "Ready to go while coding daily.",
        "I like to go with databases for persistence.",
    ],
)
def test_remaining_homograph_fabrications_stay_silent(phrase: str) -> None:
    result = _rule_based_assessment(phrase, None)
    assert {skill.name for skill in result.skills} == set()


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("I have swift development experience.", {"iOS Development"}),
        ("I deploy Lambda functions behind an AWS gateway.", {"AWS"}),
    ],
)
def test_homograph_sense_checks_keep_genuine_claims(phrase: str, expected: set[str]) -> None:
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
    # The abbreviation dots no longer split the sentence (AR2-004), and the
    # level word is shared across the comma list (AR3-003): both skills read
    # as expert instead of only the first-listed one.
    assert by_name["Python"].level == "expert"
    assert by_name["SQL"].level == "expert"


# --- AR3-003: a clause's level word covers every sibling in its list ---


@pytest.mark.parametrize(
    ("phrase", "skill", "expected"),
    [
        ("Expert in Python, SQL, and Java.", "SQL", "expert"),
        ("Expert in Python, SQL, and Java.", "Java", "expert"),
        ("Advanced in SQL and Python.", "Python", "advanced"),
    ],
)
def test_list_siblings_share_the_level_word(phrase: str, skill: str, expected: str) -> None:
    result = _rule_based_assessment(phrase, None)
    by_name = {s.name: s for s in result.skills}
    assert by_name[skill].level == expected


@pytest.mark.parametrize(
    ("phrase", "skill"),
    [
        ("Advanced in SQL but Python just starting.", "Python"),
        ("Expert in SQL. I also know Python.", "Python"),
        ("Advanced in SQL, then Python came later.", "Python"),
    ],
)
def test_level_word_sharing_stops_at_attribution_boundaries(phrase: str, skill: str) -> None:
    result = _rule_based_assessment(phrase, None)
    by_name = {s.name: s for s in result.skills}
    assert by_name[skill].level == "beginner"


def test_level_word_sharing_stops_at_another_skills_years_figure() -> None:
    """A years figure re-anchors attribution; the level word may not cross it.

    'Expert' governs Python and the figure quantifies Go; Rust (a sibling of
    Go, not of Python) must stay at its mention-only level instead of
    inheriting Python's expert across Go's experience phrase.
    """
    result = _rule_based_assessment("Expert in Python, 5 years with Go and Rust.", None)
    by_name = {s.name: s for s in result.skills}
    assert by_name["Python"].level == "expert"
    assert by_name["Go"].level == "expert"  # its own 5-year figure
    assert by_name["Rust"].level == "beginner"  # mention only, not Python's expert


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
