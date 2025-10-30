"""
Comprehensive unit tests for PromptDataService.
Tests CRUD operations, data persistence, migration, and error handling.
"""

import pytest
import json
import os
from pathlib import Path

from src.services.prompt_data_service import PromptDataService


class TestPromptCreation:
    """Test prompt creation functionality."""

    def test_create_prompt_with_all_fields(self, empty_data_service, sample_prompt_data):
        """Test creating a prompt with all fields populated."""
        prompt_data = sample_prompt_data(
            title="Complete Prompt",
            prompt="Full content",
            note="Detailed note",
            category="Testing",
            tags=["tag1", "tag2", "tag3"],
            favorite=True
        )

        prompt_id = empty_data_service.add_new_prompt(prompt_data)

        assert prompt_id == 0
        assert empty_data_service.next_id == 1
        assert prompt_id in empty_data_service.prompts

        saved_prompt = empty_data_service.prompts[prompt_id]
        assert saved_prompt['data']['title'] == "Complete Prompt"
        assert saved_prompt['data']['prompt'] == "Full content"
        assert saved_prompt['data']['note'] == "Detailed note"
        assert saved_prompt['data']['category'] == "Testing"
        assert saved_prompt['data']['tags'] == ["tag1", "tag2", "tag3"]
        assert saved_prompt['data']['favorite'] is True

    def test_create_prompt_with_minimal_fields(self, empty_data_service):
        """Test creating a prompt with only required fields."""
        minimal_data = {
            "title": "Minimal",
            "prompt": "Content"
        }

        prompt_id = empty_data_service.add_new_prompt(minimal_data)

        assert prompt_id >= 0
        saved_prompt = empty_data_service.prompts[prompt_id]
        assert saved_prompt['data']['title'] == "Minimal"
        assert saved_prompt['data']['prompt'] == "Content"

    def test_create_prompt_increments_id(self, empty_data_service, sample_prompt_data):
        """Test that creating prompts increments the ID correctly."""
        id1 = empty_data_service.add_new_prompt(sample_prompt_data(title="First"))
        id2 = empty_data_service.add_new_prompt(sample_prompt_data(title="Second"))
        id3 = empty_data_service.add_new_prompt(sample_prompt_data(title="Third"))

        assert id1 == 0
        assert id2 == 1
        assert id3 == 2
        assert empty_data_service.next_id == 3

    def test_create_prompt_creates_initial_version(self, empty_data_service, sample_prompt_data):
        """Test that creating a prompt creates an initial version."""
        prompt_data = sample_prompt_data(title="Versioned")
        prompt_id = empty_data_service.add_new_prompt(prompt_data)

        versions = empty_data_service.prompts[prompt_id]['versions']
        assert len(versions) == 1
        assert versions[0]['message'] == "Initial commit"
        assert versions[0]['parents'] == []
        assert 'version_id' in versions[0]
        assert 'timestamp' in versions[0]
        assert 'author' in versions[0]

    def test_create_prompt_with_custom_commit_message(self, empty_data_service, sample_prompt_data):
        """Test creating a prompt with a custom commit message."""
        prompt_data = sample_prompt_data(title="Custom Message")
        prompt_data['commit_message'] = "Custom initial commit"

        prompt_id = empty_data_service.add_new_prompt(prompt_data)

        versions = empty_data_service.prompts[prompt_id]['versions']
        assert versions[0]['message'] == "Custom initial commit"

    def test_create_prompt_trims_tag_whitespace(self, empty_data_service):
        """Tags should be sanitized before persistence."""
        prompt_data = {
            "title": "Whitespace Tags",
            "prompt": "Content",
            "tags": [" vision", "creativity ", "  ", "focus"]
        }

        prompt_id = empty_data_service.add_new_prompt(prompt_data)
        saved_tags = empty_data_service.prompts[prompt_id]['data']['tags']

        assert saved_tags == ["vision", "creativity", "focus"]


