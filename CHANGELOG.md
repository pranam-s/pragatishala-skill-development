# Changelog

All notable changes to PragatiShala are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — 2026-09-12

Second adversarial pass remediation (findings AR2-001..AR2-015 from
`docs/ADVERSARIAL-REVIEW-2.md`).

### Fixed
- Skill engine: the ambiguous-alias gate now requires word-bounded context
  (`know` no longer matches inside "knowledge"), evaluates that context within
  a window around the alias instead of anywhere in the sentence, treats a
  usage verb directly before the alias as evidence, and gates the remaining
  homographs (node, swift, cv, .net, lambda). Direct claims like "Built a
  payments service using Go." and "I led a team of five." land again while
  "At the coding bootcamp I was ready to go." stays silent (AR2-001/002/003).
- Skill engine: abbreviation dots (e.g./i.e./etc.) no longer split sentences
  before level-word attribution (AR2-004); experience figures bind only to
  mentions within a few tokens of the years word (AR2-006).
- Rate limiting: fully expired buckets are swept every 512 checks so unique
  keys cannot grow memory without bound (AR2-010); route matching is
  trailing-slash-insensitive (AR2-011).
- Config: the low-entropy secret error names the failing condition
  (distinct chars vs flat distribution) (AR2-012); known placeholders are
  rejected as substrings, so decorated placeholders fail too (AR2-007).

### Added
- SSE events carry a monotonic per-user `seq` (also the SSE `id` line) so
  clients can detect backpressure gaps and re-sync via REST (AR2-013).
- `GET /market/insights?refresh=true` invalidates a cached report without
  database access, and the generating LLM model is persisted and returned as
  `model_used` (AR2-014).
- `docs/deployment.md`: single-worker posture, real-IP forwarding, proxy-level
  limits, SSE-safe buffering — the guidance ADR 0007 deferred to (AR2-009).

### Testing
- e2e smoke now asserts a live SSE event with its sequence id, the second
  market call serving `cached=true`, tampered-refresh rejection, and a 429
  from an exhausted auth bucket. Refresh-token reuse *detection* remains
  deferred (tokens are not yet revocable — limitations #2, ADR 0002)
  (AR2-015).
- Backend: 232 tests, 99.31% line+branch coverage. Frontend: 37 tests
  (unchanged; no frontend code touched).

### Docs
- limitations #5 states the scorer's remaining precision limits (reported
  speech, heuristic context window); #13 records that the JWT-secret
  validator is a sanity floor, not a strength meter; #14 records the
  socket-peer trust posture (AR2-005/008/009).

## [Unreleased] — 2026-09-12 (first pass)

Adversarial-review remediation pass (findings AR-001..AR-032 from
`docs/ADVERSARIAL-REVIEW.md`) plus the publication finalization pass
(AR-033, AR-034).

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
- Readiness score: the soft bonus counted *missing* recommended skills, so
  extra adjacent knowledge could lower a candidate's score relative to an
  identical profile without it; it now counts recommended skills actually
  covered, capped at +10 (AR-033).
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
- Catch blocks narrow with a single `instanceof Error` check; the redundant
  `ApiError` narrowing (a subclass) was dropped in SkillAssessment and
  ProfilePage (AR-035).
- Finalization refresh: @chakra-ui/react 3.29 → 3.37, react/react-dom 19.2 →
  19.3, @types/react* 19.3, @types/node 24.13; backend `uv lock --upgrade`
  re-verified current. TypeScript stays ^6.0.3 (typescript-eslint 8.70.0
  peer-caps typescript <6.1.0 — re-checked against the live registry)
  (AR-034).

### Testing
- hypothesis property suite: JWT round-trips, readiness bounds, engine
  determinism, scope isolation, fenced-JSON tolerance, role-normalisation
  idempotence (AR-031).
- New error-path tests: deleted-user refresh, market-cache insert race,
  provider timeouts for both providers (AR-032); e2e smoke script now
  re-verifies SSE (401/200), ownership boundaries, resume PATCH, and
  profile PATCH over live HTTP (AR-019).
- Backend: 200 tests, 99.28% line+branch coverage. Frontend: 37 tests.
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
