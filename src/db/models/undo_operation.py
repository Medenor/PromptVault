# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""UndoOperation model for PromptVault.

This model stores undo operations for tags and categories to support
persistence across server restarts and user-scoped undo functionality.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.user import User


class UndoOperation(Base):
    """UndoOperation model for persisting undo history.

    Attributes:
        id: Auto-incrementing integer primary key
        user_id: Foreign key to User who performed the operation
        entity_type: Type of entity ('tag' or 'category')
        operation: Operation type ('create', 'update', 'delete')
        payload: JSON data needed to undo the operation (stored as text)
        created_at: Timestamp when operation was performed
        expires_at: Timestamp when operation expires (created_at + 30 days)
        user: Relationship to User who owns this operation
    """

    __tablename__ = "undo_operations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'tag' or 'category'
    operation: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'create', 'update', 'delete'
    payload: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # JSON stored as text for SQLite compatibility
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", backref="undo_operations")

    __table_args__ = (
        # Index for efficient querying by user and creation time
        Index("ix_undo_operations_user_created", "user_id", "created_at"),
        # Index for efficient cleanup of expired operations
        Index("ix_undo_operations_expires_at", "expires_at"),
    )

    def __repr__(self):
        return f"<UndoOperation(id={self.id}, user_id='{self.user_id}', entity_type='{self.entity_type}', operation='{self.operation}')>"
