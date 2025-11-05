"""Integration tests for sanitization persistence.

Tests that sanitized data is correctly persisted to storage and
can be reloaded without data corruption or security issues.
"""

import pytest
import json
import os
from src.services.prompt_data_service import PromptDataService


class TestSanitizationPersistence:
    """Test that sanitized data persists correctly to storage."""

    @pytest.fixture
    def data_service_with_file(self, tmp_path):
        """Create a data service that persists to a real file."""
        temp_file = tmp_path / "prompts_data.json"
        service = PromptDataService(data_file_path=str(temp_file))
        return service, str(temp_file)

    def test_control_characters_do_not_persist(self, data_service_with_file):
        """Test that control characters are removed before persistence."""
        service, file_path = data_service_with_file

        # Create prompt with control characters
        malicious_data = {
            "title": "Test\x00\x07\x1bTitle",
            "prompt": "Content\x00with nulls",
            "category": "Test",
            "tags": ["test"],
        }

        prompt_id = service.add_new_prompt(malicious_data)
        service.save_prompts()

        # Read raw JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # Verify control characters are not in persisted data
        prompt_data = saved_data["prompts"][str(prompt_id)]["data"]
        assert "\x00" not in prompt_data["title"]
        assert "\x07" not in prompt_data["title"]
        assert "\x1b" not in prompt_data["title"]
        assert "\x00" not in prompt_data["prompt"]

    def test_deduplicated_tags_persist(self, data_service_with_file):
        """Test that deduplicated tags are persisted."""
        service, file_path = data_service_with_file

        # Create prompt with duplicate tags
        data = {
            "title": "Test",
            "prompt": "Content",
            "category": "Test",
            "tags": ["python", "Python", "PYTHON", "coding", "Coding"],
        }

        prompt_id = service.add_new_prompt(data)
        service.save_prompts()

        # Read raw JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # Verify only unique tags are persisted
        saved_tags = saved_data["prompts"][str(prompt_id)]["data"]["tags"]
        assert len(saved_tags) == 2
        # Tags should be unique (case-insensitive)
        lower_tags = [t.lower() for t in saved_tags]
        assert len(set(lower_tags)) == len(lower_tags)

    def test_sanitized_data_reloads_correctly(self, data_service_with_file):
        """Test that sanitized data can be reloaded without corruption."""
        service, file_path = data_service_with_file

        # Create prompt with data that needs sanitization
        original_data = {
            "title": "Test   Title   With   Spaces",
            "prompt": "Content\nwith\nnewlines",
            "category": "  Category  ",
            "tags": ["python", "PYTHON", "coding"],
        }

        prompt_id = service.add_new_prompt(original_data)
        service.save_prompts()

        # Create new service instance and load data
        new_service = PromptDataService(data_file_path=file_path)
        new_service.load_prompts()

        # Verify data is correctly loaded
        loaded_prompt = new_service.prompts[prompt_id]["data"]
        assert loaded_prompt["title"] == "Test Title With Spaces"
        assert "\n" in loaded_prompt["prompt"]  # Newlines preserved
        assert loaded_prompt["category"] == "Category"
        assert len(loaded_prompt["tags"]) == 2  # Deduplicated

    def test_length_limits_enforced_in_persistence(self, data_service_with_file):
        """Test that length limits are enforced before persistence."""
        service, file_path = data_service_with_file

        # Create prompt with fields exceeding limits
        data = {
            "title": "x" * 300,
            "prompt": "y" * 60000,
            "category": "z" * 150,
            "tags": [f"tag{i}" for i in range(60)],
        }

        prompt_id = service.add_new_prompt(data)
        service.save_prompts()

        # Read raw JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # Verify length limits are enforced
        prompt_data = saved_data["prompts"][str(prompt_id)]["data"]
        assert len(prompt_data["title"]) <= 200
        assert len(prompt_data["prompt"]) <= 50000
        assert len(prompt_data["category"]) <= 100
        assert len(prompt_data["tags"]) <= 50

    def test_multiple_save_load_cycles(self, data_service_with_file):
        """Test that data remains clean through multiple save/load cycles."""
        service, file_path = data_service_with_file

        # Create prompt with malicious data
        malicious_data = {
            "title": "Test\x00Title",
            "prompt": "Content",
            "category": "Test",
            "tags": ["python", "Python", "PYTHON"],
        }

        prompt_id = service.add_new_prompt(malicious_data)
        service.save_prompts()

        # Perform multiple save/load cycles
        for _ in range(3):
            # Load data
            new_service = PromptDataService(data_file_path=file_path)
            new_service.load_prompts()

            # Verify data is still clean
            loaded_prompt = new_service.prompts[prompt_id]["data"]
            assert "\x00" not in loaded_prompt["title"]
            assert len(loaded_prompt["tags"]) == 1  # Still deduplicated

            # Update and save again
            updated_data = loaded_prompt.copy()
            updated_data["title"] += " Updated"
            new_service.update_prompt(prompt_id, updated_data, "Update cycle")
            new_service.save_prompts()

            # Reload for next iteration
            service = new_service

        # Final verification
        final_service = PromptDataService(data_file_path=file_path)
        final_service.load_prompts()
        final_prompt = final_service.prompts[prompt_id]["data"]
        assert "\x00" not in final_prompt["title"]
        assert "Updated" in final_prompt["title"]

    def test_json_file_is_valid_after_sanitization(self, data_service_with_file):
        """Test that saved JSON file is valid and readable."""
        service, file_path = data_service_with_file

        # Create multiple prompts with various sanitization needs
        prompts_data = [
            {"title": "Test\x001", "prompt": "Content", "category": "A", "tags": ["a", "A"]},
            {"title": "Test   2", "prompt": "Content", "category": "B", "tags": ["b", "b"]},
            {"title": "Test3", "prompt": "Line1\nLine2", "category": "C", "tags": ["c"]},
        ]

        for data in prompts_data:
            service.add_new_prompt(data)

        service.save_prompts()

        # Verify JSON file is valid
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                saved_data = json.load(f)
                # If we can parse it, it's valid JSON
                assert "prompts" in saved_data
                assert "next_id" in saved_data
                assert len(saved_data["prompts"]) == 3
            except json.JSONDecodeError as e:
                pytest.fail(f"Saved JSON file is invalid: {e}")

    def test_sanitization_preserves_valid_unicode(self, data_service_with_file):
        """Test that valid Unicode characters are preserved during sanitization."""
        service, file_path = data_service_with_file

        # Create prompt with valid Unicode (emojis, accents, etc.)
        unicode_data = {
            "title": "Test with émojis 🐍 and àccénts",
            "prompt": "Python 🐍 is great! Café ☕",
            "category": "Unicode Test",
            "tags": ["python🐍", "café☕"],
        }

        prompt_id = service.add_new_prompt(unicode_data)
        service.save_prompts()

        # Reload data
        new_service = PromptDataService(data_file_path=file_path)
        new_service.load_prompts()

        # Verify Unicode is preserved
        loaded_prompt = new_service.prompts[prompt_id]["data"]
        assert "🐍" in loaded_prompt["title"]
        assert "à" in loaded_prompt["title"]
        assert "☕" in loaded_prompt["prompt"]
        assert any("🐍" in tag for tag in loaded_prompt["tags"])

    def test_empty_fields_handled_correctly(self, data_service_with_file):
        """Test that empty/null fields are handled correctly."""
        service, file_path = data_service_with_file

        # Create prompt with minimal data
        minimal_data = {
            "title": "Minimal",
            "prompt": "Content",
            "category": "",
            "tags": [],
        }

        prompt_id = service.add_new_prompt(minimal_data)
        service.save_prompts()

        # Reload data
        new_service = PromptDataService(data_file_path=file_path)
        new_service.load_prompts()

        # Verify empty fields are handled correctly
        loaded_prompt = new_service.prompts[prompt_id]["data"]
        assert loaded_prompt["title"] == "Minimal"
        assert loaded_prompt["prompt"] == "Content"
        assert loaded_prompt["tags"] == []


