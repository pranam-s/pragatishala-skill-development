# Adversarial Review — pragatishala-skill-development

> **Remediation status (2026-09-12):** findings AR-001…AR-004, AR-006…AR-023,
> AR-025…AR-026, AR-028…AR-032 are fixed; AR-005's same-major drift was
> cleared by `npm audit fix` + toolchain refresh; AR-007 fixed. Remaining
> open items (deliberate, tracked):
> - **AR-024** — logout is client-side, no revocation: documented trade-off
>   (ADR 0002); rotation/revocation stays Phase-3 roadmap security work.
> - **AR-027** — `/healthz` + `/api/docs` exposure: production-guide item,
>   noted in roadmap Ops.
> - **AR-031 (mutation testing)** — hypothesis properties shipped; mutmut
>   needs Linux/WSL (fork support), wired as CI follow-up (README, roadmap).
>
> See CHANGELOG "Unreleased" for the full change list.

- **Reviewer:** independent adversarial review pass (ZCode agent)
- **Date:** 2026-09-11 (IST)
- **Commit reviewed:** `a46f9be` (tree clean at review start)
- **Scope:** backend (FastAPI, Python 3.13, uv), frontend (React 19 + Chakra v3), docs, tests, CI
- **Method:** full read of tracked sources; suspected bugs verified with targeted runs (`uv run pytest`, in-process ASGI probes, rule-engine probes) — all findings carry evidence; dependencies checked against live PyPI/npm registries and GitHub Actions releases on 2026-09-11. Findings only — nothing was fixed.

---

## Pass 1 — Dependency audit (live registries, checked 2026-09-11 ~23:30 IST)

Backend pyproject floors vs PyPI latest (`pypi.org/pypi/<pkg>/json`, `info.version`):
all 10 runtime deps and all 5 dev deps are at or admit the current latest
(fastapi 0.141.1, sqlalchemy 2.0.52, pydantic-settings 2.15.0, pydantic 2.13.5,
uvicorn 0.52.4, httpx 0.28.1, argon2-cffi 25.1.0, aiosqlite 0.22.1,
email-validator 2.3.0, python-multipart 0.0.32, mypy 2.3.1, pytest 9.1.1,
pytest-asyncio 1.4.0, pytest-cov 7.1.0, uv-build 0.12.13 within the
`>=0.12.10,<0.13.0` build pin). The `uv.lock` is likewise current except the
two same-week items in AR-001 below. The frontend is where staleness
concentrates: several majors behind, one unused dependency, and one tilde-pin.

### Findings added this pass

- **AR-001 (P3, deps-backend):** `uv.lock` pins `ruff 0.16.6` (latest 0.16.7)
  and `pyjwt 2.13.0` (2.14.0 was released 2026-09-11, one day after the lock
  was generated on 2026-09-10). Not a pinning violation — floors admit both —
  but `uv lock --upgrade` should be run before the next commit.
- **AR-002 (P2, deps-frontend):** `framer-motion` is a direct dependency
  (`package.json` ^12.23.24, lock 12.23.24) but **zero imports exist anywhere
  in `frontend/src`**; latest is 13.2.0 (a major behind as well). Chakra UI v3
  does not require framer-motion. Dead dependency — remove it.
- **AR-003 (P2, deps-frontend):** `typescript` is the only tilde-pinned
  version in the manifest (`~5.9.3`, lock 5.9.3); npm latest is **7.0.2**.
  Two majors behind plus a hand-pin that blocks even minor updates. Either
  upgrade the toolchain (checking typescript-eslint/vitest compat with the
  TS 7 native compiler) or, at minimum, use a caret range for the 5.x line.
- **AR-004 (P2, deps-frontend):** build/lint majors behind npm latest:
  `vite` lock 7.2.1 vs latest **8.3.0**; `@vitejs/plugin-react` 5.1.0 vs
  **6.1.1**; `eslint` 9.39.1 vs **10.10.0** (with `@eslint/js` 10.0.1);
  `eslint-plugin-react-hooks` 5.2.0 vs **7.1.1**.