class TestPromptUpdate:
    """Test prompt update functionality."""

    def test_update_existing_prompt(self, populated_data_service):
        """Test updating an existing prompt."""
        prompt_id = 0
        updated_data = {
            "title": "Updated Title",
            "prompt": "Updated content",
            "category": "Updated Category",
            "tags": ["updated"],
            "favorite": True
        }

        result = populated_data_service.update_prompt(prompt_id, updated_data, "Update test")

        assert result is True
        saved_data = populated_data_service.prompts[prompt_id]['data']
        assert saved_data['title'] == "Updated Title"
        assert saved_data['prompt'] == "Updated content"

    def test_update_nonexistent_prompt(self, populated_data_service):
        """Test updating a prompt that doesn't exist."""
        result = populated_data_service.update_prompt(9999, {"title": "Test"}, "Update")

        assert result is False

    def test_update_creates_new_version(self, populated_data_service):
        """Test that updating a prompt creates a new version."""
        prompt_id = 0
        initial_version_count = len(populated_data_service.prompts[prompt_id]['versions'])

        updated_data = {"title": "New Version", "prompt": "New content"}
        populated_data_service.update_prompt(prompt_id, updated_data, "Version 2")

        versions = populated_data_service.prompts[prompt_id]['versions']
        assert len(versions) == initial_version_count + 1
        assert versions[-1]['message'] == "Version 2"

    def test_update_maintains_version_chain(self, populated_data_service):
        """Test that updates maintain proper version parent relationships."""
        prompt_id = 0

        # Get initial version ID
        initial_version_id = populated_data_service.prompts[prompt_id]['versions'][0]['version_id']

        # Update prompt
        populated_data_service.update_prompt(prompt_id, {"title": "V2", "prompt": "C2"}, "Update 1")

        versions = populated_data_service.prompts[prompt_id]['versions']
        latest_version = versions[-1]

        assert initial_version_id in latest_version['parents']

    def test_update_updates_branch_head(self, populated_data_service):
        """Test that updating a prompt updates the main branch head."""
        prompt_id = 0

        # Update prompt
        populated_data_service.update_prompt(prompt_id, {"title": "New", "prompt": "New"}, "Update")

        versions = populated_data_service.prompts[prompt_id]['versions']
        latest_version_id = versions[-1]['version_id']
        branch_head = populated_data_service.prompts[prompt_id]['branches']['main']

        assert branch_head == latest_version_id


class TestPromptDeletion:
    """Test prompt deletion functionality."""

    def test_delete_existing_prompt(self, populated_data_service):
        """Test deleting an existing prompt."""
        prompt_id = 0
        assert prompt_id in populated_data_service.prompts

        result = populated_data_service.delete_prompt(prompt_id)

        assert result is True
        assert prompt_id not in populated_data_service.prompts

    def test_delete_nonexistent_prompt(self, populated_data_service):
        """Test deleting a prompt that doesn't exist."""
        result = populated_data_service.delete_prompt(9999)

        assert result is False

    def test_delete_multiple_prompts(self, populated_data_service):
        """Test deleting multiple prompts."""
        initial_count = len(populated_data_service.prompts)

        populated_data_service.delete_prompt(0)
        populated_data_service.delete_prompt(1)

        assert len(populated_data_service.prompts) == initial_count - 2


class TestPromptRetrieval:
    """Test prompt data retrieval functionality."""

    def test_get_prompt_data_existing(self, populated_data_service):
        """Test getting data for an existing prompt."""
        prompt_id = 0
        data = populated_data_service.get_prompt_data(prompt_id)

        assert isinstance(data, dict)
        assert 'title' in data
        assert 'prompt' in data

    def test_get_prompt_data_nonexistent(self, populated_data_service):
        """Test getting data for a nonexistent prompt."""
        data = populated_data_service.get_prompt_data(9999)

        assert data == {}

    def test_get_prompt_versions(self, populated_data_service):
        """Test getting version history for a prompt."""
        prompt_id = 0
        versions = populated_data_service.get_prompt_versions(prompt_id)

        assert isinstance(versions, list)
        assert len(versions) > 0
        assert 'version_id' in versions[0]
        assert 'timestamp' in versions[0]

    def test_get_prompt_versions_nonexistent(self, populated_data_service):
        """Test getting versions for a nonexistent prompt."""
        versions = populated_data_service.get_prompt_versions(9999)

        assert versions == []


