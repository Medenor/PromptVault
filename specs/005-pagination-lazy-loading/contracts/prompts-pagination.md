# API Contract: Prompt List & Search Pagination

## `GET /api/prompts`

Lists prompts, now paginated.

### Query Parameters

| Name    | Type    | Required | Default | Notes                                                             |
| ------- | ------- | -------- | ------- | ----------------------------------------------------------------- |
| `page`  | integer | No       | `1`     | Normalized to `1` if `<1` or invalid                              |
| `limit` | integer | No       | `50`    | Clamped to `100` if higher; normalized to `50` if `<1` or invalid |

### Response `200 OK`

```json
{
  "prompts": {
    "42": {
      "id": 42,
      "title": "Example",
      "prompt": "...",
      "category": "Marketing",
      "category_color": "#ff0000",
      "tags": ["email"],
      "tag_colors": { "email": "#00ff00" },
      "note": "",
      "favorite": false,
      "user_id": "abc",
      "created_at": "2026-07-01T00:00:00Z",
      "updated_at": "2026-07-08T00:00:00Z"
    }
  },
  "page": 1,
  "limit": 50,
  "total_pages": 3,
  "total_count": 120,
  "has_next": true,
  "has_previous": false
}
```

Unchanged from current behavior: no authentication required; authenticated users get personalization logging only (no behavior change).

## `GET /api/prompts/search`

Search/filter prompts, now paginated. All existing filter parameters (`search`, `category`, `tag`, `favorites`, `case_sensitive`) are unchanged and compose with pagination.

### Query Parameters

| Name             | Type    | Required | Default | Notes                                                           |
| ---------------- | ------- | -------- | ------- | --------------------------------------------------------------- |
| `search`         | string  | No       | `""`    | Unchanged                                                       |
| `category`       | string  | No       | `""`    | Unchanged                                                       |
| `tag`            | string  | No       | `""`    | Unchanged                                                       |
| `favorites`      | boolean | No       | `false` | Unchanged; requires auth (401 if used without auth — unchanged) |
| `case_sensitive` | boolean | No       | `false` | Unchanged                                                       |
| `page`           | integer | No       | `1`     | Same normalization as above                                     |
| `limit`          | integer | No       | `50`    | Same clamping as above                                          |

### Response `200 OK`

Same envelope shape as `GET /api/prompts` above. `total_count`/`total_pages` reflect the filtered result set, not the full library (spec FR-006).

### Behavior contract

- Changing any filter parameter between requests is a client-side responsibility to reset `page=1`; the server does not track client-side pagination state across requests (each request is independently paginated per its own parameters — spec FR-011 is enforced by the frontend resetting `page` in the request, not by server-side session state).
- Requesting a `page` beyond `total_pages` returns `200 OK` with an empty `prompts` object, `has_next=false`, and correctly computed `total_count`/`total_pages` (spec Edge Cases) — not a `404`/`400`.
- `favorites=true` without authentication still returns `401 Unauthorized` (unchanged, existing behavior — pagination does not alter auth requirements).

### Backward compatibility note

Both endpoints previously returned a bare `{"prompts": {...}}` with no pagination fields. This change is additive (new fields on the same envelope); no existing field is removed or renamed. Clients not yet aware of pagination fields continue to work unmodified, but will only ever receive the first 50 results by default instead of the full dataset — this is a deliberate, spec-mandated behavior change (SC-002) and MUST be called out in the PR description as a behavioral change even though it's not a schema break.
