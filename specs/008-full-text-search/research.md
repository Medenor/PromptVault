# Phase 0 Research: Full-Text Search

All Technical Context items were resolvable from the codebase and well-established database features; there were **no open NEEDS CLARIFICATION** items. This document records the key design decisions and the alternatives weighed.

## Decision 1 — SQLite backend: FTS5 external-content virtual table + triggers

- **Decision**: Create an `prompts_fts` FTS5 virtual table over `(title, prompt, note)` configured as an **external-content** table (`content='prompts', content_rowid='id'`), kept in sync by `AFTER INSERT / UPDATE / DELETE` triggers on `prompts`. Rank with the built-in `bm25()` function, weighting title > prompt > note. Extract snippets with `snippet()`.
- **Rationale**:
  - FTS5 is compiled into standard SQLite builds shipped with CPython — **zero new dependency**.
  - External-content mode avoids duplicating the prompt text; the FTS table stores only the index, referencing `prompts` by rowid.
  - `bm25()` gives real relevance ranking with per-column weights (`bm25(prompts_fts, w_title, w_prompt, w_note)`), directly satisfying FR-001/FR-003.
  - Triggers keep the index current automatically (FR-013) with no application-level bookkeeping.
- **Alternatives considered**:
  - *Contentless / standalone FTS table storing its own copy of the text* — rejected: doubles storage and risks drift; external-content is the idiomatic choice when a base table already holds the rows.
  - *`LIKE` with an expression index* — rejected: SQLite cannot index `%term%` leading-wildcard patterns; no ranking, no snippets.
- **Migration note**: external-content tables need the standard three-trigger sync pattern (delete uses the special `'delete'` command insert into the FTS table). The one-time backfill after creating the table populates it from existing rows (`INSERT INTO prompts_fts(rowid, title, prompt, note) SELECT id, title, prompt, note FROM prompts`).

## Decision 2 — PostgreSQL backend: generated `tsvector` column + GIN index

- **Decision**: Add a `search_vector tsvector` column populated from weighted `to_tsvector` over the three fields — title weight `A`, prompt weight `B`, note weight `C` — and index it with GIN. Match with `search_vector @@ plainto_tsquery(...)`, rank with `ts_rank(search_vector, query)`, snippet via `ts_headline`.
- **Rationale**:
  - Native to Postgres — **zero new dependency**; `tsvector`/GIN is the standard FTS approach.
  - Weighted vector (`setweight(to_tsvector(...), 'A')` etc.) gives the title > body > note ordering for free via `ts_rank` (FR-001).
  - A **stored generated column** (`GENERATED ALWAYS AS (...) STORED`) keeps the vector in sync automatically on INSERT/UPDATE (FR-013) without triggers — simpler than a trigger and available on the Postgres versions this project targets.
  - `plainto_tsquery` treats user input as plain text (AND of terms) and never raises a syntax error on arbitrary input — it inherently sanitizes, complementing our own sanitization layer. `phraseto_tsquery` handles quoted phrases (FR-012).
- **Alternatives considered**:
  - *Trigger-maintained plain `tsvector` column* — acceptable, but a generated column is less code and cannot drift. Chosen generated column as primary; trigger noted as fallback if a target PG version rejects the generated expression.
  - *`to_tsquery` for user input* — rejected as the default: it throws on unbalanced operators/special chars. Reserve it (if ever) behind sanitization; `plainto_tsquery`/`phraseto_tsquery` are the safe defaults.

## Decision 3 — Dialect detection & the fallback path

- **Decision**: Detect the active dialect at query time via `self.session.bind.dialect.name` (`"sqlite"` vs `"postgresql"`). Route to the FTS branch for the normal case; route to the **existing `ilike` substring path** when: (a) `case_sensitive=True`, or (b) the sanitized query is empty after stripping operators, or (c) the FTS query raises (caught, logged, fall back).
- **Rationale**:
  - Mirrors the established pattern already used across this repo's Alembic migrations (`op.get_bind().dialect.name`, `7182f1f03364`, `b7a1c2d3e4f5`).
  - Case-sensitive FTS is not natively supported by either engine's default configuration; the current Python-side case filter (already in `prompt_repository.py`) remains correct and is the right fallback (FR-009).
  - Graceful fallback on parser errors satisfies FR-010/FR-011 — the user never sees an FTS syntax error.
- **Alternatives considered**:
  - *Global config flag to pick the engine* — rejected: the dialect is already known from the session; a flag adds config surface with no benefit.

## Decision 4 — Input sanitization & phrase support

