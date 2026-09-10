# Changelog

All notable changes to PragatiShala are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-09-11

First working end-to-end release: full backend, wired frontend, quality gates.

### Added

- Backend (FastAPI, async):
  - App factory with lifespan-managed skill engine, database creation, and
    CORS; `/api/v1` versioned API; OpenAPI docs at `/api/docs`.
  - Auth: registration, OAuth2 password login, JWT access/refresh pair,
    `/auth/me`; Argon2id hashing; 32-byte minimum signing secret.
  - Users: profile read/update.
  - Skill assessments, learning paths, resumes: create/list/get with ownership
    enforcement; learning paths derive from the latest or an explicit
    assessment; resume partial updates.
  - Market insights with a 24-hour per-role cache.
  - SSE endpoint with per-user fan-out, keep-alives, and disconnect cleanup.
  - AI integration: OpenAI-compatible + Anthropic providers (env-only keys,
    strict JSON validation) with a deterministic rule-based fallback per
    feature; `engine_used` records the origin of every result.
  - `.env.example` documenting every environment variable.
- Frontend (React 19 + TypeScript + Vite + Chakra UI v3):
  - Typed API client with automatic auth headers and single-retry refresh.
  - Auth context (bootstrap, login, register, logout) and protected routing
    with redirect-back.
  - Login and registration pages with labelled, keyboard-operable forms and
    screen-reader announced errors.
  - Skill assessment and learning path pages rendering real API results with
    live-region announcements and accessible module lists.
  - Navbar with `aria-current` page state and a real logout button.
- Quality/infra:
  - Backend tests: 146 tests, ~99% line+branch coverage (≥90% enforced),
    `concurrency = ["greenlet"]` for truthful async SQLAlchemy coverage.
  - Frontend tests: 31 Vitest/Testing Library tests.
  - Ruff + strict mypy clean; ESLint + `tsc --strict` clean.
  - GitHub Actions CI running all gates (backend + frontend jobs).
  - Docs: PRD, architecture, five ADRs, style guide, limitations, roadmap,
    README rewrite, this changelog, and a truthful build log.

### Changed

- README rewritten to reflect reality (uv-based setup, honest status section)
  instead of the aspirational stack list (MySQL/Redis/LinkedIn integrations are
  not part of the implementation yet).
- `backend/main.py` placeholder ("Hello World") replaced by a re-export of the
  real app; placeholder `requirements.txt` removed in favour of `uv.lock`.

### Fixed

- Health endpoint reported the wrong component's provider name.
- SSE router referenced a non-existent setting (`sse_keepalive_seconds`).
- Rule-based assessment let proficiency words anywhere in the text inflate
  unrelated skills' levels (now windowed to ±30 chars around the mention).
- Frontend did not compile against Chakra UI v3 (v2-era component APIs,
  missing `react-icons` dependency, missing `ChakraProvider` value).
