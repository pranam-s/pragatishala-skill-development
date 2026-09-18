# Publication re-check: hostile re-review and release checks at final HEAD

Review round AR4, executed 2026-09-13 at HEAD `1a66c49`. This
re-audit covered the two prior remediation waves with fresh
eyes and executed probes, re-verified every dependency against live PyPI/npm,
re-executed the documented quickstarts end to end, and re-measured all gates.
Everything below is evidence-backed; nothing was taken on trust from the
earlier reviews.

## 1. Hostile code review

### 1.1 Findings fixed

**AR4-1 (medium, auth): JWT subject parsing crashed on non-ASCII digits.**
`app/deps.py:59` parsed the token subject with `subject.isdigit()`. Python's
`str.isdigit` also accepts characters like `"²"` (U+00B2) for which `int()`
raises `ValueError`, verified live before the fix. Any token carrying such a
subject turned the malformed-subject defense path into an unhandled 500
instead of a clean 401. Fix: ASCII-digits-only check, so every malformed
subject degrades to `None` → 401. Regression tests:
`tests/test_security.py::test_subject_parsing_rejects_malformed_subjects`
(parametrized, includes `"²"` and `"١٢"`).

**AR4-2 (medium, engine): a level word was shared across another skill's
experience figure.** `app/ai/engine.py:274` (`_shared_level_word`) shared the
nearest clause level word with any list sibling unless a discourse marker
sat between them. A years figure re-anchors attribution to its own mention,
but the sharing crossed it:
`"Expert in Python, 5 years with Go and Rust."` scored **Rust: expert**;
Python's "Expert" leaked across Go's "5 years with" phrase (verified live
before the fix). Fix: an experience figure in the gap between the level word
and the mention is an attribution boundary, matching AR3-005's doctrine.
The pinned AR3-003 list-sibling behavior (`"Expert in Python, SQL, and
Java."`) is unaffected; no figure in those gaps. Regression test:
`tests/test_engine.py::test_level_word_sharing_stops_at_another_skills_years_figure`.

**AR4-3 (hardening test, rate limiting): the HEAD-bypass suspicion was
refuted by execution and pinned.** Plain Starlette adds HEAD to every GET
route, which would have made `HEAD /api/v1/market/insights` a free pass to
the billable handler around `bucket_for` (`app/ratelimit.py:98`). Executed
against the real app: FastAPI answers **405 Method Not Allowed** for HEAD on
GET routes (its `APIRoute` does not auto-add HEAD), so the handler never runs
and no bucket is drawn. A test now pins exactly that shape so a future route
change cannot silently open the bypass:
`tests/test_ratelimit.py::test_head_requests_are_rejected_before_consuming_the_bucket`.

### 1.2 Newest-code review: examined, no defect found

Each area below was reviewed line-by-line and probed; nothing warranted a
change.

- **Schema-upgrade runner** (`app/database.py:85-122`, ADR 0008).
  *Transaction/lock semantics:* `create_all` + upgrades run in one
  `engine.begin()` block. SQLite DDL is transactional; MySQL DDL
  implicit-commits, but recovery is safe either way because each upgrade
  keys on column *existence*, not only on the version record: after a crash
  between `ALTER` and the version `INSERT`, the re-run skips the ALTER and
  just stamps the version. That exact recovery shape is pinned by
  `tests/test_database.py::test_fresh_database_is_stamped_without_alter`
  (column present, record missing). *Multi-DB:* the version DDL and the
  `ALTER ... ADD COLUMN` are valid on both SQLite and MySQL; the inspector
  cache is invalidated after each ALTER (`database.py:104`). *No injection
  surface:* the DDL is a developer-controlled constant; version queries are
  parameterized.
