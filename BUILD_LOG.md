# Build log

Honest, reverse-chronological log of significant work sessions.

## 2026-09-14 — AR-027 information-exposure fix (quick win)

- **Fix:** `/healthz` returned the active AI provider, app version, and debug
  flag to unauthenticated callers, and `/api/docs` + `/api/openapi.json` were
  always public (AR-027 from `docs/ADVERSARIAL-REVIEW.md`). Now `/healthz`
  answers only `{"status":"ok"}` and the docs/schema endpoints 404, unless
  `PRAGATISHALA_DEBUG=true` (default off) opts the operator back in —
  `create_app` wires `docs_url`/`openapi_url` from that flag, and the healthz
  handler branches on it per request.
- **Tests:** posture tests for both surfaces in both postures — minimal
  healthz by default, diagnostics opt-in, uninitialized-engine diagnostics,
  docs/schema hidden by default, docs/schema available in debug. Backend:
  291 tests (was 289), 99.37% line+branch coverage (was 99.36%).
- **Docs synced:** README (API-docs note + counts), AGENTS.md, CHANGELOG,
  `docs/limitations.md`, `docs/roadmap.md` (Ops row: exposure resolved; the
  production guide only needs the "never enable debug in production" note,
  added to `docs/deployment.md` §4), `backend/.env.example`.
- Gates at close: pytest 291 passed (99.37% line+branch), ruff check/format
  and mypy strict clean.

## 2026-09-13 — Publication re-pass at final HEAD (fourth pass, AR4)

- **Hostile re-review at HEAD `1a66c49` with executed probes**, focused on the
  AR2/AR3 remediation waves (schema-upgrade runner, market-refresh budget,
  refund middleware, engine veto/binding logic). Two real findings fixed with
  regression tests, one suspicion refuted and pinned instead:
  - `deps.user_id_from_subject` crashed with `ValueError` on non-ASCII digit
    subjects ("²" passes `str.isdigit`, `int()` rejects it) — the
    malformed-subject defense path turned into a 500; now ASCII-digits-only.
  - `engine._shared_level_word` shared a clause's level word across ANOTHER
    skill's experience figure ("Expert in Python, 5 years with Go and Rust."
    scored Rust expert); a years figure in the gap is now an attribution
    boundary, consistent with AR3-005's doctrine.
  - HEAD-rate-limit bypass suspicion was refuted by execution: FastAPI
    returns 405 for HEAD on GET routes (no auto-HEAD like plain Starlette),
    so the handler never runs; a test pins the 405 and proves the bucket is
    not consumed. Full findings incl. explicitly empty categories:
    [docs/PUBLICATION-PASS.md](docs/PUBLICATION-PASS.md).
- **Dependencies re-verified against live PyPI/npm** (2026-09-13): everything
  locked at the newest release; stale floors raised (pyjwt ≥2.14.0,
  ruff ≥0.16.7, uv_build ≥0.12.13). TypeScript stays on 6.0.3 —
  typescript-eslint 8.70.0 peers `typescript <6.1.0`, so TS 7.0.2 is
  ecosystem-blocked.
- **Docs verified by execution:** README quickstart (uv sync → .env →
  uvicorn → healthz/docs/register/login/market), the Vite dev-proxy path
  (register 201 + market 200 through :5174), and the full
  `scripts/e2e_smoke.sh` (ALL CHECKS PASSED, including the AR3 market-refresh
  and SSE-seq probes). Stale test counts synced to 289 (README, AGENTS.md,
  limitations.md, CHANGELOG).
- Gates at close: pytest 289 passed (99.36% line+branch), ruff check/format
  and mypy strict clean; frontend eslint clean, 37 vitest passed, tsc+vite
  build clean.

## 2026-09-12 — Third adversarial pass (AR3) remediation

