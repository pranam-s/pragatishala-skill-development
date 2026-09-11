# ADR 0002 — Authentication: JWT pairs, Argon2id, localStorage tokens

Status: accepted

## Context

The SPA and API are separate apps. We need stateless auth for the MVP with
refresh capability, strong password storage, and a screen-reader friendly
client flow (no silent redirects, explicit error announcements).

## Decision

- OAuth2 password flow (`POST /auth/login` with form credentials) returning an
  access token (30 min) + refresh token (7 days), both HS256 JWTs carrying
  `sub`, `type`, `exp`, `jti` — extended 2026-09 (AR-025) to also carry and
  require `iss`/`aud`/`iat`, with the algorithm pinned to the HS family, so
  tokens minted for another system never validate here.
- Passwords hashed with Argon2id via `argon2-cffi`; unknown accounts perform a
  dummy verify to equalize timing.
- The signing secret must be ≥32 bytes (RFC 7518 for HS256); enforced by a
  `Settings` validator so the app refuses to boot with a weak key (tightened
  by [ADR 0006](0006-jwt-secret-policy.md) with a placeholder denylist and
  entropy floor).
- The SPA stores both tokens in `localStorage` and injects the access token on
  every request; a 401 triggers exactly one refresh + retry. Trade-off: tokens
  are readable by page JS (XSS-amplified). Mitigations for this MVP: strict
  TypeScript, no third-party scripts, no dangerouslySetInnerHTML. HttpOnly
  cookies require same-site deployment and CSRF defence — deferred to Phase 3
  security hardening.

## Consequences

- Any service instance can validate tokens without shared state (horizontal
  scaling friendly).
- Refresh revocation is not implemented (no token denylist); a leaked refresh
  token is valid until expiry. Rotation with server-side revocation is the
  planned upgrade.
- The client refresh logic is fully unit-tested, including the
  "network error must not clear the session" case.
