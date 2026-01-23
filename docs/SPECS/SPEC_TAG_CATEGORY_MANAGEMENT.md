---
id: spec-tag-category-management
title: Tag and Category Management
version: 1.1.0
date_created: 2026-01-21
last_updated: 2026-01-23
owner: medenor
tags: [taxonomy, functional, process, api]
status: draft
---

## 1. Introduction

This specification defines the required behavior for managing Tags and Categories in a prompt
management system. It describes the expected user-visible and programmatic outcomes for
creating, updating, merging, deleting, analyzing, and suggesting Tags and Categories while
preserving existing compatibility interfaces.

---

## 2. Purpose, Scope, and Out-of-Scope

### 2.1 Purpose

Provide a centralized, consistent, and safe management layer for Tags and Categories with CRUD,
bulk operations, analytics, orphan detection, and suggestions derived from prompt content.

### 2.2 In Scope

- Tag and Category management operations (create, rename, merge, delete).
- Bulk operations (bulk delete, bulk tag application/removal).
- Usage analytics (counts, most/least used, co-occurrence summaries).
- Orphan detection and cleanup guidance.
- Find-and-replace across prompts.
- Import/export of Tag and Category definitions.
- Suggestion generation from prompt content.
- Compatibility with existing list endpoints.

### 2.3 Out of Scope

- Real-time collaboration and conflict resolution.
- External machine learning services.
- Changes to prompt creation/editing data models beyond Tag/Category management.
- Full hierarchical taxonomy enforcement (optional future feature).

### 2.4 Assumptions

- The system supports authentication and role-based authorization.
- Prompts can be associated with at most one Category and zero or more Tags.
- Existing clients depend on two compatibility list interfaces for Tags and Categories.

---

## 3. Definitions & Terminology

| Term | Definition |
|------|------------|
| Tag | A label that can be attached to a prompt; multiple Tags MAY be attached to a prompt. |
| Category | A single classification value assigned to a prompt; at most one Category is assigned per prompt. |
| Prompt | A content item that can be labeled with Tags and a Category. |
| Orphan | A Tag with zero associated prompts, a prompt with no Category assigned, or a prompt with no Tags assigned. |
| Unused Category | A Category with zero associated prompts. |
| Unused Tag | A Tag with zero associated prompts. |
| Merge | The act of consolidating multiple Tags/Categories into a single target. |
| Compatibility Endpoint | An interface whose response shape MUST remain unchanged for existing clients. |
| CRUD | Create, Read, Update, Delete. |
| NLP | Natural Language Processing. |
| Suggestion | A candidate Tag derived from prompt content analysis. |

---

## 4. System States & Lifecycle

### 4.1 States

Tags and Categories do not have explicit lifecycle states beyond existence.

### 4.2 Events / Triggers

- CREATE
- UPDATE
- DELETE
- MERGE
- BULK_DELETE
- BULK_TAG_UPDATE
- FIND_REPLACE
- IMPORT
- EXPORT
- SUGGEST
- UNDO

### 4.3 Allowed State Transitions

Not applicable. Any transition not listed MUST be considered invalid.

---

## 5. Functional Requirements

### 5.1 Functional Requirements (REQ-***)

- **REQ-001 — Compatibility List Interfaces**  
  The system **MUST** preserve the existing Compatibility Endpoints for listing Categories
  and Tags, including their response shapes.

- **REQ-002 — Category CRUD**  
  The system **MUST** provide operations to create, read, update, and delete Categories.

- **REQ-003 — Tag CRUD**  
  The system **MUST** provide operations to create, read, update, and delete Tags.

- **REQ-004 — Rename Operation**  
  The system **MUST** allow renaming a Tag or Category and update all associated prompts
  within a single logical operation.

- **REQ-005 — Merge Operation**  
  The system **MUST** allow merging multiple Tags or Categories into a single target and
  update all associated prompts within a single logical operation.

- **REQ-006 — Bulk Delete**  
  The system **MUST** support bulk deletion of Tags and Categories with explicit confirmation.

- **REQ-007 — Orphan Detection**  
  The system **MUST** identify unused Tags, unused Categories, prompts without Categories, and prompts without Tags.

- **REQ-008 — Usage Analytics**  
  The system **MUST** provide usage counts for Tags and Categories and expose most/least used
  summaries.

- **REQ-009 — Tag Co-Occurrence Summary**  
  The system **MUST** provide a summary of Tag co-occurrence across prompts.

- **REQ-010 — Find and Replace**  
  The system **MUST** support find-and-replace for Tag and Category names across prompts.

