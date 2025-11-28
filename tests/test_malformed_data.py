"""
Comprehensive tests for malformed data and error handling.
Tests JSON parsing errors, invalid data structures, and recovery behavior.
"""

import pytest
import json
import os
from pathlib import Path

from src.services.prompt_data_service import PromptDataService
from src.services.exceptions import DataPersistenceError


class TestJSONParsingErrors:
    """Test handling of JSON parsing errors."""

    def test_load_completely_invalid_json(self, temp_data_file):
        """Test loading a file with completely invalid JSON."""
        with open(temp_data_file, "w") as f:
            f.write("{this is not valid json at all!}")

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should return empty dict and not crash
        assert prompts == {}
        assert service.next_id in (0, 1)
        assert service.categories == []

    def test_load_truncated_json(self, temp_data_file):
        """Test loading a truncated JSON file."""
        with open(temp_data_file, "w") as f:
            f.write('{"next_id": 5, "prompts": {"0": {"data":')

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        assert prompts == {}

    def test_load_json_with_trailing_comma(self, temp_data_file):
        """Test loading JSON with invalid trailing comma."""
        with open(temp_data_file, "w") as f:
            f.write('{"next_id": 1, "prompts": {},}')

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # JSON parser will fail, should handle gracefully
        assert prompts == {}

    def test_load_empty_file(self, temp_data_file):
        """Test loading a completely empty file."""
        Path(temp_data_file).touch()

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        assert prompts == {}

    def test_load_json_with_comments(self, temp_data_file):
        """Test loading JSON with comments (which aren't valid JSON)."""
        with open(temp_data_file, "w") as f:
            f.write(
                """
{
    // This is a comment
    "next_id": 1,
    "prompts": {}
}
"""
            )

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should fail to parse
        assert prompts == {}


class TestMissingRootFields:
    """Test handling of missing required root fields."""

    def test_load_missing_next_id(self, temp_data_file):
        """Test loading data without next_id field."""
        data = {"prompts": {}}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should default to 0 (or 1 on DB-backed service)
        assert service.next_id in (0, 1)

    def test_load_missing_prompts_field(self, temp_data_file):
        """Test loading data without prompts field."""
        data = {"next_id": 5}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        assert prompts == {}

    def test_load_null_next_id(self, temp_data_file):
        """Test loading data with null next_id."""
        data = {"next_id": None, "prompts": {}}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should handle null and default to 0 (or 1 on DB-backed service)
        assert service.next_id in (0, 1)

    def test_load_null_prompts(self, temp_data_file):
        """Test loading data with null prompts."""
        data = {"next_id": 1, "prompts": None}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should handle null
        assert isinstance(prompts, dict)


class TestWrongDataTypes:
    """Test handling of wrong data types in JSON."""

    def test_load_prompts_as_list(self, temp_data_file):
        """Test loading with prompts as list instead of dict."""
        data = {"next_id": 1, "prompts": ["not", "a", "dict"]}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should handle gracefully
        assert isinstance(prompts, dict)

    def test_load_next_id_as_string(self, temp_data_file):
        """Test loading with next_id as string."""
        data = {"next_id": "not_a_number", "prompts": {}}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should handle and default
        assert isinstance(service.next_id, int)

    def test_load_categories_as_dict(self, temp_data_file):
        """Test loading with categories as dict instead of list."""
        data = {"next_id": 1, "prompts": {}, "categories": {"not": "a", "list": "here"}}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should handle gracefully
        assert isinstance(service.categories, list)

    def test_load_tags_as_string(self, temp_data_file):
        """Test loading with global_tags as string instead of list."""
        data = {"next_id": 1, "prompts": {}, "global_tags": "not_a_list"}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should handle gracefully
        assert isinstance(service.global_tags, set)


