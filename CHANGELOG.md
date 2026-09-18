# Changelog

All notable changes to PragatiShala are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased] — 2026-09-18 (production-completion pass)

### Changed
- Dependencies refreshed to latest stable: backend `uv lock --upgrade`
  (sqlalchemy 2.0.54, uvicorn 0.53.0, ruff 0.16.8, coverage 7.16.1, idna
  3.20, greenlet 3.5.6, ast-serialize 0.11.2); frontend `npm update`
  within semver ranges (vitest 5.0.1, @vitest/coverage-v8 5.0.1,
  react-router-dom 7.18.4, jsdom 30.1.0, @testing-library/dom 10.4.2,
  eslint-plugin-react-refresh 0.5.7, @types/node 24.13.5).
- `pydantic` and `starlette` are now declared as direct dependencies
  (they are imported directly, not only reached through FastAPI).

### Added
- Dead-code analysis as first-class gates: `deptry` and `vulture` in the
  backend dev group (package/module name maps and justified DEP002
  exemptions documented in `pyproject.toml`), `knip.json` for the
  frontend. Both run clean.
- docs/design.md — HLD + LLD overview layer with system and data-flow
  diagrams and the ADR index (architecture.md remains the deep reference).
- docs/screenshots/ — seven screenshots captured from a real
  register → login → assessment → learning-path run through the Vite dev
  proxy on 2026-09-18.

### Removed
- `@emotion/styled` (unused after the Chakra v3 migration) and the
  unused `ExperienceLevel` type alias.

## [Unreleased] — 2026-09-14 (AR-027 information-exposure fix)

### Fixed
- Security: `/healthz` no longer discloses the active AI provider, app
  version, or debug flag to unauthenticated callers — it returns only
  `{"status":"ok"}` (AR-027). The diagnostics return behind
  `PRAGATISHALA_DEBUG=true` (default off).
- Security: `/api/docs` (Swagger UI) and `/api/openapi.json` are served only
  when `PRAGATISHALA_DEBUG=true`; by default both return 404 instead of
  enumerating every endpoint to anonymous callers (AR-027).

### Testing
- Backend: 291 tests (was 289), 99.37% line+branch coverage (was 99.36%).
  New posture tests: healthz minimal-by-default, healthz diagnostics
  opt-in, docs/schema hidden-by-default, docs/schema available-in-debug.

## [Unreleased] — 2026-09-13 (fourth pass, publication re-check)

Hostile re-review of the AR2/AR3 remediation waves at final HEAD, with
executed probes; findings and explicitly empty categories in
`docs/PUBLICATION-PASS.md`.

### Fixed
- Auth: JWT subjects with non-ASCII digit characters ("²") crashed subject
  parsing with a `ValueError` (a 500 where 401 belongs); parsing now accepts
  ASCII digits only and degrades every malformed subject to "unauthenticated".
- Skill engine: a clause's level word is no longer shared across another
  skill's experience figure ("Expert in Python, 5 years with Go and Rust."
  no longer scores Rust as expert); a years figure in the gap is an
  attribution boundary, consistent with AR3-005.

### Verified (no change needed)
- FastAPI answers 405 for HEAD on GET routes, so HEAD cannot bypass the
  rate-limit buckets to reach billable handlers; the 405 shape and the
  unconsumed bucket are now pinned by tests.
- Every dependency re-verified against live PyPI/npm (2026-09-13): all
  locked versions are the newest releases. Stale floors raised: pyjwt
  ≥2.14.0, ruff ≥0.16.7, uv_build ≥0.12.13. TypeScript stays on 6.0.3:
  typescript-eslint 8.70.0 peers `typescript <6.1.0`, so the released
  TS 7.0.2 is ecosystem-blocked for lint.
- README quickstart, the Vite dev-proxy path, and the full
  `scripts/e2e_smoke.sh` re-executed against this HEAD (all passed).

### Testing
- Backend: 289 tests (was 278), 99.36% line+branch coverage held.
  Frontend unchanged: 37 Vitest tests, ESLint/tsc/build clean.

## [Unreleased] — 2026-09-12 (third pass)

Third adversarial pass remediation (findings AR3-001..AR3-011 from
`docs/ADVERSARIAL-REVIEW-3.md`; resolution table appended to that review).

### Fixed
- Skill engine: lowercase "led" is a leadership claim again (only the
  all-caps "LED" acronym is gated, causative "led to …" stays vetoed),
  restoring "I led the migration and I am an expert in Python." and the
  other dominant phrasings the AR2 gate dropped (AR3-001).
- Skill engine: decimal years parse as one figure ("0.5 years with Python"
  is beginner, not expert), and decimal points no longer split sentences
  (AR3-002).
- Skill engine: a clause's level word covers every list sibling
  ("Expert in Python, SQL, and Java." → all expert), stopping at discourse
  markers (AR3-003).
- Skill engine: the surviving homograph fabrications are closed ("go-to
  person for databases", "Updated my CV with new skills", "wrote a lambda
  expression", "the swift development of the feature", "a node in the
  database cluster"); cv/lambda require domain cues (AR3-004).
- Skill engine: a comma or discourse marker between a years figure and a
  skill voids the binding, and the boundary-free proximity budget widened
  4→6 tokens ("10 years designing and building data pipelines in Python."
  now scores expert) (AR3-005).
- Market: `refresh=true` draws from a per-user hourly budget
  (`PRAGATISHALA_MARKET_REFRESH_PER_HOUR`, default 6; 0 disables), so the
  24 h cache again bounds LLM spend per account (AR3-006).
- Rate limiting: 3xx redirects no longer consume the budget; a followed
  trailing-slash request consumes exactly one hit (AR3-009).

### Added
- Database: idempotent, versioned startup schema upgrades
  (`schema_upgrades` table, ADR 0008); a legacy `market_reports` table is
  altered at startup to add `model_used` instead of 500ing on every market
  request (AR3-007).

### Testing
- e2e smoke probes the market refresh path (`cached=false`, `model_used`
  presence); the 60 s re-run cool-down after the 429 burst is documented in
  deployment.md §5 (AR3-010). Backend: 278 tests, 99.36% line+branch
  coverage (AR3-011 included: "ASP.NET" detects as C#).

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
