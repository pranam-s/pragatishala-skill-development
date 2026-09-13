# PragatiShala - Project Tracker

This document tracks the progress of the PragatiShala project: owner
instructions, research notes, plans, and implementation status. It is updated
throughout development. Current-state detail lives in [README.md](README.md),
[docs/architecture.md](docs/architecture.md), and [BUILD_LOG.md](BUILD_LOG.md).

## User Instructions (standing)

*   Implement the GitHub repository, which has a `readme.md` with features and requirements.
*   Use for backend latest Python + FastAPI + complete async + UV + Ruff, and whatever you wish and find best for frontend.
*   Follow best practices.
*   Find best features and more things to add.
*   Take references from platforms like vedai.in and other similar products, but ensure that you do it the best manner.
*   Keep researching or refining features to be added or implemented in the platform accordingly.
*   Keep this document updated with instructions, findings, plans, and status.
*   Owner accessibility requirement (added 2026-09): the owner is a blind NVDA
    screen-reader user. Every UI must be keyboard-navigable, labelled, and
    screen-reader friendly; a11y regressions are release blockers.
*   Owner quality bar (added 2026-09): latest stable toolchains; ≥90% line AND
    branch coverage on core packages; lint/format/typecheck with zero
    warnings; conventional commits; docs kept synced (README, PRD, ADRs,
    build log, changelog, style guide, CI).

## Research & Information

*   **Initial Research:**
    *   "AI-powered skill development platforms": identified Skillsoft Percipio
        (AI-native skills intelligence, dynamic skills, talent-opportunity matching).
    *   **vedai.in:** personalized "Skill DNA" assessments, activity-based
        evaluations, hybrid AI-human mentorship, career mapping with earning opportunities.
*   **AI Models:** GPT-4 (accuracy/customizability), Gemini (context window),
    Claude (coding/writing). Rather than committing to one vendor, the
    implementation uses a provider-agnostic JSON contract with an
    OpenAI-compatible client and an Anthropic client (ADR 0005), so the model
    is configuration, not code.
*   **Agentic frameworks:** LangChain et al. were evaluated and deliberately
    NOT used — the product needs one structured JSON call per feature with
    strict validation and a deterministic fallback; a framework would add
    abstraction without value at this scale (see ADR 0005).
*   **FastAPI best practices:** applied — async throughout, dependency
    injection via `Annotated` aliases, router/service separation,
    pydantic-settings with env prefix, Ruff + strict mypy.

## Plan

1.  **Initial Research and Feature Ideation.** (Complete)
2.  **Architecture and System Design.** (Complete — docs/architecture.md, ADRs)
3.  **Phase 1: Core Platform Development.** (Complete)
4.  **Phase 2: AI Integration.** (Complete — env-keyed providers + offline fallback)
5.  **Phase 3: Platform Enhancement.** (Partially complete — see docs/roadmap.md)

## Feature Implementation Status

### Implemented (verified end-to-end, see limitations in docs/)

*   **Backend user management:** register / login (OAuth2 password flow) /
    refresh / me; JWT access + refresh; Argon2id hashing; profile read/update.
*   **Skill assessment API:** narrative → structured result (skills + levels,
    strengths, gaps, recommended roles, readiness score).
*   **Learning path API:** roadmap generation from latest/explicit assessment.
*   **Resume API:** generate / list / get / partial update with ownership checks.
*   **Market analysis API:** cached per-role insights.
*   **SSE realtime events:** per-user stream with keep-alives.
*   **AI integration:** OpenAI-compatible + Anthropic providers, strict JSON
    schema validation, deterministic offline rule-based engine fallback;
    `engine_used` records the origin.
*   **Frontend user management (wired to backend):** login, registration,
    protected routes, logout, session restore.
*   **Frontend AI features (wired to backend):** skill assessment page and
    learning path page rendering real API results.
*   **Accessibility:** labelled forms, `role="alert"` errors, live regions,
    `aria-current` navigation, real buttons, visible focus, keyboard-first.

### Not implemented (tracked in docs/roadmap.md)

*   OAuth social login, email verification, password reset, refresh-token
    revocation.
*   Full Alembic migrations (additive column changes are covered by versioned
    startup upgrades, ADR 0008), Redis-backed event bus, Docker/packaging,
    CI deployment.
*   Progress analytics, interview prep, job-board integrations, multi-language
    UI, resume PDF export.

## Current Status (updated 2026-09-13)

*   **Overall:** Phase 1 + Phase 2 functional end-to-end. Full user journey
    (register → login → assessment → learning path → resume → market →
    refresh → SSE) verified over live HTTP and through the Vite dev proxy.
*   **Backend:** FastAPI app factory (`app/main.py`), async SQLAlchemy
    (SQLite dev / MySQL-ready), strict mypy, Ruff, 291 pytest tests with
    99.37% line+branch coverage (≥90% enforced). See ADR 0001–0008.
*   **AR-027 fix (2026-09-14):** `/healthz` returns only `{"status":"ok"}`
    by default (provider/version/debug diagnostics behind
    `PRAGATISHALA_DEBUG`), and `/api/docs` + `/api/openapi.json` are served
    only in debug mode.
*   **Fourth pass / publication re-check (2026-09-13):** hostile re-review at
    final HEAD with executed probes; findings and explicitly empty review
    categories recorded in `docs/PUBLICATION-PASS.md`. Fixes: JWT subject
    parsing hardened (non-ASCII digits crashed instead of returning None),
    engine level-word sharing stopped at another skill's years figure; the
    FastAPI HEAD-on-GET 405 shape is pinned so the rate-limit audit stays
    honest. All dependencies re-verified against live PyPI/npm; the e2e
    smoke and the README quickstart were re-executed against this HEAD.
*   **Third adversarial pass (2026-09-12):** all 11 findings from
    `docs/ADVERSARIAL-REVIEW-3.md` fixed with per-finding regression tests;
    resolution table appended to that review (led/LED case disambiguation,
    decimal years, list-level sharing, homograph sense checks, years-gap
    boundaries, per-user market-refresh budget, startup schema upgrades,
    bare-preceder corroboration, redirect refund, smoke refresh probe,
    asp.net alias).
*   **Frontend:** React 19 + Chakra UI v3 + React Router; typed API client with
    token refresh; AuthContext session bootstrap; 37 Vitest tests; ESLint and
    `tsc` strict clean. Note: the earlier tracker claim that the frontend "was
    running successfully" was inaccurate — the v2-era code never compiled
    against the installed v3 library; it was rebuilt on 2026-09-11.
*   **Quality gates:** all enforced locally and in CI
    (`.github/workflows/ci.yml`). Known subtlety: backend coverage requires
    `concurrency = ["greenlet"]` (see docs/limitations.md #1).
*   **Known gaps:** listed honestly in docs/limitations.md (token revocation,
    no Playwright e2e yet, MySQL untested in CI, rule-based engine
    heuristics).
