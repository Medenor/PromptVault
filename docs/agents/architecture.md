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

### Web Layer (`src/web/`)

- **App** ([`app.py`](../../src/web/app.py)): FastAPI routes, Jinja2 rendering, static file serving, DI, error handling.
- **Templates** ([`templates/`](../../src/web/templates/)): `index.html`, `import_export.html`, `backup_management.html`.
- **Static** ([`static/`](../../src/web/static/)):
  - **TypeScript** (`ts/`) — active frontend source: `app.ts`, `import-export.ts`, `backup-management.ts`, and a component system in `components/` (Button, Card, Input, Form, Modal, Layout, Navigation).
  - **CSS** (`css/`) — Tailwind CSS v4 only (`tailwind-globals.css` + `tailwind.config.ts`); see [frontend.md](frontend.md).
  - **i18n** (`locales/`) — `en`, `fr`, `es`, `de` translation files.

## Data Storage

- **Primary store**: Database — SQLite at `data/prompts.db` (dev) or PostgreSQL via `DATABASE_URL` (production).
- **Schema**: `users`, `categories`, `tags`, `prompts` (includes `legacy_public` — grandfathered pre-sharing prompts visible to all authenticated users until un-grandfathered), `prompt_tags`, `prompt_versions`, `prompt_shares` (`prompt_id`, `grantee_id`, `permission` [`read`\|`edit`], `granted_by`; unique per `(prompt_id, grantee_id)`; cascades on prompt/grantee delete, `SET NULL` on grantor delete), `backups`.
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
