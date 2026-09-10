# Build log

Honest, reverse-chronological log of significant work sessions.

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
