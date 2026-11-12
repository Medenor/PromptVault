---

description: "Task list for 011-skill-packages"
---

# Tasks: Skill Packages

**Input**: Design documents from `/specs/011-skill-packages/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/skills-api.md, quickstart.md

**Tests**: Included. Constitution II (≥ 85 % coverage, tests written alongside the code) makes them mandatory for every new endpoint and service method.

**Organization**: Tasks are grouped by user story so each story can be built and tested on its own.

> [!IMPORTANT]
> **Sequencing**: implementation starts only after `009-totp-2fa` and `010-docs-portal-i18n` are finalized and merged into `main`. Phase 1 (T001–T004) syncs this branch with that `main` before any code is written.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: The user story the task belongs to (US1–US5)
- Paths are relative to the repository root. Every new file gets the MPL 2.0 header (AGENTS.md).

---

## Phase 1: Setup (Resume & Shared Infrastructure)

**Purpose**: Line the branch up with `main` after 009 and 010 merge, and add dependencies and configuration.

- [ ] T001 Rebase branch `011-skill-packages` onto the current `main`, after 009 and 010 are merged, and confirm a clean `make test` baseline before any change
- [ ] T002 Run `alembic heads` and record the current head revision in `specs/011-skill-packages/data-model.md` (section "Migration"), replacing `c3d4e5f6a7b8` if 009 or 010 added migrations
- [ ] T003 Search for every query that reads all prompts (`grep -rn "PromptRepository(\|query(Prompt)\|select(Prompt)" src/`) and add any path introduced by 009 or 010 to the guard table in `specs/011-skill-packages/research.md` (Decision 7)
- [ ] T004 Add `PyYAML`, `markdown-it-py` and `nh3` to `[project].dependencies` in `pyproject.toml` and install them in the dev environment
- [ ] T005 [P] Create `SkillSettings(BaseSettings)` with the limits from research.md Decision 9 (`SKILL_MAX_UPLOAD_BYTES`, `SKILL_MAX_TOTAL_BYTES`, `SKILL_MAX_FILES`, `SKILL_MAX_DEPTH`, `SKILL_MAX_FILE_BYTES`, `SKILL_MAX_COMPRESSION_RATIO`, `SKILL_TEXT_PREVIEW_BYTES`, `SKILL_MAX_SKILL_MD_BYTES`) and a cached `get_skill_settings()` in `src/config/skill_config.py`
- [ ] T006 [P] Document the new `SKILL_*` variables with their defaults in `.env.example` and `docs/DEPLOYMENT.md`
- [ ] T007 [P] Create the package `src/services/skills/__init__.py` and `src/services/skills/errors.py`, defining `SkillArchiveError(code: str, message: str, offending_entry: str | None)` and the error code constants from `contracts/skills-api.md`
- [ ] T008 [P] Create the fixture builder `tests/fixtures/skills/build_fixtures.py`. It builds zips in memory at test time: a valid wrapped skill, a valid root-level skill, no frontmatter, a bad name, `__MACOSX` clutter, `../evil`, an absolute path, a symbolic link (via `external_attr`), a case-only duplicate, depth 11, 501 files, an oversized file, a high-ratio bomb, an encrypted flag, corrupt bytes, and non-UTF-8 `SKILL.md`. Expose them as pytest fixtures in `tests/fixtures/skills/conftest.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The item-type discriminator, tables, models and prompt-only guards. Once this phase ships, no skill exists yet and every prompt behaves exactly as before (SC-005).

**⚠️ CRITICAL**: No user story work starts until this phase is complete.

