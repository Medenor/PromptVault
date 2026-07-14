# Implementation Plan: Pagination & Lazy Loading (Core)

**Branch**: `005-pagination-lazy-loading` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-pagination-lazy-loading/spec.md`

## Summary

Add server-side offset pagination (`page`, `limit`) to `GET /api/prompts` and `GET /api/prompts/search`, replacing the current full-dataset load with a bounded, standardized page envelope. Extend the prompt repository to paginate via SQLAlchemy `.limit()`/`.offset()` plus a count query, reusing existing filter logic. Add a "Load More" control and page-size selector to the TypeScript frontend (`app.ts`), appending pages to the currently rendered list.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript (frontend, strict `tsc`)

**Primary Dependencies**: FastAPI, SQLAlchemy ORM, Pydantic (backend); no new frontend dependencies — vanilla TS with existing `apiGet`/`apiFetch` helpers

**Storage**: SQLite/PostgreSQL via SQLAlchemy (migration complete, issue #13)

**Testing**: pytest (backend, ≥85% coverage gate), Vitest (frontend, ≥85% coverage gate)

**Target Platform**: Linux server (self-hosted web app)

**Project Type**: Web application (existing single FastAPI + TS frontend project, not a new project)

**Performance Goals**: First page of 1,000+ prompt library renders in <1s; each subsequent "Load More" fetch <1s under normal conditions (per spec SC-001, SC-003)

**Constraints**: Initial payload size reduced ≥90% vs. full-dataset load for 1,000+ prompt libraries (SC-002); no duplicate concurrent "Load More" requests; existing filter behavior must not regress

**Scale/Scope**: Two backend endpoints (`list_prompts`, `search_prompts`) in `src/web/routers/prompts.py`; one repository extension (`PromptRepository`); one frontend module (`app.ts`) plus its response types and template (`index.html`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layered Service Architecture**: PASS. Pagination logic (limit/offset/count) is added to `PromptRepository` (data layer), invoked from the router (web layer) — no layer bypass.
- **II. Test Coverage Gate**: PASS (must be enforced during implementation). New pagination code paths in both router and repository require pytest coverage; frontend "Load More" logic requires Vitest coverage. Tracked as explicit tasks.
- **III. Security-First Authentication**: PASS / N/A. Both affected endpoints (`GET /api/prompts`, `GET /api/prompts/search`) are read-only and already publicly accessible with optional auth; pagination adds no new mutation surface.
- **IV. TypeScript-Only Frontend**: PASS *with correction*. The user-supplied implementation notes referenced `src/web/static/js/app.js`, which is legacy and MUST NOT be edited per this principle. The actual target is `src/web/static/ts/app.ts` (and its compiled output). This plan corrects that and targets `app.ts` exclusively.
- **V. Database-Backed Persistence**: PASS. Pagination is implemented purely via SQLAlchemy `.limit()`/`.offset()` and a count query — no raw SQL, no JSON storage involvement for the primary path.

**Legacy data_service fallback**: Both `list_prompts` and `search_prompts` contain a legacy branch that loads from `data_service` (JSON-backed) when present, used by existing monkeypatched tests. Per Principle V, JSON/file-based storage MUST NOT be used for *new* features. Decision: the legacy branch is left functionally as-is (unpaginated) for backward test compatibility, and pagination is only added to the SQLAlchemy-backed path. This is not a new use of JSON storage — it's non-expansion of an existing deprecated path. Documented as a research decision in `research.md`.

No unresolved violations. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/005-pagination-lazy-loading/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/            # Phase 1 output
└── tasks.md              # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── web/
│   ├── routers/
│   │   └── prompts.py             # list_prompts, search_prompts — add page/limit params, pagination envelope
│   ├── static/
│   │   └── ts/
│   │       ├── app.ts             # loadPrompts, renderPrompts, search handler — add Load More + page size selector
│   │       └── types/
│   │           └── api/
│   │               └── responses.ts   # PromptListResponse — extend with pagination metadata
│   └── templates/
│       └── index.html             # Add Load More button + page size selector markup
└── db/
    └── repositories/
        └── prompt_repository.py   # search() already accepts limit/offset; add a matching count(filters) helper
        └── base.py                # get_all(skip, limit) and count() already exist — reused as-is for list_prompts

tests/
├── unit/ or backend test dir      # pytest: pagination param parsing, clamping, envelope shape
└── (frontend) src/web/static/ts/__tests__/  # Vitest: Load More flow, page size reset, loading-state guard
```

**Structure Decision**: Existing single web-application project (FastAPI backend + TypeScript frontend under the same repo). No new projects or services are introduced — pagination is added as an extension of the existing router + repository + frontend module, consistent with the Simplicity and Anti-Abstraction principles implied by spec-kit's constitutional gates and this project's own constitution (Principle I: Layered Service Architecture).

## Complexity Tracking

*No violations requiring justification.*
