---
description: "Task list for Full-Text Search (SQLite FTS5 / PostgreSQL tsvector)"
---

# Tasks: Full-Text Search

**Input**: Design documents from `/specs/008-full-text-search/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/search-api.md, quickstart.md

**Tests**: INCLUDED — the spec mandates a full cross-dialect test matrix + a 5k benchmark, and Constitution Principle II requires tests alongside implementation (≥85% coverage gate).

**Organization**: Grouped by user story (US1–US4 from spec.md) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US4 (user-story phases only)
- Paths are repo-relative and concrete.

## Path Conventions

Web application, existing layout: backend `src/`, frontend `src/web/static/ts/`, migrations `alembic/versions/`, tests `tests/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the FTS helper module location and confirm the toolchain.

- [ ] T001 Create the search helper package `src/db/search/` with an empty `__init__.py`
- [ ] T002 [P] Add a `tests/benchmarks/` directory with `__init__.py` and a `conftest.py` placeholder for benchmark fixtures
- [ ] T003 [P] Confirm SQLite build has FTS5 available and record the check in `tests/test_fts_search.py` skeleton (a module-level `pytest.importorskip`/`PRAGMA compile_options` guard that skips with a clear message if FTS5 is absent)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Collapse the redundant dual-path so FTS is observable, then build the dialect-branched schema and shared query helpers that ALL stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. In particular T004 is a hard prerequisite — until the legacy in-Python search path is removed, the repository `search()` FTS work is shadowed in production and cannot be validated end-to-end (Codeberg #72).

- [ ] T004 Collapse the legacy `data_service` dual-path to the repository path in `src/web/routers/prompts_search_router.py` (remove the `web_app.data_service.load_prompts()` dispatch and the `if legacy_prompts:` block in BOTH `list_prompts` and `search_prompts`; always use `PromptRepository(db)`). Rewrite/drop the two dependent tests in `tests/test_api_endpoints.py` (`test_legacy_prompt_structure_fallbacks`, `test_search_prompts_exception_returns_500`) and verify pagination/ordering assertions elsewhere still hold. Ref: Codeberg #72.
- [ ] T005 [P] Implement dialect detection + FTS query sanitization in `src/db/search/fts.py`: `active_dialect(session) -> str`, `sanitize_fts_query(raw: str) -> SafeQuery | None` (strips operator-only tokens, extracts `"quoted phrases"`, OR-joins remaining bare terms rather than AND, returns None when empty ⇒ signal fallback). Ref: research.md Decisions 3–4, FR-002/FR-003/FR-010/FR-011/FR-012.
- [ ] T006 [P] Implement snippet sentinel constants + helpers in `src/db/search/fts.py` (`MATCH_START='[[MATCH]]'`, `MATCH_END='[[/MATCH]]'`, and the per-dialect snippet arg builders for `snippet()` / `ts_headline`). Ref: research.md Decision 5, FR-005/FR-006.
- [ ] T007 Create the dialect-branched Alembic migration `alembic/versions/<rev>_full_text_search.py` (down_revision = `f1a2b3c4d5e6`), branching on `op.get_bind().dialect.name`:
  - **SQLite**: create `prompts_fts` FTS5 external-content virtual table over `(title, prompt, note)` with `content='prompts', content_rowid='id'`; create AFTER INSERT/UPDATE/DELETE sync triggers; backfill from existing rows.
  - **PostgreSQL**: add generated `search_vector tsvector` column (weighted title=A, prompt=B, note=C, `coalesce`-guarded) + `GIN` index.
  - Provide a symmetric `downgrade()` dropping all created objects. Ref: data-model.md, research.md Decisions 1–2, FR-013/FR-015.
- [ ] T008 [P] Migration test in `tests/test_fts_migration.py`: upgrade→downgrade→upgrade round-trips cleanly on SQLite; asserts the FTS table/triggers exist after upgrade and are gone after downgrade; asserts backfill populated existing rows. (Postgres leg runs when the matrix fixture from T009 is active.)
- [ ] T009 [P] Stand up the cross-dialect test matrix fixture in `tests/conftest_db.py`: a parametrized/`postgres_db` fixture + marker that provides a Postgres-backed session when a Postgres test DB is available and is `skip`-marked otherwise (SQLite leg always runs). This enables the Postgres leg of every parametrized FTS test (T008 migration, T010 ranking, T016 snippet, T024 fallback) from US1 onward (SC-005). Ref: research.md Decision 7, FR-017.

**Checkpoint**: Legacy path removed, FTS schema live on both dialects, shared helpers and cross-dialect matrix ready. User stories can begin.

---

## Phase 3: User Story 1 — Ranked, relevant search results (Priority: P1) 🎯 MVP

**Goal**: `search()`/`count()` return index-backed, relevance-ranked matches (title > body > note; all-words > some-words), with existing sort options still overriding relevance.

**Independent Test**: Seed a term in one prompt's title and once in another's body; `GET /api/prompts/search?search=<term>` returns both with the title match first; multi-word query ranks all-words matches above partial.

### Tests for User Story 1 ⚠️

- [ ] T010 [P] [US1] Ranking correctness tests in `tests/test_fts_search.py`: title-weighted-above-body, all-words-above-partial-but-partial-still-included (OR semantics, FR-003), and "returns the same matches ordinary substring would for word queries" (FR-001/FR-002/FR-003). Parametrized for dialect (SQLite always; Postgres via the T009 matrix marker).
- [ ] T011 [P] [US1] Sort-precedence + pagination-stability tests in `tests/test_fts_search.py`: explicit sort overrides relevance (FR-004); ranked pagination with `id` tiebreaker never duplicates/skips across pages (FR-014); `count()` matches the ranked list size (FR-008).

### Implementation for User Story 1

- [ ] T012 [US1] Implement the FTS branch of `PromptRepository.search()` in `src/db/repositories/prompt_repository.py`: dialect-branch to FTS5 `MATCH` (OR-joined bare terms, e.g. `term1 OR term2`) + `bm25(...)` weighting (SQLite) or `@@ to_tsquery('term1 | term2')` (OR-joined, not `plainto_tsquery`'s implicit AND) + `ts_rank` (Postgres) using bound parameters; add `ranked: bool = True` param; keep existing category/tag/favorite filters; deterministic `ORDER BY relevance, id`; fall back to the existing `ilike` path when `case_sensitive` or sanitized query is empty. **Multi-word semantics (pinned): bare (non-quoted) multi-word queries use OR — no query word is required for a match — so `bm25()`/`ts_rank()` naturally score all-words matches above partial-word matches without excluding partial matches (FR-002/FR-003).** **Return shape (pinned): `search()` ALWAYS returns `list[tuple[Prompt, str | None]]`** — the second element is `match_context` (populated in US2, `None` here and on the fallback/non-ranked path); the router adapts to this single shape (no dual return type). **Rank weights (pinned, recorded as inline constants so SC-003 is reproducible): title=10.0, prompt=4.0, note=1.0** — expressed as `bm25(prompts_fts, 10.0, 4.0, 1.0)` on SQLite (lower=more relevant; bm25 applies weights as column multipliers) and as `A/B/C` tsvector weights with `ts_rank` default weight array `{0.1, 0.2, 0.4, 1.0}` on Postgres. Adjust only if T010 ranking assertions require it, keeping title>prompt>note. (depends on T005, T007)
- [ ] T013 [US1] Make `PromptRepository.count()` mirror the exact FTS predicate in `src/db/repositories/prompt_repository.py` so totals match `search()` (FR-008). (depends on T012)
- [ ] T014 [US1] Wrap the FTS execution in try/except in `prompt_repository.py`: on FTS operational/parse error, log and fall back to the substring path returning `200`-worthy results (FR-010). (depends on T012)
- [ ] T015 [US1] Add `ranked: bool = True` to `search_prompts` in `src/web/routers/prompts_search_router.py` (query param `?ranked=true` default) and pass it through to the repository; adapt the router to unpack the `(Prompt, match_context)` tuples from `search()`; preserve existing sort-option handling (FR-004). (depends on T004, T012)

**Checkpoint**: Ranked search works end-to-end via the API on both dialects. MVP deliverable.

---

## Phase 4: User Story 2 — Result snippets with highlighted matches (Priority: P2)

**Goal**: Each result carries a `match_context` snippet with highlighted terms, rendered safely (no markup/script execution).

**Independent Test**: Search a term buried in a body → result card shows an excerpt with the term highlighted; a `<script>`-laced prompt renders as literal text.

### Tests for User Story 2 ⚠️

- [ ] T016 [P] [US2] Backend snippet tests in `tests/test_fts_snippet.py`: `search()` returns `match_context` with `[[MATCH]]…[[/MATCH]]` sentinels for body matches; `None` for title-only match; both dialects (FR-005/FR-006).
- [ ] T017 [P] [US2] Frontend safe-render test in `src/web/static/ts/app/__tests__/prompt-card.test.ts`: a `match_context` containing `<script>`/markup renders escaped, with sentinels converted to `<mark>` only, and no `innerHTML` of raw content (FR-007/SC-006).

### Implementation for User Story 2

- [ ] T018 [US2] Return `match_context` from the FTS branch of `PromptRepository.search()` in `src/db/repositories/prompt_repository.py` via `snippet()`/`ts_headline` using the sentinel helpers from T006 (`None` when no body snippet). (depends on T012, T006)
- [ ] T019 [US2] Surface `match_context` in the response in `src/web/routers/prompts_search_router.py` and `src/web/routers/prompts_shared.py` (extend `_prompt_to_dict`/envelope to carry the optional field). (depends on T018)
- [ ] T020 [P] [US2] Add optional `match_context?: string` to `PromptResponse` in `src/web/static/ts/types/api/responses.ts`.
- [ ] T021 [US2] Render the snippet under the card title in `src/web/static/ts/app/prompt-card.ts`: `escapeHtml(match_context)` first, then replace `[[MATCH]]`/`[[/MATCH]]` with `<mark>`/`</mark>` (reuse existing `escapeHtml` from `./shared`). (depends on T020)

**Checkpoint**: Ranked results now show safe, highlighted snippets in the UI.

---

## Phase 5: User Story 3 — Fast search on large vaults (Priority: P2)

**Goal**: Prove index-backed search is fast and scales (flat, not linear) and beats the substring baseline.

**Independent Test**: Benchmark on ≥5,000 prompts returns a typical query in <1s and faster than `ilike` on the same data with identical matches.

### Tests for User Story 3 ⚠️

- [ ] T022 [P] [US3] Seed-data benchmark in `tests/benchmarks/test_fts_benchmark.py`: build ~5,000 prompts, assert a single-word query returns in <1s (SC-001) and that FTS wall-clock beats the `ilike` baseline with equal correct matches (SC-002). **Also assert near-flat scaling** (FR-016): measure the same query at ~1,000 and ~5,000 prompts and assert FTS latency grows sub-linearly (e.g. 5× data ⇒ well under 5× time), while the `ilike` baseline grows roughly linearly — proving the "does not degrade linearly" requirement, not just the absolute point. (depends on T012)

### Implementation for User Story 3

- [ ] T023 [US3] Verify/confirm index usage: ensure the GIN index (Postgres) and FTS5 table (SQLite) are actually exercised by the ranked query path (no accidental full-scan); adjust the query in `src/db/repositories/prompt_repository.py` if the benchmark reveals a non-indexed plan. (depends on T012, T022)

**Checkpoint**: Performance target met and demonstrated against the baseline.

---

## Phase 6: User Story 4 — Reliable fallback & case-sensitive matching (Priority: P3)

**Goal**: Case-sensitive and un-parseable queries keep working via substring fallback; quoted phrases match as a unit.

**Independent Test**: `case_sensitive=true` respects case exactly as before; operator-only junk returns `200` (no FTS error); `"quoted phrase"` matches the phrase.

### Tests for User Story 4 ⚠️

- [ ] T024 [P] [US4] Fallback + sanitization + phrase tests in `tests/test_fts_search.py`: case-sensitive matching behavior unchanged from before this feature (FR-009); **case-sensitive pagination is consistent** — with `case_sensitive=true`, seed enough matching rows to span two pages and assert no row is duplicated or skipped across pages, and that `count()` equals the total matching rows (regression test for the pre-existing Python-post-`OFFSET`/`LIMIT` filtering bug, FR-014); operator-only query returns without error via fallback (FR-010/FR-011); quoted phrase matches as a unit (FR-012). Parametrized cross-dialect via the T009 matrix marker (SC-005).

### Implementation for User Story 4

- [ ] T025 [US4] Harden the fallback/phrase routing surfaced by T024 in `src/db/repositories/prompt_repository.py`: the error/empty-query fallback is already implemented in T012/T014 — this task (a) adds the quoted-phrase route (`phraseto_tsquery`/FTS5 phrase) if not already covered by the T005 sanitizer, and (b) **fixes case-sensitive filtering to run in the SQL predicate before `OFFSET`/`LIMIT`** instead of the current Python-side post-fetch filter, so `search()` and `count()` stay consistent under pagination (FR-014). No duplication of the T012/T014 fallback logic. (depends on T005, T012, T014, T024)

**Checkpoint**: No existing search behavior is lost; all edge cases handled.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T026 [P] Add a list-endpoint regression test in `tests/test_api_endpoints.py`: after the T004 dual-path collapse, `GET /api/prompts` (no search) returns correctly ordered, correctly paginated results via the repository path (guards against the `list_prompts` half of the collapse). (depends on T004)
- [ ] T027 [P] Update `CHANGELOG.md` with the FTS entry and the upgrade note (one-time index build may take seconds on large vaults). (FR-015 migration note)
- [ ] T028 [P] Update the `/api/prompts/search` docstring in `src/web/routers/prompts_search_router.py` to document `ranked` and `match_context` per `contracts/search-api.md`.
- [ ] T029 Run the backend coverage gate: `python3 -m pytest` ≥85% (Constitution II); fill any gaps in `tests/test_fts_search.py`.
- [ ] T030 [P] Run the frontend gates: `npm run typecheck && npm run lint && npm run test:unit:coverage` (≥85%).
- [ ] T031 Validate `docker-compose up --build` starts cleanly with the migration applied (Constitution workflow #6).
- [ ] T032 Execute `specs/008-full-text-search/quickstart.md` scenarios 1–6 against a running `python run_web.py` instance and confirm all pass; **also smoke-test the plain `GET /api/prompts` list endpoint** post-collapse (companion to T026).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup. **BLOCKS all user stories.** T004 (dual-path collapse) and T007 (migration) are the critical blockers.
- **US1 (Phase 3)**: after Foundational. The MVP.
- **US2 (Phase 4)**: after US1 (snippets extend the ranked `search()` from T012/T018).
- **US3 (Phase 5)**: after US1 (benchmarks the ranked path).
- **US4 (Phase 6)**: after US1 (hardens fallback/phrase routing around the FTS branch). The Postgres matrix fixture it relies on for cross-dialect legs is now created in Foundational (T009), not here.
- **Polish (Phase 7)**: after all targeted stories.

### Within Each User Story

- Tests written first and expected to fail before implementation (Constitution II).
- Repository `search()` (T012) is the spine; `count()`, snippet, fallback, and API all build on it.

### Parallel Opportunities

- Setup: T002, T003 in parallel.
- Foundational: T005, T006, T009 in parallel; T008 after T007.
- US1: T010, T011 (tests) in parallel before T012.
- US2: T016, T017, T020 in parallel; T020→T021.
- Polish: T026, T027, T028, T030 in parallel.

---

## Parallel Example: User Story 1

```bash
# Tests first (parallel):
Task: "Ranking correctness tests in tests/test_fts_search.py"
Task: "Sort-precedence + pagination-stability tests in tests/test_fts_search.py"

# Then implementation (sequential on the shared repository file):
Task: "Implement FTS branch of PromptRepository.search() in src/db/repositories/prompt_repository.py"
Task: "Mirror predicate in PromptRepository.count()"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup.
2. Phase 2: Foundational — **T004 dual-path collapse (Codeberg #72) is the gating step**, then migration + helpers.
3. Phase 3: US1 ranked search.
4. **STOP and VALIDATE**: quickstart Scenario 1 on both dialects.
5. Deploy/demo — ranked search is the headline value.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 → ranked results (MVP).
3. US2 → highlighted snippets.
4. US3 → proven performance at 5k.
5. US4 → fallback/case-sensitive safety net.
6. Polish → CHANGELOG, gates, docker parity, quickstart.

---

## Notes

- [P] = different files, no incomplete-task dependencies.
- Constitution deviation (backend-native FTS SQL) is bounded: **bound parameters only**, no user input interpolated into SQL strings.
- Postgres test leg is skip-marked where no Postgres DB is present; SQLite leg always runs, so coverage never depends on external services.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
