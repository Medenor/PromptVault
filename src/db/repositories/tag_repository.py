# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tag repository for PromptVault.

This module provides data access layer for Tag model with
lookup and management operations.
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from src.db.models import Tag, Prompt
from src.db.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository for Tag model.

    Provides methods for tag management including:
    - Name-based lookup
    - Get-or-create pattern
    - Tag statistics
    - Popular tags
    """

    def __init__(self, session: Session):
        """Initialize TagRepository.

        Args:
            session: Database session
        """
        super().__init__(Tag, session)

    def get_by_name(self, name: str) -> Optional[Tag]:
        """Get tag by name.

        Args:
            name: Tag name

        Returns:
            Tag or None if not found
        """
        return self.session.query(Tag).filter(
            Tag.name == name
        ).first()

    def get_or_create(self, name: str) -> Tag:
        """Get existing tag or create new one.

        Args:
            name: Tag name

        Returns:
            Existing or newly created Tag

        Note:
            Uses get-or-create pattern to avoid duplicates.
            Thread-safe due to unique constraint on name.
        """
        tag = self.get_by_name(name)
        if tag:
            return tag

        try:
            tag = self.create(name=name)
            return tag
        except IntegrityError:
            # Race condition: another transaction created it
            self.session.rollback()
            return self.get_by_name(name)

    def get_by_names(self, names: List[str]) -> List[Tag]:
        """Get multiple tags by name.

        Args:
            names: List of tag names

        Returns:
            List of found tags (may be fewer than requested names)
        """
        return self.session.query(Tag).filter(
            Tag.name.in_(names)
        ).all()

    def get_or_create_many(self, names: List[str]) -> List[Tag]:
        """Get or create multiple tags.

        Args:
            names: List of tag names

        Returns:
            List of Tag objects
        """
        tags = []
        for name in names:
            tag = self.get_or_create(name.strip())
            tags.append(tag)
        return tags

    def list_all_with_counts(self) -> List[tuple]:
        """Get all tags with usage counts.

        Returns:
            List of tuples (tag, usage_count) ordered by count descending
        """
        from src.db.models.associations import prompt_tags

        results = self.session.query(
            Tag,
            func.count(prompt_tags.c.prompt_id).label('usage_count')
        ).outerjoin(
            prompt_tags, prompt_tags.c.tag_id == Tag.id
        ).group_by(
            Tag.id
        ).order_by(
            func.count(prompt_tags.c.prompt_id).desc(),
            Tag.name
        ).all()

        return results

    def get_popular_tags(self, limit: int = 10) -> List[tuple]:
        """Get most popular tags by usage count.

        Args:
            limit: Maximum number of tags to return

        Returns:
            List of tuples (tag, usage_count) ordered by count descending
        """
        results = self.list_all_with_counts()
        return results[:limit]

    def delete_if_unused(self, tag_id: int) -> bool:
        """Delete tag only if not used by any prompts.

        Args:
            tag_id: Tag ID

        Returns:
            True if deleted, False if in use or not found
        """
        from src.db.models.associations import prompt_tags

        tag = self.get_by_id(tag_id)
        if not tag:
            return False

        # Check if any prompts use this tag
        usage_count = self.session.query(prompt_tags).filter(
            prompt_tags.c.tag_id == tag_id
        ).count()

        if usage_count > 0:
            return False

        return self.delete(tag_id)

    def rename(self, tag_id: int, new_name: str) -> Optional[Tag]:
        """Rename a tag.

        Args:
            tag_id: Tag ID
            new_name: New tag name

        Returns:
            Updated tag or None if not found

        Raises:
            IntegrityError: If new_name already exists
        """
        return self.update(tag_id, name=new_name)

    def merge_tags(self, source_tag_id: int, target_tag_id: int) -> bool:
        """Merge source tag into target tag.

        All prompts using source_tag will be updated to use target_tag,
        then source_tag is deleted.

        Args:
            source_tag_id: Tag to merge from (will be deleted)
            target_tag_id: Tag to merge into (will remain)

        Returns:
            True if merged successfully, False if tags not found
        """
        source_tag = self.get_by_id(source_tag_id)
        target_tag = self.get_by_id(target_tag_id)

        if not source_tag or not target_tag:
            return False

        # Get all prompts using source tag
        prompts = source_tag.prompts

        # Add target tag to these prompts (if not already present)
        for prompt in prompts:
            if target_tag not in prompt.tags:
                prompt.tags.append(target_tag)

        # Remove source tag from all prompts
        source_tag.prompts.clear()
        self.session.flush()

        # Delete source tag
        self.delete(source_tag_id)

        return True
