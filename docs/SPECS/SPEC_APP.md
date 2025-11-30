---
title: PromptVault Application Architecture
version: 1.0
date_created: 2025-11-27
last_updated: 2025-11-27
owner: medenor
status: published
tags: [architecture, app, prompt-management, design]
---

## Introduction

This specification defines the architecture, requirements, constraints, and interfaces for the PromptVault web application. It is intended to be clear, precise, and machine-parsable so that Generative AIs and developers can unambiguously implement, test, and validate the application.

This document is self-contained and references local repository documentation where additional implementation details are required.

### 1. Purpose & Scope

- Purpose: Provide a single-source architecture specification for the entire PromptVault application to enable development, testing, automation, and AI-assisted feature generation.
- Scope: Covers the main system components and responsibilities including data persistence, version control, import/export, backup, the web REST API, validation/monitoring, observability, and testing requirements.
- Audience: Developers, QA engineers, DevOps, and Generative AI agents that work on coding, testing, or maintaining PromptVault.
- Assumptions: The repository's implementation (FastAPI backend, Jinja2 frontend, Python services) is authoritative for small structural details; this spec defines architectural boundaries and contracts.

### 2. Definitions

- Prompt: A data entity with an identifier, content, title, category, tags, version history, favorites, and metadata.
- Version: A distinct, immutable representation of a Prompt at a specific point in time, with metadata (timestamp, author, message) and a unique version_id.
- Backup: A persisted snapshot of the entire data set (or subset) that includes metadata for restoration and retention management.
- Service: Logical business-layer modules in `src/services/` that implement a bounded responsibility (e.g., PromptDataService).
- API Contract: The Pydantic models used by FastAPI to define request/response shapes and validation rules.

### 3. Requirements, Constraints & Guidelines

- **REQ-001**: All API endpoints must use Pydantic schemas and enforce server-side validation for every POST/PUT request.
- **REQ-002**: Every prompt update must create a new independent immutable version with UUID-like `version_id` and full metadata.
- **REQ-003**: The system must provide a way to list a prompt's versions, compare any two versions and revert to a previous version (revert must create a new version rather than removing history).
- **REQ-004**: All write operations that can cause data loss (delete, restore) must create automatic backups before proceeding and expose undo or audit trails.
- **REQ-005**: The system must provide import and export features for CSV, Markdown, and JSON formats including validation and preview.
- **REQ-006**: Input validation rules: Title: 1-200 chars, Prompt: 1-50000 chars, Category: <=100 chars, Tags <=50 items with tag length <=50, Backup name <=64 chars, file upload <=10MB.
- **REQ-007**: Structured, newline-delimited JSON logs stored in `data/logs` for auditability and integration with log analysis tools.
- **REQ-008**: Tests must achieve a minimum coverage of 85% for source files and the repository must include integration-level tests for critical flows (backup, versioning, import/export).
- **SEC-001**: All user-supplied filenames must be sanitized; directory traversal and path separators in user-provided names are forbidden.
- **SEC-002**: File upload validation must check MIME type and extension matches (whitelist: .csv, .json, .md/.markdown, .txt), size <= 10MB.
- **CON-001**: The app is web-first; the repository only supports the web app. The legacy desktop app is deprecated.
- **CON-002**: By default, the app uses a relational database (SQLite for development, PostgreSQL for production) as the canonical persistence layer. Legacy JSON file-backed storage under `data/` is still supported for backward compatibility and migration scenarios; a migration script (`scripts/migrate_json_to_db.py`) is provided to safely migrate legacy JSON data to the database.
- **GUD-001**: Prefer clear, small service boundaries (e.g., PromptDataService should not implement backup management directly; those live in BackupService).
- **PAT-001**: Follow a Git-like versioning pattern that treats every update as a commit: metadata includes author, timestamp, message, parents, version_id.

### 4. Interfaces & Data Contracts

The repository uses FastAPI with Pydantic models. The following API endpoints represent the primary integration surface.

### Main API Endpoints (non-exhaustive)

- GET /api/prompts: List prompts with filter parameters (tags, category, text search, favorited). Returns 200 with array of PromptSummary.
- POST /api/prompts: Create a new prompt. Expects `PromptCreateRequest`. Returns 201 with Prompt resource and created version metadata.
- PUT /api/prompts/{id}: Update a prompt. Expects `PromptUpdateRequest` (including `commit_message`). Returns 200 and a new version.
- DELETE /api/prompts/{id}: Delete a single prompt (creates automatic backup).
- DELETE /api/prompts/bulk: Delete multiple prompts. Expects `BulkDeleteRequest` with 1-1000 unique prompt IDs. Creates automatic backup before deletion. Returns statistics on successful and failed deletions.
- GET /api/prompts/{id}: Get a prompt with current data, versions summary.
- GET /api/prompts/{id}/versions: List prompt versions (pagination optional).
- GET /api/prompts/{id}/versions/{version_id}: Get specific version payload.
- POST /api/prompts/{id}/versions/{version_id}/revert: Revert prompt to `version_id` (creates a new version).
- POST /api/import: File-based import with `ImportRequest` and upload field.
- POST /api/export: Export according to `ExportRequest`.
- GET /api/backups: List backups and their metadata.
- POST /api/backups: Create manual backup. Request: `BackupCreateRequest`.
- POST /api/backups/{backup_id}/restore: Restore a backup (auto pre-restore backup created).
- POST /api/backups/compress: Compress backups older than threshold.

