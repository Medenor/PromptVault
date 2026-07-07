# Tasks: Enhanced Backup & Restore System

**Input**: Design documents from `/specs/003-enhanced-backup-restore/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/backup-api.md ✅, quickstart.md ✅, constitution.md ✅

**Tests**: Not explicitly requested — test tasks omitted. Add them if TDD approach is desired.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths are included in all task descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add new dependency, wire app entry point, create the backup router skeleton

- [x] T001 Add `boto3` to `requirements.txt` and run `pip install boto3`
- [x] T002 Create `src/web/routers/backup.py` as a FastAPI `APIRouter` with prefix `/api` and include it in `src/web/app.py`, removing duplicate backup route registrations from `app.py`
- [x] T003 [P] Create `src/scheduler/backup_scheduler.py` as an empty module with `register_backup_jobs(scheduler)` stub
- [x] T004 [P] Create `tests/unit/` and `tests/integration/` directories (add `.gitkeep` if empty)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Alembic migration for all new tables + Backup column additions, new ORM models, and base repositories — MUST be complete before any user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Write Alembic migration `alembic/versions/XXXXXX_enhanced_backup_tables.py` adding new columns to `backups` (`backup_kind`, `parent_backup_id`, `checksum`, `integrity_verified_at`, `is_encrypted`, `encryption_salt`, `encryption_nonce`, `cloud_provider_id`, `cloud_path`, `cloud_uploaded_at`, `tags`, `delta_payload`) and creating four new tables: `backup_schedules`, `backup_storage_providers`, `backup_audit_log`, `encryption_key_configs`
- [x] T006 Extend `src/db/models/backup.py` with the twelve new columns per data-model.md; add self-referential `parent_backup` relationship and optional `storage_provider` relationship
- [x] T007 [P] Create `src/db/models/backup_schedule.py` with `BackupSchedule` ORM model (all columns per data-model.md)
- [x] T008 [P] Create `src/db/models/backup_storage_provider.py` with `BackupStorageProvider` ORM model (all columns including `credentials_encrypted`, `credentials_salt`, `credentials_nonce`)
- [x] T009 [P] Create `src/db/models/backup_audit_log.py` with `AuditLogEntry` ORM model (append-only; `occurred_at`, `operation`, `outcome`, `backup_id` FK, `performed_by`, `detail`)
- [x] T010 [P] Create `src/db/models/encryption_key_config.py` with `EncryptionKeyConfig` ORM model (all columns per data-model.md; never stores passphrase)
- [x] T011 Create `src/db/repositories/backup_repository.py` with `BackupRepository`: `create`, `get_by_id`, `list_backups` (with tag/date/kind filters), `update`, `delete`, `get_all_for_cleanup`
- [x] T012 [P] Create `src/db/repositories/backup_schedule_repository.py` with `BackupScheduleRepository`: `get_active`, `upsert` (singleton pattern — at most one row)
- [x] T013 [P] Create `src/db/repositories/backup_storage_provider_repository.py` with `BackupStorageProviderRepository`: `create`, `get_by_id`, `list_all`, `delete`
- [x] T014 [P] Create `src/db/repositories/backup_audit_log_repository.py` with `BackupAuditLogRepository`: `append` (insert-only), `list_entries` (with operation/outcome filters, pagination)
- [x] T015 Run `alembic upgrade head` to apply migration and verify all five tables exist

**Checkpoint**: Foundation ready — all models and repositories exist; user story implementation can now begin

---

## Phase 3: User Story 1 — Scheduled Automatic Backups (Priority: P1) 🎯 MVP

**Goal**: Administrators configure and activate a backup schedule; APScheduler fires the job automatically; schedule survives server restarts via SQLAlchemyJobStore.

**Independent Test**: Configure daily schedule via `PUT /api/backup-schedule`, trigger APScheduler job directly in a test using `freezegun`, verify a `Backup` row was created and `last_run_status = 'success'`.

### Implementation for User Story 1

- [x] T016 Create `src/services/backup_scheduler_service.py` with `BackupSchedulerService`: `get_schedule`, `upsert_schedule`, `enable`, `disable`, `_run_scheduled_backup` (calls `BackupService.create_backup`, prevents concurrent execution via a lock or APScheduler `coalesce=True`), `_register_job`, `_unregister_job`; wire `SQLAlchemyJobStore` using `DATABASE_URL`
- [x] T017 [P] Implement schedule APScheduler job in `src/scheduler/backup_scheduler.py`: `register_backup_jobs(scheduler)` reads enabled `BackupSchedule` rows and registers `CronTrigger` job(s) pointing to `BackupSchedulerService._run_scheduled_backup`; integrate into app startup in `src/web/app.py`
- [x] T018 [US1] Implement `GET /api/backup-schedule` and `PUT /api/backup-schedule` in `src/web/routers/backup.py` using `BackupSchedulerService`; validate `frequency`/`hour`/`minute`/`day_of_week`/`day_of_month` per data-model.md constraints; return schedule object per contracts/backup-api.md
- [x] T019 [US1] Add schedule configuration UI to `src/web/static/ts/backup-management.ts`: enable/disable toggle, frequency dropdown (daily/weekly/monthly), hour/minute pickers, retention count fields; wire to `PUT /api/backup-schedule`
- [x] T020 [US1] Add schedule config section to `src/web/templates/backup_management.html` and bind to TypeScript component

**Checkpoint**: Scheduled backups work end-to-end — configure schedule, trigger fires, backup created and visible in history

---

## Phase 4: User Story 2 — Backup Encryption (Priority: P2)

**Goal**: Admin enables AES-256-GCM encryption with Argon2id key derivation; encrypted backups are unreadable without the passphrase; key rotation increments `key_version`.

**Independent Test**: Enable encryption via `PUT /api/backup-encryption`, create a backup with `encrypt=true`, open the file and confirm it is binary/non-SQLite, restore with correct passphrase and confirm success, attempt restore with wrong passphrase and confirm failure.

### Implementation for User Story 2

- [x] T021 Create `src/services/backup_encryption_service.py` with `BackupEncryptionService`: `get_config`, `enable(passphrase)`, `disable`, `rotate_key(old_passphrase, new_passphrase)` (increments `key_version`, re-encrypts future backups; existing backups retain old salt/nonce), `encrypt_file(path, passphrase) -> bytes` (Argon2id key derivation + AES-256-GCM; stores per-backup random salt + nonce in `Backup` row), `decrypt_file(path, passphrase, salt, nonce) -> bytes`; passphrase is NEVER stored — only salt/nonce stored per backup
- [x] T022 [US2] Extend `src/services/backup_service_db.py` to call `BackupEncryptionService.encrypt_file` when `encrypt=True` or `EncryptionKeyConfig.is_enabled=True`; write ciphertext to disk; persist `is_encrypted=True`, `encryption_salt`, `encryption_nonce`, and `key_version` in `backup_metadata` to `Backup` row
- [x] T023 [US2] Implement `GET /api/backup-encryption` and `PUT /api/backup-encryption` (enable/disable and key rotation) in `src/web/routers/backup.py`; never return passphrase; return config object per contracts/backup-api.md
- [x] T024 [US2] Extend restore path in `src/services/backup_service_db.py` to call `BackupEncryptionService.decrypt_file` when `Backup.is_encrypted=True`, using stored `encryption_salt` and `encryption_nonce`; accept `passphrase` in restore request body
- [x] T025 [US2] Add encryption configuration UI to `src/web/static/ts/backup-management.ts`: enable toggle, passphrase input, rotate key form (old/new passphrase); bind to `PUT /api/backup-encryption`
- [x] T026 [US2] Add encryption config section to `src/web/templates/backup_management.html`

**Checkpoint**: Encrypted backups are unreadable on disk; decryption succeeds with correct passphrase; key rotation works

---

## Phase 5: User Story 3 — Cloud Storage Integration (Priority: P3)

**Goal**: Admin configures S3/S3-compatible provider; backups auto-upload after creation; local copy retained; restore from cloud supported.

**Independent Test**: Configure MinIO provider via `POST /api/backup-providers`, test connectivity via `POST /api/backup-providers/{id}/test`, create a backup with `cloud_provider_id` set, verify `cloud_path` and `cloud_uploaded_at` are non-null, verify local file still exists (FR-015), restore from cloud path.

### Implementation for User Story 3

- [x] T027 Create `src/services/backup_cloud_service.py` with `BackupCloudService`: `upload(backup_path, provider, remote_key) -> str` (boto3 `upload_fileobj`), `download(provider, remote_key, dest_path)` (boto3 `download_fileobj`), `test_connectivity(provider) -> bool`, `_decrypt_credentials(provider) -> dict` (uses `BackupEncryptionService` pattern with admin passphrase stored as `credentials_encrypted`); all boto3 calls use `endpoint_url` for S3-compatible support
- [x] T028 [US3] Implement `GET /api/backup-providers`, `POST /api/backup-providers`, `DELETE /api/backup-providers/{provider_id}`, `POST /api/backup-providers/{provider_id}/test` in `src/web/routers/backup.py`; encrypt credentials before persisting (`BackupStorageProvider.credentials_encrypted`); never return raw credentials in responses; return 409 if provider is referenced by backups on delete
- [x] T029 [US3] Extend `src/services/backup_service_db.py` post-creation step: if `cloud_provider_id` is set, call `BackupCloudService.upload`; on failure, log to audit log and retain local backup (do not fail the whole backup operation — FR-015); update `Backup.cloud_path` and `cloud_uploaded_at` on success
- [x] T030 [US3] Extend restore path in `src/services/backup_service_db.py`: if restore source is a cloud backup and local file is absent, call `BackupCloudService.download` first; then proceed with normal restore (including decryption if encrypted)
- [x] T031 [US3] Extend `GET /api/backups` and `GET /api/backups/{backup_id}` responses to include `cloud_provider_id`, `cloud_path`, `cloud_uploaded_at`, and storage location label in `src/web/routers/backup.py`
- [x] T032 [US3] Add cloud provider management UI to `src/web/static/ts/backup-management.ts`: provider list, add-provider form (name, type, endpoint, bucket, credentials), test-connection button; bind to provider endpoints
- [x] T033 [US3] Add cloud provider section to `src/web/templates/backup_management.html`

**Checkpoint**: Cloud upload/download works; local copy always retained; credentials never exposed in API responses

---

## Phase 6: User Story 4 — Restore Preview & Selective Restore (Priority: P4)

**Goal**: Admin previews a diff (added/updated/deleted prompts) before restoring; can select a subset of prompts to restore.

**Independent Test**: Create a backup, modify some prompts, call `POST /api/backups/{id}/restore-preview`, verify diff summary matches expected changes, call selective restore with specific `prompt_ids`, verify only those prompts were changed.

### Implementation for User Story 4

- [x] T034 Implement `_compute_restore_diff(backup_id, passphrase=None) -> dict` in `src/services/backup_service_db.py`: deserialize backup data (decrypt if needed), compare each prompt record against current DB state, return `{added: [...], updated: [{id, before, after}], deleted: [...]}` per contracts/backup-api.md; for incremental backups, compose delta with parent full backup
- [x] T035 [US4] Implement `POST /api/backups/{backup_id}/restore-preview` in `src/web/routers/backup.py` calling `_compute_restore_diff`; accept optional `passphrase` in request body; return full diff payload per contracts/backup-api.md
- [x] T036 [US4] Extend `POST /api/backups/{backup_id}/restore` in `src/web/routers/backup.py` to accept optional `prompt_ids` list; when provided, only restore matching prompts; create pre-restore safety backup before applying changes; return `{restored: true, pre_restore_backup_id: "..."}`
- [x] T037 [US4] Create `src/web/static/ts/components/backup-restore-preview.ts`: diff viewer component showing added (green)/updated (yellow)/deleted (red) prompt rows; checkboxes for selective restore; confirm/cancel actions; passphrase input when `is_encrypted=true`
- [x] T038 [US4] Add restore preview modal/section to `src/web/templates/backup_management.html` and wire to `backup-restore-preview.ts` component

**Checkpoint**: Preview diff accurately shows what would change; selective restore applies only chosen prompts; pre-restore safety backup created

---

## Phase 7: User Story 5 — Backup Monitoring & Audit (Priority: P5)

**Goal**: Admin views monitoring dashboard (history, success rate, storage trends, quota warning); every backup/restore operation recorded in audit log with user, timestamp, outcome.

**Independent Test**: Perform several backup and restore operations, call `GET /api/backup-monitoring`, verify counts match, call `GET /api/backup-audit-log`, verify all operations appear with correct `performed_by` and `outcome`.

### Implementation for User Story 5

- [x] T039 Create `src/services/backup_audit_service.py` with `BackupAuditService`: `log(operation, outcome, backup_id, performed_by, detail)` — writes `AuditLogEntry` via `BackupAuditLogRepository`; `get_log(operation, outcome, limit, offset)` — reads with filters; `get_dashboard_stats() -> dict` — computes `total_backups`, `success_rate_30d`, `total_size_bytes`, `last_backup_at`, `last_backup_status`, `quota_warning`, `history` (per-day counts for last 30 days)
- [x] T040 [US5] Instrument all backup mutation paths with `BackupAuditService.log` calls: `backup.create` (in `BackupService`), `backup.restore` (in restore path), `backup.delete` (in delete handler), `backup.verify` (in integrity check), `schedule.update`, `cloud.upload`, `integrity.check` — cover SC-005 (100% of operations logged); pass `performed_by` from JWT `sub` claim or `'scheduler'` for automated jobs
- [x] T041 [US5] Implement `GET /api/backup-monitoring` in `src/web/routers/backup.py` calling `BackupAuditService.get_dashboard_stats()`; include `quota_warning=True` when `total_size_bytes > storage_quota_bytes * 0.9`; return per-day history array per contracts/backup-api.md
- [x] T042 [US5] Implement `GET /api/backup-audit-log` in `src/web/routers/backup.py` with `operation`, `outcome`, `limit`, `offset` query params; return paginated entries per contracts/backup-api.md
- [x] T043 [US5] Create `src/web/static/ts/components/backup-monitoring-dashboard.ts`: success rate gauge, storage usage bar, per-day history table, audit log table with operation/outcome/user columns; poll or refresh on demand
- [x] T044 [US5] Add monitoring dashboard section to `src/web/templates/backup_management.html`

**Checkpoint**: Dashboard shows accurate stats; audit log contains all operations with no gaps (SC-005)

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integrity verification, incremental backups, retention cleanup, tagging/search, and edge-case hardening across all stories

- [X] T045 Implement backup integrity check in `src/services/backup_service_db.py`: `verify_backup(backup_id) -> dict` — read file, compute SHA-256 (on ciphertext for encrypted backups), compare to `Backup.checksum`, update `integrity_verified_at` if valid, log to audit; implement `POST /api/backups/{backup_id}/verify` in `src/web/routers/backup.py`
- [X] T046 [P] Implement incremental backup creation in `src/services/backup_service_db.py`: on `backup_kind='incremental'`, snapshot current prompts as JSON, diff against parent full backup, store only delta in `Backup.delta_payload`; enforce `parent_backup_id IS NOT NULL`; fall back to full backup when no valid prior backup exists (FR-006)
- [X] T047 [P] Implement retention cleanup in `src/services/backup_service_db.py`: `apply_retention_policy(dry_run=True) -> dict` — applies `retention_daily_count`, `retention_weekly_count`, `retention_monthly_count` from `BackupSchedule`; returns `{dry_run, would_delete, deleted}`; implement `POST /api/backups/cleanup` in `src/web/routers/backup.py`
- [X] T048 [P] Implement tagging API in `src/web/routers/backup.py`: `POST /api/backups/{backup_id}/tags` validates tag count (max 20) and length (max 64 chars) before persisting to `Backup.tags`
- [X] T049 [P] Extend `GET /api/backups` to support `tag`, `start_date`, `end_date`, `kind` query params via `BackupRepository.list_backups` filters; extend backup list UI in `src/web/static/ts/backup-management.ts` with filter controls
- [X] T050 [P] Add concurrent-backup guard to `src/services/backup_service_db.py`: return `409 Conflict` if a backup is already in progress when `POST /api/backups` or a scheduled trigger fires (FR-004); add disk-space check pre-creation and log failure to audit if insufficient
- [X] T051 [P] Add in-app notification on backup success/failure (FR-026): emit notification via existing notification system (or create a simple `flash` mechanism) after each scheduled backup completes; surface in monitoring dashboard
- [X] T052 Run full quickstart.md validation scenarios (Scenarios 1–7) against local stack to confirm all acceptance criteria pass
- [X] T053 [P] Run `python -m pytest tests/ --cov=src --cov-report=term-missing` and confirm coverage ≥ 85%; run `npm run typecheck && npm run lint && npm run test:unit:coverage` and confirm frontend coverage ≥ 85%

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories; run `alembic upgrade head` before any service code
- **Phase 3 (US1)**: Requires Phase 2
- **Phase 4 (US2)**: Requires Phase 2; US3 depends on US2 (encryption must exist before cloud stores encrypted backups)
- **Phase 5 (US3)**: Requires Phase 2 + US2 (`BackupEncryptionService` used to encrypt cloud credentials)
- **Phase 6 (US4)**: Requires Phase 2; independent of US1–US3 at service layer
- **Phase 7 (US5)**: Requires Phase 2; `BackupAuditService` must be instrumented across all stories (T040 touches all mutation paths)
- **Phase 8 (Polish)**: Requires all desired user story phases to be complete

### User Story Dependencies

- **US1 (Scheduled Backups, P1)**: Independent after Foundational
- **US2 (Encryption, P2)**: Independent after Foundational; US3 depends on US2
- **US3 (Cloud Storage, P3)**: Depends on US2 (credential encryption uses `BackupEncryptionService`)
- **US4 (Restore Preview, P4)**: Independent after Foundational; complements US2 (passphrase param in preview)
- **US5 (Monitoring, P5)**: Independent after Foundational; instrumentation (T040) spans all stories

### Within Each Phase

- ORM models (T006–T010) before repositories (T011–T014)
- Repositories before services
- Services before routers/endpoints
- Backend endpoints before TypeScript UI components
- TypeScript components before HTML template wiring

### Parallel Opportunities

- T007, T008, T009, T010 — all new ORM models (different files)
- T012, T013, T014 — all new repositories (different files)
- T003, T004 — setup scaffolding tasks
- T017 — scheduler wiring can parallel T016 service creation after T016 is stubbed
- T045, T046, T047, T048, T049, T050, T051 — all Polish tasks are independent

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T005 migration is written and T006 Backup model extended:
# All four new ORM models can be created simultaneously:
Task: T007 — src/db/models/backup_schedule.py
Task: T008 — src/db/models/backup_storage_provider.py
Task: T009 — src/db/models/backup_audit_log.py
Task: T010 — src/db/models/encryption_key_config.py

# After all models exist, all four repositories can be created simultaneously:
Task: T011 — src/db/repositories/backup_repository.py
Task: T012 — src/db/repositories/backup_schedule_repository.py
Task: T013 — src/db/repositories/backup_storage_provider_repository.py
Task: T014 — src/db/repositories/backup_audit_log_repository.py
```

