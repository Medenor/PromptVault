# Quickstart: Validate Enhanced Backup & Restore

**Feature Branch**: `003-enhanced-backup-restore`
**Date**: 2026-07-07

This guide describes runnable validation scenarios that prove the feature works end-to-end. See [contracts/backup-api.md](./contracts/backup-api.md) for full API shapes and [data-model.md](./data-model.md) for entity details.

---

## Prerequisites

1. App running: `python run_web.py` (or `make dev`)
2. `AUTH_ENABLED=true` in `.env`, an admin account exists
3. Obtain a JWT token: `POST /api/auth/login` → `{"access_token": "..."}`
4. Set shell variable: `TOKEN=<access_token>`
5. For cloud tests: MinIO running locally (see docker-compose.yml or `docker run -p 9000:9000 minio/minio server /data`)
6. Database migrated: `alembic upgrade head`

---

## Scenario 1 — Manual Backup & Integrity Verification

**Validates**: FR-001 (manual creation), FR-007/FR-008 (checksum), SC-008 (integrity detection)

```bash
# Create a backup
curl -s -X POST http://localhost:8080/api/backups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_name": "quickstart-test"}' | jq .
# Expected: {"backup_id": "backup_quickstart-test", "status": "created"}

# Verify integrity
BACKUP_ID="backup_quickstart-test"
curl -s -X POST http://localhost:8080/api/backups/$BACKUP_ID/verify \
  -H "Authorization: Bearer $TOKEN" | jq .
# Expected: {"valid": true, "checksum": "<sha256>", "verified_at": "..."}
```

---

## Scenario 2 — Scheduled Backup

**Validates**: FR-001 through FR-004, SC-001, SC-002

```bash
# Configure daily schedule at 02:00 UTC
curl -s -X PUT http://localhost:8080/api/backup-schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "frequency": "daily", "hour": 2, "minute": 0,
       "retention_daily_count": 7, "retention_weekly_count": 4, "retention_monthly_count": 12,
       "encrypt_scheduled_backups": false}' | jq .
# Expected: schedule object with enabled=true

# Confirm schedule is active (verify last_run_at advances after trigger)
curl -s http://localhost:8080/api/backup-schedule \
  -H "Authorization: Bearer $TOKEN" | jq '.last_run_status'

# Disable schedule
curl -s -X PUT http://localhost:8080/api/backup-schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"enabled": false, "frequency": "daily", "hour": 2, "minute": 0}' | jq '.enabled'
# Expected: false
```

For automated test: use `freezegun` to mock time and trigger the APScheduler job directly in a pytest fixture rather than waiting.

---

## Scenario 3 — Encrypted Backup & Restore

**Validates**: FR-010, FR-011, FR-012, SC-007

```bash
# Enable encryption
curl -s -X PUT http://localhost:8080/api/backup-encryption \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true, "passphrase": "test-passphrase-123"}' | jq .

# Create encrypted backup
BACKUP_ID=$(curl -s -X POST http://localhost:8080/api/backups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_name": "encrypted-test", "encrypt": true, "passphrase": "test-passphrase-123"}' \
  | jq -r '.backup_id')

# Confirm is_encrypted=true
curl -s http://localhost:8080/api/backups/$BACKUP_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.is_encrypted'
# Expected: true

# Confirm file is unreadable without passphrase (attempt to read raw bytes)
BACKUP_PATH=$(curl -s http://localhost:8080/api/backups/$BACKUP_ID \
  -H "Authorization: Bearer $TOKEN" | jq -r '.storage_path')
file "$BACKUP_PATH"
# Expected: binary/encrypted — NOT "SQLite" or "SQL text"

# Restore with correct passphrase
curl -s -X POST http://localhost:8080/api/backups/$BACKUP_ID/restore-preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"passphrase": "test-passphrase-123"}' | jq '.summary'
# Expected: {"added": 0, "updated": 0, "deleted": 0} (no changes since backup was just made)
```

---

## Scenario 4 — Cloud Upload & Restore from Cloud (S3/MinIO)

**Validates**: FR-013 through FR-016, SC-006