- [ ] T009 Write the Alembic migration `alembic/versions/d4e5f6a7b8c9_add_skill_packages.py`, with `down_revision` set to the head recorded in T002. It adds `prompts.item_type` (server default `'prompt'`, check constraint, index `idx_prompts_item_type`) through `batch_alter_table` and creates `skill_packages` and `skill_files` exactly as in data-model.md (`UNIQUE(prompt_id, path_folded)`, `ON DELETE CASCADE`, `sa.false()` for the `is_text` default). It uses `sa.inspect()` for existence checks. The downgrade refuses to run while skill rows exist.
- [ ] T010 [P] Add the `item_type: Mapped[str]` column, the `skill_package` relationship (one-to-one) and the `skill_files` relationship (cascade `all, delete-orphan`, `passive_deletes=True`) to `src/db/models/prompt.py`
- [ ] T011 [P] Create the `SkillPackage` model in `src/db/models/skill_package.py`, with the fields from data-model.md and `format_warnings` as `JSON`
- [ ] T012 [P] Create the `SkillFile` model in `src/db/models/skill_file.py` with `content` as `LargeBinary`, and `content` deferred by default (`deferred=True`)
- [ ] T013 Register the new models in `src/db/models/__init__.py`, after T011 and T012
- [ ] T014 [P] Write the migration test in `tests/integration/test_skill_migration.py`. It checks that the migration upgrades on SQLite (and on PostgreSQL when `TEST_DATABASE_URL` is set), that existing rows get `item_type='prompt'`, that the check constraint rejects `'foo'`, and that the downgrade is blocked when a skill row exists.
- [ ] T015 Add an `item_type: str | None` parameter (`'prompt'`, `'skill'` or None for all) to `_apply_common_filters`, `search()` and `count()` in `src/db/repositories/prompt_repository.py`, and make `get_statistics()` return `prompt_count` and `skill_count`
- [ ] T016 Create `SkillRepository` in `src/db/repositories/skill_repository.py` with:
  - `get_package(prompt_id)`
  - `list_files(prompt_id)`, which never loads `content`
  - `get_file(prompt_id, path)`, which loads `content`
  - `iter_file_contents(prompt_id)`
  - `insert_files(prompt_id, files)`
  - `delete_files(prompt_id)`
  - `upsert_package(...)`
- [ ] T017 [P] Write repository tests in `tests/unit/test_skill_repository.py`: the `item_type` filter in `search`/`count`, the case-insensitive uniqueness constraint, cascade on delete, and `list_files` not loading `content`
- [ ] T018 Add `ItemIsSkillError` and `ItemIsPromptError` to `src/services/exceptions.py`, and map them to 409 `ITEM_IS_SKILL` and 409 `ITEM_IS_PROMPT` in the existing exception handlers in `src/web/routers/prompts_shared.py`
- [ ] T019 Add a guard `_ensure_prompt_item(prompt)` that raises `ItemIsSkillError` (from T018) to `src/services/prompt_data_service_db.py`. Apply it in `update_prompt`, `revert_prompt_to_version` and `copy-with-version` handling. Restrict `clear_all_prompts` and `load_prompts` to `item_type='prompt'`. Make `add_new_prompt` always set `item_type='prompt'`.
- [ ] T020 [P] Return 409 `ITEM_IS_SKILL` for skill targets in the version, branch and revert endpoints in `src/web/routers/prompts_versions_router.py`
- [ ] T021 [P] Return 409 `ITEM_IS_SKILL` for skill targets in every endpoint of `src/web/routers/prompts_sharing_router.py`
- [ ] T022 Add `item_type` to every prompt response model, and the optional skill summary fields (`skill_identifier`, `description`, `file_count`, `total_bytes`, `format_warnings`), in `src/web/models/prompt_responses.py`. Fill them in `_prompt_to_dict` in `src/services/prompt_data_service_db.py`.
- [ ] T023 Add the `item_type` query parameter (`all`, `prompt` or `skill`, default `all`) to the list and search endpoints in `src/web/routers/prompts_search_router.py` and `src/web/routers/prompts_crud_router.py`, passed through to the repository
- [ ] T024 Make the undo service skip skill rows when capturing and restoring deletions, in `src/services/undo_service.py`
- [ ] T025 Make bulk export prompts-only, return `skills_excluded: int` in the export response, and add `skill_count` to the stats endpoint, in `src/services/prompt_import_export_service.py` and `src/web/routers/import_export_router.py`
- [ ] T026 [P] Write the guard tests in `tests/integration/test_skill_prompt_guards.py`, using a skill row inserted straight through the repository:
  - `PUT`/`PATCH /api/prompts/{id}`, versions, revert, `copy-with-version` and sharing each return 409 and create no `prompt_versions` row;
  - a bulk import in Replace mode keeps the skill;
  - bulk export leaves it out and reports `skills_excluded=1`;
  - `POST /api/prompts` ignores `item_type`.

**Checkpoint**: run `make test`. Every existing suite passes unchanged (SC-005) and the guards are proven.

