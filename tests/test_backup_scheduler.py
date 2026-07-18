# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for src.scheduler.backup_scheduler.register_backup_jobs."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from src.scheduler.backup_scheduler import register_backup_jobs


def _session_cm(session):
    @contextmanager
    def _cm():
        yield session

    return _cm()


class TestRegisterBackupJobs:
    def test_register_backup_jobs_with_active_schedule_registers_job(self, caplog):
        schedule = MagicMock(
            enabled=True,
            frequency="daily",
            hour=3,
            minute=30,
            day_of_week=None,
            day_of_month=None,
        )
        mock_repo = MagicMock()
        mock_repo.get_active.return_value = schedule
        mock_session = MagicMock()

        with patch(
            "src.scheduler.backup_scheduler.get_db_session",
            return_value=_session_cm(mock_session),
        ), patch(
            "src.scheduler.backup_scheduler.BackupScheduleRepository",
            return_value=mock_repo,
        ), patch(
            "src.services.backup_scheduler_service.BackupSchedulerService"
        ) as mock_service_cls:
            mock_service = MagicMock()
            mock_service_cls.return_value = mock_service

            with caplog.at_level("INFO"):
                register_backup_jobs()

            mock_service._register_job.assert_called_once_with(
                {
                    "frequency": "daily",
                    "hour": 3,
                    "minute": 30,
                    "day_of_week": None,
                    "day_of_month": None,
                    "enabled": True,
                }
            )

        assert any(
            getattr(record, "event", None) == "backup.schedule.loaded"
            for record in caplog.records
        )

    def test_register_backup_jobs_with_no_active_schedule_skips_registration(self, caplog):
        mock_repo = MagicMock()
        mock_repo.get_active.return_value = None
        mock_session = MagicMock()

        with patch(
            "src.scheduler.backup_scheduler.get_db_session",
            return_value=_session_cm(mock_session),
        ), patch(
            "src.scheduler.backup_scheduler.BackupScheduleRepository",
            return_value=mock_repo,
        ), patch(
            "src.services.backup_scheduler_service.BackupSchedulerService"
        ) as mock_service_cls:
            with caplog.at_level("INFO"):
                register_backup_jobs()

            mock_service_cls.return_value._register_job.assert_not_called()

        assert any(
            getattr(record, "event", None) == "backup.schedule.none"
            for record in caplog.records
        )

    def test_register_backup_jobs_with_disabled_schedule_skips_registration(self, caplog):
        schedule = MagicMock(enabled=False)
        mock_repo = MagicMock()
        mock_repo.get_active.return_value = schedule
        mock_session = MagicMock()

        with patch(
            "src.scheduler.backup_scheduler.get_db_session",
            return_value=_session_cm(mock_session),
        ), patch(
            "src.scheduler.backup_scheduler.BackupScheduleRepository",
            return_value=mock_repo,
        ), patch(
            "src.services.backup_scheduler_service.BackupSchedulerService"
        ) as mock_service_cls:
            with caplog.at_level("INFO"):
                register_backup_jobs()

            mock_service_cls.return_value._register_job.assert_not_called()

        assert any(
            getattr(record, "event", None) == "backup.schedule.none"
            for record in caplog.records
        )

    def test_register_backup_jobs_on_repository_error_logs_and_does_not_raise(self, caplog):
        with patch(
            "src.scheduler.backup_scheduler.get_db_session",
            side_effect=RuntimeError("db unavailable"),
        ):
            with caplog.at_level("ERROR"):
                register_backup_jobs()  # must not raise

        assert any(
            getattr(record, "event", None) == "backup.schedule.load_failure"
            for record in caplog.records
        )
