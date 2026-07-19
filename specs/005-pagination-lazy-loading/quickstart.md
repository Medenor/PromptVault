# Quickstart: Validating Pagination & Lazy Loading (Core)

## Prerequisites

- Python 3.14+ environment with project dependencies installed
- Database migrated (issue #13 baseline) with a seeded dataset large enough to exercise pagination (100+ prompts recommended; use existing seed/fixture scripts if available, or create via `POST /api/prompts` in a loop)
- Node/npm environment for frontend build (`npm install` if not already done)

## Backend validation

1. Start the server:
   ```bash
   python run_web.py
   ```
2. Request the first page of prompts with default paging:
   ```bash
   curl -s "http://localhost:8003/api/prompts" | python3 -m json.tool
   ```
   Expect: `prompts` contains at most 50 entries; `page=1`, `limit=50`, `total_count` reflects full library size, `has_previous=false`.
3. Request a second page:
   ```bash
   curl -s "http://localhost:8003/api/prompts?page=2&limit=50" | python3 -m json.tool
   ```
   Expect: different prompt IDs than page 1 (no overlap under stable data), `has_previous=true`.
4. Request an out-of-range page:
   ```bash
   curl -s "http://localhost:8003/api/prompts?page=9999&limit=50" | python3 -m json.tool
   ```
   Expect: `200 OK`, empty `prompts`, `has_next=false`.
5. Request an oversized limit:
   ```bash
   curl -s "http://localhost:8003/api/prompts?limit=9999" | python3 -m json.tool
   ```
   Expect: `limit` in response clamped to `100`, at most 100 prompts returned.
6. Combine search + pagination:
   ```bash
   curl -s "http://localhost:8003/api/prompts/search?search=email&page=1&limit=25" | python3 -m json.tool
   ```
   Expect: `total_count`/`total_pages` reflect only prompts matching "email", not the full library.

## Backend tests

```bash
python3 -m pytest tests/ -k "pagination or list_prompts or search_prompts" -v
python3 -m pytest --cov=src --cov-report=term-missing
```

Expect: new pagination tests pass; overall coverage remains ≥ 85% (constitution gate).

## Frontend validation

1. Build/typecheck:
   ```bash
   npm run typecheck && npm run lint
   ```
2. Run the app (`python run_web.py`) and open the main prompt list in a browser with a seeded library of 100+ prompts.
3. Confirm only the first page (default 50, or the selected page size) renders initially.
4. Click "Load More" — confirm additional prompts append below the existing list without clearing it, and a loading indicator shows while the request is in flight.
5. Click "Load More" repeatedly until all pages are exhausted — confirm the control disables or disappears once `has_next=false`.
6. Change the page-size selector (25 / 50 / 100) — confirm the list reloads from page 1 with the new size.
7. Apply a search/filter — confirm the list resets to page 1 for the filtered set, and "Load More" continues to paginate within that filtered set.
8. Rapidly double-click "Load More" — confirm only one network request fires (no duplicate page fetch).

## Frontend tests

```bash
npm run test:unit:coverage
```

Expect: new Vitest tests for `loadPrompts` pagination behavior, Load More guard, and page-size reset pass; overall coverage remains ≥ 85% (constitution gate).

## Success criteria mapping

| Quickstart step                        | Spec criterion |
| -------------------------------------- | -------------- |
| Steps 2–3 (backend page fetch)         | SC-001, SC-002 |
| Frontend step 4 (Load More)            | SC-003         |
| Steps 4–6 backend + frontend steps 3,7 | SC-004         |
| Frontend step 6                        | SC-005         |
