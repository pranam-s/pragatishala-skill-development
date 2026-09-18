# ADR 0004: Realtime: in-process SSE bus, Redis pub/sub later

Status: accepted

## Context

Users should learn when long-running AI work (assessment, path generation,
resume drafting) finishes without polling. Deployment for the MVP is a single
process; multi-instance deployment is not on the table yet.

## Decision

- Server-Sent Events (one GET /api/v1/events stream per authenticated user).
- `EventBus` keeps bounded per-user queues (`asyncio.Queue`, maxsize 100);
  publishes never block and full queues drop events with a warning; REST
  remains the source of truth, so drops are cosmetic, never corrupting.
- Keep-alive comments flow on idle so proxies do not close the stream; the
  generator unsubscribes in a `finally` block on disconnect.

## Consequences

- No external infrastructure (Redis) for the MVP.
- Events are lost on process restart and not delivered across replicas; the
  planned Phase 3 upgrade routes publishes through Redis pub/sub and keeps the
  same SSE contract, so clients and routers do not change.
- SSE (not WebSockets) chosen: unidirectional server→client is all we need,
  and it survives plain-HTTP proxies better.
