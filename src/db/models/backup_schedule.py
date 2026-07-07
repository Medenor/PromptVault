# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupSchedule model for PromptVault.

Tracks scheduled backup configuration. At most one active schedule per system.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from src.db.base import Base


class BackupSchedule(Base):
    """Scheduled backup configuration model.

    Singleton-style: at most one active schedule per system (enforced at service layer).

    Attributes:
        id: UUID primary key
        enabled: Whether schedule is active
        frequency: 'daily', 'weekly', or 'monthly'
        hour: Hour of day (0-23, UTC)
        minute: Minute of hour (0-59, UTC)
        day_of_week: Day of week (0=Mon-6=Sun), required for weekly
        day_of_month: Day of month (1-31), required for monthly
        retention_daily_count: How many daily backups to keep
        retention_weekly_count: How many weekly backups to keep
        retention_monthly_count: How many monthly backups to keep
        encrypt_scheduled_backups: Whether scheduled backups are encrypted
        cloud_provider_id: Auto-upload destination provider
        created_at: When schedule was created
        updated_at: When schedule was last updated
        last_run_at: When last scheduled backup ran
        last_run_status: 'success' or 'failure'
    """

    __tablename__ = "backup_schedules"

    id = Column(String(36), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    frequency = Column(String(20), nullable=False)
    hour = Column(Integer, nullable=False)
    minute = Column(Integer, nullable=False, default=0)
    day_of_week = Column(Integer, nullable=True)
    day_of_month = Column(Integer, nullable=True)
    retention_daily_count = Column(Integer, nullable=False, default=7)
    retention_weekly_count = Column(Integer, nullable=False, default=4)
    retention_monthly_count = Column(Integer, nullable=False, default=12)
    encrypt_scheduled_backups = Column(Boolean, nullable=False, default=False)
    cloud_provider_id = Column(
        String(36), ForeignKey("backup_storage_providers.id"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_run_status = Column(String(20), nullable=True)

    def __repr__(self):
        return f"<BackupSchedule(id='{self.id[:8]}...', frequency='{self.frequency}', enabled={self.enabled})>"
