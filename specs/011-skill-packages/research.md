# Research: Skill Packages

**Feature**: 011-skill-packages | **Date**: 2026-11-12

This file records the design decisions made for the skill packages feature. Each decision gives what was chosen, why, and what else was considered.

## Decision 1 — Skills are rows in the existing `prompts` table, marked with an `item_type` column

- **Decision**: Add `item_type VARCHAR(16) NOT NULL DEFAULT 'prompt'` to `prompts`, with a check that the value is `prompt` or `skill`, and an index. A skill is a `prompts` row with `item_type = 'skill'`. The row's `prompt` column holds the full `SKILL.md` text. Data that only skills have lives in two new tables: `skill_packages`, one row per skill, and `skill_files`, one row per file.
- **Rationale**:
  - Lists, pagination (005), visibility rules, categories, tags, favorites and full-text search (008) already work on `prompts`. A mixed list filtered by type (FR-002) becomes a single `WHERE item_type = ?` clause, not a UNION across two tables that would break the paging totals 005 relies on.
  - The full-text index from 008 already covers `(title, prompt, note)`, through FTS5 triggers on SQLite and a generated `search_vector` column on PostgreSQL. Storing the `SKILL.md` text in `prompt` makes the instructions and the frontmatter `description` searchable (FR-024) with no change to the search code.
  - Existing rows get `'prompt'` from the server default, so they need no data migration (FR-001, SC-005).
- **Alternatives considered**:
  - *A separate `skills` table*. This would leave prompts completely untouched, but the mixed list, search, tag counts and category counts would all need a UNION or two queries merged in Python. Paging totals and relevance ranking across the two sources would then disagree. Rejected.
  - *Single-table inheritance in SQLAlchemy (`polymorphic_on`)*. Rejected for v1. Every `session.query(Prompt)` call would start returning subclass instances, which is a much larger change than an explicit filter in the few places that need one (Decision 7).

## Decision 2 — File contents stored in the database as binary columns

- **Decision**: `skill_files.content` is `LargeBinary`, which becomes `BYTEA` on PostgreSQL and `BLOB` on SQLite. Nothing about skills is written to the filesystem.
- **Rationale**:
  - Constitution Principle V requires new features to keep their data in the database.
  - Backups need no changes. `SqliteDumpStrategy` uses the SQLite backup API and `PostgresDumpStrategy` uses `pg_dump`, so skills are included automatically (FR-026).
  - A whole import or replacement is one transaction. If it fails, everything rolls back and leaves nothing behind (FR-010), with no temporary folders or orphan cleanup.
  - Files are read through the same owner-scoped queries as the skill itself (FR-014). No file path is ever exposed.
  - The limits keep this practical: 50 MB per skill and 10 MB per file. Both PostgreSQL `BYTEA` and the SQLite default `SQLITE_MAX_LENGTH` (1 GB) handle values far larger than that.
- **Alternatives considered**: storing files on disk under `PROMPTVAULT_DATA_DIR`, with only paths and hashes in the database. Rejected because it would need a constitution exception, new backup and restore code, and a way to keep the dump and the files consistent. Worth revisiting only if the limits grow to hundreds of MB.

## Decision 3 — Reading the zip safely with the standard library

- **Decision**: Use `zipfile` from the standard library and never call `extractall()`. A `SkillArchiveReader` makes two passes:
  1. **Check the central directory**, before reading any file content. It checks:
     - the number of entries against the file-count limit;
     - the declared uncompressed sizes against the per-file and total limits;
     - the compression ratio of each entry (`file_size / compress_size > 100` with `file_size > 1 MB` counts as a bomb);
     - each path, by normalising separators, rejecting absolute paths and `..` segments, and rejecting names that are invalid on Windows or macOS (`<>:"|?*`, control characters, trailing dot or space, reserved names such as `CON`);
     - folder depth;
     - duplicate paths, compared case-insensitively;
     - symbolic links, detected from the Unix mode in `external_attr >> 16` (`stat.S_ISLNK`);
     - encrypted entries (`flag_bits & 0x1`).
  2. **Read the contents** with `ZipFile.open()` in chunks, counting the bytes actually read. It aborts as soon as a file or the running total passes its limit, so a header that lies about its size cannot get round the check.
