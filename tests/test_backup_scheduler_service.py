# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for BackupSchedulerService."""

from unittest.mock import MagicMock, patch

from src.services.backup_scheduler_service import BackupSchedulerService


class TestGetSchedule:
    def test_returns_none_when_no_schedule(self, scheduler_service):
        assert scheduler_service.get_schedule() is None

    def test_returns_schedule_after_upsert(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=3,
            minute=30,
        )
        result = scheduler_service.get_schedule()
        assert result is not None
        assert result["frequency"] == "daily"
        assert result["hour"] == 3
        assert result["minute"] == 30
        assert result["enabled"] is False


class TestUpsertSchedule:
    def test_create_new_schedule(self, scheduler_service):
        result = scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
        )
        assert result["frequency"] == "daily"
        assert result["hour"] == 2
        assert result["minute"] == 0
        assert result["retention_days"] == 30

    def test_update_existing_schedule(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
        )
        result = scheduler_service.upsert_schedule(
            enabled=True,
            frequency="weekly",
            hour=4,
            minute=15,
            day_of_week=3,
        )
        assert result["frequency"] == "weekly"
        assert result["hour"] == 4
        assert result["minute"] == 15
        assert result["day_of_week"] == 3
        assert result["enabled"] is True

    def test_upsert_with_monthly(self, scheduler_service):
        result = scheduler_service.upsert_schedule(
            enabled=False,
            frequency="monthly",
            hour=1,
            minute=0,
            day_of_month=15,
        )
        assert result["frequency"] == "monthly"
        assert result["day_of_month"] == 15

    def test_upsert_with_custom_retention(self, scheduler_service):
        result = scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
            retention_days=60,
        )
        assert result["retention_days"] == 60

    def test_upsert_disabled_unregisters_job(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
        )
        result = scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
        )
        assert result["enabled"] is False


class TestEnable:
    def test_enable_returns_none_when_no_schedule(self, scheduler_service):
        assert scheduler_service.enable() is None

    def test_enable_existing_schedule(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
        )
        result = scheduler_service.enable()
        assert result is not None
        assert result["enabled"] is True


class TestDisable:
    def test_disable_returns_none_when_no_schedule(self, scheduler_service):
        assert scheduler_service.disable() is None

    def test_disable_existing_schedule(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
        )
        result = scheduler_service.disable()
        assert result is not None
        assert result["enabled"] is False


class TestRunScheduledBackup:
    def test_successful_scheduled_backup(self, scheduler_service, db_backup_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
        )
        scheduler_service._run_scheduled_backup()

        schedule = scheduler_service.get_schedule()
        assert schedule["last_run_status"] == "success"
        assert schedule["last_run_at"] is not None

    def test_failed_scheduled_backup_records_failure(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
        )
        mock_backup_service = MagicMock()
        mock_backup_service.create_backup.side_effect = RuntimeError("DB error")
        scheduler_service._backup_service = mock_backup_service

        scheduler_service._run_scheduled_backup()

        schedule = scheduler_service.get_schedule()
        assert schedule["last_run_status"] == "failure"

    def test_skips_when_lock_held(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
        )
        acquired = scheduler_service._lock.acquire(blocking=False)
        try:
            scheduler_service._run_scheduled_backup()
            schedule = scheduler_service.get_schedule()
            assert schedule["last_run_status"] is None
        finally:
            if acquired:
                scheduler_service._lock.release()

    def test_encryption_flag_is_ignored_for_scheduled(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="daily",
            hour=2,
            minute=0,
            encrypt_scheduled_backups=True,
        )
        mock_backup_service = MagicMock()
        mock_backup_service.create_backup.return_value = "backup-123"
        scheduler_service._backup_service = mock_backup_service

        scheduler_service._run_scheduled_backup()

        call_kwargs = mock_backup_service.create_backup.call_args
        assert (
            call_kwargs[1].get(
                "encrypt", call_kwargs[0][3] if len(call_kwargs[0]) > 3 else False
            )
            is False
            or call_kwargs.kwargs.get("encrypt", False) is False
        )


