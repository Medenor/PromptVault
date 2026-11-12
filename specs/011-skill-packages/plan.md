# Implementation Plan: Skill Packages

**Branch**: `011-skill-packages` | **Date**: 2026-11-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-skill-packages/spec.md`

## Summary

This feature adds skills to the vault as a second content type, next to prompts. A skill is a `SKILL.md` package with bundled files, imported from a `.zip`, browsable as a file tree, and exported again as a standard-layout `.zip`.

A skill is a row in the existing `prompts` table, marked by a new `item_type` column. Its `SKILL.md` text goes in the indexed `prompt` column, so lists, paging, categories, tags, favorites and full-text search work without changes. Two new tables, `skill_packages` and `skill_files`, hold skill metadata and file contents. The contents are stored as binary columns in the database, which satisfies Constitution V, makes imports all-or-nothing, and puts skills into backups with no extra code.

A hardened archive reader works only in memory, using the standard-library `zipfile` and never extracting entries to disk. The upload size is enforced before and during receipt of the request body. It enforces the path, link and size rules. Frontmatter is checked leniently, against the Agent Skills rules, producing warnings rather than rejections. Explicit guards keep prompt-only features (versioning, sharing, placeholders, bulk import/export) away from skills.

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript, strict (frontend)

**Primary Dependencies**:
- **Existing**: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 / pydantic-settings, python-multipart, slowapi; i18next, Tailwind v4.
- **New backend**: `PyYAML` (already installed through `uvicorn[standard]`, now declared), `markdown-it-py`, `nh3`.
- **New frontend**: none.

**Storage**: PostgreSQL (production) and SQLite (dev and tests). Adds one column to `prompts` and two tables. File contents are stored as `BYTEA`/`BLOB`.

**Testing**: pytest with coverage ≥ 85 %, parametrised over both database dialects where possible. Vitest with v8 coverage ≥ 85 %. Playwright for the end-to-end smoke test of import, browse and download.

**Target Platform**: self-hosted Linux server (Docker), modern desktop and mobile browsers.

**Project Type**: web service (FastAPI with a server-rendered shell and a TypeScript frontend) in one repository.

**Performance Goals**:
- Importing a typical skill (under 1 MB, under 20 files) takes under 30 s including user interaction, and under 1 s on the server (SC-001).
- The detail view of a 500-file skill responds in under 2 s (SC-007).
- Export streams without building the whole archive in memory once it passes 8 MB.

**Constraints**:
- Default limits: 10 MB upload, 50 MB unpacked, 500 files, depth 10, 10 MB per file, compression ratio 100, all configurable.
- Archive entries are never extracted to the filesystem. The raw upload may be spooled to a temporary file by the framework, with its size capped by an early `Content-Length` check and a body-limit middleware, and it is deleted when the request ends (research.md Decision 9).
- Bundled content is never executed or rendered as active content.
- Imports and replacements are all-or-nothing.
- Migrations must run on both SQLite and PostgreSQL.

**Scale/Scope**: personal or small-team vaults, around tens to low hundreds of skills, each typically under 1 MB.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the design complies |
|---|---|---|
| I. Layered service architecture | ✅ Pass | Routes in `skills_router.py` call `SkillService`, which uses `SkillRepository` and `PromptRepository`. Archive reading, frontmatter parsing and Markdown rendering are plain modules the service calls and have no HTTP code. |
| II. Test coverage ≥ 85 % (non-negotiable) | ✅ Pass (planned) | Each new module gets unit tests. The malicious-archive set is tested with parameters. API integration tests. Vitest tests for each new `.ts` file. Coverage is checked by `make test`. |
| III. Security-first authentication | ✅ Pass | Every changing endpoint uses the same auth dependencies as prompts. Other users' skills return 404, and administrators see everything, as they do for prompts. Import and replacement are rate-limited. In anonymous mode the existing configuration guard applies, checked by a dedicated test (T031). |
| IV. TypeScript-only frontend | ✅ Pass | New code goes under `src/web/static/ts/skills/`. Typed `t()` keys are added to all four locales. `CACHE_VERSION` is bumped. No edits to `static/js/`. |
| V. Database-backed persistence | ✅ Pass | File contents are stored in the database (research.md Decision 2). One Alembic migration, tested on both dialects. Transactions use the `get_db_session()` context managers. |
| Security & quality standards | ✅ Pass | Inputs are checked with Pydantic, ORM only, no `innerHTML` with untrusted data (server-sanitised HTML through `raw()`, file text through `textContent`). Black and Prettier. MPL 2.0 headers on new files. |

**Post-design re-check (after Phase 1)**: ✅ Pass. No violations, so Complexity Tracking is left empty.

## Project Structure

### Documentation (this feature)

```text
specs/011-skill-packages/
├── plan.md              # This file
├── research.md          # Phase 0: 12 design decisions
├── data-model.md        # Phase 1: tables, invariants, migration
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── skills-api.md    # Phase 1: REST contract plus changes to existing endpoints
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks, not created here)
```

### Source Code (repository root)

```text
alembic/versions/
└── d4e5f6a7b8c9_add_skill_packages.py          # new: item_type, skill_packages, skill_files

src/config/
└── skill_config.py                              # new: SkillSettings (limits)

src/db/models/
├── prompt.py                                    # + item_type column, skill_package and skill_files relationships
├── skill_package.py                             # new
└── skill_file.py                                # new

src/db/repositories/
├── prompt_repository.py                         # + item_type filter in _apply_common_filters, search(), count(), stats
└── skill_repository.py                          # new: files without content, single-file content, replace_files

