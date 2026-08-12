# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup scheduler module.

Provides APScheduler job registration for automated backups.
Reads enabled BackupSchedule rows and registers CronTrigger jobs.
"""

import logging

from src.db.repositories.backup_schedule_repository import BackupScheduleRepository
from src.db.session import get_db_session

logger = logging.getLogger(__name__)


def register_backup_jobs() -> None:
    """Register backup-related scheduled jobs with APScheduler.

    Reads enabled BackupSchedule rows from the database and registers
    corresponding CronTrigger jobs for automated backups. BackupSchedulerService
    manages its own shared APScheduler instance internally.
    """
    try:
        with get_db_session() as session:
            repo = BackupScheduleRepository(session)
            schedule = repo.get_active()

            if schedule and schedule.enabled:
                from src.services.backup_scheduler_service import BackupSchedulerService

                service = BackupSchedulerService()
                service._register_job(
                    {
                        "frequency": schedule.frequency,
                        "hour": schedule.hour,
                        "minute": schedule.minute,
                        "day_of_week": schedule.day_of_week,
                        "day_of_month": schedule.day_of_month,
                        "enabled": True,
                    }
                )
                logger.info(
                    "Backup schedule loaded from database and registered",
                    extra={
                        "event": "backup.schedule.loaded",
                        "frequency": schedule.frequency,
                    },
                )
            else:
                logger.info(
                    "No enabled backup schedule found in database",
                    extra={"event": "backup.schedule.none"},
                )

    except Exception as exc:
        logger.error(
            "Failed to register backup jobs from database",
            extra={"event": "backup.schedule.load_failure"},
            exc_info=exc,
        )
