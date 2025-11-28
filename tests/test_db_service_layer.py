"""
Integration tests for database-backed service layer.

Tests the PromptDataService and BackupService with database backend.
"""

import pytest


class TestDatabaseDataService:
    """Test PromptDataService with database backend."""

    def test_add_new_prompt(self, db_data_service, sample_prompt_data):
        """Test adding a new prompt."""
        prompt_data = sample_prompt_data(
            title="Test Prompt",
            prompt="Test content",
            category="Testing",
            tags=["test", "db"]
        )

        prompt_id = db_data_service.add_new_prompt(prompt_data)

        assert prompt_id is not None
        assert isinstance(prompt_id, int)

    def test_load_prompts(self, populated_db_service):
        """Test loading prompts in dict format."""
        prompts = populated_db_service.load_prompts()

        assert len(prompts) == 5
        assert all(isinstance(pid, int) for pid in prompts.keys())
        assert all("data" in p for p in prompts.values())
        assert all("versions" in p for p in prompts.values())
        assert all("branches" in p for p in prompts.values())

    def test_get_prompt_data(self, populated_db_service):
        """Test getting prompt data."""
        prompts = populated_db_service.load_prompts()
        first_id = list(prompts.keys())[0]

        data = populated_db_service.get_prompt_data(first_id)

        assert data is not None
        assert "title" in data
        assert "prompt" in data
        assert "category" in data
        assert "tags" in data

    def test_update_prompt(self, populated_db_service, sample_prompt_data):
        """Test updating a prompt."""
        prompts = populated_db_service.load_prompts()
        first_id = list(prompts.keys())[0]

        update_data = sample_prompt_data(
            title="Updated Title",
            prompt="Updated content"
        )

        success = populated_db_service.update_prompt(
            first_id,
            update_data,
            "Test update"
        )

        assert success is True

        # Verify update
        data = populated_db_service.get_prompt_data(first_id)
        assert data["title"] == "Updated Title"

    def test_delete_prompt(self, populated_db_service):
        """Test deleting a prompt."""
        prompts = populated_db_service.load_prompts()
        initial_count = len(prompts)
        first_id = list(prompts.keys())[0]

        success = populated_db_service.delete_prompt(first_id)

        assert success is True

        # Verify deletion
        prompts = populated_db_service.load_prompts()
        assert len(prompts) == initial_count - 1
        assert first_id not in prompts

    def test_delete_prompts_bulk(self, populated_db_service):
        """Test bulk deletion of prompts."""
        prompts = populated_db_service.load_prompts()
        ids_to_delete = list(prompts.keys())[:2]

        result = populated_db_service.delete_prompts_bulk(ids_to_delete)

        assert result["deleted_count"] == 2
        assert result["failed_count"] == 0
        assert set(result["deleted_ids"]) == set(ids_to_delete)

    def test_get_categories(self, populated_db_service):
        """Test getting all categories."""
        categories = populated_db_service.get_categories()

        assert len(categories) > 0
        assert "Programming" in categories
        assert "Development" in categories

    def test_get_tags(self, populated_db_service):
        """Test getting all tags."""
        tags = populated_db_service.get_tags()

        assert len(tags) > 0
        assert "python" in tags or "test" in tags

    def test_get_tags_with_counts(self, populated_db_service):
        """Test getting tags with usage counts."""
        tags = populated_db_service.get_tags_with_counts()

        assert len(tags) > 0
        assert all("name" in tag for tag in tags)
        assert all("count" in tag for tag in tags)

    def test_get_prompt_versions(self, populated_db_service):
        """Test getting prompt version history."""
        prompts = populated_db_service.load_prompts()
        first_id = list(prompts.keys())[0]

        versions = populated_db_service.get_prompt_versions(first_id)

        assert isinstance(versions, list)
        assert len(versions) >= 1  # At least initial version

    def test_version_tracking(self, db_data_service, sample_prompt_data):
        """Test that updates create new versions."""
        # Create prompt
        prompt_data = sample_prompt_data(title="Version Test")
        prompt_id = db_data_service.add_new_prompt(prompt_data)

        # Get initial version count
        versions = db_data_service.get_prompt_versions(prompt_id)
        initial_count = len(versions)

        # Update prompt
        update_data = sample_prompt_data(title="Version Test Updated")
        db_data_service.update_prompt(prompt_id, update_data, "Update 1")

        # Verify new version created
        versions = db_data_service.get_prompt_versions(prompt_id)
        assert len(versions) == initial_count + 1

    def test_backward_compatibility_properties(self, populated_db_service):
        """Test backward compatibility properties."""
        # Test prompts property
        assert isinstance(populated_db_service.prompts, dict)

        # Test next_id property
        assert isinstance(populated_db_service.next_id, int)
        assert populated_db_service.next_id > 0

        # Test categories property
        assert isinstance(populated_db_service.categories, list)

        # Test global_tags property
        assert isinstance(populated_db_service.global_tags, set)

    def test_save_prompts_deprecated(self, db_data_service):
        """Test that save_prompts is a no-op."""
        with pytest.warns(DeprecationWarning):
            result = db_data_service.save_prompts()

        assert result is True


