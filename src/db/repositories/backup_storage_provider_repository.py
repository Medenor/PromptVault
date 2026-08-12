# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupStorageProvider repository for PromptVault.

Provides data access for cloud storage provider configurations.
"""

from sqlalchemy.orm import Session

from src.db.models.backup_storage_provider import BackupStorageProvider
from src.db.repositories.base import BaseRepository


class BackupStorageProviderRepository(BaseRepository[BackupStorageProvider]):
    """Repository for BackupStorageProvider entity."""

    def __init__(self, session: Session):
        """Initialize with database session.

        Args:
            session: SQLAlchemy database session
        """
        super().__init__(BackupStorageProvider, session)

    def list_all(self) -> list[BackupStorageProvider]:
        """List all configured storage providers.

        Returns:
            List of all BackupStorageProvider instances
        """
        return self.session.query(BackupStorageProvider).all()
