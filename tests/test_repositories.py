"""
Unit tests for database repositories.

Tests the repository layer (PromptRepository, VersionRepository, etc.) using
in-memory SQLite for fast, isolated testing.
"""

import pytest
from src.db.models import Prompt, PromptVersion, Category, Tag


class TestPromptRepository:
    """Test PromptRepository CRUD operations."""

    def test_create_prompt(self, prompt_repo, test_category, test_user):
        """Test creating a new prompt."""
        prompt = prompt_repo.create(
            title="New Prompt",
            prompt="New content",
            category_id=test_category.id,
            user_id=test_user.id
        )

        assert prompt.id is not None
        assert prompt.title == "New Prompt"
        assert prompt.prompt == "New content"

    def test_get_by_id(self, prompt_repo, test_prompt):
        """Test retrieving prompt by ID."""
        prompt = prompt_repo.get_by_id(test_prompt.id)

        assert prompt is not None
        assert prompt.id == test_prompt.id
        assert prompt.title == test_prompt.title

    def test_get_by_id_not_found(self, prompt_repo):
        """Test retrieving non-existent prompt returns None."""
        prompt = prompt_repo.get_by_id(99999)
        assert prompt is None

    def test_get_all(self, prompt_repo, test_prompt, test_category, test_user):
        """Test retrieving all prompts."""
        # Create additional prompt
        prompt_repo.create(
            title="Second Prompt",
            prompt="Second content",
            category_id=test_category.id,
            user_id=test_user.id
        )

        prompts = prompt_repo.get_all()
        assert len(prompts) == 2

    def test_update_prompt(self, prompt_repo, test_prompt):
        """Test updating prompt."""
        updated = prompt_repo.update(
            test_prompt.id,
            title="Updated Title",
            prompt="Updated content"
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.prompt == "Updated content"

    def test_delete_prompt(self, prompt_repo, test_prompt):
        """Test deleting prompt."""
        success = prompt_repo.delete(test_prompt.id)
        assert success is True

        # Verify deletion
        prompt = prompt_repo.get_by_id(test_prompt.id)
        assert prompt is None

    def test_search_by_text(self, prompt_repo, test_prompt):
        """Test searching prompts by text."""
        results = prompt_repo.search(query="test")
        assert len(results) >= 1
        assert test_prompt.id in [p.id for p in results]

    def test_search_by_category(self, prompt_repo, test_prompt, test_category):
        """Test filtering prompts by category."""
        results = prompt_repo.search(category=test_category.name)
        assert len(results) >= 1
        assert test_prompt.id in [p.id for p in results]

    def test_search_by_tags(self, prompt_repo, test_prompt):
        """Test filtering prompts by tags."""
        results = prompt_repo.search(tags=["test"])
        assert len(results) >= 1
        assert test_prompt.id in [p.id for p in results]

    def test_search_by_favorite(self, prompt_repo, test_prompt):
        """Test filtering prompts by favorite status."""
        # Update prompt to be favorite
        prompt_repo.update(test_prompt.id, favorite=True)

        results = prompt_repo.search(favorite=True)
        assert len(results) >= 1
        assert test_prompt.id in [p.id for p in results]

    def test_get_favorites(self, prompt_repo, test_prompt):
        """Test getting favorite prompts."""
        # Update prompt to be favorite
        prompt_repo.update(test_prompt.id, favorite=True)

        favorites = prompt_repo.get_favorites()
        assert len(favorites) >= 1
        assert test_prompt.id in [p.id for p in favorites]

    def test_get_statistics(self, prompt_repo, test_prompt):
        """Test getting prompt statistics."""
        stats = prompt_repo.get_statistics()

        assert stats["total"] >= 1
        assert "favorites" in stats
        assert "with_versions" in stats


class TestVersionRepository:
    """Test VersionRepository operations."""

    def test_create_version(self, version_repo, test_prompt, test_user):
        """Test creating a new version."""
        version = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="Test version"
        )

        assert version.id is not None
        assert version.prompt_id == test_prompt.id
        assert version.version_number == 1
        assert version.message == "Test version"

    def test_get_versions_for_prompt(self, version_repo, test_prompt_with_versions):
        """Test retrieving all versions for a prompt."""
        prompt, versions = test_prompt_with_versions

        results = version_repo.get_versions_for_prompt(prompt.id)

        assert len(results) == 3
        # Should be ordered newest first
        assert results[0].version_number == 3
        assert results[-1].version_number == 1

    def test_get_latest_version(self, version_repo, test_prompt_with_versions):
        """Test getting the latest version."""
        prompt, versions = test_prompt_with_versions

        latest = version_repo.get_latest_version(prompt.id)

        assert latest is not None
        assert latest.version_number == 3

    def test_get_version_count(self, version_repo, test_prompt_with_versions):
        """Test counting versions."""
        prompt, versions = test_prompt_with_versions

        count = version_repo.get_version_count(prompt.id)
        assert count == 3

    def test_get_version_chain(self, version_repo, test_prompt_with_versions):
        """Test getting version parent chain."""
        prompt, versions = test_prompt_with_versions

        # Get chain from latest version
        chain = version_repo.get_version_chain(versions[-1].version_id)

        assert len(chain) >= 1


