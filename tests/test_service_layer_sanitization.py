# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for service-layer sanitization and defense-in-depth.

This test suite verifies that the service layer provides defense-in-depth
by sanitizing and validating data even if API-layer validation is bypassed.
"""

import pytest
from src.services.prompt_data_service import PromptDataService
from src.web.validators import sanitize_text_field, sanitize_tags, deduplicate_tags


class TestServiceLayerSanitization:
    """Test that service layer sanitizes data for defense-in-depth."""

    @pytest.fixture
    def data_service(self, tmp_path):
        """Create a temporary data service for testing."""
        temp_file = tmp_path / "test_prompts.json"
        service = PromptDataService(data_file_path=str(temp_file))
        return service

    def test_sanitize_title_with_control_characters(self, data_service):
        """Test that control characters are removed from titles."""
        malicious_data = {
            "title": "Test\x00Title\x07With\x1bControls",  # Null, bell, escape
            "prompt": "Content",
            "category": "Test",
            "tags": ["test"],
        }

        prompt_id = data_service.add_new_prompt(malicious_data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Control characters should be removed
        assert "\x00" not in saved_prompt["title"]
        assert "\x07" not in saved_prompt["title"]
        assert "\x1b" not in saved_prompt["title"]
        assert saved_prompt["title"] == "TestTitleWithControls"

    def test_sanitize_prompt_preserves_newlines(self, data_service):
        """Test that newlines are preserved in prompt content."""
        data = {
            "title": "Test",
            "prompt": "Line 1\nLine 2\nLine 3",
            "category": "Test",
            "tags": ["test"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Newlines should be preserved in prompt content
        assert "\n" in saved_prompt["prompt"]
        assert saved_prompt["prompt"].count("\n") == 2

    def test_sanitize_prompt_removes_control_characters(self, data_service):
        """Test that control characters (except newlines) are removed from prompts."""
        malicious_data = {
            "title": "Test",
            "prompt": "Content\x00with\x07null\x1band bell",
            "category": "Test",
            "tags": ["test"],
        }

        prompt_id = data_service.add_new_prompt(malicious_data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Control characters should be removed
        assert "\x00" not in saved_prompt["prompt"]
        assert "\x07" not in saved_prompt["prompt"]
        assert "\x1b" not in saved_prompt["prompt"]

    def test_tag_deduplication_case_insensitive(self, data_service):
        """Test that duplicate tags (case-insensitive) are removed."""
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "Test",
            "tags": ["python", "PYTHON", "Python", "coding", "CODING"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_tags = data_service.prompts[prompt_id]["data"]["tags"]

        # Should have unique tags (case-insensitive)
        assert len(saved_tags) == 2
        assert "python" in [t.lower() for t in saved_tags]
        assert "coding" in [t.lower() for t in saved_tags]

    def test_tag_limit_enforcement(self, data_service):
        """Test that tag count is limited to maximum."""
        # Create 60 tags (exceeds 50 limit)
        tags = [f"tag{i}" for i in range(60)]
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "Test",
            "tags": tags,
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_tags = data_service.prompts[prompt_id]["data"]["tags"]

        # Should be limited to 50 tags
        assert len(saved_tags) <= 50

    def test_tag_length_limit(self, data_service):
        """Test that individual tags are truncated to max length."""
        long_tag = "x" * 100  # Exceeds 50 character limit
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "Test",
            "tags": [long_tag, "short"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_tags = data_service.prompts[prompt_id]["data"]["tags"]

        # Long tag should be truncated
        assert all(len(tag) <= 50 for tag in saved_tags)

    def test_whitespace_normalization_in_category(self, data_service):
        """Test that excessive whitespace is normalized."""
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "  Test    Category   With     Spaces  ",
            "tags": ["test"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_category = data_service.prompts[prompt_id]["data"]["category"]

        # Excessive whitespace should be normalized
        assert "    " not in saved_category
        assert saved_category == "Test Category With Spaces"

    def test_length_limits_enforced(self, data_service):
        """Test that field length limits are enforced."""
        data = {
            "title": "x" * 300,  # Exceeds 200 limit
            "prompt": "y" * 60000,  # Exceeds 50000 limit
            "category": "z" * 150,  # Exceeds 100 limit
            "tags": ["test"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Fields should be truncated to limits
        assert len(saved_prompt["title"]) <= 200
        assert len(saved_prompt["prompt"]) <= 50000
        assert len(saved_prompt["category"]) <= 100

    def test_empty_tags_removed(self, data_service):
        """Test that empty/whitespace-only tags are removed."""
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "Test",
            "tags": ["valid", "", "   ", "also_valid", "\t"],
        }

        prompt_id = data_service.add_new_prompt(data)
        saved_tags = data_service.prompts[prompt_id]["data"]["tags"]

        # Only valid tags should remain
        assert len(saved_tags) == 2
        assert "valid" in saved_tags
        assert "also_valid" in saved_tags

    def test_update_prompt_also_sanitizes(self, data_service):
        """Test that updating a prompt also applies sanitization."""
        # Create initial prompt
        prompt_id = data_service.add_new_prompt(
            {
                "title": "Original",
                "prompt": "Content",
                "category": "Test",
                "tags": ["test"],
            }
        )

        # Update with malicious data
        malicious_update = {
            "title": "Updated\x00Title",
            "prompt": "New content",
            "category": "Updated",
            "tags": ["python", "PYTHON", "Python"],  # Duplicates
        }

        data_service.update_prompt(
            prompt_id, malicious_update, "Update with sanitization"
        )
        updated_prompt = data_service.prompts[prompt_id]["data"]

        # Control characters should be removed
        assert "\x00" not in updated_prompt["title"]
        # Tags should be deduplicated
        assert len(updated_prompt["tags"]) == 1


class TestSanitizationFunctions:
    """Test individual sanitization helper functions."""

    def test_sanitize_text_field_removes_controls(self):
        """Test control character removal."""
        text = "Hello\x00World\x07Test\x1b"
        result = sanitize_text_field(text)
        assert "\x00" not in result
        assert "\x07" not in result
        assert "\x1b" not in result

    def test_sanitize_text_field_normalizes_whitespace(self):
        """Test whitespace normalization."""
        text = "  Too    many     spaces   "
        result = sanitize_text_field(text, allow_newlines=False)
        assert result == "Too many spaces"

    def test_sanitize_text_field_preserves_newlines(self):
        """Test that newlines are preserved when requested."""
        text = "Line 1\nLine 2\nLine 3"
        result = sanitize_text_field(text, allow_newlines=True)
        assert "\n" in result
        assert result.count("\n") == 2

    def test_sanitize_text_field_enforces_max_length(self):
        """Test length limit enforcement."""
        text = "x" * 100
        result = sanitize_text_field(text, max_length=50)
        assert len(result) == 50

    def test_deduplicate_tags_preserves_order(self):
        """Test that tag order is preserved during deduplication."""
        tags = ["first", "second", "first", "third", "second"]
        result = deduplicate_tags(tags)
        assert result == ["first", "second", "third"]

    def test_deduplicate_tags_case_insensitive(self):
        """Test case-insensitive deduplication."""
        tags = ["Python", "PYTHON", "python", "Coding"]
        result = deduplicate_tags(tags)
        # Should keep first occurrence of each unique tag (case-insensitive)
        assert len(result) == 2
        assert result[0].lower() == "python"
        assert result[1].lower() == "coding"

    def test_sanitize_tags_comprehensive(self):
        """Test comprehensive tag sanitization."""
        tags = [
            "python",
            "PYTHON",  # Duplicate (case-insensitive)
            "  spaces  ",  # Whitespace
            "valid_tag",
            "x" * 100,  # Too long
            "",  # Empty
            "control\x00char",  # Control character
        ]
        result = sanitize_tags(tags, max_count=50, max_length_per_tag=50)

        # Should have deduplicated, sanitized tags
        assert len(result) <= 5
        # No duplicates
        lower_tags = [t.lower() for t in result]
        assert len(lower_tags) == len(set(lower_tags))
        # No empty tags
        assert all(tag for tag in result)
        # No control characters
        assert all("\x00" not in tag for tag in result)
        # Length limits enforced
        assert all(len(tag) <= 50 for tag in result)


class TestDefenseInDepth:
    """Test that service layer provides defense even if API validation fails."""

    @pytest.fixture
    def data_service(self, tmp_path):
        """Create a temporary data service for testing."""
        temp_file = tmp_path / "test_prompts.json"
        service = PromptDataService(data_file_path=str(temp_file))
        return service

    def test_direct_service_call_bypassing_api(self, data_service):
        """Test that calling service directly (bypassing API) still sanitizes."""
        # Simulate direct service call with malicious data
        malicious_data = {
            "title": "Malicious\x00\x07\x1bTitle",
            "prompt": "Content\x00with nulls",
            "category": "Test   Category",
            "tags": ["python", "Python", "PYTHON", "x" * 100],
        }

        prompt_id = data_service.create_prompt(malicious_data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Even though we bypassed API validation, service layer should sanitize
        assert "\x00" not in saved_prompt["title"]
        assert "\x07" not in saved_prompt["title"]
        assert len(saved_prompt["tags"]) == 2  # Deduplicated
        assert all(len(tag) <= 50 for tag in saved_prompt["tags"])

    def test_import_data_from_untrusted_source(self, data_service):
        """Test that importing data from external sources is sanitized."""
        # Simulate importing prompts from CSV/JSON with malicious content
        imported_data = {
            "title": "Imported\x00Prompt",
            "prompt": "Malicious content",
            "category": "Imported",
            "tags": ["import", "Import", "IMPORT"],
        }

        prompt_id = data_service.add_new_prompt(imported_data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Imported data should be sanitized
        assert "\x00" not in saved_prompt["title"]
        assert len(saved_prompt["tags"]) == 1  # Deduplicated

    def test_migration_of_legacy_data(self, data_service):
        """Test that legacy data migration applies sanitization."""
        # Simulate loading legacy data that lacks sanitization
        legacy_data = {
            "title": "Legacy\x00Data",
            "prompt": "Old content",
            "category": "Legacy",
            "tags": ["old", "OLD", "Old"],
        }

        prompt_id = data_service.add_new_prompt(legacy_data)
        saved_prompt = data_service.prompts[prompt_id]["data"]

        # Legacy data should be sanitized when normalized
        assert "\x00" not in saved_prompt["title"]
        assert len(saved_prompt["tags"]) == 1
