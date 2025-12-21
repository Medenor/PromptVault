---
id: spec-database-migration
title: PromptVault Relational Database Migration
version: 1.0.1
date_created: 2025-11-29
last_updated: 2025-12-10
owner: medenor
tags: [database, functional, migration, storage, api]
status: published
dependencies: [spec-app]
---

## 1. Introduction

This specification defines the functional behavior and constraints of the PromptVault data layer migration from file-based JSON storage to a relational database backend. It describes WHAT the system MUST do to store, retrieve, migrate, and manage prompt data (including versions, categories, tags, and backups) while maintaining full backward compatibility with existing external interfaces.

---

## 2. Purpose, Scope, and Out-of-Scope

### 2.1 Purpose

- Define a normative, technology-agnostic data model and behavior for relational storage of prompts.
- Specify how existing JSON-based data MUST be migrated to the relational data store.
- Preserve existing externally visible behavior (API contracts, IDs, and semantics).
- Provide a basis for implementation, testing, and future extensions.

### 2.2 In Scope

- Migration of prompt data from JSON storage to a relational database.
- Functional behavior for:
  - Prompt creation, retrieval, update, and deletion.
  - Version history and versioning behavior.
  - Categories and tags management.
  - Search and filtering behavior.
  - Backup and restore at the database level.
  - Backward compatibility with existing external API contracts.
- Performance, reliability, and data consistency requirements for the data layer.
- Error-handling behavior for migration and normal operations.
- Conceptual service/API interfaces and data contracts.

### 2.3 Out of Scope

- Any change to existing external API paths, parameter names, or response shapes.
- User interface (UI) and frontend behavior.
- Authentication and authorization mechanism details.
- Full-text search and advanced ranking (beyond basic text search).
- Support for non-relational databases or additional database engines.
- Analytics, recommendations, and real-time synchronization features.

### 2.4 Assumptions

- The system operates in an environment where a relational database management system (RDBMS) is available and reliable.
- The existing JSON data source is well-formed and accessible at migration time.
- An external authentication and authorization solution exists and is applied consistently to any externally exposed endpoints.
- Time is represented in a consistent, timezone-aware format (e.g., Coordinated Universal Time) for all timestamps.
- The system runs in a trusted environment where database connectivity and storage capacity are sufficient for the specified dataset sizes.
- Existing clients depend on stable prompt identifiers and response formats.

---

## 3. Definitions & Terminology

- **Prompt**: A record representing a user-facing text snippet (and associated metadata) used as input for other systems.
- **Prompt ID**: A stable, unique numeric identifier for a Prompt.
- **Category**: A named grouping for prompts (e.g., "General", "Coding").
- **Tag**: A label attached to prompts for classification and filtering.
- **Version**: An immutable snapshot of a prompt’s state at a given time.
- **Version ID**: A unique identifier for a version snapshot.
- **JSON** (JavaScript Object Notation): A text-based data format used for representing structured data.
- **RDBMS** (Relational Database Management System): A database that stores data in relational tables with support for transactions and constraints.
- **ACID**: Atomicity, Consistency, Isolation, Durability; properties that database transactions MUST satisfy.
- **Backup**: A complete copy of the database (or relevant subset) used for recovery.
- **Restore**: The process of reconstructing the database state from a backup.
- **Soft Delete**: Marking a record as deleted without physically removing it.
- **Hard Delete**: Permanently removing a record from storage.
- **Client**: Any external system or component that interacts with the PromptVault data via defined interfaces.
- **API** (Application Programming Interface): The conceptual set of operations exposed to clients (e.g., HTTP endpoints or equivalent service methods).
- **Search Query**: A text input used to match prompts based on title and content.
- **Favorite**: A boolean attribute indicating whether a prompt is marked as preferred.

---

## 4. Functional Requirements

Normative keywords (MUST, MUST NOT, SHOULD, SHOULD NOT, MAY) follow RFC 2119.

### 4.1 Data Storage

