# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupAuditLog repository for PromptVault.

Provides append-only data access for audit log entries.
"""

from sqlalchemy.orm import Session

from src.db.models.backup_audit_log import AuditLogEntry
from src.db.repositories.base import BaseRepository


class BackupAuditLogRepository(BaseRepository[AuditLogEntry]):
    """Repository for AuditLogEntry entity.

    Append-only: supports insert and read, never update or delete.
    """

    def __init__(self, session: Session):
        """Initialize with database session.

        Args:
            session: SQLAlchemy database session
        """
        super().__init__(AuditLogEntry, session)

    def append(self, **kwargs) -> AuditLogEntry:
        """Insert a new audit log entry (insert-only).

        Args:
            **kwargs: AuditLogEntry attributes

        Returns:
            The created AuditLogEntry instance
        """
        instance = AuditLogEntry(**kwargs)
        self.session.add(instance)
        self.session.flush()
        return instance

    def list_entries(
        self,
        operation: str | None = None,
        outcome: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogEntry]:
        """List audit log entries with optional filters.

        Args:
            operation: Filter by operation type
            outcome: Filter by outcome ('success' or 'failure')
            limit: Max results to return
            offset: Number of results to skip

        Returns:
            List of AuditLogEntry instances, newest first
        """
        query = self.session.query(AuditLogEntry).order_by(
            AuditLogEntry.occurred_at.desc()
        )

        if operation:
            query = query.filter(AuditLogEntry.operation == operation)
        if outcome:
            query = query.filter(AuditLogEntry.outcome == outcome)

        return query.offset(offset).limit(limit).all()

    def count_with_filters(
        self,
        operation: str | None = None,
        outcome: str | None = None,
    ) -> int:
        """Count audit log entries matching filters.

        Args:
            operation: Filter by operation type
            outcome: Filter by outcome

        Returns:
            Count of matching entries
        """
        query = self.session.query(AuditLogEntry)
        if operation:
            query = query.filter(AuditLogEntry.operation == operation)
        if outcome:
            query = query.filter(AuditLogEntry.outcome == outcome)
        return query.count()
