# PragatiShala — AI-Powered Skill Development Platform

PragatiShala helps Indian learners understand where their skills stand and what
to learn next. Describe your experience in plain language and the platform
produces a structured skill assessment, a personalized milestone-based learning
path, an AI-drafted resume, and market insight for your target role.

Designed accessibility-first: every flow is keyboard-operable and screen-reader
friendly (semantic HTML, labelled fields, live regions for status, no
mouse-only interactions).

## Current status (honest)

What works end-to-end today (verified over live HTTP and through the Vite dev
proxy):

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
job-board integrations, Docker/deployment packaging, Alembic migrations.

## Tech stack

| Layer    | Choice                                                                |
| -------- | --------------------------------------------------------------------- |
| Backend  | Python 3.13, FastAPI (async), SQLAlchemy 2 async, SQLite/MySQL (async) |
| Auth     | JWT (PyJWT), Argon2id password hashing                                |
| AI       | OpenAI-compatible + Anthropic providers, rule-based offline fallback  |
| Tooling  | uv (deps/lock), Ruff (lint+format), mypy (strict), pytest ≥90% branch coverage |
| Frontend | React 19, TypeScript, Vite 7, Chakra UI v3, React Router 7            |
| Tests    | pytest (backend), Vitest + Testing Library (frontend)                 |

## Getting started

Prerequisites: Python via [uv](https://docs.astral.sh/uv/) and Node.js ≥ 20.

### 1. Backend

```bash
cd backend
uv sync                                # creates .venv from uv.lock
cp .env.example .env                   # then set PRAGATISHALA_JWT_SECRET_KEY
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

API docs: <http://127.0.0.1:8000/api/docs>

Generate a dev secret:

```bash
uv run python -c "import secrets; print(secrets.token_urlsafe(48))"
```

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
uv run pytest                   # 146 tests, ≥90% line + branch coverage enforced

# Frontend
cd frontend
npm run lint
npm run build                   # tsc + vite
npm run test                    # 36 tests (Vitest + Testing Library)
```

CI runs the same gates on every push (see `.github/workflows/ci.yml`).

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

- [Product requirements](docs/PRD.md)
- [Architecture](docs/architecture.md)
- [ADRs](docs/adr/) — key decisions with context and consequences
- [Style guide](docs/STYLE_GUIDE.md)
- [Limitations](docs/limitations.md) and [roadmap](docs/roadmap.md)
- [Build log](BUILD_LOG.md) and [changelog](CHANGELOG.md)

## Contributing

Issues and PRs welcome. Please run the quality gates locally before pushing;
CI enforces them. Accessibility regressions (mouse-only flows, unlabelled
controls, focus loss) are release blockers.

## License

[MIT](LICENSE)