- **REQ-DS-001**: The system **MUST** store all prompt-related data (prompts, versions, categories, tags, backups) in a relational schema with explicit primary keys and foreign keys.
- **REQ-DS-002**: The system **MUST** support at least two distinct deployment profiles (e.g., development and production) that both use a relational database backend.
- **REQ-DS-003**: The system **MUST** maintain referential integrity between prompts, versions, categories, tags, and backups.
- **REQ-DS-004**: The system **MUST** preserve all existing prompt attributes and metadata present in the JSON source, including title, content, category, tags, favorite status, and timestamps.
- **REQ-DS-005**: The system **MUST** represent each prompt version as an immutable snapshot containing all necessary data to reconstruct that version.
- **REQ-DS-006**: The system **MUST** ensure that each prompt ID is unique, stable over time, and preserved during and after migration.

### 4.2 Data Migration

- **REQ-MIG-001**: The system **MUST** provide an automated migration process that reads prompts from the JSON source and writes them into the relational database.
- **REQ-MIG-002**: The migration process **MUST** preserve all prompts, their version histories, categories, tags, favorite status, and relevant timestamps.
- **REQ-MIG-003**: The migration process **MUST** preserve existing prompt IDs from the JSON source.
- **REQ-MIG-004**: The migration process **MUST** be idempotent: re-running the migration with the same input data **MUST NOT** create duplicate logical prompts or versions.
- **REQ-MIG-005**: The migration process **MUST** provide a dry-run mode that validates the input data and reports what would change without modifying the database.
- **REQ-MIG-006**: The migration process **MUST** produce a summary report of processed records, successes, and failures.
- **REQ-MIG-007**: The migration process **MUST NOT** commit partial data when a fatal error occurs in a batch that is intended to be atomic.

### 4.3 CRUD Operations

- **REQ-CRUD-001**: The system **MUST** support creating new prompts with automatically assigned unique IDs (except for prompts created during migration, which **MUST** preserve existing IDs).
- **REQ-CRUD-002**: The system **MUST** support retrieving a prompt by Prompt ID.
- **REQ-CRUD-003**: The system **MUST** support listing prompts with pagination parameters.
- **REQ-CRUD-004**: The system **MUST** support updating prompts, automatically creating a new version snapshot for each update.
- **REQ-CRUD-005**: The system **MUST** support deleting prompts by Prompt ID.
- **REQ-CRUD-006**: The system **MUST** support bulk delete of multiple prompts in a single request and **MUST** return per-prompt success/failure statistics.
- **REQ-CRUD-007**: The system **MAY** support soft deletes, but soft delete semantics **MUST** be consistent across the system if enabled.
- **REQ-CRUD-008**: The system **MUST** ensure that updates and deletes apply only to existing prompts; operations on non-existing IDs **MUST** result in a defined error.

### 4.4 Search and Filtering

- **REQ-SRCH-001**: The system **MUST** support text search across prompt title and prompt content.
- **REQ-SRCH-002**: The system **MUST** support filtering prompts by category.
- **REQ-SRCH-003**: The system **MUST** support filtering prompts by tags, with the ability to express logical AND (prompts having all specified tags) and logical OR (prompts having any specified tag).
- **REQ-SRCH-004**: The system **MUST** support filtering by favorite status.
- **REQ-SRCH-005**: The system **MUST** support combined search and filter criteria (e.g., text search + category + tags + favorite).
- **REQ-SRCH-006**: The system **MUST** support pagination (offset/limit or equivalent) for search results.
- **REQ-SRCH-007**: The system **SHOULD** perform searches in a case-insensitive manner for text-based criteria.

### 4.5 Version Control

- **REQ-VERS-001**: The system **MUST** automatically create an initial version when a new prompt is created.
- **REQ-VERS-002**: The system **MUST** automatically create a new version snapshot whenever a prompt is updated.
- **REQ-VERS-003**: Each version **MUST** store sufficient data (title, content, category reference, tags, favorite status, and relevant metadata) to reconstruct the prompt state at that version.
- **REQ-VERS-004**: The system **MUST** store version metadata, including at least: creation timestamp and an optional author identifier and message.
- **REQ-VERS-005**: The system **MUST** support retrieval of version history for a given prompt, ordered from newest to oldest.
- **REQ-VERS-006**: The system **MUST** represent parent-child relationships between versions (e.g., version chains).
- **REQ-VERS-007**: The system **MUST NOT** allow modification of an existing version snapshot (versions are immutable).
- **REQ-VERS-008**: The system **MAY** support reverting a prompt to a previous version by creating a new version that copies the reverted state.