class TestVersionHistoryPersistence:
    """Test that sanitization works correctly with version history."""

    @pytest.fixture
    def data_service_with_file(self, tmp_path):
        """Create a data service that persists to a real file."""
        temp_file = tmp_path / "prompts_data.json"
        service = PromptDataService(data_file_path=str(temp_file))
        return service, str(temp_file)

    def test_version_history_contains_sanitized_data(self, data_service_with_file):
        """Test that version history contains sanitized versions."""
        service, file_path = data_service_with_file

        # Create initial prompt with malicious data
        prompt_id = service.add_new_prompt({
            "title": "Test\x00Version",
            "prompt": "Initial",
            "category": "Test",
            "tags": ["v1", "V1"],
        })

        # Update prompt
        service.update_prompt(prompt_id, {
            "title": "Test   Version   Updated",
            "prompt": "Updated",
            "category": "Test",
            "tags": ["v2", "V2", "v2"],
        }, "Update version")

        service.save_prompts()

        # Read raw JSON
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)

        # Verify all versions are sanitized
        versions = saved_data["prompts"][str(prompt_id)]["versions"]
        for version in versions:
            version_data = version["data"]
            # Control characters should not be in any version
            if "title" in version_data:
                assert "\x00" not in version_data["title"]
            # Tags should be deduplicated in all versions
            if "tags" in version_data:
                lower_tags = [t.lower() for t in version_data["tags"]]
                assert len(set(lower_tags)) == len(lower_tags)