---

## Phase 3: User Story 1 — Import a skill from a zip archive (Priority: P1) 🎯 MVP

**Goal**: Users upload a `.zip` and get a skill item marked as a skill in the vault list, with leniently checked frontmatter and malicious archives rejected.

**Independent Test**: Quickstart Scenarios 1 (import part), 2 and 4. A valid zip gives 201 with a skill badge in the list. Each malicious fixture is rejected with its error code, with no rows added and one audit event.

### Tests for User Story 1

- [ ] T027 [P] [US1] Write parametrised unit tests in `tests/unit/test_skill_archive_reader.py`, covering:
  - every malicious fixture → expected `SkillArchiveError.code` and `offending_entry`;
  - clutter skipped and not counted toward limits;
  - root detection for wrapped and root-level archives;
  - empty folders dropped;
  - stored paths free of the wrapping folder name;
  - a header that lies about its size still caught by the live byte count.
- [ ] T028 [P] [US1] Write unit tests in `tests/unit/test_skill_frontmatter.py`, covering:
  - each warning code from research.md Decision 4;
  - a byte-order mark removed;
  - non-UTF-8 handling;
  - `yaml.safe_load` refusing a `!!python/object` tag;
  - the 64 KB and depth caps;
  - the identifier slug rules (Decision 5: non-ASCII, empty result → `skill`, cut to 64 characters).
- [ ] T029 [P] [US1] Write integration tests for `POST /api/skills/import` in `tests/integration/test_skills_api.py`, covering:
  - 201 with the `SkillDetail` shape;
  - warnings returned;
  - every rejection → 400 or 413 with nothing stored (row counts unchanged);
  - a `skill.import` or `skill.import.rejected` audit record without contents;
  - with auth on: 401 when not signed in;
  - the rate limit applied.
- [ ] T030 [P] [US1] Write upload-limit tests in `tests/integration/test_skills_upload_limits.py`, covering:
  - a `Content-Length` over the limit gets 413 `LIMIT_UPLOAD_SIZE` before the body is read (assert the handler and `SkillService` are never called);
  - a chunked upload with no `Content-Length` gets 413 as soon as the streamed bytes pass the limit;
  - the spooled temporary file is deleted after both success and rejection (no leftover files in the temp folder);
  - nothing is ever written under `PROMPTVAULT_DATA_DIR`.
- [ ] T031 [P] [US1] Write auth-mode tests in `tests/integration/test_skills_auth_modes.py`, for the import, replace and delete endpoints (Constitution III, FR-025):
  - With `AUTH_ENABLED=false`: they apply the same configuration-level guard as the matching prompt endpoints (`POST /api/prompts`, `PUT /api/prompts/{id}`, `DELETE /api/prompts/{id}`), so each is allowed or refused exactly as its prompt counterpart is under the same configuration.
  - With `AUTH_ENABLED=true`: a non-owner gets 404 on every skill endpoint. An administrator gets 200 on read, file and download endpoints and 204 on delete, but 404 on `PATCH` and `PUT /archive` for another user's skill.

### Implementation for User Story 1

- [ ] T032 [P] [US1] Implement `SkillArchiveReader.read(data: bytes, archive_name: str) -> ReadArchive` in `src/services/skills/archive_reader.py`, as described in research.md Decision 3:
  - clutter filtering first;
  - a central-directory pass (count, declared sizes, ratio, path normalisation and validation, depth, folded duplicates, symbolic links from `external_attr`, encrypted flag);
  - root detection;
  - reading contents in chunks with live per-file and total byte limits, plus the separate `SKILL_MAX_SKILL_MD_BYTES` limit on `SKILL.md` (`LIMIT_SKILL_MD_SIZE`);
  - text detection (no NUL byte and valid UTF-8).

  It returns the files (path, bytes, size, sha256, is_text), a `wrapped_folder_name` and `has_wrapping_folder`.
