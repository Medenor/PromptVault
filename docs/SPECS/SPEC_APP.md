---
id: spec-app-promptvault
title: PromptVault Application Functional Specification
version: 1.0.1
date_created: 2025-11-27
last_updated: 2025-12-10
owner: medenor
tags: [app, functional, architecture, prompt-management]
status: published
---

## 1. Introduction

This specification defines the expected functional behavior, constraints, interfaces, and invariants of the **PromptVault** web application.

The goal is to provide a **single, technology-agnostic contract** that can be used by humans and Generative AI agents to implement, refactor, and test the application consistently. It describes **WHAT** the system MUST do, not HOW it is implemented.

---

## 2. Purpose, Scope, and Out-of-Scope

### 2.1 Purpose

- Provide a **canonical functional specification** for the PromptVault application.
- Enable **spec-driven development**, automated test generation, and AI-assisted implementation.
- Define the **core domain model** (prompts, versions, backups) and main application behaviors.

### 2.2 In Scope

This specification covers:

- Prompt lifecycle:
  - creation, update, deletion, and retrieval
  - versioning, comparison, and revert
- Import and export of prompts in supported formats.
- Backup creation, listing, restoration, and related safety behaviors.
- Input validation rules and standardized error responses.
- Logging and observability expectations at the application level.
- High-level non-functional requirements (test coverage, safety, data integrity).

### 2.3 Out of Scope

The following topics are **explicitly out of scope** for this spec and are (or will be) covered by separate specifications:

- Authentication, authorization, RBAC, and user management  
  → see [SPEC_AUTHENTICATION](SPEC_AUTHENTICATION.md).
- Detailed database schema and migration behavior  
  → see [SPEC_DATABASE](SPEC_DATABASE.md).
- Deployment, infrastructure, and container orchestration details.
- Frontend layout, styling, and UI/UX design specifics.
- Implementation details of particular libraries or frameworks.

### 2.4 Assumptions

- The system is used as a **web-first application**.
- A persistent storage mechanism exists that can:
  - store prompts and versions,
  - store backups,
  - store logs.
- There is a separate **authentication layer** ensuring that calls to protected endpoints are properly authenticated.
- For small structural details, the codebase MAY introduce implementation-specific variations, but MUST NOT violate any requirement, invariant, or contract defined in this spec.

---

## 3. Definitions & Terminology

- **Prompt**  
  A data entity with an identifier, content, title, category, tags, optional note, favorite flag, and associated metadata.

- **Version**  
  An immutable snapshot of a Prompt at a specific point in time. Includes:
  - `version_id` (unique identifier),
  - timestamp,
  - author,
  - commit message,
  - snapshot of prompt data,
  - optional parent version(s).

- **Version History / Version Graph**  
  The ordered (and potentially branching) set of Versions associated with a Prompt. It MUST behave like an append-only history.

- **Backup**  
  A persisted snapshot of the dataset (or subset) intended for restoration. Includes metadata (timestamp, scope, name, etc.).

- **Service**  
  A logical business-layer module responsible for a bounded responsibility (e.g., prompt management, backup management). The internal structure is out of scope.

- **API Contract**  
  The shape of request and response payloads exposed via HTTP endpoints. Defined in this spec as JSON-like schemas.

- **Bulk Operation**  
  An operation that applies to multiple prompts at once (e.g. bulk delete).

---

## 4. Functional Requirements

All requirements use normative language:

- **REQ-001 (API Validation)**  
  All API endpoints that accept a request body MUST validate that body against a well-defined schema. Invalid inputs MUST result in standardized error responses and MUST NOT alter persisted data.

- **REQ-002 (Prompt Creation)**  
  The system MUST allow creation of new prompts with:
  - title  
  - prompt content  
  - optional category, tags, note  
  When a prompt is created, the system MUST also create an initial Version associated with that prompt.

- **REQ-003 (Prompt Update & Versioning)**  
  Every update to a prompt that modifies persisted data:
  - MUST create a new immutable Version with a unique `version_id` and associated metadata (timestamp, author, commit message).
  - MUST NOT modify existing versions in place.

- **REQ-004 (Version Listing & Retrieval)**  
  For any prompt, the system MUST:
  - provide an endpoint to list its versions (with optional pagination),
  - provide an endpoint to retrieve a specific version by `version_id`.

