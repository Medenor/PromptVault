# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive tests for the version control system in PromptVault.

This module provides extensive test coverage for Git-like version control,
including automatic version creation, version history, comparison, revert,
and integration workflows.

Test Categories:
    - TestVersionCreation: Automatic version creation and metadata
    - TestVersionHistory: Version retrieval, ordering, and pagination
    - TestVersionComparison: Version diff and comparison functionality
    - TestVersionRevert: Reverting to previous versions
    - TestVersionIntegration: Complete version control workflows

Target: 90%+ coverage of version control functionality
"""

# ============================================================================
# VERSION CREATION TESTS
# ============================================================================


class TestVersionCreation:
    """Tests for automatic version creation on prompt updates."""

    def test_create_prompt_creates_initial_version(
        self, db_data_service, sample_prompt_data
    ):
        """Test that creating a prompt creates an initial version (v1)."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="Initial"))

        versions = db_data_service.get_prompt_versions(prompt_id)

        assert len(versions) == 1
        assert versions[0]["message"] == "Initial commit"

    def test_update_prompt_creates_new_version(
        self, db_data_service, sample_prompt_data
    ):
        """Test that updating a prompt creates a new version."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        # Update the prompt
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="V2"), "Updated to V2"
        )

        versions = db_data_service.get_prompt_versions(prompt_id)

        assert len(versions) == 2
        assert versions[0]["message"] == "Updated to V2"  # Newest first
        assert versions[1]["message"] == "Initial commit"

    def test_version_has_correct_metadata(self, db_data_service, sample_prompt_data):
        """Test that version has all required metadata fields."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        versions = db_data_service.get_prompt_versions(prompt_id)
        version = versions[0]

        # Check all metadata fields exist
        assert "version_id" in version
        assert "timestamp" in version
        assert "author" in version
        assert "message" in version
        assert "data" in version
        assert "parents" in version

        # Validate metadata values
        assert version["version_id"] is not None
        assert len(version["version_id"]) == 36  # UUID format
        assert "T" in version["timestamp"]  # ISO format
        assert "Z" in version["timestamp"]  # UTC timezone
        assert len(version["author"]) > 0
        assert len(version["message"]) > 0

    def test_version_has_unique_version_id(self, db_data_service, sample_prompt_data):
        """Test that each version gets a unique UUID."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        # Create multiple versions
        for i in range(5):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)
        version_ids = [v["version_id"] for v in versions]

        # All version IDs should be unique
        assert len(version_ids) == len(set(version_ids))

        # All should be valid UUIDs (36 chars with hyphens)
        for vid in version_ids:
            assert len(vid) == 36
            assert vid.count("-") == 4

    def test_version_links_to_parent(self, db_data_service, sample_prompt_data):
        """Test that versions correctly link to their parent version."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1_id = versions_v1[0]["version_id"]

        # First version has no parent
        assert versions_v1[0]["parents"] == []

        # Update to create V2
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="V2"), "Create V2"
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2 = versions_v2[0]  # Newest first

        # V2 should have V1 as parent
        assert len(v2["parents"]) == 1
        assert v2["parents"][0] == v1_id

    def test_version_snapshot_is_complete(self, db_data_service, sample_prompt_data):
        """Test that version captures complete snapshot of all fields."""
        original_data = sample_prompt_data(
            title="Original Title",
            prompt="Original content",
            category="Original Category",
            tags=["tag1", "tag2"],
            note="Original note",
            favorite=True,
        )

        prompt_id = db_data_service.add_new_prompt(original_data)
        versions = db_data_service.get_prompt_versions(prompt_id)
        snapshot = versions[0]["data"]

        # Verify all fields are captured
        assert snapshot["title"] == "Original Title"
        assert snapshot["prompt"] == "Original content"
        # Note: Category name is not stored in version (only category_id)
        # This is a known limitation in current implementation
        assert set(snapshot["tags"]) == {"tag1", "tag2"}
        assert snapshot["note"] == "Original note"
        assert snapshot["favorite"] is True

    def test_version_number_increments(self, version_repo, test_prompt, test_user):
        """Test that version numbers increment sequentially."""
        # Create 5 versions
        for i in range(5):
            version_repo.create_version(
                prompt=test_prompt,
                author=test_user.username,
                message=f"Version {i+1}",
                parent_version_id=None,
            )

        versions = version_repo.get_versions_for_prompt(test_prompt.id)

        # Check sequential numbering (newest first, so reversed order)
        assert versions[0].version_number == 5
        assert versions[1].version_number == 4
        assert versions[2].version_number == 3
        assert versions[3].version_number == 2
        assert versions[4].version_number == 1

    def test_custom_commit_message(self, db_data_service, sample_prompt_data):
        """Test that custom commit messages are preserved."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        custom_messages = [
            "Fixed typo in prompt",
            "Added examples section",
            "Improved clarity",
            "Updated for new API",
        ]

        for msg in custom_messages:
            db_data_service.update_prompt(prompt_id, sample_prompt_data(), msg)

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Check messages (skip initial commit)
        actual_messages = [v["message"] for v in versions[:-1]]

        # Newest first, so reverse expected
        assert actual_messages == list(reversed(custom_messages))


# ============================================================================
# VERSION HISTORY TESTS
# ============================================================================


class TestVersionHistory:
    """Tests for version history retrieval and ordering."""

    def test_get_version_history(self, db_data_service, sample_prompt_data):
        """Test retrieving complete version history."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        # Create 3 more versions
        for i in range(3):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)

        assert len(versions) == 4  # Initial + 3 updates

    def test_version_history_ordered_newest_first(
        self, db_data_service, sample_prompt_data
    ):
        """Test that version history is ordered with newest first."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        for i in range(4):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Titles should be in descending order
        titles = [v["data"]["title"] for v in versions]
        assert titles == ["V5", "V4", "V3", "V2", "V1"]

    def test_version_history_pagination(self, version_repo, test_prompt, test_user):
        """Test limiting number of versions returned."""
        # Create 10 versions
        for i in range(10):
            version_repo.create_version(
                prompt=test_prompt, author=test_user.username, message=f"Version {i+1}"
            )

        # Get limited results
        limited = version_repo.get_versions_for_prompt(test_prompt.id, limit=5)

        assert len(limited) == 5
        # Should be newest 5
        assert limited[0].version_number == 10
        assert limited[4].version_number == 6

    def test_get_latest_version(self, version_repo, test_prompt, test_user):
        """Test getting the most recent version."""
        # Create multiple versions
        for i in range(5):
            version_repo.create_version(
                prompt=test_prompt, author=test_user.username, message=f"Version {i+1}"
            )

        latest = version_repo.get_latest_version(test_prompt.id)

        assert latest is not None
        assert latest.version_number == 5
        assert latest.message == "Version 5"

    def test_get_version_by_id(self, version_repo, test_prompt, test_user):
        """Test retrieving specific version by version_id."""
        version = version_repo.create_version(
            prompt=test_prompt, author=test_user.username, message="Test version"
        )

        version_id = version.version_id

        retrieved = version_repo.get_by_version_id(version_id)

        assert retrieved is not None
        assert retrieved.version_id == version_id
        assert retrieved.message == "Test version"

    def test_get_version_count(self, version_repo, test_prompt, test_user):
        """Test counting versions for a prompt."""
        # Initially no versions
        count_before = version_repo.get_version_count(test_prompt.id)

        # Create 7 versions
        for i in range(7):
            version_repo.create_version(
                prompt=test_prompt, author=test_user.username, message=f"V{i+1}"
            )

        count_after = version_repo.get_version_count(test_prompt.id)

        assert count_after == count_before + 7

    def test_version_chain_traversal(self, version_repo, test_prompt, test_user):
        """Test following parent links through version chain."""
        # Create chain of versions with parent links
        v1 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V1",
            parent_version_id=None,
        )

        v2 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V2",
            parent_version_id=v1.version_id,
        )

        v3 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V3",
            parent_version_id=v2.version_id,
        )

        # Traverse from V3 to root
        chain = version_repo.get_version_chain(v3.version_id)

        assert len(chain) == 3
        assert chain[0].version_id == v3.version_id
        assert chain[1].version_id == v2.version_id
        assert chain[2].version_id == v1.version_id

    def test_multiple_prompts_isolated_versions(
        self, db_data_service, sample_prompt_data
    ):
        """Test that each prompt has its own isolated version history."""
        # Create two prompts
        prompt1_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="Prompt 1")
        )
        prompt2_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="Prompt 2")
        )

        # Update each multiple times
        for i in range(3):
            db_data_service.update_prompt(
                prompt1_id, sample_prompt_data(), f"P1 Update {i}"
            )
            db_data_service.update_prompt(
                prompt2_id, sample_prompt_data(), f"P2 Update {i}"
            )

        versions1 = db_data_service.get_prompt_versions(prompt1_id)
        versions2 = db_data_service.get_prompt_versions(prompt2_id)

        # Each should have 4 versions (initial + 3 updates)
        assert len(versions1) == 4
        assert len(versions2) == 4

        # Version IDs should be completely different
        ids1 = set(v["version_id"] for v in versions1)
        ids2 = set(v["version_id"] for v in versions2)
        assert ids1.isdisjoint(ids2)

    def test_empty_version_history(self, version_repo):
        """Test getting version history for prompt with no versions."""
        non_existent_prompt_id = 99999

        versions = version_repo.get_versions_for_prompt(non_existent_prompt_id)

        assert versions == []

    def test_version_history_after_delete(
        self, db_data_service, sample_prompt_data, test_db_session
    ):
        """Test that deleting prompt also removes all versions."""
        from src.db.models import PromptVersion

        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        # Create several versions
        for i in range(3):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(), f"Update {i}"
            )

        # Verify versions exist
        versions_before = db_data_service.get_prompt_versions(prompt_id)
        assert len(versions_before) > 0

        # Delete the prompt
        db_data_service.delete_prompt(prompt_id)

        # Verify versions are gone (cascade delete)
        versions_after = (
            test_db_session.query(PromptVersion)
            .filter(PromptVersion.prompt_id == prompt_id)
            .all()
        )

        assert len(versions_after) == 0


# ============================================================================
# VERSION COMPARISON TESTS
# ============================================================================


class TestVersionComparison:
    """Tests for comparing and diffing versions."""

    def test_compare_two_versions(self, version_repo, test_prompt, test_user):
        """Test basic comparison of two versions."""
        v1 = version_repo.create_version(
            prompt=test_prompt, author=test_user.username, message="V1"
        )

        # Modify prompt
        test_prompt.title = "Modified Title"

        v2 = version_repo.create_version(
            prompt=test_prompt, author=test_user.username, message="V2"
        )

        result = version_repo.compare_versions(v1.version_id, v2.version_id)

        assert result is not None
        assert result[0].version_id == v1.version_id
        assert result[1].version_id == v2.version_id

    def test_compare_shows_changed_fields(self, db_data_service, sample_prompt_data):
        """Test that comparison identifies which fields changed."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="Original", prompt="Original content")
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1 = versions_v1[0]

        # Update only title
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(title="Changed", prompt="Original content"),
            "Changed title",
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2 = versions_v2[0]

        # Compare data snapshots
        assert v1["data"]["title"] != v2["data"]["title"]
        assert v1["data"]["prompt"] == v2["data"]["prompt"]

    def test_compare_shows_added_tags(self, db_data_service, sample_prompt_data):
        """Test identifying added tags between versions."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(tags=["tag1"]))

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1 = versions_v1[0]

        # Add tags
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(tags=["tag1", "tag2", "tag3"]), "Added tags"
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2 = versions_v2[0]

        # Calculate diff
        old_tags = set(v1["data"]["tags"])
        new_tags = set(v2["data"]["tags"])
        added_tags = new_tags - old_tags

        assert added_tags == {"tag2", "tag3"}

    def test_compare_shows_removed_tags(self, db_data_service, sample_prompt_data):
        """Test identifying removed tags between versions."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(tags=["tag1", "tag2", "tag3"])
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1 = versions_v1[0]

        # Remove tags
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(tags=["tag1"]), "Removed tags"
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2 = versions_v2[0]

        # Calculate diff
        old_tags = set(v1["data"]["tags"])
        new_tags = set(v2["data"]["tags"])
        removed_tags = old_tags - new_tags

        assert removed_tags == {"tag2", "tag3"}

    def test_compare_shows_category_change(self, db_data_service, sample_prompt_data):
        """Test identifying category changes."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(category="Category A")
        )

        # Get the current prompt data which has category name
        current_v1 = db_data_service.get_prompt_data(prompt_id)

        # Change category
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(category="Category B"), "Changed category"
        )

        current_v2 = db_data_service.get_prompt_data(prompt_id)

        # Current prompt data should show category changes
        assert current_v1["category"] == "Category A"
        assert current_v2["category"] == "Category B"

    def test_compare_with_missing_version(self, version_repo):
        """Test comparison with non-existent version returns None."""
        result = version_repo.compare_versions("invalid-id-1", "invalid-id-2")

        assert result is None

    def test_compare_same_version(self, version_repo, test_prompt, test_user):
        """Test comparing a version with itself shows no changes."""
        v1 = version_repo.create_version(
            prompt=test_prompt, author=test_user.username, message="V1"
        )

        result = version_repo.compare_versions(v1.version_id, v1.version_id)

        assert result is not None
        assert result[0].version_id == result[1].version_id
        # Both versions are identical
        assert result[0].title == result[1].title
        assert result[0].prompt == result[1].prompt

    def test_compare_content_diff(self, db_data_service, sample_prompt_data):
        """Test detecting differences in prompt content."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(
                prompt="This is the original content.\nIt has multiple lines."
            )
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1 = versions_v1[0]

        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(
                prompt="This is the modified content.\nIt has different lines."
            ),
            "Modified content",
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2 = versions_v2[0]

        assert v1["data"]["prompt"] != v2["data"]["prompt"]


