# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup repository for PromptVault.

Provides data access layer for Backup entities with filtering support.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.db.repositories.base import BaseRepository
from src.db.models.backup import Backup


class BackupRepository(BaseRepository[Backup]):
    """Repository for Backup entity with filtering and search.

    Extends BaseRepository with backup-specific query methods including
    tag filtering, date range filtering, and kind filtering.
    """

    def __init__(self, session: Session):
        """Initialize with database session.

        Args:
            session: SQLAlchemy database session
        """
        super().__init__(Backup, session)

    def list_backups(
        self,
        tag: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        kind: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Backup]:
        """List backups with optional filters.

        Args:
            tag: Filter by tag label
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            kind: Filter by backup_kind ('full' or 'incremental')
            limit: Max results to return
            offset: Number of results to skip

        Returns:
            List of Backup instances matching filters, newest first
        """
        query = self.session.query(Backup).order_by(Backup.created_at.desc())

        if tag:
            query = query.filter(Backup.tags.contains([tag]))

        if start_date:
            query = query.filter(Backup.created_at >= start_date)

        if end_date:
            query = query.filter(Backup.created_at <= end_date)

        if kind:
            query = query.filter(Backup.backup_kind == kind)

        return query.offset(offset).limit(limit).all()

    def get_all_for_cleanup(self) -> List[Backup]:
        """Get all backups for retention cleanup processing.

        Returns:
            List of all Backup instances ordered by created_at ascending
        """
        return self.session.query(Backup).order_by(Backup.created_at.asc()).all()

    def count_with_filters(
        self,
        tag: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        kind: Optional[str] = None,
    ) -> int:
        """Count backups matching filters.

        Args:
            tag: Filter by tag label
            start_date: Filter by created_at >= start_date
            end_date: Filter by created_at <= end_date
            kind: Filter by backup_kind

        Returns:
            Count of matching backups
        """
        query = self.session.query(Backup)

        if tag:
            query = query.filter(Backup.tags.contains([tag]))
        if start_date:
            query = query.filter(Backup.created_at >= start_date)
        if end_date:
            query = query.filter(Backup.created_at <= end_date)
        if kind:
            query = query.filter(Backup.backup_kind == kind)

        return query.count()
