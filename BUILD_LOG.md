# Build log

Honest, reverse-chronological log of significant work sessions.

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
