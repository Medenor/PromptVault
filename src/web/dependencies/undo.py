# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI dependency functions for undo service.

This module provides reusable dependency functions for FastAPI route handlers
to inject the UndoService for managing user-scoped undo operations.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.undo_service import UndoService


def get_undo_service(db: Session = Depends(get_db)) -> UndoService:
    """Provide UndoService instance.

    Creates an UndoService instance with the current database session.
    The service handles database-backed undo operations for tags and categories.

    Args:
        db: Database session (injected)

    Returns:
        UndoService: Undo service instance

    Example:
        >>> @router.post("/categories/{category_id}/undo")
        >>> def undo_category_operation(
        ...     category_id: int,
        ...     undo_service: UndoService = Depends(get_undo_service),
        ...     user: User = Depends(get_current_active_user)
        ... ):
        ...     op = undo_service.pop(user.id, "category")
        ...     if op:
        ...         # Perform undo logic
        ...         return {"undone": op["operation"]}
        ...     raise HTTPException(404, "No undo operation available")
    """
    return UndoService(db)
