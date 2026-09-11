# Style guide

Applies to the whole repository. CI enforces the mechanical parts; review the
judgement parts.

## Backend (Python 3.13, FastAPI)

### Formatting and linting

- Ruff is the only formatter/linter. Line length 100. Rules: pycodestyle,
  pyflakes, isort, bugbear, pyupgrade, simplify, RUF, ASYNC, bandit (S), C4,
  PIE, RET, PTH. `S101` (assert) is allowed project-wide; `S105/S106/S107` are
  allowed only in `tests/` for hardcoded test credentials.
- `mypy --strict` must pass on `app/` with the pydantic plugin. No new
  `# type: ignore` without a justification comment.

### Code organization

- Routers: HTTP concerns only (status codes, error mapping). Domain errors are
  raised by `services.py` and translated at the boundary.
- Dependencies are declared with `Annotated` aliases (`SessionDep`,
  `CurrentUser`, `EngineDep`, `BusDep`) — never inline `Depends(...)` chains.
- All settings flow through `app.config.Settings` with the
  `PRAGATISHALA_` env prefix. No `os.environ` reads outside config (tests may
  bootstrap env before import).
- Secrets never appear in code, defaults, or tests. Everything user-visible in
  config is prefixed and documented in `backend/.env.example`.
- Docstrings: one-line summary for every public module, class, and function.
- Async all the way: no blocking calls inside `async def` handlers.

### Tests (pytest)

- Function-scoped isolation: every test gets a fresh database and settings via
  the autouse fixture in `tests/conftest.py`.
- API tests go through `httpx.ASGITransport`; SSE is tested by driving the
  endpoint generator directly (ASGI transport buffers infinite streams).
- Coverage: `--cov-branch --cov-fail-under=90` on `app`; currently ~99%.
  Add `# pragma: no cover - <reason>` only for defensive branches.
- Test names state behaviour: `test_<thing>_<expected_outcome>`.

## Frontend (React 19, TypeScript, Chakra UI v3)

### Tooling

- ESLint 10 flat config + `typescript-eslint` + react-hooks/react-refresh
  plugins; `tsc -b` strict. (Biome was considered; ESLint was already
  configured with the needed React plugins — one linter, used deeply.)
- Vitest + Testing Library. Query by role/label (never test-id) so tests
  double as accessibility checks.

### Components

- Function components with typed props. Pages default-export from
  `src/components/<Name>.tsx`; co-located `<Name>.test.tsx`.
- Chakra v3 only: `Field.Root/Label` for form association, `NativeSelect.Root`
  for selects, `gap` (not the removed `spacing`), `colorPalette` (not
  `colorScheme`), `Link asChild` wrapping a router `Link` for navigation.
- Data fetching lives in `src/api/client.ts`; components call `api.*` inside
  event handlers/effects and own their loading/error state.

### Accessibility (release-blocking)

- Every input has a programmatic label; helper text via `Field.HelperText`.
- Errors render in a `role="alert"` region; long-running work announces in an
  `aria-live="polite"` region.
- Navigation state is exposed with `aria-current="page"`; logout is a real
  `<button>`; all functionality reachable by keyboard in DOM order.
- `autocomplete` attributes on credential fields (`email`, `current-password`,
  `new-password`, `name`).

### Error handling

- API failures surface the backend `detail` message in the page's alert
  region; forms never clear user input on failure.
- The API client retries exactly once via refresh on 401; transient network
  failures during refresh must not clear stored tokens.

## Commits

Conventional commits: `feat|fix|chore|docs|test|refactor(scope): summary`.
Keep summaries imperative and ≤72 chars; commit early and often.