- **Review:** [docs/ADVERSARIAL-REVIEW-3.md](docs/ADVERSARIAL-REVIEW-3.md)
  attacks the AR2-fix wave itself: 11 findings (1 high, 6 medium, 4 low),
  every claim verified by executed probes. Headline: the AR2 ambiguity gate
  matched on `text.lower()`, erasing the led/LED distinction, so "I led the
  migration and I am an expert in Python." scored no Leadership at all.
- **Remediation:** one conventional commit per finding, each with regression
  tests built from the review's repro strings (verified red before the fix):
  led/LED case disambiguation (AR3-001), decimal years + decimal-point
  sentence splits (AR3-002), clause-level word shared across list siblings
  (AR3-003), homograph sense vetoes/cues for go/cv/lambda/swift/node
  (AR3-004), discourse boundaries in years proximity + budget 4→6 (AR3-005),
  per-user market-refresh budget (AR3-006), versioned startup schema
  upgrades + ADR-0008 (AR3-007), weak preceders need corroboration (AR3-008),
  3xx redirect refund in the rate limiter (AR3-009), smoke refresh probe +
  60 s re-run cool-down (AR3-010), asp.net C# alias (AR3-011).
- Deviations recorded in the review's resolution table: AR3-006 solved with
  a per-user budget instead of staff-role gating (no role model exists);
  AR3-007 solved with startup upgrades instead of Alembic (ADR-0003's
  trigger has not fired); AR2-004's committed SQL=beginner expectation
  flipped to expert per AR3-003.
- Gates at close: pytest 278 passed (99.36% line+branch), ruff check/format
  and mypy strict clean; frontend untouched (37 vitest tests).

## 2026-09-11 → 2026-09-12 — Adversarial-review remediation and publication finalization

- **Remediation pass:** all 32 findings (AR-001..AR-032) from
  [docs/ADVERSARIAL-REVIEW.md](docs/ADVERSARIAL-REVIEW.md) fixed across
  security (secret policy, rate limiting, JWT claims, prompt fencing),
  engine correctness (sentence-scoped scoring, ambiguous aliases), deps,
  tests, and docs — see the review doc and CHANGELOG for the full record.
  Suite grew to 199 tests at 99.28% line+branch; frontend to 37 tests.
- **Finalization pass (publication readiness):** hostile re-read of the
  remediated codebase found two new items, both fixed:
  - AR-033 — the readiness score's "soft bonus" counted *missing*
    recommended skills (extra adjacent knowledge could lower a score); it
    now counts recommended skills actually covered, with a regression test.
  - AR-034 — frontend minors drifted again (Chakra 3.29 → 3.37, React
    19.3, @types refresh); backend `uv lock --upgrade` re-verified current.
    TypeScript stays ^6.0.3: typescript-eslint 8.70.0 peer-caps TS <6.1.0.
- Docs swept against reality: architecture auth section (AR-025 claims),
  PRD (rate limiting shipped), style guide (ESLint 10), ADR 0002 amended,
  counts synced everywhere (200 backend / 37 frontend), Vite 8, Node 24
  `engines`.
- Re-verified end to end: `uv sync --frozen`, uvicorn boot, full e2e smoke
  (`scripts/e2e_smoke.sh`) ALL CHECKS PASSED over live HTTP, the same
  register flow through the Vite 8 dev proxy, `index.html` given a real
  title + description (was the Vite scaffold default).
- Gates at close: pytest 200 passed (99.28%), ruff + mypy strict clean;
  vitest 37 passed, ESLint + `tsc -b` + vite build clean.

## 2026-09-10 → 2026-09-11 — Backend completion, frontend wiring, revival (unlimited window 22:00–06:30 IST)

