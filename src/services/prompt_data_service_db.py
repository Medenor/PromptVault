# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database-backed PromptDataService with backward compatibility.

This service maintains the same interface as the JSON-based service but uses
SQLAlchemy repositories for data persistence. The dict-based interface is
maintained for backward compatibility with existing API endpoints.
"""

import json
import os
import uuid
import warnings
from collections.abc import Iterable
from datetime import UTC
from typing import Any

from src.db.models import Category, Prompt, PromptVersion, User
from src.db.repositories import (
    CategoryRepository,
    PromptRepository,
    TagRepository,
    VersionRepository,
)
from src.db.repositories.sharing_repository import SharingRepository
from src.db.repositories.user_repository import UserRepository
from src.db.session import get_db_session
from src.services.exceptions import DataPersistenceError, ShareGrantError
from src.services.logging_service import logging_service

# Import sanitization utilities from validators
from src.web.validators import (
    MAX_CATEGORY_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_PROMPT_LENGTH,
    MAX_TAG_COUNT,
    MAX_TAG_LENGTH,
    MAX_TITLE_LENGTH,
    sanitize_tags,
    sanitize_text_field,
)

logger = logging_service.get_logger(__name__)


class PromptDataService:
    """Database-backed service for handling prompt data operations.

    This service provides backward compatibility with the JSON-based service
    by maintaining the same dict-based interface while using database repositories
    for persistence.

    Key differences from JSON-based service:
    - load_prompts() queries database instead of reading JSON file
    - save_prompts() is a no-op (database auto-commits via context manager)
    - All operations use transactions for data consistency
    - IDs are managed by database sequences (except during migration)
    """

    def __init__(self, data_file_path: str = None):
        """Initialize the PromptDataService.

        Args:
            data_file_path (str): Kept for backward compatibility but unused.
                Database connection is configured via DATABASE_URL environment variable.
        """
        # Keep for backward compatibility but not used
        if data_file_path:
            warnings.warn(
                "data_file_path parameter is deprecated and ignored. "
                "Use DATABASE_URL environment variable instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.data_file = data_file_path

        # Cache properties (populated from database)
        self._prompts_cache = None
        self._categories_cache = None
        self._tags_cache = None

        # Get or create default user
        self._ensure_default_user()

    def _ensure_default_user(self) -> User:
        """Ensure default 'system' user exists."""
        try:
            with get_db_session() as session:
                user = (
                    session.query(User)
                    .filter_by(email="system@promptvault.local")
                    .first()
                )
                if not user:
                    user = User(
                        id=str(uuid.uuid4()),
                        username="system",
                        display_name="System User",
                        email="system@promptvault.local",
                        password_hash="system",  # Not used for system user
                        role="system",
                    )
                    session.add(user)
                    session.flush()
                return user
        except Exception as e:
            logger.error(
                "Failed to ensure default user exists",
                extra={"event": "user.create.failure"},
                exc_info=e,
            )
            # Create minimal user object for backward compatibility
            return User(id=str(uuid.uuid4()), username="system")

    def _get_default_user(self) -> User:
        """Get the default system user."""
        with get_db_session() as session:
            user = session.query(User).filter_by(username="system").first()
            if not user:
                user = self._ensure_default_user()
            return user

    def _normalize_tags(self, tags: Iterable[Any]) -> list[str]:
        """Normalize a collection of tags by trimming whitespace and dropping blanks.

        Args:
            tags (Iterable[Any]): Raw tag values.

        Returns:
            List[str]: Cleaned tag strings preserving input order.
        """
        normalized: list[str] = []
        for tag in tags or []:
            if not isinstance(tag, str):
                continue
            cleaned = tag.strip()
            if cleaned:
                normalized.append(cleaned)
        return normalized

    def _normalize_prompt_payload(self, data: dict[str, Any]) -> dict[str, Any]:
        """Normalize prompt payload fields such as tags prior to persistence.

        This provides defense-in-depth by sanitizing data at the service layer,
        even if API validation is bypassed or data comes from other sources.

        Args:
            data (Dict[str, Any]): Prompt data to normalize.

        Returns:
            Dict[str, Any]: Normalized prompt data.

        Sanitization applied:
            - Title: Control character removal, whitespace normalization, length limit
            - Prompt: Control character removal (preserves newlines), length limit
            - Category: Control character removal, whitespace normalization, length limit
            - Note: Control character removal (preserves newlines), length limit
            - Tags: Deduplication, sanitization, length limits
        """
        if not isinstance(data, dict):
            return {}

        # Sanitize title
        if "title" in data and data["title"]:
            data["title"] = sanitize_text_field(
                str(data["title"]), max_length=MAX_TITLE_LENGTH, allow_newlines=False
            )

        # Sanitize prompt content
        if "prompt" in data and data["prompt"]:
            data["prompt"] = sanitize_text_field(
                str(data["prompt"]), max_length=MAX_PROMPT_LENGTH, allow_newlines=True
            )

        # Sanitize category
        if "category" in data and data["category"]:
            data["category"] = sanitize_text_field(
                str(data["category"]),
                max_length=MAX_CATEGORY_LENGTH,
                allow_newlines=False,
            )

        # Sanitize note
        if "note" in data and data["note"]:
            data["note"] = sanitize_text_field(
                str(data["note"]), max_length=MAX_NOTE_LENGTH, allow_newlines=True
            )

        # Sanitize and deduplicate tags
        tags = data.get("tags", [])
        if isinstance(tags, list):
            data["tags"] = sanitize_tags(
                tags, max_count=MAX_TAG_COUNT, max_length_per_tag=MAX_TAG_LENGTH
            )
        else:
            data["tags"] = []

        return data

    def save_prompts(self) -> bool:
        """Save prompts to persistent storage.

        NOTE: This is a no-op for database backend as all changes are
        automatically persisted via transaction commits in the context manager.

        Returns:
            bool: Always returns True for backward compatibility
        """
        warnings.warn(
            "save_prompts() is deprecated with database backend. "
            "Changes are automatically persisted via transactions.",
            DeprecationWarning,
            stacklevel=2,
        )
        logger.debug(
            "save_prompts() called (no-op with database backend)",
            extra={"event": "prompts.save.noop"},
        )
        if not self.data_file:
            return True

        payload = {
            "next_id": self.next_id,
            "prompts": self.load_prompts(),
            "categories": self.get_categories(),
            "global_tags": list(self.global_tags),
        }

        try:
            data_dir = os.path.dirname(self.data_file) or "."
            os.makedirs(data_dir, exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return True
        except Exception as exc:
            logger.error(
                "Failed to persist prompts to data file",
                extra={"event": "prompts.save.failure", "resource_id": self.data_file},
                exc_info=exc,
            )
            raise DataPersistenceError(
                "Failed to persist prompts to data file.",
                context={"data_file": self.data_file},
            ) from exc

    def load_prompts(self) -> dict[int, dict]:
        """Load prompts from database.

        Converts ORM objects to dict format for backward compatibility.

        Returns:
            Dict[int, Dict]: The loaded prompts in legacy format:
                {
                    prompt_id: {
                        "data": {...},
                        "versions": [...],
                        "branches": {...}
                    }
                }
        """
        try:
            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                prompts = prompt_repo.get_all()

                # Convert to legacy dict format
                result = {}
                for prompt in prompts:
                    result[prompt.id] = self._prompt_to_dict(prompt)

                # Cache for next_id calculation
                self._prompts_cache = result

                logger.debug(
                    "Loaded prompts from database",
                    extra={"event": "prompts.load.success", "count": len(result)},
                )

                return result

        except Exception as exc:
            logger.error(
                "Failed to load prompts from database",
                extra={"event": "prompts.load.failure"},
                exc_info=exc,
            )
            return {}

    def _prompt_to_dict(self, prompt: Prompt) -> dict[str, Any]:
        """Convert Prompt ORM object to legacy dict format.

        Args:
            prompt: Prompt ORM object

        Returns:
            Dict with keys: data, versions, branches
        """
        return {
            "data": {
                "title": prompt.title,
                "prompt": prompt.prompt,
                "category": prompt.category.name if prompt.category else "No category",
                "tags": [tag.name for tag in prompt.tags],
                "note": prompt.note or "",
                "favorite": prompt.favorite,
                "semantic_version": prompt.semantic_version,
            },
            "versions": [self._version_to_dict(v) for v in prompt.versions],
            "branches": {
                branch.branch_name: branch.current_version_id
                for branch in prompt.branches
            },
        }

    def _version_to_dict(self, version: PromptVersion) -> dict[str, Any]:
        """Convert PromptVersion ORM object to legacy dict format.

        Args:
            version: PromptVersion ORM object

        Returns:
            Dict with version details
        """
        # Convert to UTC and format as ISO 8601 with Z suffix
        if version.created_at.tzinfo is not None:
            # Timezone-aware (PostgreSQL): convert to UTC
            timestamp = (
                version.created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            )
        else:
            # Naive datetime (SQLite): assume UTC
            timestamp = version.created_at.isoformat() + "Z"

        # Get category name from category_id
        category_name = ""
        if version.category_id:
            with get_db_session() as session:
                category = (
                    session.query(Category).filter_by(id=version.category_id).first()
                )
                if category:
                    category_name = category.name

        return {
            "version_id": version.version_id,
            "version_number": version.version_number,
            "timestamp": timestamp,
            "author": version.author,
            "message": version.message,
            "semantic_version": version.semantic_version,
            "data": {
                "title": version.title,
                "prompt": version.prompt,
                "category": category_name,  # Now returns actual category name
                "tags": version.tags or [],
                "note": version.note or "",
                "favorite": version.favorite,
            },
            "parents": [version.parent_version_id] if version.parent_version_id else [],
        }

    @property
    def prompts(self) -> dict[int, dict]:
        """Get prompts dict for backward compatibility."""
        if self._prompts_cache is None:
            self._prompts_cache = self.load_prompts()
        return self._prompts_cache

    @property
    def next_id(self) -> int:
        """Get next available prompt ID.

        Note: With database backend, IDs are managed by sequences.
        This property is kept for compatibility but not used for ID generation.
        """
        if self._prompts_cache is None:
            self.load_prompts()

        if not self._prompts_cache:
            return 1

        return max(self._prompts_cache.keys()) + 1

    @next_id.setter
    def next_id(self, value: int):
        """Setter for next_id (no-op, kept for compatibility)."""
        pass

    @property
    def categories(self) -> list[str]:
        """Get all categories."""
        return self.get_categories()

    @property
    def global_tags(self) -> set[str]:
        """Get all tags as a set."""
        return set(self.get_tags())

    def add_new_prompt(self, data: dict[str, Any], user_id: str | None = None) -> int:
        """Add a new prompt with initial version.

        Args:
            data (Dict[str, Any]): The prompt data
            user_id (Optional[str]): The ID of the user who owns the prompt

        Returns:
            int: The ID of the new prompt
        """
        try:
            data = self._normalize_prompt_payload(data.copy())
            commit_message = data.pop("commit_message", "Initial commit")

            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                version_repo = VersionRepository(session)
                category_repo = CategoryRepository(session)
                tag_repo = TagRepository(session)

                # Get or create category
                category_name = data.get("category", "No category")
                category = category_repo.get_or_create(category_name)

                # Get or create tags
                tag_names = data.pop("tags", [])
                tags = tag_repo.get_or_create_many(tag_names)

                # Get user (specified user_id or default system user)
                if user_id:
                    user = session.query(User).filter_by(id=user_id).first()
                else:
                    user = session.query(User).filter_by(username="system").first()

                # Create prompt
                prompt = prompt_repo.create(
                    title=data["title"],
                    prompt=data["prompt"],
                    category_id=category.id,
                    note=data.get("note", ""),
                    favorite=data.get("favorite", False),
                    user_id=user.id if user else None,
                )

                # Add tags
                prompt.tags.extend(tags)
                session.flush()

                # Create initial version
                version = version_repo.create_version(
                    prompt=prompt,
                    author=user.username if user else "system",
                    message=commit_message,
                    parent_version_id=None,
                )

                # Create main branch
                from src.db.models import PromptBranch

                main_branch = PromptBranch(
                    prompt_id=prompt.id,
                    branch_name="main",
                    current_version_id=version.version_id,
                )
                session.add(main_branch)
                session.flush()

                logging_service.log_audit_event(
                    action="prompt.create",
                    resource_type="prompt",
                    resource_id=str(prompt.id),
                    title=data.get("title"),
                    version_id=version.version_id,
                    commit_message=commit_message,
                )

                # Invalidate cache
                self._prompts_cache = None

                return prompt.id

        except Exception as exc:
            logger.error(
                "Failed to create prompt",
                extra={"event": "prompt.create.failure"},
                exc_info=exc,
            )
            raise DataPersistenceError(
                "Could not create prompt in database.", context={"data": data}
            ) from exc

    def update_prompt(
        self,
        prompt_id: int,
        data: dict[str, Any],
        commit_message: str = "Update",
        author: str | None = None,
    ) -> bool:
        """Update an existing prompt with a new version.

        Args:
            prompt_id (int): The ID of the prompt to update
            data (Dict[str, Any]): The updated prompt data
            commit_message (str): The commit message
            author (Optional[str]): The author username. If not provided, uses "system"

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._normalize_prompt_payload(data.copy())

            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                version_repo = VersionRepository(session)
                category_repo = CategoryRepository(session)
                tag_repo = TagRepository(session)

                # Get prompt
                prompt = prompt_repo.get_by_id(prompt_id)
                if not prompt:
                    return False

                # Get or create category
                category_name = data.get("category", "No category")
                category = category_repo.get_or_create(category_name)

                # Get or create tags
                tag_names = data.pop("tags", [])
                tags = tag_repo.get_or_create_many(tag_names)

                # Get current version ID (parent for new version)
                main_branch = next(
                    (b for b in prompt.branches if b.branch_name == "main"), None
                )
                parent_version_id = (
                    main_branch.current_version_id if main_branch else None
                )

                # Update prompt
                prompt.title = data["title"]
                prompt.prompt = data["prompt"]
                prompt.category_id = category.id
                prompt.note = data.get("note", "")
                prompt.favorite = data.get("favorite", False)

                # Update tags
                prompt.tags.clear()
                prompt.tags.extend(tags)
                session.flush()

                # Create new version
                author_name = author if author else "system"
                version = version_repo.create_version(
                    prompt=prompt,
                    author=author_name,
                    message=commit_message,
                    parent_version_id=parent_version_id,
                )
                # Update main branch
                if main_branch:
                    main_branch.current_version_id = version.version_id
                else:
                    from src.db.models import PromptBranch

                    main_branch = PromptBranch(
                        prompt_id=prompt.id,
                        branch_name="main",
                        current_version_id=version.version_id,
                    )
                    session.add(main_branch)
                session.flush()

                logging_service.log_audit_event(
                    action="prompt.update",
                    resource_type="prompt",
                    resource_id=str(prompt_id),
                    version_id=version.version_id,
                    commit_message=commit_message,
                )

                # Invalidate cache
                self._prompts_cache = None

                return True

        except Exception as exc:
            logger.error(
                "Failed to update prompt",
                extra={"event": "prompt.update.failure", "resource_id": str(prompt_id)},
                exc_info=exc,
            )
            return False

    def delete_prompt(self, prompt_id: int) -> bool:
        """Delete a prompt.

        Args:
            prompt_id (int): The ID of the prompt to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                success = prompt_repo.delete(prompt_id)

                if success:
                    logging_service.log_audit_event(
                        action="prompt.delete",
                        resource_type="prompt",
                        resource_id=str(prompt_id),
                    )
                    # Invalidate cache
                    self._prompts_cache = None

                return success

        except Exception as exc:
            logger.error(
                "Failed to delete prompt",
                extra={"event": "prompt.delete.failure", "resource_id": str(prompt_id)},
                exc_info=exc,
            )
            return False

    def delete_prompts_bulk(self, prompt_ids: list[int]) -> dict[str, Any]:
        """Delete multiple prompts in a single operation.

        Args:
            prompt_ids (List[int]): List of prompt IDs to delete

        Returns:
            Dict[str, Any]: Dictionary containing:
                - deleted_ids: List of successfully deleted IDs
                - failed_ids: List of IDs that failed (non-existent)
                - deleted_count: Number of successful deletions
                - failed_count: Number of failures
        """
        deleted_ids = []
        failed_ids = []

        try:
            with get_db_session() as session:
                prompt_repo = PromptRepository(session)

                for prompt_id in prompt_ids:
                    success = prompt_repo.delete(prompt_id)

                    if success:
                        deleted_ids.append(prompt_id)
                        logging_service.log_audit_event(
                            action="prompt.delete",
                            resource_type="prompt",
                            resource_id=str(prompt_id),
                            status="success",
                        )
                    else:
                        failed_ids.append(prompt_id)
                        logging_service.log_audit_event(
                            action="prompt.delete",
                            resource_type="prompt",
                            resource_id=str(prompt_id),
                            status="failure",
                            error="Prompt not found",
                        )

                # Invalidate cache
                self._prompts_cache = None

        except Exception as exc:
            logger.error(
                "Failed to delete prompts in bulk",
                extra={"event": "prompt.delete_bulk.failure"},
                exc_info=exc,
            )

        return {
            "deleted_ids": deleted_ids,
            "failed_ids": failed_ids,
            "deleted_count": len(deleted_ids),
            "failed_count": len(failed_ids),
        }

    def clear_all_prompts(self) -> bool:
        """Clear all prompts and reset the data service to initial state.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                prompts = prompt_repo.get_all()

                for prompt in prompts:
                    prompt_repo.delete(prompt.id)

                logging_service.log_audit_event(
                    action="prompt.clear_all",
                    resource_type="prompt",
                    resource_id="all",
                )

                # Invalidate caches
                self._prompts_cache = None
                self._categories_cache = None
                self._tags_cache = None

                return True

        except Exception as exc:
            logger.error(
                "Failed to clear all prompts",
                extra={"event": "prompts.clear.failure"},
                exc_info=exc,
            )
            raise DataPersistenceError(
                "Unable to clear prompt storage.", context={}
            ) from exc

    def get_prompt_data(self, prompt_id: int) -> dict[str, Any]:
        """Get the current data for a prompt.

        Args:
            prompt_id (int): The ID of the prompt

        Returns:
            Dict[str, Any]: The prompt data, or empty dict if not found
        """
        try:
            with get_db_session() as session:
                prompt_repo = PromptRepository(session)
                prompt = prompt_repo.get_by_id(prompt_id)

                if prompt:
                    return {
                        "title": prompt.title,
                        "prompt": prompt.prompt,
                        "category": (
                            prompt.category.name if prompt.category else "No category"
                        ),
                        "tags": [tag.name for tag in prompt.tags],
                        "note": prompt.note or "",
                        "favorite": prompt.favorite,
                    }

                return {}

        except Exception as exc:
            logger.error(
                "Failed to get prompt data",
                extra={"event": "prompt.get.failure", "resource_id": str(prompt_id)},
                exc_info=exc,
            )
            return {}

    def get_prompt_versions(self, prompt_id: int) -> list[dict[str, Any]]:
        """Get the version history for a prompt.

        Args:
            prompt_id (int): The ID of the prompt

        Returns:
            List[Dict[str, Any]]: The version history, or empty list if not found
        """
        try:
            with get_db_session() as session:
                version_repo = VersionRepository(session)
                versions = version_repo.get_versions_for_prompt(prompt_id)

                return [self._version_to_dict(v) for v in versions]

        except Exception as exc:
            logger.error(
                "Failed to get prompt versions",
                extra={
                    "event": "prompt.versions.get.failure",
                    "resource_id": str(prompt_id),
                },
                exc_info=exc,
            )
            return []

    def revert_prompt_to_version(
        self,
        prompt_id: int,
        reverted_data: dict[str, Any],
        commit_message: str,
        author: str | None = None,
    ) -> bool:
        """Revert a prompt to a specific version.

        Args:
            prompt_id (int): The ID of the prompt to revert
            reverted_data (Dict[str, Any]): The data to revert to
            commit_message (str): The commit message
            author (Optional[str]): Username to attribute the new version to
                (the acting grantee, when reverted via an edit share grant)

        Returns:
            bool: True if successful, False otherwise
        """
        # Reuse update_prompt with reverted data
        return self.update_prompt(
            prompt_id, reverted_data, commit_message, author=author
        )

    def create_prompt(self, data: dict[str, Any]) -> int:
        """Create a new prompt (alias for add_new_prompt).

        Args:
            data (Dict[str, Any]): The prompt data

        Returns:
            int: The ID of the new prompt
        """
        return self.add_new_prompt(data)

    def get_categories(self) -> list[str]:
        """Get all categories.

        Returns:
            List[str]: List of categories
        """
        try:
            with get_db_session() as session:
                category_repo = CategoryRepository(session)
                categories = category_repo.get_all()
                # Filter out empty category names
                return sorted([cat.name for cat in categories if cat.name.strip()])

        except Exception as exc:
            logger.error(
                "Failed to get categories",
                extra={"event": "categories.get.failure"},
                exc_info=exc,
            )
            return []

    def get_tags(self) -> list[str]:
        """Get all tags.

        Returns:
            List[str]: List of tags
        """
        try:
            with get_db_session() as session:
                tag_repo = TagRepository(session)
                tags = tag_repo.get_all()
                return sorted([tag.name for tag in tags])

        except Exception as exc:
            logger.error(
                "Failed to get tags", extra={"event": "tags.get.failure"}, exc_info=exc
            )
            return []

    def get_tags_with_counts(self) -> list[dict[str, Any]]:
        """Get all tags with their usage counts.

        Returns:
            List[Dict[str, Any]]: List of dictionaries with 'name' and 'count' keys,
                                  sorted by tag name
        """
        try:
            with get_db_session() as session:
                tag_repo = TagRepository(session)
                results = tag_repo.list_all_with_counts()
                return [
                    {"name": tag.name, "count": count or 0} for tag, count in results
                ]
        except Exception as exc:
            logger.error(
                "Failed to get tags with counts",
                extra={"event": "tags.get_counts.failure"},
                exc_info=exc,
            )
            return []

    def get_all_tags_from_prompts(self) -> set[str]:
        """Get all unique tags from all prompts.

        Returns:
            Set[str]: Set of all tags
        """
        return set(self.get_tags())

    def _update_categories_and_tags(self) -> None:
        """Update categories and tags from current prompts.

        NOTE: This is a no-op for database backend as categories and tags
        are managed automatically via get-or-create pattern.
        """
        pass

    def _reset_state(self) -> None:
        """Reset in-memory caches."""
        self._prompts_cache = None
        self._categories_cache = None
        self._tags_cache = None

    def grant_share(
        self,
        prompt_id: int,
        identifier: str,
        permission: str,
        acting_user: User,
    ) -> dict[str, Any]:
        """Grant (or update) a prompt share to another user.

        Resolves ``identifier`` as a username or email of an active user,
        rejects self-share and sharing to the prompt's own owner, and
        upserts the grant. All rejection paths raise the same
        :class:`ShareGrantError` (FR-010, SC-006 — no user enumeration).

        Args:
            prompt_id: Prompt being shared. Must be visible to acting_user
                via any path (ownership, admin, or legacy_public) — callers
                are expected to have already checked owner-level access.
            identifier: Username or email of the grantee.
            permission: 'read' or 'edit'.
            acting_user: The user creating/updating the grant.

        Returns:
            Dict[str, Any]: The created/updated PromptShare, serialized.

        Raises:
            ShareGrantError: Prompt not found, unknown/inactive grantee,
                self-share, or sharing to the owner.
        """
        with get_db_session() as session:
            prompt_repo = PromptRepository(session)
            user_repo = UserRepository(session)
            sharing_repo = SharingRepository(session)

            prompt = prompt_repo.get_by_id(prompt_id)
            if not prompt:
                raise ShareGrantError(
                    "Prompt not found", context={"prompt_id": prompt_id}
                )

            grantee = user_repo.get_by_email_or_username(identifier)
            if not grantee or not grantee.is_active:
                raise ShareGrantError(
                    "Unknown or inactive grantee", context={"prompt_id": prompt_id}
                )

            if grantee.id == acting_user.id:
                raise ShareGrantError(
                    "Cannot share a prompt with yourself",
                    context={"prompt_id": prompt_id},
                )

            if grantee.id == prompt.user_id:
                raise ShareGrantError(
                    "Cannot share a prompt with its owner",
                    context={"prompt_id": prompt_id},
                )

            share = sharing_repo.upsert(
                prompt_id=prompt_id,
                grantee_user_id=grantee.id,
                permission=permission,
                granted_by=acting_user.id,
            )
            session.flush()

            logging_service.log_audit_event(
                action="prompt.share.granted",
                resource_type="prompt",
                resource_id=str(prompt_id),
                actor=acting_user.username,
                grantee=grantee.username,
                permission=permission,
            )

            granter = user_repo.get_by_id(acting_user.id) if acting_user.id else None

            return {
                "prompt_id": prompt_id,
                "grantee": {"id": grantee.id, "username": grantee.username},
                "permission": share.permission,
                "granted_by": granter.username if granter else None,
                "created_at": share.created_at,
                "updated_at": share.updated_at,
            }

    def list_shares(self, prompt_id: int) -> dict[str, Any]:
        """List all grants on a prompt (grant review, US3).

        Callers are expected to have already checked owner-level access
        (``check_prompt_access(prompt, user, "owner", db)``) before calling.

        Args:
            prompt_id: Prompt whose grants are being listed.

        Returns:
            Dict[str, Any]: ``{"prompt_id": ..., "shares": [...]}`` with each
            share serialized the same shape as :meth:`grant_share`'s result.
        """
        with get_db_session() as session:
            sharing_repo = SharingRepository(session)
            user_repo = UserRepository(session)

            shares = sharing_repo.list_for_prompt(prompt_id)

            grantee_ids = {share.grantee_user_id for share in shares}
            granter_ids = {share.granted_by for share in shares if share.granted_by}
            users_by_id = {
                u.id: u
                for u in (user_repo.get_by_id(uid) for uid in grantee_ids | granter_ids)
                if u is not None
            }

            serialized = []
            for share in shares:
                grantee = users_by_id.get(share.grantee_user_id)
                granter = (
                    users_by_id.get(share.granted_by) if share.granted_by else None
                )
                serialized.append(
                    {
                        "prompt_id": prompt_id,
                        "grantee": {
                            "id": share.grantee_user_id,
                            "username": grantee.username if grantee else "",
                        },
                        "permission": share.permission,
                        "granted_by": granter.username if granter else None,
                        "created_at": share.created_at,
                        "updated_at": share.updated_at,
                    }
                )

            return {"prompt_id": prompt_id, "shares": serialized}

    def revoke_share(
        self, prompt_id: int, grantee_user_id: str, acting_user: User
    ) -> bool:
        """Revoke a prompt share grant (owner/admin only, US3).

        Callers are expected to have already checked owner-level access.

        Args:
            prompt_id: Prompt the grant belongs to.
            grantee_user_id: Grantee whose access is being revoked.
            acting_user: The user performing the revocation (for audit).

        Returns:
            bool: True if a grant was found and removed, False otherwise.
        """
        with get_db_session() as session:
            sharing_repo = SharingRepository(session)

            revoked_permission = sharing_repo.permission_for(prompt_id, grantee_user_id)
            removed = sharing_repo.revoke(prompt_id, grantee_user_id)

            if removed:
                logging_service.log_audit_event(
                    action="prompt.share.revoked",
                    resource_type="prompt",
                    resource_id=str(prompt_id),
                    actor=acting_user.username,
                    grantee=grantee_user_id,
                    permission=revoked_permission,
                    status="success",
                )
            else:
                logging_service.log_audit_event(
                    action="prompt.share.revoked",
                    resource_type="prompt",
                    resource_id=str(prompt_id),
                    actor=acting_user.username,
                    grantee=grantee_user_id,
                    status="failure",
                    error="No grant found for that user on this prompt",
                )

            return removed

    def set_legacy_public(self, prompt_id: int, acting_user: User) -> int:
        """Un-grandfather a legacy-public prompt (owner/admin only, US3).

        Flips ``Prompt.legacy_public`` from ``True`` to ``False``. One-way —
        callers must reject a request to set it back to ``True`` before
        calling this (contracts §4b, FR-018). Creates no ``PromptShare`` rows;
        anyone who could previously view the prompt only via ``legacy_public``
        loses that access immediately unless separately granted a share.

        Callers are expected to have already checked owner-level access.
        Serializing the updated prompt for the API response is the caller's
        responsibility — the service layer doesn't depend on web-layer
        serialization helpers.

        Args:
            prompt_id: Prompt being un-grandfathered.
            acting_user: The user performing the action (for audit).

        Returns:
            int: The updated prompt's ID.

        Raises:
            ShareGrantError: Prompt not found, or already ``legacy_public=False``.
        """
        with get_db_session() as session:
            prompt_repo = PromptRepository(session)

            prompt = prompt_repo.get_by_id(prompt_id)
            if not prompt:
                raise ShareGrantError(
                    "Prompt not found", context={"prompt_id": prompt_id}
                )
            if not prompt.legacy_public:
                raise ShareGrantError(
                    "Prompt is not legacy-public",
                    context={"prompt_id": prompt_id},
                )

            prompt.legacy_public = False
            session.flush()

            logging_service.log_audit_event(
                action="prompt.legacy_public.revoked",
                resource_type="prompt",
                resource_id=str(prompt_id),
                actor=acting_user.username,
            )

            return prompt.id