### 4.6 Categories and Tags

- **REQ-CT-001**: The system **MUST** implement a get-or-create behavior for categories when assigning a category by name to a prompt.
- **REQ-CT-002**: The system **MUST** implement a get-or-create behavior for tags when assigning tag names to a prompt.
- **REQ-CT-003**: The system **MUST** support renaming categories and tags.
- **REQ-CT-004**: The system **MUST** support merging duplicate tags, consolidating associations onto a single canonical tag.
- **REQ-CT-005**: The system **MUST** track usage counts for categories and tags.
- **REQ-CT-006**: The system **MUST** provide a way to list all category names.
- **REQ-CT-007**: The system **MUST** provide a way to list all tag names, and **MAY** provide counts alongside the names.

### 4.7 Backup and Restore

- **REQ-BKP-001**: The system **MUST** support full database backups at the logical level (e.g., schema and data).
- **REQ-BKP-002**: The system **MUST** record backup metadata, including at least: backup identifier, type, creation timestamp, size (if known), and optional descriptive metadata.
- **REQ-BKP-003**: The system **MUST** support a restore operation that can restore the database from a selected backup.
- **REQ-BKP-004**: Before performing any destructive restore, the system **SHOULD** create a pre-restore backup of the current state.
- **REQ-BKP-005**: The system **MUST** support listing available backups and their metadata.
- **REQ-BKP-006**: The system **MUST** support a retention policy for backups (e.g., maximum count or age) and **MUST** enforce this policy deterministically.
- **REQ-BKP-007**: The system **MAY** support compression for backups, but if enabled, backup and restore operations **MUST** remain logically lossless.

### 4.8 Backward Compatibility

- **REQ-BC-001**: The system **MUST** maintain existing external API response formats (field names, types, and overall structure) for all existing endpoints.
- **REQ-BC-002**: The system **MUST NOT** change existing API paths or HTTP methods (or equivalent external invocation semantics).
- **REQ-BC-003**: The system **MUST** provide a dictionary-like interface or equivalent abstraction to allow legacy code to access prompts as key/value data.
- **REQ-BC-004**: The system **MUST** preserve the existing prompt ID sequence for prompts that pre-exist the migration.
- **REQ-BC-005**: Deprecated methods that are effectively no-ops **MUST** continue to behave as before (e.g., return a success indicator) but **SHOULD** emit a deprecation signal (e.g., log message) for observability.

### 4.9 Security Requirements

- **SEC-001**: The system **MUST** ensure that only authorized clients can access prompt data, consistent with the broader platform’s authentication and authorization policies.
- **SEC-002**: The system **MUST NOT** expose internal database identifiers or structural details beyond what is required by the public data contract.
- **SEC-003**: The system **MUST NOT** log full prompt content or sensitive fields in plaintext in error logs, except in explicitly configured debugging modes.
- **SEC-004**: Backup files **MUST** be protected by the same or stronger access controls as the primary database.

### 4.10 Non-Functional Requirements

- **NFR-001**: Loading all prompts (up to 10,000 prompts) via the standard listing interface **MUST** complete in less than 1 second under nominal conditions.
- **NFR-002**: Search operations across up to 10,000 prompts **MUST** complete in less than 500 milliseconds under nominal conditions.
- **NFR-003**: Single prompt create, read, update, and delete operations **MUST** complete in less than 100 milliseconds under nominal conditions.
- **NFR-004**: The system **MUST** use ACID transactions for all operations that modify the database.
- **NFR-005**: The system **MUST** support at least 20 concurrent logical client operations without degradation below the above latencies under nominal conditions.
- **NFR-006**: The system **SHOULD** be able to handle datasets of at least 10,000 prompts, each with multiple versions and tags, without violating the above performance constraints.
- **NFR-007**: The system **MUST** provide observability signals (e.g., logs, metrics) sufficient to diagnose failures in migration, backup, and critical CRUD operations.

### 4.11 Error-Handling Requirements

