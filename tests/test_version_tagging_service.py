# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Unit tests for VersionTaggingService covering tag lifecycle, search, and statistics.
"""

import re

import pytest

from src.services.version_tagging_service import VersionTaggingService


class TestTagCreation:
    """Tests for creating tags."""

    def test_create_tag_with_description(self):
        service = VersionTaggingService()

        tag = service.create_tag("version-1", "stable", "Ready for production")

        assert tag["version_id"] == "version-1"
        assert tag["tag_name"] == "stable"
        assert tag["description"] == "Ready for production"
        assert tag["created_at"].endswith("Z")
        assert tag["color"] == "#27ae60"
        assert tag["tag_id"] == "version-1_stable"

    def test_create_tag_without_description(self):
        service = VersionTaggingService()

        tag = service.create_tag("version-2", "beta")

        assert tag["description"] == ""
        assert tag["color"] == "#f39c12"

    def test_tag_id_generation_is_unique_per_name(self):
        service = VersionTaggingService()

        tag1 = service.create_tag("version-1", "review")
        tag2 = service.create_tag("version-1", "stable")

        assert tag1["tag_id"] != tag2["tag_id"]


class TestTagManagement:
    """Tests for adding and removing tags."""

    def test_add_tag_to_version_creates_tag_list(self):
        service = VersionTaggingService()
        version_info = {}

        updated = service.add_tag_to_version(version_info, "stable", "Stable release")

        assert "tags" in updated
        assert len(updated["tags"]) == 1
        assert updated["tags"][0]["tag_name"] == "stable"

    def test_add_duplicate_tag_is_noop(self):
        service = VersionTaggingService()
        version_info = {
            "tags": [
                {"tag_name": "stable", "description": "Stable", "color": "#27ae60"}
            ]
        }

        updated = service.add_tag_to_version(version_info, "stable", "Stable again")

        assert len(updated["tags"]) == 1

    def test_remove_existing_tag(self):
        service = VersionTaggingService()
        version_info = {"tags": [{"tag_name": "stable"}, {"tag_name": "beta"}]}

        updated = service.remove_tag_from_version(version_info, "beta")

        assert len(updated["tags"]) == 1
        assert updated["tags"][0]["tag_name"] == "stable"

    def test_remove_nonexistent_tag(self):
        service = VersionTaggingService()
        version_info = {"tags": [{"tag_name": "stable"}]}

        updated = service.remove_tag_from_version(version_info, "beta")

        assert len(updated["tags"]) == 1

    def test_delete_tag_returns_boolean(self):
        service = VersionTaggingService()
        assert service.delete_tag("version-1", "stable") is True

    def test_get_version_tags_handles_missing_field(self):
        service = VersionTaggingService()
        assert service.get_version_tags({}) == []

    def test_get_predefined_tags_returns_templates(self):
        service = VersionTaggingService()
        tags = service.get_predefined_tags()

        assert isinstance(tags, list)
        assert any(tag["name"] == "stable" for tag in tags)


class TestTagSearchAndStatistics:
    """Tests search and statistics helpers."""

    def test_search_versions_by_tag(self):
        service = VersionTaggingService()
        versions = [
            {"version_id": "v1", "tags": [{"tag_name": "stable"}]},
            {"version_id": "v2", "tags": [{"tag_name": "beta"}]},
            {"version_id": "v3", "tags": [{"tag_name": "stable"}]},
        ]

        stable_versions = service.search_versions_by_tag(versions, "stable")

        assert len(stable_versions) == 2
        assert {v["version_id"] for v in stable_versions} == {"v1", "v3"}

    def test_search_versions_by_tag_no_matches(self):
        service = VersionTaggingService()
        versions = [{"version_id": "v1", "tags": [{"tag_name": "stable"}]}]

        result = service.search_versions_by_tag(versions, "beta")

        assert result == []

    def test_tag_statistics_counts_usage(self):
        service = VersionTaggingService()
        versions = [
            {"tags": [{"tag_name": "stable"}, {"tag_name": "beta"}]},
            {"tags": [{"tag_name": "stable"}]},
            {},
        ]

        stats = service.get_tag_statistics(versions)

        assert stats["stable"] == 2
        assert stats["beta"] == 1

    def test_tag_statistics_empty_versions(self):
        service = VersionTaggingService()

        stats = service.get_tag_statistics([])

        assert stats == {}


class TestTagColors:
    """Tests for color assignment edge cases."""

    def test_predefined_color_mapping(self):
        service = VersionTaggingService()

        tag = service.create_tag("version-1", "production")

        assert tag["color"] == "#2ecc71"

    def test_hash_based_color_generation(self):
        service = VersionTaggingService()

        tag = service.create_tag("version-1", "custom-tag")

        assert re.match(r"^#[0-9a-fA-F]{6}$", tag["color"])