- [ ] T033 [P] [US1] Implement `parse_skill_md(raw: bytes, wrapped_folder_name: str | None, archive_name: str) -> SkillMetadata` (`name`, `description`, `text`, `warnings`, `identifier`, `title`) in `src/services/skills/frontmatter.py`
- [ ] T034 [US1] Implement `SkillService.import_skill(upload_bytes, archive_name, user, category, tags)` in `src/services/skills/skill_service.py`. In one `get_db_session()` transaction it creates the `prompts` row (`item_type='skill'`, `prompt` = the `SKILL.md` text, `legacy_public=False`, title cut to 200 characters), the `skill_packages` row and the `skill_files` rows. It writes the `skill.import` audit event, or `skill.import.rejected` with `reason_code` on a `SkillArchiveError`. It depends on T032 and T033.
- [ ] T035 [P] [US1] Create the Pydantic models `SkillDetailResponse`, `SkillSummary`, `SkillFileEntry` and `SkillImportResponse` in `src/web/models/skill_responses.py`, and `SkillUpdateRequest` with `extra='forbid'` in `src/web/models/skill_requests.py`
- [ ] T036 [US1] Implement the upload size limit described in research.md Decision 9. Create the route dependency `enforce_skill_upload_size` in `src/web/dependencies/skill_upload.py`: it returns 413 `LIMIT_UPLOAD_SIZE` from `Content-Length` before the body is read. Create `RequestBodyLimitMiddleware` in `src/web/middleware/request_body_limit.py`: it counts streamed bytes and stops with 413, and applies only to `POST /api/skills/import` and `PUT /api/skills/{id}/archive`. Register the middleware where the app's other middleware is added.
- [ ] T037 [US1] Create `src/web/routers/skills_router.py` (prefix `/skills`, tag `Skills`) with `POST /import`. It applies `enforce_skill_upload_size` (from T036), reads the `UploadFile` into memory, and closes it in a `finally` block so the spooled temporary file is always deleted. It uses the same auth dependencies and anonymous-mode guard as the matching `prompts_crud_router.py` endpoints, applies the `expensive_limit` rate limit, and maps `SkillArchiveError` to the error body in the contract. Register it under `/api` wherever the prompt routers are included.
- [ ] T038 [P] [US1] Create the typed client in `src/web/static/ts/skills/skill-api.ts`, with `importSkill(file, category?, tags?)` using `apiPostForm` (never `apiFetch` for `FormData`) and the exported interfaces `SkillSummary`, `SkillDetail`, `SkillFileEntry` and `SkillApiError`
- [ ] T039 [US1] Build the import dialog in `src/web/static/ts/skills/skill-import.ts`, using `components/Modal.ts`:
  - a file input limited to `.zip`;
  - optional category and tags;
  - a progress state;
  - a translated rejection message from `code`, with `offending_entry` shown as text;
  - a non-blocking warning notice listing the translated warning codes;
  - on success, open the new skill.

  Add an "Import skill" entry point next to the create-prompt action in `src/web/templates/index.html`.
- [ ] T040 [P] [US1] Add a type badge (Prompt or Skill, with an `aria-label`) to cards in `src/web/static/ts/app/prompt-card.ts`, and hide the placeholder, version and share actions for `item_type === 'skill'` in `src/web/static/ts/app/prompt-crud.ts` and `src/web/static/ts/app/prompt-card.ts`
- [ ] T041 [P] [US1] Add the `skills.import.*`, `skills.badge.*`, `skills.warnings.<code>` and `skills.errors.<code>` keys to `src/web/static/locales/en.json`, `fr.json`, `es.json` and `de.json`
- [ ] T042 [P] [US1] Write Vitest tests in `src/web/static/ts/skills/__tests__/skill-api.test.ts`, `skill-import.test.ts` and `src/web/static/ts/app/__tests__/prompt-card.skill.test.ts`. They cover: the form upload, the error and warning rendering (all through `textContent`), the badge, and the prompt-only actions being hidden.

**Checkpoint**: importing works from start to finish. Scenarios 1 (import part), 2 and 4 pass.

---

## Phase 4: User Story 2 — Browse and read a stored skill (Priority: P1)

**Goal**: The skill detail view shows the metadata, the rendered instructions, a file tree, a read-only text viewer, and a download option for binary files.

**Independent Test**: Quickstart Scenario 1 (browse part). The tree is in the right order, text files show as text, binary files show size and download, `${CLAUDE_SKILL_DIR}` stays literal, and `<script>` in `SKILL.md` appears as escaped text.

### Tests for User Story 2

