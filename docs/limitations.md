# Limitations and evaluation

Honest assessment of what this codebase does well and where it falls short.
Last updated: 2026-09-12.

## What is solid

- **Backend correctness.** 232 tests, 99.3% line and branch coverage on `app`
  (≥90% enforced in CI), strict mypy, Ruff clean. API tests exercise the real
  app (auth, ownership boundaries, validation, error paths) over ASGI.
- **End-to-end verified.** The full journey (register → login → assessment →
  learning path → resume → market → refresh → SSE) was exercised over live
  HTTP, and through the Vite dev proxy exactly as the SPA calls it.
- **Offline-first AI.** Every AI feature degrades deterministically; responses
  record `engine_used`. Provider clients handle fenced JSON, bad bodies, HTTP
  errors, and schema-invalid output with tests for each.
- **Accessibility.** All interactive flows are labelled, keyboard-operable, and
  announce errors via `role="alert"`; the primary user is an NVDA user and the
  author treats a11y regressions as release blockers.

## Known limitations

1. **Coverage measurement needed `concurrency = ["greenlet"]`.** Without it,
   SQLAlchemy's greenlet switches silently disarmed the tracer and ~10% of
   executed lines went unmeasured (misleadingly LOW numbers, not high). If you
   add new async/sqlalchemy machinery, re-check that endpoint bodies still
   appear in coverage.
2. **JWTs are not revocable.** No denylist; a stolen refresh token works until
   expiry (7 days). Rotation/revocation is planned (see ADR 0002).
3. **Tokens in localStorage.** XSS-amplified risk accepted for the MVP; no
   third-party scripts ship, but HttpOnly cookies + CSRF defence is the real
   fix (roadmap).
4. **Rate limiting is single-process; no account recovery.** Login/register/
   refresh and the LLM-billed endpoints are throttled per client IP
   (in-process sliding window, ADR 0007), but a multi-worker deployment needs
   proxy-level limits; limits reset on restart. There is no email
   verification, password reset, or account lockout.
5. **Rule-based quality is heuristic.** The offline engine scores each skill
   mention within its own sentence (level words and year figures bind to the
   clause they appear in, and year figures must sit within a few tokens of the
   mention) and rejects homograph aliases ("go", "c", "node", "swift",
   "cv", ".net", "lambda") unless skill-talk evidence sits near the word;
   lowercase "led" is treated as the leadership verb it almost always is, so
   only the all-caps acronym ("LED lights") is gated (AR3-001). It
   is deliberately conservative: it will miss unusual phrasings (e.g. "I use
   Go" with no skill-context word nearby) and unqualified claims default to
   beginner. Two precision limits remain: a proficiency word between two
   mentions in one clause can bind to both, so reported speech ("Dr. Smith
   says I led the migration and I am an expert in Python") scores like a
   direct claim, and the
   ±24-character context window is a heuristic, not parsing. A few everyday
   constructions are hard-vetoed near a homograph (the "go" infinitive, "the
   swift development of …", article usage before "node", hyphen compounds
   like "go-to"), and "cv"/"lambda" additionally require domain cues nearby
   (vision terms; aws/serverless) — which costs legitimate phrasings such as
   "Go-based services" or an unqualified "I write lambdas"
   (AR3-004). `engine_used`
   tells you when you are reading its output.
6. **LLM prompt-injection defences are minimal.** User text is fenced in
   `<user_data>` tags and system prompts instruct the model to treat that
   content as data, but a determined injection can still try to skew the
   model's prose. Blast radius is bounded: output is schema-validated and
   rendered only back to the injecting user, and the shared market cache is
   never fed user text.
7. **Single-process SSE.** Events do not cross process boundaries and are lost
   on restart (ADR 0004). REST is the source of truth.
8. **No Alembic migrations.** Destructive schema changes during development
   currently mean deleting the dev database (ADR 0003).
9. **Market data is curated, not live.** Offline market snapshots are hand
   written INR ranges; only the LLM path can give fresher (still unverified)
   figures. No job-board integrations yet.
10. **Frontend coverage focuses on logic.** The API client, auth context, and
   page behaviour are tested (37 tests); Navbar/Footer/route table are UI glue
   deliberately left unmeasured — they contain no logic beyond markup. The
   ≥90% rule is enforced on the backend `app` package; frontend coverage is
   reported but not gated, with this justification.
11. **No browser-level e2e (Playwright) yet.** Backend e2e runs over real HTTP
   and frontend flows are tested with jsdom; a Playwright suite (including a
   screen-reader smoke pass) is roadmap work.
12. **MySQL path is untested.** The connection string is supported, but CI runs
   SQLite only.
13. **The JWT-secret validator is a floor, not a strength meter.** The
   placeholder denylist (now substring-matched) catches copied examples, and
   the entropy floor kills degenerate keys ("xxxx…", "abab…"), but per-character
   Shannon entropy measures histogram flatness, not guessability: a keyboard
   walk or a repeated block like "Sunshine-Rain99!"×3 can pass, while a strong
   Diceware passphrase needs many characters to clear it. The real control is
   generating the key with `secrets.token_urlsafe(48)` as the docs prescribe;
   the validator only stops obvious mistakes (AR2-007/AR2-008).
14. **Rate limiting trusts the socket peer.** Behind a reverse proxy that does
   not set a real client IP, every client shares the proxy's bucket; the
   deployment guidance (proxy limits, real-IP forwarding) lives in
   [deployment.md](deployment.md) and must be applied when deploying (AR2-009).

## Evaluation against the PRD

Phase 1 and Phase 2 acceptance criteria in [PRD.md](PRD.md) are met. Phase 3
items are tracked in [roadmap.md](roadmap.md) with none marked done except the
security partials listed there.