- **ERR-001**: If the migration encounters malformed JSON or invalid data for a given prompt, the system **MUST** log the error, skip the invalid record, and continue processing other records, unless configured to fail-fast.
- **ERR-002**: If a duplicate Prompt ID is encountered during migration, the system **MUST** treat it as a conflict and **MUST NOT** create a second prompt with the same ID.
- **ERR-003**: In case of a database error during a transactional operation, the system **MUST** roll back all changes in that transaction and return a failure status.
- **ERR-004**: Operations on non-existent Prompt IDs **MUST** return a standardized “not found” error.
- **ERR-005**: Requests with invalid input payloads (e.g., missing required fields, invalid types) **MUST** result in a standardized “validation error” response.
- **ERR-006**: If a restore operation fails, the system **MUST** report the failure and **MUST** leave the database in a consistent state (either fully restored to the selected backup or left unchanged).

### 4.12 Guidelines

- **GUD-001**: The system **SHOULD** minimize the number of database round-trips required for common operations (e.g., use set-based operations where possible).
- **GUD-002**: The system **SHOULD** structure queries to leverage indexes on frequently filtered fields (title, category, tags, favorite, timestamps).
- **GUD-003**: The system **SHOULD** avoid long-running transactions for bulk operations by batching where appropriate.
- **GUD-004**: The system **MAY** expose additional read-only statistics (e.g., total prompt count, per-category counts) as separate operations if needed for observability or UI.

---

## 5. Invariants

- **INV-001**: A Prompt ID **MUST** uniquely identify a single prompt at any point in time.
- **INV-002**: A prompt that has been deleted (hard or soft) **MUST NOT** appear in any standard listing or search results that are intended to show active prompts.
- **INV-003**: Once created, a version record **MUST NOT** be modified or deleted, except as part of a full prompt deletion that explicitly removes all versions.
- **INV-004**: Every version **MUST** be associated with exactly one prompt.
- **INV-005**: Each prompt’s current state **MUST** correspond to the most recent version in its version history.
- **INV-006**: Tag and category names **MUST** be unique within their respective namespaces.
- **INV-007**: The combination of prompt ID and version number **MUST** be unique.
- **INV-008**: For any category or tag with a usage count greater than zero, at least one prompt **MUST** reference it.
- **INV-009**: Backup metadata **MUST** accurately describe the associated backup artifact (identifier, creation time, and type).
- **INV-010**: Migration **MUST NOT** alter the externally observable semantics of existing endpoints (input parameters, output fields, and error semantics).

---

## 6. Interfaces & Data Contracts

All schemas are expressed in JSON-like pseudo-notation and are conceptual. They do not mandate any specific transport (e.g., HTTP) or framework.

### 6.1 Core Prompt Data Schema

#### 6.1.1 Prompt Resource

```json
{
  "id": 123,
  "title": "Example prompt",
  "content": "Prompt text",
  "category": "General",
  "tags": ["tag1", "tag2"],
  "favorite": false,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-02T13:00:00Z"
}
```

#### 6.1.2 Version Resource

```json
{
  "version_id": "string-unique-id",
  "prompt_id": 123,
  "version_number": 1,
  "author": "user-identifier",
  "message": "Initial version",
  "created_at": "2025-01-01T12:00:00Z",
  "snapshot": {
    "title": "Example prompt",
    "content": "Prompt text",
    "category": "General",
    "tags": ["tag1", "tag2"],
    "favorite": false
  },
  "parent_version_id": null
}
```

#### 6.1.3 Backup Resource

```json
{
  "backup_id": "string-unique-id",
  "backup_type": "full",
  "description": "optional description",
  "filename": "logical or physical name",
  "size_bytes": 123456,
  "created_at": "2025-01-03T10:00:00Z",
  "metadata": {
    "schema_version": "1.0.0"
  }
}
```

### 6.2 Logical API Operations

The following tables define conceptual operations. They may map to HTTP endpoints or equivalent service methods.

#### Operation: Create Prompt

| Field         | Description                                                 |
| ------------- | ----------------------------------------------------------- |
| Name          | `CreatePrompt`                                              |
| Auth Required | YES (authenticated client)                                  |
| Inputs        | `title`, `content`, optional `category`, `tags`, `favorite` |
| Output        | Created Prompt resource                                     |
| Errors        | Validation error, unauthorized, internal error              |

**Input Fields**