- [ ] T043 [P] [US2] Write unit tests in `tests/unit/test_skill_markdown_renderer.py`. They check that frontmatter is removed and that `<script>`, `<img onerror>`, `javascript:`, `data:` links and raw HTML blocks all produce no active markup. Headings, lists, code blocks and links survive.
- [ ] T044 [P] [US2] Write integration tests in `tests/integration/test_skills_api_browse.py` for:
  - `GET /api/skills/{id}`: shape, 404 for another user's skill, 409 for a prompt id;
  - `GET .../files/content`: truncation at `SKILL_TEXT_PREVIEW_BYTES` at a character boundary, `text` null for binary files, 404 for an unknown path;
  - `GET .../files/raw`: exact bytes, plus the `Content-Disposition`, `nosniff` and `CSP: sandbox` headers.

### Implementation for User Story 2

- [ ] T045 [P] [US2] Implement `render_instructions(skill_md_text: str) -> str` in `src/services/skills/markdown_renderer.py`, using `markdown-it-py` (CommonMark preset, `html=False`) and then `nh3.clean` with an explicit allow-list of tags and attributes. Links get `rel="noopener noreferrer nofollow"`.
- [ ] T046 [US2] Add `get_skill_detail(id, user)`, `get_file_preview(id, path, user)` and `get_file_raw(id, path, user)` to `src/services/skills/skill_service.py`, with owner-scoped visibility through `PromptRepository._apply_visibility_filter` (the shared branch never matches, since skills are never shared). Administrators use the unscoped path and see every skill (contract "Auth"). Write methods (`update_skill_metadata`, `replace_skill_archive`) always require ownership, even for administrators.
- [ ] T047 [US2] Add `GET /{id}`, `GET /{id}/files/content` and `GET /{id}/files/raw` to `src/web/routers/skills_router.py`. The raw endpoint uses a `Response` with the headers from the contract and an RFC 5987 `filename*`.
- [ ] T048 [P] [US2] Build the file tree in `src/web/static/ts/skills/skill-file-tree.ts`. It builds a nested tree from the flat `files[]` list (folders first, then by `localeCompare`), uses `role="tree"`, `role="treeitem"` and `aria-expanded`, has arrow-key navigation through `utils/keyboard-nav.ts`, and emits `onSelect(path)`.
- [ ] T049 [P] [US2] Build the file viewer in `src/web/static/ts/skills/skill-file-viewer.ts`. It shows text in a `<pre>` through `textContent` with a truncation notice, and name, size and download link for binary files and truncated files.
- [ ] T050 [US2] Build the detail view in `src/web/static/ts/skills/skill-detail.ts`. It shows the header (title, description, category, tags, note, file count, readable total size, format warnings), the instructions through `raw()` from `utils/safe-html.ts`, and the tree and viewer in a two-column layout on large screens and stacked on mobile (Tailwind). Opening a skill card in `src/web/static/ts/app/prompt-list.ts` routes here instead of the prompt form.
- [ ] T051 [P] [US2] Add the `skills.detail.*`, `skills.tree.*` and `skills.viewer.*` keys to all four locale files in `src/web/static/locales/`
- [ ] T052 [P] [US2] Write Vitest tests in `src/web/static/ts/skills/__tests__/skill-file-tree.test.ts`, `skill-file-viewer.test.ts` and `skill-detail.test.ts`. They cover tree order and nesting, keyboard navigation, text and binary rendering, XSS-shaped file text shown as text, and routing from the card.

**Checkpoint**: the MVP (US1 and US2) is complete. Import, then open and read any file.

---

## Phase 5: User Story 3 — Download a skill as a zip (Priority: P2)

**Goal**: Export rebuilds a standard-layout archive `<skill-id>.zip` containing `<skill-id>/…`, byte-identical to the stored files and built for each request.

**Independent Test**: Quickstart Scenario 3: `diff -r` prints IDENTICAL, `skills-ref validate` passes, and the archive keeps the identifier name after the title is renamed.

### Tests for User Story 3

- [ ] T053 [P] [US3] Write unit tests in `tests/unit/test_skill_archive_writer.py`, covering:
  - entries prefixed with the identifier;
  - the same bytes produced twice (fixed timestamps);
  - sha256 matching for every file;
  - round trip: writer output → reader → the same files with no warnings;
  - SC-008: when `skills-ref` is on `PATH` (`shutil.which`), extract a warning-free exported archive into `tmp_path` and assert that `skills-ref validate <dir>` exits 0. Otherwise the test is skipped with a reason. Add `skills-ref` to the CI image or document it in `docs/TESTING.md`.