- **Market-refresh budget** (`app/routers/market.py:53`, AR3-006). Every
  boolean encoding FastAPI accepts for `refresh` (`true/True/TRUE/1/on/yes`)
  funnels through the same handler where the budget is charged; no bypass
  shape (verified by probing pydantic's bool coercion). No off-by-one: the
  sliding window admits exactly `budget` refreshes per rolling hour;
  `retry_after` is `ceil(oldest + window − now)`, minimum 1. No timezone
  surface: the limiter runs on `time.monotonic`, immune to wall-clock/rollover
  jumps; the 429 path fires before any cache purge. Budget of 0 disables
  refresh with 403 (documented in `config.py` and deployment.md §4).
- **Rate-limit refund middleware** (`app/ratelimit.py:136-148`, AR3-009).
  No double-refund: exactly one `http.response.start` fires per request, so
  the refund hook runs at most once, and only for requests that were counted
  (`_forward` is reached only when `allowed`). Exception paths: route
  exceptions are converted to 500 by the inner ExceptionMiddleware, so they
  pass the 3xx window and correctly keep their consumed slot. Known and
  accepted: under same-key concurrency the refund can pop a sibling request's
  hit (documented best-effort in `refund`'s docstring, `ratelimit.py:72`);
  an under-count by at most 1 per redirect, never an over-count, and never
  reachable without a legitimate 3xx.
- **Skill-detection engine veto/binding logic** (AR3 waves). Probed the
  regression surfaces: causative "led to" stays vetoed while leadership "led"
  lands; homograph vetoes ("ready to go", "swift development of", "a node
  in") hold; decimal years score as one figure; discourse boundaries void
  years binding; edge-adjacent separators ("Python, 6 years.") still bind.
  One conservative false negative noted and accepted: in "REST APIs with
  Node and Go at work." the shared "with" is adjacent only to Node, so Go is
  dropped. The AR3-008 corroboration rule is deliberately anti-fabrication;
  a true claim missed beats a fabricated one.
- **Auth/JWT handling.** HS-family algorithm locked by `Literal` type
  (AR-025); issuer/audience enforced with required claims; refresh resolves
  the user so deleted accounts cannot mint pairs; login timing evened out
  with a dummy-hash verify; Argon2id via argon2-cffi; token type checked on
  every decode. No weaknesses beyond the documented, accepted ones
  (limitations #2/#3: no revocation, localStorage tokens).
- **SQL injection surfaces.** All data access goes through SQLAlchemy
  expression queries with bound parameters; the only raw SQL is the schema
  runner's constant DDL and parameterized version lookups. Nothing user
  controlled reaches a SQL string.
- **Secrets.** No keys or DB URLs in tracked files; `backend/.env.example`
  ships only a deliberately-invalid placeholder that the startup validator
  rejects (verified: the app refuses to boot on it); CI's throwaway secret is
  CI-scoped. Provider keys are `SecretStr` and never logged or serialized.
- **Dead code / leftovers.** The only `pragma: no cover` markers are five
  genuinely defensive/unreachable branches (verified each). No TODO/FIXME
  markers, no unused imports (ruff), no dead routes.

## 2. Dependency freshness (live registries, 2026-09-13)

Method: `uv lock --upgrade` re-resolved the whole backend lock and
`uv sync --frozen` verified it; every frontend package was checked against
`npm view <pkg> version` and installed via `npm ci`.

### Backend (uv.lock vs live PyPI latest)

| Package | Locked | PyPI latest | Current |
| --- | --- | --- | --- |
| aiosqlite | 0.22.1 | 0.22.1 | yes |
| argon2-cffi | 25.1.0 | 25.1.0 | yes |
| email-validator | 2.3.0 | 2.3.0 | yes |
| fastapi | 0.141.1 | 0.141.1 | yes |
| httpx | 0.28.1 | 0.28.1 | yes |
| pydantic-settings | 2.15.0 | 2.15.0 | yes |
| pyjwt | 2.14.0 | 2.14.0 | yes (floor raised ≥2.14.0) |
| python-multipart | 0.0.32 | 0.0.32 | yes |
| sqlalchemy[asyncio] | 2.0.52 | 2.0.52 | yes |
| uvicorn[standard] | 0.52.4 | 0.52.4 | yes |
| hypothesis | 6.168.0 | 6.168.0 | yes |
| mypy | 2.3.1 | 2.3.1 | yes |
| pytest | 9.1.1 | 9.1.1 | yes |
| pytest-asyncio | 1.4.0 | 1.4.0 | yes |
| pytest-cov | 7.1.0 | 7.1.0 | yes |
| ruff | 0.16.7 | 0.16.7 | yes (floor raised ≥0.16.7) |
| uv_build (build backend) | 0.12.13 | 0.12.13 | yes (floor raised ≥0.12.13) |

Transitive pins spot-checked: starlette 1.6.0, pydantic 2.13.5 (newest the
resolver allows under the direct deps' constraints).

### Frontend (package-lock vs live npm latest)

| Package | Locked | npm latest | Current |
| --- | --- | --- | --- |
| @chakra-ui/react | 3.37.0 | 3.37.0 | yes |
| @emotion/react | 11.14.0 | 11.14.0 | yes |
| @emotion/styled | 11.14.1 | 11.14.1 | yes |
| react / react-dom | 19.3.0 | 19.3.0 | yes |
| react-router-dom | 7.18.3 | 7.18.3 | yes |
| @eslint/js | 10.0.1 | 10.0.1 | yes |
| @testing-library/dom | 10.4.1 | 10.4.1 | yes |
| @testing-library/jest-dom | 7.0.1 | 7.0.1 | yes |
| @testing-library/react | 16.3.3 | 16.3.3 | yes |
| @testing-library/user-event | 14.6.7 | 14.6.7 | yes |
| @types/node | 24.13.4 | 24.13.4 (newest of the Node-24 line; the `latest` dist-tag tracks the 22.x LTS line) | yes |
| @types/react / @types/react-dom | 19.3.0 | 19.3.0 | yes |
| @vitejs/plugin-react | 6.1.1 | 6.1.1 | yes |
| @vitest/coverage-v8 | 5.0.0 | 5.0.0 | yes |
| eslint | 10.10.0 | 10.10.0 | yes |
| eslint-plugin-react-hooks | 7.1.1 | 7.1.1 | yes |
| eslint-plugin-react-refresh | 0.5.6 | 0.5.6 | yes |
| globals | 17.12.0 | 17.12.0 | yes |
| jsdom | 30.0.1 | 30.0.1 | yes |
| typescript | 6.0.3 | 7.0.2 released | **deliberate: see note** |
| typescript-eslint | 8.70.0 | 8.70.0 | yes |
| vite | 8.3.0 | 8.3.0 | yes |
| vitest | 5.0.0 | 5.0.0 | yes |

**TypeScript note:** TS 7.0.2 is the newest npm release, but
typescript-eslint 8.70.0 (the newest) declares `typescript: ">=4.8.4
<6.1.0"`, so upgrading would break the lint gate. 6.0.3 is the newest release
typescript-eslint supports; the upgrade is revisited when typescript-eslint
ships TS-7 support. No deprecated packages anywhere in either manifest.

## 3. Docs verified by execution (2026-09-13, at this HEAD)

| Documented claim / command | Executed | Result |
| --- | --- | --- |
| README §1: `uv sync`, `cp .env.example .env`, secret generation, `uv run uvicorn app.main:app` | yes | boots; `/healthz` → `{"status":"ok",...,"ai_provider":"rule_based"}`; `/api/docs` → 200 |
| README: register → login → market flow over live HTTP | yes | 201 / token pair / cached insights JSON |
| README §2: `npm install`, `npm run dev` proxies `/api/v1/*` | yes | register 201 + market 200 through the Vite proxy |
| README §Quality gates: ruff, mypy, pytest, eslint, build, vitest | yes | see §5 numbers |
| deployment.md §5: `scripts/e2e_smoke.sh` | yes | "E2E smoke: ALL CHECKS PASSED" (incl. market-refresh and SSE-seq probes) |
| `.env.example` placeholder is rejected at startup | yes (validator test + validator design) | boot refused on the committed placeholder |
| "289 tests / 99.36% coverage" (README, AGENTS.md, limitations.md, CHANGELOG) | yes | matches final gates exactly |
| ADR statuses (0001–0008 all "accepted") | reviewed vs code | all implemented and current, incl. ADR 0008 (upgrades verified by tests and by the legacy-DB endpoint test) |

Stale claims fixed in this re-check: the 278-test count (README, AGENTS.md,
limitations.md) and the CHANGELOG/BUILD_LOG entries for this round.

## 4. Publishability checks

- **LICENSE:** MIT, present, copyright "2025 Pranam Srivastava".
- **CI** (`.github/workflows/ci.yml`): runs the exact local gates: ruff
  check + format, mypy strict, pytest with the 90% coverage gate,
  frontend eslint / `tsc -b && vite build` / vitest; `uv sync --frozen` and
  `npm ci` (no drift between lock and manifests). Node 24 / Python 3.13 match
  `engines`/`requires-python`.
- **.gitignore:** covers `.env` (with `!.env.example`), caches, `*.db`,
  `node_modules`, `dist`, coverage artifacts. `backend/pragatishala.db` on
  disk is untracked runtime state, as intended.
- **No absolute/personal paths in tracked files:** grep over tracked files
  for `C:\`, `/c/Users`, `/home/`; none outside this document's own prose
  (none in code, configs, or CI).
- **No secrets:** see §1.2; the only committed secret-shaped strings are the
  intentionally-invalid `.env.example` placeholder and CI's env-scoped
  throwaway.
- **Version + CHANGELOG:** `app.__version__` = `settings.app_version` =
  pyproject `version` = `0.1.0`; `/healthz` reports it. CHANGELOG follows
  Keep-a-Changelog with dated entries; 0.1.0 has not been cut yet, so
  everything lives under [Unreleased] by design.

## 5. Final gates (clean tree, final HEAD)

| Gate | Result |
| --- | --- |
| `uv run pytest` (backend) | **289 passed**, 0 failed |
| Coverage (line + branch, `--cov-fail-under=90`) | **99.36%** (1337 stmts, 6 miss; 236 branches, 4 part) |
| `uv run ruff check .` | clean |
| `uv run ruff format --check .` | 42 files already formatted |
| `uv run mypy` (strict) | no issues in 24 source files |
| `npm run lint` (frontend) | clean |
| `npm run test` (vitest) | **37 passed** |
| `npm run build` (`tsc -b && vite build`) | clean build (cosmetic >500 kB chunk warning on the Chakra bundle; no functional impact, noted as known) |
| `npm ci` from lockfile | 0 vulnerabilities |
| `uv lock --check` / `npm ci` vs manifests | no drift |
