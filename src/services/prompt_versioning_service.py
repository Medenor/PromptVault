# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import uuid
import getpass
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.db.repositories.version_repository import VersionRepository


@dataclass
class VersionConflictResult:
    """Result of checking a client's expected prompt version against the server's current version."""

    has_conflict: bool
    current_version: int


def check_version_conflict(
    version_repo: VersionRepository, prompt_id: int, expected_version: Optional[int]
) -> VersionConflictResult:
    """Compare a client-supplied `expected_version` against the prompt's current version.

    Used by the offline-sync conflict-detection contract (specs/004-mobile-responsive-ui):
    when a queued offline edit is replayed, the client sends the version it last saw
    (`expected_version`). If the server's current version has since advanced, this
    surfaces as a conflict instead of silently overwriting the newer server-side write.

    Args:
        version_repo: VersionRepository bound to the active DB session
        prompt_id: Prompt being updated
        expected_version: The version the client last saw, or None if not supplied
            (backward-compatible — non-offline clients never send this)

    Returns:
        VersionConflictResult with has_conflict=False when expected_version is None
        (no check requested) or matches the current version.
    """
    latest = version_repo.get_latest_version(prompt_id)
    current_version = latest.version_number if latest else 0

    if expected_version is None:
        return VersionConflictResult(has_conflict=False, current_version=current_version)

    return VersionConflictResult(
        has_conflict=expected_version != current_version,
        current_version=current_version,
    )


def _utc_now_iso_z() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class PromptVersioningService:
    """Service for handling prompt versioning operations."""

    def __init__(self):
        """Initialize the PromptVersioningService."""
        pass

    def generate_version_id(self) -> str:
        """
        Generate a unique version ID.

        Returns:
            str: A unique version ID
        """
        return str(uuid.uuid4())

    def get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.

        Returns:
            str: Current timestamp
        """
        return _utc_now_iso_z()

    def get_current_user(self) -> str:
        """
        Get the current user.

        Returns:
            str: Current user name
        """
        try:
            return getpass.getuser()
        except Exception:
            return "unknown"

    def create_initial_version(
        self, data: Dict[str, Any], commit_message: str = "Initial commit"
    ) -> Dict[str, Any]:
        """
        Create an initial version for a new prompt.

        Args:
            data (Dict[str, Any]): The prompt data
            commit_message (str): The commit message

        Returns:
            Dict[str, Any]: The initial version
        """
        version_id = self.generate_version_id()
        return {
            "version_id": version_id,
            "timestamp": self.get_current_timestamp(),
            "author": self.get_current_user(),
            "message": commit_message,
            "data": data,
            "parents": [],
        }

    def create_new_version(
        self,
        data: Dict[str, Any],
        parent_version_id: Optional[str],
        commit_message: str = "Update",
    ) -> Dict[str, Any]:
        """
        Create a new version for an existing prompt.

        Args:
            data (Dict[str, Any]): The prompt data
            parent_version_id (Optional[str]): The parent version ID
            commit_message (str): The commit message

        Returns:
            Dict[str, Any]: The new version
        """
        version_id = self.generate_version_id()
        parents = [parent_version_id] if parent_version_id else []

        return {
            "version_id": version_id,
            "timestamp": self.get_current_timestamp(),
            "author": self.get_current_user(),
            "message": commit_message,
            "data": data,
            "parents": parents,
        }

    def get_prompt_versions(self, prompt_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get the version history for a prompt.

        Args:
            prompt_info (Dict[str, Any]): The prompt information

        Returns:
            List[Dict[str, Any]]: The version history
        """
        return prompt_info.get("versions", [])

    def get_latest_version_id(self, prompt_info: Dict[str, Any]) -> Optional[str]:
        """
        Get the latest version ID for a prompt.

        Args:
            prompt_info (Dict[str, Any]): The prompt information

        Returns:
            Optional[str]: The latest version ID, or None if not found
        """
        branches = prompt_info.get("branches", {})
        return branches.get("main")

    def revert_to_version(
        self,
        prompt_info: Dict[str, Any],
        reverted_data: Dict[str, Any],
        commit_message: str,
    ) -> Dict[str, Any]:
        """
        Revert a prompt to a specific version.

        Args:
            prompt_info (Dict[str, Any]): The prompt information
            reverted_data (Dict[str, Any]): The data to revert to
            commit_message (str): The commit message

        Returns:
            Dict[str, Any]: The new version
        """
        # Create a new version with the reverted data
        parent_version_id = prompt_info["branches"].get("main")
        parents = [parent_version_id] if parent_version_id else []

        version_id = self.generate_version_id()
        new_version = {
            "version_id": version_id,
            "timestamp": self.get_current_timestamp(),
            "author": self.get_current_user(),
            "message": commit_message,
            "data": reverted_data,
            "parents": parents,
        }

        return new_version
