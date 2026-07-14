# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupSchedule repository for PromptVault.

Provides data access for BackupSchedule with singleton pattern enforcement.
"""

from typing import Optional, List

from sqlalchemy.orm import Session

from src.db.repositories.base import BaseRepository
from src.db.models.backup_schedule import BackupSchedule


class BackupScheduleRepository(BaseRepository[BackupSchedule]):
    """Repository for BackupSchedule entity.

    Enforces singleton pattern: at most one active schedule row.
    """

    def __init__(self, session: Session):
        """Initialize with database session.

        Args:
            session: SQLAlchemy database session
        """
        super().__init__(BackupSchedule, session)

    def get_active(self) -> Optional[BackupSchedule]:
        """Get the currently active schedule (if any).

        Returns:
            The first BackupSchedule found, or None
        """
        return self.session.query(BackupSchedule).first()

    def upsert(self, **kwargs) -> BackupSchedule:
        """Create or update the singleton schedule row.

        If a schedule exists, update it. Otherwise create a new one.

        Args:
            **kwargs: Schedule attributes to set

        Returns:
            The created or updated BackupSchedule instance
        """
        existing = self.get_active()
        if existing:
            for key, value in kwargs.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            self.session.flush()
            return existing
        else:
            instance = BackupSchedule(**kwargs)
            self.session.add(instance)
            self.session.flush()
            return instance
