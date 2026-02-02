<!--
  This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
  If a copy of the MPL was not distributed with this file, You can obtain one at
  https://mozilla.org/MPL/2.0/.
-->

# Tag & Category Management - Implementation Checklist

Purpose: verify the implementation matches `docs/PLAN_TAG_CATEGORY_MANAGEMENT.md` and
`docs/SPECS/SPEC_TAG_CATEGORY_MANAGEMENT.md`. Use this as a manual QA list and as a guide for
automated test coverage. Mark items as **Pass / Fail / N/A** and add notes where needed.

---

## 0) Preflight & Environment

- [ ] App starts via `python run_web.py` (do not run uvicorn directly).
- [ ] Database migrations are applied (`alembic upgrade head` if needed).
- [ ] Frontend assets build cleanly (`npm run build`) and are served without 404s.
- [ ] Clear browser cache or verify dev-mode no-cache headers are working.
- [ ] Create test data:
  - [ ] At least 3 categories (one unused, one used, one to delete).
  - [ ] At least 6 tags (include 1 unused and 1 sub-tag).
  - [ ] At least 5 prompts (some with category, some without; some with tags, some without).

---

## 1) Compatibility Endpoints (REQ-001, NFR-001, INV-005)

- [ ] `GET /api/categories` returns `{ "categories": ["string"] }` with names only.
- [ ] `GET /api/tags` returns `{ "tags": [{ "name": "string", "count": 0 }] }`.
- [ ] Response shapes match spec exactly; no extra fields.
- [ ] Existing UI (sidebar filters + tag autocomplete) still works with these endpoints.

---

## 2) Data Model & Migrations (Plan §1, Spec §7)

- [ ] Category fields include: `id`, `name`, `description`, `color`, `sort_order`,
  `created_at`, `updated_at`.
- [ ] Tag fields include: `id`, `name`, `description`, `color`, `parent_tag_id`,
  `created_at`, `updated_at`.
- [ ] Case-insensitive uniqueness enforced for names (INV-001).
- [ ] Color validation enforced (hex or allowed token).
- [ ] `usage_count` is computed or stored as designed and correct.

---

## 3) Auth & Authorization (SEC-001, SEC-002, ERR-004)

- [ ] All management endpoints require authentication.
- [ ] Destructive actions require admin or elevated role (delete/merge/bulk/find-replace).
- [ ] Unauthorized access returns structured auth errors.

---

## 4) Category Management - API Behavior

- [ ] `GET /api/categories/manage` returns metadata + usage counts.
- [ ] `POST /api/categories` creates a category (validations enforced).
- [ ] `PUT /api/categories/{id}` updates name/metadata (atomic).
- [ ] `DELETE /api/categories/{id}` requires confirmation flag (ERR-005).
- [ ] `POST /api/categories/merge` merges sources to target (atomic, REQ-005).
- [ ] `POST /api/categories/bulk-delete` deletes selected with confirmation.
- [ ] `POST /api/categories/find-replace` updates prompts’ categories.
- [ ] `POST /api/categories/reorder` persists custom order.
- [ ] `GET /api/categories/orphans` returns prompts without a category.
- [ ] `GET /api/categories/orphans/details` returns prompt details (id/title).
- [ ] `GET /api/categories/unused` returns categories with zero prompts.
- [ ] `GET /api/categories/analytics` returns usage summaries.
- [ ] `POST /api/categories/import` + `GET /api/categories/export` work with validation.
- [ ] `POST /api/categories/undo` reverses most recent operation.

---

## 5) Tag Management - API Behavior

- [ ] `GET /api/tags/manage` returns metadata + usage counts.
- [ ] `POST /api/tags` creates a tag (validations enforced).
- [ ] `PUT /api/tags/{id}` updates name/metadata (atomic).
- [ ] `DELETE /api/tags/{id}` requires confirmation flag (ERR-005).
- [ ] `POST /api/tags/merge` merges sources to target (atomic, REQ-005).
- [ ] `POST /api/tags/bulk-delete` deletes selected with confirmation.
- [ ] `POST /api/tags/find-replace` updates prompts’ tags.
- [ ] `POST /api/tags/bulk-update` adds/removes tags across prompts.
- [ ] `GET /api/tags/orphans` returns unused tags.
- [ ] `GET /api/tags/orphan-prompts` returns prompts without tags.
- [ ] `GET /api/tags/orphan-prompts/details` returns prompt details (id/title).
- [ ] `GET /api/tags/analytics` returns usage and co-occurrence summary.
- [ ] `POST /api/tags/suggest` returns suggestions for content or prompt_id.
- [ ] `POST /api/tags/import` + `GET /api/tags/export` work with validation.
- [ ] `POST /api/tags/undo` reverses most recent operation.

---

## 6) Error Handling & Validation (ERR-***, NFR-004)

