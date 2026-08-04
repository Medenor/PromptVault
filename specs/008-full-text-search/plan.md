# Implementation Plan: Full-Text Search

**Branch**: `008-full-text-search` | **Date**: 2026-08-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-full-text-search/spec.md`

## Summary

Replace the current `ilike '%term%'` substring scan in `PromptRepository.search()`/`count()` with native, index-backed full-text search on both supported backends: an FTS5 virtual table on SQLite and a weighted `tsvector` GIN column on PostgreSQL. Results are ranked by relevance (title > body > note), each result carries a highlighted excerpt (`match_context`), and the existing substring path is retained as a fallback for case-sensitive queries and for inputs the FTS parser cannot interpret. No new runtime dependencies — both engines are native to the databases already in use. Dialect branching follows patterns already established in this repo's Alembic migrations (`op.get_bind().dialect.name`, `sa.inspect()`).

## Technical Context

**Language/Version**: Python 3.14+ (backend); TypeScript (frontend, `src/web/static/ts/`)

**Primary Dependencies**: FastAPI, SQLAlchemy ORM, Alembic (existing). psycopg2-binary already present for Postgres. No new dependencies.

**Storage**: PostgreSQL (production) and SQLite (local/tests) via SQLAlchemy ORM + Alembic migrations. FTS5 is compiled into standard SQLite builds; `tsvector`/GIN is native to Postgres.

**Testing**: pytest (backend, ≥85% coverage gate); Vitest + v8 (frontend, ≥85% gate). Existing `tests/conftest_db.py` provides DB fixtures.

**Target Platform**: Linux server (Docker) and local dev; self-hosted deployments.

**Project Type**: Web application (FastAPI backend + TypeScript SPA frontend), layered service/repository architecture.

**Performance Goals**: Single-word search returns in < 1s on a 5,000-prompt vault; response time flat (index-backed) rather than linear in vault size; ranked FTS measurably beats the substring-scan baseline on the same data set.

**Constraints**: Must work identically across SQLite and Postgres. Highlight output must render through the existing `escapeHtml` safe-text path (no `innerHTML` of raw DB content). One-time index build on upgrade may take several seconds on large vaults; must be communicated in CHANGELOG. Must not regress the existing case-sensitive search behavior.

**Scale/Scope**: Repository search layer (`search`/`count`), one search API endpoint, one Alembic migration (dialect-branched), and the result-card frontend rendering. Benchmark harness for 5k prompts.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| **I. Layered Service Architecture** | ✅ FTS logic lives in the repository layer (`PromptRepository`); the router stays thin and only forwards params + shapes response. No SQL in routes. |
| **II. Test Coverage Gate (≥85%)** | ✅ Plan includes unit tests for FTS query building, fallback, sanitization, snippet rendering, plus a cross-dialect matrix and a 5k benchmark. Frontend snippet rendering covered by Vitest. |
| **III. Security-First Authentication** | ✅ Search is a public read endpoint (unchanged); no auth surface change. Input sanitization prevents FTS-injection; snippet output is escaped (no XSS). |
| **IV. TypeScript-Only Frontend** | ✅ Frontend changes (render `match_context`) are in `src/web/static/ts/` only, reuse existing `escapeHtml`, and go through `tsc`/ESLint. Legacy `js/` untouched. |
| **V. Database-Backed Persistence** | ✅ Uses SQLAlchemy + a new Alembic migration for the FTS objects. No new JSON/file storage. (See Complexity note re: raw SQL for FTS.) |

**Security & Quality standards note**: Constitution says "SQL access MUST go through SQLAlchemy ORM — no raw SQL strings with user input." FTS `MATCH` / `@@ plainto_tsquery` are not expressible through the pure ORM. This is handled as a bounded exception — see Complexity Tracking. All user input is passed via **bound parameters** (never string-interpolated) and sanitized, so the "no raw SQL strings with user input" intent (injection safety) is preserved.

**Result**: PASS (one justified deviation tracked below).

## Project Structure

### Documentation (this feature)

```text
specs/008-full-text-search/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── search-api.md    # /api/prompts/search contract (ranked, match_context)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── db/
│   ├── models/
│   │   └── prompt.py                     # Prompt model (title/prompt/note) — no schema change needed
│   ├── repositories/
│   │   └── prompt_repository.py          # MODIFY: dialect-aware search()/count(); FTS + fallback; snippet
│   └── search/                           # NEW (optional): fts_dialect.py helpers (query build, sanitize, snippet)
│       └── fts.py                        # NEW: dialect detection, safe-query builder, snippet extraction
├── web/
│   └── routers/
│       ├── prompts_search_router.py      # MODIFY: add ranked flag; surface match_context in response
│       └── prompts_shared.py             # MODIFY: _prompt_to_dict / envelope carries match_context
└── web/static/ts/
    ├── app/
    │   ├── prompt-filters.ts             # MODIFY: build ?ranked=true default in search URL
    │   └── prompt-card.ts                # MODIFY: render match_context snippet under title (escaped + <mark>)
    └── types/api/responses.ts            # MODIFY: PromptResponse gains optional match_context

alembic/
└── versions/
    └── <new>_full_text_search.py         # NEW: dialect-branched migration (FTS5 table+triggers / tsvector+GIN)

tests/
├── test_fts_search.py                    # NEW: correctness + ranking + fallback + sanitization (both dialects)
├── test_fts_snippet.py                   # NEW: snippet/highlight safety
├── benchmarks/
│   └── test_fts_benchmark.py             # NEW: 5k-seed benchmark, FTS vs LIKE
└── conftest_db.py                        # MAYBE: add a Postgres-backed fixture / marker for the matrix
```

**Structure Decision**: Single web-application layout (existing). Core work is concentrated in the repository layer per Principle I, with a thin new `src/db/search/fts.py` helper module holding the dialect-specific query construction, input sanitization, and snippet extraction so the repository method stays readable and both `search()` and `count()` share one code path. The migration follows the existing dialect-branch pattern in `alembic/versions/`. Frontend changes are minimal and additive.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Raw/textual SQL for the FTS predicate (`MATCH`, `bm25()`, `@@ plainto_tsquery`, `ts_rank`, `snippet()`, `ts_headline`) instead of pure SQLAlchemy ORM expressions | FTS ranking, matching, and snippet functions are database-native and have no portable ORM expression. They must be issued as backend-specific SQL via SQLAlchemy `text()` / `func`. | A pure-ORM approach cannot express relevance ranking or snippets at all — it would leave us on `ilike`, which is exactly the problem being solved. Injection risk is mitigated by **bound parameters only** + input sanitization, satisfying the constitution's actual intent (no user input in SQL strings). |
| Two searchable representations kept in sync (FTS5 shadow table + triggers on SQLite; generated `tsvector` column on Postgres) | Index-backed FTS requires a maintained derived structure; triggers/generated columns keep it current automatically (FR-013). | Querying the base table directly with `ilike` cannot use an index and degrades linearly (the status quo). A manual reindex step was rejected because FR-013 requires no manual reindex. |