- **REQ-005 (Version Comparison & Revert)**  
  The system MUST:
  - allow comparison of any two versions of the same prompt (at least by presenting the two payloads),
  - allow reverting a prompt to a previous version. Reverting MUST create a **new** Version reflecting the revert action and MUST NOT delete or overwrite historical versions.

- **REQ-006 (Data-Loss-Prone Operations & Backups)**  
  Any operation that can cause data loss (e.g. delete, restore from backup) MUST:
  - create an automatic backup before applying the change,
  - make that backup discoverable via backup listing,
  - allow recovery from the backup.

- **REQ-007 (Import)**  
  The system MUST support importing prompts from files in at least the following formats:
  - CSV
  - JSON
  - Markdown  
  Import MUST:
  - validate format and content,
  - provide a preview or dry-run mode (where applicable),
  - reject invalid or unsupported files without modifying existing data.

- **REQ-008 (Export)**  
  The system MUST support exporting prompts (and optionally their versions) to:
  - CSV
  - JSON
  - Markdown  
  The export operation MUST:
  - respect the requested format,
  - return data in a consistent, machine-readable structure.

- **REQ-009 (Field Constraints)**  
  The system MUST enforce the following constraints:
  - `title`: string, 1–200 characters (non-whitespace).
  - `prompt`: string, 1–50,000 characters.
  - `category`: optional string, max 100 characters.
  - `tags`: optional list of strings, max 50 tags, each tag max 50 characters.
  - `note`: optional string, max 2,000 characters.
  - `backup name`: optional string, max 64 characters, safe characters only.
  - `bulk delete prompt_ids`: list of integers, 1–1000 items, all unique.
  - file uploads: max size 10 MB.

- **REQ-010 (Logging)**  
  The system MUST produce structured logs in a machine-readable format (e.g. newline-delimited JSON) suitable for audit and analysis. Logs MUST be persisted in a configurable location.

- **REQ-011 (Error Reporting)**  
  Validation and conversion errors MUST use a standardized error structure, including:
  - a general error message,
  - human-readable details,
  - machine-readable error entries (type, location, message).

- **NFR-001 (Test Coverage)**  
  The codebase implementing this spec MUST maintain at least 85% automated test coverage for the core application logic, including:
  - prompt lifecycle,
  - versioning,
  - import/export,
  - backup operations.

- **CON-001 (Application Form Factor)**  
  The primary form factor of the application MUST be a web application accessible via HTTP.

- **CON-002 (Canonical Persistence)**  
  A relational database MUST be the canonical persistence layer for new deployments. Legacy JSON-file-based storage MAY be supported for backward compatibility and migration purposes but MUST NOT diverge in behavior from the contracts defined here.

- **GUD-001 (Service Boundaries)**  
  Logical service boundaries SHOULD remain focused and cohesive. For example, backup-related logic SHOULD reside in a dedicated backup service rather than being embedded in prompt management logic.

- **PAT-001 (Git-like Versioning Pattern)**  
  Versioning SHOULD follow a Git-like pattern: every change is treated as a commit with metadata (author, message, timestamp, parents, version_id).

---

## 5. Invariants

The following invariants MUST always hold:

- **INV-001 (Immutable Versions)**  
  Once created, a Version MUST be immutable. Its content and metadata MUST NOT be changed.

- **INV-002 (Append-Only Version History)**  
  The version history of a prompt MUST be append-only. Reverts, imports that affect existing prompts, and other modifications MUST result in new Versions being appended.

- **INV-003 (Backup Safety)**  
  For any destructive operation (e.g. delete, restore), there MUST exist at least one backup created **before** the operation is applied.

- **INV-004 (Consistent Constraints)**  
  Validation constraints defined in **REQ-009** MUST be enforced consistently across:
  - API requests,
  - import flows (file-based),
  - internal service calls (where applicable).

- **INV-005 (Error Format Consistency)**  
  All validation errors exposed via API MUST follow the same error structure, regardless of which component detected the error.

- **INV-006 (Bulk Operations Integrity)**  
  Bulk operations MUST treat each prompt independently and MUST return:
  - successful operations,
  - failed operations,  
  in a way that makes it clear which prompt IDs were processed and with what outcome.

---

## 6. Interfaces & Data Contracts

This section defines the **observable contracts** of the main HTTP API. It does not dictate implementation details.

### 6.1 Common Conventions