- **AR-005 (P3, deps-frontend):** same-major drift (stale lock, refresh
  recommended): `react-router-dom` 7.9.5 vs 7.18.3, `@chakra-ui/react` 3.29.0
  vs 3.37.0, `react`/`react-dom` 19.2.0 vs 19.3.0, `typescript-eslint` 8.46.3
  vs 8.70.0, `@types/react`/`@types/react-dom` 19.2.2 vs 19.3.0,
  `eslint-plugin-react-refresh` 0.4.24 vs 0.5.6, `globals` 16.5.0 vs 17.12.0.
- **AR-006 (P3, ci):** GitHub Actions pinned to old majors:
  `actions/checkout@v4` (latest v7.0.1), `actions/setup-node@v4` (latest
  v7.0.0), `astral-sh/setup-uv@v5` (latest v10.1.0). No dependabot/renovate
  config exists to keep actions or npm deps current — a likely reason the
  drift in AR-002…AR-005 accumulated.
- **AR-007 (P3, ci):** `ci.yml` uses `node-version: 22` while the project
  pins `@types/node` ^24 (lock 24.10.0) — type definitions for a newer Node
  major than the CI runtime. Align both (Node 24 is LTS as of 2026).

---

## Pass 2 — Documentation drift and code health (static)

- **AR-008 (P2, a11y/code):** `frontend/src/components/RouteTitle.tsx` — the
  `TITLES` map has no `"/profile"` entry, so the Profile page falls back to
  the generic title "PragatiShala". `/profile` was added in the latest commit
  (a46f9be) without updating the map. This is exactly the page-context cue
  the component exists to provide; the project itself classifies a11y
  regressions as release blockers, hence P2.
- **AR-009 (P3, DRY):** `EXPERIENCE_LEVELS` is duplicated verbatim in
  `frontend/src/components/RegistrationPage.tsx` and
  `frontend/src/components/ProfilePage.tsx`, and must be manually kept in
  sync with the backend `Literal` in `app/schemas.py`. Extract to a shared
  module (and consider generating from the OpenAPI schema).
- **AR-010 (P3, logic-UX):** `SkillAssessment.tsx` sets both
  `minLength={MIN_LENGTH}` on the Textarea **and** `noValidate` on the form —
  `noValidate` disables the native constraint, so the declared minimum never
  fires client-side; every too-short submit makes a pointless round trip and
  surfaces a raw 422 message. Either drop `noValidate` or do explicit
  client-side validation.
- **AR-011 (P3, correctness-frontend):** `LearningPath.tsx` uses
  `key={module.title}` — the AI provider path can legitimately return two
  modules with the same title, producing duplicate React keys and mis-rendered
  list items. Use the index-stable id (e.g. `key={`${index}-${module.title}`}`)
  or require unique titles in the schema.
- **AR-012 (P3, dead-code):** `backend/main.py` is a tracked 5-line re-export
  whose only purpose is supporting `uvicorn main:app`; `app.main:app` is the
  documented entrypoint. YAGNI — remove the module (and the mention in the
  `app/main.py` docstring) or justify it in the architecture doc.
- **AR-013 (P3, dead-code):** `EventBus.subscriber_count()` is used only by
  tests (its own docstring says so) — production code living for tests.
  Assert against `bus._subscribers` in tests or drop the method.
- **AR-014 (P3, doc-drift):** `docs/limitations.md` #9 says frontend has
  "**31 tests**" and `AGENTS.md` says "**31 Vitest tests**"; README and
  reality say **36** (verified: 36 `it(`/`test(` blocks, vitest collects 36).
  Commit d06e4a8 updated some docs but missed these two.
- **AR-015 (P3, doc-drift):** `docs/architecture.md` "Routing" lists
  authenticated routes as `/assessment`, `/learning-path` — `/profile` is
  missing (same commit-blind spot as AR-008).
