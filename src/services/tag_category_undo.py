# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Undo stack for tag/category management operations."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class UndoOperation:
    entity_type: str  # "category" or "tag"
    operation: str
    payload: Dict[str, Any]


class UndoStack:
    """In-memory undo stack for management operations."""

    def __init__(self, max_items: int = 50) -> None:
        self._items: List[UndoOperation] = []
        self._max_items = max_items

    def push(self, op: UndoOperation) -> None:
        self._items.append(op)
        if len(self._items) > self._max_items:
            self._items.pop(0)

    def pop(self) -> Optional[UndoOperation]:
        if not self._items:
            return None
        return self._items.pop()

    def clear(self) -> None:
        self._items.clear()


category_undo_stack = UndoStack()
tag_undo_stack = UndoStack()