- [ ] T054 [P] [US3] Write integration tests in `tests/integration/test_skills_api_export.py` for `GET /api/skills/{id}/download`: the headers, the archive name staying the identifier after a title change, 404 for another user's skill, and nothing stored after a download

### Implementation for User Story 3

- [ ] T055 [P] [US3] Implement `write_skill_archive(identifier, files_iter, timestamp) -> SpooledTemporaryFile` in `src/services/skills/archive_writer.py`, using `ZIP_DEFLATED`, `max_size` 8 MB, and `ZipInfo.date_time` from `files_updated_at`
- [ ] T056 [US3] Add `export_skill(id, user)` to `src/services/skills/skill_service.py`, streaming the contents through `SkillRepository.iter_file_contents`, and add `GET /{id}/download` returning a `StreamingResponse` to `src/web/routers/skills_router.py`
- [ ] T057 [US3] Add a Download button to `src/web/static/ts/skills/skill-detail.ts`, using a plain link so the browser saves the file, and a `downloadSkillUrl(id)` helper to `skill-api.ts`. Add the `skills.download.*` keys to all four locale files.

**Checkpoint**: export is byte-exact and accepted by the reference validator.

---

## Phase 6: User Story 4 — Organize, edit, replace and delete skills (Priority: P2)

**Goal**: Users edit metadata, filter by type, find skills through search, replace the files with a new zip (keeping the title and metadata), and delete with confirmation, with audit events throughout.

**Independent Test**: Quickstart Scenario 5 (steps 1 to 4) and Scenario 6.

### Tests for User Story 4

- [ ] T058 [P] [US4] Write integration tests in `tests/integration/test_skills_api_manage.py`, covering:
  - `PATCH`: allowed fields; 422 for `prompt`, `description` or `skill_identifier`; no version row created.
  - `PUT /archive`:
    - the title, note, tags, category and favorite are kept;
    - the identifier and description are refreshed even when the new `name` differs;
    - a rejected replacement leaves the files and row byte-identical;
    - the `skill.replace` and `skill.replace.rejected` audit events are written.
  - `DELETE`: 204, cascade (no orphan `skill_files` or `skill_packages` rows), the `skill.delete` audit event, and bulk delete writing one `skill.delete` per skill.
- [ ] T059 [P] [US4] Write search tests in `tests/integration/test_skill_search.py`, parametrised over both dialects. A term that appears only in the `SKILL.md` body matches with a `match_context` snippet. A term that appears only in a bundled script does not match. The type filter returns only the matching type. After a replacement, the old body term no longer matches and the new one does.

### Implementation for User Story 4

- [ ] T060 [US4] Add `update_skill_metadata(id, request, user)` to `src/services/skills/skill_service.py`, reusing the category and tag normalisation from `PromptDataServiceDB` and never creating a version, and add `PATCH /{id}` to `src/web/routers/skills_router.py`
- [ ] T061 [US4] Add `replace_skill_archive(id, upload_bytes, archive_name, user)` to `src/services/skills/skill_service.py`. It reads and checks the archive before touching the database, then in one transaction deletes the old files, inserts the new ones, updates `skill_packages` (identifier, description, warnings, totals, `source_archive_name`, `files_updated_at`) and `prompts.prompt`, keeping the title and metadata. It writes the audit events. Add `PUT /{id}/archive` to `src/web/routers/skills_router.py`.
- [ ] T062 [US4] Add `delete_skill(id, user)` with the `skill.delete` audit event to `src/services/skills/skill_service.py`, add `DELETE /{id}` to `src/web/routers/skills_router.py`, and write one `skill.delete` event per skill in the bulk-delete path in `src/services/prompt_data_service_db.py` (`delete_prompt`, `delete_prompts_bulk`)
- [ ] T063 [P] [US4] Add the type filter (All, Prompts, Skills) to `src/web/static/ts/app/prompt-filters.ts` and pass `item_type` through the list and search requests in `src/web/static/ts/app/prompt-list.ts` and `src/web/static/ts/app/search.ts`. The filter is kept in the URL query like the other filters.
- [ ] T064 [US4] Add an edit-metadata form (reusing the tag autocomplete from `app/tag-autocomplete.ts`), a "Replace files" upload (reusing the error and warning rendering from `skill-import.ts`) and a Delete action to `src/web/static/ts/skills/skill-detail.ts`. Delete uses the confirmation dialog from `utils/dialogs.ts`, whose message (`skills.delete.confirmPermanent`) says that deletion is permanent and cannot be undone (FR-023). No undo toast is shown after deleting a skill.
- [ ] T065 [P] [US4] Add the notice "Skills are not included; export them one at a time from each skill", shown when `skills_excluded > 0` or always, to `src/web/templates/import_export.html` and `src/web/static/ts/import-export.ts`
- [ ] T066 [P] [US4] Add the `skills.edit.*`, `skills.replace.*`, `skills.delete.*`, `filters.itemType.*` and `importExport.skillsExcluded` keys to all four locale files
- [ ] T067 [P] [US4] Write Vitest tests in `src/web/static/ts/app/__tests__/prompt-filters.item-type.test.ts`, `src/web/static/ts/skills/__tests__/skill-detail.manage.test.ts` and `src/web/static/ts/__tests__/import-export.skills-notice.test.ts`

