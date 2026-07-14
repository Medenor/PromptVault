# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt repository for PromptVault.

This module provides data access layer for Prompt model with advanced
search, filtering, and relationship management capabilities.
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func

from src.db.models import Prompt, Tag, Category
from src.db.repositories.base import BaseRepository


class PromptRepository(BaseRepository[Prompt]):
    """Repository for Prompt model with search and filtering.

    Provides methods for CRUD operations plus advanced features like:
    - Full-text search (LIKE-based, FTS deferred to future phase)
    - Category filtering
    - Tag filtering
    - Favorite filtering
    - Eager loading of relationships
    """

    def __init__(self, session: Session):
        """Initialize PromptRepository.

        Args:
            session: Database session
        """
        super().__init__(Prompt, session)

    def search(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        case_sensitive: bool = False,
    ) -> List[Prompt]:
        """Search prompts with multiple filters.

        Args:
            query: Text search in title and prompt content (LIKE-based)
            category: Filter by category name
            tags: Filter by tag names (prompts with ANY of these tags)
            favorite: Filter by favorite status
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of matching Prompt objects

        Example:
            # Search for favorited marketing prompts
            repo.search(query="email", category="Marketing", favorite=True)
        """
        q = self.session.query(Prompt)

        # Text search (simple LIKE-based, FTS deferred to future phase per plan)
        if query:
            search_pattern = f"%{query}%"
            comparator = or_(
                Prompt.title.ilike(search_pattern),
                Prompt.prompt.ilike(search_pattern),
                Prompt.note.ilike(search_pattern),
            )
            q = q.filter(comparator)

        # Category filter
        if category:
            q = q.join(Category).filter(Category.name == category)

        # Tags filter (prompts with ANY of the specified tags)
        if tags and len(tags) > 0:
            q = q.join(Prompt.tags).filter(Tag.name.in_(tags)).distinct()

        # Favorite filter
        if favorite is not None:
            q = q.filter(Prompt.favorite == favorite)

        # Order by most recently updated (must come before limit/offset)
        q = q.order_by(Prompt.updated_at.desc().nullslast(), Prompt.created_at.desc())

        # Pagination
        q = q.offset(offset)
        if limit:
            q = q.limit(limit)

        results = q.all()

        # Enforce case-sensitive matching in Python when requested (SQLite LIKE is case-insensitive)
        if case_sensitive and query:
            filtered = []
            for prompt in results:
                if (
                    (query in prompt.title)
                    or (query in prompt.prompt)
                    or (prompt.note and query in prompt.note)
                ):
                    filtered.append(prompt)
            return filtered

        return results

    def count(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        favorite: Optional[bool] = None,
        case_sensitive: bool = False,
    ) -> int:
        """Count prompts matching the same filters as search().

        Mirrors search()'s filter-building logic exactly (minus limit/offset/
        ordering) so total_count/total_pages reflect the same result set that
        search() would page through.

        Args:
            query: Text search in title and prompt content (LIKE-based)
            category: Filter by category name
            tags: Filter by tag names (prompts with ANY of these tags)
            favorite: Filter by favorite status
            case_sensitive: Enforce case-sensitive matching on query

        Returns:
            Total number of matching prompts
        """
        q = self.session.query(Prompt)

        if query:
            search_pattern = f"%{query}%"
            comparator = or_(
                Prompt.title.ilike(search_pattern),
                Prompt.prompt.ilike(search_pattern),
                Prompt.note.ilike(search_pattern),
            )
            q = q.filter(comparator)

        if category:
            q = q.join(Category).filter(Category.name == category)

        if tags and len(tags) > 0:
            q = q.join(Prompt.tags).filter(Tag.name.in_(tags)).distinct()

        if favorite is not None:
            q = q.filter(Prompt.favorite == favorite)

        # Case-sensitive matching can't be expressed in SQL here (SQLite LIKE
        # is case-insensitive), so fall back to counting in Python, same as
        # search() does when case_sensitive is requested.
        if case_sensitive and query:
            count = 0
            for prompt in q.all():
                if (
                    (query in prompt.title)
                    or (query in prompt.prompt)
                    or (prompt.note and query in prompt.note)
                ):
                    count += 1
            return count

        return q.count()

    def get_with_relationships(self, prompt_id: int) -> Optional[Prompt]:
        """Get a prompt with all relationships eagerly loaded.

        This method eagerly loads category, tags, versions, branches, and user
        to avoid N+1 query problems.

        Args:
            prompt_id: Prompt ID

        Returns:
            Prompt with all relationships loaded, or None if not found
        """
        return (
            self.session.query(Prompt)
            .filter(Prompt.id == prompt_id)
            .options(
                joinedload(Prompt.category),
                joinedload(Prompt.tags),
                joinedload(Prompt.versions),
                joinedload(Prompt.branches),
                joinedload(Prompt.user),
            )
            .first()
        )

    def get_by_category(self, category_name: str) -> List[Prompt]:
        """Get all prompts in a specific category.

        Args:
            category_name: Category name

        Returns:
            List of prompts in the category
        """
        return (
            self.session.query(Prompt)
            .join(Category)
            .filter(Category.name == category_name)
            .all()
        )

    def get_by_tag(self, tag_name: str) -> List[Prompt]:
        """Get all prompts with a specific tag.

        Args:
            tag_name: Tag name

        Returns:
            List of prompts with the tag
        """
        return (
            self.session.query(Prompt)
            .join(Prompt.tags)
            .filter(Tag.name == tag_name)
            .all()
        )

    def get_favorites(self, limit: Optional[int] = None) -> List[Prompt]:
        """Get all favorited prompts.

        Args:
            limit: Maximum number of results

        Returns:
            List of favorited prompts
        """
        q = self.session.query(Prompt).filter(Prompt.favorite == True)
        if limit:
            q = q.limit(limit)
        return q.all()

    def set_favorite(self, prompt_id: int, favorite: bool) -> Optional[Prompt]:
        """Set favorite status for a prompt.

        Args:
            prompt_id: Prompt ID
            favorite: New favorite status

        Returns:
            Updated prompt or None if not found
        """
        return self.update(prompt_id, favorite=favorite)

    def add_tag(self, prompt_id: int, tag: Tag) -> Optional[Prompt]:
        """Add a tag to a prompt.

        Args:
            prompt_id: Prompt ID
            tag: Tag object to add

        Returns:
            Updated prompt or None if not found
        """
        prompt = self.get_by_id(prompt_id)
        if prompt and tag not in prompt.tags:
            prompt.tags.append(tag)
            self.session.flush()
        return prompt

    def remove_tag(self, prompt_id: int, tag: Tag) -> Optional[Prompt]:
        """Remove a tag from a prompt.

        Args:
            prompt_id: Prompt ID
            tag: Tag object to remove

        Returns:
            Updated prompt or None if not found
        """
        prompt = self.get_by_id(prompt_id)
        if prompt and tag in prompt.tags:
            prompt.tags.remove(tag)
            self.session.flush()
        return prompt

    def get_statistics(self) -> Dict[str, int]:
        """Get prompt statistics.

        Returns:
            Dictionary with statistics:
            - total: Total number of prompts
            - favorites: Number of favorited prompts
            - with_versions: Number of prompts with version history
        """
        total = self.count()
        favorites = self.session.query(Prompt).filter(Prompt.favorite == True).count()

        # Count prompts that have at least one version
        with_versions = self.session.query(Prompt).filter(Prompt.versions.any()).count()

        return {"total": total, "favorites": favorites, "with_versions": with_versions}
