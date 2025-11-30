# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Service for handling version export operations."""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def _utc_now_iso_z() -> str:
    """Return current UTC time in ISO format with Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class VersionExportService:
    """Service for exporting version history and data."""

    def __init__(self):
        """Initialize the VersionExportService."""
        pass

    def export_version_history(
        self, prompt_id: str, versions: List[Dict[str, Any]], format: str = "json"
    ) -> str:
        """
        Export version history in specified format.

        Args:
            prompt_id (str): The prompt ID
            versions (List[Dict[str, Any]]): List of versions to export
            format (str): Export format (json, csv, markdown)

        Returns:
            str: Exported data as string
        """
        if format == "json":
            return self._export_as_json(prompt_id, versions)
        elif format == "csv":
            return self._export_as_csv(prompt_id, versions)
        elif format == "markdown":
            return self._export_as_markdown(prompt_id, versions)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_as_json(self, prompt_id: str, versions: List[Dict[str, Any]]) -> str:
        """
        Export version history as JSON.

        Args:
            prompt_id (str): The prompt ID
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            str: JSON string
        """
        export_data = {
            "prompt_id": prompt_id,
            "export_date": _utc_now_iso_z(),
            "total_versions": len(versions),
            "versions": versions,
        }
        return json.dumps(export_data, indent=2)

    def _export_as_csv(self, prompt_id: str, versions: List[Dict[str, Any]]) -> str:
        """
        Export version history as CSV.

        Args:
            prompt_id (str): The prompt ID
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            str: CSV string
        """
        lines = []
        lines.append("Version ID,Timestamp,Author,Message,Tags,Parent Versions")

        for version in versions:
            version_id = version.get("version_id", "")
            timestamp = version.get("timestamp", "")
            author = version.get("author", "")
            message = version.get("message", "").replace(",", ";")  # Escape commas
            tags = ",".join(
                [tag.get("tag_name", "") for tag in version.get("tags", [])]
            )
            parents = ",".join(version.get("parents", []))

            line = f'"{version_id}","{timestamp}","{author}","{message}","{tags}","{parents}"'
            lines.append(line)

        return "\n".join(lines)

    def _export_as_markdown(
        self, prompt_id: str, versions: List[Dict[str, Any]]
    ) -> str:
        """
        Export version history as Markdown.

        Args:
            prompt_id (str): The prompt ID
            versions (List[Dict[str, Any]]): List of versions

        Returns:
            str: Markdown string
        """
        lines = []
        lines.append(f"# Version History for Prompt {prompt_id}\n")
        lines.append(f"**Export Date:** {_utc_now_iso_z()}\n")
        lines.append(f"**Total Versions:** {len(versions)}\n")
        lines.append("---\n")

        for idx, version in enumerate(versions, 1):
            version_id = version.get("version_id", "")
            timestamp = version.get("timestamp", "")
            author = version.get("author", "")
            message = version.get("message", "")
            tags = version.get("tags", [])
            parents = version.get("parents", [])

            lines.append(f"## Version {idx}: {version_id[:8]}...\n")
            lines.append(f"**Timestamp:** {timestamp}\n")
            lines.append(f"**Author:** {author}\n")
            lines.append(f"**Message:** {message}\n")

            if tags:
                tag_names = ", ".join([f"`{tag.get('tag_name', '')}`" for tag in tags])
                lines.append(f"**Tags:** {tag_names}\n")

            if parents:
                lines.append(f"**Parent Versions:** {', '.join(parents)}\n")

            lines.append("---\n")

        return "\n".join(lines)

    def export_single_version(
        self, version: Dict[str, Any], format: str = "json"
    ) -> str:
        """
        Export a single version.

        Args:
            version (Dict[str, Any]): The version to export
            format (str): Export format (json, markdown)

        Returns:
            str: Exported data as string
        """
        if format == "json":
            return json.dumps(version, indent=2)
        elif format == "markdown":
            return self._format_version_as_markdown(version)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _format_version_as_markdown(self, version: Dict[str, Any]) -> str:
        """
        Format a single version as Markdown.

        Args:
            version (Dict[str, Any]): The version

        Returns:
            str: Markdown string
        """
        lines = []
        version_id = version.get("version_id", "")
        timestamp = version.get("timestamp", "")
        author = version.get("author", "")
        message = version.get("message", "")
        data = version.get("data", {})
        tags = version.get("tags", [])

        lines.append(f"# Version {version_id[:8]}...\n")
        lines.append(f"**Timestamp:** {timestamp}\n")
        lines.append(f"**Author:** {author}\n")
        lines.append(f"**Message:** {message}\n")

        if tags:
            tag_names = ", ".join([f"`{tag.get('tag_name', '')}`" for tag in tags])
            lines.append(f"**Tags:** {tag_names}\n")

        lines.append("---\n")
        lines.append("## Content\n")

        if data:
            if "title" in data:
                lines.append(f"### Title\n{data['title']}\n")
            if "prompt" in data:
                lines.append(f"### Prompt\n{data['prompt']}\n")
            if "category" in data:
                lines.append(f"### Category\n{data['category']}\n")
            if "tags" in data and isinstance(data["tags"], list):
                formatted_tags = ", ".join([f"`{tag}`" for tag in data["tags"]])
                lines.append(f"### Tags\n{formatted_tags}\n")

        return "\n".join(lines)

    def export_version_comparison(
        self,
        v1: Dict[str, Any],
        v2: Dict[str, Any],
        changes: Dict[str, Any],
        format: str = "markdown",
    ) -> str:
        """
        Export a version comparison.

        Args:
            v1 (Dict[str, Any]): First version
            v2 (Dict[str, Any]): Second version
            changes (Dict[str, Any]): Changes between versions
            format (str): Export format (json, markdown)

        Returns:
            str: Exported comparison as string
        """
        if format == "json":
            return json.dumps(
                {
                    "v1_id": v1.get("version_id"),
                    "v2_id": v2.get("version_id"),
                    "changes": changes,
                },
                indent=2,
            )
        elif format == "markdown":
            return self._format_comparison_as_markdown(v1, v2, changes)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _format_comparison_as_markdown(
        self, v1: Dict[str, Any], v2: Dict[str, Any], changes: Dict[str, Any]
    ) -> str:
        """
        Format a version comparison as Markdown.

        Args:
            v1 (Dict[str, Any]): First version
            v2 (Dict[str, Any]): Second version
            changes (Dict[str, Any]): Changes between versions

        Returns:
            str: Markdown string
        """
        lines = []
        v1_id = v1.get("version_id", "")[:8]
        v2_id = v2.get("version_id", "")[:8]

        lines.append(f"# Version Comparison\n")
        lines.append(f"**From:** {v1_id}... ({v1.get('timestamp', '')})\n")
        lines.append(f"**To:** {v2_id}... ({v2.get('timestamp', '')})\n")
        lines.append("---\n")

        if not changes:
            lines.append("No changes between these versions.\n")
            return "\n".join(lines)

        for field, change in changes.items():
            lines.append(f"## {field.capitalize()}\n")

            old_value = change.get("old", "")
            new_value = change.get("new", "")

            lines.append("### Before\n")
            lines.append(f"```\n{old_value}\n```\n")

            lines.append("### After\n")
            lines.append(f"```\n{new_value}\n```\n")

        return "\n".join(lines)

    def get_export_filename(self, prompt_id: str, format: str) -> str:
        """
        Generate an export filename.

        Args:
            prompt_id (str): The prompt ID
            format (str): Export format

        Returns:
            str: Filename
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        extension = format if format in ["json", "csv", "md"] else "txt"
        if format == "markdown":
            extension = "md"

        return f"prompt_{prompt_id}_versions_{timestamp}.{extension}"