**Checkpoint**: Scenarios 5 and 6 pass.

---

## Phase 7: User Story 5 — Skills survive backup and restore (Priority: P2)

**Goal**: Backups include skills, restore is byte-exact, and backups taken before this feature still restore. No production code change is expected (research.md Decisions 2 and 8).

**Independent Test**: Quickstart Scenario 7.

- [ ] T068 [P] [US5] Write a round-trip test in `tests/integration/test_skill_backup_roundtrip.py`, following the pattern in `tests/integration/test_backup_full_roundtrip.py`. It imports two skills (one with a binary file), creates a backup, restores into an empty database with `PROMPTVAULT_DATA_DIR` isolated, and compares every file's sha256 and the metadata.
- [ ] T069 [US5] Add a pre-feature restore test to `tests/integration/test_skill_backup_roundtrip.py`. It restores a backup created at the head recorded in T002, before this migration, runs `alembic upgrade head`, and checks that all rows are `item_type='prompt'` and that the prompt counts match.
- [ ] T070 [US5] If T068 or T069 reveal a gap (for example, the PostgreSQL restore path ignoring the new tables), fix it in `src/services/backup_dump_strategy.py` or `src/services/backup_restore_service.py` and record the cause in `specs/011-skill-packages/research.md` (Decision 8)

