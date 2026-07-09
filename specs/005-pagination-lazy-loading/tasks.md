---

description: "Task list for Pagination & Lazy Loading (Core)"
---

# Tasks: Pagination & Lazy Loading (Core)

**Input**: Design documents from `/specs/005-pagination-lazy-loading/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/prompts-pagination.md, quickstart.md

**Tests**: Included — this project's constitution (Principle II, non-negotiable) requires tests alongside every new endpoint/service method with an ≥85% coverage gate.

**Organization**: Tasks are grouped by user story (from spec.md: US1 = browse without slow load, US2 = pagination + filters combined, US3 = page-size selector).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps task to US1 / US2 / US3 from spec.md

## Path Conventions

Existing single web-application project. Backend: `src/web/routers/prompts.py`, `src/db/repositories/prompt_repository.py`, `src/db/repositories/base.py`. Frontend: `src/web/static/ts/app.ts`, `src/web/static/ts/types/api/responses.ts`, `src/web/templates/index.html`. Backend tests: `tests/test_api_endpoints.py`, `tests/test_db_repositories.py`. Frontend tests: `src/web/static/ts/__tests__/`.

---

## Phase 1: Setup

**Purpose**: No new project scaffolding needed — this feature extends an existing router, repository, and frontend module in place. Nothing to initialize.

- [X] T001 Confirm local dev environment runs cleanly before changes: `python run_web.py` starts, `npm run typecheck` passes, `python3 -m pytest -q` passes on current `main`/base branch (baseline sanity check, no files modified)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pagination primitives that both US1 (list) and US2 (search) depend on. MUST complete before any user story work begins.

**⚠️ CRITICAL**: No user story task can begin until this phase is complete.

- [X] T002 Add `count(query, category, tags, favorite, case_sensitive)` method to `PromptRepository` in `src/db/repositories/prompt_repository.py`, mirroring the filter-building logic of the existing `search()` method (lines 38-111) but returning `int` via a `.count()` query instead of `.all()` — MUST apply identical filter predicates as `search()` per data-model.md's "Relationships" note
- [X] T003 [P] Add a shared pagination-normalization helper (e.g., `normalize_pagination(page: int, limit: int) -> tuple[int, int]`) in `src/web/routers/prompts.py` implementing the rules from research.md Decision 3: `page<1` or invalid → `1`; `limit<1` or invalid → `50`; `limit>100` → clamp to `100`
- [X] T004 [P] Extend `PromptListResponse` type in `src/web/static/ts/types/api/responses.ts` with `page: number`, `limit: number`, `total_pages: number`, `total_count: number`, `has_next: boolean`, `has_previous: boolean` fields alongside the existing `prompts` field, per data-model.md
- [X] T005 [P] Extend the backend Pydantic response model for prompt list/search (co-located with or referenced by `src/web/routers/prompts.py`) with the same pagination fields, matching contracts/prompts-pagination.md response shape

**Checkpoint**: Count helper, normalization helper, and both response type definitions exist — user story implementation can now begin.

---

## Phase 3: User Story 1 - Browse a large prompt library without a slow initial load (Priority: P1) 🎯 MVP

**Goal**: `GET /api/prompts` returns one page of results (default 50) with pagination metadata instead of the entire dataset.

**Independent Test**: Seed 100+ prompts, call `GET /api/prompts` with no params, confirm response contains ≤50 prompts plus correct `page/limit/total_pages/total_count/has_next/has_previous`; call again with `page=2`, confirm different, non-overlapping prompts.

### Tests for User Story 1 ⚠️

- [X] T006 [P] [US1] Add pytest cases in `tests/test_api_endpoints.py` for `GET /api/prompts`: default pagination (≤50 results, correct envelope fields), explicit `page=2`, `limit` clamped when `>100`, invalid/negative `page` normalizes to 1, empty-library returns `total_count=0` and empty `prompts`, out-of-range `page` returns empty `prompts` with `has_next=false` and `200 OK` (not an error)
- [X] T007 [P] [US1] Add pytest cases in `tests/test_db_repositories.py` for `BaseRepository.get_all(skip, limit)` + `.count()` combination as used by the paginated list path (confirm skip/limit slicing is correct and count is independent of limit/offset)

### Implementation for User Story 1

- [X] T008 [US1] Update `list_prompts` in `src/web/routers/prompts.py` (~line 200) to accept `page: int = 1, limit: int = 50` query params, call the T003 normalization helper, use `PromptRepository.get_all(skip=(page-1)*limit, limit=limit)` and `.count()` for the SQLAlchemy-backed path, and build the pagination envelope (page, limit, total_pages, total_count, has_next, has_previous) per contracts/prompts-pagination.md
- [X] T009 [US1] Update the legacy `data_service` fallback branch inside `list_prompts` (same function) to populate the same pagination envelope fields with "single page containing everything" semantics (page=1, total_pages=1 if any results else 0, total_count=len(results), has_next=false, has_previous=false) per research.md Decision 4 — do not add real pagination to this deprecated path
- [X] T010 [US1] Update `loadPrompts()` in `src/web/static/ts/app.ts` (~line 1317) to request `page`/`limit` params, read pagination metadata from `PromptListResponse`, and support an "append" mode that merges new results into the existing rendered dict rather than replacing it, using the extended type from T004
- [X] T011 [US1] Add a "Load More" button and loading-state indicator to the prompt list container in `src/web/templates/index.html`, wired to call `loadPrompts()` in append mode for the next page; button/indicator visibility driven by `has_next` from the last response
- [X] T012 [US1] Add a module-level guard flag (e.g., `isLoadingMore`) in `src/web/static/ts/app.ts` around the Load More click handler to prevent duplicate concurrent fetches per spec Edge Cases / FR-008, and disable/hide the Load More control when `has_next` is false per FR-009
- [X] T013 [P] [US1] Add Vitest cases in `src/web/static/ts/__tests__/` covering: `loadPrompts()` append behavior, Load More becomes disabled/hidden when `has_next=false`, duplicate-click guard prevents a second concurrent request while one is in flight

**Checkpoint**: Opening the prompt list now loads one page at a time; "Load More" works end-to-end. This is independently testable and deployable as the MVP.

---

## Phase 4: User Story 2 - Combine pagination with search and filters (Priority: P1)

**Goal**: `GET /api/prompts/search` supports the same pagination as US1, with `total_count`/`total_pages` reflecting the filtered set, and changing a filter resets to page 1.

**Independent Test**: Seed 100+ prompts where 30 match a given search term, call `GET /api/prompts/search?search=X` with default paging, confirm `total_count=30` (not the full library size) and pagination metadata is consistent; confirm changing the search term in the UI resets to page 1.

### Tests for User Story 2 ⚠️

- [X] T014 [P] [US2] Add pytest cases in `tests/test_api_endpoints.py` for `GET /api/prompts/search` with pagination: `total_count`/`total_pages` reflect only filtered results (not full library), pagination combined with each existing filter (`search`, `category`, `tag`, `favorites`, `case_sensitive`) individually and combined, `favorites=true` without auth still returns 401 (unchanged behavior) even with pagination params present
- [X] T015 [P] [US2] Add pytest case in `tests/test_db_repositories.py` confirming the new `count()` method (T002) returns the same count as `len(search(...))` without limit, for a representative set of filter combinations

### Implementation for User Story 2

- [X] T016 [US2] Update `search_prompts` in `src/web/routers/prompts.py` (~line 281) to accept `page`/`limit` query params, apply the T003 normalization helper, pass `limit`/`offset` through to `PromptRepository.search()` (already supports them per research.md Decision 1), call the new `count()` method (T002) with the same filter args, and build the pagination envelope per contracts/prompts-pagination.md
- [X] T017 [US2] Update the legacy `data_service` fallback branch inside `search_prompts` (same function) with the same "single page containing everything" envelope semantics as T009, applied to the filtered result set
- [X] T018 [US2] Update the search handler in `src/web/static/ts/app.ts` (~line 2407) to pass `page`/`limit` and reset to page 1 whenever any filter value (search text, category, tag, favorites, case-sensitive) changes, per FR-011; reuse the append/Load More logic from T010-T012 for subsequent pages of a filtered result set
- [X] T019 [P] [US2] Add Vitest cases in `src/web/static/ts/__tests__/` covering: changing a filter resets `currentPage` to 1 and clears previously appended results, Load More continues to paginate correctly within an active filter

**Checkpoint**: Both list and search endpoints are fully paginated; filters and pagination compose correctly. US1 and US2 both work independently and together.

---

## Phase 5: User Story 3 - Choose how many prompts load per page (Priority: P2)

**Goal**: Users can select a page size (25/50/100) that applies to both the initial load and subsequent "Load More" fetches.

**Independent Test**: Select page size 25, confirm initial load returns ≤25 prompts; trigger Load More, confirm the next fetch also uses limit=25; switch to 100, confirm the list reloads from page 1 with up to 100 prompts.

### Tests for User Story 3 ⚠️

- [X] T020 [P] [US3] Add Vitest cases in `src/web/static/ts/__tests__/` covering: page size selector change triggers a reload from page 1 with the new `limit`, subsequent Load More calls use the newly selected page size, only the three defined options (25/50/100) are selectable

### Implementation for User Story 3

- [X] T021 [US3] Add a page-size `<select>` control (options 25/50/100) to `src/web/templates/index.html` near the Load More control from T011
- [X] T022 [US3] Wire the page-size selector in `src/web/static/ts/app.ts` to update the pagination state's `pageSize`, reset to page 1, and re-fetch via `loadPrompts()` (replace mode, not append) — reusing the state model from data-model.md's "Pagination State"

**Checkpoint**: All three user stories are independently functional; page size selection works for both the unfiltered list and filtered search.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation, not tied to a single story.

- [X] T023 Run `python3 -m pytest --cov=src --cov-report=term-missing` and confirm overall backend coverage remains ≥85% per constitution Principle II
- [X] T024 [P] Run `npm run typecheck && npm run lint && npm run test:unit:coverage` and confirm overall frontend coverage remains ≥85% per constitution Principle II
- [X] T025 Execute all steps in `specs/005-pagination-lazy-loading/quickstart.md` manually against a locally seeded 100+ prompt library and confirm every expected outcome
- [X] T026 [P] Update API documentation/OpenAPI descriptions in `src/web/routers/prompts.py` docstrings for `list_prompts` and `search_prompts` to document the new `page`/`limit` params and response envelope, matching contracts/prompts-pagination.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — sanity check only.
- **Foundational (Phase 2)**: Depends on Phase 1. BLOCKS all user stories (T002-T005 are prerequisites for T006+).
- **User Story 1 (Phase 3)**: Depends on Phase 2. No dependency on US2/US3 — independently testable and shippable as MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Reuses US1's frontend append/guard logic (T010-T012) but the backend work (T016-T017) is independent of US1's backend work (T008-T009) — different function, same file.
- **User Story 3 (Phase 5)**: Depends on Phase 2. Builds on the pagination state model shared with US1/US2 but is additive UI — can be implemented after either US1 or US2 is done, though US1 should land first since it's the MVP path.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Parallel Opportunities

- T003 and T004 and T005 (Phase 2) touch different files and can run in parallel.
- T006 and T007 (US1 tests) touch different test files and can run in parallel.
- T013 (US1 frontend tests) can run in parallel with backend-only tasks once T010-T012 land.
- T014 and T015 (US2 tests) can run in parallel.
- T019 and T020 (frontend tests for US2/US3) can run in parallel with each other once their respective implementation tasks land.
- T024 and T026 (Phase 6) can run in parallel.

---

## Parallel Example: Phase 2 (Foundational)

```bash
Task: "Add count() method to PromptRepository in src/db/repositories/prompt_repository.py"
Task: "Add pagination-normalization helper in src/web/routers/prompts.py"
Task: "Extend PromptListResponse type in src/web/static/ts/types/api/responses.ts"
Task: "Extend backend Pydantic response model with pagination fields"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (sanity check) and Phase 2 (foundational: count helper, normalization helper, response types).
2. Complete Phase 3 (US1: paginated `GET /api/prompts` + Load More UI).
3. **STOP and VALIDATE**: Run quickstart.md steps 1-3 and frontend steps 3-5 against a seeded 100+ prompt library.
4. This alone resolves the core problem statement (slow full-dataset load) and is deployable.

### Incremental Delivery

1. Setup + Foundational → shared primitives ready.
2. US1 → paginated list + Load More → validate → deploy (MVP).
3. US2 → paginated search/filter → validate filters still work correctly with pagination → deploy.
4. US3 → page-size selector → validate → deploy.
5. Polish → coverage checks, full quickstart run, doc updates.

---

## Notes

- [P] tasks touch different files with no dependency on incomplete same-phase work.
- Both `list_prompts` and `search_prompts` live in the same file (`src/web/routers/prompts.py`) but are separate functions — T008-T009 (US1) and T016-T017 (US2) do not conflict, though sequential commits are recommended to keep diffs reviewable.
- Per constitution Principle II, write each story's tests before or alongside its implementation tasks, not after.
- Per constitution Principle IV, all frontend work targets `src/web/static/ts/app.ts` — the legacy `src/web/static/js/app.js` MUST NOT be edited.
