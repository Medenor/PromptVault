# Tag & Category Management Interface Plan

## Overview

Deliver a dedicated management interface for categories and tags with CRUD, bulk operations,
usage analytics, orphan detection, and content-based suggestions. This plan is grounded in the
current implementation, where categories/tags are database-backed but only surfaced indirectly
through prompt editing and sidebar filters.

## Goals

- Centralize category/tag administration with global rename/merge/delete operations.
- Provide usage metrics, orphan detection, and search to reduce sprawl.
- Enable bulk tagging and find/replace across prompts.
- Add metadata (description, color, created_at, usage_count) for governance.
- Add optional content-based suggestions to improve tag consistency.

## Non-Goals (Phase 1)

- Real-time collaborative tagging or multi-admin conflict resolution.
- Full NLP pipelines or external ML services.
- Breaking changes to existing prompt create/edit flows.

## Dependencies

- Depends on Issue #13 (as noted in roadmap).
- Requires database migration support and repository updates.

## Current State Snapshot

Backend:

- Categories and tags are persisted in dedicated tables:
  - `Category`: `id`, `name`, `description`, `created_at`
  - `Tag`: `id`, `name`, `created_at`
- `PromptDataServiceDB` creates categories/tags via `get_or_create` when prompts are created or
  updated, and does not manage global rename/merge/delete operations.
- `TagRepository` already exposes:
  - `rename`, `delete_if_unused`, and `merge_tags` (single source -> target)
  - `list_all_with_counts` (used by `/api/tags`)
- `CategoryRepository` already exposes:
  - `rename`, `delete_if_unused`, and `list_all_with_counts`
- API endpoints (legacy/compatibility):
  - `GET /api/categories` returns a list of category names.
  - `GET /api/tags` returns tags with usage counts.

Frontend:

- `index.html` shows categories/tags in the sidebar for filtering.
- Prompt editor includes category select + tags input with autocomplete.
- `app.ts` calls `/api/categories` and `/api/tags` to render filter lists and tag suggestions.
- Client-side validation already deduplicates tags (case-insensitive) and validates category/tag
  length, but the database unique constraint is case-sensitive.

Gaps:

- No global management UI or APIs for rename/merge/delete/bulk operations.
- No usage analytics for categories beyond counts.
- No orphan detection or cleanup workflows.
- No metadata beyond minimal schema (no color, sort order, or updated_at).

## Integration Points

- `src/services/prompt_data_service_db.py`:
  - Uses `CategoryRepository.get_or_create` and `TagRepository.get_or_create_many` during prompt
    create/update. New management actions must not break this flow.
- `src/web/app.py`:
  - Provides `/api/categories` and `/api/tags` consumed by the main UI.
- `src/web/static/ts/app.ts` and `src/web/templates/index.html`:
  - Render sidebar filters and tag autocomplete from existing endpoints.
## Assumptions

- Backend uses database-backed services (PromptDataServiceDB).
- Legacy JS is not modified; TypeScript sources are used.
- Existing endpoints for `/api/categories` and `/api/tags` must remain stable for the sidebar
  and autocomplete.

## Workstreams

### 1) Data Model & Migrations

1. Extend existing `categories` and `tags` tables:
   - Add `color`, `updated_at`.
   - Add `sort_order` for categories (drag-and-drop).
   - Consider keeping `usage_count` computed (current approach) unless performance indicates a
     need to denormalize.
2. Add constraints:
   - Enforce case-insensitive uniqueness (DB index or normalized column).
   - Preserve current max lengths from `SPEC_APP.md`.
3. Create Alembic migration to add columns and set defaults.
4. Update SQLAlchemy models and repositories to include new fields.

Deliverables:
- `src/db/models.py` updates.
- `alembic` migration file.
- Repository methods for CRUD, merge, bulk operations.

### 2) Backend Services & API

1. Keep existing endpoints for compatibility:
   - `GET /api/categories`
   - `GET /api/tags`
