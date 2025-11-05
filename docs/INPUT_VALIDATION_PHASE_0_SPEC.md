# Input Validation & Sanitization Framework - Phase 0 Specification

**Issue**: [#9 Input Validation & Sanitization Framework](https://codeberg.org/medenor/promptvault/issues/9)
**Phase**: Phase 0 - Discovery & Planning
**Date**: 2025-11-05
**Status**: Complete

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Endpoint Inventory](#endpoint-inventory)
3. [Current Validation State](#current-validation-state)
4. [Service Layer Analysis](#service-layer-analysis)
5. [Field Constraints & Validation Rules](#field-constraints--validation-rules)
6. [Security Vulnerabilities & Risks](#security-vulnerabilities--risks)
7. [Recommended Implementation Approach](#recommended-implementation-approach)
8. [Success Criteria](#success-criteria)

---

## Executive Summary

This document provides a comprehensive analysis of input validation and sanitization requirements for PromptVault. The current implementation has **minimal input validation**, relying primarily on basic type coercion and optional field handling. Critical security vulnerabilities have been identified including:

- **Path traversal risks** in file upload/export operations (lines 346, 390 in app.py)
- **No length constraints** on text fields (title, prompt, category, tags)
- **Insufficient character set validation** across all user inputs
- **Missing sanitization** for special characters that could enable injection attacks
- **No file type validation** beyond filename extension checks
- **Weak backup name sanitization** (basic regex, no length enforcement in validation layer)

**Estimated Impact**: High priority - affects all user-facing endpoints and data persistence layers.

---

## Endpoint Inventory

### 1. Prompt Management Endpoints

#### POST /api/prompts
**Purpose**: Create a new prompt
**Input Parameters**:
- `title` (Form, required): Prompt title
- `prompt` (Form, required): Prompt content
- `category` (Form, optional, default=""): Category name
- `tags` (Form, optional, default=""): Comma-separated tags

**Current Validation**: None - accepts any string values
**Handler**: `create_prompt()` at app.py:85-102

---

#### PUT /api/prompts/{prompt_id}
**Purpose**: Update an existing prompt
**Input Parameters**:
- `prompt_id` (Path, required): Integer prompt ID
- `title` (Form, required): Prompt title
- `prompt` (Form, required): Prompt content
- `category` (Form, optional, default=""): Category name
- `tags` (Form, optional, default=""): Comma-separated tags
- `commit_message` (Form, optional, default="Update"): Version commit message

**Current Validation**:
- Path parameter: Basic `int()` conversion with try/except (lines 198-200)
- Form fields: None

**Handler**: `update_prompt()` at app.py:187-221

---

#### DELETE /api/prompts/{prompt_id}
**Purpose**: Delete a prompt
**Input Parameters**:
- `prompt_id` (Path, required): Integer prompt ID

**Current Validation**:
- Path parameter: Basic `int()` conversion with try/except (lines 227-229)

**Handler**: `delete_prompt()` at app.py:223-242

---

#### PUT /api/prompts/{prompt_id}/favorite
**Purpose**: Toggle favorite status
**Input Parameters**:
- `prompt_id` (Path, required): Integer prompt ID

**Current Validation**:
- Path parameter: Basic `int()` conversion with try/except (lines 248-250)

**Handler**: `toggle_favorite()` at app.py:244-270

---

#### GET /api/prompts/search
**Purpose**: Search and filter prompts
**Input Parameters**:
- `search` (Query, optional, default=""): Search term
- `category` (Query, optional, default=""): Category filter
- `tag` (Query, optional, default=""): Tag filter
- `favorites` (Query, optional, default=False): Boolean filter
- `case_sensitive` (Query, optional, default=False): Boolean flag

**Current Validation**: None - accepts any query string values
**Handler**: `search_prompts()` at app.py:105-164

---

### 2. Import/Export Endpoints

#### POST /api/export
**Purpose**: Export prompts in specified format
**Input Parameters**:
- `format` (Form, required): Export format ("csv", "markdown", "json")
- `filename` (Form, optional, default="promptvault_export"): Export filename
- `include_favorites` (Form, optional, default=False): Boolean filter
- `include_metadata` (Form, optional, default=True): Boolean flag

**Current Validation**:
- Format: Lowercase comparison only (line 349-352)
- **Filename: NO PATH TRAVERSAL VALIDATION** - Potential vulnerability at line 346

**Security Risk**: 🔴 **HIGH** - Path traversal vulnerability
**Handler**: `export_prompts()` at app.py:319-379

---

#### POST /api/import
**Purpose**: Import prompts from uploaded file
**Input Parameters**:
- `file` (UploadFile, required): File upload
- `mode` (Form, optional, default="append"): Import mode ("append", "merge", "replace")
- `validate_data` (Form, optional, default=True): Boolean validation flag

**Current Validation**:
- File extension: Basic endswith() checks (lines 399-421)
- **Filename: NO PATH TRAVERSAL VALIDATION** - Potential vulnerability at line 390
- Data validation: Optional basic checks (title and prompt existence, lines 424-429)

**Security Risk**: 🔴 **HIGH** - Path traversal vulnerability, insufficient file type validation
**Handler**: `import_prompts()` at app.py:381-485

---

### 3. Backup Management Endpoints

#### POST /api/backups
**Purpose**: Create a manual backup
**Input Parameters**:
- `name` (Form, optional): Custom backup name

**Current Validation**:
- Backup name: Regex-based sanitization in service layer (backup_service.py:392-397)
  - Pattern: `r"[^A-Za-z0-9_-]+"`
  - Max length: 64 characters (truncation)
  - **No validation at API layer**

**Handler**: `create_manual_backup()` at app.py:556-566

---

#### POST /api/backups/{backup_id}/restore
**Purpose**: Restore from a specific backup
**Input Parameters**:
- `backup_id` (Path, required): Backup identifier

**Current Validation**: None at API layer - relies on service layer path resolution
**Handler**: `restore_backup()` at app.py:568-578

---

#### DELETE /api/backups/{backup_id}
**Purpose**: Delete a specific backup
**Input Parameters**:
- `backup_id` (Path, required): Backup identifier

**Current Validation**: None at API layer
**Handler**: `delete_backup()` at app.py:580-599

---

#### POST /api/backups/cleanup
**Purpose**: Clean up old backups
**Input Parameters**:
- `retention_days` (Form, optional, default=30): Days to retain

**Current Validation**: None - accepts any integer
**Handler**: `cleanup_backups()` at app.py:601-606

---

#### POST /api/backups/compress
**Purpose**: Compress old backups
**Input Parameters**:
- `days_threshold` (Form, optional, default=7): Days threshold

**Current Validation**: None - accepts any integer
**Handler**: `compress_backups()` at app.py:608-613

---

### 4. Version Control Endpoints

#### GET /api/prompts/{prompt_id}/versions/compare
**Purpose**: Compare two versions
**Input Parameters**:
- `prompt_id` (Path, required): Integer prompt ID
- `v1` (Query, required): Version ID (UUID string)
- `v2` (Query, required): Version ID (UUID string)

**Current Validation**:
- Prompt ID: Basic int conversion (lines 662-664)
- Version IDs: None - no UUID format validation

**Handler**: `compare_versions()` at app.py:658-707

---

#### POST /api/prompts/{prompt_id}/versions/{version_id}/revert
**Purpose**: Revert to a specific version
**Input Parameters**:
- `prompt_id` (Path, required): Integer prompt ID
- `version_id` (Path, required): Version ID (UUID string)
- `commit_message` (Form, optional, default="Revert to previous version"): Commit message

**Current Validation**:
- Prompt ID: Basic int conversion (lines 739-741)
- Version ID: None - no UUID format validation
- Commit message: None

**Handler**: `revert_to_version()` at app.py:731-782

---

## Current Validation State

### API Layer (src/web/app.py)

**Validation Present**:
1. ✅ Basic integer conversion for path parameters with try/except
2. ✅ File extension checks for import/export (endswith() method)
3. ✅ Optional data validation in import (title/prompt existence check)
4. ✅ Helper function `_parse_tags_field()` for tag normalization (lines 32-49)

**Validation Missing**:
1. ❌ Length constraints on all text fields
2. ❌ Character set validation
3. ❌ Path traversal protection for filenames
4. ❌ File size limits for uploads
5. ❌ MIME type validation for uploads
6. ❌ UUID format validation for version IDs
7. ❌ Enum validation for mode/format parameters
8. ❌ Range validation for numeric parameters
9. ❌ Cross-field validation
10. ❌ Request rate limiting

---

### Service Layer Analysis

#### PromptDataService (src/services/prompt_data_service.py)

**Validation Present**:
1. ✅ Tag normalization (`_normalize_tags()`, lines 32-49)
   - Strips whitespace
   - Filters empty strings
   - Ensures list type
2. ✅ Prompt payload normalization (`_normalize_prompt_payload()`, lines 51-68)
   - Validates dict type
   - Normalizes tags array
3. ✅ Category normalization (`_update_categories_and_tags()`, lines 361-366)
   - Trims whitespace
   - Defaults to "No category"
4. ✅ Type checking for tags (isinstance checks)

**Validation Missing**:
1. ❌ Length limits on title, prompt, category, tags
2. ❌ Character set restrictions
3. ❌ XSS/injection prevention
4. ❌ Maximum tag count
5. ❌ Maximum category length
6. ❌ Duplicate tag prevention

---

#### BackupService (src/services/backup_service.py)

**Validation Present**:
1. ✅ Backup name sanitization (`_sanitize_backup_name()`, lines 392-397)
   - Regex pattern: `[^A-Za-z0-9_-]+` replaced with `_`
   - 64-character truncation
2. ✅ Backup file validation (`_is_valid_backup_file()`)
3. ✅ Path resolution with safety checks (`_resolve_backup_path()`)

**Validation Missing**:
1. ❌ Input validation before sanitization (no length check before truncation)
2. ❌ Retention days range validation
3. ❌ Compression threshold range validation
4. ❌ Backup ID format validation

---

#### PromptImportExportService (src/services/prompt_import_export_service.py)

**Validation**: Not inspected in detail during Phase 0 - requires Phase 1 analysis

**Known Issues**:
- File parsing without strict schema validation
- CSV/Markdown parsing may accept malformed data

---

## Field Constraints & Validation Rules

### Proposed Constraints

#### Prompt Fields

| Field | Type | Min Length | Max Length | Required | Pattern/Rules |
|-------|------|------------|------------|----------|---------------|
| `title` | string | 1 | 200 | Yes | No leading/trailing whitespace |
| `prompt` | string | 1 | 50,000 | Yes | No restrictions (allows code, markdown) |
| `category` | string | 0 | 100 | No | Alphanumeric + spaces, trim whitespace |
| `tags` | array[string] | 0 items | 50 items | No | Each tag: 1-50 chars, alphanumeric + spaces/hyphens |
| `note` | string | 0 | 10,000 | No | No restrictions |
| `favorite` | boolean | - | - | No | true/false only |
| `commit_message` | string | 1 | 500 | No | Default: "Update" |

#### Import/Export Fields

| Field | Type | Allowed Values | Max Length | Pattern/Rules |
|-------|------|----------------|------------|---------------|
| `format` | string | csv, markdown, json | - | Enum validation |
| `filename` | string | - | 255 | Filename-safe chars only, no path separators |
| `mode` | string | append, merge, replace | - | Enum validation |
| `validate_data` | boolean | true, false | - | Boolean only |

#### Backup Fields

| Field | Type | Min | Max | Default | Rules |
|-------|------|-----|-----|---------|-------|
| `name` | string | 0 | 64 | - | [A-Za-z0-9_-] only |
| `retention_days` | integer | 1 | 3650 | 30 | Positive integer (1-10 years) |
| `days_threshold` | integer | 1 | 365 | 7 | Positive integer (1-1 year) |

#### Version Control Fields

| Field | Type | Format | Rules |
|-------|------|--------|-------|
| `version_id` | string | UUID v4 | RFC 4122 compliant |
| `prompt_id` | integer | - | Positive integer, exists in database |

---

## Security Vulnerabilities & Risks

### 🔴 Critical Vulnerabilities

#### 1. Path Traversal in File Operations
**Location**: app.py:346, 390
**Risk Level**: Critical
**Description**: User-controlled filenames used directly in file system operations

```python
# app.py:390 - VULNERABLE
temp_file = f"/tmp/{file.filename}"
```

**Attack Vector**:
```
filename = "../../etc/passwd"
# Results in: /tmp/../../etc/passwd = /etc/passwd
```

**Remediation**:
- Use `os.path.basename()` to strip directory components
- Validate against allowlist of characters
- Use secure temporary file creation (tempfile module)

---

#### 2. No File Size Limits
**Location**: app.py:381-485 (import endpoint)
**Risk Level**: High
**Description**: No maximum file size enforcement allows DoS via resource exhaustion

**Attack Vector**:
```
Upload 10GB JSON file → Server runs out of memory
```

**Remediation**:
- Implement FastAPI `File(...)` max_size parameter
- Add streaming validation for large files
- Set reasonable limits (e.g., 10MB for JSON/CSV)

---

#### 3. Insufficient MIME Type Validation
**Location**: app.py:399-421
**Risk Level**: High
**Description**: Relies only on file extension, not actual file content

**Attack Vector**:
```
malicious.exe renamed to malicious.csv → uploaded and processed
```

**Remediation**:
- Validate MIME type from file headers
- Use python-magic or similar library
- Reject files with mismatched extension/MIME type

---

### 🟡 High Priority Issues

#### 4. No Length Constraints on Text Fields
**Location**: All prompt creation/update endpoints
**Risk Level**: Medium-High
**Description**: Can store arbitrarily large strings leading to DoS

**Impact**:
- Database bloat
- Memory exhaustion during load
- Performance degradation
- Backup file size explosion

**Remediation**: Enforce field length limits via Pydantic models

---

#### 5. Missing Character Set Validation
**Location**: All text input endpoints
**Risk Level**: Medium
**Description**: No sanitization against special characters or control characters

**Potential Issues**:
- Log injection via control characters
- Display issues with unusual Unicode
- Data corruption with invalid UTF-8 sequences

**Remediation**:
- Strip/reject control characters (except \n, \r, \t)
- Validate UTF-8 encoding
- Sanitize for JSON storage

---

#### 6. No Rate Limiting
**Location**: All API endpoints
**Risk Level**: Medium
**Description**: No protection against brute force or DoS attacks

**Remediation**: Implement FastAPI rate limiting middleware

---

### 🟢 Medium Priority Issues

#### 7. Weak Backup Name Sanitization
**Location**: backup_service.py:392-397
**Risk Level**: Low-Medium
**Description**: Sanitization happens in service layer, not at API validation

**Issue**: Invalid input silently transformed, no user feedback

**Remediation**: Validate at API layer, reject invalid input with error message

---

#### 8. No UUID Format Validation
**Location**: Version control endpoints
**Risk Level**: Low
**Description**: Version IDs accepted as strings without UUID format validation

**Remediation**: Use Pydantic UUID type validation

---

#### 9. Missing Cross-Field Validation
**Location**: All endpoints
**Risk Level**: Low
**Description**: No validation of field relationships

**Examples**:
- If `include_favorites=true`, ensure favorites exist
- If `mode=merge`, validate merge criteria

**Remediation**: Implement Pydantic model validators

---

## Recommended Implementation Approach

### Phase 1: API Layer Validation

#### Step 1.1: Define Pydantic Request Models

Create `src/web/models/validation.py`:

```python
from pydantic import BaseModel, Field, validator, constr
from typing import List, Optional
from enum import Enum

class PromptCreateRequest(BaseModel):
    title: constr(min_length=1, max_length=200, strip_whitespace=True)
    prompt: constr(min_length=1, max_length=50000)
    category: Optional[constr(max_length=100, strip_whitespace=True)] = ""
    tags: Optional[str] = ""  # Will be parsed separately

    @validator('tags')
    def validate_tags(cls, v):
        if not v:
            return []
        tags = [t.strip() for t in v.split(',')]
        if len(tags) > 50:
            raise ValueError('Maximum 50 tags allowed')
        for tag in tags:
            if len(tag) > 50:
                raise ValueError('Each tag must be ≤50 characters')
        return tags

class ExportFormatEnum(str, Enum):
    csv = "csv"
    markdown = "markdown"
    json = "json"

class ExportRequest(BaseModel):
    format: ExportFormatEnum
    filename: constr(max_length=255, regex=r'^[A-Za-z0-9_-]+$')
    include_favorites: bool = False
    include_metadata: bool = True
```

#### Step 1.2: Implement Validator Utilities

Create `src/web/validators/`:
- `sanitizers.py` - Filename, path, string sanitization
- `file_validators.py` - MIME type, size, extension checks
- `constraints.py` - Shared constraint definitions

#### Step 1.3: Update API Endpoints

Replace Form parameters with Pydantic models using FastAPI dependency injection

---

### Phase 2: Server Enforcement

#### Step 2.1: Service Layer Hardening
- Add pre-condition checks in service methods
- Implement defensive programming patterns
- Add length/type assertions

#### Step 2.2: File Upload Hardening
- Use `tempfile.NamedTemporaryFile()` for secure temp file creation
- Implement chunked reading for large files
- Add MIME type validation
- Enforce size limits

#### Step 2.3: Expand Test Coverage
- Add malicious payload tests
- Path traversal attempt tests
- Boundary condition tests
- Large file tests

---

### Phase 3: User Interface

#### Step 3.1: Client-Side Validation
- Mirror server constraints in JavaScript
- Add real-time validation feedback
- Implement maxlength attributes on inputs

#### Step 3.2: Error Messages (i18n)
- Add validation error keys to translation files
- Display user-friendly error messages
- Include field-specific guidance

#### Step 3.3: Accessibility
- Add ARIA error announcements
- Associate error messages with form fields
- Ensure keyboard navigation works with validation

---

### Phase 4: Quality Assurance

#### Step 4.1: Testing
- Unit tests for all validators
- Integration tests for API endpoints
- Security penetration testing
- Performance regression tests

#### Step 4.2: Documentation
- Update OpenAPI/Swagger docs with validation rules
- Document validation error codes
- Add validation examples to API docs

#### Step 4.3: Monitoring
- Log validation failures
- Track validation error rates
- Alert on suspicious patterns

---

## Success Criteria

### Phase 0 Completion Criteria ✅

- [x] Complete inventory of all input-accepting endpoints
- [x] Document current validation state for each endpoint
- [x] Analyze service layer input handling patterns
- [x] Establish field constraints and validation rules
- [x] Identify security vulnerabilities and risk levels
- [x] Create comprehensive specification document

### Phase 1-4 Success Criteria (Future)

**Phase 1 - API Layer**:
- [ ] All endpoints use Pydantic request models
- [ ] Validation errors return standardized 422 responses
- [ ] 100% field coverage with constraints
- [ ] Validator utility library created

**Phase 2 - Server Enforcement**:
- [ ] File upload path traversal prevented
- [ ] MIME type validation implemented
- [ ] Size limits enforced
- [ ] Malicious payload test suite passes 100%

**Phase 3 - User Interface**:
- [ ] Client-side validation matches server rules
- [ ] All error messages localized (en/fr/es/de)
- [ ] WCAG 2.1 AA compliance for validation errors
- [ ] Real-time validation feedback implemented

**Phase 4 - Quality Assurance**:
- [ ] Test coverage ≥ 85% maintained
- [ ] OpenAPI docs updated with validation schemas
- [ ] Validation monitoring dashboard created
- [ ] Post-rollout maintenance procedures documented

---

## Next Steps

1. **Review & Approval**: Stakeholder review of Phase 0 specification
2. **Prioritization**: Confirm vulnerability remediation order (suggest: Critical → High → Medium)
3. **Phase 1 Kickoff**: Begin Pydantic model implementation
4. **Resource Allocation**: Assign developers to validation framework work
5. **Timeline**: Establish milestones for Phases 1-4 (suggested 2-week total per issue estimate)

---

## Appendix A: Code References

### Critical Code Locations

**Path Traversal Vulnerabilities**:
- app.py:346 - Export filename handling
- app.py:390 - Import temp file creation

**Tag Parsing**:
- app.py:32-49 - `_parse_tags_field()` helper
- prompt_data_service.py:32-49 - `_normalize_tags()`

**Backup Sanitization**:
- backup_service.py:392-397 - `_sanitize_backup_name()`

**Integer Validation Pattern**:
- app.py:198-200, 227-229, 248-250, 662-664, 739-741

---

## Appendix B: Validation Libraries

**Recommended Dependencies**:
- `pydantic` (already in project) - Request/response validation
- `python-magic` - MIME type detection
- `slowapi` - Rate limiting for FastAPI
- `validators` - Additional validation utilities

---

## Appendix C: Attack Scenarios

### Scenario 1: Path Traversal Export
```python
POST /api/export
Content-Type: application/x-www-form-urlencoded

format=json&filename=../../../etc/passwd
```

**Current Behavior**: Creates file at `/tmp/../../../etc/passwd.json`
**Expected Behavior**: Reject with 400 Bad Request, "Invalid filename"

### Scenario 2: Oversized Prompt DoS
```python
POST /api/prompts
Content-Type: application/x-www-form-urlencoded

title=Test&prompt=<10GB_of_text>
```

**Current Behavior**: Attempts to load entire payload into memory → OOM crash
**Expected Behavior**: Reject with 413 Payload Too Large

### Scenario 3: Malicious File Upload
```python
POST /api/import
Content-Type: multipart/form-data

file=<malware.exe_renamed_to_data.json>
```

**Current Behavior**: Accepts file, attempts to parse as JSON
**Expected Behavior**: Reject with 400 Bad Request, "Invalid file type"

---

**Document Version**: 1.0
**Last Updated**: 2025-11-05
**Next Review**: Upon Phase 1 completion