| Name     | Type     | Required | Description                                           |
| -------- | -------- | -------- | ----------------------------------------------------- |
| title    | string   | yes      | Prompt title, max length defined by system constraint |
| content  | string   | yes      | Prompt body                                           |
| category | string   | no       | Category name; get-or-create                          |
| tags     | string[] | no       | Tag names; get-or-create                              |
| favorite | boolean  | no       | Default `false` if omitted                            |

**Output Schema**

- Prompt resource (see 6.1.1).

**Error Conditions**

| Code | Condition                 | Description                                       |
| ---- | ------------------------- | ------------------------------------------------- |
| 400  | Invalid or missing fields | Violates **ERR-005**                              |
| 401  | Unauthenticated           | Violates **SEC-001**                              |
| 500  | Storage failure           | Violates **ERR-003** if transaction cannot commit |

#### Operation: Get Prompt

| Field         | Description                             |
| ------------- | --------------------------------------- |
| Name          | `GetPrompt`                             |
| Auth Required | YES                                     |
| Inputs        | `id` (Prompt ID)                        |
| Output        | Prompt resource                         |
| Errors        | Not found, unauthorized, internal error |

**Error Conditions**

| Code | Condition        | Description |
| ---- | ---------------- | ----------- |
| 404  | Prompt not found | **ERR-004** |
| 401  | Unauthenticated  | **SEC-001** |
| 500  | Storage failure  | **ERR-003** |

#### Operation: List/Search Prompts

| Field         | Description                                                  |
| ------------- | ------------------------------------------------------------ |
| Name          | `SearchPrompts`                                              |
| Auth Required | YES                                                          |
| Inputs        | `query`, `category`, `tags[]`, `favorite`, `offset`, `limit` |
| Output        | List of Prompt resources + paging metadata                   |
| Errors        | Validation error, unauthorized, internal error               |

**Input Fields**

| Name     | Type     | Required | Description                                |
| -------- | -------- | -------- | ------------------------------------------ |
| query    | string   | no       | Text search string                         |
| category | string   | no       | Category filter                            |
| tags     | string[] | no       | Tag filters (MAY support AND/OR semantics) |
| favorite | boolean  | no       | Favorite-only filter                       |
| offset   | integer  | no       | Pagination offset (default 0)              |
| limit    | integer  | no       | Page size (system-defined maximum)         |