2. Add management endpoints (RESTful):
   - `GET /api/categories` (list + filter + usage stats)
   - `POST /api/categories` (create)
   - `PUT /api/categories/{id}` (rename, update metadata)
   - `DELETE /api/categories/{id}` (delete, optionally reassign or warn)
   - `POST /api/categories/merge` (merge list into target)
   - `POST /api/categories/bulk-delete`
   - `POST /api/categories/find-replace`
   - `GET /api/categories/orphans`
   - `GET /api/categories/prompts` (filter prompts by category)
   - `GET /api/categories/analytics`
   - `POST /api/categories/import`
   - `GET /api/categories/export`
   - `POST /api/categories/reorder`
   - `POST /api/categories/undo`
3. Mirror endpoints for tags:
   - `GET /api/tags`, `POST /api/tags`, `PUT /api/tags/{id}`, `DELETE /api/tags/{id}`
   - `POST /api/tags/merge`, `POST /api/tags/bulk-delete`
   - `POST /api/tags/find-replace`, `GET /api/tags/orphans`
   - `GET /api/tags/prompts`, `GET /api/tags/analytics`
   - `POST /api/tags/import`, `GET /api/tags/export`
   - `POST /api/tags/undo`
4. Implement transaction-safe rename and merge:
   - Update all prompt relationships in a single transaction.
   - Ensure usage counts are recalculated (computed counts are already supported).
5. Bulk operations:
   - Bulk add/remove tags across multiple prompts.
   - Bulk delete with validation and warnings.
6. Validation rules:
   - Unique names, length limits, allowed characters.
   - Case-insensitive matching for duplicates.
7. Add confirmation requirements for destructive endpoints.

Implementation Notes:

- Reuse existing repository methods where possible:
  - `TagRepository.merge_tags` can be extended to support multiple sources.
  - `CategoryRepository.rename` can be used for rename flows.
- Introduce `CategoryRepository.merge_categories` (not present today).
- Preserve existing response shapes for `/api/tags` (name + count) to avoid breaking autocomplete
  and sidebar rendering.

Deliverables:
- `src/web/app.py` routes.
- `src/services/` updates or new `tag_category_service_db.py`.
- Pydantic schemas in `src/web/schemas/`.

### 3) UI & UX

1. Sidebar navigation:
   - Add "Manage Categories" and "Manage Tags".
2. Management pages:
   - Table/list view with search, filters, usage counts.
   - Inline rename, description edit, color picker.
   - Bulk selection with actions (merge, delete, reassign).
3. Drag-and-drop category order:
   - Persist `sort_order`.
4. Analytics & usage:
   - Top/least used items, co-occurrence matrix for tags.
5. Orphan cleanup wizard:
   - Identify prompts without categories (or tags).
   - Reassign or mark as uncategorized.
6. Bulk tagging:
   - Select prompts, add/remove tags in batch.
7. Find and replace:
   - Replace tag/category names across prompts.
8. Suggest tags button:
   - In prompt editor, trigger content-based suggestions.
   - Integrate with existing tag autocomplete UX.
9. Preserve existing filter list behavior:
   - Sidebar category/tag filters remain driven by `/api/categories` and `/api/tags`.

Deliverables:
- New templates: `src/web/templates/manage_categories.html`,
  `src/web/templates/manage_tags.html`
- New TS entrypoints: `src/web/static/ts/manage-categories.ts`,
  `src/web/static/ts/manage-tags.ts`
- Update `src/web/static/ts/app.ts` and `src/web/templates/index.html`
  to add navigation links.

### 4) Suggestion System (Lightweight NLP)

1. Start with deterministic keyword extraction:
   - Tokenize prompt content.
   - Remove stopwords.
   - Score by frequency and existing taxonomy overlaps.
2. Return ranked suggestions:
   - Only suggest tags not already applied.
   - Include confidence scores.
3. API endpoint:
   - `POST /api/tags/suggest` with prompt content or id.