class TestDatabaseBackupService:
    """Test BackupService with database backend."""

    def test_create_backup(self, db_backup_service):
        """Test creating a database backup."""
        backup_id = db_backup_service.create_backup("test_backup")

        assert backup_id is not None
        assert isinstance(backup_id, str)

    def test_list_backups(self, db_backup_service):
        """Test listing backups."""
        # Create a backup first
        db_backup_service.create_backup("test_backup")

        backups = db_backup_service.list_backups()

        assert len(backups) >= 1
        assert all("backup_id" in b for b in backups)
        assert all("backup_type" in b for b in backups)
        assert all("filename" in b for b in backups)

    def test_get_backup_info(self, db_backup_service):
        """Test getting backup info."""
        backup_id = db_backup_service.create_backup("test_backup")

        info = db_backup_service.get_backup_info(backup_id)

        assert info is not None
        assert info["backup_id"] == backup_id
        assert "backup_type" in info
        assert "size_bytes" in info

    def test_get_backup_stats(self, db_backup_service):
        """Test getting backup statistics."""
        # Create a backup first
        db_backup_service.create_backup("test_backup")

        stats = db_backup_service.get_backup_stats()

        assert stats["total_backups"] >= 1
        assert stats["total_size"] > 0
        assert "newest_backup" in stats

    def test_delete_backup(self, db_backup_service):
        """Test deleting a backup."""
        backup_id = db_backup_service.create_backup("test_backup")

        success = db_backup_service.delete_backup(backup_id)

        assert success is True

        # Verify deletion
        info = db_backup_service.get_backup_info(backup_id)
        assert info is None

    def test_cleanup_old_backups(self, db_backup_service):
        """Test cleaning up old backups."""
        # Create some backups
        db_backup_service.create_backup("backup1")
        db_backup_service.create_backup("backup2")

        # Cleanup with retention_days=0 (delete all)
        removed = db_backup_service.cleanup_old_backups(retention_days=0)

        assert removed >= 2

        # Verify cleanup
        backups = db_backup_service.list_backups()
        assert len(backups) == 0


class TestDataServiceIntegration:
    """Integration tests for database service operations."""

    def test_create_and_retrieve_full_flow(self, db_data_service, sample_prompt_data):
        """Test complete flow: create, retrieve, update, delete."""
        # 1. Create
        prompt_data = sample_prompt_data(
            title="Integration Test",
            prompt="Integration test content",
            category="Testing",
            tags=["integration", "test"]
        )
        prompt_id = db_data_service.add_new_prompt(prompt_data)

        # 2. Retrieve
        prompts = db_data_service.load_prompts()
        assert prompt_id in prompts
        assert prompts[prompt_id]["data"]["title"] == "Integration Test"

        # 3. Update
        update_data = sample_prompt_data(title="Integration Test Updated")
        success = db_data_service.update_prompt(prompt_id, update_data, "Update")
        assert success is True

        # 4. Verify update
        data = db_data_service.get_prompt_data(prompt_id)
        assert data["title"] == "Integration Test Updated"

        # 5. Delete
        success = db_data_service.delete_prompt(prompt_id)
        assert success is True

        # 6. Verify deletion
        prompts = db_data_service.load_prompts()
        assert prompt_id not in prompts

    def test_category_and_tag_management(self, db_data_service, sample_prompt_data):
        """Test category and tag handling."""
        # Create prompts with different categories and tags
        db_data_service.add_new_prompt(
            sample_prompt_data(category="Cat1", tags=["tag1", "tag2"])
        )
        db_data_service.add_new_prompt(
            sample_prompt_data(category="Cat2", tags=["tag2", "tag3"])
        )

        # Verify categories
        categories = db_data_service.get_categories()
        assert "Cat1" in categories
        assert "Cat2" in categories

        # Verify tags
        tags = db_data_service.get_tags()
        assert "tag1" in tags
        assert "tag2" in tags
        assert "tag3" in tags

        # Verify tag counts
        tag_counts = db_data_service.get_tags_with_counts()
        tag_count_dict = {t["name"]: t["count"] for t in tag_counts}

        assert tag_count_dict.get("tag1", 0) >= 1
        assert tag_count_dict.get("tag2", 0) >= 2  # Used in both prompts

    def test_version_history_preservation(self, db_data_service, sample_prompt_data):
        """Test that version history is preserved correctly."""
        # Create prompt
        prompt_data = sample_prompt_data(title="V1")
        prompt_id = db_data_service.add_new_prompt(prompt_data)

        # Create multiple updates
        for i in range(5):
            update_data = sample_prompt_data(title=f"V{i+2}")
            db_data_service.update_prompt(prompt_id, update_data, f"Update {i+1}")

        # Verify version count
        versions = db_data_service.get_prompt_versions(prompt_id)
        assert len(versions) == 6  # Initial + 5 updates

        # Verify version ordering (newest first)
        assert versions[0]["message"] == "Update 5"
        assert versions[-1]["message"] == "Initial commit"
