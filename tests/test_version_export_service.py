# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Unit tests for VersionExportService covering history, single version, and comparison exports.
"""

import json

import pytest


class TestVersionHistoryExport:
    """Tests for exporting full version histories."""

    def test_export_history_as_json(self, export_service, sample_version_data):
        versions = [
            sample_version_data(version_id="v1", message="Initial", parents=[]),
            sample_version_data(version_id="v2", message="Update", parents=["v1"]),
        ]

        result = export_service.export_version_history("123", versions, format="json")
        payload = json.loads(result)

        assert payload["prompt_id"] == "123"
        assert payload["total_versions"] == 2
        assert payload["versions"][1]["message"] == "Update"

    def test_export_history_as_csv(self, export_service, sample_version_data):
        versions = [
            sample_version_data(
                version_id="v1",
                message="Message, with, commas",
                parents=[],
                data={"title": "Title"},
            ),
            sample_version_data(
                version_id="v2",
                message="Second",
                parents=["v1"],
                data={"title": "Other"},
            ),
        ]

        csv_output = export_service.export_version_history(
            "123", versions, format="csv"
        )

        lines = csv_output.splitlines()
        assert lines[0].startswith("Version ID")
        assert '"Message; with; commas"' in lines[1]  # commas converted to semicolons
        assert '"v2"' in lines[2]

    def test_export_history_as_markdown(self, export_service, sample_version_data):
        versions = [
            sample_version_data(version_id="abc12345", message="Init"),
            sample_version_data(version_id="def67890", message="Update"),
        ]

        markdown = export_service.export_version_history(
            "321", versions, format="markdown"
        )

        assert "# Version History for Prompt 321" in markdown
        assert "**Total Versions:** 2" in markdown
        assert "Version 1: abc12345" in markdown
        assert "Version 2: def67890" in markdown

    def test_export_empty_version_list(self, export_service):
        markdown = export_service.export_version_history("555", [], format="markdown")

        assert "**Total Versions:** 0" in markdown

    def test_export_history_with_unicode(self, export_service, sample_version_data):
        versions = [
            sample_version_data(
                message="Unicode 🚀",
                data={"title": "你好", "prompt": "Contenido", "category": "Test"},
            )
        ]

        json_output = export_service.export_version_history(
            "unicode", versions, format="json"
        )
        payload = json.loads(json_output)

        assert payload["versions"][0]["message"] == "Unicode 🚀"
        assert payload["versions"][0]["data"]["title"] == "你好"

    def test_export_history_invalid_format(self, export_service, sample_version_data):
        versions = [sample_version_data()]

        with pytest.raises(ValueError):
            export_service.export_version_history("id", versions, format="pdf")


class TestSingleVersionExport:
    """Tests for exporting a single version."""

    def test_export_single_version_json(self, export_service, sample_version_data):
        version = sample_version_data(version_id="solo")

        output = export_service.export_single_version(version, format="json")

        payload = json.loads(output)
        assert payload["version_id"] == "solo"

    def test_export_single_version_markdown(self, export_service, sample_version_data):
        version = sample_version_data(
            version_id="solo",
            data={
                "title": "API Prompt",
                "prompt": "Explain FastAPI",
                "category": "Docs",
                "tags": ["fastapi", "docs"],
            },
            message="Documented",
        )

        markdown = export_service.export_single_version(version, format="markdown")

        assert "# Version solo" in markdown
        assert "Explain FastAPI" in markdown
        assert "`fastapi`" in markdown

    def test_export_single_version_missing_fields(self, export_service):
        version = {"version_id": "v1", "message": "Partial data"}

        markdown = export_service.export_single_version(version, format="markdown")

        assert "Version v1" in markdown
        assert "Partial data" in markdown

    def test_export_single_version_invalid_format(
        self, export_service, sample_version_data
    ):
        version = sample_version_data()

        with pytest.raises(ValueError):
            export_service.export_single_version(version, format="xml")


class TestComparisonExport:
    """Tests for exporting comparisons between versions."""

    def test_export_comparison_json(self, export_service, sample_version_data):
        v1 = sample_version_data(version_id="a1", data={"title": "First"})
        v2 = sample_version_data(version_id="a2", data={"title": "Second"})
        changes = {"title": {"old": "First", "new": "Second"}}

        output = export_service.export_version_comparison(
            v1, v2, changes, format="json"
        )
        payload = json.loads(output)

        assert payload["v1_id"] == "a1"
        assert payload["changes"]["title"]["new"] == "Second"

    def test_export_comparison_markdown(self, export_service, sample_version_data):
        v1 = sample_version_data(
            version_id="11111111", timestamp="2024-01-01T00:00:00Z"
        )
        v2 = sample_version_data(
            version_id="22222222", timestamp="2024-01-02T00:00:00Z"
        )
        changes = {
            "prompt": {"old": "Old content", "new": "New content"},
            "note": {"old": "Old note", "new": "New note"},
        }

        markdown = export_service.export_version_comparison(
            v1, v2, changes, format="markdown"
        )

        assert "Version Comparison" in markdown
        assert "Old content" in markdown
        assert "New note" in markdown

    def test_export_comparison_no_changes(self, export_service, sample_version_data):
        v1 = sample_version_data(version_id="abc")
        v2 = sample_version_data(version_id="def")

        markdown = export_service.export_version_comparison(
            v1, v2, {}, format="markdown"
        )

        assert "No changes between these versions." in markdown


class TestUtilityFunctions:
    """Tests for helper utilities."""

    def test_get_export_filename_default_extensions(self, export_service):
        filename = export_service.get_export_filename("42", "json")

        assert filename.startswith("prompt_42_versions_")
        assert filename.endswith(".json")

    def test_get_export_filename_markdown_extension(self, export_service):
        filename = export_service.get_export_filename("42", "markdown")

        assert filename.endswith(".md")
