# API Contract: Skill Packages

**Feature**: 011-skill-packages | All paths are under `/api`.

**Auth**: the same rules as prompts (FR-025).
- **`AUTH_ENABLED=true`**: every skill endpoint needs a valid access token. A skill the caller does not own returns **404**, not 403, so that other users' skills cannot be detected. **Administrators** can see, download and delete every skill, matching the admin path for prompts (`visible_to_user_id=None`). Administrators cannot edit or replace another user's skill: those calls return 404, the same as for other non-owners.
- **`AUTH_ENABLED=false`**: anonymous access acts as the default user, the same as the prompt endpoints. Endpoints that change data use the configuration-level guard required by Constitution III.

**Rate limits**: import and replacement use the existing `expensive_limit` from slowapi, as `/import` does.

## Error format

Errors use the project's existing error body. The `code` field can be checked by programs, and the `message` field is shown to users (translated in the client from `code`).

```json
{ "detail": { "code": "SKILL_MD_MISSING", "message": "SKILL.md not found at the archive root or in a single top-level folder", "offending_entry": null } }
```

| HTTP | `code` | When |
|---|---|---|
| 400 | `ARCHIVE_INVALID` | Not a zip file, corrupt, or empty |
| 400 | `ARCHIVE_ENCRYPTED` | Password-protected entries |
| 400 | `SKILL_MD_MISSING` | FR-005 |
| 400 | `ENTRY_PATH_UNSAFE` | Absolute path or `..` escaping the skill root (`offending_entry` set) |
| 400 | `ENTRY_LINK` | Symbolic link entry (`offending_entry` set) |
| 400 | `ENTRY_NAME_INVALID` | Name invalid on common operating systems (`offending_entry` set) |
| 400 | `ENTRY_DUPLICATE` | Duplicate path, including a case-only difference (`offending_entry` set) |
| 400 | `LIMIT_DEPTH` | More folder levels than `SKILL_MAX_DEPTH` |
| 400 | `LIMIT_FILE_COUNT` | More files than `SKILL_MAX_FILES` |
| 400 | `LIMIT_FILE_SIZE` | One file over `SKILL_MAX_FILE_BYTES` (`offending_entry` set) |
| 400 | `LIMIT_TOTAL_SIZE` | Total uncompressed size over `SKILL_MAX_TOTAL_BYTES` |
| 400 | `ARCHIVE_SUSPICIOUS_RATIO` | Compression ratio over `SKILL_MAX_COMPRESSION_RATIO` |
| 400 | `LIMIT_SKILL_MD_SIZE` | `SKILL.md` over `SKILL_MAX_SKILL_MD_BYTES` |
| 413 | `LIMIT_UPLOAD_SIZE` | Upload over `SKILL_MAX_UPLOAD_BYTES`. Returned before the body is read when `Content-Length` is over the limit, otherwise as soon as the streamed body passes it (research.md Decision 9). |
| 404 | `SKILL_NOT_FOUND` / `FILE_NOT_FOUND` | Unknown id, not owned by the caller, or unknown path |
| 409 | `ITEM_IS_SKILL` | A prompt-only endpoint was called on a skill |
| 409 | `ITEM_IS_PROMPT` | A skill endpoint was called on a prompt |

Every 400 and 413 above also writes the audit event `skill.import.rejected` or `skill.replace.rejected` (FR-025b).

## Shared response objects

```jsonc
// SkillSummary: embedded in list and search results through item_type.
// It deliberately has no `prompt` field: clients fetch SkillDetail from
// /api/skills/{id} before showing instructions.
{
  "id": 42, "item_type": "skill", "title": "pdf-tools",
  "skill_identifier": "pdf-tools", "description": "Fill PDF forms…",
  "category": "Docs", "tags": ["pdf"], "favorite": false,
  "file_count": 7, "total_bytes": 182044,
  "format_warnings": [], "created_at": "…", "updated_at": "…"
}

// SkillDetail = SkillSummary plus:
{
  "note": "…",
  "instructions_html": "<h1>…</h1>…",   // sanitised (research.md Decision 6), frontmatter removed
  "files": [ { "path": "SKILL.md", "size": 3412, "is_text": true, "sha256": "…" },
             { "path": "references/guide.pdf", "size": 1820554, "is_text": false, "sha256": "…" } ]
}
```

