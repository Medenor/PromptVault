# Phase 1 Data Model: Full-Text Search

No user-facing entity changes; the `prompts` table is unchanged. This feature adds **derived search structures** kept in sync automatically, and a **transient result shape** carrying rank + snippet.

## Existing entity (unchanged)

### Prompt (`prompts` table, `src/db/models/prompt.py`)

Searchable fields (already present):

| Field | Type | Search weight | Notes |
|-------|------|---------------|-------|
| `title` | `String(200)` NOT NULL | **A / highest** | already has `idx_prompts_title` |
| `prompt` | `Text` NOT NULL | **B / medium** | body content |
| `note` | `Text` NULL | **C / lowest** | optional; may be empty/NULL |
| `id` | `Integer` PK | — | used as FTS rowid (SQLite) and pagination tiebreaker |

No columns are added to `prompts` on SQLite. On Postgres, one **generated** column is added (see below); it is derived, not user-set.

## New derived structures (per dialect)

### SQLite — `prompts_fts` (FTS5 virtual table)

- **Type**: FTS5 external-content virtual table.
- **Config**: `content='prompts'`, `content_rowid='id'`, columns `(title, prompt, note)`.
- **Sync**: `AFTER INSERT`, `AFTER UPDATE`, `AFTER DELETE` triggers on `prompts` maintain it (delete via the FTS5 `'delete'` sentinel insert). No manual reindex (FR-013).
- **Backfill**: one-time populate from existing rows during the migration (FR-015).
- **Rank**: `bm25(prompts_fts, <w_title>, <w_prompt>, <w_note>)` — lower is more relevant; weights order title > prompt > note (FR-001).
- **Snippet**: `snippet(prompts_fts, <col>, '[[MATCH]]', '[[/MATCH]]', '…', <tokens>)`.

### PostgreSQL — `prompts.search_vector` (tsvector, GIN-indexed)

- **Type**: `tsvector` column, `GENERATED ALWAYS AS (...) STORED`.
- **Expression**: `setweight(to_tsvector('simple'|config, coalesce(title,'')), 'A') || setweight(to_tsvector(..., coalesce(prompt,'')), 'B') || setweight(to_tsvector(..., coalesce(note,'')), 'C')`.
- **Index**: `GIN (search_vector)`.
- **Sync**: automatic via the generated column (FR-013); no trigger, no manual reindex.
- **Backfill**: implicit — a stored generated column is computed for all existing rows when added (FR-015).
- **Rank**: `ts_rank(search_vector, query)` — higher is more relevant.
- **Snippet**: `ts_headline(config, prompt, query, 'StartSel=[[MATCH]], StopSel=[[/MATCH]], ...')`.

> `coalesce(...,'')` guards NULL `note` (edge case: empty fields).

## Transient shapes (not persisted)

### Search Query (input)

| Field | Type | Meaning |
|-------|------|---------|
| `query` | `str \| None` | raw user text; may include `"quoted phrases"` |
| `case_sensitive` | `bool` | when true → substring fallback path (FR-009) |
| `ranked` | `bool` (default `true`) | relevance ordering unless an explicit sort is chosen (FR-004) |
| plus existing | `category`, `tags`, `favorite`, `limit`, `offset` | unchanged filters |

**Sanitization** (`sanitize_fts_query`): strips operator-only tokens; extracts quoted phrases; joins remaining bare terms with **OR** (not AND) so partial multi-word matches are included and ranked below all-word matches (FR-003); yields a safe query object or signals "empty → fallback" (FR-010/FR-011).

### Search Result (output)

Existing `_prompt_to_dict(...)` shape **plus** one optional field:

| Field | Type | Meaning |
|-------|------|---------|
| `match_context` | `str \| None` | snippet with `[[MATCH]]…[[/MATCH]]` sentinels around hits (FR-005/FR-006). `None` when no body snippet applies (e.g. title-only match). |

Rank is used for ordering only and is **not** exposed in the response (implementation detail).

## Consistency rules

- `count()` MUST build the **same** FTS predicate as `search()` so totals match the ranked list (FR-008).
- Ranked ordering MUST include a deterministic tiebreaker (`id`) so OFFSET/LIMIT pagination never duplicates or skips a row (FR-014).
- Case-sensitive fallback filtering MUST be applied in the SQL predicate **before** `OFFSET`/`LIMIT`, not in Python after the page is fetched, so `count()` and the returned page stay consistent under case-sensitive mode (FR-014).
- The frontend MUST convert `[[MATCH]]`/`[[/MATCH]]` to `<mark>` **only after** `escapeHtml()` on the whole string (FR-007/SC-006).