**Checkpoint**: SC-006 and FR-027 are verified.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T071 [P] Write a performance benchmark in `tests/benchmarks/test_skill_detail_perf.py`. It imports a 500-file skill and checks that `GET /api/skills/{id}` responds in under 2 s on SQLite (SC-007), and that a typical import finishes server-side in under 1 s (SC-001).
- [ ] T072 [P] Write a Playwright end-to-end test in `tests/e2e/skills.spec.ts` that imports the fixture skill, opens it, navigates the tree by keyboard, views a file and downloads it. Run the axe accessibility check on the detail view, following the `tests/accessibility/` patterns. Also check the user-facing part of SC-001: from opening the import dialog to the skill appearing in the list takes under 30 s for the typical fixture skill, with the file chosen by script (Playwright's `setInputFiles`).
- [ ] T073 [P] Add a compatibility test in `tests/integration/test_skill_reference_corpus.py`, marked `@pytest.mark.network` and skipped offline. It imports every skill in a pinned snapshot of `anthropics/skills` and checks that there are 0 errors and at most 5 % with warnings (SC-004).
  - **Pinning**: record the repository URL and a full 40-character commit SHA in `tests/fixtures/skills/reference_corpus.json`. Choose the latest `main` commit at implementation time and update it deliberately.
  - **Download**: fetch `https://codeload.github.com/anthropics/skills/zip/<sha>` once into the cache folder `.cache/skill-corpus/<sha>/` (git-ignored), check the archive's sha256 recorded in the same JSON, then zip each `skills/<name>/` folder in memory and import it through `SkillService`.
- [ ] T074 Bump `CACHE_VERSION` in `src/web/static/ts/sw.ts` (required by `make lint` / `check-sw-cache-version`)
- [ ] T075 [P] Document the skill tables, the `item_type` discriminator, the guard list and the `/api/skills/*` endpoints in `docs/agents/architecture.md` and `docs/agents/api.md`
- [ ] T076 [P] Add a user-facing "Skills" page to the docs portal (from 010) in every shipped locale: `docs-portal/docs/` plus the `i18n/<locale>/` folders. It covers import, warnings, limits, export, and that skills are never run.
- [ ] T077 Run all quickstart scenarios (1–9) from `specs/011-skill-packages/quickstart.md`, including the PostgreSQL leg of T014, T059 and T068 against a local container (never the root `docker-compose.yml`)
- [ ] T078 Run `make lint` and `make test`, confirm both coverage gates are at or above 85 %, and add the "Constitution Check" section to the PR description (Governance)

---

## Dependencies & Execution Order

```mermaid
flowchart LR
  S[Phase 1 Setup<br/>after 009 + 010 merge] --> F[Phase 2 Foundational]
  F --> U1[US1 Import P1]
  U1 --> U2[US2 Browse P1]
  U1 --> U3[US3 Export P2]
  U1 --> U4[US4 Manage P2]
  U1 --> U5[US5 Backup P2]
  U2 --> P[Polish]
  U3 --> P
  U4 --> P
  U5 --> P
```

### Phase dependencies

- **Setup (Phase 1)**: blocked until 009 and 010 are merged into `main`. T001 to T003 run in order; T004 to T008 can then run in parallel.
- **Foundational (Phase 2)**: depends on Setup and blocks every story.
- **US1 (Phase 3)**: depends on Foundational. Every other story needs skills to exist, so US1 comes first.
- **US2, US3, US4, US5**: each depends only on US1 and can run in parallel. The UI tasks T057 and T064 change `skill-detail.ts` from T050, so do them after US2 or merge carefully.
- **Polish (Phase 8)**: after the stories you want to ship.

### Within each story

- Tests first, written to fail.
- Pure modules (reader, frontmatter, renderer, writer), then the service, then the router, then the UI.
- Locale keys can be added in parallel with the UI work.

### Parallel opportunities

- Phase 1: T005, T006, T007 and T008.
- Phase 2: the models T010 to T012; the router guards T020 and T021; the tests T014, T017 and T026.
- US1: the tests T027 to T031 together; the reader T032 and frontmatter T033 together; the client, card and locale work T038, T040 and T041 alongside the backend.
- After US1: US3 (backend), US5 (tests only) and US4 (backend) can run at the same time as US2.

## Parallel Example: User Story 1

```text
Task: "T027 Archive reader unit tests in tests/unit/test_skill_archive_reader.py"
Task: "T028 Frontmatter unit tests in tests/unit/test_skill_frontmatter.py"
Task: "T029 Import API integration tests in tests/integration/test_skills_api.py"

Task: "T032 SkillArchiveReader in src/services/skills/archive_reader.py"
Task: "T033 parse_skill_md in src/services/skills/frontmatter.py"
Task: "T038 skill-api.ts client"
Task: "T041 Locale keys in src/web/static/locales/*.json"
```

---

## Implementation Strategy

### MVP first (US1 + US2)

1. After 009 and 010 merge: Phase 1, then Phase 2. Stop and check that every existing test passes (SC-005).
2. Phase 3 (US1): stop and check quickstart Scenarios 2 and 4.
3. Phase 4 (US2): stop and check quickstart Scenario 1. This is the MVP: skills can be stored and read.

### Incremental delivery

4. US3 export: byte-exact, accepted by the validator.
5. US4 manage: edit, replace, delete, filter, search.
6. US5 backup: proven by tests.
7. Polish: performance, end-to-end, docs, the reference-corpus check, then the PR with its Constitution Check section.

PromptVault releases are batched. Tag only when the user decides to cut a release.

---

## Notes

- 78 tasks. Every task names exact files. `[P]` means different files and no unfinished dependency.
- Never use `extractall()` and never write archive content to disk (research.md Decision 3).
- Never use `innerHTML` with bundled content. Only the server-sanitised `instructions_html` goes through `raw()`.
- Run `npm run build` after TypeScript edits before checking anything in the browser.
- Commit after each task or logical group, on `011-skill-packages` only.