- **REQ-011 — Bulk Tag Update**  
  The system **MUST** support adding and removing Tags across multiple prompts in a single
  operation.

- **REQ-012 — Import/Export**  
  The system **MUST** support import and export of Tag and Category definitions in a structured
  format.

- **REQ-013 — Suggestions**  
  The system **MUST** provide Tag suggestions derived from prompt content and existing taxonomy.

- **REQ-014 — Undo Support**  
  The system **MUST** provide an undo capability for recent management operations.

- **REQ-015 — Search and Filter**  
  The system **MUST** provide search and filter over Tags and Categories by name and usage.

- **REQ-016 — Ordering**  
  The system **MUST** allow a custom order for Categories.

### 5.2 Security Requirements (SEC-***)

- **SEC-001 — Authentication Required**  
  The system **MUST** require authenticated access for all management operations.

- **SEC-002 — Authorization**  
  The system **MUST** enforce role-based access control for destructive operations
  (delete, merge, bulk delete, find-and-replace).

- **SEC-003 — Auditability**  
  The system **MUST** record audit events for create, update, delete, merge, bulk, and undo
  operations.

### 5.3 Non-Functional Requirements (NFR-***)

- **NFR-001 — Backward Compatibility**  
  The system **MUST NOT** change Compatibility Endpoints or their response shapes.

- **NFR-002 — Transactionality**  
  The system **MUST** execute rename, merge, bulk, and find-and-replace operations atomically.

- **NFR-003 — Deterministic Output**  
  The system **MUST** return deterministic ordering for list responses when no explicit order
  is provided.

- **NFR-004 — Input Validation**  
  The system **MUST** validate all inputs and reject invalid names or colors.

### 5.4 Error-Handling Requirements (ERR-***)

- **ERR-001 — Validation Errors**  
  The system **MUST** return a structured validation error when input constraints are violated.

- **ERR-002 — Not Found**  
  The system **MUST** return a structured error when a Tag or Category identifier does not exist.

- **ERR-003 — Conflict**  
  The system **MUST** return a structured conflict error when a rename or create would violate
  uniqueness constraints.

- **ERR-004 — Unauthorized**  
  The system **MUST** return a structured authorization error when access is denied.

- **ERR-005 — Precondition Failed**  
  The system **MUST** return a structured error when a destructive operation is requested without
  required confirmation.

---

## 6. Invariants (INV-***)

- **INV-001 — Unique Names**  
  Tag and Category names **MUST** be unique in a case-insensitive manner.

- **INV-002 — Category Cardinality**  
  A prompt **MUST** have at most one Category assigned.

- **INV-003 — Tag Cardinality**  
  A prompt **MAY** have zero or more Tags.

- **INV-004 — Referential Integrity**  
  Tag and Category references in prompts **MUST** reference existing Tag or Category entities.

- **INV-005 — Compatibility Output Shapes**  
  Compatibility Endpoints **MUST** return the same output shapes as specified in this document.

---

## 7. Interfaces & Data Contracts

### 7.1 Operations / API Overview

#### Operation: List Categories (Compatibility)

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories |
| Auth Required | no |
| Description | Returns list of Category names for legacy clients. |

#### Operation: List Tags (Compatibility)

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags |
| Auth Required | no |
| Description | Returns list of Tag names with usage counts for legacy clients. |

#### Operation: List Categories (Management)

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories/manage |
| Auth Required | yes |
| Description | Returns Category metadata with usage counts. |

#### Operation: Create Category

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories |
| Auth Required | yes |
| Description | Creates a Category. |

#### Operation: Update Category

| Field | Description |
|-------|-------------|
| Identifier | PUT /api/categories/{id} |
| Auth Required | yes |
| Description | Updates Category name/metadata. |

#### Operation: Delete Category

| Field | Description |
|-------|-------------|
| Identifier | DELETE /api/categories/{id} |
| Auth Required | yes |
| Description | Deletes Category with confirmation. |

#### Operation: Merge Categories

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/merge |
| Auth Required | yes |
| Description | Merges multiple Categories into a target. |

#### Operation: Bulk Delete Categories

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/bulk-delete |
| Auth Required | yes |
| Description | Deletes multiple Categories with confirmation. |

#### Operation: Find & Replace Category

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/find-replace |
| Auth Required | yes |
| Description | Replaces a Category name across prompts. |

#### Operation: Reorder Categories

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/reorder |
| Auth Required | yes |
| Description | Sets custom Category ordering. |

