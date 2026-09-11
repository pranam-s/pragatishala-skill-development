# Architecture

## System overview

```
┌────────────────────┐         ┌──────────────────────────────────────────┐
│ React 19 SPA       │  /api/v1│  FastAPI (uvicorn, single process)       │
│ (Vite build)       │────────>│                                          │
│  - api client      │  JSON + │  routers ──> services ──> SQLAlchemy 2   │
│  - AuthContext     │  SSE    │                │              (async)    │
│  - Chakra UI v3    │<────────│  deps (auth/session/engine/bus)          │
└────────────────────┘         │                                          │
                               │  SkillEngine ──> LLM provider (optional) │
                               │       │        └──> rule-based fallback  │
                               │       v                                  │
                               │  EventBus (in-process) ──> SSE streams   │
                               └──────────────┬───────────────────────────┘
                                              v
                                    SQLite (dev) / MySQL (prod)
```

## Backend

### Layers

- **routers/** — HTTP concerns only: status codes, error mapping, response
  schemas. No business logic.
- **services.py** — business logic: ownership checks, persistence, event
  publishing. Raises domain errors (`NotFoundError`,
  `AlreadyRegisteredError`, …) that routers translate to HTTP.
- **models.py / schemas.py** — persistence (SQLAlchemy) and transport (Pydantic)
  contracts, kept separate; `model_validate` converts at the boundary.
- **deps.py** — dependency wiring: DB session, current user, skill engine,
  event bus. Handlers declare what they need via `Annotated` aliases.

### The SkillEngine (AI + offline)

`SkillEngine` wraps an optional `LLMProvider`. Each feature method
(`analyze_skills`, `build_learning_path`, `generate_resume`, `market_insights`)
follows one contract:

1. Compute the deterministic fallback from `app/ai/skills_data.py`.
2. If a provider is configured, ask it for STRICT JSON matching the Pydantic
   schema; validate; on any failure log a warning and use the fallback.
3. Return `(value, engine_used)` so persistence records which path produced it.

Providers: `OpenAICompatibleProvider` (OpenAI, Azure gateways, Gemini's
OpenAI-compatible endpoint, Groq, OpenRouter, Ollama, vLLM via `base_url`) and
`AnthropicProvider` (Messages API). Both tolerate markdown-fenced JSON and are
unit-tested with mocked HTTP transports. API keys come from the environment
only (`build_provider` reads `Settings`).

### Auth

- Passwords: Argon2id (`argon2-cffi`), constant-shape verification; unknown
  accounts burn a hash comparison to avoid user-enumeration timing leaks.
- Tokens: HS-family JWTs (HS256 by default; `jwt_algorithm` is pinned to
  HS256/HS384/HS512) carrying `sub` (user id), `type` (access|refresh), `exp`,
  `iat`, `jti`, `iss`, `aud`. `decode_token` enforces issuer and audience,
  requires those claims plus `exp`/`iat`/`sub`/`jti`, and rejects wrong types,
  expired/invalid tokens, and missing subjects. The signing secret must be
  ≥32 bytes with an entropy floor (enforced in `Settings`,
  [adr/0006](adr/0006-jwt-secret-policy.md)).
- Endpoints: `POST /auth/register`, `POST /auth/login` (OAuth2 form),
  `POST /auth/refresh`, `GET /auth/me`, `GET/PATCH /users/me`.

### Realtime

`EventBus` is an in-process, per-user fan-out of bounded queues (full queues
drop events — REST is the source of truth). `GET /api/v1/events` streams SSE
frames with keep-alive comments and unsubscribes on disconnect. Single-process
by design for the MVP; see [adr/0004](adr/0004-realtime.md).

### Database

Async SQLAlchemy 2 with aiosqlite (dev) / MySQL drivers (prod). Tables: users,
assessments, learning_paths, resumes, market_reports (role-unique cache).
Startup runs idempotent `create_all`; migrations are a deliberate
post-MVP step ([adr/0003](adr/0003-database-migrations.md)).

## Frontend

- **api/client.ts** — typed fetch wrapper: injects the bearer token, retries
  once through `/auth/refresh` on 401, parses FastAPI error details into
  `ApiError`. Base URL defaults to `/api/v1` (Vite proxy in dev).
- **AuthContext** — session bootstrap (`me()` on mount when a token exists),
  login, registration (auto sign-in), logout. Tokens persist in localStorage
  ([adr/0002](adr/0002-authentication.md)).
- **Routing** — public (`/`, `/login`, `/register`) and authenticated
  (`/assessment`, `/learning-path`, `/profile`) routes; `ProtectedRoute` redirects
  anonymous visitors to `/login` with a `from` location for return.
- **Accessibility** — Chakra `Field` label association, `role="alert"` error
  regions, `aria-live="polite"` status regions, `aria-current="page"` nav,
  real buttons/links, visible focus, no mouse-only affordances.

## Cross-cutting decisions

- Errors: domain exceptions in services → `HTTPException` mapping in routers;
  no raw exceptions cross the HTTP boundary.
- Configuration: one `Settings` class, `PRAGATISHALA_`-prefixed env vars,
  validators enforce invariants (positive TTLs, strong secret).
- Determinism: the offline engine is pure functions over curated data — the
  entire platform is demonstrable with zero network access.
