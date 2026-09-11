# Changelog

All notable changes to PragatiShala are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — 2026-09-12

Adversarial-review remediation pass (findings AR-001..AR-032 from
`docs/ADVERSARIAL-REVIEW.md`).

### Security
- JWT secrets: placeholder denylist + entropy floor; copied `.env.example`
  values are rejected at startup with generation instructions (AR-021,
  ADR 0006).
- Rate limiting: in-process sliding-window middleware on auth (10/min) and
  LLM-billed generation endpoints (15/min), 429 + Retry-After, env-tunable
  (AR-023, ADR 0007).
- `/auth/refresh` resolves the subject and rejects deleted users and
  non-numeric subjects (AR-022).
- `jwt_algorithm` restricted to HS256/HS384/HS512; tokens carry and require
  `iss`/`aud` claims (AR-025).
- LLM prompts fence user text in `<user_data>` tags with treat-as-data
  instructions (AR-026).

### Fixed
- Rule-based engine: proficiency evidence (level words, year figures) binds
  only to the skill mentioned in the same sentence - the old ±30-char window
  leaked attributes across skills (AR-029).
- Ambiguous aliases ("go", "led", "c") only match with skill context, so
  "ready to go", "LED lights", and "grade A B C" no longer invent skills
  (AR-030).
- `/profile` restored to the RouteTitle map - screen-reader page context
  (AR-008).
- Market cache cold-start race returns the winner's row instead of a 500
  (AR-028).
- Frontend: native minLength validation active (noValidate removed) and
  index-stable list keys (AR-010, AR-011).

### Changed
- Frontend toolchain: TypeScript ~5.9.3 → ^6.0.3 (TS 7 blocked by
  typescript-eslint's supported range), Vite 7 → 8, @vitejs/plugin-react
  5 → 6, ESLint 9 → 10 (+@eslint/js 10, react-hooks plugin 7),
  typescript-eslint 8.70, react-router-dom 7.18.3; framer-motion removed;
  0 npm audit findings (AR-002..AR-005).
- CI: actions/checkout v7, setup-node v7 (Node 24 LTS), setup-uv v10;
  dependabot config added (AR-006, AR-007).
- Backend: `uv lock --upgrade` (ruff 0.16.7, pyjwt 2.14.0) (AR-001).
- Always-"completed" status columns removed from assessments and learning
  paths (AR-017); dead code removed (backend/main.py re-export,
  EventBus.subscriber_count) (AR-012, AR-013); redundant manual
  `updated_at` write dropped (AR-018).
- EXPERIENCE_LEVELS de-duplicated into frontend/src/api/types.ts (AR-009).
- `.gitignore` trimmed to project-relevant entries; `.env.example` ships a
  denylisted placeholder that fails loudly (AR-020).

### Testing
- hypothesis property suite: JWT round-trips, readiness bounds, engine
  determinism, scope isolation, fenced-JSON tolerance, role-normalisation
  idempotence (AR-031).
- New error-path tests: deleted-user refresh, market-cache insert race,
  provider timeouts for both providers (AR-032); e2e smoke script now
  re-verifies SSE (401/200), ownership boundaries, resume PATCH, and
  profile PATCH over live HTTP (AR-019).
- Backend: 199 tests, 99.28% line+branch coverage. Frontend: 37 tests.
- Mutation testing assessed: mutmut 3.x needs Linux/WSL (fork support);
  wired as CI follow-up (README, roadmap).

### Docs
- limitations #4/#5 rewritten to match shipped behaviour; #6 added for
  prompt-injection residual risk; architecture routing and test counts
  synced; ADR 0006 and ADR 0007 added (AR-014, AR-015, AR-027, AR-024
  remain documented trade-offs tracked in the roadmap).

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
