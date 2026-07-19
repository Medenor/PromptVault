# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for BackupAuditService."""

import pytest
from datetime import datetime, timezone, timedelta

from src.db.models import Backup
from src.services.backup_audit_service import BackupAuditService


class TestLog:
    def test_log_creates_entry(self, audit_service):
        audit_service.log(
            operation="backup.create",
            outcome="success",
            performed_by="admin",
        )
        result = audit_service.get_log()
        assert result["total"] == 1
        assert result["entries"][0]["operation"] == "backup.create"
        assert result["entries"][0]["outcome"] == "success"
        assert result["entries"][0]["performed_by"] == "admin"

    def test_log_with_backup_id(self, audit_service, patched_db_session):
        with patched_db_session() as session:
            backup = Backup(
                id="backup-for-audit",
                backup_type="sqlite_copy",
                filename="test.db",
                storage_path="/tmp/test.db",
            )
            session.add(backup)
            session.commit()

        audit_service.log(
            operation="backup.restore",
            outcome="success",
            backup_id="backup-for-audit",
            performed_by="admin",
        )
        result = audit_service.get_log()
        assert result["entries"][0]["backup_id"] == "backup-for-audit"

    def test_log_with_detail(self, audit_service):
        audit_service.log(
            operation="backup.delete",
            outcome="success",
            detail={"reason": "retention policy"},
        )
        result = audit_service.get_log()
        assert result["entries"][0]["detail"] == {"reason": "retention policy"}

    def test_log_failure_outcome(self, audit_service):
        audit_service.log(
            operation="backup.create",
            outcome="failure",
            detail={"error": "disk full"},
        )
        result = audit_service.get_log()
        assert result["entries"][0]["outcome"] == "failure"

    def test_log_swallows_db_errors(self, audit_service, monkeypatch):
        from src.db import session as session_module

        def bad_session():
            raise RuntimeError("DB connection lost")

        @property
        def ctx(self):
            raise RuntimeError("DB connection lost")

        original = session_module.get_db_session
        monkeypatch.setattr(session_module, "get_db_session", bad_session)

        audit_service.log(operation="backup.create", outcome="success")

        monkeypatch.setattr(session_module, "get_db_session", original)


class TestGetLog:
    def test_empty_log(self, audit_service):
        result = audit_service.get_log()
        assert result["entries"] == []
        assert result["total"] == 0

    def test_pagination(self, audit_service):
        for i in range(5):
            audit_service.log(operation="backup.create", outcome="success")

        result = audit_service.get_log(limit=2, offset=0)
        assert len(result["entries"]) == 2
        assert result["total"] == 5

        result2 = audit_service.get_log(limit=2, offset=2)
        assert len(result2["entries"]) == 2
        assert result2["total"] == 5

        result3 = audit_service.get_log(limit=2, offset=4)
        assert len(result3["entries"]) == 1
        assert result3["total"] == 5

    def test_filter_by_operation(self, audit_service):
        audit_service.log(operation="backup.create", outcome="success")
        audit_service.log(operation="backup.restore", outcome="success")
        audit_service.log(operation="backup.create", outcome="failure")

        result = audit_service.get_log(operation="backup.create")
        assert result["total"] == 2
        for entry in result["entries"]:
            assert entry["operation"] == "backup.create"

    def test_filter_by_outcome(self, audit_service):
        audit_service.log(operation="backup.create", outcome="success")
        audit_service.log(operation="backup.create", outcome="failure")
        audit_service.log(operation="backup.restore", outcome="success")

        result = audit_service.get_log(outcome="failure")
        assert result["total"] == 1
        assert result["entries"][0]["outcome"] == "failure"

    def test_filter_by_operation_and_outcome(self, audit_service):
        audit_service.log(operation="backup.create", outcome="success")
        audit_service.log(operation="backup.create", outcome="failure")
        audit_service.log(operation="backup.restore", outcome="success")

        result = audit_service.get_log(operation="backup.create", outcome="success")
        assert result["total"] == 1

    def test_entries_ordered_newest_first(self, audit_service, patched_db_session):
        import time

        audit_service.log(operation="op1", outcome="success")
        time.sleep(1.1)
        audit_service.log(operation="op2", outcome="success")
        time.sleep(1.1)
        audit_service.log(operation="op3", outcome="success")

        result = audit_service.get_log()
        ops = [e["operation"] for e in result["entries"]]
        assert ops == ["op3", "op2", "op1"]

    def test_serialize_entry_fields(self, audit_service):
        audit_service.log(
            operation="backup.create",
            outcome="success",
            backup_id=None,
            performed_by="scheduler",
            detail={"kind": "daily"},
        )
        entry = audit_service.get_log()["entries"][0]
        assert "id" in entry
        assert "occurred_at" in entry
        assert entry["operation"] == "backup.create"
        assert entry["outcome"] == "success"
        assert entry["performed_by"] == "scheduler"
        assert entry["detail"] == {"kind": "daily"}


