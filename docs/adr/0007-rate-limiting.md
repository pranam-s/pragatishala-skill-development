# ADR 0007: In-process sliding-window rate limiting

Status: accepted

## Context

Auth endpoints (`/auth/login`, `/auth/register`, `/auth/refresh`) had no
throttling, enabling unlimited password guessing and account enumeration.
The LLM-billed endpoints (`POST /assessments`, `POST /learning-paths/generate`,
`POST /resumes/generate`, `GET /market/insights` on a cold cache) were
unthrottled too: with a provider key configured, scripted access converted
into an open tap on the operator's LLM budget (adversarial review AR-023).

FastAPI has no official rate-limiting story; `slowapi` (0.1.10) is a thin
wrapper adding a dependency for what is ~80 lines here. The platform is
explicitly single-process (SSE bus, in-memory state; see ADR 0004 and
limitations), so distributed coordination is not currently needed.

## Decision

A dependency-free, pure-ASGI middleware (`app/ratelimit.py`) enforces a
sliding-window limit per client host and per bucket:

- **auth bucket**: login, register, refresh; default 10 requests/minute.
- **generation bucket**: the four LLM-billed routes above; default
  15 requests/minute (exact routes only; list/read paths stay unthrottled).

Properties:

- Requests are counted in a monotonic-clock sliding window; the oldest hit
  leaves the window before capacity is granted again. The N+1th request gets
  `429` with a `Retry-After` header (seconds until capacity frees).
- Limits come from `Settings` (`PRAGATISHALA_AUTH_RATE_LIMIT_PER_MINUTE`,
  `PRAGATISHALA_GENERATION_RATE_LIMIT_PER_MINUTE`, resolved per request);
  `0` disables a bucket.
- The middleware is a plain ASGI callable: the SSE stream and everything
  outside the rule table passes through untouched (no response buffering).
- It sits *inside* the CORS middleware so 429 responses still carry CORS
  headers and the SPA can read the `detail`.
- Clients are keyed by the ASGI `scope["client"]` host. `X-Forwarded-For` is
  deliberately ignored: trusting spoofable headers would let attackers mint
  fresh buckets.

## Consequences

- Same single-process scope as the SSE bus: with multiple workers each
  process enforces its own window. Production deployments behind a reverse
  proxy should enforce equivalent limits there (nginx `limit_req` etc.);
  The deployment guidance this ADR deferred to now exists: see
  [deployment.md](../deployment.md) (single worker, real-IP forwarding,
  proxy-level limits, SSE-safe buffering).
- Per-IP keying means many legitimate students behind one NAT share a
  bucket; defaults (10 auth/min) are set well above interactive use.
- In-memory state: limits reset on restart. That is acceptable for
  brute-force slowdown and budget protection, not for auditing; token
  revocation/lockout remains roadmap security work (see ADR 0002).
