# Contributing

## How this project is organized

This is a single-operator / small-team monorepo. The Lead Architect coordinates
module boundaries; Business Backend, Frontend, AI, Knowledge, Automation, and QA
agents each own clearly separated areas (see `docs/agents.md` and
`docs/agent-status.md`).

## Rules of the road

1. **Inspect before implementing.** Read the existing code before changing it.
2. **One writer per file.** Never have two agents edit the same file concurrently.
3. **Contracts first.** Shared schemas live in `apps/api/app/schemas.py`; frontend
   consumes via the API client.
4. **Tests before merge.** Every change to a module ships with tests.
5. **No fake implementations.** No hardcoded business data, no silent stubs in
   production paths. Honest 503/not-configured responses are acceptable; fake
   successes are not.
6. **Soft deletes.** No hard deletes in normal paths.
7. **Docs are part of the work.** Update `docs/` when behavior changes.

## Development flow

```bash
git checkout -b feature/your-change
make install
# ... implement + tests ...
make test
make test-web
cd apps/web && npm run build   # typecheck + vite build
git commit && git push
# open a PR with: what changed, what was tested, known limitations
```

## Code style

- Python: type-annotated, Ruff-clean, docstring on every module.
- TypeScript: strictly typed, no `any` in new code, components in `src/components/`,
  pages in `src/pages/`, no inlined styles beyond layouts.
- Tests live next to the module they cover (`apps/api/tests/`, `src/**/*.test.ts(x)`).

## Reporting issues

Use the issue template:
- **Bug:** steps to reproduce, expected, actual, environment.
- **Feature:** why, the user-visible behavior, trade-offs.
- **Doc drift:** exact file + line.

## What PRs look like

- Small, single-purpose diffs.
- "Implemented", "Partially Implemented", and "Planned" status labels in the
  docs update along with the code.
- Include a test note in the PR description.
