# Contributing

## Development workflow

1. Create a focused branch from `main`.
2. Keep tenant filters and authorization checks on every data-access path.
3. Add tests for stock-changing commands and role changes.
4. Run backend tests and the frontend production build locally.
5. Open a pull request describing behavior, risk, and verification evidence.

## Required checks

```bash
cd backend && pytest -q
cd frontend && pnpm lint && pnpm build
```

## Commit style

Use concise imperative messages, for example:

- `feat: add carrier tracking events`
- `fix: preserve tenant scope in inventory lookup`
- `docs: document payment webhook setup`

Do not commit generated output, secrets, local databases, logs, or customer documents.
