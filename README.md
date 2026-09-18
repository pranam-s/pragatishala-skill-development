# PragatiShala — AI-Powered Skill Development Platform

PragatiShala helps Indian learners understand where their skills stand and what
to learn next. Describe your experience in plain language and the platform
produces a structured skill assessment, a personalized milestone-based learning
path, an AI-drafted resume, and market insight for your target role.

Designed accessibility-first: every flow is keyboard-operable and screen-reader
friendly (semantic HTML, labelled fields, live regions for status, no
mouse-only interactions).

## Current status (honest)

Last verified 2026-09-18: all gates green from a clean tree — backend
**291 tests passed** (99.33% line+branch coverage, strict mypy, ruff,
deptry, vulture), frontend **37 tests passed** (eslint, `tsc -b`, Knip,
production build). Every feature below was re-exercised over live HTTP and
through the Vite dev proxy on that date; the screenshots in
[docs/screenshots/](docs/screenshots/) come from that run.

What works end-to-end today:

- **User management** — registration, login (OAuth2 password flow), JWT access
  + refresh tokens, profile view/update, logout.
- **Skill assessment** — submit a free-form narrative (20–8,000 chars), get
  detected skills with levels, strengths, gaps, recommended roles, and a
  readiness score.
- **Learning paths** — generate an ordered roadmap (up to 8 modules with
  milestones, estimated hours, resources) from your latest assessment.
- **Resume builder** — generate a structured resume draft from a target role,
  skills, and experience text; list/fetch/update saved resumes.
- **Market insights** — cached market analysis per role family (24-hour cache).
- **Realtime events** — per-user Server-Sent Events stream announcing completed
  assessments, learning paths, and resumes.
- **AI or offline, always working** — if an OpenAI-compatible or Anthropic API
  key is configured, LLM output (strictly schema-validated) powers the
  features; with no keys configured a deterministic rule-based engine takes
  over so every feature works fully offline.

Not built yet (see `docs/roadmap.md`): OAuth social login, multi-language UI,
job-board integrations, Docker/deployment packaging. Schema changes run
through the startup upgrade runner (ADR-0008) rather than Alembic — a
recorded decision, not an omission.

## Tech stack

| Layer    | Choice                                                                |
| -------- | --------------------------------------------------------------------- |
| Backend  | Python 3.13, FastAPI (async), SQLAlchemy 2 async, SQLite/MySQL (async) |
| Auth     | JWT (PyJWT), Argon2id password hashing                                |
| AI       | OpenAI-compatible + Anthropic providers, rule-based offline fallback  |
| Tooling  | uv (deps/lock), Ruff (lint+format), mypy (strict), pytest ≥90% branch coverage |
| Frontend | React 19, TypeScript, Vite 8, Chakra UI v3, React Router 7            |
| Tests    | pytest (backend), Vitest + Testing Library (frontend)                 |

## Getting started

