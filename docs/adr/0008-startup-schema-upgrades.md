# ADR 0008 — Startup schema upgrades (create_all + versioned ALTERs)

Status: accepted

## Context

`model_used` was added to the existing `market_reports` table (AR2-014), but
`Base.metadata.create_all` never alters existing tables: on any pre-upgrade
database the ORM SELECT on `market_reports` fails and every
`/market/insights` request 500s (AR3-007). ADR 0003 defers Alembic to the
first destructive schema change or the first production deployment; that
trigger has not fired yet (this change is additive), but "delete the dev
database" is not an upgrade story for deployments that keep data.

## Decision

- `init_db` runs `create_all` and then applies a small, append-only list of
  versioned column upgrades (`SCHEMA_UPGRADES` in `app/database.py`).
- Each upgrade applies only when its column is missing, and is recorded in a
  `schema_upgrades` table; databases that already conform are stamped so the
  column check is paid once.
- Upgrades run through the same async engine as the app, so they are valid
  for SQLite (dev) and MySQL (production) alike.

## Consequences

- Pre-upgrade databases are upgraded automatically at startup; no manual
  ALTER is required (deployment.md documents the equivalent SQL for
  externally managed databases).
- Alembic remains deferred per ADR 0003's trigger; adopting it then means
  stamping the baseline and porting `SCHEMA_UPGRADES` into revisions.