- Content type for JSON APIs: `application/json`.
- File upload: `multipart/form-data`.
- All responses MUST be valid JSON when they include a body.
- For validation errors:
  - `400 Bad Request` MAY be used for format or transport-level issues (e.g. invalid file).
  - `422 Unprocessable Entity` SHOULD be used for schema / field-level validation failures.

### 6.2 Main Prompt Endpoints (Conceptual)

#### 6.2.1 List Prompts

- **Method & Path**: `GET /api/prompts`
- **Auth**: As required by auth spec (not defined here).
- **Purpose**: List prompts with optional filtering.

**Query Parameters (conceptual):**

| Name       | Type     | Description                           |
|------------|----------|---------------------------------------|
| tags       | string[] | Filter prompts by tags                |
| category   | string   | Filter prompts by category            |
| search     | string   | Full-text search in title/prompt      |
| favorite   | bool     | Filter by favorite flag               |
| page       | int      | Optional pagination page              |
| page_size  | int      | Optional page size                    |

**Success Response (200):**

- Body: array of **PromptSummary** objects (at minimum: id, title, category, tags, favorite, created_at, updated_at).

---

#### 6.2.2 Create Prompt

- **Method & Path**: `POST /api/prompts`
- **Auth**: Required.
- **Purpose**: Create a new prompt and its initial version.

**Request Body:**

```json
{
  "title": "string (1-200 chars)",
  "prompt": "string (1-50000 chars)",
  "category": "optional string (<=100 chars)",
  "tags": ["optional string, <=50 chars, max 50 items"],
  "note": "optional string (<=2000 chars)"
}
```

**Success Response (201):**

```json
{
  "id": 123,
  "data": {
    "title": "Improve email subject",
    "prompt": "Create a short email subject that increases open rates...",
    "category": "Marketing",
    "tags": ["email", "marketing"],
    "note": "Short objective explanation",
    "favorite": false
  },
  "versions": [
    {
      "version_id": "uuid-v1",
      "timestamp": "2025-11-27T12:34:56Z",
      "author": "user-id-or-name",
      "message": "Initial creation",
      "data": {},
      "parents": []
    }
  ],
  "branches": {
    "main": "uuid-v1"
  }
}
```

**Error Responses:**

| Status | Condition                                  |
|--------|--------------------------------------------|
| 400    | Malformed JSON or invalid payload format   |
| 422    | Field-level validation failure             |

---

#### 6.2.3 Update Prompt

- **Method & Path**: `PUT /api/prompts/{id}`
- **Auth**: Required.
- **Purpose**: Update an existing prompt and create a new version.

**Request Body (partial fields allowed):**

```json
{
  "title": "optional string",
  "prompt": "optional string",
  "category": "optional string",
  "tags": ["optional string"],
  "note": "optional string",
  "commit_message": "string (1-500 chars)"
}
```

**Behavior:**

- Valid updates MUST:
  - apply to the current prompt data,
  - create a new Version with updated data and the given commit message.

**Success Response (200):**

- Returns updated prompt representation, including updated version history.

**Error Responses:**

| Status | Condition                            |
|--------|--------------------------------------|
| 404    | Prompt not found                     |
| 422    | Validation or constraint violation   |

---

#### 6.2.4 Delete Prompt

- **Method & Path**: `DELETE /api/prompts/{id}`
- **Auth**: Required.
- **Purpose**: Delete a single prompt.

**Behavior:**

- MUST create an automatic backup before deletion.
- MUST remove the prompt from normal listing endpoints once deleted.

**Success Response (200 or 204):**

- MAY return statistics or metadata about the deletion and backup.

---

#### 6.2.5 Bulk Delete Prompts

- **Method & Path**: `DELETE /api/prompts/bulk`
- **Auth**: Required.
- **Purpose**: Delete multiple prompts in a single operation.

**Request Body:**

```json
{
  "prompt_ids": [1, 2, 3]
}
```

Constraints:

- `prompt_ids`: 1–1000 unique integers.

**Behavior:**

- MUST create at least one backup capturing all affected prompts prior to deletion.
- MUST return per-ID success/failure information.

**Success Response (200):**

```json
{
  "deleted_count": 3,
  "failed_ids": [],
  "backup_id": "backup-uuid"
}
```

---

#### 6.2.6 Version Operations

##### List Versions

- **Method & Path**: `GET /api/prompts/{id}/versions`
- Returns a list of version summaries: `version_id`, timestamp, author, message.

##### Get Version