## Endpoints

### `POST /api/skills/import` — create a skill (FR-004–FR-011)

- **Request**: `multipart/form-data` with `archive` (the file, required) and optionally `category` and `tags` (comma-separated).
- **201**: `{ "skill": SkillDetail, "warnings": ["name_missing", …] }`. `warnings` is the same list as `format_warnings` and is shown as a non-blocking notice.
- **Errors**: see the table. Nothing is stored on any error.
- **Audit**: `skill.import` (FR-025a).

### `GET /api/skills/{id}` — skill detail (FR-013, FR-015)

- **200**: `SkillDetail`. **404**: `SKILL_NOT_FOUND`. **409**: `ITEM_IS_PROMPT`.

### `GET /api/skills/{id}/files/content?path=<relative path>` — view a file (FR-016)

- **200**: `{ "path", "size", "is_text", "truncated": bool, "text": string | null }`. `text` is cut to `SKILL_TEXT_PREVIEW_BYTES`. For binary files `text` is null and `truncated` is false.
- **404**: `FILE_NOT_FOUND`.

### `GET /api/skills/{id}/files/raw?path=<relative path>` — download one file (FR-018)

- **200**: the raw bytes, with `Content-Type: application/octet-stream`, `Content-Disposition: attachment; filename*=UTF-8''<basename>`, `X-Content-Type-Options: nosniff`, and `Content-Security-Policy: sandbox`.

### `GET /api/skills/{id}/download` — export as a zip (FR-019, FR-020)

- **200**: a streamed `application/zip` with `Content-Disposition: attachment; filename="<skill_identifier>.zip"`. Every entry is `<skill_identifier>/<path>`. The archive is built per request and never stored.

### `PATCH /api/skills/{id}` — edit metadata (FR-021)

- **Request (JSON)**: any of `title` (1–200 characters), `category` (string or null), `tags` (string[]), `note`, `favorite`.
- **200**: `SkillDetail`. This never creates a version. Files, `prompt`, description and identifier cannot be changed here; sending those fields returns 422.

### `PUT /api/skills/{id}/archive` — replace the files (FR-022)

- **Request**: `multipart/form-data` with `archive`.
- **200**: `{ "skill": SkillDetail, "warnings": [...] }`. The title, note, favorite, category and tags are kept. Description, identifier, `prompt` and files are replaced.
- **Errors**: same as import. On any error the skill is left unchanged.
- **Audit**: `skill.replace` or `skill.replace.rejected`.

### `DELETE /api/skills/{id}` — delete (FR-023)

- **204**. The cascade removes the files. The client shows its own confirmation dialog first (FR-023).
- **Audit**: `skill.delete` with `skill_identifier`, `file_count` and `total_bytes`.

## Changes to existing endpoints

| Endpoint | Change |
|---|---|
| `GET /api/prompts`, `GET /api/prompts/search` | New query parameter `item_type` = `all` (default), `prompt` or `skill` (FR-002). Every result gains `item_type`. A prompt result retains its required `prompt` body; a skill result is a `SkillSummary` and deliberately omits `prompt`. Skill results carry `skill_identifier`, `description`, `file_count`, `total_bytes` and `format_warnings`. Full-text matches on the `SKILL.md` text return the usual `match_context` snippet (FR-024). |
| `GET /api/prompts/{id}` | Includes `item_type`. For a skill it returns `SkillSummary` (without `prompt`); the client uses `/api/skills/{id}` for the detail view. |
| `PUT`/`PATCH /api/prompts/{id}`, version, branch, revert, `copy-with-version` and sharing endpoints | **409 `ITEM_IS_SKILL`** when the target is a skill (FR-003) |
| `PUT /api/prompts/{id}/favorite` | Works for skills unchanged |
| `DELETE /api/prompts/{id}` and `DELETE /api/prompts/bulk` | Work for skills (cascade). Write one `skill.delete` audit event per skill. |
| `POST /api/prompts` | Always creates `item_type = 'prompt'`. An `item_type` field in the request body is ignored. |
| `POST /export`, `POST /import` (bulk) | Prompts only. Replace clears prompts only (FR-024a). The export response gains `skills_excluded: <count>` so the interface can show the notice. |
| `GET /import-export/stats` | Adds `skill_count` |