- **Rationale**: `zipfile` cannot be told to stop extracting at a size limit, and its headers can lie. Reading everything into memory with live byte counts protects against both. Archive entries are never extracted to disk, so path traversal cannot reach the filesystem. (The raw upload itself may be spooled to a temporary file by the framework, see Decision 9.) Paths are still checked, because the stored paths are what a later export writes.
- **Hard links**: the zip format has no hard-link entries. Hard links collapse into ordinary files when the archive is created, so they need no special handling.
- **Clutter filtering (FR-009)**: these entries are skipped before any check, as if they were not in the archive at all: `__MACOSX/`, `.DS_Store`, `Thumbs.db`, and AppleDouble files (`._*`). They do not count toward the limits.
- **Skill root (FR-005)**: after clutter is removed, the root is the archive root if it contains `SKILL.md`. Otherwise it is the single top-level folder, when there is exactly one and it contains `SKILL.md`. In any other case the upload is rejected.
- **Alternatives considered**: `shutil.unpack_archive`, rejected because it does no checks; third-party "safe zip" libraries, rejected because the checks above are short and testable and an extra dependency adds supply-chain risk.

## Decision 4 — Frontmatter parsing with PyYAML `safe_load`

- **Decision**: Split off the frontmatter block, from `---` on line 1 to the next `---` line, and parse it with `yaml.safe_load`. Anything above 64 KB of frontmatter or nesting deeper than 20 levels counts as malformed. Check the Agent Skills rules (FR-006) and collect warning codes; never reject over frontmatter. Store `SKILL.md` byte for byte (FR-012b).
- **Rationale**: Skill frontmatter can contain nested `metadata` maps and lists, which a hand-written parser would get wrong. PyYAML is already installed as a dependency of `uvicorn[standard]`, and it will now be declared explicitly in `pyproject.toml`. `safe_load` cannot build arbitrary objects.
- **Warning codes** (stored in `skill_packages.format_warnings` and translated in the interface):

| Code | Rule broken |
|---|---|
| `frontmatter_missing` | No frontmatter block |
| `frontmatter_malformed` | Not valid YAML, not a mapping, or over the size or depth cap |
| `name_missing` | No `name` field |
| `name_invalid` | `name` is not `^[a-z0-9]+(-[a-z0-9]+)*$` or is over 64 characters |
| `name_folder_mismatch` | `name` differs from the wrapping folder name |
| `description_missing` | No `description` field |
| `description_too_long` | `description` is over 1,024 characters |
| `no_wrapping_folder` | `SKILL.md` was at the archive root |
| `skill_md_not_utf8` | `SKILL.md` is not valid UTF-8 (decoded with replacement characters for display and search) |

- **Encoding**: `SKILL.md` is decoded as UTF-8 for the `prompt` column, with a leading byte-order mark removed. The original bytes stay in `skill_files` for byte-exact export.

## Decision 5 — Skill identifier

- **Decision**: If the frontmatter `name` follows the format rules, it becomes the identifier. Otherwise the identifier is a slug made from `name` if present, else from the archive file name without `.zip`. To make the slug: normalise with NFKD, drop non-ASCII characters, lowercase, turn runs of other characters into `-`, trim `-` from both ends, cut to 64 characters, and use `skill` if the result is empty. The identifier is stored in `skill_packages.skill_identifier`, which is not unique (names do not have to be unique). It is recalculated whenever the files are replaced (FR-012a).

## Decision 6 — Rendering `SKILL.md`

