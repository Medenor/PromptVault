# Architecture

## Overview

PromptVault is a service-oriented FastAPI app: business logic lives in `src/services/`, data access in `src/db/repositories/`, and the web layer in `src/web/` coordinates between them. Nothing in `src/web/app.py` should contain business logic — it calls into services.

## Core Systems

### Database Layer (`src/db/`)

- **Models** ([`models.py`](../../src/db/models.py)): SQLAlchemy ORM — `Prompt`, `PromptVersion`, `Category`, `Tag`, `User`, `Backup`.
- **Repositories** ([`repositories/`](../../src/db/repositories/)): `PromptRepository`, `VersionRepository`, `CategoryRepository`, `TagRepository` — CRUD, search, filtering, pagination.
- **Config** ([`config.py`](../../src/db/config.py)): PostgreSQL (production) / SQLite (development), connection pooling, session management.

### Service Layer (`src/services/`)

- **PromptDataServiceDB**: CRUD for prompts, automatic versioning on update, category/tag management, search.
- **BackupServiceDB**: SQLite (file copy) / PostgreSQL (`pg_dump`) backups, restore, retention, compression.
- **PromptImportExportService**: CSV/Markdown/JSON import-export, multiple import modes (append/merge/replace), validation on import.
- **SkillService** ([`services/skills/`](../../src/services/skills/)): import, browse, export, edit, replace and delete skill packages, with audit events. Plain modules do the format work: `archive_reader` (hardened in-memory zip reader), `frontmatter` (lenient `SKILL.md` checks, warning codes, identifier slug), `markdown_renderer` (`markdown-it-py` with raw HTML off, then `nh3`), `archive_writer` (standard-layout export).

### Web Layer (`src/web/`)

- **App** ([`app.py`](../../src/web/app.py)): FastAPI routes, Jinja2 rendering, static file serving, DI, error handling.
- **Templates** ([`templates/`](../../src/web/templates/)): `index.html`, `import_export.html`, `backup_management.html`.
- **Static** ([`static/`](../../src/web/static/)):
  - **TypeScript** (`ts/`) — active frontend source: `app.ts`, `import-export.ts`, `backup-management.ts`, and a component system in `components/` (Button, Card, Input, Form, Modal, Layout, Navigation).
  - **CSS** (`css/`) — Tailwind CSS v4 only (`tailwind-globals.css` + `tailwind.config.ts`); see [frontend.md](frontend.md).
  - **i18n** (`locales/`) — `en`, `fr`, `es`, `de` translation files.

## Data Storage

- **Primary store**: Database — SQLite at `data/prompts.db` (dev) or PostgreSQL via `DATABASE_URL` (production).
- **Schema**: `users`, `categories`, `tags`, `prompts` (includes `item_type` and `legacy_public` — grandfathered pre-sharing prompts visible to all authenticated users until un-grandfathered), `prompt_tags`, `prompt_versions`, `skill_packages`, `skill_files` (see [Skill packages](#skill-packages)), `prompt_shares` (`prompt_id`, `grantee_id`, `permission` [`read`\|`edit`], `granted_by`; unique per `(prompt_id, grantee_id)`; cascades on prompt/grantee delete, `SET NULL` on grantor delete), `backups`.
- **Legacy**: `data/prompts_data.json` — deprecated, kept only for migration.
- **Backups**: `data/backups/` (SQLite file copies or PostgreSQL `pg_dump` SQL, with metadata).
- **Logs**: `data/logs/` (application and audit).

## Key Patterns

- Service-oriented architecture with clear data/business-logic/presentation separation.
- RESTful design, proper HTTP methods throughout.
- Factory pattern for service instantiation and injection.
- Async I/O via FastAPI + `aiofiles`.
- i18next for internationalization; WCAG 2.1 Level AA accessibility target.

## Version Control System

- Version snapshots stored in `prompt_versions`, parent-child relationships, immutable history.
- Every prompt update automatically creates a new version; revert creates a new version rather than deleting history.
- Each version carries timestamp, author, message, and a full data snapshot.
- Full details: [`docs/VERSION_CONTROL.md`](../VERSION_CONTROL.md).

## Backup System

- SQLite: file copy + metadata row. PostgreSQL: `pg_dump` + metadata row.
- Automatic pre-operation backups before risky operations (delete, replace-import, restore).
- Manual/named backups, configurable retention cleanup, gzip compression of older backups.

## Skill packages

A skill (a `SKILL.md` with bundled files, imported from a `.zip`) is a second item type next to prompts. Design reasons: [`specs/011-skill-packages/research.md`](../../specs/011-skill-packages/research.md).

- **Discriminator**: `prompts.item_type` is `'prompt'` (default) or `'skill'` (check constraint `ck_prompts_item_type`, index `idx_prompts_item_type`). A skill is a `prompts` row, so lists, paging, categories, tags, favorites and full-text search work unchanged. Its `SKILL.md` text sits in the indexed `prompts.prompt` column; bundled files are never indexed.
- **Tables**: `skill_packages` (one row per skill: `skill_identifier`, `description`, `total_bytes`, `file_count`, `format_warnings`, `source_archive_name`, `files_updated_at`) and `skill_files` (one row per file: `path`, `path_folded`, `size`, `sha256`, `is_text`, `content` as BLOB/BYTEA, `UNIQUE (prompt_id, path_folded)`). Both cascade on delete. `content` is deferred: lists and metadata never load it.
- **Storage**: file contents live in the database (Constitution V), so a backup includes skills with no skill-specific code, and an import or replacement is one transaction.
- **Archives**: read with `zipfile` in memory only, never extracted to disk. Limits (`SKILL_*` variables, [`DEPLOYMENT.md`](../DEPLOYMENT.md)) are enforced from the central directory, from a live byte count, and (uploads) by `RequestBodyLimitMiddleware` before and while the body arrives.
- **Never executed**: bundled content is never run or rendered as active content. Only the server-sanitised `instructions_html` is inserted as HTML; file text goes through `textContent`; raw downloads are `attachment` with `nosniff` and `CSP: sandbox`.
- **Guard list** (prompt-only features that must refuse or skip skills):
  - `PUT`/`PATCH /api/prompts/{id}`, `copy-with-version`, the version, branch and revert endpoints and every sharing endpoint return 409 `ITEM_IS_SKILL` (`reject_if_skill` in `prompts_shared.py`; `PromptDataService._ensure_prompt_item` as defence in depth). A skill the caller cannot see is 404.
  - `POST /api/prompts` always creates `item_type='prompt'`.
  - Bulk import (Replace mode clears prompts only), bulk export and `load_prompts` cover prompts only. Export reports `X-Skills-Excluded`, and `/api/import-export/stats` adds `skill_count`.
  - Selective backup restore skips skill rows (their text must stay in step with their files), and the restore diff leaves them out.
  - Delete paths write one `skill.delete` audit event per skill (`prepare_skill_deleted_audit`, emitted after the commit). Deleting a skill is permanent (no undo).
- **Auth**: skills are owner-only. Administrators can read, download and delete every skill but cannot edit or replace another user's skill (404). Skills are never shared and never `legacy_public`.
