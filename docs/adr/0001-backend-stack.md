# ADR 0001: Backend stack: Python 3.13 + FastAPI, managed with uv

Status: accepted

## Context

The project requires a Python backend with the latest stable tooling,
complete async, and strong quality gates; tooling must be fast and lean.

## Decision

- FastAPI (latest stable) with fully async endpoints on Python 3.13.
- SQLAlchemy 2 async ORM + aiosqlite for development; MySQL-compatible async
  drivers for production (`PRAGATISHALA_DATABASE_URL`).
- Dependencies and environments managed exclusively with **uv**
  (`pyproject.toml` + committed `uv.lock`); no `requirements.txt`, no pip.
- Quality gates: Ruff (lint + format), mypy `--strict` on `app`, pytest with
  `--cov-branch --cov-fail-under=90`.

## Consequences

- `uv sync` reproduces the exact environment in seconds; CI caches it.
- The old `pip install -r requirements.txt` workflow was removed; the
  placeholder `requirements.txt` file was deleted in favour of the lockfile.
- async end-to-end means every DB call must use the async session; the
  `greenlet`-based execution inside SQLAlchemy required
  `coverage concurrency = ["greenlet"]` for truthful coverage measurement.
