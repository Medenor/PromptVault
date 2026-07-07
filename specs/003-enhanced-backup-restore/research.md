# Phase 0 Research: Enhanced Backup & Restore

**Feature Branch**: `003-enhanced-backup-restore`
**Date**: 2026-07-07

---

## R1 – Backup Scheduling Library

- **Decision**: Use APScheduler 3.x `CronTrigger` with `BackgroundScheduler`, extending the existing `src/scheduler/session_cleanup.py` pattern.
- **Rationale**: APScheduler 3.x is already a declared dependency (`apscheduler>=3.10.0`). `CronTrigger` natively supports daily/weekly/monthly schedules with configurable hour/minute. The existing `BackgroundScheduler` pattern used for session cleanup is directly reusable — just add a new job with a `CronTrigger` instead of `IntervalTrigger`. No new dependency needed.
- **Alternatives considered**: APScheduler 4.x has a redesigned async-first API but is not yet stable and would require a disruptive migration. Celery Beat adds a broker dependency (Redis/RabbitMQ) and significant operational overhead for a single scheduled task; overkill for this use case.

---

## R2 – Incremental Backup Strategy

- **Decision**: Application-level incremental backup via JSON snapshot diff of prompt records, storing only changed/added/deleted prompts since the last full backup.
- **Rationale**: The spec explicitly scopes "incremental" to prompt-level changes (title, content, tags) and the restore preview shows a "diff of prompts added, updated, deleted." WAL/pg_logical requires PostgreSQL streaming replication setup, superuser access, and is incompatible with SQLite — both databases must be supported. An application-level JSON diff is database-agnostic, self-contained, and directly supports the restore preview feature (FR-017). Each incremental backup stores: a reference to the parent full backup ID, and a delta payload `{added: [...], updated: [...], deleted: [...]}` of serialized `Prompt` records.
- **Alternatives considered**: WAL-based (pg_basebackup, pg_logical) is robust for pure PostgreSQL but adds infra complexity and breaks SQLite support. Filesystem-level snapshotting (ZFS, LVM) is infra-dependent and out of scope for a self-hosted app.

---

## R3 – Encryption Approach

- **Decision**: AES-256-GCM via `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
- **Rationale**: AES-256-GCM provides authenticated encryption (confidentiality + integrity in one operation), making a separate HMAC unnecessary. The `cryptography` library is already installed (`cryptography>=41.0.0`). AES-256-GCM is the NIST/OWASP preferred mode for file encryption. The encryption layer wraps the entire backup file (bytes → encrypted bytes) before writing to disk, so cloud-stored backups are always encrypted (satisfies FR-010 and FR-013/scenario 4). A random 96-bit nonce is prepended to the ciphertext for each backup.
- **Alternatives considered**: Fernet uses AES-128-CBC + HMAC-SHA256, which is secure but limited to 128-bit keys and less composable for key rotation. `age` requires an external CLI binary, introducing a runtime dependency that may not be present in all deployment environments.

---

## R4 – Cloud Storage SDK

- **Decision**: `boto3` (AWS S3 / S3-compatible) as the v1 cloud provider.
- **Rationale**: S3-compatible APIs (AWS S3, MinIO, Backblaze B2, Cloudflare R2) are the widest-reach target: one SDK covers self-hosted (MinIO) and multiple commercial providers. `boto3` is the most battle-tested Python cloud storage library, has excellent mocking support (`moto` for tests), and the `upload_fileobj` / `download_fileobj` API is straightforward. Self-hostable MinIO makes integration tests runnable in CI without real AWS credentials.
- **Alternatives considered**: `google-api-python-client` for Google Drive requires OAuth2 browser flow, complicating server-side auth. The `dropbox` SDK is vendor-locked and has lower adoption in self-hosted contexts. Both can be added in v2 behind the `BackupStorageProvider` abstraction.

---

## R5 – Backup Integrity / Checksum

- **Decision**: SHA-256 stored as a hex digest in `Backup.backup_metadata["checksum"]` and in the sidecar `_metadata.json` file.
- **Rationale**: SHA-256 is the NIST-recommended general-purpose hash for integrity verification — fast enough to hash multi-MB backup files synchronously, collision-resistant, and universally available in Python's `hashlib` (no extra dependency). The verification flow reads the backup file post-creation, computes SHA-256, stores the digest; re-verification re-computes and compares. For encrypted backups, the checksum is computed on the **ciphertext** (so the stored hash matches what is on disk/cloud).
- **Alternatives considered**: MD5 is cryptographically broken and inappropriate even for integrity use. SHA-512 is slower with no meaningful benefit at backup file sizes (<1 GB typical). BLAKE3 is faster but requires a third-party library (`blake3` package).

---

## R6 – Key Storage Security

- **Decision**: Derive the AES-256 encryption key from the admin's passphrase using Argon2id (via `argon2-cffi`, already installed). The derived key is used directly and never stored. A random 128-bit salt (per backup) is stored in plaintext in backup metadata.
- **Rationale**: Deriving the key from the passphrase means no key material is stored anywhere — the passphrase itself is the secret (satisfies FR-012 "MUST NOT store in plaintext"). Argon2id is already the project's password hashing algorithm (Constitution §III), so the dependency is zero-cost. Key rotation: when the admin rotates to a new passphrase, they provide the old passphrase (to decrypt) and the new passphrase (to re-encrypt) for each existing backup, or accept that old backups remain accessible only with the old passphrase (spec FR-011: "existing backups remain accessible with their original key"). The salt + nonce per backup means each encrypted file is independently keyed even if the same passphrase is reused.
- **Alternatives considered**: AES key-encryption-key (KEK) pattern still requires storing the KEK somewhere securely, deferring the problem. OS keyring (macOS Keychain, Linux Secret Service) is not portable to Docker/server deployments. HashiCorp Vault is high-overhead for a self-hosted single-server app.

---

## R7 – APScheduler Persistence for Crash Recovery

- **Decision**: Use `apscheduler.jobstores.sqlalchemy.SQLAlchemyJobStore` backed by the existing SQLAlchemy `DATABASE_URL`, storing jobs in a table named `apscheduler_jobs`.
- **Rationale**: APScheduler 3.x `SQLAlchemyJobStore` creates a single table (`apscheduler_jobs` by default) managed entirely by APScheduler — no Alembic migration needed since APScheduler calls `metadata.create_all()` on startup. This means scheduled backup jobs survive server restarts: on startup, `BackgroundScheduler` reloads jobs from the DB and re-arms triggers. The `BackupSchedule` config entity (stored in the application's own table) drives whether the APScheduler job is registered; on app startup, the service reads `BackupSchedule` records and re-registers any enabled schedules into APScheduler.
- **Alternatives considered**: In-memory jobstore (default) loses all jobs on restart — unacceptable for a "99%+ reliability" schedule (SC-002). File-based jobstore requires a separate file path and is not suitable for PostgreSQL deployments. A fully custom cron implementation in the app's own DB would duplicate APScheduler's trigger logic.
