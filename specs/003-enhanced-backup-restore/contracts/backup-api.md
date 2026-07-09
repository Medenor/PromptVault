# Contract: Backup REST API

**Feature Branch**: `003-enhanced-backup-restore`
**Date**: 2026-07-07

All endpoints require `Authorization: Bearer <JWT>` with admin role unless noted. Responses use `application/json`.

---

## Backup CRUD

### `GET /api/backups`

List all backups (newest first).

**Query params**:

- `tag` (string, optional) — filter by tag label
- `start_date` / `end_date` (ISO-8601, optional) — filter by `created_at`
- `kind` (`full` | `incremental`, optional)
- `limit` (int, default 50) / `offset` (int, default 0)

**Response 200**:

```json
{
  "backups": [
    {
      "backup_id": "backup_20260707_120000_000",
      "backup_kind": "full",
      "backup_type": "sqlite_copy",
      "filename": "backup_20260707_120000_000.db",
      "storage_path": "/data/backups/...",
      "timestamp": "2026-07-07T12:00:00Z",
      "size_bytes": 204800,
      "prompt_count": 42,
      "created_by": "admin",
      "is_encrypted": false,
      "checksum": "a3f1...",
      "integrity_verified_at": null,
      "cloud_provider_id": null,
      "cloud_path": null,
      "tags": ["before-migration"]
    }
  ],
  "total": 1
}
```

---

### `POST /api/backups`

Create a manual backup.

**Request body**:

```json
{
  "custom_name": "before-migration",
  "encrypt": false,
  "passphrase": "optional-if-encrypt-true",
  "cloud_provider_id": "uuid-or-null"
}
```

**Response 201**:

```json
{ "backup_id": "backup_...", "status": "created" }
```

**Errors**: `409` if another backup is already running.

---

### `GET /api/backups/{backup_id}`

Get metadata for a single backup.

**Response 200**: Single backup object (same shape as list item).
**Response 404**: Backup not found.

---

### `DELETE /api/backups/{backup_id}`

Delete a backup and its file.

**Response 200**: `{ "deleted": true }`
**Response 404**: Not found.

---

### `GET /api/backups/{backup_id}/download`

Download the backup file directly.

**Response 200**: `application/octet-stream` with `Content-Disposition: attachment`.

---

### `POST /api/backups/{backup_id}/tags`

Add or replace tags on a backup.

**Request body**: `{ "tags": ["label1", "label2"] }`
**Response 200**: `{ "tags": ["label1", "label2"] }`

---

## Restore

### `POST /api/backups/{backup_id}/restore-preview`

Compute and return a diff of what would change if this backup were restored.

**Request body**:

```json
{
  "passphrase": "optional-if-encrypted"
}
```

**Response 200**:

```json
{
  "backup_id": "backup_...",
  "summary": { "added": 5, "updated": 12, "deleted": 2 },
  "changes": {
    "added": [{ "id": "uuid", "title": "Prompt Title", "content": "..." }],
    "updated": [
      {
        "id": "uuid",
        "title": "Changed Title",
        "before": { "title": "Old Title", "content": "..." },
        "after": { "title": "Changed Title", "content": "..." }
      }
    ],
    "deleted": [{ "id": "uuid", "title": "Deleted Prompt" }]
  }
}
```

---

### `POST /api/backups/{backup_id}/restore`

Execute a restore. Optionally selective (subset of prompt IDs).

**Request body**:

```json
{
  "passphrase": "optional-if-encrypted",
  "prompt_ids": ["uuid1", "uuid2"]
}
```

If `prompt_ids` is omitted or empty, full restore is performed.

**Response 200**: `{ "restored": true, "pre_restore_backup_id": "backup_..." }`
**Response 409**: Restore already in progress.

---

## Integrity

### `POST /api/backups/{backup_id}/verify`

Manually trigger integrity check (re-computes SHA-256 and compares to stored checksum).

**Response 200**: `{ "valid": true, "checksum": "a3f1...", "verified_at": "2026-07-07T..." }`
**Response 200** (corrupt): `{ "valid": false, "expected": "a3f1...", "actual": "deadb...", "verified_at": "..." }`

---