- **Decision**: Render on the server with `markdown-it-py` (CommonMark preset, raw HTML turned off, its default link checking that blocks `javascript:`, `vbscript:` and `data:` links). Then pass the result through `nh3` with an allow-list of tags and attributes, so the protection does not depend on a single library. Strip the frontmatter before rendering. The API returns `instructions_html`, and the frontend inserts it through the existing `raw()` wrapper in `safe-html.ts`.
- **Rationale**: The frontend has no Markdown library. Rendering on the server keeps sanitising in one place that is easy to test. With raw HTML turned off, `<script>` or `<img onerror>` in a `SKILL.md` comes out as escaped text. `nh3` (Rust `ammonia`) is the maintained successor to `bleach`.
- **Alternatives considered**: `marked` plus `DOMPurify` in the browser, rejected because it puts two new libraries in the frontend bundle and sanitises on the client; plain-text display, rejected because FR-015 requires formatted output.

## Decision 7 — Keeping prompt-only code paths away from skills

The only risk of using one table is that existing code treats every row as a prompt. Each affected path gets an explicit guard:

| Path | Today | Change |
|---|---|---|
| `PromptDataServiceDB.update_prompt` / `PUT` and `PATCH /api/prompts/{id}` | Overwrites `prompt` and creates a version | Return 409 `ITEM_IS_SKILL` for skills. Skill metadata is edited through `PATCH /api/skills/{id}`, which never creates versions. |
| Version, branch and revert endpoints | Work on any row | 409 `ITEM_IS_SKILL` |
| Sharing endpoints (007) | Work on any row | 409 `ITEM_IS_SKILL`. Skills are always created with `legacy_public = false`. |
| `POST /api/prompts` | Creates a prompt | Always creates `item_type = 'prompt'`; the client cannot set the type |
| `copy-with-version` | Copies a prompt | 409 for skills |
| `clear_all_prompts` (bulk import, Replace mode) | Deletes every row | Deletes only `item_type = 'prompt'` rows (FR-024a) |
| `load_prompts` and bulk export | Every row | Filtered to `item_type = 'prompt'` (FR-024a) |
| `PromptRepository.get_statistics` | Counts every row | Returns counts per type |
| Undo service (`undo_operations`) | Snapshots deleted prompts to restore them | Deleting a skill is not undoable in v1. The delete endpoint asks for confirmation (FR-023), and the undo service skips skill rows. |
| Bulk delete `DELETE /api/prompts/bulk` | Deletes rows | Allowed for skills; `skill_files` and `skill_packages` are removed by cascade. Audited per skill (FR-025a). |
| Placeholder detection (006, frontend) | Scans `prompt` text | Never run for `item_type = 'skill'` (FR-012b; `${CLAUDE_SKILL_DIR}` is not a PromptVault placeholder) |

## Decision 8 — Restoring old backups (FR-027)

- **Decision**: No code change is needed. A backup taken before this feature restores an older schema. The existing procedure applies, just as it did for the 007 and 008 migrations: `src/db/health.py` detects the outdated schema and `alembic upgrade head` brings it up to date. The new migration's server default `'prompt'` marks every restored row as a prompt. `quickstart.md` includes a test for this.

## Decision 9 — Limits and configuration

- **Decision**: A `SkillSettings(BaseSettings)` class in `src/config/skill_config.py`, following the pattern of `DatabaseSettings`:

| Variable | Default |
|---|---|
| `SKILL_MAX_UPLOAD_BYTES` | 10 MB (10_485_760) |
| `SKILL_MAX_TOTAL_BYTES` | 50 MB (52_428_800) |
| `SKILL_MAX_FILES` | 500 |
| `SKILL_MAX_DEPTH` | 10 |
| `SKILL_MAX_FILE_BYTES` | 10 MB (10_485_760) |
| `SKILL_MAX_COMPRESSION_RATIO` | 100 |
| `SKILL_TEXT_PREVIEW_BYTES` | 1 MB (1_048_576) |
| `SKILL_MAX_SKILL_MD_BYTES` | 1 MB (1_048_576) |

