# ADR 0003 — Database: create_all now, Alembic later

Status: accepted

## Context

The MVP schema is still moving (assessments, learning paths, resumes, and the
market cache were all added in the first two phases). Migration tooling adds
process weight that a pre-release project cannot monetize yet.

## Decision

- Dev/MVP startup runs idempotent `Base.metadata.create_all` inside the app
  lifespan.
- SQLite (via aiosqlite) is the default development database; production
  targets MySQL through an async driver via `PRAGATISHALA_DATABASE_URL`.
- Introduce Alembic at the first destructive schema change or before the first
  production deployment, whichever comes first.

## Consequences

- Fresh environments bootstrap with zero commands beyond `uv sync`.
- Schema changes that alter existing columns are NOT handled by create_all;
  during development, delete the dev SQLite file instead of fighting drift.
- The lifespan owns engine setup and disposal, which keeps tests
  hermetic (each test gets a fresh temporary database).
