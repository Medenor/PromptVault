# Phase 0 Research: Pagination & Lazy Loading (Core)

## Decision 1: Reuse existing repository pagination primitives

**Decision**: No new repository methods are needed for retrieval. `PromptRepository.search()` (`src/db/repositories/prompt_repository.py:38`) already accepts `limit` and `offset`. `BaseRepository.get_all(skip, limit)` and `BaseRepository.count()` (`src/db/repositories/base.py:56,139`) already exist and are inherited by `PromptRepository`. Only a filtered-count helper is missing (needed to compute `total_count`/`total_pages` for the `search()` path, since `BaseRepository.count()` counts the whole table with no filters).

**Rationale**: Avoids duplicating query-building logic; keeps filter definitions (text/category/tag/favorite) in exactly one place (`search()`), satisfying the Anti-Abstraction / Simplicity spirit even though this project's constitution doesn't name that gate explicitly. Adding a `count(...)` method mirroring `search()`'s filter args is the minimal change.

**Alternatives considered**:

- Running `search()` twice (once unbounded to count via `len()`) — rejected, defeats the purpose of pagination by always loading full result set.
- A generic `paginate()` wrapper — rejected as premature abstraction; two call sites (`get_all`+`count` for list, `search`+new `count` for search) don't yet justify a shared paginator.

## Decision 2: Pagination response envelope shape

**Decision**: Extend `PromptListResponse` (backend Pydantic response model + `src/web/static/ts/types/api/responses.ts:116`) with pagination metadata fields alongside the existing `prompts` dict:

```ts
export interface PromptListResponse {
  prompts: Record<string, PromptResponse>;
  page: number;
  limit: number;
  total_pages: number;
  total_count: number;
  has_next: boolean;
  has_previous: boolean;
}
```

**Rationale**: Keeping `prompts` as `Record<string, PromptResponse>` (keyed by ID) preserves the existing shape consumed by `renderPrompts()` in `app.ts:1377`, minimizing frontend rewrite — pagination metadata is purely additive, not a breaking change to the envelope's existing field.

**Alternatives considered**:

- Switching `prompts` to an array — rejected; would require rewriting `renderPrompts` and all call sites for no functional gain, and increases the blast radius of this change beyond what the spec calls for.
- A separate `/api/prompts/page-info` endpoint — rejected; splits an atomic read into two requests for no benefit.

## Decision 3: Default and max page size

**Decision**: Default `limit=50`, maximum `limit=100`. Requests with `limit` above 100 are clamped to 100 (not rejected with an error), per spec Edge Cases. Requests with `page < 1` or non-numeric are normalized to `page=1`.

**Rationale**: Matches the spec's stated page-size selector options (25, 50, 100) and Assumptions section. Clamping instead of erroring keeps the API forgiving for the frontend's fixed selector, consistent with FR-012 ("handle out-of-range or invalid page/page-size inputs gracefully").

**Alternatives considered**: Rejecting invalid params with HTTP 422 — rejected because the spec explicitly requires graceful handling, not errors, for these cases.

## Decision 4: Legacy `data_service` (JSON) fallback path

**Decision**: The legacy branch in `list_prompts` and `search_prompts` (used when `data_service.load_prompts()` returns data, primarily for existing monkeypatched tests) is left unpaginated — it continues to return the full filtered dict as today, but is updated to also match the new response envelope shape with pagination fields defaulted to reflect "single page containing everything" (page=1, total_pages=1, total_count=len(results), has_next=false, has_previous=false).

**Rationale**: Constitution Principle V forbids JSON/file storage for _new_ features but does not mandate removing already-existing legacy code paths in this change. Adding real pagination to the JSON-backed path would mean writing new pagination logic against deprecated storage — contrary to the constitution's intent. Normalizing its response shape (not its behavior) keeps the API contract consistent for frontend consumers without expanding use of the deprecated path.

**Alternatives considered**:

- Fully paginating the legacy path too — rejected as expanding investment in deprecated storage.
- Leaving the legacy response shape untouched (no pagination fields at all) — rejected because it would make the frontend's envelope handling inconsistent depending on which backend path served the request.

## Decision 5: Frontend integration point

**Decision**: Extend `loadPrompts()` (`app.ts:1317`) and the search handler (`app.ts:2407`) to accept a page/limit and an "append vs. replace" mode. Add a page-size selector and a "Load More" button + loading-state guard variable (module-level flag or data attribute) to prevent duplicate concurrent fetches, wired into `index.html` template near the existing prompt list container.

**Rationale**: `app.ts` already owns all prompt list fetch/render logic; extending it in place avoids introducing a new module for a cohesive, small addition. This is the only frontend file touched, consistent with Principle IV (TypeScript-only; legacy `app.js` must not be edited).

**Alternatives considered**: New dedicated `pagination.ts` module — rejected as premature given the entire feature is ~2 new functions and one piece of UI state; can be extracted later if reused elsewhere.

## Resolved Technical Context

All Technical Context fields in `plan.md` are resolved with no outstanding `NEEDS CLARIFICATION` markers.