Deliverables:
- Suggestion utility module in `src/services/`.
- Tests for edge cases (empty content, short prompts).

### 5) Import/Export

1. JSON format for tags and categories:
   - `name`, `description`, `color`, `sort_order`.
2. API endpoints for import/export (see above).
3. Validate on import (duplicates, invalid names).

Deliverables:
- Import/export helpers in `src/services/`.
- API routes and tests.

### 6) Undo Support

1. Record recent operations:
   - Rename, merge, bulk delete, reassign.
2. Store operation log in a dedicated table or log store.
3. Undo endpoints for recent operations only (last N).

Deliverables:
- New model/table for operations log or structured audit records.
- Undo endpoints.

## Data Model Changes (Proposed)

### Category

| Field         | Type        | Notes                                     |
| ------------- | ----------- | ----------------------------------------- |
| id            | int         | Primary key                               |
| name          | string      | Unique, case-insensitive                  |
| description   | string      | Optional                                 |
| color         | string      | Optional, validated hex or token          |
| sort_order    | int         | Optional, for drag-and-drop ordering      |
| created_at    | datetime    | Already exists                            |
| updated_at    | datetime    | New                                      |
| usage_count   | int         | Prefer computed unless needed to cache    |

### Tag

| Field         | Type        | Notes                                     |
| ------------- | ----------- | ----------------------------------------- |
| id            | int         | Primary key                               |
| name          | string      | Unique, case-insensitive                  |
| description   | string      | Optional                                 |
| color         | string      | Optional                                 |
| created_at    | datetime    | Already exists                            |
| updated_at    | datetime    | New                                      |
| usage_count   | int         | Prefer computed unless needed to cache    |

## API Contract Notes

- Existing endpoints must keep current shapes:
  - `/api/categories` -> `{ categories: string[] }`
  - `/api/tags` -> `{ tags: [{ name, count }] }`
- New management endpoints can return richer objects (id, name, description, color, counts).
- All destructive operations require confirmation flags.
- Merge endpoints accept `source_ids` + `target_id`.
- Validation error responses align with existing API patterns.

## UI States & Error Handling

- Inline errors for duplicate names and invalid input.
- Confirmation dialogs for merge/delete.
- Toasts for success/failure with i18n keys.
- Disabled actions when selection empty.

## Testing Plan

1. Service tests:
   - Rename/merge operations update prompt relations.
   - Bulk delete handles orphan warnings.
   - Usage count updates.
2. API tests:
   - CRUD, merge, bulk delete, find/replace, suggest.
3. Frontend tests:
   - UI rendering, selection logic, search/filter.
4. Edge cases:
   - Duplicate names, case-insensitivity.
   - Deleting categories that would orphan prompts.
   - Invalid color format.

## i18n Updates

- Add new keys in `src/web/static/locales/*.json` for:
  - Manage Categories/Tags pages.
  - Confirm dialogs, success messages, error messages.
  - Analytics labels and suggestion UI.

## Documentation

- Update `docs/ROADMAP.md` status when implemented.
- Add `docs/TAG_CATEGORY_MANAGEMENT.md` describing workflows.
- Add best practices for taxonomy naming and normalization.

## Milestones & Estimates

1. Data model + migrations (2-3 days)
2. Backend services + API (3-4 days)
3. UI/UX pages + navigation (3-4 days)
4. Suggestions + analytics (2-3 days)
5. Tests + docs (3-4 days)

Total estimate: ~2 weeks.

## Risks

- Data migration errors if existing tags are duplicated with case variance.
- Enforcing case-insensitive uniqueness may require a cleanup step or automated merge plan.
- Performance considerations for large prompt sets during merge/find-replace.
- Undo scope and storage of operation logs.

## Open Questions

- Should categories be required for all prompts?
- Should tag hierarchy/nesting be included in phase 1 or deferred?
- Maximum allowed tags per prompt?
- Should usage_count be real-time or periodically recalculated?