- **AR-016 (P3, doc-drift):** `app/events.py` module docstring claims events
  are published "when long-running AI work **starts and finishes**" — services
  publish only completion events; no start events exist.
- **AR-017 (P3, YAGNI):** `Assessment.status` and `LearningPath.status` are
  always written `"completed"` and never transition; `Resume` has no status at
  all. Either implement the state machine or drop the columns.
- **AR-018 (P3, robustness):** `services.update_resume` manually sets
  `resume.updated_at = datetime.now(UTC)` although the column already has
  `onupdate=utcnow` — redundant dual mechanism that can drift.
- **AR-019 (P3, script-hygiene):** `scripts/e2e_smoke.sh` line 23 is dead
  (`curl ... "/../healthz" ... || true` — the result is discarded and the next
  line re-checks healthz properly), and the candidate-path loop contains
  stray multiple spaces. Also: the script never exercises SSE, ownership
  boundaries, or resume PATCH, while `docs/limitations.md` claims the full
  journey "→ SSE" was verified over live HTTP (that was a one-off manual run;
  the committed script cannot re-verify it).
- **AR-020 (P3, redundancy):** `.gitignore` is the raw GitHub Python template
  (Django/Flask/Scrapy/Sphinx/PyInstaller sections) plus a duplicated
  project-specific section at the bottom; `backend/.env.example` ships
  `PRAGATISHALA_JWT_SECRET_KEY=change-me-at-least-32-bytes-long`, which is
  33 chars and therefore **passes** the ≥32-byte validator (see AR-021 for
  the security impact).

---

## Pass 3 — Security (verified with live runs against the ASGI app)

Verification script (in-process httpx + ASGITransport, throwaway temp SQLite):

| Probe | Result |
|---|---|
| `GET /api/v1/events` without token | **401** — SSE requires auth (good) |
| Refresh token presented as access bearer | **401** — type confusion rejected (good) |
| Garbage bearer | **401** (good) |
| `POST /auth/refresh` after the user row was deleted | **200 — mints a fresh pair for a deleted user** (AR-022) |
| That minted access token on `/users/me` | 401 (blast radius contained — access checks the DB) |
| `Settings(jwt_secret_key=".env.example placeholder")` | **Accepted** (AR-021) |

Also verified good: CORS is an explicit allow-list (no wildcard) with
credentials; all queries go through SQLAlchemy `select`/`session.get` (no raw
SQL anywhere); update schemas are field-limited so `apply_profile_update`'s
`setattr` loop cannot mass-assign `email`/`hashed_password`; ownership checks
live in services and are tested (`test_other_users_assessment_is_404`, the
resume-PATCH "Hijacked" probe); unknown accounts burn a dummy Argon2 verify
against timing enumeration; password hashing is Argon2id with library defaults.

### Findings added this pass

- **AR-021 (P2, security-secrets):** The weak-secret guard is length-only.
  The placeholder committed in `backend/.env.example`
  (`change-me-at-least-32-bytes-long`, 33 bytes) passes the validator
  (verified by direct construction). A developer who copies the example
  without editing — the exact workflow the README documents (`cp .env.example
  .env`) — deploys with a publicly-known signing key: any outsider can mint
  valid access/refresh JWTs for any user id. No startup warning is emitted
  for known placeholder values. Fix: reject a denylist of placeholder
  literals in the validator and/or warn at startup.
- **AR-022 (P3, security-auth):** `/auth/refresh` never checks that the
  subject still exists — verified above: it happily re-mints for a deleted
  user for the full 7-day window. Same handler does `int(subject)` unguarded
  (a validly-signed non-numeric `sub` yields an unhandled 500). Fix: resolve
  the user in the refresh service (it currently has no DB dependency at all)
  and guard the conversion.
- **AR-023 (P2, security-rate):** No rate limiting or account-lockout on
  `/auth/login`, `/auth/register`, `/auth/refresh`; nothing throttles
  `/assessments`/`/resumes/generate` either, which with a provider key
  configured converts into an open tap on the owner's LLM budget. Documented
  in limitations #4 and roadmap (so not a surprise), but it is the largest
  open door on a platform holding student PII — severity P2 until it ships.
