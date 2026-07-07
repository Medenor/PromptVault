# Data Model: Enhanced Backup & Restore

**Feature Branch**: `003-enhanced-backup-restore`
**Date**: 2026-07-07

---

## Entity Overview

```
Backup ─────────────── BackupSchedule
  │                      (1 active per system)
  │
  ├── parent_backup_id ──▶ Backup   (incremental → full chain)
  ├── storage_provider_id ──▶ BackupStorageProvider
  │
AuditLogEntry ─────────── (references backup_id, performed_by user_id)
EncryptionKeyConfig ───── (system singleton or per-backup salt metadata)
```

---

## 1. Backup (extend existing `backups` table)

**Existing columns** (keep as-is): `id`, `backup_type`, `filename`, `storage_path`, `size_bytes`, `prompt_count`, `created_by`, `created_at`, `succeeded`, `backup_metadata`.

**New columns** (via Alembic migration):

| Column                  | Type                                            | Nullable | Default  | Description                                                                                   |
| ----------------------- | ----------------------------------------------- | -------- | -------- | --------------------------------------------------------------------------------------------- |
| `backup_kind`           | `String(20)`                                    | No       | `'full'` | `'full'` or `'incremental'`                                                                   |
| `parent_backup_id`      | `String(36)` FK → `backups.id`                  | Yes      | NULL     | Parent full backup for incremental                                                            |
| `checksum`              | `String(64)`                                    | Yes      | NULL     | SHA-256 hex digest of backup file (ciphertext if encrypted)                                   |
| `integrity_verified_at` | `DateTime(tz=True)`                             | Yes      | NULL     | Last successful integrity check timestamp                                                     |
| `is_encrypted`          | `Boolean`                                       | No       | `False`  | Whether backup file is AES-256-GCM encrypted                                                  |
| `encryption_salt`       | `String(32)`                                    | Yes      | NULL     | 16-byte hex-encoded salt for Argon2id key derivation                                          |
| `encryption_nonce`      | `String(24)`                                    | Yes      | NULL     | 12-byte hex-encoded GCM nonce (prepended to ciphertext; also stored here for metadata access) |
| `cloud_provider_id`     | `String(36)` FK → `backup_storage_providers.id` | Yes      | NULL     | If uploaded to cloud, which provider                                                          |
| `cloud_path`            | `Text`                                          | Yes      | NULL     | Remote path/key in the cloud bucket/folder                                                    |
| `cloud_uploaded_at`     | `DateTime(tz=True)`                             | Yes      | NULL     | When cloud upload completed                                                                   |
| `tags`                  | `JSON`                                          | Yes      | `[]`     | Admin-assigned labels e.g. `["before-migration", "prod"]`                                     |
| `delta_payload`         | `JSON`                                          | Yes      | NULL     | For incremental backups: `{added:[...], updated:[...], deleted:[...]}` prompt records         |

**Relationships**:

- `parent_backup` → self-referential FK (incremental → full)
- `storage_provider` → `BackupStorageProvider` (optional)

**State transitions**:

```
(creating) → succeeded=True, checksum set → (verified: integrity_verified_at set)
                                           → (uploaded: cloud_uploaded_at set)
           → succeeded=False              → (failed)
```

**Validation rules**:

- `backup_kind == 'incremental'` requires `parent_backup_id IS NOT NULL`
- `is_encrypted == True` requires `encryption_salt IS NOT NULL` and `encryption_nonce IS NOT NULL`
- `cloud_path IS NOT NULL` requires `cloud_provider_id IS NOT NULL`
- `tags` max 20 elements; each tag max 64 chars

---

## 2. BackupSchedule (new table `backup_schedules`)

Singleton-style: at most one active schedule per system (enforced at service layer).

| Column                      | Type                                            | Nullable | Default | Description                             |
| --------------------------- | ----------------------------------------------- | -------- | ------- | --------------------------------------- |
| `id`                        | `String(36)` PK                                 | No       | UUID    |                                         |
| `enabled`                   | `Boolean`                                       | No       | `False` | Whether schedule is active              |
| `frequency`                 | `String(20)`                                    | No       | —       | `'daily'`, `'weekly'`, `'monthly'`      |
| `hour`                      | `Integer`                                       | No       | —       | 0–23, UTC                               |
| `minute`                    | `Integer`                                       | No       | `0`     | 0–59, UTC                               |
| `day_of_week`               | `Integer`                                       | Yes      | NULL    | 0=Mon–6=Sun; required for `weekly`      |
| `day_of_month`              | `Integer`                                       | Yes      | NULL    | 1–31; required for `monthly`            |
| `retention_daily_count`     | `Integer`                                       | No       | `7`     | How many daily backups to keep          |
| `retention_weekly_count`    | `Integer`                                       | No       | `4`     | How many weekly backups to keep         |
| `retention_monthly_count`   | `Integer`                                       | No       | `12`    | How many monthly backups to keep        |
| `encrypt_scheduled_backups` | `Boolean`                                       | No       | `False` | Whether scheduled backups are encrypted |
| `cloud_provider_id`         | `String(36)` FK → `backup_storage_providers.id` | Yes      | NULL    | Auto-upload destination                 |
| `created_at`                | `DateTime(tz=True)`                             | No       | `now()` |                                         |
| `updated_at`                | `DateTime(tz=True)`                             | No       | `now()` | Updated on every config change          |
| `last_run_at`               | `DateTime(tz=True)`                             | Yes      | NULL    | When last scheduled backup ran          |
| `last_run_status`           | `String(20)`                                    | Yes      | NULL    | `'success'` or `'failure'`              |

**Validation rules**:

