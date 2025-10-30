import uuid
from datetime import datetime
import getpass
from typing import Dict, Any, List, Optional


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
        return datetime.utcnow().isoformat() + "Z"

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
