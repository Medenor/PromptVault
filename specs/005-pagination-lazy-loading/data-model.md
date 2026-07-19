# Phase 1 Data Model: Pagination & Lazy Loading (Core)

No new persisted entities or schema changes are introduced by this feature — pagination operates on the existing `Prompt` model (`src/db/models`) via read-only queries. This document describes the two request/response shapes introduced at the API boundary.

## Pagination Request Parameters

Applies to `GET /api/prompts` and `GET /api/prompts/search`.

| Field   | Type    | Required | Default | Validation / Normalization                                                   |
| ------- | ------- | -------- | ------- | ---------------------------------------------------------------------------- |
| `page`  | integer | No       | `1`     | Values `< 1` or non-numeric normalize to `1`                                 |
| `limit` | integer | No       | `50`    | Values `> 100` clamp to `100`; values `< 1` or non-numeric normalize to `50` |

Existing filter parameters on `search` (`search`, `category`, `tag`, `favorites`, `case_sensitive`) are unchanged and combine with the above (spec FR-005, FR-006).

## Prompt Page Result (response envelope)

Extends the existing `PromptListResponse` shape.

| Field          | Type                             | Description                                                                                     |
| -------------- | -------------------------------- | ----------------------------------------------------------------------------------------------- |
| `prompts`      | `Record<string, PromptResponse>` | Unchanged existing shape — prompts for the current page, keyed by ID                            |
| `page`         | integer                          | Current page number returned (post-normalization)                                               |
| `limit`        | integer                          | Page size used (post-clamping)                                                                  |
| `total_pages`  | integer                          | `ceil(total_count / limit)`, minimum `1` when `total_count > 0`, else `0`                       |
| `total_count`  | integer                          | Total number of prompts matching the current filters (not the whole library, unless unfiltered) |
| `has_next`     | boolean                          | `true` if `page < total_pages`                                                                  |
| `has_previous` | boolean                          | `true` if `page > 1`                                                                            |

**Relationships**: `total_count`/`total_pages` are computed relative to the same filter predicate applied to `prompts` (spec FR-006) — i.e., the count query MUST use identical filter conditions as the page query, differing only in `limit`/`offset` vs. `count()`.

## Pagination State (frontend, in-memory only)

Not persisted; lives in `app.ts` module state while the prompt list view is active.

| Field           | Type    | Description                                                                                                           |
| --------------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| `currentPage`   | number  | Last successfully loaded page                                                                                         |
| `pageSize`      | number  | Currently selected page size (25 \| 50 \| 100)                                                                        |
| `hasNext`       | boolean | Mirrors last response's `has_next`, controls Load More visibility/enabled state                                       |
| `isLoadingMore` | boolean | Guards against duplicate concurrent "Load More" requests (spec Edge Cases, FR-008)                                    |
| `activeFilters` | object  | Current search/category/tag/favorites/case-sensitivity values, used to know when to reset `currentPage` to 1 (FR-011) |