- `frequency == 'weekly'` requires `day_of_week IN (0..6)`
- `frequency == 'monthly'` requires `day_of_month IN (1..31)`
- `hour IN (0..23)`, `minute IN (0..59)`

---

## 3. BackupStorageProvider (new table `backup_storage_providers`)

| Column                  | Type                | Nullable | Default | Description                                                                   |
| ----------------------- | ------------------- | -------- | ------- | ----------------------------------------------------------------------------- |
| `id`                    | `String(36)` PK     | No       | UUID    |                                                                               |
| `name`                  | `String(100)`       | No       | —       | Admin-given display name, e.g. "My MinIO"                                     |
| `provider_type`         | `String(20)`        | No       | —       | `'s3'` (v1 only)                                                              |
| `endpoint_url`          | `Text`              | Yes      | NULL    | For S3-compatible (MinIO, etc.); NULL for AWS S3                              |
| `bucket_name`           | `String(255)`       | No       | —       | S3 bucket / cloud folder                                                      |
| `prefix`                | `String(512)`       | Yes      | `''`    | Key prefix within bucket                                                      |
| `region`                | `String(50)`        | Yes      | NULL    | AWS region (optional for S3-compatible)                                       |
| `credentials_encrypted` | `Text`              | No       | —       | AES-256-GCM encrypted JSON blob: `{"access_key": "...", "secret_key": "..."}` |
| `credentials_salt`      | `String(32)`        | No       | —       | Argon2id salt for credential encryption                                       |
| `credentials_nonce`     | `String(24)`        | No       | —       | GCM nonce for credential encryption                                           |
| `enabled`               | `Boolean`           | No       | `True`  | Whether this provider is active                                               |
| `created_at`            | `DateTime(tz=True)` | No       | `now()` |                                                                               |

**Validation rules**:

- `provider_type` must be one of `{'s3'}` (extensible)
- `bucket_name` max 63 chars (S3 limit)
- Credentials decrypted only in-memory via admin passphrase at connection time — never logged

---

## 4. AuditLogEntry (new table `backup_audit_log`)

Append-only (never updated or deleted by application code).

| Column         | Type                           | Nullable | Default | Description                                                                                                               |
| -------------- | ------------------------------ | -------- | ------- | ------------------------------------------------------------------------------------------------------------------------- |
| `id`           | `String(36)` PK                | No       | UUID    |                                                                                                                           |
| `occurred_at`  | `DateTime(tz=True)`            | No       | `now()` | Operation timestamp                                                                                                       |
| `operation`    | `String(50)`                   | No       | —       | e.g. `'backup.create'`, `'backup.restore'`, `'backup.delete'`, `'schedule.update'`, `'cloud.upload'`, `'integrity.check'` |
| `outcome`      | `String(20)`                   | No       | —       | `'success'` or `'failure'`                                                                                                |
| `backup_id`    | `String(36)` FK → `backups.id` | Yes      | NULL    | Associated backup (if applicable); nullable for schedule/config operations                                                |
| `performed_by` | `String(100)`                  | Yes      | NULL    | Username or `'scheduler'` for automated ops                                                                               |
| `detail`       | `JSON`                         | Yes      | NULL    | Operation-specific context (error message, size, provider name, etc.)                                                     |

**Validation rules**:

- `operation` is constrained to a known enum at service layer (not DB-level)
- `outcome` must be `'success'` or `'failure'`
- Rows are never deleted; retention enforcement is out of scope for v1

---

## 5. EncryptionKeyConfig (new table `encryption_key_configs`)

Stores per-system configuration metadata for encryption. Does NOT store the key itself.

| Column            | Type                | Nullable | Default         | Description                                                  |
| ----------------- | ------------------- | -------- | --------------- | ------------------------------------------------------------ |
| `id`              | `String(36)` PK     | No       | UUID            |                                                              |
| `is_enabled`      | `Boolean`           | No       | `False`         | Whether encryption is active for new backups                 |
| `algorithm`       | `String(20)`        | No       | `'AES-256-GCM'` | Encryption algorithm identifier                              |
| `kdf`             | `String(20)`        | No       | `'argon2id'`    | Key derivation function used                                 |
| `kdf_time_cost`   | `Integer`           | No       | `3`             | Argon2 time cost parameter                                   |
| `kdf_memory_cost` | `Integer`           | No       | `65536`         | Argon2 memory cost (64 MB)                                   |
| `kdf_parallelism` | `Integer`           | No       | `1`             | Argon2 parallelism                                           |
| `key_version`     | `Integer`           | No       | `1`             | Monotonically increasing; incremented on passphrase rotation |
| `rotated_at`      | `DateTime(tz=True)` | Yes      | NULL            | When last key rotation occurred                              |
| `created_at`      | `DateTime(tz=True)` | No       | `now()`         |                                                              |

**Notes**:

- The passphrase itself is never stored. Each `Backup` row stores its own `encryption_salt` and `encryption_nonce`.
- On key rotation, `key_version` increments and new backups use the new passphrase. Existing backups record their `key_version` in `backup_metadata["key_version"]` for lookup purposes.
- Add `key_version` to `Backup.backup_metadata` (JSON field — no migration column needed).

---

## Alembic Migration Plan

Single migration file: `XXXXXX_enhanced_backup_tables.py`

1. Add new columns to `backups` table (nullable with defaults — safe for existing rows)
2. Create `backup_schedules` table
3. Create `backup_storage_providers` table
4. Create `backup_audit_log` table
5. Create `encryption_key_configs` table
6. `apscheduler_jobs` table is managed by APScheduler itself (no Alembic step needed)