- **Decision**: Add a `sanitize_fts_query()` helper. Default mode: split on whitespace, drop tokens that are only FTS operator/punctuation characters, and pass the remaining terms to `plainto_tsquery` (PG) or as quoted/space-joined terms to FTS5 `MATCH`. Support explicit quoted phrases (`"code review"`) mapped to `phraseto_tsquery` (PG) / an FTS5 phrase (`"code review"`).
- **Rationale**: Guarantees no syntax error reaches the engine (FR-011), while still allowing the one advanced feature in scope — quoted phrases (FR-012). Advanced boolean operators are explicitly out of scope per the spec.
- **Alternatives considered**:
  - *Pass user input raw to `to_tsquery`/FTS5 `MATCH`* — rejected: both throw on unbalanced quotes/operators, violating FR-011.

## Decision 5 — Snippet generation & safe rendering

- **Decision**: Return a `match_context` string per result from `snippet()` (SQLite) / `ts_headline` (Postgres), configured to wrap matches in a **neutral sentinel** (e.g. `[[MATCH]]…[[/MATCH]]`) rather than raw `<mark>`. The frontend converts sentinels to `<mark>` **after** `escapeHtml()` so the surrounding DB text is escaped and only the intended highlight becomes markup.
- **Rationale**: Satisfies FR-005/FR-006 while guaranteeing FR-007/SC-006 (no XSS). The repo already has a battle-tested `escapeHtml` in `src/web/static/ts/app/shared.ts` and `utils/dom.ts`; reusing it keeps us inside Principle IV's safe-rendering rule. Emitting raw `<mark>` from the DB and trying to escape "everything except the mark tags" is error-prone; the sentinel approach is provably safe.
- **Alternatives considered**:
  - *Have the DB emit `<mark>` directly and render with `innerHTML`* — rejected: mixes trusted markup with untrusted content in one string; the exact XSS footgun the spec warns against.
  - *Highlight purely client-side by re-matching the query* — rejected: duplicates ranking logic, can't reproduce stemming, and misclassifies matches; DB-side snippet is authoritative.

## Decision 6 — Ranked default, sort precedence, pagination

- **Decision**: Add `ranked: bool = True` to the repository `search()` and the `/api/prompts/search` endpoint (`?ranked=true` default). When ranked and no explicit sort is chosen, `ORDER BY` relevance (bm25 asc / ts_rank desc), with a deterministic tiebreaker (`id`) so OFFSET/LIMIT pagination is stable (FR-014). Explicit sort options continue to override relevance (FR-004). `count()` uses the identical FTS predicate so totals match (FR-008).
- **Rationale**: Keeps API backward-compatible (default on, existing callers keep working), preserves existing sort UX, and the explicit tiebreaker prevents the duplicate/skip pagination bug the current code already guards against for `updated_at`.
- **Alternatives considered**:
  - *Make ranked opt-in (`ranked=false` default)* — rejected: the spec makes ranked the default experience (FR-004); opt-in would hide the feature.

## Decision 7 — Testing & benchmark strategy

- **Decision**: (1) Correctness + ranking + fallback + sanitization unit tests parametrized over both dialects. (2) A snippet-safety test feeding markup-like input. (3) A seed-data benchmark (`tests/benchmarks/`) building a 5,000-prompt vault and asserting FTS returns correct results and beats the `ilike` baseline in wall-clock time (SC-002). (4) Postgres leg of the matrix runs where a Postgres test DB is available (driver `psycopg2-binary` is already a dependency); SQLite leg always runs.
- **Rationale**: Directly maps to SC-001..SC-005 and the constitution's ≥85% gate. The repo already has DB fixtures in `tests/conftest_db.py` to build on.
- **Open item for tasks phase**: confirm/enable a Postgres-backed pytest fixture (container or service) so the Postgres matrix leg runs in CI; if unavailable it degrades to a `skip`-marked leg, with SQLite still fully covered. (Tracked as a task, not a spec blocker.)

## Cross-cutting note (raised during planning, not blocking)

The search router currently has a **dual code path**: `data_service.load_prompts()` (which is itself DB-backed) returns the whole table and the router filters/paginates **in Python**, shadowing the `PromptRepository(db)` SQL path — the repo path only runs when the DB is empty. In production with data, the in-Python path always wins, ignoring DB indexes and `ORDER BY`. The FTS work targets the **repository `search()`/`count()` path**, so this redundant dispatch must be collapsed to the SQL path for FTS to actually take effect. Filed as **Codeberg issue [#72](https://codeberg.org/medenor/promptvault/issues/72)**. Not a blocker for writing the spec/plan, but it is a **prerequisite for the FTS implementation to be observable** — collapsing the dual-path is captured as an early task in the tasks phase.
