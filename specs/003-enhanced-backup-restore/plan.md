# Implementation Plan: Enhanced Backup & Restore System

**Branch**: `003-enhanced-backup-restore` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-enhanced-backup-restore/spec.md`

## Summary

Extend the existing `BackupService` (db-backed, supports pg_dump + SQLite copy) with: scheduled automatic backups via APScheduler, AES-based encryption with Argon2-derived keys, S3-compatible cloud storage upload/download, incremental (application-level diff) backups, restore preview with selective restore, backup integrity checksums, configurable retention policies with tagging/search, and a monitoring/audit dashboard.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript 5.x (frontend)

**Primary Dependencies**:

- FastAPI 0.104.1, SQLAlchemy 2.x, APScheduler 3.10+ (already installed)
- `cryptography>=41.0.0` — Fernet/AES encryption (already installed)
- `argon2-cffi>=23.1.0` — key derivation for encryption (already installed)
- `boto3` — S3-compatible cloud storage (new dependency)
- Alembic — migrations for new tables (already installed)

**Storage**: PostgreSQL (primary) / SQLite (dev/test) via SQLAlchemy ORM; new tables via Alembic migrations

**Testing**: pytest + pytest-cov (≥85% coverage gate), Vitest (frontend)

**Target Platform**: Linux server (self-hosted), Docker (docker-compose.yml present)

**Project Type**: Web service (FastAPI backend + TypeScript SPA frontend)

**Performance Goals**:

- SC-002: Scheduled backups execute within 5 minutes of trigger time
- SC-003: Incremental backups ≥50% faster than full backups for <20% data change volume

**Constraints**:

- Encryption keys MUST NOT be stored in plaintext (FR-012)
- All backup ops must be admin-only (FR-029, Constitution §III)
- No raw SQL with user input (Constitution Security Standards)
- All TypeScript under `src/web/static/ts/` (Constitution §IV)

**Scale/Scope**: Single-tenant self-hosted; backup files stored locally + optional cloud; audit log for all operations

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                              | Status          | Notes                                                                                                                                                                                                                                                         |
| -------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **I. Layered Service Architecture**    | PASS            | New services (`BackupSchedulerService`, `BackupEncryptionService`, `CloudStorageService`) sit in `src/services/`. Routes stay in `src/web/app.py` or a new `src/web/routers/backup.py`. Repositories in `src/db/repositories/`. No route touches DB directly. |
| **II. Test Coverage Gate (≥85%)**      | PASS — enforced | All new service methods and routes must have tests in the same PR. High-risk paths (encryption, cloud upload, scheduler) need explicit coverage.                                                                                                              |
| **III. Security-First Authentication** | PASS            | All backup mutation endpoints (create, restore, delete, schedule config, cloud config, encryption config) are protected by admin role requirement. JWT ES256 validation applies. FR-029 enforces admin-only.                                                  |
| **IV. TypeScript-Only Frontend**       | PASS            | New UI code in `src/web/static/ts/backup-management.ts` (existing file to extend) + new components under `src/web/static/ts/components/`. No edits to `src/web/static/js/`.                                                                                   |
| **V. Database-Backed Persistence**     | PASS            | New entities (BackupSchedule, BackupStorageProvider, AuditLogEntry, EncryptionKeyConfig) as SQLAlchemy ORM models with Alembic migrations. No JSON file storage for new features.                                                                             |

**Post-Phase-1 Re-check**: Verify BackupScheduleRepository and AuditLogRepository do not bypass service layer; verify cloud provider credentials are stored as encrypted column, not plaintext.

## Project Structure

### Documentation (this feature)

```text
specs/003-enhanced-backup-restore/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── backup-api.md
│   └── backup-schedule-config.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
src/
├── db/
│   ├── models/
│   │   ├── backup.py                    # EXTEND: add checksum, encryption_status, backup_kind, tags
│   │   ├── backup_schedule.py           # NEW: BackupSchedule ORM model
│   │   ├── backup_storage_provider.py   # NEW: CloudStorageProvider ORM model
│   │   ├── backup_audit_log.py          # NEW: AuditLogEntry ORM model
│   │   └── encryption_key_config.py     # NEW: EncryptionKeyConfig ORM model
│   └── repositories/
│       ├── backup_repository.py         # NEW: CRUD for Backup (currently inline in service)
│       ├── backup_schedule_repository.py
│       ├── backup_storage_provider_repository.py
│       └── backup_audit_log_repository.py
├── services/
│   ├── backup_service_db.py             # EXTEND: add checksum, incremental, encryption, retention
│   ├── backup_scheduler_service.py      # NEW: APScheduler integration for scheduled backups
│   ├── backup_encryption_service.py     # NEW: Fernet/AES-GCM encryption with Argon2 key derivation
│   ├── backup_cloud_service.py          # NEW: boto3 S3 upload/download abstraction
│   └── backup_audit_service.py          # NEW: AuditLogEntry write/read
├── web/
│   ├── app.py                           # EXTEND: wire new routers/services
│   └── routers/
│       └── backup.py                    # NEW: extract all /api/backups* routes here
└── scheduler/
    └── backup_scheduler.py             # NEW: APScheduler job definitions (cron triggers)

alembic/versions/
└── XXXXXX_enhanced_backup_tables.py    # NEW: migration for 4 new tables + Backup column additions

src/web/static/ts/
├── backup-management.ts                # EXTEND: schedule UI, encryption UI, cloud config UI
└── components/
    ├── backup-restore-preview.ts       # NEW: diff viewer component
    └── backup-monitoring-dashboard.ts  # NEW: monitoring dashboard component

src/web/templates/
└── backup_management.html             # EXTEND: new sections for schedule, cloud, encryption, monitor

tests/
├── unit/
│   ├── test_backup_scheduler_service.py
│   ├── test_backup_encryption_service.py
│   ├── test_backup_cloud_service.py
│   └── test_backup_audit_service.py
├── integration/
│   ├── test_backup_schedule_api.py
│   ├── test_backup_encryption_api.py
│   ├── test_backup_cloud_api.py
│   └── test_backup_restore_preview_api.py
└── contract/
    └── test_backup_api_contracts.py
```

**Structure Decision**: Extends existing web service (Option 2 adapted — single repo with FastAPI backend + TypeScript frontend). Extracts backup routes from the monolithic `app.py` into `src/web/routers/backup.py` to keep the router boundary clean. Introduces four new service files rather than growing `backup_service_db.py` unboundedly.

## Complexity Tracking

> No constitution violations detected. All new patterns align with established project conventions.
