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
from sqlalchemy import func

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
        return self.session.query(Category).filter(Category.name == name).first()

    def get_by_name_case_insensitive(self, name: str) -> Optional[Category]:
        """Get category by name (case-insensitive)."""
        return (
            self.session.query(Category)
            .filter(func.lower(Category.name) == name.lower())
            .first()
        )

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

        results = (
            self.session.query(Category, func.count(Prompt.id).label("prompt_count"))
            .outerjoin(Prompt, Prompt.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.name)
            .all()
        )

        return results

    def count_usage(self, category_id: int) -> int:
        """Return number of prompts assigned to the category."""
        from src.db.models import Prompt

        return (
            self.session.query(Prompt).filter(Prompt.category_id == category_id).count()
        )

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
        prompt_count = self.count_usage(category_id)

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

    def get_prompt_ids(self, category_id: int) -> List[int]:
        """Return IDs of prompts assigned to the category."""
        from src.db.models import Prompt

        return [
            row[0]
            for row in self.session.query(Prompt.id)
            .filter(Prompt.category_id == category_id)
            .all()
        ]

    def clear_from_prompts(self, category_id: int) -> None:
        """Unset category_id on all prompts referencing this category."""
        from src.db.models import Prompt

        self.session.query(Prompt).filter(Prompt.category_id == category_id).update(
            {Prompt.category_id: None},
            synchronize_session=False,
        )

    def clear_from_prompt_versions(self, category_id: int) -> None:
        """Unset category_id on historical prompt versions referencing this category."""
        from src.db.models import PromptVersion

        self.session.query(PromptVersion).filter(
            PromptVersion.category_id == category_id
        ).update(
            {PromptVersion.category_id: None},
            synchronize_session=False,
        )

    def bulk_clear_from_prompts(self, category_ids: List[int]) -> None:
        """Unset category_id on all prompts referencing any of these categories."""
        from src.db.models import Prompt

        self.session.query(Prompt).filter(
            Prompt.category_id.in_(category_ids)
        ).update(
            {Prompt.category_id: None},
            synchronize_session=False,
        )

    def bulk_clear_from_prompt_versions(self, category_ids: List[int]) -> None:
        """Unset category_id on historical prompt versions referencing any of these categories."""
        from src.db.models import PromptVersion

        self.session.query(PromptVersion).filter(
            PromptVersion.category_id.in_(category_ids)
        ).update(
            {PromptVersion.category_id: None},
            synchronize_session=False,
        )

    def get_orphan_prompt_ids(self) -> List[int]:
        """Return IDs of prompts with no category assigned."""
        from src.db.models import Prompt

        return [
            row[0]
            for row in self.session.query(Prompt.id)
            .filter(Prompt.category_id.is_(None))
            .all()
        ]

    def get_orphan_prompts(self) -> List[tuple]:
        """Return (id, title) tuples for prompts with no category assigned."""
        from src.db.models import Prompt

        return (
            self.session.query(Prompt.id, Prompt.title)
            .filter(Prompt.category_id.is_(None))
            .all()
        )

    def assign_prompts(self, prompt_ids: List[int], category_id: int) -> int:
        """Assign the given prompts to a category, returning matched count.

        Loads prompts individually (rather than a bulk UPDATE) so callers can
        validate which requested IDs matched real prompts.
        """
        from src.db.models import Prompt

        prompts = (
            self.session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()
        )
        for prompt in prompts:
            prompt.category_id = category_id
        self.session.flush()
        return len(prompts)

    def restore_prompts_category(self, prompt_ids: List[int], category_id: int) -> None:
        """Bulk-set category_id on the given prompts (used by undo restore)."""
        if not prompt_ids:
            return
        from src.db.models import Prompt

        self.session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).update(
            {Prompt.category_id: category_id},
            synchronize_session=False,
        )

    def merge_categories(
        self, source_category_ids: List[int], target_category_id: int
    ) -> int:
        """Merge source categories into target category.

        Args:
            source_category_ids: Category IDs to merge into target
            target_category_id: Target category ID

        Returns:
            Number of categories merged (deleted)
        """
        from src.db.models import Prompt, PromptVersion

        if not source_category_ids:
            return 0

        filtered_sources = [
            cid for cid in source_category_ids if cid != target_category_id
        ]
        if not filtered_sources:
            return 0

        self.session.query(Prompt).filter(
            Prompt.category_id.in_(filtered_sources)
        ).update(
            {Prompt.category_id: target_category_id},
            synchronize_session=False,
        )

        # Preserve historical versions while maintaining FK integrity.
        self.session.query(PromptVersion).filter(
            PromptVersion.category_id.in_(filtered_sources)
        ).update(
            {PromptVersion.category_id: target_category_id},
            synchronize_session=False,
        )

        deleted = (
            self.session.query(Category)
            .filter(Category.id.in_(filtered_sources))
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return deleted
