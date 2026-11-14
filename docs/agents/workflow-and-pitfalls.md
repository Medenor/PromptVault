# Development Workflow

1. Read the relevant service/module and its existing tests before changing anything — tests document expected behavior.
2. Follow established architectural patterns (see [architecture.md](architecture.md)); consider downstream effects.
3. Implement, then update tests to keep coverage ≥85%.
4. Frontend changes: run `npm run typecheck` (TypeScript changes are not live until compiled) and `npm run lint`.
   Anything changed under `src/web/static/` (locales, CSS, JS) also needs a `CACHE_VERSION` bump in `src/web/static/ts/sw.ts` **every time**, not once per branch; see [frontend.md](frontend.md#service-worker-cache-versioning).
5. Run relevant tests (`make test`, or a targeted `python3 -m pytest`/`npm run test:unit` — see [testing.md](testing.md)) before considering the change done.
6. Update `CHANGELOG.md` with user-facing changes.
7. For sharing/validation changes: keep `docs/API_VALIDATION_AND_MONITORING.md` and `docs/VALIDATION_TEST_CHECKLIST.md` aligned, and verify client/server validation parity plus `/api/validation/stats` monitoring.

## Common Pitfalls

- Don't hardcode file paths — use `os.path.join()` / relative paths.
- Don't skip error handling — wrap I/O and database operations in try/except.
- Don't forget transactions — use database sessions with proper commit/rollback.
- Use the database-backed services (`PromptDataServiceDB`, `BackupServiceDB`) — the legacy JSON-file services have been removed.
- Don't break database migrations — test with both SQLite and PostgreSQL when modifying models (see [python-style.md#alembic-migrations](python-style.md#alembic-migrations)).
- Don't leave `console.log` in committed frontend code.
- Don't assume an earlier `CACHE_VERSION` bump on the branch covers later static changes: `make check-sw-cache-version` only checks for one bump per branch, and missed bumps show up as raw i18n keys in the browser.
- Don't skip database session cleanup.
