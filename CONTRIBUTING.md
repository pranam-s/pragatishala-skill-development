# Contributing

Thanks for considering a contribution to PragatiShala. The bar for every
change is the one the codebase already holds itself to.

## Ground rules

- **Accessibility is a release blocker.** The owner is a blind NVDA
  screen-reader user: keyboard-navigable flows, labelled controls, focus
  management, and status conveyed by more than colour are required, not
  nice-to-have.
- **Tests stay offline and deterministic.** AI features are tested through
  the rule-based fallback and mocked providers; a test that needs an API
  key or network does not belong here.
- **No hacks.** No placeholders, no stubs treated as done, no suppressed
  warnings (`filterwarnings = ["error"]` is deliberate — the suite must
  stay warning-free), no skipped tests.
- **Layer boundaries hold.** Routers have no business logic; services own
  rules; AI is a strategy behind the SkillEngine contract (ADR-0005).
- **Schema changes** go through the startup upgrade runner (ADR-0008),
  not a migration tool.

## Setup

```bash
cd backend && uv sync --all-groups
cd frontend && npm ci
```

## Quality gates (all required before a commit)

Backend (from `backend/`):

```bash
uv run ruff check app tests && uv run ruff format --check app tests
uv run mypy                      # strict
uv run deptry . && uv run vulture app --min-confidence 80
uv run pytest                    # branch coverage ≥ 90% enforced
```

Frontend (from `frontend/`):

```bash
npm run lint
npm run test
npx knip --no-progress
npm run build
```

## Commit style

Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore(deps):`,
`ci:`), one logical change per commit.

## Security issues

Do not open a public issue; use GitHub's private security advisory.
