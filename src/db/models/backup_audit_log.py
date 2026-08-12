# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""AuditLogEntry model for PromptVault.

Append-only audit log for all backup-related operations.
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from src.db.base import Base


class AuditLogEntry(Base):
    """Append-only audit log entry for backup operations.

    Records every backup-related operation with outcome, actor, and context.
    Rows are never deleted by application code.

    Attributes:
        id: UUID primary key
        occurred_at: When the operation occurred
        operation: Operation type (e.g. 'backup.create', 'backup.restore')
        outcome: 'success' or 'failure'
        backup_id: Associated backup ID (nullable for config operations)
        performed_by: Username or 'scheduler' for automated ops
        detail: Operation-specific context as JSON
    """

    __tablename__ = "backup_audit_log"

    id = Column(String(36), primary_key=True)
    occurred_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    operation = Column(String(50), nullable=False)
    outcome = Column(String(20), nullable=False)
    backup_id = Column(String(36), ForeignKey("backups.id"), nullable=True)
    performed_by = Column(String(100), nullable=True)
    detail = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<AuditLogEntry(id='{self.id[:8]}...', op='{self.operation}', outcome='{self.outcome}')>"