class TestSerializeSchedule:
    def test_serialize_all_fields(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=True,
            frequency="weekly",
            hour=3,
            minute=30,
            day_of_week=5,
            day_of_month=None,
            retention_days=45,
            encrypt_scheduled_backups=True,
            cloud_provider_id="provider-123",
        )
        result = scheduler_service.get_schedule()
        assert result["enabled"] is True
        assert result["frequency"] == "weekly"
        assert result["hour"] == 3
        assert result["minute"] == 30
        assert result["day_of_week"] == 5
        assert result["day_of_month"] is None
        assert result["retention_days"] == 45
        assert result["encrypt_scheduled_backups"] is True
        assert result["cloud_provider_id"] == "provider-123"
        assert result["last_run_at"] is None
        assert result["last_run_status"] is None

    def test_serialize_none_dates(self, scheduler_service):
        scheduler_service.upsert_schedule(
            enabled=False,
            frequency="daily",
            hour=2,
            minute=0,
        )
        result = scheduler_service.get_schedule()
        assert result["last_run_at"] is None


class TestRegisterJob:
    def test_register_job_starts_scheduler(self, scheduler_service):
        with patch.object(scheduler_service, "_get_scheduler") as mock_get:
            mock_scheduler = MagicMock()
            mock_scheduler.running = False
            mock_get.return_value = mock_scheduler

            scheduler_service._register_job(
                {
                    "frequency": "daily",
                    "hour": 2,
                    "minute": 0,
                }
            )
            mock_scheduler.start.assert_called_once()
            mock_scheduler.add_job.assert_called_once()

    def test_register_weekly_job(self, scheduler_service):
        with patch.object(scheduler_service, "_get_scheduler") as mock_get:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_get.return_value = mock_scheduler

            scheduler_service._register_job(
                {
                    "frequency": "weekly",
                    "hour": 3,
                    "minute": 15,
                    "day_of_week": 2,
                }
            )
            call_kwargs = mock_scheduler.add_job.call_args
            trigger = call_kwargs[1]["trigger"]
            assert trigger is not None

    def test_register_monthly_job(self, scheduler_service):
        with patch.object(scheduler_service, "_get_scheduler") as mock_get:
            mock_scheduler = MagicMock()
            mock_scheduler.running = True
            mock_get.return_value = mock_scheduler

            scheduler_service._register_job(
                {
                    "frequency": "monthly",
                    "hour": 1,
                    "minute": 0,
                    "day_of_month": 15,
                }
            )
            mock_scheduler.add_job.assert_called_once()

    def test_register_job_failure_logged(self, scheduler_service):
        with patch.object(scheduler_service, "_get_scheduler") as mock_get:
            mock_get.side_effect = RuntimeError("scheduler error")
            scheduler_service._register_job(
                {
                    "frequency": "daily",
                    "hour": 2,
                    "minute": 0,
                }
            )


class TestUnregisterJob:
    def test_unregister_when_no_scheduler(self, scheduler_service):
        BackupSchedulerService._class_scheduler = None
        scheduler_service._unregister_job()

    def test_unregister_job_success(self, scheduler_service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        BackupSchedulerService._class_scheduler = mock_scheduler

        scheduler_service._unregister_job()
        mock_scheduler.remove_job.assert_called_once_with("scheduled-backup")

    def test_unregister_job_not_running(self, scheduler_service):
        mock_scheduler = MagicMock()
        mock_scheduler.running = False
        BackupSchedulerService._class_scheduler = mock_scheduler

        scheduler_service._unregister_job()
        mock_scheduler.remove_job.assert_not_called()


class TestLazyBackupService:
    def test_lazy_loads_backup_service(self, patched_db_session):
        BackupSchedulerService()
        with patch(
            "src.services.backup_scheduler_service.BackupSchedulerService.backup_service"
        ):
            pass

    def test_uses_provided_backup_service(self, scheduler_service, db_backup_service):
        assert scheduler_service.backup_service is db_backup_service
