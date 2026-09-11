"""Property-based tests (hypothesis) for core backend invariants.

Covers the invariants named in the adversarial review (AR-031): JWT round-
trips, readiness-score bounds, rule-engine determinism, role normalisation,
fenced-JSON tolerance, and the AR-029 scope-isolation property that level and
years evidence attach only to skills mentioned in the same sentence.
"""

import json

from app.ai.engine import _LEVEL_WORDS, _level_rank, _rule_based_assessment
from app.ai.provider import AIError, _extract_json_object
from app.security import TokenError, create_access_token, create_refresh_token, decode_token
from app.services import _normalize_role
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

VALID_LEVELS = {"beginner", "intermediate", "advanced", "expert"}
_LEVEL_BY_WORD = dict(_LEVEL_WORDS)


# --- JWT round-trips -----------------------------------------------------------


@given(subject=st.text(min_size=1, max_size=64))
@settings(max_examples=50)
def test_token_round_trip_preserves_subject(subject: str) -> None:
    assert decode_token(create_access_token(subject), expected_type="access") == subject
    assert decode_token(create_refresh_token(subject), expected_type="refresh") == subject


@given(subject=st.text(min_size=1, max_size=64))
@settings(max_examples=25)
def test_token_type_confusion_always_rejected(subject: str) -> None:
    refresh = create_refresh_token(subject)
    try:
        decode_token(refresh, expected_type="access")
    except TokenError:
        pass
    else:
        raise AssertionError("refresh token accepted as access token")
    # ...and the access token remains usable for its own type.
    assert decode_token(create_access_token(subject), expected_type="access") == subject


# --- Rule-based engine ---------------------------------------------------------


@given(
    text=st.text(max_size=1200),
    role=st.one_of(st.none(), st.text(max_size=80)),
)
@settings(max_examples=100)
def test_assessment_invariants_hold_for_arbitrary_text(text: str, role: str | None) -> None:
    result = _rule_based_assessment(text, role)
    assert 0 <= result.readiness_score <= 100
    assert all(skill.level in VALID_LEVELS for skill in result.skills)
    ranks = [_level_rank(skill.level) for skill in result.skills]
    assert ranks == sorted(ranks, reverse=True)  # skills sorted best-first


@given(
    text=st.text(max_size=600),
    role=st.one_of(st.none(), st.text(max_size=80)),
)
@settings(max_examples=50)
def test_assessment_is_deterministic(text: str, role: str | None) -> None:
    first = _rule_based_assessment(text, role)
    second = _rule_based_assessment(text, role)
    assert first.model_dump() == second.model_dump()


# --- AR-029 scope isolation: evidence never crosses sentences ------------------

_SKILL_POOL = ["Python", "SQL", "Docker", "React", "Rust", "Django"]
_LEVEL_WORD_POOL = sorted({word for word, _level in _LEVEL_WORDS})
# Canaries: proficiency evidence with NO skill mention. A segmentation bug
# (like the old 30-char window) lets them leak into neighbouring sentences.
_CANARY_TEMPLATES = [
    "After 2 years I finally felt {word}.",
    "Honestly {word} is how it all felt.",
]
_PLAIN_FILLER = "The team shipped the project on time."


def _years_level(years: int) -> str:
    if years >= 5:
        return "expert"
    if years >= 3:
        return "advanced"
    if years >= 1:
        return "intermediate"
    return "beginner"


def _count_level(count: int) -> str:
    if count >= 3:
        return "advanced"
    if count == 2:
        return "intermediate"
    return "beginner"


@st.composite
def _narratives(draw: DrawFn) -> tuple[str, dict[str, str]]:
    chosen = sorted(draw(st.sets(st.sampled_from(_SKILL_POOL), min_size=1, max_size=3)))
    sentences: list[str] = []
    expected: dict[str, str] = {}
    for skill in chosen:
        kind = draw(st.sampled_from(["level", "years", "plain1", "plain2", "plain3"]))
        if kind == "level":
            word = draw(st.sampled_from(_LEVEL_WORD_POOL))
            sentences.append(f"I do {word} {skill}.")
            expected[skill] = _LEVEL_BY_WORD[word]
        elif kind == "years":
            years = draw(st.integers(min_value=1, max_value=9))
            sentences.append(f"{skill} for {years} years.")
            expected[skill] = _years_level(years)
        else:
            count = int(kind[-1])
            sentences.extend([f"I use {skill}."] * count)
            expected[skill] = _count_level(count)
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        template = draw(st.sampled_from(_CANARY_TEMPLATES))
        word = draw(st.sampled_from(_LEVEL_WORD_POOL))
        sentences.append(template.format(word=word))
    sentences.append(_PLAIN_FILLER)
    return " ".join(draw(st.permutations(sentences))), expected


@given(narrative=_narratives())
@settings(max_examples=100)
def test_level_and_years_evidence_stay_in_their_own_sentence(
    narrative: tuple[str, dict[str, str]],
) -> None:
    text, expected = narrative
    result = _rule_based_assessment(text, None)
    detected = {skill.name: skill.level for skill in result.skills}
    # No invented skills: every detection traces to a generated mention.
    assert set(detected) == set(expected)
    # Every level equals what the skill's OWN sentences justify - a canary's
    # level word or years figure one sentence away must never inflate a skill.
    for skill, level in expected.items():
        assert detected[skill] == level, f"{skill}: expected {level}, got {detected[skill]}"


# --- Role normalisation ---------------------------------------------------------


@given(role=st.text(max_size=120))
@settings(max_examples=50)
def test_normalize_role_is_idempotent(role: str) -> None:
    once = _normalize_role(role)
    assert _normalize_role(once) == once


# --- Tolerant LLM-JSON extraction ------------------------------------------------

json_values = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(min_value=-(10**9), max_value=10**9)
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text(max_size=40),
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=4)
    ),
    max_leaves=12,
)


@given(payload=st.dictionaries(st.text(min_size=1, max_size=20), json_values, max_size=6))
@settings(max_examples=50)
def test_fenced_json_always_extracts(payload: dict[str, object]) -> None:
    raw = json.dumps(payload)
    for wrapped in (
        raw,
        f"```json\n{raw}\n```",
        f"Sure! Here is the answer:\n{raw}\nHope that helps.",
        f"```\n{raw}\n``` trailing prose",
    ):
        assert _extract_json_object(wrapped) == payload


@given(noise=st.text(max_size=200).filter(lambda s: "{" not in s and "}" not in s))
@settings(max_examples=25)
def test_json_extraction_without_object_raises(noise: str) -> None:
    try:
        _extract_json_object(noise)
    except AIError:
        pass
    else:
        raise AssertionError("extraction succeeded without a JSON object")
