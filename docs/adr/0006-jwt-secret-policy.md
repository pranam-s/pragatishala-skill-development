# ADR 0006: JWT signing secret policy: placeholders and entropy rejected

Status: accepted

## Context

ADR 0002 enforced a single property on `PRAGATISHALA_JWT_SECRET_KEY`: at
least 32 bytes (RFC 7518 section 3.2 for HS256). Length alone does not make a
key strong. The committed `backend/.env.example` shipped the placeholder
`change-me-at-least-32-bytes-long`, 33 bytes, so it **passed** the validator.
The documented onboarding flow (`cp .env.example .env`, then run) therefore
produced a bootable app signed with a publicly-known key: anyone who read the
repository could mint valid access/refresh JWTs for any user id, with no
warning at startup (adversarial review finding AR-021, verified by direct
construction of `Settings`).

## Decision

The `Settings` JWT-secret validator now enforces three checks, in order:

1. **Placeholder denylist**: an exact (whitespace-trimmed, case-insensitive)
   match against a frozen set of publicly-known placeholder literals is
   rejected, including the current and historical `.env.example` values and
   common framework defaults. `.env.example` itself ships a value from that
   denylist, so the copy-paste workflow fails loudly at startup with a message
   that tells the developer how to generate a real secret
   (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) instead of
   silently deploying a known key.
2. **Minimum length**: unchanged, 32 bytes.
3. **Basic entropy floor**: at least 12 distinct characters and at least
   3.0 bits of Shannon entropy per character. This rejects degenerate keys
   (`xxxx…`, `abab…`) of any length while accepting random hex/base64 output
   of the `secrets` module and long varied passphrases.

Rejection is at settings-construction time: the app cannot boot with a weak
key, which is strictly stronger than a runtime warning.

## Consequences

- Copying `.env.example` verbatim no longer yields a running app, by design.
  The README quickstart says to set the secret after copying; the failure
  message now repeats the generation command.
- The entropy floor is a sanity check, not a password-strength meter: a
  low-entropy-looking string built from many distinct characters (e.g. a
  dictionary phrase with rich character use) can still pass. The denylist
  handles the publicly-known cases; generation via the `secrets` module
  remains the documented path.
- Tests use realistic high-entropy secrets; single-repeated-character test
  constants are themselves rejected now.