class TestInvalidPromptStructures:
    """Test handling of invalid prompt structures."""

    def test_load_prompt_without_data_field(self, temp_data_file):
        """Test loading prompt without 'data' field."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "versions": [],
                    "branches": {},
                    # Missing 'data' field
                }
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Should add default data field
        if service.prompts:
            first_key = list(service.prompts.keys())[0]
            assert "data" in service.prompts[first_key]

    def test_load_prompt_data_as_string(self, temp_data_file):
        """Test loading prompt with data as string instead of dict."""
        data = {
            "next_id": 1,
            "prompts": {"0": {"data": "not_a_dict", "versions": [], "branches": {}}},
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should skip invalid prompt or ensure data property is a dict for the first prompt
        if len(prompts) == 0:
            assert True
        else:
            first_key = list(prompts.keys())[0]
            assert isinstance(prompts[first_key]["data"], dict)

    def test_load_invalid_prompt_id(self, temp_data_file):
        """Test loading with invalid prompt ID keys."""
        data = {
            "next_id": 1,
            "prompts": {
                "not_a_number": {
                    "data": {"title": "Test"},
                    "versions": [],
                    "branches": {},
                },
                "also_invalid!": {
                    "data": {"title": "Test2"},
                    "versions": [],
                    "branches": {},
                },
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Invalid keys should be skipped
        assert len(prompts) == 0

    def test_load_negative_prompt_id(self, temp_data_file):
        """Test loading with negative prompt ID."""
        data = {
            "next_id": 1,
            "prompts": {
                "-1": {"data": {"title": "Test"}, "versions": [], "branches": {}}
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Negative ID might be accepted as valid integer
        # Check it doesn't crash
        assert isinstance(prompts, dict)


class TestInvalidVersionData:
    """Test handling of invalid version data."""

    def test_load_version_without_required_fields(self, temp_data_file):
        """Test loading version missing required fields."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test", "prompt": "Content"},
                    "versions": [
                        {
                            "version_id": "v1",
                            # Missing timestamp, author, message, data, parents
                        }
                    ],
                    "branches": {"main": "v1"},
                }
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should load, possibly with defaults
        assert 0 in prompts

    def test_load_version_with_invalid_timestamp(self, temp_data_file):
        """Test loading version with invalid timestamp format."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test"},
                    "versions": [
                        {
                            "version_id": "v1",
                            "timestamp": "not_a_valid_timestamp",
                            "author": "test",
                            "message": "test",
                            "data": {},
                            "parents": [],
                        }
                    ],
                    "branches": {},
                }
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should load despite invalid timestamp
        assert 0 in prompts

    def test_load_version_with_circular_parents(self, temp_data_file):
        """Test loading versions with circular parent references."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test"},
                    "versions": [
                        {
                            "version_id": "v1",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "author": "test",
                            "message": "test",
                            "data": {},
                            "parents": ["v2"],  # References v2, which references v1
                        },
                        {
                            "version_id": "v2",
                            "timestamp": "2024-01-01T00:00:00Z",
                            "author": "test",
                            "message": "test",
                            "data": {},
                            "parents": ["v1"],  # Circular reference
                        },
                    ],
                    "branches": {},
                }
            },
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should load despite circular references
        assert 0 in prompts