src/services/
├── skills/                                      # new package
│   ├── archive_reader.py                        # SkillArchiveReader: checks, clutter filter, root detection
│   ├── frontmatter.py                           # split + yaml.safe_load + format warnings + identifier slug
│   ├── markdown_renderer.py                     # markdown-it-py (raw HTML off) + nh3
│   ├── archive_writer.py                        # export zip built per request
│   ├── errors.py                                # SkillArchiveError(code, offending_entry)
│   └── skill_service.py                         # import / replace / update / delete / read / export, audit events
├── prompt_data_service_db.py                    # guards: update_prompt, clear_all_prompts, load_prompts
├── prompt_import_export_service.py              # prompts-only export, skills_excluded count
└── undo_service.py                              # skip skill rows

src/web/
├── models/skill_requests.py, skill_responses.py # new Pydantic models
├── routers/skills_router.py                     # new: /api/skills/*
├── dependencies/skill_upload.py                 # new: Content-Length check (413)
├── middleware/request_body_limit.py             # new: streamed body limit for skill uploads
├── routers/prompts_crud_router.py               # 409 ITEM_IS_SKILL guards, item_type in responses
├── routers/prompts_search_router.py             # item_type query param
├── routers/prompts_versions_router.py           # 409 guards
├── routers/prompts_sharing_router.py            # 409 guards
├── routers/import_export_router.py              # skills_excluded, Replace clears prompts only
├── templates/import_export.html                 # "skills are exported one at a time" notice
└── static/
    ├── ts/skills/                               # new: skill-api, skill-import, skill-detail,
    │                                            #      skill-file-tree, skill-file-viewer (+ __tests__)
    ├── ts/app/prompt-card.ts, prompt-list.ts    # type badge, open the skill detail view
    ├── ts/app/prompt-filters.ts                 # type filter (all / prompts / skills)
    ├── ts/app/prompt-crud.ts                    # hide version, share and placeholder actions for skills
    ├── ts/sw.ts                                 # bump CACHE_VERSION
    └── locales/{en,fr,es,de}.json               # skills.* keys, warning and error code labels

tests/
├── fixtures/skills/build_fixtures.py            # builds valid and malicious archives at test time
├── unit/test_skill_archive_reader.py
├── unit/test_skill_frontmatter.py
├── unit/test_skill_markdown_renderer.py
├── unit/test_skill_archive_writer.py
├── unit/test_skill_service.py
├── integration/test_skills_api.py              # US1 import
├── integration/test_skills_api_browse.py       # US2
├── integration/test_skills_api_export.py       # US3
├── integration/test_skills_api_manage.py       # US4
├── integration/test_skills_upload_limits.py    # 413 before/while receiving, temp-file cleanup
├── integration/test_skills_auth_modes.py       # Constitution III, admin visibility
├── integration/test_skill_migration.py          # both dialects, downgrade guard
├── integration/test_skill_prompt_guards.py      # 409s, bulk import Replace safety, export exclusion
├── integration/test_skill_backup_roundtrip.py   # SC-006
├── benchmarks/test_skill_detail_perf.py         # SC-007
└── e2e/skills.spec.ts                           # Playwright: import, browse, download
```

**Structure Decision**: Keep the existing single-repository layout: backend in `src/`, active frontend in `src/web/static/ts/`, tests in `tests/` split into unit, integration, benchmarks and e2e. Skill logic gets its own `src/services/skills/` package so the archive and format code can be tested without HTTP or database setup. Shared vault behaviour stays in the existing prompt repository and service, extended with an `item_type` filter and guards rather than copied.

## Delivery Order (input for `/speckit-tasks`)

1. **Foundation**: migration, models, `SkillSettings`, `item_type` in repository filters and API responses, prompt-only guards (FR-001–FR-003, FR-024a). Shippable on its own: no skills exist yet, and prompts are unchanged (SC-005).
2. **Story 1, import (P1)**: archive reader, frontmatter, service import, `POST /api/skills/import`, audit, import interface.
3. **Story 2, browse (P1)**: Markdown renderer, detail, file-content and raw endpoints, detail view with tree and viewer. Steps 1–3 make the MVP.
4. **Story 3, export (P2)**: archive writer, download endpoint, check with `skills-ref`.
5. **Story 4, manage (P2)**: PATCH, replace, delete, type filter, search check, bulk-export notice.
6. **Story 5, backup (P2)**: round-trip and old-backup restore tests. No production code is expected.
7. **Polish**: i18n completeness, accessibility (tree keyboard navigation, axe), performance benchmark, docs (`docs/agents/architecture.md` and `api.md`, the docs-portal page in four locales).

## Risks

| Risk | Mitigation |
|---|---|
| A code path that reads every row from `prompts` treats a skill as a prompt | Guard table in research.md Decision 7, plus `test_skill_prompt_guards.py`. Before implementing, `grep` for `PromptRepository(` and `session.query(Prompt)` uses and decide on each. |
| Migration ordering with the unmerged `009-totp-2fa` branch | Re-point `down_revision` to whichever head is current at merge time (data-model.md). |
| Large `BYTEA` values make `pg_dump` and restore slower | Bounded by the limits. Documented in the deployment docs. Revisit storage only if the limits are raised a lot. |
| The full-text index on SQLite grows with large `SKILL.md` files | `SKILL.md` is usually under 500 lines. Its file size is still capped by `SKILL_MAX_FILE_BYTES`. |

## Complexity Tracking

No constitution violations. Nothing to justify.
