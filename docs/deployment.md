# Deployment guide

What a production (or production-like) deployment of PragatiShala must
configure beyond `uv run uvicorn app.main:app`. The codebase is explicitly
single-process (SSE bus and rate limiting keep in-memory state — ADR 0004,
ADR 0007); the guidance here is written for the documented posture: one
process behind a local reverse proxy.

## 1. Run one worker behind a reverse proxy

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Do not raise `--workers`: each process would keep its own rate-limit windows
and SSE subscriber lists, splitting both protections. Horizontal scale is a
roadmap item that requires moving that state to Redis.

## 2. Forward the real client IP

The rate limiter keys buckets on the socket peer (`scope["client"]`). Behind
an unconfiguring proxy, every request would share the proxy's IP and one
bucket — one busy NAT or one attacker locks every student out of
login/register (AR2-009).

Configure the proxy to set `X-Forwarded-For` and make uvicorn trust it only
from that proxy:

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 \
    --proxy-headers --forwarded-allow-ips="127.0.0.1"
```

- `--forwarded-allow-ips` must list ONLY your proxy addresses. Trusting it
  blindly would let attackers mint fresh rate-limit buckets per request.
- Terminate TLS at the proxy; the app should never see raw internet traffic.

## 3. Enforce equivalent limits at the proxy

Defence in depth for the auth and LLM-billed endpoints (nginx example):

```nginx
limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=generation:10m rate=15r/m;

location = /api/v1/auth/login      { limit_req zone=auth burst=5;  proxy_pass http://127.0.0.1:8000; }
location = /api/v1/auth/register   { limit_req zone=auth burst=5;  proxy_pass http://127.0.0.1:8000; }
location = /api/v1/auth/refresh    { limit_req zone=auth burst=5;  proxy_pass http://127.0.0.1:8000; }
location ~ ^/api/v1/(assessments|learning-paths/generate|resumes/generate|market/insights)$ {
    limit_req zone=generation burst=10 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";      # keep SSE streams alive
    proxy_read_timeout 300s;             # SSE keep-alives arrive every 15 s
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

The SSE endpoint (`GET /api/v1/events`) is deliberately unthrottled by the
app; buffering must stay off so keep-alive comments flush (`proxy_buffering
off;` is safe to add for the events location).

## 4. Secrets and environment

- Generate the signing key with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
  The startup validator rejects known placeholders and degenerate keys, but it
  is a sanity floor, not a strength meter — the generator is the control
  (limitations #13).
- Point `PRAGATISHALA_DATABASE_URL` at MySQL (`mysql+aiomysql://…`); the
  SQLite default is for development only (and the MySQL path is currently
  untested — limitations #12).
- Set `PRAGATISHALA_CORS_ORIGINS` to the real frontend origin(s).
- `PRAGATISHALA_MARKET_REFRESH_PER_HOUR` (default 6) caps per-user
  `refresh=true` cache purges on `/market/insights`; `0` disables refresh.
  Each purge triggers a billable LLM call: the per-IP generation limit is the
  outer bound on market LLM spend, and this budget is the per-account bound
  (AR3-006).

## 5. Smoke test the deployment

```bash
scripts/e2e_smoke.sh https://your-host/api/v1
```

The smoke exercises register/login, generation endpoints, a live SSE event,
the market cache, refresh rotation and reuse rejection, and the rate limit —
all against the running deployment.
