# Testing

Full guide: [`docs/TESTING.md`](../TESTING.md) — fixture catalogue, suite structure, how to write a database-backed test.

## Running tests

Use `make test` (root `make` targets — see [`docs/DEVELOPMENT.md`](../DEVELOPMENT.md)). It runs backend + frontend and fails if either fails.

To run a single backend suite, always invoke pytest via `python3 -m pytest` (not bare `pytest`) — this ensures the correct dependency versions (httpx, fastapi, starlette) rather than whatever's installed globally:

```bash
python3 -m pytest tests/test_db_repositories.py
python3 -m pytest tests/test_db_services.py
python3 -m pytest tests/test_version_system.py
python3 -m pytest tests/test_web_api.py
python3 -m pytest tests/test_admin_api.py
```

Frontend: `npm run test:unit` (all), `npm run test:unit:coverage` (with v8 coverage).

## Coverage

85% minimum, enforced in `pytest.ini` (backend) and `vitest.config.ts` (frontend). Coverage % and test counts are not pinned in docs — they change every PR. Run the suites and read the console output / `htmlcov/index.html` / `coverage/` for current numbers; treat those as the source of truth.

## Conventions

- Tests live in [`tests/`](../../tests/), one file per service/module, filenames start with `test_`.
- Shared fixtures in [`tests/conftest.py`](../../tests/conftest.py) — see `docs/TESTING.md` for the full catalogue (database, model, repository, service, API-client fixtures).
- Test coverage must remain ≥85% after any change; update tests alongside code, not after.
- For frontend changes: `npm run typecheck` must pass before considering the change done.
