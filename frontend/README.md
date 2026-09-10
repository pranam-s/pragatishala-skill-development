# PragatiShala frontend

React 19 + TypeScript + Vite + Chakra UI v3 single-page app for PragatiShala.

## Development

```bash
npm install
npm run dev     # http://127.0.0.1:5173 — proxies /api/v1 to the FastAPI backend
```

Start the backend first (see the repository root README). API base URL can be
overridden with `VITE_API_BASE_URL` (see `.env.example`).

## Quality gates

```bash
npm run lint           # ESLint (flat config, typescript-eslint)
npm run build          # tsc -b && vite build
npm run test           # Vitest + Testing Library (jsdom)
npm run test:coverage
```

## Accessibility contract

Every page must remain keyboard-operable and screen-reader friendly:
labelled inputs (Chakra `Field`), `role="alert"` error regions,
`aria-live="polite"` status regions, `aria-current="page"` navigation, real
buttons and links, visible focus. Accessibility regressions are release
blockers — see `docs/STYLE_GUIDE.md`.