class TestDataPersistence:
    """Test save and load functionality."""

    def test_save_prompts_creates_file(self, empty_data_service, temp_data_file, sample_prompt_data):
        """Test that saving prompts creates the data file."""
        empty_data_service.add_new_prompt(sample_prompt_data())
        result = empty_data_service.save_prompts()

        assert result is True
        assert os.path.exists(temp_data_file)

    def test_save_and_load_prompts(self, temp_data_file, sample_prompt_data):
        """Test that prompts can be saved and loaded correctly."""
        # Create and save
        service1 = PromptDataService(temp_data_file)
        prompt_data = sample_prompt_data(title="Save Test", prompt="Test content")
        prompt_id = service1.add_new_prompt(prompt_data)
        service1.save_prompts()

        # Load in new instance
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()

        assert prompt_id in service2.prompts
        assert service2.prompts[prompt_id]['data']['title'] == "Save Test"

    def test_load_nonexistent_file(self, temp_data_file):
        """Test loading when the data file doesn't exist."""
        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        assert prompts == {}
        assert service.next_id == 0

    def test_save_with_special_characters(self, temp_data_file, sample_prompt_data):
        """Test saving and loading prompts with special characters."""
        service = PromptDataService(temp_data_file)
        prompt_data = sample_prompt_data(
            title="Special: <>&\"'",
            prompt="Content with 你好 unicode ñ é",
            note="Emoji test 🚀 ⭐ 🎉"
        )
        service.add_new_prompt(prompt_data)
        service.save_prompts()

        # Load and verify
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()

        loaded_data = service2.prompts[0]['data']
        assert loaded_data['title'] == "Special: <>&\"'"
        assert "你好" in loaded_data['prompt']
        assert "🚀" in loaded_data['note']

    def test_save_updates_categories_and_tags(self, temp_data_file, sample_prompt_data):
        """Test that saving updates categories and tags from prompts."""
        service = PromptDataService(temp_data_file)

        service.add_new_prompt(sample_prompt_data(category="Cat1", tags=["tag1", "tag2"]))
        service.add_new_prompt(sample_prompt_data(category="Cat2", tags=["tag2", "tag3"]))
        service.save_prompts()

        # Load and check
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()

        assert "Cat1" in service2.categories
        assert "Cat2" in service2.categories
        assert "tag1" in service2.global_tags
        assert "tag2" in service2.global_tags
        assert "tag3" in service2.global_tags