- **Enforcing the upload limit (fixes analysis finding U1)**: FastAPI's `UploadFile` is a `SpooledTemporaryFile` that moves to a temporary file on disk once it passes 1 MB. Multipart parsing happens before the route handler runs, so checking the size inside the handler is too late. Three layers make the limit hold:
  1. **Reject by `Content-Length`**: a route dependency `enforce_skill_upload_size` reads the `Content-Length` header and returns 413 `LIMIT_UPLOAD_SIZE` before the body is read, when the header is present and exceeds `SKILL_MAX_UPLOAD_BYTES` plus 64 KB for multipart overhead.
  2. **Count the streamed body**: a small ASGI middleware, `RequestBodyLimitMiddleware`, is applied only to `POST /api/skills/import` and `PUT /api/skills/{id}/archive`. It counts the bytes received and stops with 413 once the same limit is passed. This covers chunked uploads with no `Content-Length`.
  3. **Clean up**: `UploadFile.close()` runs in a `finally` block, so the spooled temporary file is always deleted.
- **Scope of the "no disk" rule**: archive *entries* are never extracted to disk. The raw upload may be spooled to the system temporary folder by the framework, with a bounded size, deleted at the end of the request, and never written under `PROMPTVAULT_DATA_DIR`.

## Decision 10 — Text detection, file viewer, downloads

- **Text vs binary**: a file is text when it has no NUL byte and decodes as UTF-8. This is checked once at import and stored in `skill_files.is_text`.
- **Viewer (FR-016)**: `GET /api/skills/{id}/files/content?path=…` returns JSON `{path, size, is_text, truncated, text}` for text files, cut to `SKILL_TEXT_PREVIEW_BYTES` at a character boundary. For binary files `text` is null. The frontend shows it with `textContent`, never as HTML.
- **Single-file download (FR-018)**: `GET /api/skills/{id}/files/raw?path=…` returns `Content-Type: application/octet-stream`, `Content-Disposition: attachment` with the file name encoded per RFC 5987, and `X-Content-Type-Options: nosniff`. The browser never renders bundled content inline (FR-017).
- **Whole-skill download (FR-019, FR-020)**: the zip is built when requested, using `zipfile` with `ZIP_DEFLATED`, written into a `SpooledTemporaryFile` (in memory up to 8 MB) and streamed back. Entries are `<skill_identifier>/<path>` and use a fixed timestamp (the skill's `updated_at`), so the same skill always exports the same bytes. Nothing is stored.

## Decision 11 — Audit events (FR-025a–c)

- **Decision**: Use `logging_service.log_audit_event` with `resource_type="skill"`. Actions: `skill.import`, `skill.replace`, `skill.delete`, `skill.import.rejected`, `skill.replace.rejected`. Context fields: `skill_identifier`, `file_count`, `total_bytes`. For rejections: `archive_name` and `reason_code`, plus `offending_entry` where it applies. File contents and lists of file names are never logged.

## Decision 12 — Frontend structure

- **Decision**: Add a new module folder `src/web/static/ts/skills/`, containing `skill-import.ts`, `skill-detail.ts`, `skill-file-tree.ts`, `skill-file-viewer.ts` and `skill-api.ts`. Skills open in their own detail view, not the prompt card or form. The existing list (`app/prompt-list.ts`, `app/prompt-card.ts`) gets a type badge, a type filter in `app/prompt-filters.ts`, and routing that opens a skill's detail view when a skill card is clicked. Uploads use `apiPostForm`, because `apiFetch` forces a JSON content type that breaks FastAPI form parsing. New strings go into all four locale files. `CACHE_VERSION` in `sw.ts` is bumped.
- **File tree**: built on the client from the flat `files[]` list returned by the API, with folders first and then alphabetical order (FR-015). It uses `role="tree"` and `role="treeitem"` and arrow-key navigation, reusing `utils/keyboard-nav.ts`.
