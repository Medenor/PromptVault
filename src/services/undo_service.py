# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""UndoService for database-backed, user-scoped undo functionality.

This service provides persistent undo/redo functionality for tag and category
management operations. Each undo operation is scoped to a specific user and
stored in the database, allowing undo history to persist across server restarts.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from src.db.models.undo_operation import UndoOperation

logger = logging.getLogger(__name__)


class UndoService:
    """Service for managing user-scoped undo operations.

    This service stores undo operations in the database with a maximum of 50
    operations per (user_id, entity_type) pair. Operations are automatically
    expired after 30 days.

    Attributes:
        db: SQLAlchemy database session
        max_operations_per_entity: Maximum undo operations per user per entity type (default: 50)
        expiration_days: Number of days until operations expire (default: 30)
    """

    def __init__(
        self,
        db: Session,
        max_operations_per_entity: int = 50,
        expiration_days: int = 30,
    ):
        """Initialize the UndoService.

        Args:
            db: SQLAlchemy database session
            max_operations_per_entity: Maximum operations to keep per user per entity type
            expiration_days: Number of days until operations expire
        """
        self.db = db
        self.max_operations_per_entity = max_operations_per_entity
        self.expiration_days = expiration_days

    def push(
        self,
        user_id: Optional[str],
        entity_type: str,
        operation: str,
        payload: Dict[str, Any],
    ) -> None:
        """Store an undo operation in the database.

        This method stores a new undo operation for the specified user and entity type.
        If the number of operations exceeds max_operations_per_entity, the oldest
        operation is automatically removed.

        Args:
            user_id: ID of the user who performed the operation
            entity_type: Type of entity ('tag' or 'category')
            operation: Operation type (e.g., 'create', 'update', 'delete', 'merge')
            payload: JSON-serializable dict containing undo data

        Raises:
            ValueError: If payload is not JSON-serializable

        Example:
            >>> service.push(
            ...     user_id="user-123",
            ...     entity_type="category",
            ...     operation="delete",
            ...     payload={"category": {"name": "Test"}, "prompt_ids": [1, 2, 3]}
            ... )
        """
        if user_id is None:
            logger.debug("Skipping undo push for anonymous operation (no user_id)")
            return

        try:
            # Serialize payload to JSON
            payload_json = json.dumps(payload)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize undo payload: {e}")
            raise ValueError(f"Payload must be JSON-serializable: {e}")

        # Calculate expiration timestamp
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(days=self.expiration_days)

        # Create new undo operation
        undo_op = UndoOperation(
            user_id=user_id,
            entity_type=entity_type,
            operation=operation,
            payload=payload_json,
            created_at=created_at,
            expires_at=expires_at,
        )

        self.db.add(undo_op)
        self.db.flush()  # Flush to get the ID without committing

        # Check if we've exceeded the limit for this user/entity_type
        count = (
            self.db.query(func.count(UndoOperation.id))
            .filter(
                and_(
                    UndoOperation.user_id == user_id,
                    UndoOperation.entity_type == entity_type,
                )
            )
            .scalar()
        )

        if count > self.max_operations_per_entity:
            # Delete oldest operations to maintain limit
            excess = count - self.max_operations_per_entity
            oldest_ops = (
                self.db.query(UndoOperation)
                .filter(
                    and_(
                        UndoOperation.user_id == user_id,
                        UndoOperation.entity_type == entity_type,
                    )
                )
                .order_by(UndoOperation.created_at.asc())
                .limit(excess)
                .all()
            )

            for op in oldest_ops:
                self.db.delete(op)

            logger.debug(
                f"Removed {excess} oldest undo operations for user {user_id}, "
                f"entity_type {entity_type}"
            )

        logger.info(
            f"Pushed undo operation for user {user_id}: {entity_type}.{operation}"
        )

    def pop(self, user_id: str, entity_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve and remove the most recent undo operation.

        This method returns the most recent undo operation for the specified
        user and entity type, and removes it from the database.

        Args:
            user_id: ID of the user
            entity_type: Type of entity ('tag' or 'category')

        Returns:
            Dict containing operation details if found, None otherwise

        Example:
            >>> op = service.pop(user_id="user-123", entity_type="category")
            >>> if op:
            ...     print(f"Undoing {op['operation']} on {op['entity_type']}")
            ...     # Use op['payload'] to perform undo
        """
        # Query for the most recent operation
        undo_op = (
            self.db.query(UndoOperation)
            .filter(
                and_(
                    UndoOperation.user_id == user_id,
                    UndoOperation.entity_type == entity_type,
                )
            )
            .order_by(desc(UndoOperation.created_at))
            .first()
        )

        if not undo_op:
            logger.debug(
                f"No undo operation found for user {user_id}, entity_type {entity_type}"
            )
            return None

        # Parse payload from JSON
        try:
            payload = json.loads(undo_op.payload)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to deserialize undo payload: {e}")
            # Delete the corrupted operation
            self.db.delete(undo_op)
            self.db.flush()
            return None

        # Build result dict
        result = {
            "entity_type": undo_op.entity_type,
            "operation": undo_op.operation,
            "payload": payload,
            "created_at": undo_op.created_at,
        }

        # Remove the operation from the database
        self.db.delete(undo_op)
        self.db.flush()

        logger.info(
            f"Popped undo operation for user {user_id}: "
            f"{undo_op.entity_type}.{undo_op.operation}"
        )

        return result

    def get_history(
        self, user_id: str, entity_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve undo history for a user.

        Returns recent undo operations without removing them from the database.
        Useful for displaying undo history to the user.

        Args:
            user_id: ID of the user
            entity_type: Optional entity type filter ('tag' or 'category')
            limit: Maximum number of operations to return (default: 10)

        Returns:
            List of operation dicts, ordered by most recent first

        Example:
            >>> history = service.get_history(user_id="user-123", limit=5)
            >>> for op in history:
            ...     print(f"{op['entity_type']}.{op['operation']} at {op['created_at']}")
        """
        query = self.db.query(UndoOperation).filter(UndoOperation.user_id == user_id)

        if entity_type is not None:
            query = query.filter(UndoOperation.entity_type == entity_type)

        operations = query.order_by(desc(UndoOperation.created_at)).limit(limit).all()

        result = []
        for op in operations:
            try:
                payload = json.loads(op.payload)
                result.append(
                    {
                        "id": op.id,
                        "entity_type": op.entity_type,
                        "operation": op.operation,
                        "payload": payload,
                        "created_at": op.created_at,
                        "expires_at": op.expires_at,
                    }
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Skipping corrupted undo operation {op.id}: {e}")
                continue

        return result

    def clear_user_undo(self, user_id: str) -> int:
        """Clear all undo operations for a user.

        This method removes all undo operations for the specified user across
        all entity types.

        Args:
            user_id: ID of the user

        Returns:
            Number of operations deleted

        Example:
            >>> deleted = service.clear_user_undo(user_id="user-123")
            >>> print(f"Cleared {deleted} undo operations")
        """
        deleted_count = (
            self.db.query(UndoOperation)
            .filter(UndoOperation.user_id == user_id)
            .delete(synchronize_session=False)
        )

        self.db.flush()

        logger.info(f"Cleared {deleted_count} undo operations for user {user_id}")

        return deleted_count

    def cleanup_expired(self) -> int:
        """Delete expired undo operations.

        This method removes all undo operations where expires_at is in the past.
        Should be called periodically (e.g., via a scheduled task) to clean up
        old operations.

        Returns:
            Number of expired operations deleted

        Example:
            >>> deleted = service.cleanup_expired()
            >>> print(f"Cleaned up {deleted} expired undo operations")
        """
        now = datetime.now(timezone.utc)

        deleted_count = (
            self.db.query(UndoOperation)
            .filter(UndoOperation.expires_at < now)
            .delete(synchronize_session=False)
        )

        self.db.flush()

        logger.info(f"Cleaned up {deleted_count} expired undo operations")

        return deleted_count