class TestDataMigration:
    """Test data migration from old format."""

    def test_migrate_old_data_structure(self, temp_data_file):
        """Test migration of old data structure with 'history' field."""
        # Create old format data
        old_data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {
                        "title": "Old Format",
                        "prompt": "Current content",
                        "category": "Test",
                        "tags": []
                    },
                    "history": [
                        {"title": "Old Format", "prompt": "First content"},
                        {"title": "Old Format", "prompt": "Second content"}
                    ]
                }
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(old_data, f)

        # Load and check migration
        service = PromptDataService(temp_data_file)
        service.load_prompts()

        assert 0 in service.prompts
        prompt_info = service.prompts[0]

        # Should have versions now, not history
        assert 'versions' in prompt_info
        assert 'history' not in prompt_info
        assert len(prompt_info['versions']) > 0

    def test_migrate_ensures_versioned_structure(self, temp_data_file):
        """Test that migration ensures proper versioned structure."""
        # Create data without versions or branches
        incomplete_data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test", "prompt": "Content"}
                }
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(incomplete_data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        prompt_info = service.prompts[0]
        assert 'versions' in prompt_info
        assert 'branches' in prompt_info
        assert isinstance(prompt_info['versions'], list)
        assert isinstance(prompt_info['branches'], dict)

    def test_migrate_sets_default_category(self, temp_data_file):
        """Test that migration sets default category if missing."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test", "prompt": "Content"}
                }
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        assert service.prompts[0]['data']['category'] == 'No category'

    def test_migrate_sets_default_favorite(self, temp_data_file):
        """Test that migration sets default favorite status."""
        data = {
            "next_id": 1,
            "prompts": {
                "0": {
                    "data": {"title": "Test", "prompt": "Content", "category": "Test"}
                }
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        assert service.prompts[0]['data']['favorite'] is False


class TestCategoriesAndTags:
    """Test category and tag management."""

    def test_get_categories(self, populated_data_service):
        """Test getting all categories."""
        categories = populated_data_service.get_categories()

        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "Programming" in categories

    def test_get_tags(self, populated_data_service):
        """Test getting all tags."""
        tags = populated_data_service.get_tags()

        assert isinstance(tags, list)
        assert len(tags) > 0

    def test_categories_preserve_defined_order(self, populated_data_service):
        """Categories should preserve predefined ordering."""
        categories = populated_data_service.get_categories()

        assert categories == [
            "Programming",
            "Development",
            "Database",
            "Documentation",
            "Security",
        ]

    def test_save_preserves_category_order_from_file(self, temp_data_file, sample_prompt_data):
        """Category ordering defined in the data file should remain intact after save/load cycles."""
        service = PromptDataService(temp_data_file)

        manual_order = [
            "Développement personnel",
            "Écriture",
            "Éducation et apprentissage",
            "No category",
        ]

        service.add_new_prompt(sample_prompt_data(category="Développement personnel"))
        service.add_new_prompt(sample_prompt_data(category="Écriture"))
        service.add_new_prompt(sample_prompt_data(category="Éducation et apprentissage"))

        service.categories = manual_order[:]
        service.save_prompts()

        loaded_service = PromptDataService(temp_data_file)
        loaded_service.load_prompts()

        assert loaded_service.get_categories() == manual_order

    def test_tags_sorted(self, populated_data_service):
        """Test that tags are returned sorted."""
        tags = populated_data_service.get_tags()

        assert tags == sorted(tags)

    def test_get_all_tags_from_prompts(self, populated_data_service):
        """Test extracting all unique tags from prompts."""
        tags = populated_data_service.get_all_tags_from_prompts()

        assert isinstance(tags, set)
        assert len(tags) > 0

    def test_get_tags_with_counts(self, populated_data_service):
        """Test getting tags with their usage counts."""
        tags_with_counts = populated_data_service.get_tags_with_counts()

        assert isinstance(tags_with_counts, list)
        assert len(tags_with_counts) > 0

        # Each tag should have 'name' and 'count' fields
        for tag in tags_with_counts:
            assert 'name' in tag
            assert 'count' in tag
            assert isinstance(tag['name'], str)
            assert isinstance(tag['count'], int)
            assert tag['count'] >= 0

        # Tags should be sorted by name
        tag_names = [tag['name'] for tag in tags_with_counts]
        assert tag_names == sorted(tag_names)

    def test_get_tags_with_counts_accuracy(self, empty_data_service, sample_prompt_data):
        """Test that tag counts are accurate."""
        # Create prompts with overlapping tags
        empty_data_service.add_new_prompt(sample_prompt_data(tags=["python", "ai"]))
        empty_data_service.add_new_prompt(sample_prompt_data(tags=["python", "web"]))
        empty_data_service.add_new_prompt(sample_prompt_data(tags=["ai", "ml"]))

        tags_with_counts = empty_data_service.get_tags_with_counts()

        # Convert to dict for easier checking
        tag_dict = {tag['name']: tag['count'] for tag in tags_with_counts}

        assert tag_dict['python'] == 2
        assert tag_dict['ai'] == 2
        assert tag_dict['web'] == 1
        assert tag_dict['ml'] == 1


class TestVersionOperations:
    """Test version-related operations."""

    def test_revert_prompt_to_version(self, populated_data_service):
        """Test reverting a prompt to a previous version."""
        prompt_id = 0
        initial_data = populated_data_service.get_prompt_data(prompt_id).copy()

        # Update prompt
        populated_data_service.update_prompt(
            prompt_id,
            {"title": "Modified", "prompt": "Modified content"},
            "Modify"
        )

        # Revert to initial data
        result = populated_data_service.revert_prompt_to_version(
            prompt_id,
            initial_data,
            "Revert to initial"
        )

        assert result is True

        # Check that data was reverted
        current_data = populated_data_service.get_prompt_data(prompt_id)
        assert current_data['title'] == initial_data['title']

    def test_revert_nonexistent_prompt(self, populated_data_service):
        """Test reverting a nonexistent prompt."""
        result = populated_data_service.revert_prompt_to_version(
            9999,
            {"title": "Test"},
            "Revert"
        )

        assert result is False

    def test_revert_creates_new_version(self, populated_data_service):
        """Test that revert creates a new version."""
        prompt_id = 0
        initial_version_count = len(populated_data_service.get_prompt_versions(prompt_id))

        initial_data = populated_data_service.get_prompt_data(prompt_id).copy()
        populated_data_service.revert_prompt_to_version(
            prompt_id,
            initial_data,
            "Revert test"
        )

        versions = populated_data_service.get_prompt_versions(prompt_id)
        assert len(versions) == initial_version_count + 1
        assert versions[-1]['message'] == "Revert test"


class TestClearAllPrompts:
    """Test clearing all prompts functionality."""

    def test_clear_all_prompts(self, populated_data_service):
        """Test clearing all prompts."""
        assert len(populated_data_service.prompts) > 0

        result = populated_data_service.clear_all_prompts()

        assert result is True
        assert len(populated_data_service.prompts) == 0
        assert populated_data_service.next_id == 0
        assert len(populated_data_service.categories) == 0
        assert len(populated_data_service.global_tags) == 0

    def test_clear_all_prompts_saves_state(self, temp_data_file, populated_data_service):
        """Test that clearing all prompts saves the empty state."""
        populated_data_service.clear_all_prompts()

        # Load in new instance
        service2 = PromptDataService(temp_data_file)
        service2.load_prompts()

        assert len(service2.prompts) == 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_load_corrupted_json(self, temp_data_file):
        """Test loading a file with corrupted JSON."""
        with open(temp_data_file, 'w') as f:
            f.write("{invalid json content}")

        service = PromptDataService(temp_data_file)
        prompts = service.load_prompts()

        # Should return empty dict and not crash
        assert prompts == {}
        assert service.next_id == 0

    def test_load_invalid_prompt_key(self, temp_data_file):
        """Test loading data with invalid prompt keys."""
        invalid_data = {
            "next_id": 1,
            "prompts": {
                "not_a_number": {
                    "data": {"title": "Test"}
                }
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Invalid key should be ignored
        assert len(service.prompts) == 0

    def test_load_invalid_prompt_structure(self, temp_data_file):
        """Test loading data with invalid prompt structure."""
        invalid_data = {
            "next_id": 1,
            "prompts": {
                "0": "not a dict"
            }
        }

        with open(temp_data_file, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)

        service = PromptDataService(temp_data_file)
        service.load_prompts()

        # Invalid structure should be ignored
        assert len(service.prompts) == 0

    def test_create_prompt_alias(self, empty_data_service, sample_prompt_data):
        """Test that create_prompt is an alias for add_new_prompt."""
        prompt_data = sample_prompt_data()

        prompt_id = empty_data_service.create_prompt(prompt_data)

        assert prompt_id >= 0
        assert prompt_id in empty_data_service.prompts