### Example Pydantic / JSON Schemas (canonical shapes)

Prompt data schema (JSON example — API payloads remain JSON while storage is database-backed):

```json
{
  "id": 123,
  "data": {
    "title": "Improve email subject",
    "prompt": "Create a short email subject that increases open rates...",
    "category": "Marketing",
    "tags": ["email","marketing"],
    "note": "Short objective explanation",
    "favorite": false
  },
  "versions": [
    {
      "version_id": "uuid-v1",
      "timestamp": "2025-11-27T12:34:56Z",
      "author": "raphael",
      "message": "Updated prompt content",
      "data": {},
      "parents": ["uuid-v0"]
    }
  ],
  "branches": {"main": "uuid-v1"}
}
```

Pydantic model examples (Python-like pseudo-code to be used as guidance):

```python
class PromptCreateRequest(BaseModel):
    title: str  # min_length=1, max_length=200
    prompt: str  # min_length=1, max_length=50000
    category: Optional[str] = None  # max_length=100
    tags: Optional[List[str]] = []  # max_items=50, each max_length=50
    note: Optional[str] = None  # max_length=2000


class PromptUpdateRequest(BaseModel):
    title: Optional[str]
    prompt: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    note: Optional[str]
    commit_message: str  # min_length=1, max_length=500


class ExportRequest(BaseModel):
    format: Literal['csv', 'json', 'markdown']
    include_versions: Optional[bool] = False
    filename: Optional[str] = 'export'


class ImportRequest(BaseModel):
    format: Literal['csv','json','markdown']
    preview: Optional[bool] = False
    filename: str


class BackupCreateRequest(BaseModel):
    name: Optional[str]
    include_versions: Optional[bool] = True


class BulkDeleteRequest(BaseModel):
    prompt_ids: List[int]  # min_items=1, max_items=1000, unique values only
```

Field-level constraints (machine readable):

- `title`: string, min length 1, max length 200
- `prompt`: string, min length 1, max length 50000
- `category`: string, max length 100
- `tags`: array[string], max_items 50, each max_length 50
- `note`: string, max length 2000
- `commit_message` (on updates): min length 1, max length 500
- `backup_name`: string, safe characters only, max length 64
- `prompt_ids` (bulk delete): array[integer], min_items 1, max_items 1000, unique values only

Transport/Integration Notes

- All endpoints should use `application/json` for request/response content where applicable.
- File upload endpoints expect `multipart/form-data` with enforced file extension and MIME type constraints.
- Standardized error response structure follows `docs/API_VALIDATION_AND_MONITORING.md` and uses HTTP 422 for Pydantic validation errors and 400 for upload or conversion errors.

Standardized Error Response (Validation):

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

### 5. Acceptance Criteria

- **AC-001**: Given a valid `PromptCreateRequest`, When the API receives it, Then the service shall persist the new prompt, return `201` with the stored entity, and create an initial version with metadata.
- **AC-002**: Given an update request with `commit_message`, When applied, Then the system shall create a new `version` entry, update the `branches.main` pointer, and preserve previous versions unmodified.
- **AC-003**: Given a delete or restore operation, When the action is confirmed, Then an automatic backup is created before the operation completes and stored in `data/backups` with metadata.
- **AC-004**: Given an import file with invalid format or disallowed MIME type, When the server processes the import, Then it should return `400` with a standardized validation error and not modify the persisted data.
- **AC-005**: Given the backup restore operation, When it completes successfully, Then the system should create a pre-restore backup, restore state, and increment the version history accordingly if changes are applied.
- **AC-006**: The codebase must keep a minimum unit/integration test coverage of 85% as enforced by CI settings in `pytest.ini`.

Acceptance mapping to requirements:

- REQ-001 -> AC-004: API validation enforced -> return 422/400 when invalid.
- REQ-002/REQ-003 -> AC-001/AC-002: Version creation and retrieval.
- REQ-004 -> AC-003/AC-005: Pre-operation backups and restore traceability.
- REQ-005 -> AC-004: Import/Export processing behavior.

### 6. Test Automation Strategy

- Test Levels:
  - Unit: Test `src/services/*` units — Prompt data operations, validation logic, version ID generation, and migration.
  - Integration: API endpoints and end-to-end flows using the FastAPI TestClient or similar.
  - End-to-End: Docker-compose integration run that exercises the REST API and static files via web UI tests if applicable.

- Frameworks:
  - Python: `pytest` and built-in fixtures.
  - Assertion: built-in `pytest` assertions with `pytest-mock` or equivalent for mocking.
  - Coverage: `pytest-cov` to enforce a minimum coverage threshold (85%).