Prerequisites: Python via [uv](https://docs.astral.sh/uv/) and Node.js 24 LTS
(enforced via `engines` in `frontend/package.json`).

### 1. Backend

```bash
cd backend
uv sync                                # creates .venv from uv.lock
cp .env.example .env                   # then set PRAGATISHALA_JWT_SECRET_KEY
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

API docs: <http://127.0.0.1:8000/api/docs> — served only when
`PRAGATISHALA_DEBUG=true` (default off, AR-027); otherwise the Swagger UI and
`/api/openapi.json` return 404.

Generate a dev secret:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The startup validator rejects known placeholders and degenerate keys, but it
is a sanity floor, not a strength meter: always boot from a generated random
key, never from a "strong-looking" hand-made one (see limitations #13).
Production deployments additionally need the reverse-proxy posture described
in [docs/deployment.md](docs/deployment.md).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                            # http://127.0.0.1:5173
```

The dev server proxies `/api/v1/*` to the backend, so no CORS or environment
configuration is needed for local development. For a production build, set
`VITE_API_BASE_URL` to the absolute API base (see `frontend/.env.example`).

### 3. AI providers (optional)

Without API keys everything works offline via the rule-based engine. To enable
LLM features, set exactly one key in `backend/.env`:

```env
PRAGATISHALA_OPENAI_API_KEY=...      # any OpenAI-compatible endpoint
# or
PRAGATISHALA_ANTHROPIC_API_KEY=...
```

Keys are read from the environment only — never hardcoded, never committed.

## Quality gates (all enforced)

```bash
# Backend
cd backend
uv run ruff check app tests && uv run ruff format --check app tests
uv run mypy                     # strict
uv run pytest                   # 291 tests, ≥90% line + branch coverage enforced

# Frontend
cd frontend
npm run lint
npm run build                   # tsc + vite
npm run test                    # 37 tests (Vitest + Testing Library)
```

CI runs the same gates on every push (see `.github/workflows/ci.yml`).

### Property and mutation testing

In addition to the conventional suite, the backend carries hypothesis
property tests (`backend/tests/test_properties.py`) covering JWT round-trips,
readiness-score bounds, rule-engine determinism, scope isolation in the skill
engine, and tolerant LLM-JSON extraction.

Mutation testing was assessed (adversarial review AR-031: ~1,200 statements,
~30 s suite — well within a bounded run) but is **not wired in on this host**:
the current tool, mutmut 3.x, requires process forking and needs WSL on
Windows, while CI runs on Ubuntu where it would work. When a Linux
environment is available:

```bash
cd backend
uv add --group mutation "mutmut>=3.7.0"
# [tool.mutmut] source_paths = ["app/"], pytest_add_cli_args_test_selection = ["tests/"]
uv run --group mutation mutmut run
uv run --group mutation mutmut browse   # triage survivors: fix or justify each
```

This is tracked as follow-up work in `docs/roadmap.md`.

## Project layout

```
backend/
  app/
    ai/          # provider clients + rule-based engine + curated skill data
    routers/     # auth, users, assessments, learning-paths, resumes, market, events
    main.py      # app factory (lifespan, CORS, router wiring)
    config.py    # env-only settings (PRAGATISHALA_* prefix)
    models.py    # SQLAlchemy ORM models
    schemas.py   # Pydantic API schemas
    security.py  # Argon2id hashing + JWT
    services.py  # business logic
    events.py    # in-process SSE event bus
  tests/         # pytest suite (unit + API integration)
frontend/
  src/
    api/         # typed HTTP client + schema types
    auth/        # AuthContext (session bootstrap, login/register/logout)
    components/  # pages, protected routes, navbar/footer
    test/        # test setup + helpers
docs/            # PRD, architecture, ADRs, style guide, limitations, roadmap
```

## Documentation

- [Design (HLD + LLD overview)](docs/design.md)
- [Product requirements](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [ADRs](docs/adr/) — key decisions with context and consequences
- [Style guide](docs/STYLE_GUIDE.md)
- [Limitations](docs/limitations.md) and [roadmap](docs/roadmap.md)
- [Build log](BUILD_LOG.md) and [changelog](CHANGELOG.md)
- [Screenshots](docs/screenshots/) — captured from a real run (2026-09-18)

## Contributing

Issues and PRs welcome. Please run the quality gates locally before pushing;
CI enforces them. Accessibility regressions (mouse-only flows, unlabelled
controls, focus loss) are release blockers.

## License

[MIT](LICENSE)

## CI note (2026-09-16)

GitHub Actions is DISABLED on this repository by owner decision (no paid Actions: the account is billing-blocked and the owner declined spend). Every quality gate was verified by local execution at the recorded HEAD. Zero-cost remote option if ever wanted: a self-hosted runner (re-enable via Settings -> Actions, or gh api -X PUT repos/pranam-s/pragatishala-skill-development/actions/permissions -F enabled=true).
