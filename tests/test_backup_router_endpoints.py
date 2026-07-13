# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for new backup router endpoints (spec 003)."""

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest

from src.db.models import Backup
from src.db.models.backup_schedule import BackupSchedule
from src.db.models.backup_storage_provider import BackupStorageProvider
from src.db.models.encryption_key_config import EncryptionKeyConfig


@pytest.fixture
def api_client(api_client_context):
    return api_client_context["client"]


@pytest.fixture
def api_auth_headers(api_client_context) -> Dict[str, str]:
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-test-user-id",
        username="apiuser",
        email="api@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def api_admin_auth_headers(api_client_context) -> Dict[str, str]:
    from src.services.auth.jwt_service import JWTService
    from src.services.auth.password_service import PasswordService
    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.models.user_session import UserSession
    from src.db.session import SessionLocal

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("AdminP@ssw0rd123")

    test_session = SessionLocal()
    try:
        admin_user = test_session.query(User).filter_by(id="api-admin-backup-test-id").first()
        if not admin_user:
            admin_user = User(
                id="api-admin-backup-test-id",
                username="backupadmin",
                email="backupadmin@example.com",
                password_hash=password_hash,
                role="admin",
                is_active=True,
                email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            test_session.add(admin_user)
            test_session.flush()

            admin_session = UserSession(
                user_id=admin_user.id,
                family_id="api-admin-backup-test-family",
                refresh_token_jti="api-admin-backup-test-jti",
                ip_address="127.0.0.1",
                device_info="Test Agent",
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                is_revoked=False,
            )
            test_session.add(admin_session)
            test_session.commit()
    finally:
        test_session.close()

    jwt_service = JWTService(auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-admin-backup-test-id",
        username="backupadmin",
        email="backupadmin@example.com",
        role="admin",
    )
    return {"Authorization": f"Bearer {access_token}"}


class TestRestorePreview:
    def test_restore_preview_success(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]
        backup_db_path = os.path.join(temp_dir, "backups", "preview_test.db")
        conn = sqlite3.connect(backup_db_path)
        conn.execute("""
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY, title TEXT, content TEXT,
                note TEXT, favorite INTEGER, category_id INTEGER, semantic_version TEXT
            )
        """)
        conn.execute("INSERT INTO prompts VALUES (1, 'Test', 'Content', NULL, 0, NULL, '1.0')")
        conn.commit()
        conn.close()

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            backup = Backup(
                id="backup-preview-ep", backup_type="sqlite_copy",
                filename="preview_test.db", storage_path=backup_db_path,
                succeeded=True,
            )
            session.add(backup)
            session.commit()
        finally:
            session.close()

        resp = api_client.post(
            "/api/backups/backup-preview-ep/restore-preview",
            headers=api_admin_auth_headers,
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "changes" in data

    def test_restore_preview_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/nonexistent/restore-preview",
            headers=api_admin_auth_headers,
            json={},
        )
        assert resp.status_code == 404


class TestSelectiveRestore:
    def test_selective_restore_success(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]
        backup_db_path = os.path.join(temp_dir, "backups", "selective_test.db")
        conn = sqlite3.connect(backup_db_path)
        conn.execute("""
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY, title TEXT, content TEXT,
                note TEXT, favorite INTEGER, category_id INTEGER, semantic_version TEXT
            )
        """)
        conn.execute("INSERT INTO prompts VALUES (1, 'Test', 'Content', NULL, 0, NULL, '1.0')")
        conn.commit()
        conn.close()

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            backup = Backup(
                id="backup-selective-ep", backup_type="sqlite_copy",
                filename="selective_test.db", storage_path=backup_db_path,
                succeeded=True,
            )
            session.add(backup)
            session.commit()
        finally:
            session.close()

        resp = api_client.post(
            "/api/backups/backup-selective-ep/restore",
            headers=api_admin_auth_headers,
            json={"prompt_ids": [1]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["restored"] is True

    def test_selective_restore_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/nonexistent/restore",
            headers=api_admin_auth_headers,
            json={"prompt_ids": [1]},
        )
        assert resp.status_code in (404, 500)


class TestBackupSchedule:
    def test_get_schedule_not_found(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backup-schedule", headers=api_auth_headers)
        assert resp.status_code == 404

    def test_get_schedule_unauthenticated(self, api_client):
        resp = api_client.get("/api/backup-schedule")
        assert resp.status_code == 401

    def test_update_schedule_daily(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "daily", "hour": 3, "minute": 30},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "daily"
        assert data["hour"] == 3
        assert data["minute"] == 30

    def test_update_schedule_weekly(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "weekly", "hour": 2, "minute": 0, "day_of_week": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "weekly"
        assert data["day_of_week"] == 3

    def test_update_schedule_monthly(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "monthly", "hour": 1, "minute": 0, "day_of_month": 15},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "monthly"
        assert data["day_of_month"] == 15

    def test_update_schedule_invalid_frequency(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "yearly", "hour": 2, "minute": 0},
        )
        assert resp.status_code == 422

    def test_update_schedule_invalid_hour(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "daily", "hour": 25, "minute": 0},
        )
        assert resp.status_code == 422

    def test_update_schedule_invalid_minute(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "daily", "hour": 2, "minute": 60},
        )
        assert resp.status_code == 422

    def test_update_schedule_weekly_missing_day(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "weekly", "hour": 2, "minute": 0},
        )
        assert resp.status_code == 422

    def test_update_schedule_monthly_missing_day(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "monthly", "hour": 2, "minute": 0},
        )
        assert resp.status_code == 422

    def test_update_schedule_unauthenticated(self, api_client):
        resp = api_client.put(
            "/api/backup-schedule",
            json={"frequency": "daily", "hour": 2, "minute": 0},
        )
        assert resp.status_code in (401, 403)

    def test_get_schedule_after_create(self, api_client, api_admin_auth_headers, api_auth_headers):
        api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "daily", "hour": 4, "minute": 15},
        )
        resp = api_client.get("/api/backup-schedule", headers=api_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["frequency"] == "daily"
        assert data["hour"] == 4


class TestBackupEncryption:
    def test_get_encryption_default(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backup-encryption", headers=api_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_enabled"] is False
        assert data["algorithm"] == "AES-256-GCM"

    def test_enable_encryption(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"is_enabled": True, "passphrase": "test-passphrase-123"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_enabled"] is True
        assert data["key_version"] == 1

    def test_enable_encryption_no_passphrase(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"is_enabled": True, "passphrase": ""},
        )
        assert resp.status_code == 422

    def test_disable_encryption(self, api_client, api_admin_auth_headers):
        api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"is_enabled": True, "passphrase": "pass-123"},
        )
        resp = api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"is_enabled": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_enabled"] is False

    def test_rotate_key(self, api_client, api_admin_auth_headers):
        api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"is_enabled": True, "passphrase": "old-pass"},
        )
        resp = api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"rotate_key": True, "old_passphrase": "old-pass", "new_passphrase": "new-pass"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["key_version"] == 2

    def test_rotate_key_missing_passphrases(self, api_client, api_admin_auth_headers):
        resp = api_client.put(
            "/api/backup-encryption",
            headers=api_admin_auth_headers,
            json={"rotate_key": True, "old_passphrase": "", "new_passphrase": ""},
        )
        assert resp.status_code == 422

    def test_get_encryption_unauthenticated(self, api_client):
        resp = api_client.get("/api/backup-encryption")
        assert resp.status_code == 401


