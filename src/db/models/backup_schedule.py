# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupSchedule model for PromptVault.

Tracks scheduled backup configuration. At most one active schedule per system.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
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
        retention_days: How many days of backups to keep
        encrypt_scheduled_backups: Whether scheduled backups are encrypted
        cloud_provider_id: Auto-upload destination provider
        created_at: When schedule was created
        updated_at: When schedule was last updated
        last_run_at: When last scheduled backup ran
        last_run_status: 'success' or 'failure'
    """

    __tablename__ = "backup_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    hour: Mapped[int] = mapped_column(nullable=False)
    minute: Mapped[int] = mapped_column(nullable=False, default=0)
    day_of_week: Mapped[int | None] = mapped_column(nullable=True)
    day_of_month: Mapped[int | None] = mapped_column(nullable=True)
    retention_days: Mapped[int] = mapped_column(nullable=False, default=30)
    encrypt_scheduled_backups: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    cloud_provider_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("backup_storage_providers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_run_status: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self):
        return f"<BackupSchedule(id='{self.id[:8]}...', frequency='{self.frequency}', enabled={self.enabled})>"