class TestGetDashboardStats:
    def test_empty_dashboard(self, audit_service):
        stats = audit_service.get_dashboard_stats()
        assert stats["total_backups"] == 0
        assert stats["success_rate_30d"] == 1.0
        assert stats["total_size_bytes"] == 0
        assert stats["quota_warning"] is False
        assert stats["last_backup_at"] is None
        assert stats["last_backup_status"] is None
        assert stats["history"] == []
        assert stats["storage_quota_bytes"] == 10 * 1024 * 1024 * 1024

    def test_dashboard_with_backups(self, audit_service, patched_db_session):
        now = datetime.now(timezone.utc)
        with patched_db_session() as session:
            for i in range(3):
                backup = Backup(
                    id=f"backup-dash-{i}",
                    backup_type="sqlite_copy",
                    filename=f"backup_{i}.db",
                    storage_path=f"/tmp/backup_{i}.db",
                    size_bytes=1024 * (i + 1),
                    succeeded=True,
                    created_at=now - timedelta(days=i),
                )
                session.add(backup)
            session.commit()

        stats = audit_service.get_dashboard_stats()
        assert stats["total_backups"] == 3
        assert stats["success_rate_30d"] == 1.0
        assert stats["total_size_bytes"] == 1024 + 2048 + 3072
        assert stats["last_backup_at"] is not None
        assert stats["last_backup_status"] == "success"

    def test_dashboard_quota_warning(self, audit_service, patched_db_session):
        with patched_db_session() as session:
            backup = Backup(
                id="backup-huge",
                backup_type="sqlite_copy",
                filename="huge.db",
                storage_path="/tmp/huge.db",
                size_bytes=10 * 1024 * 1024 * 1024,
                succeeded=True,
            )
            session.add(backup)
            session.commit()

        stats = audit_service.get_dashboard_stats()
        assert stats["quota_warning"] is True

    def test_dashboard_mixed_success_rate(self, audit_service, patched_db_session):
        now = datetime.now(timezone.utc)
        with patched_db_session() as session:
            session.add(
                Backup(
                    id="b-ok",
                    backup_type="sqlite_copy",
                    filename="ok.db",
                    storage_path="/tmp/ok.db",
                    succeeded=True,
                    created_at=now - timedelta(days=1),
                )
            )
            session.add(
                Backup(
                    id="b-fail",
                    backup_type="sqlite_copy",
                    filename="fail.db",
                    storage_path="/tmp/fail.db",
                    succeeded=False,
                    created_at=now - timedelta(days=2),
                )
            )
            session.commit()

        stats = audit_service.get_dashboard_stats()
        assert stats["success_rate_30d"] == 0.5

    def test_dashboard_history(self, audit_service, patched_db_session):
        now = datetime.now(timezone.utc)
        with patched_db_session() as session:
            session.add(
                Backup(
                    id="b-h1",
                    backup_type="sqlite_copy",
                    filename="h1.db",
                    storage_path="/tmp/h1.db",
                    succeeded=True,
                    size_bytes=100,
                    created_at=now,
                )
            )
            session.add(
                Backup(
                    id="b-h2",
                    backup_type="sqlite_copy",
                    filename="h2.db",
                    storage_path="/tmp/h2.db",
                    succeeded=False,
                    size_bytes=200,
                    created_at=now,
                )
            )
            session.commit()

        stats = audit_service.get_dashboard_stats()
        assert len(stats["history"]) >= 1
        today_entry = stats["history"][-1]
        assert today_entry["count"] == 2
        assert today_entry["success"] == 1
        assert today_entry["failure"] == 1
        assert today_entry["total_size_bytes"] == 300

    def test_dashboard_last_backup_failure_status(
        self, audit_service, patched_db_session
    ):
        with patched_db_session() as session:
            session.add(
                Backup(
                    id="b-last-fail",
                    backup_type="sqlite_copy",
                    filename="f.db",
                    storage_path="/tmp/f.db",
                    succeeded=False,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

        stats = audit_service.get_dashboard_stats()
        assert stats["last_backup_status"] == "failure"
