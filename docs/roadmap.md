# Roadmap

Ordered by value per unit of risk. Items move to ADRs/PRD when they start.

## Phase 3 — Platform enhancement (next up)

1. **Security hardening**
   - ~~Rate limiting on auth endpoints~~ — shipped: in-process sliding-window
     middleware on the auth + LLM-billed endpoints (ADR 0007); multi-worker
     deployments still need proxy-level limits.
   - Refresh-token rotation with server-side revocation (denylist table).
   - Password reset + email verification (requires an email transport choice).
   - Move tokens to HttpOnly cookies behind same-site deployment + CSRF defence.
2. **Migrations** — introduce Alembic before any destructive schema change
   (ADR 0003 exit condition).
3. **Realtime at scale** — Redis pub/sub behind the existing `EventBus`
   interface for multi-instance deployments (ADR 0004 exit condition).
4. **Browser e2e** — Playwright suite covering register → assess → learning
   path; includes a keyboard-only pass. Schedule a manual NVDA pass per
   release.
5. **Mutation testing in CI** — hypothesis property tests have shipped
   (`backend/tests/test_properties.py`); mutmut 3.x needs a Linux/WSL
   environment (fork support), so wire `mutmut run` into the GitHub Actions
   workflow and triage survivors.

## Phase 4 — Product depth

- **Progress tracking** — assessment history diffs, readiness trend charts
  (must remain screen-reader friendly: provide tabular alternatives).
- **Interview prep** — generated question banks from assessment gaps.
- **Job-board integration** — scrape/match postings against detected skills
  (needs a legal/ToS review per source).
- **Multi-language UI** — i18n framework plus Hindi/regional translations of
  the (small) UI string surface; AI features accept any input language already.
- **Resume export** — PDF/DOCX rendering of the structured resume JSON.
- **Admin/analytics console** — aggregate, privacy-preserving usage metrics.

## Ops

- Dockerfile + compose for one-command full-stack bring-up.
- MySQL integration tests in CI (service container).
- Production deployment guide (reverse proxy, TLS, SSE buffering caveats —
  `X-Accel-Buffering: no` is already set). Information exposure is already
  hardened in code (AR-027, shipped 2026-09-14): `/healthz` returns only
  `{"status":"ok"}` unless `PRAGATISHALA_DEBUG=true`, and `/api/docs` +
  `/api/openapi.json` are served only in debug mode — the guide just needs
  to say "never enable debug mode in production".
