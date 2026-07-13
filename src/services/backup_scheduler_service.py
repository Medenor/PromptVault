# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup scheduler service for PromptVault.

Manages scheduled automatic backups using APScheduler with SQLAlchemyJobStore
for crash recovery. Supports daily/weekly/monthly schedules with configurable
retention policies.
"""

import os
import uuid
import logging
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from src.db.config import db_settings
from src.db.session import get_db_session
from src.db.repositories.backup_schedule_repository import BackupScheduleRepository
from src.db.models.backup_schedule import BackupSchedule

logger = logging.getLogger(__name__)


class BackupSchedulerService:
    """Service for managing scheduled automatic backups.

    Uses APScheduler with SQLAlchemyJobStore for persistent job storage.
    Supports daily/weekly/monthly schedules with configurable retention.

    The APScheduler instance and the concurrency lock are class-level so that
    multiple service instances (created per HTTP request) share a single
    background scheduler thread and the same lock.
    """

    _class_scheduler: Optional[BackgroundScheduler] = None
    _class_lock: threading.Lock = threading.Lock()
    _scheduler_lock: threading.Lock = threading.Lock()

    def __init__(self, backup_service=None):
        """Initialize the backup scheduler service.

        Args:
            backup_service: BackupService instance for creating backups
        """
        self._backup_service = backup_service

    @property
    def _lock(self) -> threading.Lock:
        return BackupSchedulerService._class_lock

    @property
    def backup_service(self):
        """Lazy-load backup service to avoid circular imports.

        Reads PROMPTVAULT_DATA_DIR explicitly rather than relying on
        BackupService's own default, since APScheduler's SQLAlchemyJobStore
        pickles jobs for crash recovery and reloads them in a fresh instance
        that never went through app.py's configure_services() injection.
        """
        if self._backup_service is None:
            from src.services.backup_service_db import BackupService
            self._backup_service = BackupService(os.getenv("PROMPTVAULT_DATA_DIR"))
        return self._backup_service

    def _get_scheduler(self) -> BackgroundScheduler:
        """Get or create the shared APScheduler instance."""
        if BackupSchedulerService._class_scheduler is None:
            with BackupSchedulerService._scheduler_lock:
                if BackupSchedulerService._class_scheduler is None:
                    jobstores = {
                        "default": SQLAlchemyJobStore(url=db_settings.DATABASE_URL),
                    }
                    BackupSchedulerService._class_scheduler = BackgroundScheduler(
                        jobstores=jobstores,
                        job_defaults={
                            "coalesce": True,
                            "max_instances": 1,
                            # Default grace window is 1 second, so a machine asleep
                            # through the trigger time (e.g. laptop/Mac Mini) would
                            # otherwise have its backup silently skipped on wake.
                            "misfire_grace_time": 6 * 3600,
                        },
                        daemon=True,
                    )
        return BackupSchedulerService._class_scheduler

    def get_schedule(self) -> Optional[Dict[str, Any]]:
        """Get the current backup schedule configuration.

        Returns:
            Schedule dict or None if no schedule configured
        """
        with get_db_session() as session:
            repo = BackupScheduleRepository(session)
            schedule = repo.get_active()
            if schedule is None:
                return None
            return self._serialize_schedule(schedule)

    def upsert_schedule(self, **kwargs) -> Dict[str, Any]:
        """Create or update the backup schedule.

        Args:
            **kwargs: Schedule attributes (frequency, hour, minute, etc.)

        Returns:
            Updated schedule dict
        """
        with get_db_session() as session:
            repo = BackupScheduleRepository(session)
            existing = repo.get_active()

            if existing:
                schedule = repo.upsert(**kwargs)
            else:
                schedule_id = str(uuid.uuid4())
                schedule = repo.upsert(id=schedule_id, **kwargs)

            session.commit()
            result = self._serialize_schedule(schedule)

        if result.get("enabled"):
            self._register_job(result)
        else:
            self._unregister_job()

        return result

    def enable(self) -> Optional[Dict[str, Any]]:
        """Enable the backup schedule.

        Returns:
            Updated schedule dict or None
        """
        with get_db_session() as session:
            repo = BackupScheduleRepository(session)
            schedule = repo.get_active()
            if schedule is None:
                return None
            schedule.enabled = True
            schedule.updated_at = datetime.now(timezone.utc)
            session.commit()
            result = self._serialize_schedule(schedule)

        self._register_job(result)
        return result

    def disable(self) -> Optional[Dict[str, Any]]:
        """Disable the backup schedule.

        Returns:
            Updated schedule dict or None
        """
        with get_db_session() as session:
            repo = BackupScheduleRepository(session)
            schedule = repo.get_active()
            if schedule is None:
                return None
            schedule.enabled = False
            schedule.updated_at = datetime.now(timezone.utc)
            session.commit()
            result = self._serialize_schedule(schedule)

        self._unregister_job()
        return result

    def _run_scheduled_backup(self) -> None:
        """Execute a scheduled backup.

        Called by APScheduler when the cron trigger fires.
        Prevents concurrent execution via threading lock.
        Updates last_run_at and last_run_status on the schedule.
        """
        if not self._lock.acquire(blocking=False):
            logger.warning("Scheduled backup skipped: another backup is in progress")
            return

        try:
            encrypt = False
            cloud_provider_id = None
            with get_db_session() as session:
                repo = BackupScheduleRepository(session)
                active = repo.get_active()
                if active:
                    encrypt = bool(active.encrypt_scheduled_backups)
                    cloud_provider_id = active.cloud_provider_id

            # Scheduled backups cannot prompt for a passphrase, so encryption
            # is not supported for scheduler-triggered runs. Log and skip.
            if encrypt:
                logger.warning(
                    "Scheduled backup has encrypt_scheduled_backups=True but no "
                    "passphrase is available to the scheduler; running unencrypted.",
                    extra={"event": "backup.scheduled.encryption_skipped"},
                )
                encrypt = False

            frequency = "daily"
            with get_db_session() as session:
                repo = BackupScheduleRepository(session)
                active = repo.get_active()
                if active:
                    frequency = active.frequency or "daily"

            backup_id = self.backup_service.create_backup(
                custom_name="scheduled",
                created_by="scheduler",
                encrypt=encrypt,
                backup_kind=frequency,
            )

            if backup_id and cloud_provider_id:
                self._upload_to_cloud(backup_id, cloud_provider_id)

            with get_db_session() as session:
                repo = BackupScheduleRepository(session)
                schedule = repo.get_active()
                if schedule:
                    schedule.last_run_at = datetime.now(timezone.utc)
                    schedule.last_run_status = "success" if backup_id else "failure"
                    session.commit()

            logger.info(
                "Scheduled backup completed",
                extra={"event": "backup.scheduled.success", "backup_id": backup_id},
            )

        except Exception as exc:
            logger.error(
                "Scheduled backup failed",
                extra={"event": "backup.scheduled.failure"},
                exc_info=exc,
            )

            with get_db_session() as session:
                repo = BackupScheduleRepository(session)
                schedule = repo.get_active()
                if schedule:
                    schedule.last_run_at = datetime.now(timezone.utc)
                    schedule.last_run_status = "failure"
                    session.commit()
        finally:
            self._lock.release()

    def _upload_to_cloud(self, backup_id: str, provider_id: str) -> None:
        """Upload a completed backup to its configured cloud storage provider.

        Failures are logged but do not fail the scheduled run; the local
        backup has already succeeded by the time this is called.
        """
        from src.services.backup_cloud_service import BackupCloudService

        BackupCloudService().upload_backup_by_id(
            self.backup_service, backup_id, provider_id, log_prefix="backup.scheduled"
        )

    def _register_job(self, schedule: Dict[str, Any]) -> None:
        """Register the backup job with APScheduler.

        Args:
            schedule: Schedule configuration dict
        """
        try:
            scheduler = self._get_scheduler()
            frequency = schedule.get("frequency", "daily")
            hour = schedule.get("hour", 2)
            minute = schedule.get("minute", 0)

            trigger_kwargs: Dict[str, Any] = {
                "hour": hour,
                "minute": minute,
            }

            if frequency == "weekly":
                trigger_kwargs["day_of_week"] = schedule.get("day_of_week", 0)
            elif frequency == "monthly":
                trigger_kwargs["day"] = schedule.get("day_of_month", 1)

            trigger = CronTrigger(**trigger_kwargs)

            if not scheduler.running:
                scheduler.start()

            scheduler.add_job(
                self._run_scheduled_backup,
                trigger=trigger,
                id="scheduled-backup",
                name="Scheduled database backup",
                replace_existing=True,
            )

            logger.info(
                "Backup schedule registered",
                extra={
                    "event": "backup.schedule.registered",
                    "frequency": frequency,
                    "hour": hour,
                    "minute": minute,
                },
            )

        except Exception as exc:
            logger.error(
                "Failed to register backup schedule",
                extra={"event": "backup.schedule.register_failure"},
                exc_info=exc,
            )

    def _unregister_job(self) -> None:
        """Remove the backup job from APScheduler."""
        try:
            scheduler = BackupSchedulerService._class_scheduler
            if scheduler and scheduler.running:
                scheduler.remove_job("scheduled-backup")
                logger.info(
                    "Backup schedule unregistered",
                    extra={"event": "backup.schedule.unregistered"},
                )
        except Exception:
            pass

    @staticmethod
    def _serialize_schedule(schedule: BackupSchedule) -> Dict[str, Any]:
        """Serialize a BackupSchedule ORM object to a dict.

        Args:
            schedule: BackupSchedule ORM instance

        Returns:
            Dict representation of the schedule
        """
        return {
            "id": schedule.id,
            "enabled": schedule.enabled,
            "frequency": schedule.frequency,
            "hour": schedule.hour,
            "minute": schedule.minute,
            "day_of_week": schedule.day_of_week,
            "day_of_month": schedule.day_of_month,
            "retention_days": schedule.retention_days,
            "encrypt_scheduled_backups": schedule.encrypt_scheduled_backups,
            "cloud_provider_id": schedule.cloud_provider_id,
            "last_run_at": (
                schedule.last_run_at.isoformat() if schedule.last_run_at else None
            ),
            "last_run_status": schedule.last_run_status,
        }
