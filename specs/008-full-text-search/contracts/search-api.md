# Contract: `GET /api/prompts/search` (ranked full-text search)

Extends the existing search endpoint (`src/web/routers/prompts_search_router.py`). **Backward-compatible**: all existing params and the response envelope are unchanged; ranking is on by default and one optional field is added to each result.

## Request

| Param | Type | Default | Change | Notes |
|-------|------|---------|--------|-------|
| `search` | string | `""` | — | full-text query; supports `"quoted phrases"` |
| `category` | string | `""` | — | unchanged filter |
| `tag` | string | `""` | — | unchanged filter |
| `favorites` | bool | `false` | — | unchanged; auth-gated as today |
| `case_sensitive` | bool | `false` | — | `true` → substring fallback (no ranking/snippet) |
| `ranked` | bool | `true` | **NEW** | `false` restores legacy substring ordering |
| `page` | int | `1` | — | 1-indexed |
| `limit` | int | `50` | — | clamped to 100 |

## Response `200`

Existing pagination envelope. Each prompt in `prompts` gains **one optional field**:

```jsonc
{
  "prompts": {
    "42": {
      "id": 42,
      "title": "Python code review checklist",
      "prompt": "...",
      "note": "...",
      "category": "Engineering",
      "tags": ["python", "review"],
      "favorite": false,
      "created_at": "...",
      "updated_at": "...",
      "match_context": "…follows the [[MATCH]]python[[/MATCH]] style guide…"  // NEW, optional
    }
  },
  "pagination": { "page": 1, "limit": 50, "total_count": 3, "total_pages": 1 }
}
```

### `match_context`
- Present when the engine produced a body snippet; may be absent/`null` for title-only matches or when `ranked=false`/`case_sensitive=true`.
- Contains `[[MATCH]]…[[/MATCH]]` sentinels, **not** HTML. The client escapes the string, then replaces sentinels with `<mark>` (safe-render contract, FR-007).

## Ordering contract
- `ranked=true` (default) + no explicit sort → results ordered by relevance (title > body > note), tiebroken by `id` for stable pagination (FR-004/FR-014).
- Explicit sort option selected → that sort wins over relevance (FR-004).
- `ranked=false` or `case_sensitive=true` → existing `updated_at desc, created_at desc` substring behavior (FR-009).

## Consistency & error contract
- `pagination.total_count` reflects the **same** predicate as the returned list (FR-008).
- `case_sensitive=true` filtering is applied in the SQL predicate before `OFFSET`/`LIMIT` (not in Python after fetch), so paginated results and `total_count` stay consistent under case-sensitive mode (FR-014, fixes a pre-existing pagination inconsistency).
- A query the FTS parser cannot interpret MUST NOT 4xx/5xx on account of FTS: the server sanitizes and, if needed, falls back to substring — returning `200` with results (FR-010/FR-011).
- Existing error behaviors (e.g. `401` for `favorites` without auth when auth enabled) are unchanged.

## Repository contract (`PromptRepository`)

```python
def search(self, query=None, category=None, tags=None, favorite=None,
           limit=None, offset=0, case_sensitive=False,
           ranked=True) -> list[tuple[Prompt, str | None]]: ...
def count(self, query=None, category=None, tags=None, favorite=None,
          case_sensitive=False) -> int: ...
```

- `search()` **always** returns `list[tuple[Prompt, str | None]]` — a single, stable shape. The second element is the `match_context` snippet, populated on the ranked FTS path (US2) and `None` on the fallback/non-ranked/case-sensitive path. The router unpacks the tuple uniformly; there is no dual return type.
- `count()` MUST mirror `search()`'s predicate exactly.
- Both MUST select the FTS branch or substring fallback based on `self.session.bind.dialect.name`, `case_sensitive`, and sanitized-query emptiness.
