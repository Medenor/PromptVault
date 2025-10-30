"""Service for handling version tagging and labeling operations."""

from typing import Dict, Any, List, Optional
from datetime import datetime


class VersionTaggingService:
    """Service for managing version tags and labels."""

    def __init__(self):
        """Initialize the VersionTaggingService."""
        pass

    def create_tag(
        self, version_id: str, tag_name: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a tag for a specific version.

        Args:
            version_id (str): The version ID to tag
            tag_name (str): The name of the tag
            description (str): Optional description of the tag

        Returns:
            Dict[str, Any]: The created tag object
        """
        return {
            "tag_id": f"{version_id}_{tag_name}",
            "version_id": version_id,
            "tag_name": tag_name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "color": self._get_tag_color(tag_name),
        }

    def delete_tag(self, version_id: str, tag_name: str) -> bool:
        """
        Delete a tag from a version.

        Args:
            version_id (str): The version ID
            tag_name (str): The tag name to delete

        Returns:
            bool: True if successful
        """
        return True

    def get_version_tags(self, version_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get all tags for a version.

        Args:
            version_info (Dict[str, Any]): The version information

        Returns:
            List[Dict[str, Any]]: List of tags
        """
        return version_info.get("tags", [])

    def add_tag_to_version(
        self, version_info: Dict[str, Any], tag_name: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        Add a tag to a version.

        Args:
            version_info (Dict[str, Any]): The version information
            tag_name (str): The tag name
            description (str): Optional description

        Returns:
            Dict[str, Any]: Updated version info
        """
        if "tags" not in version_info:
            version_info["tags"] = []

        # Check if tag already exists
        for tag in version_info["tags"]:
            if tag["tag_name"] == tag_name:
                return version_info

        # Add new tag
        new_tag = {
            "tag_name": tag_name,
            "description": description,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "color": self._get_tag_color(tag_name),
        }
        version_info["tags"].append(new_tag)

        return version_info

    def remove_tag_from_version(
        self, version_info: Dict[str, Any], tag_name: str
    ) -> Dict[str, Any]:
        """
        Remove a tag from a version.

        Args:
            version_info (Dict[str, Any]): The version information
            tag_name (str): The tag name to remove

        Returns:
            Dict[str, Any]: Updated version info
        """
        if "tags" in version_info:
            version_info["tags"] = [
                tag for tag in version_info["tags"] if tag["tag_name"] != tag_name
            ]

        return version_info

    def get_predefined_tags(self) -> List[Dict[str, str]]:
        """
        Get predefined tag templates.

        Returns:
            List[Dict[str, str]]: List of predefined tags
        """
        return [
            {"name": "stable", "description": "Stable version", "color": "#27ae60"},
            {"name": "beta", "description": "Beta version", "color": "#f39c12"},
            {
                "name": "deprecated",
                "description": "Deprecated version",
                "color": "#e74c3c",
            },
            {"name": "review", "description": "Under review", "color": "#3498db"},
            {
                "name": "production",
                "description": "Production ready",
                "color": "#2ecc71",
            },
            {"name": "archive", "description": "Archived version", "color": "#95a5a6"},
        ]

    def _get_tag_color(self, tag_name: str) -> str:
        """
        Get a color for a tag based on its name.

        Args:
            tag_name (str): The tag name

        Returns:
            str: Hex color code
        """
        tag_colors = {
            "stable": "#27ae60",
            "beta": "#f39c12",
            "deprecated": "#e74c3c",
            "review": "#3498db",
            "production": "#2ecc71",
            "archive": "#95a5a6",
            "important": "#e91e63",
            "wip": "#9c27b0",
        }

        tag_lower = tag_name.lower()
        if tag_lower in tag_colors:
            return tag_colors[tag_lower]

        # Generate color based on tag name hash
        hash_value = hash(tag_name) % 0xFFFFFF
        return f"#{hash_value:06x}"

    def search_versions_by_tag(
        self, versions: List[Dict[str, Any]], tag_name: str
    ) -> List[Dict[str, Any]]:
        """
        Search for versions with a specific tag.

        Args:
            versions (List[Dict[str, Any]]): List of versions
            tag_name (str): The tag to search for

        Returns:
            List[Dict[str, Any]]: Versions with the tag
        """
        matching_versions = []

        for version in versions:
            tags = version.get("tags", [])
            for tag in tags:
                if tag["tag_name"] == tag_name:
                    matching_versions.append(version)
                    break

        return matching_versions

    def get_tag_statistics(self, versions: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Get statistics about tag usage.

        Args:
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            Dict[str, int]: Tag usage counts
        """
        tag_stats = {}

        for version in versions:
            tags = version.get("tags", [])
            for tag in tags:
                tag_name = tag["tag_name"]
                tag_stats[tag_name] = tag_stats.get(tag_name, 0) + 1

        return tag_stats