#### Operation: Category Orphans

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories/orphans |
| Auth Required | yes |
| Description | Returns prompts without Categories. |

#### Operation: Category Orphan Details

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories/orphans/details |
| Auth Required | yes |
| Description | Returns prompt IDs and titles for prompts without Categories. |

#### Operation: Category Unused

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories/unused |
| Auth Required | yes |
| Description | Returns Categories with zero associated prompts. |

#### Operation: Category Analytics

| Field | Description |
|-------|-------------|
| Identifier | GET /api/categories/analytics |
| Auth Required | yes |
| Description | Returns usage summaries. |

#### Operation: Category Import/Export

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/import; GET /api/categories/export |
| Auth Required | yes |
| Description | Imports or exports Category definitions. |

#### Operation: Category Undo

| Field | Description |
|-------|-------------|
| Identifier | POST /api/categories/undo |
| Auth Required | yes |
| Description | Undoes recent Category management operation. |

#### Operation: List Tags (Management)

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags/manage |
| Auth Required | yes |
| Description | Returns Tag metadata with usage counts. |

#### Operation: Create Tag

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags |
| Auth Required | yes |
| Description | Creates a Tag. |

#### Operation: Update Tag

| Field | Description |
|-------|-------------|
| Identifier | PUT /api/tags/{id} |
| Auth Required | yes |
| Description | Updates Tag name/metadata. |

#### Operation: Delete Tag

| Field | Description |
|-------|-------------|
| Identifier | DELETE /api/tags/{id} |
| Auth Required | yes |
| Description | Deletes Tag with confirmation. |

#### Operation: Merge Tags

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/merge |
| Auth Required | yes |
| Description | Merges multiple Tags into a target. |

#### Operation: Bulk Delete Tags

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/bulk-delete |
| Auth Required | yes |
| Description | Deletes multiple Tags with confirmation. |

#### Operation: Find & Replace Tag

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/find-replace |
| Auth Required | yes |
| Description | Replaces a Tag name across prompts. |

#### Operation: Tag Orphans

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags/orphans |
| Auth Required | yes |
| Description | Returns unused Tags. |

#### Operation: Tag Orphan Prompts

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags/orphan-prompts |
| Auth Required | yes |
| Description | Returns prompts without Tags. |

#### Operation: Tag Orphan Prompt Details

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags/orphan-prompts/details |
| Auth Required | yes |
| Description | Returns prompt IDs and titles for prompts without Tags. |

#### Operation: Tag Analytics

| Field | Description |
|-------|-------------|
| Identifier | GET /api/tags/analytics |
| Auth Required | yes |
| Description | Returns usage summaries and co-occurrence. |

#### Operation: Tag Suggestions

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/suggest |
| Auth Required | yes |
| Description | Suggests Tags based on prompt content. |

#### Operation: Tag Import/Export

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/import; GET /api/tags/export |
| Auth Required | yes |
| Description | Imports or exports Tag definitions. |

#### Operation: Tag Undo

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/undo |
| Auth Required | yes |
| Description | Undoes recent Tag management operation. |

#### Operation: Bulk Tag Update

| Field | Description |
|-------|-------------|
| Identifier | POST /api/tags/bulk-update |
| Auth Required | yes |
| Description | Adds/removes Tags across multiple prompts. |

### 7.2 Input Schema

#### CategoryCreateRequest

