# Quickstart / Validation Guide: Full-Text Search

End-to-end checks that prove the feature works. Details live in [data-model.md](./data-model.md) and [contracts/search-api.md](./contracts/search-api.md); do not duplicate implementation here.

## Prerequisites

- Feature branch `008-full-text-search` checked out.
- **Prerequisite change**: the redundant legacy dual-path in the search/list routers is collapsed to the repository path — Codeberg [#72](https://codeberg.org/medenor/promptvault/issues/72). Until then, FTS runs but is shadowed by the in-Python path and won't be observable end-to-end.
- Apply migrations: `python3 -m alembic upgrade head` (builds the FTS objects; note the one-time index build).
- Run the app via the project script only: `python run_web.py` (never invoke uvicorn directly).

## Scenario 1 — Ranked results (P1, FR-001/FR-003)

1. Seed two prompts: one with `python` in the **title**, one with `python` once deep in the **body**.
2. `GET /api/prompts/search?search=python`
3. **Expect**: both returned; the title match appears **first** (SC-003).
4. `GET /api/prompts/search?search=code%20review` → prompts containing **both** words rank above single-word matches.

## Scenario 2 — Snippets & safe highlight (P2, FR-005/FR-006/FR-007)

1. Seed a prompt whose body contains the term mid-text, plus a prompt whose body contains `<script>alert(1)</script>` next to the term.
2. `GET /api/prompts/search?search=<term>`
3. **Expect**: each result has `match_context` with `[[MATCH]]…[[/MATCH]]` around hits.
4. Render in the UI (or run the Vitest render test): the excerpt shows highlighted text; the `<script>` is displayed as **literal text**, never executed (SC-006). Confirm the client escapes first, then swaps sentinels for `<mark>`.

## Scenario 3 — Fallback & case-sensitive (P3, FR-009/FR-010/FR-011)

1. `GET /api/prompts/search?search=API&case_sensitive=true` → case respected exactly as before (substring path); no `match_context` required.
2. `GET /api/prompts/search?search=%22%2A%2A%2A%22` (operator-only junk) → **`200`** with sensible/empty results, **no** FTS syntax error (fallback).
3. `GET /api/prompts/search?search=%22code%20review%22` (quoted phrase) → matches the phrase as a unit (FR-012).

## Scenario 4 — Count consistency & pagination (FR-008/FR-014)

1. Seed > `limit` matches for a term.
2. Page through `?search=<term>&page=1..N`.
3. **Expect**: `pagination.total_count` matches the true number of results; no prompt appears on two pages or is skipped (stable `id` tiebreaker).

## Scenario 5 — Performance at scale (P2 / SC-001/SC-002)

1. Run the seed-data benchmark: `python3 -m pytest tests/benchmarks/test_fts_benchmark.py -q` (builds ~5,000 prompts).
2. **Expect**: a typical single-word query returns in **< 1s**, and the FTS path is **measurably faster** than the `ilike` baseline on the same data, with identical correct matches.

## Scenario 6 — Live sync, no manual reindex (FR-013/SC-007)

1. Create a prompt with a unique nonsense token via the API; immediately `GET /api/prompts/search?search=<token>` → it appears.
2. Edit the prompt to remove the token; search again → it no longer matches. Delete a prompt; search → gone. No reindex step invoked.

## Cross-dialect matrix (SC-005)

- Run the FTS test suite against **SQLite** (default) and against a **Postgres** test database.
- `python3 -m pytest tests/test_fts_search.py tests/test_fts_snippet.py -q`
- **Expect**: matches, ranking order, and snippet presence are equivalent across both backends for the same seeded data.

## Gate checks before merge

- `python3 -m pytest` passes with **≥ 85%** coverage (backend gate).
- `npm run typecheck && npm run lint && npm run test:unit:coverage` pass (frontend gate).
- `docker-compose up --build` starts cleanly (migration applies; startup unaffected).
- CHANGELOG updated with the upgrade note (index build may take seconds on large vaults).