- **Method & Path**: `GET /api/prompts/{id}/versions/{version_id}`
- Returns full Version payload, including snapshot data.

##### Revert Version

- **Method & Path**: `POST /api/prompts/{id}/versions/{version_id}/revert`
- Behavior:
  - MUST restore data from the target version,
  - MUST create a new Version representing the revert action.

---

#### 6.2.7 Import & Export

##### Import

- **Method & Path**: `POST /api/import`
- **Content Type**: `multipart/form-data`
- Fields:
  - file: uploaded file
  - format: one of `csv`, `json`, `markdown`
  - preview (optional): boolean

**Behavior:**

- For `preview = true`, MUST parse and validate without persisting.
- For `preview = false`, MUST persist valid data and return a summary.

##### Export

- **Method & Path**: `POST /api/export`
- **Content Type**: `application/json`
- Request fields:
  - format: `csv`, `json`, `markdown`
  - include_versions: optional boolean
  - filename: optional suggested filename

**Behavior:**

- MUST return appropriate content in the chosen format.

---

#### 6.2.8 Backups

##### List Backups

- **Method & Path**: `GET /api/backups`
- Returns backup metadata (id, name, created_at, scope).

##### Create Backup

- **Method & Path**: `POST /api/backups`
- Request fields:
  - name: optional string
  - include_versions: optional boolean

##### Restore Backup

- **Method & Path**: `POST /api/backups/{backup_id}/restore`
- Behavior:
  - MUST create a pre-restore backup,
  - MUST restore state from the given backup.

##### Compress Backups

- **Method & Path**: `POST /api/backups/compress`
- Purpose: apply retention/compression rules to older backups.

---

### 6.3 Standardized Error Response (Conceptual)

Validation error responses SHOULD follow this structure:

```json
{
  "error": "Validation failed",
  "details": ["field: message"],
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "Title cannot be empty or whitespace only",
      "input": "   "
    }
  ]
}
```

---

## 7. Acceptance Criteria

Each criterion is testable and maps to one or more requirements.

- **AC-001 (Prompt Creation)**  
  Given a valid create request,  
  When the client sends `POST /api/prompts` with valid data,  
  Then the system MUST:
  - return `201`,
  - persist the prompt,
  - create an initial Version,
  - return the persisted entity and version metadata.

- **AC-002 (Versioned Update)**  
  Given an existing prompt and a valid update with `commit_message`,  
  When `PUT /api/prompts/{id}` is called,  
  Then the system MUST:
  - update the current prompt data,
  - create a new Version,
  - keep previous Versions unchanged.

- **AC-003 (Backup on Destructive Operations)**  
  Given a prompt or multiple prompts targeted for deletion or a restore operation,  
  When a delete or restore API is called and succeeds,  
  Then the system MUST:
  - create at least one backup before applying the operation,
  - make that backup visible in `GET /api/backups`.

- **AC-004 (Import Validation)**  
  Given an import file with invalid format or disallowed MIME type,  
  When `POST /api/import` is called,  
  Then the system MUST:
  - return a `400` or `422` error with standardized validation details,
  - NOT modify the existing data.

- **AC-005 (Backup Restore Behavior)**  
  Given a valid `backup_id`,  
  When `POST /api/backups/{backup_id}/restore` succeeds,  
  Then the system MUST:
  - create a pre-restore backup,
  - restore the state from the chosen backup,
  - ensure Version history remains consistent with the restored data.

- **AC-006 (Test Coverage)**  
  When the test suite is executed in CI,  
  Then the system MUST enforce at least 85% coverage for core application logic. A failure to reach this threshold MUST fail the CI check.

---

## 8. Test Requirements (Conceptual)

These describe **what** must be tested, not how.

- **TEST-REQ-001 (Prompt Lifecycle)**  
  There MUST be automated tests covering:
  - create, read, update, delete of prompts,
  - single and bulk delete flows.

- **TEST-REQ-002 (Versioning)**  
  Tests MUST verify:
  - every update creates a new Version,
  - revert operations create new Versions without altering history,
  - Version retrieval by `version_id` behaves as specified.

- **TEST-REQ-003 (Import/Export)**  
  Tests MUST verify:
  - valid imports for CSV, JSON, Markdown,
  - rejections for invalid files (format, MIME type, size, schema),
  - correct exports in all supported formats.