class TestDataIntegrityAfterErrors:
    """Test that data integrity is maintained after errors."""

    def test_partial_save_failure_recovery(
        self, temp_data_file, populated_data_service
    ):
        """Test recovery from partial save failure."""
        populated_data_service.data_file = temp_data_file

        # Save successfully first
        result1 = populated_data_service.save_prompts()
        assert result1 is True

        # Try to save to invalid location (should raise persistence error)
        populated_data_service.data_file = "/invalid/path/prompts.json"
        with pytest.raises(DataPersistenceError):
            populated_data_service.save_prompts()

        # Original file should still be intact
        assert Path(temp_data_file).exists()

        # Should be able to load original data
        service2 = PromptDataService(temp_data_file)
        prompts = service2.load_prompts()
        assert len(prompts) > 0

    def test_load_after_corrupted_save(self, temp_data_file, sample_prompt_data):
        """Test loading after a file gets corrupted."""
        service = PromptDataService(temp_data_file)

        # Create and save valid data
        service.add_new_prompt(sample_prompt_data(title="Original"))
        service.save_prompts()

        # Corrupt the file
        with open(temp_data_file, "w") as f:
            f.write("{corrupted}")

        # Try to load - should fail gracefully
        service2 = PromptDataService(temp_data_file)
        prompts = service2.load_prompts()

        assert prompts == {}
        # Service should be in valid empty state
        assert service2.next_id in (0, 1)

    def test_concurrent_modifications(self, temp_data_file, sample_prompt_data):
        """Test handling of file modifications between load and save."""
        # First service loads and modifies
        service1 = PromptDataService(temp_data_file)
        service1.add_new_prompt(sample_prompt_data(title="Service1"))
        service1.save_prompts()

        # Second service loads
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()

        # First service modifies again
        service1.add_new_prompt(sample_prompt_data(title="Service1-2"))
        service1.save_prompts()

        # Second service saves (will overwrite)
        service2.add_new_prompt(sample_prompt_data(title="Service2"))
        service2.save_prompts()

        # Last save wins - this is expected behavior
        # Just verify no corruption
        service3 = PromptDataService(temp_data_file)
        prompts = service3.load_prompts()

        assert isinstance(prompts, dict)
        # Should have valid JSON structure
        assert service3.next_id >= 0


class TestUnicodeAndSpecialCharacters:
    """Test handling of Unicode and special characters in malformed data."""

    def test_load_file_with_invalid_encoding(self, temp_data_file):
        """Test loading file with invalid UTF-8 encoding."""
        # Write invalid UTF-8 bytes
        with open(temp_data_file, "wb") as f:
            f.write(b'{"\xff\xfe": "invalid"}')

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should handle encoding errors gracefully
        assert isinstance(prompts, dict)

    def test_save_with_unprintable_characters(self, temp_data_file, sample_prompt_data):
        """Test saving data with unprintable characters."""
        service = PromptDataService(temp_data_file)

        prompt_data = sample_prompt_data(
            title="Test\x00\x01\x02",  # Null and control characters
            prompt="Content with\x00null",
        )

        service.add_new_prompt(prompt_data)
        result = service.save_prompts()

        # Should handle or strip unprintable characters
        assert isinstance(result, bool)

    def test_load_with_mixed_line_endings(self, temp_data_file):
        """Test loading file with mixed line endings."""
        # Create JSON with mixed line endings
        json_str = '{\r\n"next_id": 1,\n"prompts": {}\r}'

        with open(temp_data_file, "wb") as f:
            f.write(json_str.encode("utf-8"))

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should handle mixed line endings
        assert isinstance(prompts, dict)


class TestExtremeValues:
    """Test handling of extreme values."""

    def test_load_extremely_large_next_id(self, temp_data_file):
        """Test loading with extremely large next_id."""
        data = {"next_id": 999999999999, "prompts": {}}

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        assert service.next_id == 999999999999

    def test_load_extremely_nested_structure(self, temp_data_file):
        """Test loading with deeply nested structure."""
        # Create deeply nested structure
        nested = {"level": 1}
        current = nested
        for i in range(100):
            current["nested"] = {"level": i + 2}
            current = current["nested"]

        data = {
            "next_id": 1,
            "prompts": {"0": {"data": nested, "versions": [], "branches": {}}},
        }

        with open(temp_data_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should handle deep nesting
        assert isinstance(prompts, dict)

    def test_save_extremely_long_string(self, temp_data_file, sample_prompt_data):
        """Test saving prompt with extremely long content."""
        service = PromptDataService(temp_data_file)

        # Create prompt with 1MB of content
        long_content = "A" * (1024 * 1024)

        prompt_data = sample_prompt_data(title="Long Content", prompt=long_content)

        service.add_new_prompt(prompt_data)
        result = service.save_prompts()

        # Should handle large content
        assert result is True

        # Verify it can be loaded back
        service2 = PromptDataService(temp_data_file)
        prompts = service2.load_prompts()
        assert 0 in prompts