class TestBackupProviders:
    def test_list_providers_empty(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backup-providers", headers=api_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["providers"] == []

    def test_create_provider(self, api_client, api_admin_auth_headers, monkeypatch):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-creds-pass")
        resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={
                "name": "Test S3",
                "provider_type": "s3",
                "bucket_name": "my-bucket",
                "access_key": "AKIAIOSF000000000",
                "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test S3"
        assert data["bucket_name"] == "my-bucket"
        assert "credentials_encrypted" not in data

    def test_create_provider_missing_field(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={"name": "Test", "provider_type": "s3"},
        )
        assert resp.status_code == 422

    def test_create_provider_unsupported_type(self, api_client, api_admin_auth_headers, monkeypatch):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-creds-pass")
        resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={
                "name": "GDrive",
                "provider_type": "google_drive",
                "bucket_name": "bucket",
                "access_key": "ak",
                "secret_key": "sk",
            },
        )
        assert resp.status_code == 422

    def test_delete_provider(self, api_client, api_admin_auth_headers, monkeypatch):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-creds-pass")
        create_resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={
                "name": "ToDelete",
                "provider_type": "s3",
                "bucket_name": "b",
                "access_key": "ak",
                "secret_key": "sk",
            },
        )
        provider_id = create_resp.json()["id"]

        resp = api_client.delete(
            f"/api/backup-providers/{provider_id}",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_provider_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.delete(
            "/api/backup-providers/nonexistent-id",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 404

    def test_list_providers_unauthenticated(self, api_client):
        resp = api_client.get("/api/backup-providers")
        assert resp.status_code == 401


class TestManualBackupCloudUpload:
    def test_create_backup_with_cloud_provider_uploads(
        self, api_client, api_admin_auth_headers, monkeypatch
    ):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-creds-pass")
        create_provider_resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={
                "name": "Manual Upload Target",
                "provider_type": "s3",
                "bucket_name": "b",
                "access_key": "ak",
                "secret_key": "sk",
            },
        )
        provider_id = create_provider_resp.json()["id"]

        from src.services.backup_cloud_service import BackupCloudService

        called = {}

        def fake_upload_backup_by_id(self, backup_service, backup_id, provider_id_arg, log_prefix="backup"):
            called["backup_id"] = backup_id
            called["provider_id"] = provider_id_arg
            called["log_prefix"] = log_prefix
            return True

        monkeypatch.setattr(
            BackupCloudService, "upload_backup_by_id", fake_upload_backup_by_id
        )

        resp = api_client.post(
            "/api/backups",
            data={"name": "cloud-upload-backup", "cloud_provider_id": provider_id},
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert called["backup_id"] == resp.json()["backup_id"]
        assert called["provider_id"] == provider_id
        assert called["log_prefix"] == "backup.manual"

    def test_create_backup_without_cloud_provider_skips_upload(
        self, api_client, api_admin_auth_headers, monkeypatch
    ):
        from src.services.backup_cloud_service import BackupCloudService

        def fail_if_called(self, *args, **kwargs):
            raise AssertionError("upload_backup_by_id should not be called")

        monkeypatch.setattr(
            BackupCloudService, "upload_backup_by_id", fail_if_called
        )

        resp = api_client.post(
            "/api/backups",
            data={"name": "no-cloud-backup"},
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_create_backup_cloud_upload_failure_does_not_fail_request(
        self, api_client, api_admin_auth_headers, monkeypatch
    ):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-creds-pass")
        create_provider_resp = api_client.post(
            "/api/backup-providers",
            headers=api_admin_auth_headers,
            json={
                "name": "Broken Target",
                "provider_type": "s3",
                "bucket_name": "b",
                "access_key": "ak",
                "secret_key": "sk",
            },
        )
        provider_id = create_provider_resp.json()["id"]

        from src.services.backup_cloud_service import BackupCloudService

        def fake_upload_returns_false(self, backup_service, backup_id, provider_id_arg, log_prefix="backup"):
            return False

        monkeypatch.setattr(
            BackupCloudService, "upload_backup_by_id", fake_upload_returns_false
        )

        resp = api_client.post(
            "/api/backups",
            data={"name": "cloud-failure-backup", "cloud_provider_id": provider_id},
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestTestBackupProvider:
    def test_test_provider_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backup-providers/nonexistent-id/test",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 404


class TestBackupMonitoring:
    def test_get_monitoring(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backup-monitoring", headers=api_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_backups" in data
        assert "success_rate_30d" in data
        assert "total_size_bytes" in data
        assert "quota_warning" in data
        assert "history" in data

    def test_get_monitoring_unauthenticated(self, api_client):
        resp = api_client.get("/api/backup-monitoring")
        assert resp.status_code == 401


class TestBackupAuditLog:
    def test_get_audit_log_empty(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backup-audit-log", headers=api_auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["entries"] == []
        assert data["total"] == 0

    def test_get_audit_log_with_filters(self, api_client, api_auth_headers):
        resp = api_client.get(
            "/api/backup-audit-log",
            params={"operation": "backup.create", "outcome": "success"},
            headers=api_auth_headers,
        )
        assert resp.status_code == 200

    def test_get_audit_log_pagination(self, api_client, api_auth_headers):
        resp = api_client.get(
            "/api/backup-audit-log",
            params={"limit": 10, "offset": 0},
            headers=api_auth_headers,
        )
        assert resp.status_code == 200

    def test_get_audit_log_unauthenticated(self, api_client):
        resp = api_client.get("/api/backup-audit-log")
        assert resp.status_code == 401


class TestVerifyBackup:
    def test_verify_backup_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/nonexistent/verify",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 404

    def test_verify_backup_success(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]
        backup_path = os.path.join(temp_dir, "backups", "verify_test.db")
        with open(backup_path, "wb") as f:
            f.write(b"test backup data for verification")

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            import hashlib
            sha256 = hashlib.sha256()
            with open(backup_path, "rb") as f:
                sha256.update(f.read())
            expected_checksum = sha256.hexdigest()

            backup = Backup(
                id="backup-verify-ep", backup_type="sqlite_copy",
                filename="verify_test.db", storage_path=backup_path,
                succeeded=True, checksum=expected_checksum,
            )
            session.add(backup)
            session.commit()
        finally:
            session.close()

        resp = api_client.post(
            "/api/backups/backup-verify-ep/verify",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert "checksum" in data

    def test_verify_backup_checksum_mismatch(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]
        backup_path = os.path.join(temp_dir, "backups", "verify_mismatch.db")
        with open(backup_path, "wb") as f:
            f.write(b"test data")

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            backup = Backup(
                id="backup-verify-mismatch", backup_type="sqlite_copy",
                filename="verify_mismatch.db", storage_path=backup_path,
                succeeded=True, checksum="0000000000000000000000000000000000000000000000000000000000000000",
            )
            session.add(backup)
            session.commit()
        finally:
            session.close()

        resp = api_client.post(
            "/api/backups/backup-verify-mismatch/verify",
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False


class TestUpdateBackupTags:
    def test_update_tags_success(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            backup = Backup(
                id="backup-tags-ep", backup_type="sqlite_copy",
                filename="tags_test.db", storage_path=os.path.join(temp_dir, "tags_test.db"),
                succeeded=True,
            )
            session.add(backup)
            session.commit()
        finally:
            session.close()

        resp = api_client.post(
            "/api/backups/backup-tags-ep/tags",
            headers=api_admin_auth_headers,
            json={"tags": ["production", "weekly"]},
        )
        assert resp.status_code == 200
        assert resp.json()["tags"] == ["production", "weekly"]

    def test_update_tags_too_many(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/some-backup/tags",
            headers=api_admin_auth_headers,
            json={"tags": [f"tag-{i}" for i in range(21)]},
        )
        assert resp.status_code == 422

    def test_update_tags_too_long(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/some-backup/tags",
            headers=api_admin_auth_headers,
            json={"tags": ["a" * 65]},
        )
        assert resp.status_code == 422

    def test_update_tags_not_list(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/some-backup/tags",
            headers=api_admin_auth_headers,
            json={"tags": "not-a-list"},
        )
        assert resp.status_code == 422

    def test_update_tags_backup_not_found(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/nonexistent-backup/tags",
            headers=api_admin_auth_headers,
            json={"tags": ["test"]},
        )
        assert resp.status_code == 404


class TestCleanupBackupsRetention:
    def test_cleanup_dry_run_no_schedule(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/cleanup",
            headers=api_admin_auth_headers,
            data={"dry_run": "true"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert data["would_delete"] == []

    def test_cleanup_with_schedule(self, api_client, api_admin_auth_headers):
        api_client.put(
            "/api/backup-schedule",
            headers=api_admin_auth_headers,
            json={"frequency": "daily", "hour": 2, "minute": 0, "retention_days": 2},
        )
        resp = api_client.post(
            "/api/backups/cleanup",
            headers=api_admin_auth_headers,
            data={"dry_run": "true"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "would_delete" in data

    def test_cleanup_with_explicit_retention_days(self, api_client, api_admin_auth_headers):
        resp = api_client.post(
            "/api/backups/cleanup",
            headers=api_admin_auth_headers,
            data={"dry_run": "true", "retention_days": "1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["dry_run"] is True
        assert "would_delete" in data


class TestBackupListWithFilters:
    def test_list_backups_with_tag_filter(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]
        backups_dir = os.path.join(temp_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)

        tagged_path = os.path.join(backups_dir, "tagged.db")
        with open(tagged_path, "wb") as f:
            f.write(b"tagged backup")

        untagged_path = os.path.join(backups_dir, "untagged.db")
        with open(untagged_path, "wb") as f:
            f.write(b"untagged backup")

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            session.add(Backup(
                id="b-tagged", backup_type="sqlite_copy",
                filename="tagged.db", storage_path=tagged_path,
                succeeded=True, tags=["production", "daily"],
            ))
            session.add(Backup(
                id="b-untagged", backup_type="sqlite_copy",
                filename="untagged.db", storage_path=untagged_path,
                succeeded=True,
            ))
            session.commit()
        finally:
            session.close()

        resp = api_client.get(
            "/api/backups",
            params={"tag": "production"},
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_list_backups_with_kind_filter(self, api_client, api_admin_auth_headers, api_client_context):
        temp_dir = api_client_context["temp_dir"]

        from src.db.session import SessionLocal
        session = SessionLocal()
        try:
            session.add(Backup(
                id="b-daily-kind", backup_type="sqlite_copy",
                filename="daily.db", storage_path=os.path.join(temp_dir, "daily.db"),
                succeeded=True, backup_kind="daily",
            ))
            session.commit()
        finally:
            session.close()

        resp = api_client.get(
            "/api/backups",
            params={"kind": "daily"},
            headers=api_admin_auth_headers,
        )
        assert resp.status_code == 200

    def test_list_backups_unauthenticated(self, api_client):
        resp = api_client.get("/api/backups")
        assert resp.status_code == 401


class TestBackupStats:
    def test_get_stats_unauthenticated(self, api_client):
        resp = api_client.get("/api/backups/stats")
        assert resp.status_code == 401

    def test_get_stats_authenticated(self, api_client, api_auth_headers):
        resp = api_client.get("/api/backups/stats", headers=api_auth_headers)
        assert resp.status_code == 200