- **TEST-REQ-004 (Backups)**  
  Tests MUST verify:
  - automatic backups on destructive operations,
  - manual backup creation,
  - successful restore including pre-restore backup behavior.

- **TEST-REQ-005 (Validation & Error Format)**  
  Tests MUST assert:
  - field constraints from REQ-009,
  - standardized error response structure,
  - correct HTTP status codes for validation and format errors.

- **TEST-REQ-006 (Non-Regression)**  
  Critical flows (prompt lifecycle, versioning, import/export, backup/restore) MUST be covered by integration tests to detect regressions.

---

## 9. Dependencies (Conceptual Only)

### 9.1 External Systems

- **EXT-001 (Browser Client)**  
  Purpose: Consume the HTTP API and render the UI. Integration type: HTTP requests and static assets.

### 9.2 Third-Party Services

- **SVC-001 (Optional Offsite Storage)**  
  Purpose: Store backups in an external persistent location.  
  Requirements: MUST preserve integrity and durability of backup data.

- **SVC-002 (Optional Error/Monitoring Service)**  
  Purpose: Capture errors and metrics.  
  Requirements: MUST allow PII scrubbing and opt-out.

### 9.3 Infrastructure Dependencies

- **INF-001 (Persistent Storage)**  
  The application MUST have access to persistent storage for:
  - database or equivalent primary store,
  - backups,
  - logs.

### 9.4 Data Dependencies

- **DAT-001 (Database)**  
  A database or equivalent system MUST be used as the canonical store for prompts, versions, and backups.

### 9.5 Compliance Dependencies

- **COM-001 (License Compliance)**  
  The project MUST remain compliant with its chosen license (e.g. MPL 2.0), including required license headers in source files.

---

## 10. Examples & Edge Cases

- **Valid Create Prompt Example**

```json
POST /api/prompts
{
  "title": "Short Subject",
  "prompt": "Write a short subject line for an email",
  "category": "Marketing",
  "tags": ["email", "subject"],
  "note": "Keep it short"
}
```

Expected:

- `201 Created`,
- new prompt persisted,
- initial Version created.

- **Invalid Tags Example**  
  Request with 51 tags MUST produce a 422 validation error.

- **Malformed Import File**  
  - CSV missing required columns MUST result in 400/422 and no data changes.
  - Markdown with unsupported structure MUST be rejected.

- **Revert Without Content Change**  
  Reverting to a version whose content equals the current state MUST still create a new Version capturing:
  - revert intent,
  - author,
  - commit message.

- **Storage Corruption / Inaccessible Data**  
  If primary storage is corrupted or cannot be accessed:
  - the system SHOULD rely on available backups and recovery mechanisms,
  - if automatic repair is not possible, the system SHOULD fail safely and log clear diagnostics.

---

## 11. Versioning & Change Policy

- **VPOL-001**: This specification follows semantic versioning:
  - Major: incompatible changes to data contracts, invariants, or external behavior.
  - Minor: backward-compatible additions to functionality or interfaces.
  - Patch: backward-compatible bug fixes or clarifications.

- **VPOL-002**: A change is considered breaking if it:
  - Alters any existing field name, type, or semantics in the defined schemas.
  - Changes the behavior of existing operations in a way that violates any REQ, INV, or AC marked in this document.
  - Removes an existing operation or data field without providing a backward-compatible alternative.

- **VPOL-003**: When a breaking change is required:
  - The major version of this spec **MUST** be incremented.
  - Dependent specifications (e.g., application or API specs) **MUST** be updated to reference the new version and document the impact.

- **VPOL-004**: Backward-compatible changes (minor or patch) **SHOULD** be documented with clear notes, and any new optional fields or operations **MUST NOT** change behavior for clients that do not use them.

- Dependent specs (e.g. [SPEC_AUTHENTICATION](SPEC_AUTHENTICATION.md), [SPEC_DATABASE](SPEC_DATABASE.md)) MUST be reviewed and updated when changes affect cross-cutting behaviors.

---

## 12. Related Specifications / Further Reading

- [SPEC_AUTHENTICATION](SPEC_AUTHENTICATION.md) — Authentication & authorization spec (login, sessions, RBAC).
- [SPEC_DATABASE](SPEC_DATABASE.md) — Database schema and persistence behavior specification.
- Security policy and project overview documents as defined in the repository ([SECURITY](../SECURITY.md), [README](../../README.md), [ROADMAP](../ROADMAP.md)).