- [ ] Invalid names or colors return ERR-VALIDATION with details.
- [ ] Name conflict returns ERR-CONFLICT (case-insensitive).
- [ ] Missing ID returns ERR-NOT-FOUND.
- [ ] Destructive action without confirm returns ERR-PRECONDITION.
- [ ] Merge with target in sources returns ERR-VALIDATION.
- [ ] Suggest without content/prompt_id returns ERR-VALIDATION.

---

## 7) UI/UX - Navigation & Pages (Plan §3)

- [ ] Sidebar has “Manage Categories” and “Manage Tags”.
- [ ] Page titles follow “PromptVault - Page Title”.
- [ ] Header styling matches main page across management pages.
- [ ] App logo links to homepage (logo only, not title).
- [ ] Categories/Tags section titles display icons in left panel headers only.

---

## 8) UI/UX - Manage Categories Page

- [ ] List shows name, description, color, usage count, created/updated.
- [ ] Inline edit works for name/description/color.
- [ ] Create category form validates and shows errors.
- [ ] Unused categories card is present and populated.
- [ ] Prompts without category card is present and shows prompt details.
- [ ] Orphan prompts support per-prompt reassignment (not bulk).
- [ ] Delete respects confirmation and fails gracefully if in use.

---

## 9) UI/UX - Manage Tags Page

- [ ] List shows name, description, color, usage count, created/updated.
- [ ] Parent tag selection works and sub-tags display properly.
- [ ] Unused tags card is present and populated.
- [ ] Prompts without tags card is present and shows prompt details.
- [ ] Orphan prompts support per-prompt tag assignment (not bulk).
- [ ] Delete respects confirmation and fails gracefully if in use.

---

## 10) Prompt Editor - Tags & Categories UX

- [ ] Tag input allows free text + autosuggest.
- [ ] Max 15 tags enforced with user feedback (validation key present).
- [ ] Tags are additive; selecting another tag does not remove prior tags.
- [ ] Clicking tag field always opens suggestion dropdown.
- [ ] Chip UI supports removal (x button) and backspace removal.
- [ ] Category dropdown includes all categories, including unused.
- [ ] Sub-tags appear in dropdown even if parent not already selected.

---

## 11) Colors & Visual Semantics

- [ ] Category pill on prompt cards uses category color fill.
- [ ] Tag chips on prompt cards use tag color outline/icon.
- [ ] Sidebar category/tag lists show a color dot with stored color.
- [ ] Default colors fallback consistently when color is missing.

---

## 12) Internationalization (i18n)

- [ ] All new UI strings use i18n keys (no hardcoded strings).
- [ ] Keys exist for EN/FR/ES/DE.
- [ ] Manage Categories/Tags page strings translate correctly.
- [ ] “Create/Edit Prompt” title is translated.
- [ ] Validation messages (e.g., tag max) translate correctly.

---

## 13) Analytics & Orphans

- [ ] Category usage counts match actual prompt counts.
- [ ] Tag usage counts match actual prompt counts.
- [ ] Unused tags/categories update after create/delete/reassign.
- [ ] Orphan prompts update after reassign.
- [ ] Tag co-occurrence summary returns deterministic ordering.

---

## 14) Suggestions (REQ-013)

- [ ] Suggestions respect existing tags and do not return duplicates.
- [ ] Suggestions handle accents and hyphenated tokens.
- [ ] Suggestions return deterministic order for same input.
- [ ] Suggestions have score values in response.

---

## 15) Import / Export (REQ-012)

- [ ] Export returns structured JSON for tags and categories.
- [ ] Import validates duplicates, invalid colors, and length constraints.
- [ ] Import handles existing names with clear conflicts.

---

## 16) Undo (REQ-014)

- [ ] Undo returns system to prior state for:
  - [ ] rename
  - [ ] merge
  - [ ] bulk delete
  - [ ] reassign/find-replace
- [ ] Undo is limited to recent operations only (as designed).
- [ ] Undo operations are auditable/logged.

---

## 17) Audit Logging (SEC-003)

- [ ] Create/update/delete/merge/bulk/undo events are logged.
- [ ] Logs include actor, action, resource, and timestamp.

---

## 18) Automated Tests (Spec §9)

- [ ] Service tests cover rename/merge/atomicity.
- [ ] API tests cover CRUD + bulk + find/replace + suggest + undo.
- [ ] Validation errors tested for all ERR-*** cases.
- [ ] Compatibility endpoints tested for output shapes.
- [ ] Frontend tests cover:
  - [ ] Tag chip add/remove + autocomplete behavior
  - [ ] Orphan reassignment per prompt
  - [ ] Color rendering on prompt cards

---

## 19) Regression Checks

- [ ] Main prompt list loads without console errors.
- [ ] Tag autocomplete still works when no tags exist.
- [ ] Category filter still works and reflects renames.
- [ ] Prompt editing saves without losing tags/categories.
- [ ] Deleting a category or tag does not corrupt prompts.

---

## 20) Notes / Findings

- [ ] Record deviations from spec/plan here:
  - [ ] Spec gaps:
  - [ ] Plan gaps:
  - [ ] Implementation gaps:

