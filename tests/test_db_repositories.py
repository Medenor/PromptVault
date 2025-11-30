# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive tests for PromptVault database repository classes.

This module provides extensive test coverage for all repository classes:
- PromptRepository: Prompt CRUD, search, filtering, and tag management
- VersionRepository: Version control, history, and comparison
- CategoryRepository: Category management and statistics
- TagRepository: Tag management, merging, and statistics

Each test class focuses on one repository and covers:
- CRUD operations (create, read, update, delete)
- Search and filtering functionality
- Relationship management
- Edge cases and error handling
- Statistics and counting
- Unique constraints and validations

Target: 90%+ repository coverage
"""

import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from src.db.models import Prompt, PromptVersion, Category, Tag
from src.db.repositories import (
    PromptRepository,
    VersionRepository,
    CategoryRepository,
    TagRepository,
)


# ============================================================================
# PROMPT REPOSITORY TESTS
# ============================================================================


class TestPromptRepository:
    """Tests for PromptRepository.

    Covers prompt CRUD operations, search, filtering, favorites,
    tag management, and statistics.
    """

    def test_create_prompt(self, prompt_repo, test_user, test_category, test_tags):
        """Test basic prompt creation."""
        prompt = prompt_repo.create(
            title="Test Prompt",
            prompt="Test content",
            category_id=test_category.id,
            note="Test note",
            favorite=False,
            user_id=test_user.id
        )

        assert prompt.id is not None
        assert prompt.title == "Test Prompt"
        assert prompt.prompt == "Test content"
        assert prompt.note == "Test note"
        assert prompt.favorite is False
        assert prompt.user_id == test_user.id
        assert prompt.category_id == test_category.id

    def test_get_by_id(self, prompt_repo, test_prompt):
        """Test retrieving prompt by ID."""
        retrieved = prompt_repo.get_by_id(test_prompt.id)

        assert retrieved is not None
        assert retrieved.id == test_prompt.id
        assert retrieved.title == test_prompt.title
        assert retrieved.prompt == test_prompt.prompt

    def test_get_by_id_not_found(self, prompt_repo):
        """Test retrieving non-existent prompt returns None."""
        result = prompt_repo.get_by_id(99999)
        assert result is None

    def test_get_all(self, prompt_repo, test_user, test_category):
        """Test listing all prompts."""
        # Create multiple prompts
        for i in range(5):
            prompt_repo.create(
                title=f"Prompt {i}",
                prompt=f"Content {i}",
                category_id=test_category.id,
                user_id=test_user.id
            )

        prompts = prompt_repo.get_all()
        assert len(prompts) == 5

    def test_update_prompt(self, prompt_repo, test_prompt):
        """Test updating prompt fields."""
        updated = prompt_repo.update(
            test_prompt.id,
            title="Updated Title",
            prompt="Updated content",
            note="Updated note"
        )

        assert updated is not None
        assert updated.title == "Updated Title"
        assert updated.prompt == "Updated content"
        assert updated.note == "Updated note"

    def test_delete_prompt(self, prompt_repo, test_prompt):
        """Test deleting a prompt."""
        prompt_id = test_prompt.id
        result = prompt_repo.delete(prompt_id)

        assert result is True
        assert prompt_repo.get_by_id(prompt_id) is None

    def test_search_by_text_in_title(self, prompt_repo, test_user, test_category):
        """Test searching by text in title."""
        prompt_repo.create(
            title="Python Best Practices",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="JavaScript Guide",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )

        results = prompt_repo.search(query="Python")
        assert len(results) == 1
        assert results[0].title == "Python Best Practices"

    def test_search_by_text_in_content(self, prompt_repo, test_user, test_category):
        """Test searching by text in prompt content."""
        prompt_repo.create(
            title="Guide 1",
            prompt="This is about machine learning algorithms",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="Guide 2",
            prompt="This is about web development",
            category_id=test_category.id,
            user_id=test_user.id
        )

        results = prompt_repo.search(query="machine learning")
        assert len(results) == 1
        assert "machine learning" in results[0].prompt

    def test_search_by_text_in_note(self, prompt_repo, test_user, test_category):
        """Test searching by text in notes."""
        prompt_repo.create(
            title="Guide 1",
            prompt="Content",
            note="Important for database optimization",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="Guide 2",
            prompt="Content",
            note="Used for frontend testing",
            category_id=test_category.id,
            user_id=test_user.id
        )

        results = prompt_repo.search(query="database")
        assert len(results) == 1
        assert "database" in results[0].note

    def test_search_by_category(self, prompt_repo, test_user, test_db_session):
        """Test filtering by category."""
        cat1 = Category(name="Programming")
        cat2 = Category(name="Writing")
        test_db_session.add_all([cat1, cat2])
        test_db_session.flush()

        prompt_repo.create(
            title="Code Prompt",
            prompt="Content",
            category_id=cat1.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="Write Prompt",
            prompt="Content",
            category_id=cat2.id,
            user_id=test_user.id
        )

        results = prompt_repo.search(category="Programming")
        assert len(results) == 1
        assert results[0].title == "Code Prompt"

    def test_search_by_tags(self, prompt_repo, test_user, test_category, test_db_session):
        """Test filtering by tags."""
        tag1 = Tag(name="python")
        tag2 = Tag(name="javascript")
        test_db_session.add_all([tag1, tag2])
        test_db_session.flush()

        prompt1 = prompt_repo.create(
            title="Python Prompt",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt1.tags.append(tag1)

        prompt2 = prompt_repo.create(
            title="JS Prompt",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt2.tags.append(tag2)

        test_db_session.flush()

        results = prompt_repo.search(tags=["python"])
        assert len(results) == 1
        assert results[0].title == "Python Prompt"

    def test_search_by_multiple_tags(self, prompt_repo, test_user, test_category, test_db_session):
        """Test filtering by multiple tags (OR logic)."""
        tag1 = Tag(name="python")
        tag2 = Tag(name="tutorial")
        test_db_session.add_all([tag1, tag2])
        test_db_session.flush()

        prompt1 = prompt_repo.create(
            title="Python Guide",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt1.tags.append(tag1)

        prompt2 = prompt_repo.create(
            title="Tutorial",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt2.tags.append(tag2)

        test_db_session.flush()

        # Should return prompts with ANY of the tags
        results = prompt_repo.search(tags=["python", "tutorial"])
        assert len(results) == 2

    def test_search_by_favorite(self, prompt_repo, test_user, test_category):
        """Test filtering by favorite status."""
        prompt_repo.create(
            title="Favorite Prompt",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=True
        )
        prompt_repo.create(
            title="Regular Prompt",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=False
        )

        results = prompt_repo.search(favorite=True)
        assert len(results) == 1
        assert results[0].title == "Favorite Prompt"

    def test_search_combined_filters(self, prompt_repo, test_user, test_db_session):
        """Test combining multiple search filters."""
        cat = Category(name="Programming")
        tag = Tag(name="python")
        test_db_session.add_all([cat, tag])
        test_db_session.flush()

        # This should match
        prompt1 = prompt_repo.create(
            title="Python Best Practices",
            prompt="Write clean Python code",
            category_id=cat.id,
            user_id=test_user.id,
            favorite=True
        )
        prompt1.tags.append(tag)

        # This should not match (different category)
        cat2 = Category(name="Writing")
        test_db_session.add(cat2)
        test_db_session.flush()

        prompt2 = prompt_repo.create(
            title="Python in Essays",
            prompt="Content",
            category_id=cat2.id,
            user_id=test_user.id,
            favorite=True
        )
        prompt2.tags.append(tag)

        test_db_session.flush()

        results = prompt_repo.search(
            query="Python",
            category="Programming",
            tags=["python"],
            favorite=True
        )
        assert len(results) == 1
        assert results[0].title == "Python Best Practices"

    def test_get_favorites(self, prompt_repo, test_user, test_category):
        """Test getting all favorited prompts."""
        prompt_repo.create(
            title="Fav 1",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=True
        )
        prompt_repo.create(
            title="Fav 2",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=True
        )
        prompt_repo.create(
            title="Regular",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=False
        )

        favorites = prompt_repo.get_favorites()
        assert len(favorites) == 2

    def test_get_favorites_with_limit(self, prompt_repo, test_user, test_category):
        """Test limiting number of favorites returned."""
        for i in range(5):
            prompt_repo.create(
                title=f"Fav {i}",
                prompt="Content",
                category_id=test_category.id,
                user_id=test_user.id,
                favorite=True
            )

        favorites = prompt_repo.get_favorites(limit=3)
        assert len(favorites) == 3

    def test_pagination(self, prompt_repo, test_user, test_category):
        """Test pagination with offset and limit."""
        for i in range(10):
            prompt_repo.create(
                title=f"Prompt {i}",
                prompt="Content",
                category_id=test_category.id,
                user_id=test_user.id
            )

        # Get page 2 with 3 items per page
        results = prompt_repo.search(offset=3, limit=3)
        assert len(results) == 3

    def test_get_statistics(self, prompt_repo, test_user, test_category, version_repo):
        """Test getting prompt statistics."""
        # Create prompts with different states
        p1 = prompt_repo.create(
            title="Fav with Version",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=True
        )
        version_repo.create_version(p1, "test", "v1")

        p2 = prompt_repo.create(
            title="Fav without Version",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=True
        )

        p3 = prompt_repo.create(
            title="Regular with Version",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id,
            favorite=False
        )
        version_repo.create_version(p3, "test", "v1")

        stats = prompt_repo.get_statistics()
        assert stats["total"] == 3
        assert stats["favorites"] == 2
        assert stats["with_versions"] == 2

    def test_set_favorite(self, prompt_repo, test_prompt):
        """Test setting favorite status."""
        updated = prompt_repo.set_favorite(test_prompt.id, True)
        assert updated.favorite is True

        updated = prompt_repo.set_favorite(test_prompt.id, False)
        assert updated.favorite is False

    def test_add_tag(self, prompt_repo, test_prompt, test_db_session):
        """Test adding a tag to a prompt."""
        new_tag = Tag(name="newtag")
        test_db_session.add(new_tag)
        test_db_session.flush()

        updated = prompt_repo.add_tag(test_prompt.id, new_tag)
        assert new_tag in updated.tags

    def test_add_tag_duplicate(self, prompt_repo, test_user, test_category, test_db_session):
        """Test adding a tag that already exists on prompt."""
        # Create a fresh prompt and tag
        tag = Tag(name="duplicate-test")
        test_db_session.add(tag)
        test_db_session.flush()

        prompt = prompt_repo.create(
            title="Test",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt.tags.append(tag)
        test_db_session.flush()

        # Should not duplicate
        updated = prompt_repo.add_tag(prompt.id, tag)
        tag_count = sum(1 for t in updated.tags if t.id == tag.id)
        assert tag_count == 1

    def test_remove_tag(self, prompt_repo, test_user, test_category, test_db_session):
        """Test removing a tag from a prompt."""
        # Create a fresh prompt and tag
        tag = Tag(name="remove-test")
        test_db_session.add(tag)
        test_db_session.flush()

        prompt = prompt_repo.create(
            title="Test",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt.tags.append(tag)
        test_db_session.flush()

        updated = prompt_repo.remove_tag(prompt.id, tag)
        assert tag not in updated.tags

    def test_get_with_relationships(self, prompt_repo, test_prompt):
        """Test eager loading of all relationships."""
        result = prompt_repo.get_with_relationships(test_prompt.id)

        assert result is not None
        # Access relationships to ensure they're loaded
        assert result.category is not None
        assert result.tags is not None
        assert result.user is not None

    def test_get_by_category(self, prompt_repo, test_user, test_db_session):
        """Test getting all prompts in a category."""
        cat1 = Category(name="Cat1")
        cat2 = Category(name="Cat2")
        test_db_session.add_all([cat1, cat2])
        test_db_session.flush()

        prompt_repo.create(
            title="In Cat1",
            prompt="Content",
            category_id=cat1.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="In Cat2",
            prompt="Content",
            category_id=cat2.id,
            user_id=test_user.id
        )

        results = prompt_repo.get_by_category("Cat1")
        assert len(results) == 1
        assert results[0].title == "In Cat1"

    def test_get_by_tag(self, prompt_repo, test_user, test_category, test_db_session):
        """Test getting all prompts with a specific tag."""
        tag1 = Tag(name="tag1")
        tag2 = Tag(name="tag2")
        test_db_session.add_all([tag1, tag2])
        test_db_session.flush()

        prompt1 = prompt_repo.create(
            title="Prompt1",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt1.tags.append(tag1)

        prompt2 = prompt_repo.create(
            title="Prompt2",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt2.tags.append(tag2)

        test_db_session.flush()

        results = prompt_repo.get_by_tag("tag1")
        assert len(results) == 1
        assert results[0].title == "Prompt1"

    def test_cascade_delete_versions(self, prompt_repo, version_repo, test_prompt):
        """Test that versions are deleted when prompt is deleted."""
        # Create versions
        version_repo.create_version(test_prompt, "test", "v1")
        version_repo.create_version(test_prompt, "test", "v2")

        # Verify versions exist
        versions = version_repo.get_versions_for_prompt(test_prompt.id)
        assert len(versions) == 2

        # Delete prompt
        prompt_repo.delete(test_prompt.id)

        # Versions should be deleted (cascade)
        versions = version_repo.get_versions_for_prompt(test_prompt.id)
        assert len(versions) == 0

    def test_search_case_insensitive(self, prompt_repo, test_user, test_category):
        """Test that search is case-insensitive."""
        prompt_repo.create(
            title="Python Programming",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )

        # Should find with different cases
        results = prompt_repo.search(query="python")
        assert len(results) == 1

        results = prompt_repo.search(query="PYTHON")
        assert len(results) == 1

        results = prompt_repo.search(query="PyThOn")
        assert len(results) == 1

    def test_search_empty_results(self, prompt_repo):
        """Test search with no matches returns empty list."""
        results = prompt_repo.search(query="nonexistent")
        assert results == []


# ============================================================================
# VERSION REPOSITORY TESTS
# ============================================================================


class TestVersionRepository:
    """Tests for VersionRepository.

    Covers version creation, history, comparison, revert, and parent chains.
    """

    def test_create_version(self, version_repo, test_prompt, test_user):
        """Test creating a version snapshot."""
        version = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="Initial version"
        )

        assert version.id is not None
        assert version.version_id is not None
        assert version.version_number == 1
        assert version.prompt_id == test_prompt.id
        assert version.title == test_prompt.title
        assert version.prompt == test_prompt.prompt
        assert version.author == test_user.username
        assert version.message == "Initial version"

    def test_create_version_with_parent(self, version_repo, test_prompt, test_user):
        """Test creating a version with parent linkage."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(
            test_prompt,
            test_user.username,
            "v2",
            parent_version_id=v1.version_id
        )

        assert v2.parent_version_id == v1.version_id
        assert v2.version_number == 2

    def test_get_versions_for_prompt(self, version_repo, test_prompt, test_user):
        """Test retrieving all versions for a prompt."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(test_prompt, test_user.username, "v2")
        v3 = version_repo.create_version(test_prompt, test_user.username, "v3")

        versions = version_repo.get_versions_for_prompt(test_prompt.id)
        assert len(versions) == 3

    def test_get_versions_ordered_newest_first(self, version_repo, test_prompt, test_user):
        """Test that versions are ordered by version number descending."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(test_prompt, test_user.username, "v2")
        v3 = version_repo.create_version(test_prompt, test_user.username, "v3")

        versions = version_repo.get_versions_for_prompt(test_prompt.id)
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2
        assert versions[2].version_number == 1

    def test_get_latest_version(self, version_repo, test_prompt, test_user):
        """Test getting the most recent version."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(test_prompt, test_user.username, "v2")
        v3 = version_repo.create_version(test_prompt, test_user.username, "v3")

        latest = version_repo.get_latest_version(test_prompt.id)
        assert latest.version_number == 3
        assert latest.message == "v3"

    def test_get_latest_version_none(self, version_repo, test_prompt):
        """Test getting latest version when none exist."""
        latest = version_repo.get_latest_version(test_prompt.id)
        assert latest is None

    def test_get_version_by_version_id(self, version_repo, test_prompt, test_user):
        """Test retrieving version by UUID version_id."""
        version = version_repo.create_version(test_prompt, test_user.username, "v1")

        retrieved = version_repo.get_by_version_id(version.version_id)
        assert retrieved is not None
        assert retrieved.id == version.id
        assert retrieved.version_id == version.version_id

    def test_get_version_count(self, version_repo, test_prompt, test_user):
        """Test counting versions for a prompt."""
        assert version_repo.get_version_count(test_prompt.id) == 0

        version_repo.create_version(test_prompt, test_user.username, "v1")
        assert version_repo.get_version_count(test_prompt.id) == 1

        version_repo.create_version(test_prompt, test_user.username, "v2")
        assert version_repo.get_version_count(test_prompt.id) == 2

    def test_get_version_chain(self, version_repo, test_prompt, test_user):
        """Test following parent pointers to build version chain."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(
            test_prompt, test_user.username, "v2", parent_version_id=v1.version_id
        )
        v3 = version_repo.create_version(
            test_prompt, test_user.username, "v3", parent_version_id=v2.version_id
        )

        chain = version_repo.get_version_chain(v3.version_id)
        assert len(chain) == 3
        assert chain[0].version_number == 3
        assert chain[1].version_number == 2
        assert chain[2].version_number == 1

    def test_version_snapshots_immutable(self, version_repo, prompt_repo, test_prompt, test_user):
        """Test that versions remain unchanged when prompt is updated."""
        # Create initial version
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        original_title = v1.title
        original_content = v1.prompt

        # Update the prompt
        prompt_repo.update(
            test_prompt.id,
            title="Updated Title",
            prompt="Updated Content"
        )

        # Version should still have old data
        v1_check = version_repo.get_by_version_id(v1.version_id)
        assert v1_check.title == original_title
        assert v1_check.prompt == original_content

    def test_multiple_prompts_versions(self, version_repo, prompt_repo, test_user, test_category):
        """Test that versions are properly isolated per prompt."""
        p1 = prompt_repo.create(
            title="Prompt 1",
            prompt="Content 1",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p2 = prompt_repo.create(
            title="Prompt 2",
            prompt="Content 2",
            category_id=test_category.id,
            user_id=test_user.id
        )

        # Create versions for each
        version_repo.create_version(p1, test_user.username, "p1v1")
        version_repo.create_version(p1, test_user.username, "p1v2")
        version_repo.create_version(p2, test_user.username, "p2v1")

        # Check isolation
        p1_versions = version_repo.get_versions_for_prompt(p1.id)
        p2_versions = version_repo.get_versions_for_prompt(p2.id)

        assert len(p1_versions) == 2
        assert len(p2_versions) == 1

    def test_version_increments_correctly(self, version_repo, test_prompt, test_user):
        """Test that version numbers increment sequentially."""
        versions = []
        for i in range(5):
            v = version_repo.create_version(test_prompt, test_user.username, f"v{i+1}")
            versions.append(v)

        for i, v in enumerate(versions):
            assert v.version_number == i + 1

    def test_compare_versions(self, version_repo, test_prompt, test_user):
        """Test comparing two versions."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")
        v2 = version_repo.create_version(test_prompt, test_user.username, "v2")

        result = version_repo.compare_versions(v1.version_id, v2.version_id)
        assert result is not None
        assert result[0].version_id == v1.version_id
        assert result[1].version_id == v2.version_id

    def test_compare_versions_not_found(self, version_repo):
        """Test comparing versions when one doesn't exist."""
        result = version_repo.compare_versions("fake-id-1", "fake-id-2")
        assert result is None

    def test_revert_to_version(self, version_repo, prompt_repo, test_prompt, test_user):
        """Test reverting prompt to a previous version."""
        # Create initial version
        prompt_repo.update(test_prompt.id, title="V1 Title", prompt="V1 Content")
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")

        # Update and create another version
        prompt_repo.update(test_prompt.id, title="V2 Title", prompt="V2 Content")
        v2 = version_repo.create_version(test_prompt, test_user.username, "v2")

        # Revert to v1
        revert_version = version_repo.revert_to_version(
            test_prompt,
            v1.version_id,
            test_user.username
        )

        assert revert_version is not None
        assert test_prompt.title == "V1 Title"
        assert test_prompt.prompt == "V1 Content"
        assert revert_version.version_number == 3  # New version created

    def test_revert_creates_new_version(self, version_repo, test_prompt, test_user):
        """Test that revert creates a new version rather than modifying history."""
        v1 = version_repo.create_version(test_prompt, test_user.username, "v1")

        # Revert should create new version
        revert_version = version_repo.revert_to_version(
            test_prompt,
            v1.version_id,
            test_user.username
        )

        # Should have 2 versions total
        versions = version_repo.get_versions_for_prompt(test_prompt.id)
        assert len(versions) == 2

    def test_version_stores_denormalized_tags(self, version_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test that version stores tags as denormalized JSON array."""
        # Create fresh prompt and tags
        tag1 = Tag(name="tag-a")
        tag2 = Tag(name="tag-b")
        test_db_session.add_all([tag1, tag2])
        test_db_session.flush()

        prompt = prompt_repo.create(
            title="Test",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt.tags.extend([tag1, tag2])
        test_db_session.flush()

        version = version_repo.create_version(prompt, test_user.username, "v1")

        assert version.tags is not None
        assert isinstance(version.tags, list)
        assert len(version.tags) == 2
        assert tag1.name in version.tags
        assert tag2.name in version.tags


# ============================================================================
# CATEGORY REPOSITORY TESTS
# ============================================================================


class TestCategoryRepository:
    """Tests for CategoryRepository.

    Covers category CRUD, get-or-create pattern, statistics, and management.
    """

    def test_create_category(self, category_repo):
        """Test basic category creation."""
        category = category_repo.create(name="Programming", description="Code-related prompts")

        assert category.id is not None
        assert category.name == "Programming"
        assert category.description == "Code-related prompts"

    def test_get_by_name(self, category_repo, test_category):
        """Test retrieving category by name."""
        retrieved = category_repo.get_by_name(test_category.name)

        assert retrieved is not None
        assert retrieved.id == test_category.id
        assert retrieved.name == test_category.name

    def test_get_by_name_not_found(self, category_repo):
        """Test retrieving non-existent category returns None."""
        result = category_repo.get_by_name("Nonexistent")
        assert result is None

    def test_get_or_create_existing(self, category_repo, test_category):
        """Test get_or_create returns existing category."""
        result = category_repo.get_or_create(test_category.name)

        assert result.id == test_category.id
        assert result.name == test_category.name

    def test_get_or_create_new(self, category_repo):
        """Test get_or_create creates new category if not exists."""
        result = category_repo.get_or_create("New Category")

        assert result.id is not None
        assert result.name == "New Category"

    def test_get_all(self, category_repo):
        """Test listing all categories."""
        category_repo.create(name="Cat1")
        category_repo.create(name="Cat2")
        category_repo.create(name="Cat3")

        categories = category_repo.get_all()
        assert len(categories) >= 3

    def test_get_all_with_counts(self, category_repo, prompt_repo, test_user, test_db_session):
        """Test getting categories with usage counts."""
        cat1 = category_repo.create(name="Cat1")
        cat2 = category_repo.create(name="Cat2")

        # Create prompts in cat1
        prompt_repo.create(
            title="P1",
            prompt="Content",
            category_id=cat1.id,
            user_id=test_user.id
        )
        prompt_repo.create(
            title="P2",
            prompt="Content",
            category_id=cat1.id,
            user_id=test_user.id
        )

        # Create one prompt in cat2
        prompt_repo.create(
            title="P3",
            prompt="Content",
            category_id=cat2.id,
            user_id=test_user.id
        )

        results = category_repo.list_all_with_counts()

        # Find cat1 in results
        cat1_result = next((r for r in results if r[0].id == cat1.id), None)
        assert cat1_result is not None
        assert cat1_result[1] == 2  # 2 prompts

        # Find cat2 in results
        cat2_result = next((r for r in results if r[0].id == cat2.id), None)
        assert cat2_result is not None
        assert cat2_result[1] == 1  # 1 prompt

    def test_rename_category(self, category_repo, test_category):
        """Test renaming a category."""
        updated = category_repo.rename(test_category.id, "New Name")

        assert updated is not None
        assert updated.name == "New Name"

    def test_rename_category_not_found(self, category_repo):
        """Test renaming non-existent category returns None."""
        result = category_repo.rename(99999, "New Name")
        assert result is None

    def test_delete_unused_category(self, category_repo, test_category):
        """Test deleting category with no prompts."""
        result = category_repo.delete_if_unused(test_category.id)
        assert result is True

        # Verify deleted
        assert category_repo.get_by_id(test_category.id) is None

    def test_delete_used_category_fails(self, category_repo, prompt_repo, test_user, test_category):
        """Test that deleting category with prompts fails."""
        # Create a prompt using the category
        prompt_repo.create(
            title="Test",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )

        result = category_repo.delete_if_unused(test_category.id)
        assert result is False

        # Verify still exists
        assert category_repo.get_by_id(test_category.id) is not None

    def test_category_name_unique(self, category_repo):
        """Test that category names must be unique."""
        category_repo.create(name="Unique")

        with pytest.raises(IntegrityError):
            category_repo.create(name="Unique")

    def test_list_with_counts_includes_zero_counts(self, category_repo):
        """Test that categories with zero prompts are included in counts."""
        cat = category_repo.create(name="Empty Category")

        results = category_repo.list_all_with_counts()
        cat_result = next((r for r in results if r[0].id == cat.id), None)

        assert cat_result is not None
        assert cat_result[1] == 0


# ============================================================================
# TAG REPOSITORY TESTS
# ============================================================================


class TestTagRepository:
    """Tests for TagRepository.

    Covers tag CRUD, get-or-create pattern, statistics, merging, and popularity.
    """

    def test_create_tag(self, tag_repo):
        """Test basic tag creation."""
        tag = tag_repo.create(name="python")

        assert tag.id is not None
        assert tag.name == "python"

    def test_get_by_name(self, tag_repo, test_tags):
        """Test retrieving tag by name."""
        retrieved = tag_repo.get_by_name(test_tags[0].name)

        assert retrieved is not None
        assert retrieved.id == test_tags[0].id
        assert retrieved.name == test_tags[0].name

    def test_get_by_name_not_found(self, tag_repo):
        """Test retrieving non-existent tag returns None."""
        result = tag_repo.get_by_name("nonexistent")
        assert result is None

    def test_get_or_create_existing(self, tag_repo, test_tags):
        """Test get_or_create returns existing tag."""
        result = tag_repo.get_or_create(test_tags[0].name)

        assert result.id == test_tags[0].id
        assert result.name == test_tags[0].name

    def test_get_or_create_new(self, tag_repo):
        """Test get_or_create creates new tag if not exists."""
        result = tag_repo.get_or_create("newtag")

        assert result.id is not None
        assert result.name == "newtag"

    def test_get_or_create_many(self, tag_repo):
        """Test bulk get-or-create operation."""
        tags = tag_repo.get_or_create_many(["tag1", "tag2", "tag3"])

        assert len(tags) == 3
        assert all(tag.id is not None for tag in tags)
        assert [tag.name for tag in tags] == ["tag1", "tag2", "tag3"]

    def test_get_or_create_many_mixed(self, tag_repo, test_tags):
        """Test get_or_create_many with mix of new and existing tags."""
        existing_name = test_tags[0].name
        tags = tag_repo.get_or_create_many([existing_name, "newtag"])

        assert len(tags) == 2
        # First should be existing
        assert tags[0].id == test_tags[0].id
        # Second should be new
        assert tags[1].name == "newtag"

    def test_get_all(self, tag_repo):
        """Test listing all tags."""
        tag_repo.create(name="tag1")
        tag_repo.create(name="tag2")
        tag_repo.create(name="tag3")

        tags = tag_repo.get_all()
        assert len(tags) >= 3

    def test_get_all_with_counts(self, tag_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test getting tags with usage counts."""
        tag1 = tag_repo.create(name="popular")
        tag2 = tag_repo.create(name="uncommon")

        # Create prompts with tag1
        p1 = prompt_repo.create(
            title="P1",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p1.tags.append(tag1)

        p2 = prompt_repo.create(
            title="P2",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p2.tags.append(tag1)

        # Create one prompt with tag2
        p3 = prompt_repo.create(
            title="P3",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p3.tags.append(tag2)

        test_db_session.flush()

        results = tag_repo.list_all_with_counts()

        # Find tag1 in results
        tag1_result = next((r for r in results if r[0].id == tag1.id), None)
        assert tag1_result is not None
        assert tag1_result[1] == 2  # 2 prompts

        # Find tag2 in results
        tag2_result = next((r for r in results if r[0].id == tag2.id), None)
        assert tag2_result is not None
        assert tag2_result[1] == 1  # 1 prompt

    def test_rename_tag(self, tag_repo, test_tags):
        """Test renaming a tag."""
        updated = tag_repo.rename(test_tags[0].id, "newname")

        assert updated is not None
        assert updated.name == "newname"

    def test_rename_tag_not_found(self, tag_repo):
        """Test renaming non-existent tag returns None."""
        result = tag_repo.rename(99999, "newname")
        assert result is None

    def test_merge_tags(self, tag_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test merging two tags."""
        source_tag = tag_repo.create(name="old-tag")
        target_tag = tag_repo.create(name="new-tag")

        # Create prompts with source_tag
        p1 = prompt_repo.create(
            title="P1",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p1.tags.append(source_tag)

        p2 = prompt_repo.create(
            title="P2",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p2.tags.append(source_tag)

        test_db_session.flush()

        # Merge
        result = tag_repo.merge_tags(source_tag.id, target_tag.id)
        assert result is True

        # Source tag should be deleted
        assert tag_repo.get_by_id(source_tag.id) is None

        # Target tag should now be on both prompts
        test_db_session.expire_all()  # Refresh
        p1 = prompt_repo.get_by_id(p1.id)
        p2 = prompt_repo.get_by_id(p2.id)

        assert target_tag in p1.tags
        assert target_tag in p2.tags

    def test_merge_tags_not_found(self, tag_repo):
        """Test merging with non-existent tags returns False."""
        result = tag_repo.merge_tags(99999, 88888)
        assert result is False

    def test_delete_unused_tag(self, tag_repo, test_tags):
        """Test deleting tag with no prompts."""
        # Create a new tag not attached to anything
        unused_tag = tag_repo.create(name="unused")

        result = tag_repo.delete_if_unused(unused_tag.id)
        assert result is True

        # Verify deleted
        assert tag_repo.get_by_id(unused_tag.id) is None

    def test_delete_used_tag_fails(self, tag_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test that deleting tag in use fails."""
        tag = tag_repo.create(name="used-tag")

        # Attach to a prompt
        prompt = prompt_repo.create(
            title="Test",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        prompt.tags.append(tag)
        test_db_session.flush()

        result = tag_repo.delete_if_unused(tag.id)
        assert result is False

        # Verify still exists
        assert tag_repo.get_by_id(tag.id) is not None

    def test_tag_name_unique(self, tag_repo):
        """Test that tag names must be unique."""
        tag_repo.create(name="unique")

        with pytest.raises(IntegrityError):
            tag_repo.create(name="unique")

    def test_get_popular_tags(self, tag_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test getting most popular tags."""
        # Create tags with different usage counts
        tag1 = tag_repo.create(name="very-popular")
        tag2 = tag_repo.create(name="popular")
        tag3 = tag_repo.create(name="uncommon")

        # tag1: 3 prompts
        for i in range(3):
            p = prompt_repo.create(
                title=f"P{i}",
                prompt="Content",
                category_id=test_category.id,
                user_id=test_user.id
            )
            p.tags.append(tag1)

        # tag2: 2 prompts
        for i in range(2):
            p = prompt_repo.create(
                title=f"Q{i}",
                prompt="Content",
                category_id=test_category.id,
                user_id=test_user.id
            )
            p.tags.append(tag2)

        # tag3: 1 prompt
        p = prompt_repo.create(
            title="R",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p.tags.append(tag3)

        test_db_session.flush()

        # Get top 2
        popular = tag_repo.get_popular_tags(limit=2)
        assert len(popular) == 2
        assert popular[0][0].name == "very-popular"
        assert popular[0][1] == 3
        assert popular[1][0].name == "popular"
        assert popular[1][1] == 2

    def test_get_by_names(self, tag_repo, test_tags):
        """Test getting multiple tags by name."""
        names = [test_tags[0].name, test_tags[1].name]
        results = tag_repo.get_by_names(names)

        assert len(results) == 2
        result_names = [tag.name for tag in results]
        assert test_tags[0].name in result_names
        assert test_tags[1].name in result_names

    def test_get_by_names_partial_match(self, tag_repo, test_tags):
        """Test getting tags when some names don't exist."""
        names = [test_tags[0].name, "nonexistent"]
        results = tag_repo.get_by_names(names)

        # Should only return the one that exists
        assert len(results) == 1
        assert results[0].name == test_tags[0].name

    def test_list_with_counts_ordered_by_popularity(self, tag_repo, prompt_repo, test_user, test_category, test_db_session):
        """Test that tags with counts are ordered by usage descending."""
        tag1 = tag_repo.create(name="least")
        tag2 = tag_repo.create(name="most")

        # tag2: 2 prompts
        for i in range(2):
            p = prompt_repo.create(
                title=f"P{i}",
                prompt="Content",
                category_id=test_category.id,
                user_id=test_user.id
            )
            p.tags.append(tag2)

        # tag1: 1 prompt
        p = prompt_repo.create(
            title="Q",
            prompt="Content",
            category_id=test_category.id,
            user_id=test_user.id
        )
        p.tags.append(tag1)

        test_db_session.flush()

        results = tag_repo.list_all_with_counts()

        # Find our tags
        tag2_idx = next((i for i, r in enumerate(results) if r[0].id == tag2.id), None)
        tag1_idx = next((i for i, r in enumerate(results) if r[0].id == tag1.id), None)

        # tag2 should come before tag1 (higher usage)
        assert tag2_idx < tag1_idx