Starting state: last real commit was the frontend-only setup ("backend blocked
due to an environment issue"); a hygiene commit (`8e750df`) had removed Vite
cache artifacts; untracked in-progress backend scaffolding existed
(`backend/app/`, `pyproject.toml`, `uv.lock`) from an interrupted session.

### Backend (commit 167222f)

- Audited the untracked scaffolding: routers, services, models, schemas,
  security, AI provider/engine/skills data were present and well-formed; the
  missing pieces were the app factory, tests, and several wiring bugs.
- Fixed: `routers/health.py` read the event bus instead of the skill engine;
  `routers/events.py` referenced a non-existent `sse_keepalive_seconds`
  setting; `OAuth2PasswordRequestForm` needed `Annotated[..., Depends()]` for
  the installed FastAPI; `email-validator` and `python-multipart` were missing
  from dependencies (EmailStr + form login crashed on import).
- Added `app/main.py` (app factory: lifespan-managed engine, `init_db`, CORS,
  `/api/v1` router wiring) and turned the tracked `main.py` placeholder into a
  thin re-export; deleted the misleading `requirements.txt` (uv + lockfile is
  the dependency path).
- Enforced a ≥32-byte JWT secret in `Settings` (RFC 7518; PyJWT warns
  otherwise).
- Improved the rule-based engine: proficiency words and experience figures now
  only count within a ±30-char window around a skill mention — previously
  "proficient in SQL" upgraded unrelated skills mentioned anywhere in the text.
- Removed a dead branch in provider JSON extraction (a `{...}` substring can
  only parse to a dict).
- Wrote the test suite: 146 tests (config, security, event bus, database,
  auth/users/assessments/learning-paths/resumes/market APIs, SSE, engine,
  providers incl. mocked HTTP, services, app factory/CORS/openapi, lifespan).
- **The coverage hunt:** endpoint bodies tested green but reported as
  uncovered. Bisected with settrace probes to SQLAlchemy's greenlet switches
  disarming the tracer mid-run. Fix: `coverage concurrency = ["greenlet"]` in
  pyproject — coverage jumped from a false 89% to a true 98.9%. Documented in
  limitations.
- Gates: ruff check + format clean, mypy strict clean, pytest 146 passed,
  98.91% line+branch.

### Frontend (commit 372ba6c)

- Found the "working" frontend did not compile: components used Chakra UI v2
  APIs against a v3 install (`FormControl`, `useToast`, `Stack spacing`,
  `colorScheme`), imported a non-installed `react-icons` package, and
  `ChakraProvider` lacked its required `value`. The prior "dev server running"
  status claim was inaccurate — nothing had ever been built.
- Rewrote all pages for Chakra v3 and wired them to the real API:
  - `api/client.ts`: typed fetch client, bearer injection, single-retry
    refresh on 401, FastAPI detail parsing, relative `/api/v1` base proxied by
    Vite in dev.
  - `AuthContext`: token bootstrap on mount, login, register (auto sign-in),
    logout; guarded `useAuth`.
  - Login/Registration: controlled forms, Chakra `Field` label association,
    `role="alert"` errors, autocomplete attributes, loading states.
  - SkillAssessment/LearningPath: real API calls, `aria-live` progress,
    ordered accessible module lists, resource links.
  - Router: protected routes with redirect-back, `aria-current` nav, real
    logout button.
- Tooling: Vitest + Testing Library + jest-dom; 31 tests covering the client
  (including refresh-failure and transient-network cases), auth context,
  protected routes, and all wired pages. `tsc` strict and ESLint clean.
- Follow-up (same window): added `RouteTitle` (+2 tests, 33 total) so screen
  readers regain page-change context via `document.title`; added
  `scripts/e2e_smoke.sh` encoding the verified live-HTTP journey.

### E2E verification

- Ran uvicorn + `npm run dev`; exercised register → login → me → assessment →
  learning path → resume → market → refresh → 401/409 error paths over real
  HTTP, and the same login through the Vite proxy. All passed. Servers
  stopped afterwards.

### Toolchain notes for future sessions

- `uv sync` reinstalls the project wheel on each run — fine, editable .pth
  resolves to the working tree.
- Pytest config lives in `backend/pyproject.toml` (asyncio auto, coverage
  fail-under 90, filterwarnings=error — new warnings WILL fail CI).
- On this machine `python` is not on PATH; use `uv run python` or the venv's
  `python.exe`.
