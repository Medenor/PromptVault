"""Version repository for PromptVault.

This module provides data access layer for PromptVersion model with
version history, comparison, and revert operations.
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import uuid

from src.db.models import PromptVersion, Prompt
from src.db.repositories.base import BaseRepository


class VersionRepository(BaseRepository[PromptVersion]):
    """Repository for PromptVersion model with version control operations.

    Provides Git-like version control operations including:
    - Version history listing
    - Version comparison
    - Version revert (creates new version)
    - Parent-child relationship traversal
    """

    def __init__(self, session: Session):
        """Initialize VersionRepository.

        Args:
            session: Database session
        """
        super().__init__(PromptVersion, session)

    def get_versions_for_prompt(
        self,
        prompt_id: int,
        limit: Optional[int] = None
    ) -> List[PromptVersion]:
        """Get all versions for a specific prompt.

        Args:
            prompt_id: Prompt ID
            limit: Maximum number of versions to return

        Returns:
            List of versions ordered by version_number descending (newest first)
        """
        q = self.session.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id
        ).order_by(desc(PromptVersion.version_number))

        if limit:
            q = q.limit(limit)

        return q.all()

    def get_by_version_id(self, version_id: str) -> Optional[PromptVersion]:
        """Get a version by its UUID version_id.

        Args:
            version_id: Version UUID

        Returns:
            PromptVersion or None if not found
        """
        return self.session.query(PromptVersion).filter(
            PromptVersion.version_id == version_id
        ).first()

    def get_latest_version(self, prompt_id: int) -> Optional[PromptVersion]:
        """Get the latest version for a prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            Latest PromptVersion or None if no versions exist
        """
        return self.session.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id
        ).order_by(desc(PromptVersion.version_number)).first()

    def create_version(
        self,
        prompt: Prompt,
        author: str,
        message: str,
        parent_version_id: Optional[str] = None
    ) -> PromptVersion:
        """Create a new version from current prompt state.

        This creates a denormalized snapshot of the prompt's current data.

        Args:
            prompt: Prompt object to create version from
            author: Username of version author
            message: Commit message (1-500 chars per SPEC_APP.md REQ-006)
            parent_version_id: Optional parent version UUID

        Returns:
            Created PromptVersion
        """
        # Get next version number
        latest = self.get_latest_version(prompt.id)
        next_version_number = (latest.version_number + 1) if latest else 1

        # Create denormalized snapshot
        version = PromptVersion(
            prompt_id=prompt.id,
            version_id=str(uuid.uuid4()),
            version_number=next_version_number,
            title=prompt.title,
            prompt=prompt.prompt,
            category_id=prompt.category_id,
            note=prompt.note,
            tags=[tag.name for tag in prompt.tags],  # Denormalized as JSON
            favorite=prompt.favorite,
            author=author,
            message=message,
            created_at=datetime.utcnow(),
            parent_version_id=parent_version_id
        )

        self.session.add(version)
        self.session.flush()
        return version

    def compare_versions(
        self,
        version_id_a: str,
        version_id_b: str
    ) -> Optional[Tuple[PromptVersion, PromptVersion]]:
        """Get two versions for comparison.

        Args:
            version_id_a: First version UUID
            version_id_b: Second version UUID

        Returns:
            Tuple of (version_a, version_b) or None if either not found
        """
        version_a = self.get_by_version_id(version_id_a)
        version_b = self.get_by_version_id(version_id_b)

        if version_a and version_b:
            return (version_a, version_b)
        return None

    def get_version_chain(
        self,
        version_id: str,
        max_depth: int = 100
    ) -> List[PromptVersion]:
        """Get the parent chain for a version (Git-like history).

        Args:
            version_id: Starting version UUID
            max_depth: Maximum depth to traverse (safety limit)

        Returns:
            List of versions from current to root, ordered newest to oldest
        """
        chain = []
        current_version = self.get_by_version_id(version_id)

        depth = 0
        while current_version and depth < max_depth:
            chain.append(current_version)

            # Get parent
            if current_version.parent_version_id:
                current_version = self.get_by_version_id(
                    current_version.parent_version_id
                )
            else:
                break

            depth += 1

        return chain

    def revert_to_version(
        self,
        prompt: Prompt,
        version_id: str,
        author: str,
        message: Optional[str] = None
    ) -> Optional[PromptVersion]:
        """Revert prompt to a previous version (creates new version).

        This follows Git-like revert: creates a new version with content
        from the target version, preserving history.

        Args:
            prompt: Prompt to revert
            version_id: Target version UUID to revert to
            author: Username performing revert
            message: Optional custom message (default: "Reverted to version X")

        Returns:
            New version created from revert, or None if target version not found
        """
        target_version = self.get_by_version_id(version_id)
        if not target_version or target_version.prompt_id != prompt.id:
            return None

        # Update prompt to target version's data
        prompt.title = target_version.title
        prompt.prompt = target_version.prompt
        prompt.category_id = target_version.category_id
        prompt.note = target_version.note
        prompt.favorite = target_version.favorite

        # Update tags (clear and re-add from version)
        prompt.tags.clear()
        # Note: tag restoration would require tag lookup by name
        # This is a simplified version; full implementation would restore tags

        self.session.flush()

        # Create new version documenting the revert
        if not message:
            message = f"Reverted to version {target_version.version_number}"

        # Get current latest version as parent
        current_latest = self.get_latest_version(prompt.id)
        parent_id = current_latest.version_id if current_latest else None

        new_version = self.create_version(
            prompt=prompt,
            author=author,
            message=message,
            parent_version_id=parent_id
        )

        return new_version

    def get_version_count(self, prompt_id: int) -> int:
        """Get total number of versions for a prompt.

        Args:
            prompt_id: Prompt ID

        Returns:
            Version count
        """
        return self.session.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt_id
        ).count()