class TestCategoryRepository:
    """Test CategoryRepository operations."""

    def test_get_by_name(self, category_repo, test_category):
        """Test retrieving category by name."""
        category = category_repo.get_by_name(test_category.name)

        assert category is not None
        assert category.id == test_category.id

    def test_get_or_create_existing(self, category_repo, test_category):
        """Test get_or_create with existing category."""
        category = category_repo.get_or_create(test_category.name)

        assert category.id == test_category.id

    def test_get_or_create_new(self, category_repo):
        """Test get_or_create with new category."""
        category = category_repo.get_or_create("New Category")

        assert category is not None
        assert category.name == "New Category"

    def test_list_all_with_counts(self, category_repo, test_category, test_prompt):
        """Test listing categories with prompt counts."""
        results = category_repo.list_all_with_counts()

        assert len(results) >= 1
        # Each result is (category, prompt_count)
        categories = [cat for cat, count in results]
        assert test_category.id in [c.id for c in categories]

    def test_rename_category(self, category_repo, test_category):
        """Test renaming a category."""
        updated = category_repo.rename(test_category.id, "Renamed Category")

        assert updated is not None
        assert updated.name == "Renamed Category"


class TestTagRepository:
    """Test TagRepository operations."""

    def test_get_by_name(self, tag_repo, test_tags):
        """Test retrieving tag by name."""
        tag = tag_repo.get_by_name(test_tags[0].name)

        assert tag is not None
        assert tag.id == test_tags[0].id

    def test_get_or_create_existing(self, tag_repo, test_tags):
        """Test get_or_create with existing tag."""
        tag = tag_repo.get_or_create(test_tags[0].name)

        assert tag.id == test_tags[0].id

    def test_get_or_create_new(self, tag_repo):
        """Test get_or_create with new tag."""
        tag = tag_repo.get_or_create("new-tag")

        assert tag is not None
        assert tag.name == "new-tag"

    def test_get_or_create_many(self, tag_repo, test_tags):
        """Test creating multiple tags."""
        tag_names = [test_tags[0].name, "new-tag1", "new-tag2"]
        tags = tag_repo.get_or_create_many(tag_names)

        assert len(tags) == 3
        assert tags[0].id == test_tags[0].id  # Existing tag
        assert tags[1].name == "new-tag1"  # New tag
        assert tags[2].name == "new-tag2"  # New tag

    def test_list_all_with_counts(self, tag_repo, test_tags, test_prompt):
        """Test listing tags with usage counts."""
        results = tag_repo.list_all_with_counts()

        assert len(results) >= len(test_tags)
        # Each result is (tag, usage_count)
        tag_names = [tag.name for tag, count in results]
        assert "test" in tag_names

    def test_get_popular_tags(self, tag_repo, test_tags, test_prompt):
        """Test getting popular tags."""
        results = tag_repo.get_popular_tags(limit=5)

        assert len(results) <= 5

    def test_rename_tag(self, tag_repo, test_tags):
        """Test renaming a tag."""
        updated = tag_repo.rename(test_tags[0].id, "renamed-tag")

        assert updated is not None
        assert updated.name == "renamed-tag"

    def test_merge_tags(self, tag_repo, test_tags, test_prompt):
        """Test merging tags."""
        # test_prompt has test_tags[0] and test_tags[1]
        source_tag = test_tags[0]
        target_tag = test_tags[1]

        success = tag_repo.merge_tags(source_tag.id, target_tag.id)

        assert success is True

        # Source tag should be deleted
        deleted_tag = tag_repo.get_by_id(source_tag.id)
        assert deleted_tag is None
