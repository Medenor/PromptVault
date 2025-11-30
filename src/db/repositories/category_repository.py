# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category repository for PromptVault.

This module provides data access layer for Category model with
lookup and management operations.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.db.models import Category
from src.db.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """Repository for Category model.

    Provides methods for category management including:
    - Name-based lookup
    - Get-or-create pattern
    - Category statistics
    """

    def __init__(self, session: Session):
        """Initialize CategoryRepository.

        Args:
            session: Database session
        """
        super().__init__(Category, session)

    def get_by_name(self, name: str) -> Optional[Category]:
        """Get category by name.

        Args:
            name: Category name

        Returns:
            Category or None if not found
        """
        return self.session.query(Category).filter(
            Category.name == name
        ).first()

    def get_or_create(self, name: str) -> Category:
        """Get existing category or create new one.

        Args:
            name: Category name

        Returns:
            Existing or newly created Category

        Note:
            Uses get-or-create pattern to avoid duplicates.
            Thread-safe due to unique constraint on name.
        """
        category = self.get_by_name(name)
        if category:
            return category

        try:
            category = self.create(name=name)
            return category
        except IntegrityError:
            # Race condition: another transaction created it
            self.session.rollback()
            return self.get_by_name(name)

    def list_all_with_counts(self) -> List[tuple]:
        """Get all categories with prompt counts.

        Returns:
            List of tuples (category, prompt_count) ordered by name
        """
        from src.db.models import Prompt
        from sqlalchemy import func

        results = self.session.query(
            Category,
            func.count(Prompt.id).label('prompt_count')
        ).outerjoin(
            Prompt, Prompt.category_id == Category.id
        ).group_by(
            Category.id
        ).order_by(
            Category.name
        ).all()

        return results

    def delete_if_unused(self, category_id: int) -> bool:
        """Delete category only if it has no prompts.

        Args:
            category_id: Category ID

        Returns:
            True if deleted, False if has prompts or not found
        """
        from src.db.models import Prompt

        category = self.get_by_id(category_id)
        if not category:
            return False

        # Check if any prompts use this category
        prompt_count = self.session.query(Prompt).filter(
            Prompt.category_id == category_id
        ).count()

        if prompt_count > 0:
            return False

        return self.delete(category_id)

    def rename(self, category_id: int, new_name: str) -> Optional[Category]:
        """Rename a category.

        Args:
            category_id: Category ID
            new_name: New category name

        Returns:
            Updated category or None if not found

        Raises:
            IntegrityError: If new_name already exists
        """
        return self.update(category_id, name=new_name)