```json
{
  "name": "string",
  "description": "string",
  "color": "string",
  "sort_order": 0
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| name | string | yes | non-empty, max length, unique (case-insensitive) | Category name |
| description | string | no | max length | Category description |
| color | string | no | valid color token or hex | Category color |
| sort_order | integer | no | non-negative | Custom order value |

#### CategoryUpdateRequest

```json
{
  "name": "string",
  "description": "string",
  "color": "string",
  "sort_order": 0
}
```

Constraints identical to CategoryCreateRequest.

#### CategoryMergeRequest

```json
{
  "target_id": 0,
  "source_ids": [0],
  "confirm": true
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| target_id | integer | yes | must exist | Target Category identifier |
| source_ids | array[integer] | yes | all must exist; cannot include target_id | Categories to merge |
| confirm | boolean | yes | must be true | Confirmation flag |

#### CategoryBulkDeleteRequest

```json
{
  "ids": [0],
  "confirm": true
}
```

#### CategoryFindReplaceRequest

```json
{
  "find": "string",
  "replace": "string",
  "confirm": true
}
```

#### CategoryReorderRequest

```json
{
  "ordered_ids": ["string"]
}
```

#### TagCreateRequest

```json
{
  "name": "string",
  "description": "string",
  "color": "string",
  "parent_tag_id": 0
}
```

Constraints mirror CategoryCreateRequest except `sort_order`.

#### TagUpdateRequest

```json
{
  "name": "string",
  "description": "string",
  "color": "string",
  "parent_tag_id": 0
}
```

#### TagMergeRequest

```json
{
  "target_id": 0,
  "source_ids": [0],
  "confirm": true
}
```

#### TagBulkDeleteRequest

```json
{
  "ids": [0],
  "confirm": true
}
```

#### TagFindReplaceRequest

```json
{
  "find": "string",
  "replace": "string",
  "confirm": true
}
```

#### TagSuggestRequest

```json
{
  "prompt_id": 0,
  "content": "string",
  "limit": 10
}
```

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| prompt_id | integer | no | must exist if provided | Prompt identifier |
| content | string | no | non-empty if prompt_id missing | Prompt content |
| limit | integer | no | positive, max 50 | Max suggestions |

#### BulkTagUpdateRequest

```json
{
  "prompt_ids": [0],
  "add": ["string"],
  "remove": ["string"],
  "confirm": true
}
```

### 7.3 Output Schema

#### CategoryListCompatibilityResponse

```json
{
  "categories": ["string"]
}
```

#### TagListCompatibilityResponse

```json
{
  "tags": [
    {
      "name": "string",
      "count": 0
    }
  ]
}
```

#### CategoryManagementResponse

```json
{
  "items": [
    {
      "id": 0,
      "name": "string",
      "description": "string",
      "color": "string",
      "sort_order": 0,
      "usage_count": 0,
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

#### TagManagementResponse

```json
{
  "items": [
    {
      "id": 0,
      "name": "string",
      "description": "string",
      "color": "string",
      "parent_tag_id": 0,
      "usage_count": 0,
      "created_at": "string",
      "updated_at": "string"
    }
  ]
}
```

#### SuggestionResponse

```json
{
  "suggestions": [
    {
      "name": "string",
      "score": 0.0
    }
  ]
}
```

### 7.4 Error Model

| Status | Code | Condition | Description |
|--------|------|-----------|-------------|
| 400 | ERR-VALIDATION | Invalid input fields or constraints violated | Input rejected |
| 401 | ERR-AUTH | Authentication missing or invalid | Access denied |
| 403 | ERR-FORBIDDEN | Insufficient privileges | Access denied |
| 404 | ERR-NOT-FOUND | Tag/Category/Prompt not found | Resource missing |
| 409 | ERR-CONFLICT | Name uniqueness conflict or merge conflict | Conflict detected |
| 412 | ERR-PRECONDITION | Confirmation flag missing or false | Precondition not met |
| 422 | ERR-UNPROCESSABLE | Operation cannot be completed (e.g., orphaning prompts without override) | Operation blocked |

---

## 8. Acceptance Criteria (AC-***)

### 8.1 Acceptance Criteria & Requirements Mapping

| ID | Criterion (summary) | Requirement IDs | Test Cases |
|----|----------------------|-----------------|-----------|
| AC-TCM-001 | Compatibility endpoints unchanged | REQ-001, NFR-001, INV-005 | TEST-REQ-001 |
| AC-TCM-002 | CRUD operations for Tags and Categories | REQ-002, REQ-003 | TEST-REQ-001 |
| AC-TCM-003 | Rename/merge update all prompts atomically | REQ-004, REQ-005, NFR-002 | TEST-REQ-001 |
| AC-TCM-004 | Bulk delete requires confirmation | REQ-006, ERR-005 | TEST-REQ-002 |
| AC-TCM-005 | Orphan detection available | REQ-007 | TEST-REQ-001 |
| AC-TCM-006 | Usage analytics available | REQ-008, REQ-009 | TEST-REQ-001 |
| AC-TCM-007 | Find-and-replace applied system-wide | REQ-010 | TEST-REQ-001 |
| AC-TCM-008 | Bulk tag update works across prompts | REQ-011 | TEST-REQ-001 |
| AC-TCM-009 | Import/export validates and persists definitions | REQ-012 | TEST-REQ-001 |
| AC-TCM-010 | Suggestions returned for content | REQ-013 | TEST-REQ-001 |
| AC-TCM-011 | Undo restores prior state | REQ-014 | TEST-REQ-001 |
| AC-TCM-012 | Search and filter supported | REQ-015 | TEST-REQ-001 |
| AC-TCM-013 | Category ordering preserved | REQ-016 | TEST-REQ-001 |
| AC-TCM-014 | Auth and authorization enforced | SEC-001, SEC-002 | TEST-REQ-002 |

---

## 9. Test Requirements (TEST-REQ-***)

- **TEST-REQ-001**: All functional requirements and invariants MUST have automated tests.
- **TEST-REQ-002**: All error conditions in section 7.4 MUST be tested.
- **TEST-REQ-003**: All operations that change prompts MUST verify atomicity.
- **TEST-REQ-004**: Compatibility endpoints MUST be validated against expected shapes.

---

## 10. Dependencies (Conceptual Only)

- **EXT-001**: Authentication provider for identity verification.
- **EXT-002**: Authorization policy enforcement.
- **EXT-003**: Audit logging capability.

---

## 11. Examples & Edge Cases

NOTE: Examples are illustrative only.

- Case-insensitive conflicts: creating "AI" when "ai" exists MUST fail with ERR-CONFLICT.
- Merge with target in sources MUST fail with ERR-VALIDATION.
- Bulk delete without confirmation MUST fail with ERR-PRECONDITION.
- Tag suggestions with empty content and no prompt_id MUST fail with ERR-VALIDATION.
- Reorder request with missing or duplicated IDs MUST fail with ERR-VALIDATION.

---

## 12. Versioning & Change Policy

- **VPOL-001**: The specification follows semantic versioning.
- **VPOL-002**: Breaking changes require a major version increment.
- **VPOL-003**: Backward-compatible changes require a minor version increment.
- **VPOL-004**: Patch updates apply to clarifications and non-functional corrections only.
- **VPOL-005**: Compatibility Endpoints MUST remain stable across minor versions.

---

## 13. Traceability Matrix

| Requirement ID | AC IDs | TEST-REQ IDs | Interfaces |
|----------------|--------|--------------|------------|
| REQ-001 | AC-TCM-001 | TEST-REQ-004 | GET /api/categories, GET /api/tags |
| REQ-002 | AC-TCM-002 | TEST-REQ-001 | POST/PUT/DELETE /api/categories |
| REQ-003 | AC-TCM-002 | TEST-REQ-001 | POST/PUT/DELETE /api/tags |
| REQ-004 | AC-TCM-003 | TEST-REQ-003 | PUT /api/categories/{id}, PUT /api/tags/{id} |
| REQ-005 | AC-TCM-003 | TEST-REQ-003 | POST /api/categories/merge, POST /api/tags/merge |
| REQ-006 | AC-TCM-004 | TEST-REQ-002 | POST /api/*/bulk-delete |
| REQ-007 | AC-TCM-005 | TEST-REQ-001 | GET /api/categories/orphans, GET /api/categories/unused, GET /api/tags/orphans, GET /api/tags/orphan-prompts |
| REQ-008 | AC-TCM-006 | TEST-REQ-001 | GET /api/*/analytics |
| REQ-009 | AC-TCM-006 | TEST-REQ-001 | GET /api/tags/analytics |
| REQ-010 | AC-TCM-007 | TEST-REQ-001 | POST /api/*/find-replace |
| REQ-011 | AC-TCM-008 | TEST-REQ-001 | POST /api/tags/bulk-update |
| REQ-012 | AC-TCM-009 | TEST-REQ-001 | POST /api/*/import, GET /api/*/export |
| REQ-013 | AC-TCM-010 | TEST-REQ-001 | POST /api/tags/suggest |
| REQ-014 | AC-TCM-011 | TEST-REQ-001 | POST /api/*/undo |
| REQ-015 | AC-TCM-012 | TEST-REQ-001 | GET /api/*/manage |
| REQ-016 | AC-TCM-013 | TEST-REQ-001 | POST /api/categories/reorder |
| SEC-001 | AC-TCM-014 | TEST-REQ-002 | All management interfaces |
| SEC-002 | AC-TCM-014 | TEST-REQ-002 | All destructive interfaces |
| NFR-001 | AC-TCM-001 | TEST-REQ-004 | Compatibility interfaces |
| INV-001 | AC-TCM-002 | TEST-REQ-001 | Create/rename interfaces |
| INV-004 | AC-TCM-003 | TEST-REQ-003 | Merge/delete interfaces |

---

## 14. Related Specifications / References

- docs/PLAN_TAG_CATEGORY_MANAGEMENT.md
- docs/SPECS/SPEC_DATABASE.md