## Schedule

### `GET /api/backup-schedule`

Get current schedule configuration.

**Response 200**:

```json
{
  "id": "uuid",
  "enabled": true,
  "frequency": "daily",
  "hour": 2,
  "minute": 0,
  "day_of_week": null,
  "day_of_month": null,
  "retention_days": 30,
  "encrypt_scheduled_backups": false,
  "cloud_provider_id": null,
  "last_run_at": "2026-07-06T02:00:00Z",
  "last_run_status": "success"
}
```

### `PUT /api/backup-schedule`

Create or update the schedule.

**Request body**: Same fields as response (omit `id`, `last_run_at`, `last_run_status`).
**Response 200**: Updated schedule object.

---

## Cloud Storage Providers

### `GET /api/backup-providers`

List configured cloud providers.

**Response 200**: `{ "providers": [ { "id": "uuid", "name": "My MinIO", "provider_type": "s3", "bucket_name": "...", "enabled": true } ] }`
Note: `credentials_encrypted` is never returned.

### `POST /api/backup-providers`

Configure a new provider.

**Request body**:

```json
{
  "name": "My MinIO",
  "provider_type": "s3",
  "endpoint_url": "http://minio:9000",
  "bucket_name": "promptvault-backups",
  "prefix": "backups/",
  "region": null,
  "access_key": "AKIAIOSFODNN7EXAMPLE",
  "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "credentials_passphrase": "admin-passphrase-for-encrypting-creds"
}
```

**Response 201**: Provider object (without credentials).

### `DELETE /api/backup-providers/{provider_id}`

Remove a provider (fails if any backup references it).

**Response 200**: `{ "deleted": true }`

### `POST /api/backup-providers/{provider_id}/test`

Test connectivity to the provider.

**Response 200**: `{ "success": true, "message": "Connected to bucket 'promptvault-backups'" }`

---

## Encryption Config

### `GET /api/backup-encryption`

Get encryption configuration (never returns passphrase).

**Response 200**:

```json
{
  "is_enabled": true,
  "algorithm": "AES-256-GCM",
  "kdf": "argon2id",
  "key_version": 1,
  "rotated_at": null
}
```

### `PUT /api/backup-encryption`

Enable/disable encryption or rotate key.

**Request body** (enable):

```json
{ "is_enabled": true, "passphrase": "my-secret-passphrase" }
```

**Request body** (rotate):

```json
{ "rotate_key": true, "old_passphrase": "old", "new_passphrase": "new" }
```

**Response 200**: Updated encryption config object.

---

## Monitoring & Audit

### `GET /api/backup-monitoring`

Dashboard summary statistics.

**Response 200**:

```json
{
  "total_backups": 45,
  "success_rate_30d": 0.98,
  "total_size_bytes": 10485760,
  "storage_quota_bytes": 104857600,
  "quota_warning": false,
  "last_backup_at": "2026-07-07T02:00:00Z",
  "last_backup_status": "success",
  "history": [
    { "date": "2026-07-07", "count": 1, "success": 1, "failure": 0, "total_size_bytes": 204800 }
  ]
}
```

### `GET /api/backup-audit-log`

Paginated audit log.

**Query params**: `limit` (default 50), `offset` (default 0), `operation` (filter), `outcome` (filter)

**Response 200**:

```json
{
  "entries": [
    {
      "id": "uuid",
      "occurred_at": "2026-07-07T02:00:00Z",
      "operation": "backup.create",
      "outcome": "success",
      "backup_id": "backup_...",
      "performed_by": "scheduler",
      "detail": { "size_bytes": 204800 }
    }
  ],
  "total": 123
}
```

---

## Retention / Cleanup

### `POST /api/backups/cleanup`

Delete backups older than the retention period (or dry-run).

**Request body** (form-encoded): `retention_days` (optional — defaults to the active schedule's `retention_days` if omitted), `dry_run` (default `true`)

**Response 200**:

```json
{
  "success": true,
  "dry_run": true,
  "removed_count": 2,
  "would_delete": ["backup_id_1", "backup_id_2"],
  "deleted": []
}
```

When `dry_run=false`, `deleted` contains the actually-removed IDs.
