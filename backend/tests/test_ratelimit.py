"""Tests for the in-process rate limiting middleware (AR-023)."""

import pytest
from app.config import Settings, get_settings
from app.ratelimit import (
    AUTH_BUCKET,
    GENERATION_BUCKET,
    SlidingWindowLimiter,
    bucket_for,
)
from pydantic import ValidationError

from tests.conftest import login_headers

NARRATIVE = "I have 5 years of experience with Python and SQL."
SECRET = "Qk7wR2tY9uP5mJ3nV8cX4bZ6dF8gH2sL"


class _FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_limiter_allows_within_limit_then_blocks() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    for _ in range(3):
        allowed, retry_after = limiter.check("key", 3)
        assert allowed
        assert retry_after == 0
    allowed, retry_after = limiter.check("key", 3)
    assert not allowed
    assert retry_after == 60


def test_limiter_frees_up_after_window() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    assert limiter.check("key", 1)[0]
    clock.now += 61
    assert limiter.check("key", 1)[0]


def test_limiter_keys_are_isolated() -> None:
    limiter = SlidingWindowLimiter()
    assert limiter.check("client-a", 1)[0]
    assert limiter.check("client-b", 1)[0]
    assert not limiter.check("client-a", 1)[0]
    limiter.reset()
    assert limiter.check("client-a", 1)[0]


def test_limiter_sweeps_fully_expired_keys() -> None:
    clock = _FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    limiter.check("flood-1", 5)
    limiter.check("flood-2", 5)
    clock.now += 120.0  # every flood bucket is now entirely past the window
    # A generous limit keeps the steady checks allowed (rejected checks return
    # before the sweep counter) so the periodic sweep actually fires.
    for _ in range(SlidingWindowLimiter._SWEEP_EVERY):
        limiter.check("steady", 10**6)
    assert set(limiter._hits) == {"steady"}


def test_bucket_for_matches_exact_routes() -> None:
    assert bucket_for("POST", "/api/v1/auth/login") == AUTH_BUCKET
    assert bucket_for("POST", "/api/v1/auth/register") == AUTH_BUCKET
    assert bucket_for("POST", "/api/v1/auth/refresh") == AUTH_BUCKET
    assert bucket_for("POST", "/api/v1/assessments") == GENERATION_BUCKET
    assert bucket_for("POST", "/api/v1/learning-paths/generate") == GENERATION_BUCKET
    assert bucket_for("POST", "/api/v1/resumes/generate") == GENERATION_BUCKET
    assert bucket_for("GET", "/api/v1/market/insights") == GENERATION_BUCKET
    # Cheap read paths and unknown routes stay unthrottled.
    assert bucket_for("GET", "/api/v1/assessments") is None
    assert bucket_for("GET", "/api/v1/auth/me") is None
    assert bucket_for("GET", "/healthz") is None
    assert bucket_for("POST", "/api/v1/auth/login/extra") is None


async def test_auth_bucket_returns_429_with_retry_after(client, monkeypatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_AUTH_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()
    for index in range(2):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": f"ratelimit{index}@example.com", "password": "super-secret-pass-123"},
        )
        assert response.status_code == 201
    blocked = await client.post(
        "/api/v1/auth/register",
        json={"email": "ratelimit3@example.com", "password": "super-secret-pass-123"},
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert blocked.json()["detail"] == "Too many requests"


async def test_generation_bucket_returns_429(client, monkeypatch) -> None:
    headers = await login_headers(client)
    monkeypatch.setenv("PRAGATISHALA_GENERATION_RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    first = await client.post(
        "/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE}
    )
    assert first.status_code == 201
    blocked = await client.post(
        "/api/v1/assessments", headers=headers, json={"input_text": NARRATIVE}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_zero_limit_disables_a_bucket(client, monkeypatch) -> None:
    monkeypatch.setenv("PRAGATISHALA_AUTH_RATE_LIMIT_PER_MINUTE", "0")
    get_settings.cache_clear()
    for index in range(3):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": f"unlimited{index}@example.com", "password": "super-secret-pass-123"},
        )
        assert response.status_code == 201


async def test_unthrottled_routes_ignore_limits(client) -> None:
    for _ in range(12):
        assert (await client.get("/healthz")).status_code == 200


@pytest.mark.parametrize(
    "limit_setting",
    ["auth_rate_limit_per_minute", "generation_rate_limit_per_minute"],
)
def test_negative_rate_limit_rejected(limit_setting: str) -> None:
    with pytest.raises(ValidationError, match="rate limits must be zero or positive"):
        Settings(jwt_secret_key=SECRET, **{limit_setting: -1})