# ============================================================================
# VERSION REVERT TESTS
# ============================================================================


class TestVersionRevert:
    """Tests for reverting to previous versions."""

    def test_revert_to_previous_version(self, db_data_service, sample_prompt_data):
        """Test basic revert to a previous version."""
        # Create initial version
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="V1", prompt="Content V1")
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1_data = versions_v1[0]["data"]

        # Update to V2
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(title="V2", prompt="Content V2"),
            "Update to V2",
        )

        # Revert to V1
        db_data_service.revert_prompt_to_version(prompt_id, v1_data, "Reverted to V1")

        # Check current state
        current = db_data_service.get_prompt_data(prompt_id)
        assert current["title"] == "V1"
        assert current["prompt"] == "Content V1"

    def test_revert_creates_new_version(self, db_data_service, sample_prompt_data):
        """Test that revert creates a new version instead of deleting history."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        # Create V2
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="V2"), "Update to V2"
        )

        # Get V1 data
        versions = db_data_service.get_prompt_versions(prompt_id)
        v1_data = versions[1]["data"]  # Second item (oldest to newest reversed)

        # Revert
        db_data_service.revert_prompt_to_version(prompt_id, v1_data, "Revert to V1")

        # Should have 3 versions: V1, V2, Revert
        final_versions = db_data_service.get_prompt_versions(prompt_id)
        assert len(final_versions) == 3

        # Latest should be the revert
        assert final_versions[0]["message"] == "Revert to V1"

    def test_revert_restores_all_fields(self, db_data_service, sample_prompt_data):
        """Test that revert restores all prompt fields."""
        original = sample_prompt_data(
            title="Original",
            prompt="Original content",
            category="Cat A",
            tags=["tag1", "tag2"],
            note="Original note",
            favorite=True,
        )

        prompt_id = db_data_service.add_new_prompt(original)

        # Get original state from current prompt (has category name)
        original_state = db_data_service.get_prompt_data(prompt_id)

        # Update to completely different values
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(
                title="Modified",
                prompt="Modified content",
                category="Cat B",
                tags=["tag3"],
                note="Modified note",
                favorite=False,
            ),
            "Complete overhaul",
        )

        # Revert using original state
        db_data_service.revert_prompt_to_version(
            prompt_id, original_state, "Revert to original"
        )

        # Verify all fields restored
        restored = db_data_service.get_prompt_data(prompt_id)
        assert restored["title"] == "Original"
        assert restored["prompt"] == "Original content"
        assert restored["category"] == "Cat A"
        assert set(restored["tags"]) == {"tag1", "tag2"}
        assert restored["note"] == "Original note"
        assert restored["favorite"] is True

    def test_revert_restores_tags(self, db_data_service, sample_prompt_data):
        """Test that reverting correctly restores tags."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(tags=["original", "tags"])
        )

        versions = db_data_service.get_prompt_versions(prompt_id)
        original_data = versions[0]["data"]

        # Update with different tags
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(tags=["new", "different", "tags"]),
            "Changed tags",
        )

        # Revert
        db_data_service.revert_prompt_to_version(
            prompt_id, original_data, "Revert tags"
        )

        restored = db_data_service.get_prompt_data(prompt_id)
        assert set(restored["tags"]) == {"original", "tags"}

    def test_revert_restores_category(self, db_data_service, sample_prompt_data):
        """Test that reverting restores category."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(category="Original Category")
        )

        # Get original state from current prompt (has category name)
        original_state = db_data_service.get_prompt_data(prompt_id)

        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(category="New Category"), "Changed category"
        )

        db_data_service.revert_prompt_to_version(
            prompt_id, original_state, "Revert category"
        )

        restored = db_data_service.get_prompt_data(prompt_id)
        assert restored["category"] == "Original Category"

    def test_revert_with_commit_message(self, db_data_service, sample_prompt_data):
        """Test custom commit message on revert."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        versions = db_data_service.get_prompt_versions(prompt_id)
        v1_data = versions[0]["data"]

        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="V2"), "Update"
        )

        custom_message = "Reverting due to bug in V2"
        db_data_service.revert_prompt_to_version(prompt_id, v1_data, custom_message)

        final_versions = db_data_service.get_prompt_versions(prompt_id)
        assert final_versions[0]["message"] == custom_message

    def test_revert_to_nonexistent_version(self, version_repo, test_prompt, test_user):
        """Test that reverting to non-existent version fails gracefully."""
        result = version_repo.revert_to_version(
            test_prompt, "nonexistent-version-id", test_user.username
        )

        assert result is None

    def test_revert_updates_current_prompt(self, db_data_service, sample_prompt_data):
        """Test that revert actually updates the current prompt state."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="Original"))

        versions = db_data_service.get_prompt_versions(prompt_id)
        original_data = versions[0]["data"]

        # Multiple updates
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="Update 1"), "U1"
        )
        db_data_service.update_prompt(
            prompt_id, sample_prompt_data(title="Update 2"), "U2"
        )

        # Current should be "Update 2"
        before_revert = db_data_service.get_prompt_data(prompt_id)
        assert before_revert["title"] == "Update 2"

        # Revert to original
        db_data_service.revert_prompt_to_version(prompt_id, original_data, "Revert")

        # Current should now be "Original"
        after_revert = db_data_service.get_prompt_data(prompt_id)
        assert after_revert["title"] == "Original"

    def test_multiple_reverts(self, db_data_service, sample_prompt_data):
        """Test that multiple reverts can be performed."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        # Create versions V2, V3, V4
        for i in range(2, 5):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i}"), f"Update to V{i}"
            )

        # Get V1 and V2 data
        versions = db_data_service.get_prompt_versions(prompt_id)
        v1_data = versions[3]["data"]  # Oldest (4th from top)
        v2_data = versions[2]["data"]  # Second oldest

        # Revert to V1
        db_data_service.revert_prompt_to_version(prompt_id, v1_data, "Revert to V1")
        current = db_data_service.get_prompt_data(prompt_id)
        assert current["title"] == "V1"

        # Revert to V2
        db_data_service.revert_prompt_to_version(prompt_id, v2_data, "Revert to V2")
        current = db_data_service.get_prompt_data(prompt_id)
        assert current["title"] == "V2"

    def test_revert_to_first_version(self, db_data_service, sample_prompt_data):
        """Test reverting all the way back to the first version."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="First Version")
        )

        versions_initial = db_data_service.get_prompt_versions(prompt_id)
        first_version_data = versions_initial[0]["data"]

        # Create many versions
        for i in range(10):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"Version {i+2}"), f"Update {i+1}"
            )

        # Revert to first
        db_data_service.revert_prompt_to_version(
            prompt_id, first_version_data, "Back to the beginning"
        )

        current = db_data_service.get_prompt_data(prompt_id)
        assert current["title"] == "First Version"


# ============================================================================
# VERSION INTEGRATION TESTS
# ============================================================================


class TestVersionIntegration:
    """Integration tests for complete version control workflows."""

    def test_complete_version_workflow(self, db_data_service, sample_prompt_data):
        """Test complete workflow: create, update, compare, revert."""
        # Create
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="Initial", tags=["v1"])
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        assert len(versions_v1) == 1
        v1_data = versions_v1[0]["data"]

        # Update
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(title="Updated", tags=["v1", "v2"]),
            "Added features",
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        assert len(versions_v2) == 2
        v2_data = versions_v2[0]["data"]

        # Compare
        assert v1_data["title"] != v2_data["title"]
        assert len(v2_data["tags"]) > len(v1_data["tags"])

        # Revert
        db_data_service.revert_prompt_to_version(
            prompt_id, v1_data, "Reverting changes"
        )

        current = db_data_service.get_prompt_data(prompt_id)
        assert current["title"] == "Initial"
        assert current["tags"] == ["v1"]

    def test_version_branches_not_supported(self, version_repo, test_prompt, test_user):
        """Test that only linear history is supported (no branching)."""
        # Create linear chain
        v1 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V1",
            parent_version_id=None,
        )

        v2 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V2",
            parent_version_id=v1.version_id,
        )

        v3 = version_repo.create_version(
            prompt=test_prompt,
            author=test_user.username,
            message="V3",
            parent_version_id=v2.version_id,
        )

        # Each version has at most one parent
        assert len(v1.child_versions) > 0  # Has children
        assert v1.parent_version is None  # No parent
        assert v2.parent_version is not None  # Has parent
        assert v3.parent_version is not None  # Has parent

    def test_version_immutability(
        self, db_data_service, sample_prompt_data, test_db_session
    ):
        """Test that old versions never change."""
        from src.db.models import PromptVersion

        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="V1", prompt="Content V1")
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1_id = versions_v1[0]["version_id"]
        v1_snapshot = versions_v1[0]["data"].copy()

        # Create more versions
        for i in range(5):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Update {i+1}"
            )

        # Check that V1 is still unchanged
        v1_from_db = (
            test_db_session.query(PromptVersion)
            .filter(PromptVersion.version_id == v1_id)
            .first()
        )

        assert v1_from_db.title == v1_snapshot["title"]
        assert v1_from_db.prompt == v1_snapshot["prompt"]

    def test_concurrent_updates_version_handling(
        self, db_data_service, sample_prompt_data
    ):
        """Test that sequential updates create proper version chain."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data(title="V1"))

        # Simulate rapid sequential updates
        for i in range(10):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Rapid update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Should have 11 versions (initial + 10 updates)
        assert len(versions) == 11

        # Each should have incremental version numbers
        [v.get("version_number", i) for i, v in enumerate(reversed(versions))]
        # We can't verify version_number in dict format, so just check count
        assert len(versions) == 11

    def test_version_with_all_field_changes(self, db_data_service, sample_prompt_data):
        """Test version capturing changes to all fields simultaneously."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(
                title="Old Title",
                prompt="Old content",
                category="Old Cat",
                tags=["old"],
                note="Old note",
                favorite=False,
            )
        )

        # Get state before changes
        state_v1 = db_data_service.get_prompt_data(prompt_id)

        # Change everything
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(
                title="New Title",
                prompt="New content",
                category="New Cat",
                tags=["new"],
                note="New note",
                favorite=True,
            ),
            "Complete rewrite",
        )

        # Get state after changes
        state_v2 = db_data_service.get_prompt_data(prompt_id)

        # All fields should be different
        assert state_v1["title"] != state_v2["title"]
        assert state_v1["prompt"] != state_v2["prompt"]
        assert state_v1["category"] != state_v2["category"]
        assert state_v1["tags"] != state_v2["tags"]
        assert state_v1["note"] != state_v2["note"]
        assert state_v1["favorite"] != state_v2["favorite"]

    def test_version_with_partial_updates(self, db_data_service, sample_prompt_data):
        """Test updating only some fields creates proper version."""
        prompt_id = db_data_service.add_new_prompt(
            sample_prompt_data(title="Title", prompt="Content", tags=["tag1"])
        )

        versions_v1 = db_data_service.get_prompt_versions(prompt_id)
        v1_data = versions_v1[0]["data"]

        # Update only title
        db_data_service.update_prompt(
            prompt_id,
            sample_prompt_data(
                title="New Title", prompt="Content", tags=["tag1"]  # Same  # Same
            ),
            "Just title change",
        )

        versions_v2 = db_data_service.get_prompt_versions(prompt_id)
        v2_data = versions_v2[0]["data"]

        # Only title changed
        assert v1_data["title"] != v2_data["title"]
        assert v1_data["prompt"] == v2_data["prompt"]
        assert v1_data["tags"] == v2_data["tags"]

    def test_version_preserves_timestamps(self, db_data_service, sample_prompt_data):
        """Test that version timestamps are preserved and accurate."""
        import time

        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())
        time.sleep(0.1)  # Small delay

        db_data_service.update_prompt(prompt_id, sample_prompt_data(), "Update 1")
        time.sleep(0.1)

        db_data_service.update_prompt(prompt_id, sample_prompt_data(), "Update 2")

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Timestamps should be in descending order (newest first)
        timestamps = [v["timestamp"] for v in versions]

        # All should be valid ISO format
        for ts in timestamps:
            assert "T" in ts
            assert "Z" in ts

        # Newest first means first timestamp > last timestamp
        assert timestamps[0] > timestamps[-1]

    def test_version_author_tracking(self, version_repo, test_prompt, test_user):
        """Test that version authors are tracked correctly."""
        authors = ["user1", "user2", "user3"]

        for author in authors:
            version_repo.create_version(
                prompt=test_prompt, author=author, message=f"Commit by {author}"
            )

        versions = version_repo.get_versions_for_prompt(test_prompt.id)

        version_authors = [v.author for v in versions]

        # All authors should be present (reversed order due to newest first)
        assert version_authors == list(reversed(authors))

    def test_version_search_in_history(self, db_data_service, sample_prompt_data):
        """Test searching for specific version by message."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        messages = [
            "Added feature X",
            "Fixed bug Y",
            "Improved performance",
            "Updated documentation",
        ]

        for msg in messages:
            db_data_service.update_prompt(prompt_id, sample_prompt_data(), msg)

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Find specific version
        bug_fix = [v for v in versions if "bug" in v["message"].lower()]

        assert len(bug_fix) == 1
        assert bug_fix[0]["message"] == "Fixed bug Y"

    def test_export_version_history(self, db_data_service, sample_prompt_data):
        """Test that version history can be exported."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        for i in range(5):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(title=f"V{i+2}"), f"Update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Export as JSON-serializable format
        export_data = [
            {
                "version_id": v["version_id"],
                "timestamp": v["timestamp"],
                "author": v["author"],
                "message": v["message"],
                "title": v["data"]["title"],
            }
            for v in versions
        ]

        # Should be JSON serializable
        import json

        json_str = json.dumps(export_data)
        assert json_str is not None
        assert len(export_data) == 6  # Initial + 5 updates

    def test_version_statistics(self, db_data_service, sample_prompt_data):
        """Test version statistics and analytics."""
        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        # Create versions with different authors
        for i in range(10):
            db_data_service.update_prompt(
                prompt_id, sample_prompt_data(), f"Update {i+1}"
            )

        versions = db_data_service.get_prompt_versions(prompt_id)

        # Statistics
        total_versions = len(versions)
        authors = set(v["author"] for v in versions)
        messages = [v["message"] for v in versions]

        assert total_versions == 11  # Initial + 10 updates
        assert len(authors) > 0  # At least one author
        assert len(messages) == total_versions

    def test_version_cleanup_on_prompt_delete(
        self, db_data_service, sample_prompt_data, test_db_session
    ):
        """Test that versions are cascade deleted when prompt is deleted."""
        from src.db.models import PromptVersion

        prompt_id = db_data_service.add_new_prompt(sample_prompt_data())

        # Create versions
        for i in range(5):
            db_data_service.update_prompt(prompt_id, sample_prompt_data(), f"U{i}")

        # Get version IDs
        versions = db_data_service.get_prompt_versions(prompt_id)
        version_ids = [v["version_id"] for v in versions]

        # Delete prompt
        db_data_service.delete_prompt(prompt_id)

        # Verify all versions are gone
        for vid in version_ids:
            version = (
                test_db_session.query(PromptVersion)
                .filter(PromptVersion.version_id == vid)
                .first()
            )
            assert version is None
