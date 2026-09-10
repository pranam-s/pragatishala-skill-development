# PragatiShala — Product Requirements Document

Status: living document. Phase 1 and Phase 2 are implemented; Phase 3 is
partially implemented (see [roadmap.md](roadmap.md)).

## Problem

Millions of Indian learners cannot answer two questions reliably:

1. "Where do my current skills actually stand for the job I want?"
2. "What exactly should I learn next, in what order, and how do I prove it?"

Generic courses do not diagnose; career counsellors do not scale; job boards do
not teach.

## Product principles

1. **Accessibility is a feature, not a checkbox.** The primary stakeholder
   (the owner) uses NVDA. Every flow must be keyboard-operable, labelled, and
   announced correctly by screen readers. Regressions are release blockers.
2. **Works offline, better online.** Every AI feature has a deterministic
   rule-based fallback. The product never shows "service unavailable" for its
   core loop.
3. **Honesty about confidence.** Responses record which engine produced them
   (`engine_used`) so users know when they got model output vs. rules.
4. **Plain language in, structure out.** Users describe skills in their own
   words; the platform returns structured, actionable output.

## Personas

- **Asha, 21, final-year student (fresher).** Knows some Python and SQL from
  college. Wants to know if she is ready for a Data Analyst internship and what
  to learn next.
- **Rahul, 27, support engineer (career switcher).** Has Linux + scripting
  experience from work. Wants a credible path into a DevOps role.

## Features

### Phase 1 — Core platform (implemented)

| Feature             | Requirement                                                                     | Status |
| ------------------- | ------------------------------------------------------------------------------- | ------ |
| Registration        | Email + password (≥8 chars), optional name/target role/experience level         | Done   |
| Login               | OAuth2 password flow; JWT access (30 min) + refresh (7 days)                    | Done   |
| Profile             | View and update name, target role, experience level                             | Done   |
| Skill assessment    | 20–8,000 char narrative → skills with levels, strengths, gaps, readiness 0–100  | Done   |
| Learning path       | Roadmap (≤8 modules) from latest or explicit assessment; milestones + hours     | Done   |
| Resume builder      | Structured draft from role + skills + experience/education/projects text        | Done   |
| Ownership           | Users can only read/modify their own assessments, paths, and resumes            | Done   |

### Phase 2 — AI integration (implemented)

| Feature              | Requirement                                                                       | Status |
| -------------------- | --------------------------------------------------------------------------------- | ------ |
| AI provider          | OpenAI-compatible + Anthropic; keys from env only; strict JSON schema validation  | Done   |
| Offline fallback     | Deterministic engine per feature; automatic on provider failure                   | Done   |
| Market analysis      | Per-role-family insights with 24-hour cache (`engine_used` records origin)        | Done   |
| Realtime updates     | SSE stream per user; events on assessment/path/resume completion                  | Done   |

### Phase 3 — Platform enhancement (partial, see roadmap)

- Analytics and progress tracking — not started.
- Performance optimization — not started (current scale is fine for dev).
- Additional integrations (job boards, LinkedIn) — not started.
- Enhanced security — partial: strong hashing, expiry, ownership checks, CORS
  allow-list, env-only secrets done; rate limiting and account recovery missing.

## Non-functional requirements

| Area          | Requirement                                                            | Status |
| ------------- | ---------------------------------------------------------------------- | ------ |
| Accessibility | WCAG-informed: labels, landmarks, focus visibility, live regions       | Done   |
| Test coverage | ≥90% line AND branch on backend `app` package (enforced, currently ~99%) | Done   |
| Type safety   | `mypy --strict` clean; TypeScript `strict` clean                       | Done   |
| Secrets       | Environment only; `.env` git-ignored; `.env.example` documents all vars | Done   |
| Privacy       | No third-party analytics; narratives stored only for the owner's history | Done   |

## Out of scope (for now)

- Payments/subscriptions, admin console, email verification, mobile apps.