## Parallel Example: Phase 8 (Polish)

```bash
# All six Polish tasks are independent (different files/concerns):
Task: T045 — backup integrity verify endpoint
Task: T046 — incremental backup logic
Task: T047 — retention cleanup endpoint
Task: T048 — tagging API
Task: T049 — backup list filters
Task: T050 — concurrent-backup guard
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational — apply migration, verify tables exist
3. Complete Phase 3: User Story 1 (scheduled backups)
4. **STOP and VALIDATE**: Configure schedule via API, trigger job, verify backup appears in history
5. Deploy/demo if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 (US1) → Scheduled backups work → **Demo**
3. Phase 4 (US2) → Encrypted backups work → **Demo**
4. Phase 5 (US3) → Cloud upload/restore works → **Demo**
5. Phase 6 (US4) → Restore preview + selective restore → **Demo**
6. Phase 7 (US5) → Monitoring dashboard + audit log → **Demo**
7. Phase 8 → Integrity, incremental, retention, tagging → **Full feature complete**

### Parallel Team Strategy

With multiple developers after Phase 2 completes:

- Developer A: US1 (scheduler service + APScheduler integration)
- Developer B: US2 (encryption service)
- Developer C: US4 (restore preview — independent of US2/US3)
- Developer D: US5 instrumentation (audit service — wraps all mutation paths)
- US3 (cloud) begins after Developer B completes US2

---

## Notes

- **[P]** tasks = different files, no dependencies on incomplete sibling tasks
- **[USn]** label maps task to specific user story for traceability
- Constitution §I: No route may query the DB directly — all routes go through service layer
- Constitution §II: ≥ 85% coverage gate — run `pytest --cov` before merging
- Constitution §III: All backup mutation endpoints require admin JWT (FR-029)
- Constitution §IV: All new frontend code under `src/web/static/ts/` — no edits to `src/web/static/js/`
- Constitution §V: All schema changes via Alembic migration — no manual DDL
- Key security invariant: passphrase is NEVER stored; only `encryption_salt` + `encryption_nonce` per backup
- Cloud credentials are encrypted at rest in `BackupStorageProvider.credentials_encrypted`
- `AuditLogEntry` rows are NEVER deleted by application code
- Pre-restore safety backup (T036) prevents data loss on selective restore