- Test Data Management:
  - Use in-memory SQLite or an isolated test database (temporary SQLite or ephemeral PostgreSQL) for integration tests; configure via `DATABASE_URL` or test settings.
  - For legacy file-backed tests still using JSON, use temporary directories with `tmp_path` fixtures pointing to `data/` or ephemeral `data/` in CI overlays.
  - Tests must clean up local data files after execution and use isolated environment variables to avoid cross-test interference.

- CI/CD Integration:
  - Run unit and integration tests in PR gate with `pytest --maxfail=1 --disable-warnings -m "not performance"` as recommended in `README.md`.
  - Nightly or release regression should run full (`pytest`) and publish coverage HTML artifacts.

- Coverage Requirements:
  - Minimum: 85% coverage across `src/`.
  - Critical modules (PromptDataService, PromptVersioningService, BackupService) must have 90%+ coverage.

- Performance Testing:
  - Performance tests are optional in PR gating but required for nightly/regression runs.
  - Baseline: import/export/backup/time-to-save metrics described in `README.md`.

### 7. Rationale & Context

- The architecture uses a modular service layer to make each responsibility testable and swappable (the project has migrated from JSON file storage to a database-backed `PromptDataService`; the service abstraction made that migration straightforward and reversible for legacy deployments).
- All validation must be applied both in API models and within service layers to create defense-in-depth and ensure consistent behavior across programmatic and UI-driven data flows.
- The versioning approach is intentionally Git-like (immutable snapshots) to provide a robust audit trail and simplified diff/revert behavior.

### 8. Dependencies & External Integrations

### External Systems

- **EXT-001**: Browser Client — Purpose: UI access to the FastAPI backend and static assets; integration type: HTTP.

### Third-Party Services

- **SVC-001**: Optional Cloud Storage (S3 or compatible) — Purpose: Offsite backup storage if configured; SLA: eventual consistency is OK.
- **SVC-002**: Optional APM/Error Alerting (Sentry/Datadog) — Purpose: Observability and error alerting; must handle PII scrubbing and opt-out options.

### Infrastructure Dependencies

- **INF-001**: Container runtime (Docker) — Purpose: Production deployments use Docker Compose per repository; storage mount for `data/` must persist across restarts.
- **INF-002**: Volume-backed storage — Purpose: `data/` must be writeable and persistent; backup export/import and logs rely on this.

### Data Dependencies

- **DAT-001**: Database (SQLite/PostgreSQL) — The canonical persisted object store by default; previously `data/prompts_data.json` was the primary store and is kept for backward compatibility and migration. Use `DATABASE_URL` to configure the database, and the migration helper `scripts/migrate_json_to_db.py` to migrate legacy JSON data into the database when needed.

### Technology Platform Dependencies

- **PLT-001**: Python 3.8+ runtime — The app should be compatible with Python 3.8 and newer.

### Compliance Dependencies

- **COM-001**: MPL 2.0 license — The project must remain MPL 2.0-compliant. The following frontmatter license must be to each source code file in the project:

```text
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
```

### 9. Examples & Edge Cases

- Create Prompt (Valid request):

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

Expected: 201 + JSON payload with prompt ID and versions containing the initial version.

- Create Prompt (Invalid request): Tags exceed count limit (51) -> 422 with validation details.
- Import edge cases (JSON & other formats):
- A malformed CSV with missing required columns must result in 400 with a human/machine-friendly error payload.
- A `.md` file with unsupported content should be rejected and return a 400.

- Storage corruption on startup: For database-backed deployments, the application should detect DB connectivity and integrity issues and rely on pre-configured backups and migrations (Alembic + automated backup/restore tools). For environments still using legacy JSON files, the application should auto-restore a pre-existing backup if present and log the event. If no backup exists and the storage cannot be recovered, the app should reset state to empty and continue with a warning.

- Revert edge case: If reverting to a prior version that causes metadata change but no content change, the system should still create a version reflecting the revert intent and author-provided commit message.

### 10. Validation Criteria

- All functional requirements are validated by automated unit and integration tests using the `pytest` suite.
- Security: Use static analysis and tests ensuring path traversal is not possible for backup operations and file uploads.
- Observability: Structured logs exist and exports in `data/logs` and `validation_metrics.json` match the monitoring definitions.

Unit test checklist (min coverage):

- Prompt create/save/load flows.
- Migration helpers for legacy formats.
- Tag normalization and sanitization.
- Version ID generation and branch operations.
- Backup creation, restore, compression, and retention.

### 11. Related Specifications / Further Reading

- `docs/SECURITY.md` — Security policy and responsible disclosure process.
- `README.md` — Project architecture summary, roadmap, and usage.
- `ROADMAP.md` — Planned phases and feature evolution.

---

This specification is the canonical architectural reference for AI agents and humans working on PromptVault. It should be updated whenever the architecture or system constraints change and serves as the authoritative source for acceptance criteria and automated test coverage.