- **AR-024 (P3, security-auth):** Logout is purely client-side
  (`clearTokens()`); combined with no server-side revocation (documented ADR
  0002 / limitations #2) a "logged out" session's refresh token remains valid
  for 7 days, and localStorage keeps tokens XSS-readable. Documented
  trade-off; listed because for student data the roadmap item should be
  treated as security work, not enhancement work.
- **AR-025 (P3, security-jwt):** `jwt_algorithm` is a free-text env var
  honoured by both encode and decode (`algorithms=[settings.jwt_algorithm]`);
  setting it to `none` in the environment yields unsigned-token acceptance
  (requires attacker env control, hence P3 hardening). No `iss`/`aud` claims
  are validated. Fix: `Literal["HS256","HS384","HS512"]` + issuer/audience.
- **AR-026 (P3, security-ai):** Prompt injection is unmitigated: user
  narrative, target role, and resume text are interpolated verbatim into the
  user message and the system prompt's "STRICT JSON only" is the only
  defence. Blast radius is bounded — output is schema-validated and rendered
  only back to the injecting user — and, importantly, the **shared** market
  cache is safe: its prompt contains only the canonical profile title, never
  user text (verified by reading `SkillEngine.market_insights`). Fix
  direction: delimit/escape user text, add an injection-resistance note to
  the limitations doc.
- **AR-027 (P3, security-info):** `/healthz` publicly reports the active AI
  provider and the debug flag, and `/api/docs` + `/api/openapi.json` are
  always public. Reasonable in dev; there is no production hardening story
  yet (roadmap's deployment guide should own this).
- **AR-028 (P3, security-availability):** Cold-start race in
  `get_market_insights`: two concurrent requests with no cached row both
  `session.add(MarketReport(...))` → the second commit violates
  `uq_market_reports_role` → unhandled `IntegrityError` → 500. No
  concurrency tests exist (verified: only `test_events.py` uses `gather`).
  Fix: catch IntegrityError and re-read, or use an upsert.

---

## Pass 4 — Logic / semantic (verified with live runs against the rule engine)

| Probe | Result |
|---|---|
| `"I do advanced Python. Also SQL."` | **SQL = advanced** (level word leaked from Python, 30 chars away) — AR-029 |
| `"After 4 years of SQL, I touched Python yesterday."` | **Python = advanced** (`4 years` leaked from the SQL clause) — AR-029 |
| Isolated controls (`"I do advanced Python."`) | correct levels (the window is the only culprit) |
| `"We are ready to go. I also fix LED lights…"` | **Go = beginner, Leadership = beginner** — AR-030 |
| `"…grade A B C."` | **C (programming) = beginner** — AR-030 |
| `"I am an expert in Python with 6 years…"` | expert (correct) |
| Learning path from an all-skills assessment | sane module list, readiness 85 |

Also verified good: the market cache TTL is a pure report cache — there are no
updates that could go stale mid-TTL, the cached response's `refreshed_at` is
the original refresh time, roles are normalized before lookup, and the LLM
path re-writes `content`/`refreshed_at`/`engine_used` atomically (aside from
AR-028's first-write race). `CHANGELOG.md` confirms the ±30-char window was
itself the fix for a prior whole-text level leak — the fix is incomplete
(AR-029).

### Findings added this pass

- **AR-029 (P2, logic-engine):** The ±30-char proficiency window
  (`app/ai/engine.py:90-94`) attributes level words **and year figures** from
  a neighbouring skill's phrase to the skill being scored (verified above,
  with controls). This directly corrupts the skill levels that feed readiness
  scores and learning-path generation. Fix: score each mention using only the
  text between this mention and the previous/next skill mention (segmentation
  rather than a fixed window), or anchor the level word to the mention with a
  tighter, directional regex.
- **AR-030 (P3, logic-engine + doc):** Vocabulary false positives: the
  aliases "go" and "led" and the single-letter skill "C" match ordinary
  English/enumerations (verified above); unqualified claims ("I know Python")
  default to beginner. `docs/limitations.md` #5 claims the engine "will miss
  unusual phrasings" — it also **invents** skills it was never told about;
  the honest-limitations doc mischaracterizes the failure mode, which matters
  because `engine_used=rule_based` is the only disclosure.

---

## Pass 5 — Test adequacy

- Backend suite re-run during this review: **146 passed in ~12.5s, 98.91%
  line+branch coverage** (`--cov-branch --cov-fail-under=90`), ruff
  check/format clean, `mypy --strict` clean (23 files). README's numbers are
  accurate.
- Frontend suite re-run: **36/36 passed** (8 files), ESLint clean. The tests
  are behaviour-oriented: they drive components through `userEvent`,
  assert on roles/labels/announced text (doubles as a11y checks), and stub
  the network at the `api` module boundary; the client tests exercise real
  fetch mocks including refresh-retry, refresh-failure, and transient-network
  token retention. They do not mirror implementation internals. Asserting
  exact URLs/headers in `client.test.ts` is contract testing, acceptable.
- The `concurrency = ["greenlet"]` coverage fix is legitimate and correctly
  documented (pyproject comment + limitations #1); the measured coverage
  (98.91%) is consistent with the tracer actually measuring async bodies.
- e2e smoke (`scripts/e2e_smoke.sh`) covers healthz → register → dup-register
  → login → me → unauth-401 → assessment → learning path → resume → market
  → refresh, but **not** SSE, ownership boundaries, resume PATCH, or profile
  PATCH (see AR-019); `docs/limitations.md`'s "verified over live HTTP"
  journey includes SSE, which the committed script cannot re-verify.
- No user-deletion path is tested anywhere (relevant to AR-022), no
  concurrency/race tests exist (AR-028), and the provider tests mock HTTP
  failures but not timeout exceptions explicitly.

### Findings added this pass

- **AR-031 (P2, testing):** No property-based testing anywhere (`hypothesis`
  is absent from the project), despite the owner's bar requiring it for
  backend invariants. Cheap high-value properties exist: token round-trips
  (`decode(create(x)) == x` for arbitrary subjects, TTLs, both token types),
  readiness score bounds 0–100 for arbitrary narratives, rule-engine
  determinism/purity, `_normalize_role` idempotence, `_extract_json_object`
  accepting arbitrary fence-wrapped JSON. Mutation testing is also absent but
  **feasible**: 1,046 statements, 12.5s suite → mutmut (or cosmic-ray) with
  `paths_to_mutate=app` is well under an hour per run; document survivors.
- **AR-032 (P3, testing):** Error-path gaps named above: deleted-user
  refresh, market-cache first-write race, provider timeout path, SSE client
  disconnect cleanup (`finally` unsubscribe is untested; the events API test
  only checks the happy stream), and no test that `/api/v1/events` rejects
  unauthenticated clients (verified 401 manually in this review).

---

## Findings (consolidated)

| ID | Severity | Category | Location | Description | Fix direction |
|----|----------|----------|----------|-------------|---------------|
| AR-001 | P3 | deps-backend | backend/uv.lock | Lock pins ruff 0.16.6 (latest 0.16.7) and pyjwt 2.13.0 (2.14.0 released a day after lock build) | `uv lock --upgrade` |
| AR-002 | P2 | deps-frontend | frontend/package.json:19 | framer-motion declared, zero imports in src, 1 major behind (12 vs 13) | Remove dependency |
| AR-003 | P2 | deps-frontend | frontend/package.json:40 | typescript tilde-pinned ~5.9.3; npm latest 7.0.2 (two majors) | Upgrade toolchain or caret-range 5.x; drop the lone tilde pin |
| AR-004 | P2 | deps-frontend | frontend/package.json:33-37,42 | vite 7.2.1 vs 8.3.0; @vitejs/plugin-react 5.1.0 vs 6.1.1; eslint 9.39.1 vs 10.10.0 (+@eslint/js 10); eslint-plugin-react-hooks 5.2.0 vs 7.1.1 | Major upgrades in one coordinated pass |
| AR-005 | P3 | deps-frontend | frontend/package-lock.json | Same-major drift: react-router-dom 7.9.5→7.18.3, @chakra-ui/react 3.29.0→3.37.0, react/react-dom 19.2.0→19.3.0, typescript-eslint 8.46.3→8.70.0, @types/react(-dom) 19.2.2→19.3.0, eslint-plugin-react-refresh 0.4.24→0.5.6, globals 16.5.0→17.12.0 | `npm update` + lockfile commit |
| AR-006 | P3 | ci | .github/workflows/ci.yml:16,54,19 | actions/checkout@v4 (latest v7), setup-node@v4 (v7), setup-uv@v5 (v10); no dependabot/renovate config | Bump majors; add dependabot.yml |
| AR-007 | P3 | ci | .github/workflows/ci.yml:56 + frontend/package.json:30 | CI Node 22 vs @types/node ^24 (lock 24.10.0; DT latest tag 22.20.2) | Align: Node 24 LTS + matching types |
| AR-008 | P2 | a11y | frontend/src/components/RouteTitle.tsx:4-10 | TITLES lacks "/profile": profile page title falls back to generic; breaks the page-context cue for screen readers (a11y regressions are release blockers per project docs) | Add `"/profile": "Profile"` |
| AR-009 | P3 | DRY | frontend/src/components/RegistrationPage.tsx:7-13; ProfilePage.tsx:15-21 | EXPERIENCE_LEVELS duplicated verbatim; must be manually synced with backend Literal (schemas.py:20) | Extract shared module; consider OpenAPI codegen |
| AR-010 | P3 | logic-UX | frontend/src/components/SkillAssessment.tsx:69,76 | `noValidate` disables the declared minLength; too-short submits round-trip a 422 instead of client-side validation | Drop noValidate or validate before submit |
| AR-011 | P3 | correctness | frontend/src/components/LearningPath.tsx:93 | `key={module.title}` — AI output may contain duplicate titles → duplicate React keys | Index-composite key or schema-unique titles |
| AR-012 | P3 | dead-code | backend/main.py | 5-line re-export entrypoint duplicating app.main:app | Remove module + docstring mention |
| AR-013 | P3 | dead-code | backend/app/events.py:55-57 | subscriber_count() used only by tests (docstring admits it) | Drop it; assert on internals in tests |
| AR-014 | P3 | doc-drift | docs/limitations.md:48; AGENTS.md:92 | "31 tests" vs actual 36 (verified) | Update both |
| AR-015 | P3 | doc-drift | docs/architecture.md:86-88 | /profile missing from the routing section | Add it |
| AR-016 | P3 | doc-drift | backend/app/events.py:1-9 | Docstring claims events at work start AND finish; only completion events published | Fix docstring or implement start events |
| AR-017 | P3 | YAGNI | backend/app/models.py:53,70 | Assessment/LearningPath.status always "completed", never transitioned | Implement states or drop columns |
| AR-018 | P3 | redundancy | backend/app/services.py:301 | Manual `updated_at` write duplicates column `onupdate=utcnow` | Delete the manual write |
| AR-019 | P3 | test-gap/script | scripts/e2e_smoke.sh:23,14 | Dead curl line (`\|\| true`, result discarded) + stray spacing; smoke omits SSE, ownership, resume PATCH, profile PATCH | Remove dead line; add the missing steps |
| AR-020 | P3 | hygiene | .gitignore; backend/.env.example:6 | Raw Python-template gitignore (Django/Flask/Scrapy sections) + duplicated project section; example secret feeds AR-021 | Trim to relevant entries; ship a clearly-invalid placeholder |
| AR-021 | P2 | security-secrets | backend/app/config.py:63-70; backend/.env.example:6 | Weak-secret guard is length-only; the committed example value (33 bytes) passes verification → `cp .env.example .env` yields a publicly-known JWT signing key with no warning | Reject placeholder denylist in validator; startup warning |
| AR-022 | P3 | security-auth | backend/app/routers/auth.py:62-72 | /auth/refresh mints tokens for deleted users (verified); unguarded `int(subject)` can 500 | Resolve user in refresh; guard conversion |
| AR-023 | P2 | security-rate | backend/app/routers/auth.py (absence), routers/* | No rate limiting/lockout on login/register/refresh; /assessments + /resumes/generate unthrottled = open LLM-budget tap. Documented but open on a student-PII platform | slowapi or proxy limits + per-user quotas |
| AR-024 | P3 | security-auth | frontend/src/auth/AuthContext.tsx:87-90; docs/adr/0002 | Logout is client-side only; no revocation; localStorage tokens XSS-readable — documented trade-off, still open for student data | Treat roadmap security items as pre-launch work |
| AR-025 | P3 | security-jwt | backend/app/config.py:38; backend/app/security.py:88-92 | jwt_algorithm free-text env (accepts "none"); no iss/aud validation | Literal[HS256/384/512]; add iss/aud |
| AR-026 | P3 | security-ai | backend/app/ai/engine.py:689,742-748 | User text interpolated verbatim into LLM prompts; only defence is "STRICT JSON" instruction. Bounded impact (schema-validated, self-visible); market cache path uses canonical titles only (safe, verified) | Delimit/escape user text; note residual risk in limitations |
| AR-027 | P3 | security-info | backend/app/routers/health.py:12-22; backend/app/main.py:42-43 | /healthz publicly reports provider + debug flag; /api/docs + openapi.json always public | Gate/docs note for production guide |
| AR-028 | P3 | security-availability | backend/app/services.py:345-353 | Cold-cache race: concurrent first requests double-INSERT MarketReport → IntegrityError 500; no concurrency tests exist | Catch IntegrityError + re-read, or upsert |
| AR-029 | P2 | logic-engine | backend/app/ai/engine.py:88-94 | ±30-char window leaks level words AND year figures across skills (verified: "…advanced Python. Also SQL." → SQL=advanced; "4 years of SQL…Python" → Python=advanced); corrupts readiness + paths | Segment per mention; directional anchored regex |
| AR-030 | P3 | logic-engine | backend/app/ai/skills_data.py:87,30 + engine alias scan | FP vocabulary: "ready to go"→Go, "LED"→Leadership, "grade A B C"→C (verified); limitations #5 admits only false negatives — mischaracterized | Word-boundary+context rules; document FP mode honestly |
| AR-031 | P2 | testing | backend/pyproject.toml:18-25 (absence) | No property-based tests (hypothesis absent) and no mutation testing despite owner bar; feasible: 1,046 stmts, 12.5s suite → mutmut well under an hour | Add hypothesis invariants (token round-trip, score bounds, engine purity); add mutmut run to docs/CI |
| AR-032 | P3 | testing | backend/tests (absence) | Untested error paths: deleted-user refresh, market-cache race, provider timeout exception, SSE disconnect cleanup, unauthenticated SSE 401 | Add the five named tests |

## Verified good (complete list)

1. **Backend dependency floors match PyPI latest** for all 10 runtime + 5 dev
   deps; `uv-build` pin range contains latest 0.12.13; `uv.lock` current
   except two same-week releases (AR-001).
2. **Frontend core test stack current**: vitest 5.0.0, jsdom 30.0.1,
   @testing-library/react 16.3.3 / user-event 14.6.7 / jest-dom 7.0.1 /
   dom 10.4.1, @emotion/react 11.14.0 / styled 11.14.1,
   @vitest/coverage-v8 5.0.0 — all npm latest.
3. **Test counts honest**: 146 backend (re-run: pass, 98.91% coverage with
   branch coverage on), 36 frontend (re-run: pass). README numbers correct.
4. **Quality gates genuinely enforced**: ruff check/format clean, mypy
   --strict clean, ESLint clean, `tsc -b` strict clean (verified `strict:
   true` plus noUncheckedSideEffectImports etc.), CI runs the same gates.
5. **SSE endpoint requires authentication** (verified 401 unauthenticated);
   event fan-out is per-user with bounded queues and unsubscribe-on-disconnect.
6. **Token-type confusion rejected** at decode and at the API (verified);
   wrong-signature/expired/malformed/empty-subject paths all unit-tested.
7. **Ownership enforced in services on every read/update** (assessments,
   learning paths, resumes) and tested cross-user; `assessment_id` for path
   generation is ownership-checked too.
8. **No SQL injection surface** — ORM-only, no raw SQL; no string-built
   queries.
9. **No mass assignment** — update schemas enumerate fields;
   `apply_profile_update` cannot touch email/password.
10. **CORS** explicit allow-list, no wildcard origin.
11. **Timing-safe-ish login**: dummy Argon2 verify on unknown email; Argon2id
    defaults; secrets from env only; `.env` git-ignored with `.env.example`
    committed.
12. **Market LLM prompt contains no user-controlled text** (canonical profile
    title only) — shared cache is not injectable; schema bounds the enum
    fields of cached content.
13. **Offline fallback contract** (`engine_used` recorded, fallback computed
    before provider call, all four features) is real and tested.
14. **Frontend tests test behaviour** (roles/labels/live regions, keyboard
    events, error preservation of drafts), doubling as accessibility checks.
15. **The `concurrency = ["greenlet"]` coverage fix** is correct and
    documented; the coverage number it enables is honestly reported.
16. **Docs are unusually honest** — limitations list covers revocation,
    localStorage, rate limiting, SSE single-process, no-Alembic, no-Playwright,
    MySQL-untested; ADRs 0001–0005 match the code (Biome-vs-ESLint deviation
    is justified in the style guide).
17. **Clean worktree hygiene**: coverage artifacts, SQLite files, caches are
    all gitignored and untracked; no temp files or dead scripts committed
    (aside from AR-012/AR-013).

## Executive summary

**Verdict: solid, honest MVP with a disciplined test culture — but not yet
shippable to real students without closing AR-021/AR-023 (secrets, rate
limiting) and re-scoping the rule engine's failure modes.**

| Severity | Count | IDs |
|---|---|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 8 | AR-002, AR-003, AR-004, AR-008, AR-021, AR-023, AR-029, AR-031 |
| P3 | 24 | AR-001, AR-005…AR-007, AR-009…AR-020, AR-022, AR-024…AR-028, AR-030, AR-032 |

- **Total: 32 findings (0 P0, 0 P1, 8 P2, 24 P3)** — every finding has
  file:line evidence; the security and engine findings were reproduced with
  live runs, not conjecture.
- **Security first**: the highest-leverage fix is AR-021 (placeholder secret
  passes the validator) — one denylist check. AR-023 (no throttling) is next.
  Everything else security-related that the code controls (SSE auth, token
  typing, ownership, CORS, SQL, mass assignment) checks out under adversarial
  probing.
- **Dependencies**: backend is fully current; the frontend lockfile has
  accumulated real drift (one unused dep at AR-002, four majors-behind
  toolchains, a tilde-pinned TypeScript 5.9 vs latest 7.0.2) with no
  dependabot/renovate to stop recurrence (AR-006).
- **Correctness**: the ±30-char window (AR-029) demonstrably assigns other
  skills' years/level-words and invents skills (AR-030) — for an assessment
  product this is the most user-visible correctness debt, and the
  limitations doc should say so.
- **Testing**: strong conventional coverage (98.91% with branch, behaviour-driven
  frontend tests), but no property-based or mutation testing yet (AR-031) —
  both are cheap here given the 12.5s suite — and a handful of named
  error paths are untested (AR-032).
- **Process**: 3 doc-drift items (AR-014, AR-015, AR-016) trace to the last
  commit adding the profile page without sweeping the docs; a post-feature
  doc grep (`RouteTitle`, architecture routing, test counts) would have
  caught all three.