```bash
# Configure MinIO provider
PROVIDER_ID=$(curl -s -X POST http://localhost:8080/api/backup-providers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local MinIO",
    "provider_type": "s3",
    "endpoint_url": "http://localhost:9000",
    "bucket_name": "promptvault-test",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "credentials_passphrase": "admin-creds-passphrase"
  }' | jq -r '.id')

# Test connectivity
curl -s -X POST http://localhost:8080/api/backup-providers/$PROVIDER_ID/test \
  -H "Authorization: Bearer $TOKEN" | jq '.success'
# Expected: true

# Create backup with cloud upload
BACKUP_ID=$(curl -s -X POST http://localhost:8080/api/backups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"custom_name\": \"cloud-test\", \"cloud_provider_id\": \"$PROVIDER_ID\"}" \
  | jq -r '.backup_id')

# Verify cloud upload recorded
curl -s http://localhost:8080/api/backups/$BACKUP_ID \
  -H "Authorization: Bearer $TOKEN" | jq '{cloud_path, cloud_uploaded_at}'
# Expected: cloud_path != null, cloud_uploaded_at != null

# Confirm local copy retained (FR-015)
curl -s http://localhost:8080/api/backups/$BACKUP_ID \
  -H "Authorization: Bearer $TOKEN" | jq '.storage_path'
# Expected: non-null local path
```

---

## Scenario 5 — Restore Preview & Selective Restore

**Validates**: FR-017, FR-018, SC-004

```bash
# 1. Create a clean backup
BACKUP_ID=$(curl -s -X POST http://localhost:8080/api/backups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"custom_name": "before-changes"}' | jq -r '.backup_id')

# 2. Make some changes via the UI or API (add/edit/delete prompts)

# 3. Preview what restoring the backup would do
curl -s -X POST http://localhost:8080/api/backups/$BACKUP_ID/restore-preview \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq '.summary'
# Expected: {"added": N, "updated": M, "deleted": K}

# 4. Selective restore — only restore specific prompts
curl -s -X POST http://localhost:8080/api/backups/$BACKUP_ID/restore \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt_ids": ["uuid-of-prompt-to-restore"]}' | jq .
# Expected: {"restored": true, "pre_restore_backup_id": "..."}

# 5. Verify audit log recorded the restore
curl -s "http://localhost:8080/api/backup-audit-log?operation=backup.restore" \
  -H "Authorization: Bearer $TOKEN" | jq '.entries[0]'
# Expected: operation=backup.restore, outcome=success
```

---

## Scenario 6 — Monitoring Dashboard & Audit Log

**Validates**: FR-023, FR-024, FR-025, SC-005

```bash
# View dashboard
curl -s http://localhost:8080/api/backup-monitoring \
  -H "Authorization: Bearer $TOKEN" | jq '{total_backups, success_rate_30d, quota_warning}'
# Expected: counts match actual backup history

# All ops in audit log
curl -s "http://localhost:8080/api/backup-audit-log?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.entries | length'
# Expected: >= number of operations performed in this session

# Every backup operation from above should appear
curl -s "http://localhost:8080/api/backup-audit-log" \
  -H "Authorization: Bearer $TOKEN" | jq '[.entries[].operation] | unique'
# Expected includes: "backup.create", "backup.restore", "integrity.check"
```

---

## Scenario 7 — Retention Cleanup Dry Run

**Validates**: FR-019, FR-020

```bash
# Dry-run cleanup (preview which would be deleted)
curl -s -X POST http://localhost:8080/api/backups/cleanup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}' | jq .
# Expected: {"dry_run": true, "would_delete": [...], "deleted": []}

# Execute cleanup
curl -s -X POST http://localhost:8080/api/backups/cleanup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}' | jq '.deleted | length'
# Expected: same count as would_delete above
```

---

## Running the Test Suite

```bash
# Backend unit + integration tests
python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Coverage must be ≥85% (enforced in pytest.ini)

# Frontend type-check and lint
npm run typecheck && npm run lint

# Frontend unit tests with coverage
npm run test:unit:coverage
```