**Output Schema**

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}
```

#### Operation: Update Prompt

| Field         | Description                                 |
| ------------- | ------------------------------------------- |
| Name          | `UpdatePrompt`                              |
| Auth Required | YES                                         |
| Inputs        | `id`, fields identical to CreatePrompt      |
| Output        | Updated Prompt resource                     |
| Errors        | Not found, validation error, internal error |

On success, a new version **MUST** be created (REQ-VERS-002).

#### Operation: Delete Prompt

| Field         | Description                             |
| ------------- | --------------------------------------- |
| Name          | `DeletePrompt`                          |
| Auth Required | YES                                     |
| Inputs        | `id`                                    |
| Output        | Operation result + statistics (if bulk) |
| Errors        | Not found, internal error               |

#### Operation: Get Prompt Versions

| Field         | Description               |
| ------------- | ------------------------- |
| Name          | `GetPromptVersions`       |
| Auth Required | YES                       |
| Inputs        | `prompt_id`               |
| Output        | List of Version resources |
| Errors        | Not found, internal error |

#### Operation: List Categories

| Field         | Description                   |
| ------------- | ----------------------------- |
| Name          | `ListCategories`              |
| Auth Required | YES                           |
| Inputs        | none                          |
| Output        | List of category names/counts |

#### Operation: List Tags

| Field         | Description              |
| ------------- | ------------------------ |
| Name          | `ListTags`               |
| Auth Required | YES                      |
| Inputs        | none                     |
| Output        | List of tag names/counts |

#### Operation: Create Backup

| Field         | Description                         |
| ------------- | ----------------------------------- |
| Name          | `CreateBackup`                      |
| Auth Required | YES (privileged role)               |
| Inputs        | `backup_type`, optional description |
| Output        | Backup resource                     |

#### Operation: List Backups

| Field         | Description              |
| ------------- | ------------------------ |
| Name          | `ListBackups`            |
| Auth Required | YES (privileged role)    |
| Inputs        | none                     |
| Output        | List of Backup resources |

#### Operation: Restore From Backup

| Field         | Description                                 |
| ------------- | ------------------------------------------- |
| Name          | `RestoreFromBackup`                         |
| Auth Required | YES (privileged role)                       |
| Inputs        | `backup_id`                                 |
| Output        | Operation result                            |
| Errors        | Not found, validation error, internal error |

---

## 7. Acceptance Criteria

Each acceptance criterion references one or more requirements.

- **AC-001 (Migration Completeness)**:  
  Given a valid JSON source with N prompts and associated metadata,  
  When the migration (REQ-MIG-001–REQ-MIG-006) is executed in normal mode,  
  Then exactly N prompts with corresponding versions, categories, tags, and preserved IDs (REQ-DS-006, REQ-MIG-002, REQ-MIG-003) MUST exist in the database and all invariants in section 5 MUST hold.

- **AC-002 (Migration Idempotence)**:  
  Given the same JSON source and an already migrated database,  
  When the migration is re-run in idempotent mode,  
  Then no duplicate prompts, versions, categories, or tags MUST be created (REQ-MIG-004).

- **AC-003 (Migration Dry-Run)**:  
  Given a valid JSON source,  
  When the migration is executed in dry-run mode,  
  Then no database changes MUST occur, and a report of intended changes MUST be generated (REQ-MIG-005).

- **AC-004 (Create Prompt)**:  
  Given a valid create request,  
  When `CreatePrompt` is invoked,  
  Then a new prompt with a unique ID MUST be created and returned, an initial version MUST exist (REQ-CRUD-001, REQ-VERS-001), and the response MUST conform to the Prompt schema in 6.1.1 (REQ-BC-001).

- **AC-005 (Get Prompt Not Found)**:  
  Given a non-existent Prompt ID,  
  When `GetPrompt` is invoked,  
  Then a standardized “not found” error MUST be returned (ERR-004).

- **AC-006 (Search Behavior)**:  
  Given prompts with distinct titles, categories, tags, and favorite flags,  
  When `SearchPrompts` is invoked with combinations of query, category, tags, and favorite filters,  
  Then only prompts satisfying all specified filters MUST be returned (REQ-SRCH-001–REQ-SRCH-006).

- **AC-007 (Version Creation on Update)**:  
  Given an existing prompt,  
  When `UpdatePrompt` modifies any persisted field,  
  Then a new version MUST be created and associated with that prompt (REQ-VERS-002, REQ-VERS-003).

- **AC-008 (Version Immutability)**:  
  Given an existing version,  
  When an attempt is made to modify that version directly,  
  Then the system MUST reject the modification and leave the version unchanged (REQ-VERS-007, INV-003).

- **AC-009 (Category and Tag Get-or-Create)**:  
  Given a create or update operation with a new category or tags,  
  When the operation completes successfully,  
  Then the new category/tag MUST exist and be associated with the prompt, and usage counts MUST be updated (REQ-CT-001–REQ-CT-005).

- **AC-010 (Backup Creation and Listing)**:  
  Given an operational database,  
  When `CreateBackup` is invoked,  
  Then a backup MUST be created, metadata MUST be recorded (REQ-BKP-001–REQ-BKP-003), and the backup MUST appear in `ListBackups` with correct metadata (INV-009).

- **AC-011 (Restore With Pre-Backup)**:  
  Given at least one backup and a configured pre-restore policy,  
  When `RestoreFromBackup` is invoked,  
  Then a new backup MUST be created before the restore (REQ-BKP-004), and after a successful restore, all invariants MUST still hold.

- **AC-012 (Backward Compatibility)**:  
  Given an existing external client request used prior to migration,  
  When the same request is made after migration,  
  Then the response body, status code, and error behavior MUST remain identical in structure and semantics (REQ-BC-001, REQ-BC-002, INV-010).

- **AC-013 (Performance)**:  
  Given a dataset of at least 10,000 prompts under nominal system load,  
  When listing all prompts, performing search operations, or single CRUD operations,  
  Then observed latencies MUST satisfy NFR-001–NFR-003.

- **AC-014 (Error Handling and Transactions)**:  
  Given an operation that causes a database error (e.g., constraint violation),  
  When the operation is executed,  
  Then all changes in that transaction MUST be rolled back, and a standardized error MUST be returned (ERR-003, NFR-004).

- **AC-015 (Security)**:  
  Given an unauthenticated or unauthorized request,  
  When any protected operation is invoked,  
  Then the system MUST deny access and MUST NOT leak any prompt data (SEC-001, SEC-002).

---

## 8. Test Requirements (NOT test implementation)

- **TEST-REQ-001**: All migration scenarios, including success, dry-run, idempotence, invalid data, and duplicate IDs, **MUST** be validated (REQ-MIG-001–REQ-MIG-007, ERR-001–ERR-003).
- **TEST-REQ-002**: All CRUD operations **MUST** be tested for normal behavior, invalid input, and boundary conditions (REQ-CRUD-001–REQ-CRUD-008, ERR-004–ERR-005).
- **TEST-REQ-003**: Search and filtering behavior **MUST** be validated for:
  - Single and combined filters.
  - Case sensitivity behavior.
  - Pagination correctness (REQ-SRCH-001–REQ-SRCH-007).
- **TEST-REQ-004**: Versioning behavior **MUST** be tested, including automatic version creation, immutability, ordering, and optional revert (REQ-VERS-001–REQ-VERS-008, INV-003–INV-005).
- **TEST-REQ-005**: Category and tag operations (get-or-create, rename, merge, usage counts) **MUST** be tested (REQ-CT-001–REQ-CT-007, INV-006–INV-008).
- **TEST-REQ-006**: Backup and restore operations, including pre-restore backup and retention policies, **MUST** be tested (REQ-BKP-001–REQ-BKP-007, INV-009).
- **TEST-REQ-007**: Backward compatibility **MUST** be validated by comparing pre- and post-migration responses for all existing endpoints (REQ-BC-001–REQ-BC-005, INV-010).
- **TEST-REQ-008**: Non-functional performance requirements (NFR-001–NFR-007) **MUST** be verified using appropriate load scenarios.
- **TEST-REQ-009**: All invariants in section 5 **MUST** have explicit tests that attempt to violate them.

---

## 9. Dependencies (Conceptual Only)

- **EXT-001**: The system requires a relational database engine that supports ACID transactions and foreign key constraints.
- **EXT-002**: The system requires an authentication and authorization provider to enforce access control for all protected operations.
- **EXT-003**: The system requires a logging and metrics facility to record migration, backup/restore, and critical operational events.
- **SVC-001**: The system depends on an external API or service layer that exposes the logical operations defined in section 6 to clients.
- **SVC-002**: The system MAY depend on a configuration mechanism to define database connection parameters, performance thresholds, and retention policies.

---

## 10. Examples & Edge Cases

- **Example 1 (Duplicate Tags)**:  
  Given multiple prompts referencing tag names `"AI"` and `"ai"`,  
  When tags are normalized according to a chosen naming rule,  
  Then tag merging MUST preserve all prompt associations and usage counts (REQ-CT-004, INV-006, INV-008).

- **Example 2 (Invalid JSON Record)**:  
  Given a JSON file where one prompt record is missing required fields,  
  When migration is executed,  
  Then that record MUST be skipped with a logged validation error (ERR-001), and other valid records MUST still be migrated (REQ-MIG-001, REQ-MIG-006).

- **Example 3 (Large Dataset)**:  
  Given 10,000 prompts, each with multiple versions and tags,  
  When performing full listing and search operations,  
  Then the system MUST satisfy performance NFR-001–NFR-003 while maintaining all invariants.

- **Example 4 (Restore Failure)**:  
  Given a corrupted backup artifact,  
  When `RestoreFromBackup` is invoked with that backup,  
  Then the system MUST detect the failure, MUST NOT partially apply the restore, and MUST leave the database in a consistent pre-restore state (ERR-006).

- **Example 5 (Soft vs Hard Delete)**:  
  If soft delete is enabled,  
  Then soft-deleted prompts MUST be excluded from normal listings and searches but MAY be retrievable by administrative operations, and the choice between soft/hard delete MUST be consistent across the system (REQ-CRUD-007, INV-002).

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

---

## 12. Related Specifications / References

- [SPEC_AUTHENTICATION](SPEC_AUTHENTICATION.md) — Authentication & authorization spec (login, sessions, RBAC).
- [SPEC_DATABASE](SPEC_DATABASE.md) — Database schema and persistence behavior specification.
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
