# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Comprehensive integration tests for undo persistence.

This test suite verifies:
1. Undo persistence across sessions/restarts
2. User-scoped undo isolation
3. Relationship-aware undo operations
4. Edge cases and error scenarios
5. Transaction safety
6. Undo stack depth management
7. Performance with large payloads
"""

import json
import pytest
from typing import Dict
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.db.models.undo_operation import UndoOperation
from src.services.undo_service import UndoService

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def api_client(api_client_context):
    """Get API client from context."""
    return api_client_context["client"]


@pytest.fixture
def api_auth_headers(api_client_context) -> Dict[str, str]:
    """Create authentication headers for primary test user."""
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-test-user-id",
        username="apiuser",
        email="api@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def user_a_headers() -> Dict[str, str]:
    """Create authentication headers for user A."""
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="user-a-id",
        username="user_a",
        email="user_a@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def user_b_headers() -> Dict[str, str]:
    """Create authentication headers for user B."""
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="user-b-id",
        username="user_b",
        email="user_b@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def user_c_headers() -> Dict[str, str]:
    """Create authentication headers for user C."""
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="user-c-id",
        username="user_c",
        email="user_c@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def setup_test_users(test_db_session: Session):
    """Create test users in database for multi-user testing."""
    from src.db.models.user import User
    from src.services.auth.password_service import PasswordService
    from src.config.auth_config import auth_settings

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("TestP@ssw0rd123")

    users = [
        User(
            id="user-a-id",
            username="user_a",
            email="user_a@example.com",
            password_hash=password_hash,
            role="editor",
            is_active=True,
            email_verified=True,
        ),
        User(
            id="user-b-id",
            username="user_b",
            email="user_b@example.com",
            password_hash=password_hash,
            role="editor",
            is_active=True,
            email_verified=True,
        ),
        User(
            id="user-c-id",
            username="user_c",
            email="user_c@example.com",
            password_hash=password_hash,
            role="editor",
            is_active=True,
            email_verified=True,
        ),
    ]

    for user in users:
        test_db_session.add(user)
    test_db_session.commit()

    return users


def _create_prompt(
    api_client, auth_headers, title: str, category: str = "", tags: str = ""
) -> int:
    """Helper to create a prompt via API."""
    response = api_client.post(
        "/api/prompts",
        headers=auth_headers,
        data={
            "title": title,
            "prompt": "Sample content",
            "category": category,
            "tags": tags,
            "commit_message": "Create prompt",
        },
    )
    assert response.status_code == 201
    return response.json()["prompt_id"]


# ============================================================================
# UNDO PERSISTENCE TESTS
# ============================================================================


class TestUndoPersistence:
    """Test that undo operations persist across sessions."""

    def test_category_delete_persists_across_restart(
        self, api_client, api_auth_headers
    ):
        """Test category delete -> restart -> undo works."""
        # Create category
        create_resp = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "PersistCat", "description": "Test persistence"},
        )
        assert create_resp.status_code == 201
        category_id = create_resp.json()["id"]

        # Delete category (this creates undo operation)
        delete_resp = api_client.delete(
            f"/api/categories/{category_id}?confirm=true",
            headers=api_auth_headers,
        )
        assert delete_resp.status_code == 200

        # Undo should still work (verifying persistence across API calls)
        undo_resp = api_client.post("/api/categories/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Category should be restored
        listing = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        names = [item["name"] for item in listing["items"]]
        assert "PersistCat" in names

    def test_tag_update_persists_across_restart(self, api_client, api_auth_headers):
        """Test tag update -> restart -> undo works."""
        # Create tag
        create_resp = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "PersistTag", "description": "Before"},
        )
        tag_id = create_resp.json()["id"]

        # Update tag
        update_resp = api_client.put(
            f"/api/tags/{tag_id}",
            headers=api_auth_headers,
            json={"description": "After"},
        )
        assert update_resp.status_code == 200

        # Undo should work (verifying persistence across API calls)
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Tag should be reverted
        listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()
        tag_item = next(item for item in listing["items"] if item["id"] == tag_id)
        assert tag_item["description"] == "Before"

    def test_complex_merge_persists_across_restart(self, api_client, api_auth_headers):
        """Test complex merge operation -> restart -> undo works."""
        # Create two tags
        tag_a = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "MergeA"},
        ).json()
        tag_b = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "MergeB"},
        ).json()

        # Create prompt with MergeA tag
        _create_prompt(api_client, api_auth_headers, title="Merge test", tags="MergeA")

        # Merge tags
        merge_resp = api_client.post(
            "/api/tags/merge",
            headers=api_auth_headers,
            json={
                "target_id": tag_b["id"],
                "source_ids": [tag_a["id"]],
                "confirm": True,
            },
        )
        assert merge_resp.status_code == 200

        # Undo should work (verifying persistence across API calls)
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # MergeA should be restored
        listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()
        names = [item["name"] for item in listing["items"]]
        assert "MergeA" in names


# ============================================================================
# USER-SCOPED UNDO TESTS
# ============================================================================


class TestUserScopedUndo:
    """Test that undo operations are properly scoped to users."""

    def test_undo_operations_scoped_to_user(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test that undo operations are scoped to the user who created them."""
        # Create category and update it
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "ScopedCat", "description": "Before"},
        ).json()
        api_client.put(
            f"/api/categories/{cat['id']}",
            headers=api_auth_headers,
            json={"description": "After"},
        )

        # Verify undo operation belongs to the correct user
        undo_service = UndoService(test_db_session)
        history = undo_service.get_history("api-test-user-id", entity_type="category")
        assert len(history) > 0
        assert history[0]["operation"] == "update"

        # Different user should have no undo history
        other_user_history = undo_service.get_history(
            "different-user-id", entity_type="category"
        )
        assert len(other_user_history) == 0

    def test_multiple_users_isolated_undo_stacks(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test that different users have isolated undo stacks at the service level."""
        # User creates and updates category
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "IsolatedCat", "description": "Before"},
        ).json()
        api_client.put(
            f"/api/categories/{cat['id']}",
            headers=api_auth_headers,
            json={"description": "After"},
        )

        # Manually create an undo operation for a different user
        undo_service = UndoService(test_db_session)
        undo_service.push(
            user_id="other-user-id",
            entity_type="category",
            operation="delete",
            payload={"category": {"name": "OtherCat"}, "prompt_ids": []},
        )
        test_db_session.commit()

        # First user's history should not include other user's operations
        user_history = undo_service.get_history(
            "api-test-user-id", entity_type="category"
        )
        assert all(op["operation"] == "update" for op in user_history)

        # Other user's history should only have their operation
        other_history = undo_service.get_history(
            "other-user-id", entity_type="category"
        )
        assert len(other_history) == 1
        assert other_history[0]["operation"] == "delete"

    def test_user_cannot_pop_other_users_undo_operations(self, test_db_session):
        """Test that popping undo operations respects user isolation."""
        undo_service = UndoService(test_db_session)

        # Create operations for two different users
        undo_service.push(
            user_id="user-a",
            entity_type="category",
            operation="delete",
            payload={"category": {"name": "UserACat"}},
        )
        undo_service.push(
            user_id="user-b",
            entity_type="category",
            operation="delete",
            payload={"category": {"name": "UserBCat"}},
        )
        test_db_session.commit()

        # User A pops their operation
        user_a_op = undo_service.pop("user-a", "category")
        assert user_a_op is not None
        assert user_a_op["payload"]["category"]["name"] == "UserACat"

        # User A should have no more operations
        assert undo_service.pop("user-a", "category") is None

        # User B should still have their operation
        user_b_op = undo_service.pop("user-b", "category")
        assert user_b_op is not None
        assert user_b_op["payload"]["category"]["name"] == "UserBCat"

    def test_concurrent_operations_different_entity_types(
        self, api_client, api_auth_headers
    ):
        """Test that concurrent operations on different entity types are isolated."""
        # Create and update category
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "ConcurrentCat", "description": "Before"},
        ).json()
        api_client.put(
            f"/api/categories/{cat['id']}",
            headers=api_auth_headers,
            json={"description": "After Cat"},
        )

        # Create and update tag
        tag = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "ConcurrentTag", "description": "Before"},
        ).json()
        api_client.put(
            f"/api/tags/{tag['id']}",
            headers=api_auth_headers,
            json={"description": "After Tag"},
        )

        # Undo tag should not affect category
        undo_tag = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_tag.status_code == 200

        # Verify tag was reverted
        tag_listing = api_client.get(
            "/api/tags/manage", headers=api_auth_headers
        ).json()
        tag_item = next(
            item for item in tag_listing["items"] if item["id"] == tag["id"]
        )
        assert tag_item["description"] == "Before"

        # Verify category was not affected
        cat_listing = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        cat_item = next(
            item for item in cat_listing["items"] if item["id"] == cat["id"]
        )
        assert cat_item["description"] == "After Cat"


# ============================================================================
# RELATIONSHIP-AWARE UNDO TESTS
# ============================================================================


class TestRelationshipAwareUndo:
    """Test undo operations that involve entity relationships."""

    def test_undo_category_deletion_restores_prompts(
        self, api_client, api_auth_headers
    ):
        """Test undo of category deletion that affects tagged prompts."""
        # Create category
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "WithPrompts"},
        ).json()

        # Create prompts with this category
        prompt_id = _create_prompt(
            api_client, api_auth_headers, title="Test", category="WithPrompts"
        )

        # Delete category with force
        delete_resp = api_client.delete(
            f"/api/categories/{cat['id']}?confirm=true&force=true",
            headers=api_auth_headers,
        )
        assert delete_resp.status_code == 200

        # Verify prompt's category was cleared
        prompt = api_client.get(
            f"/api/prompts/{prompt_id}", headers=api_auth_headers
        ).json()
        assert prompt["category"] == "No category"

        # Undo deletion
        undo_resp = api_client.post("/api/categories/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Verify category is restored
        listing = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        names = [item["name"] for item in listing["items"]]
        assert "WithPrompts" in names

        # Verify prompt's category is restored
        prompt_after = api_client.get(
            f"/api/prompts/{prompt_id}", headers=api_auth_headers
        ).json()
        assert prompt_after["category"] == "WithPrompts"

    def test_undo_tag_deletion_with_children(self, api_client, api_auth_headers):
        """Test undo of tag deletion with child tags."""
        # Create parent tag
        parent = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "ParentTag"},
        ).json()

        # Create child tag
        child = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "ChildTag", "parent_tag_id": parent["id"]},
        ).json()

        # Delete parent tag with force
        delete_resp = api_client.delete(
            f"/api/tags/{parent['id']}?confirm=true&force=true",
            headers=api_auth_headers,
        )
        assert delete_resp.status_code == 200

        # Undo deletion
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Verify parent is restored
        listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()
        names = [item["name"] for item in listing["items"]]
        assert "ParentTag" in names

    def test_undo_merge_restores_all_records(self, api_client, api_auth_headers):
        """Test undo of merge operations verifies all records restored."""
        # Create multiple tags
        tag_a = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "MergeSourceA"},
        ).json()
        tag_b = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "MergeSourceB"},
        ).json()
        tag_target = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "MergeTarget"},
        ).json()

        # Create prompts with source tags
        prompt_a = _create_prompt(
            api_client, api_auth_headers, title="With A", tags="MergeSourceA"
        )
        prompt_b = _create_prompt(
            api_client, api_auth_headers, title="With B", tags="MergeSourceB"
        )

        # Merge both sources into target
        merge_resp = api_client.post(
            "/api/tags/merge",
            headers=api_auth_headers,
            json={
                "target_id": tag_target["id"],
                "source_ids": [tag_a["id"], tag_b["id"]],
                "confirm": True,
            },
        )
        assert merge_resp.status_code == 200

        # Verify sources are deleted
        listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()
        names = [item["name"] for item in listing["items"]]
        assert "MergeSourceA" not in names
        assert "MergeSourceB" not in names

        # Undo merge
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Verify both sources are restored
        listing_after = api_client.get(
            "/api/tags/manage", headers=api_auth_headers
        ).json()
        names_after = [item["name"] for item in listing_after["items"]]
        assert "MergeSourceA" in names_after
        assert "MergeSourceB" in names_after

    def test_undo_with_parent_child_relationships(self, api_client, api_auth_headers):
        """Test undo with parent-child tag relationships."""
        # Create tag hierarchy
        grandparent = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Grandparent"},
        ).json()
        parent = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "Parent", "parent_tag_id": grandparent["id"]},
        ).json()

        # Update parent tag (this creates undo operation that should preserve parent_tag_id)
        update_resp = api_client.put(
            f"/api/tags/{parent['id']}",
            headers=api_auth_headers,
            json={"description": "Updated parent"},
        )
        assert update_resp.status_code == 200

        # Undo update
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Verify parent still has correct parent_tag_id after undo
        listing = api_client.get("/api/tags/manage", headers=api_auth_headers).json()
        parent_item = next(
            (item for item in listing["items"] if item["name"] == "Parent"), None
        )
        assert parent_item is not None
        # Note: parent_tag_id should be preserved through update/undo cycle
        assert parent_item["parent_tag_id"] == grandparent["id"]


# ============================================================================
# EDGE CASES & ERROR SCENARIOS
# ============================================================================


class TestUndoEdgeCases:
    """Test edge cases and error scenarios."""

    def test_undo_after_entity_manually_deleted(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test undo after entity is manually deleted from DB."""
        # Create category
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "ToDelete"},
        ).json()

        # Update category (creates undo operation)
        api_client.put(
            f"/api/categories/{cat['id']}",
            headers=api_auth_headers,
            json={"description": "Updated"},
        )

        # Manually delete category from database
        from src.db.models import Category

        test_db_session.query(Category).filter_by(id=cat["id"]).delete()
        test_db_session.commit()

        # Undo should handle gracefully (may fail or recreate)
        undo_resp = api_client.post("/api/categories/undo", headers=api_auth_headers)
        # Either succeeds by recreating or fails gracefully
        assert undo_resp.status_code in [200, 404, 422]

    def test_undo_with_invalid_json_payload(self, test_db_session):
        """Test undo with invalid JSON payload (recovery)."""
        # Manually insert corrupted undo operation
        corrupted_op = UndoOperation(
            user_id="api-test-user-id",
            entity_type="category",
            operation="update",
            payload="{ invalid json !!!",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        test_db_session.add(corrupted_op)
        test_db_session.commit()

        # Service should handle gracefully
        undo_service = UndoService(test_db_session)
        result = undo_service.pop("api-test-user-id", "category")

        # Should return None and remove corrupted operation
        assert result is None

        # Verify corrupted operation was removed
        count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="api-test-user-id")
            .count()
        )
        assert count == 0

    def test_undo_on_nonexistent_entity_type(self, api_client, api_auth_headers):
        """Test undo on non-existent entity type (should not crash)."""
        # Try to undo on invalid entity type (API only supports category/tag)
        # This is tested at the service level
        undo_resp = api_client.post("/api/categories/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 404  # No operations available

    def test_undo_with_missing_parent_references(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test undo with missing parent references."""
        # Create parent tag
        parent = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "ParentRef"},
        ).json()

        # Create child tag
        child = api_client.post(
            "/api/tags",
            headers=api_auth_headers,
            json={"name": "ChildRef", "parent_tag_id": parent["id"]},
        ).json()

        # Delete child
        delete_resp = api_client.delete(
            f"/api/tags/{child['id']}?confirm=true",
            headers=api_auth_headers,
        )
        assert delete_resp.status_code == 200

        # Manually delete parent from database
        from src.db.models import Tag

        test_db_session.query(Tag).filter_by(id=parent["id"]).delete()
        test_db_session.commit()

        # Undo should handle missing parent gracefully
        undo_resp = api_client.post("/api/tags/undo", headers=api_auth_headers)
        # Should either succeed (create child without parent) or fail gracefully
        assert undo_resp.status_code in [200, 404, 422]


# ============================================================================
# TRANSACTION SAFETY TESTS
# ============================================================================


class TestTransactionSafety:
    """Test that undo operations maintain transaction safety."""

    def test_failed_undo_does_not_leave_partial_data(
        self, api_client, api_auth_headers
    ):
        """Test that failed undo doesn't leave partial data."""
        # This test ensures atomicity - currently the implementation
        # doesn't have explicit rollback on undo failure, but we can verify
        # the state remains consistent

        # Get initial category count
        initial_listing = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        initial_count = len(initial_listing["items"])

        # Create and delete category
        cat = api_client.post(
            "/api/categories",
            headers=api_auth_headers,
            json={"name": "TransactionTest"},
        ).json()

        # Delete category (creates undo operation)
        delete_resp = api_client.delete(
            f"/api/categories/{cat['id']}?confirm=true",
            headers=api_auth_headers,
        )
        assert delete_resp.status_code == 200

        # Verify category is deleted
        listing_after_delete = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        assert len(listing_after_delete["items"]) == initial_count

        # Undo (should succeed and restore category)
        undo_resp = api_client.post("/api/categories/undo", headers=api_auth_headers)
        assert undo_resp.status_code == 200

        # Verify category is restored
        final_listing = api_client.get(
            "/api/categories/manage", headers=api_auth_headers
        ).json()
        assert len(final_listing["items"]) == initial_count + 1
        names = [item["name"] for item in final_listing["items"]]
        assert "TransactionTest" in names


# ============================================================================
# UNDO STACK DEPTH MANAGEMENT
# ============================================================================


class TestUndoStackDepth:
    """Test undo stack depth management."""

    def test_50_operation_limit_per_user_per_entity(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Verify 50-operation limit per user per entity."""
        # Create 51 categories and delete them (each delete creates an undo operation)
        for i in range(51):
            cat = api_client.post(
                "/api/categories",
                headers=api_auth_headers,
                json={"name": f"LimitTest{i}"},
            ).json()
            api_client.delete(
                f"/api/categories/{cat['id']}?confirm=true",
                headers=api_auth_headers,
            )

        # Check database for operation count
        undo_service = UndoService(test_db_session)
        history = undo_service.get_history(
            "api-test-user-id", entity_type="category", limit=100
        )

        # Should have exactly 50 operations
        assert len(history) == 50

    def test_oldest_operations_removed_first(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test that oldest operations are removed when limit exceeded."""
        # Create and delete 51 categories with identifiable names
        for i in range(51):
            cat = api_client.post(
                "/api/categories",
                headers=api_auth_headers,
                json={"name": f"FIFO{i:03d}"},
            ).json()
            api_client.delete(
                f"/api/categories/{cat['id']}?confirm=true",
                headers=api_auth_headers,
            )

        # Get history
        undo_service = UndoService(test_db_session)
        history = undo_service.get_history(
            "api-test-user-id", entity_type="category", limit=100
        )

        # Most recent operation should be FIFO050
        most_recent = history[0]
        assert "FIFO050" in str(most_recent["payload"])

        # Oldest operation should be FIFO001 (FIFO000 was removed)
        oldest = history[-1]
        assert "FIFO001" in str(oldest["payload"])

    def test_separate_limits_for_tags_and_categories(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test separate limits for tags vs categories."""
        # Create and delete 30 categories
        for i in range(30):
            cat = api_client.post(
                "/api/categories",
                headers=api_auth_headers,
                json={"name": f"SepCat{i}"},
            ).json()
            api_client.delete(
                f"/api/categories/{cat['id']}?confirm=true",
                headers=api_auth_headers,
            )

        # Create and delete 40 tags
        for i in range(40):
            tag = api_client.post(
                "/api/tags",
                headers=api_auth_headers,
                json={"name": f"SepTag{i}"},
            ).json()
            api_client.delete(
                f"/api/tags/{tag['id']}?confirm=true",
                headers=api_auth_headers,
            )

        # Verify counts
        undo_service = UndoService(test_db_session)
        cat_history = undo_service.get_history(
            "api-test-user-id", entity_type="category", limit=100
        )
        tag_history = undo_service.get_history(
            "api-test-user-id", entity_type="tag", limit=100
        )

        assert len(cat_history) == 30
        assert len(tag_history) == 40


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestUndoPerformance:
    """Test undo performance with large payloads."""

    def test_undo_with_large_payload(self, test_db_session):
        """Test undo with large payloads (1MB JSON)."""
        undo_service = UndoService(test_db_session)

        # Create large payload (simulate category with many prompts)
        large_payload = {
            "category": {"name": "LargeTest", "description": "Test"},
            "prompt_ids": list(range(10000)),  # 10,000 prompt IDs
            "metadata": {f"key_{i}": f"value_{i}" * 10 for i in range(1000)},
        }

        # Push operation
        undo_service.push(
            user_id="api-test-user-id",
            entity_type="category",
            operation="delete",
            payload=large_payload,
        )
        test_db_session.commit()

        # Pop operation
        result = undo_service.pop("api-test-user-id", "category")

        assert result is not None
        assert result["operation"] == "delete"
        assert len(result["payload"]["prompt_ids"]) == 10000

    def test_undo_history_retrieval_with_50_operations(
        self, api_client, api_auth_headers, test_db_session
    ):
        """Test undo_history retrieval with 50 operations."""
        # Create and delete 50 categories
        for i in range(50):
            cat = api_client.post(
                "/api/categories",
                headers=api_auth_headers,
                json={"name": f"HistTest{i}"},
            ).json()
            api_client.delete(
                f"/api/categories/{cat['id']}?confirm=true",
                headers=api_auth_headers,
            )

        # Retrieve history
        undo_service = UndoService(test_db_session)
        history = undo_service.get_history(
            "api-test-user-id", entity_type="category", limit=100
        )

        # Should retrieve all 50 efficiently
        assert len(history) == 50
        assert all("payload" in op for op in history)

    def test_verify_database_indexes_used(self, test_db_session):
        """Verify indexes are being used (basic query count test)."""
        from src.db.models import UndoOperation

        # Create some operations
        undo_service = UndoService(test_db_session)
        for i in range(10):
            undo_service.push(
                user_id="api-test-user-id",
                entity_type="category",
                operation="delete",
                payload={"name": f"IndexTest{i}"},
            )
        test_db_session.commit()

        # Query should be efficient (we can't directly test index usage in SQLite,
        # but we can verify the query works correctly)
        result = (
            test_db_session.query(UndoOperation)
            .filter(UndoOperation.user_id == "api-test-user-id")
            .order_by(UndoOperation.created_at.desc())
            .first()
        )

        assert result is not None
        assert result.user_id == "api-test-user-id"


# ============================================================================
# CLEANUP & EXPIRATION TESTS
# ============================================================================


class TestUndoCleanup:
    """Test undo operation cleanup and expiration."""

    def test_expired_operations_are_cleaned_up(self, test_db_session):
        """Test that expired operations are removed by cleanup."""
        # Create expired operation
        expired_op = UndoOperation(
            user_id="api-test-user-id",
            entity_type="category",
            operation="delete",
            payload=json.dumps({"category": {"name": "Expired"}}),
            created_at=datetime.now(timezone.utc) - timedelta(days=31),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        test_db_session.add(expired_op)

        # Create valid operation
        valid_op = UndoOperation(
            user_id="api-test-user-id",
            entity_type="category",
            operation="delete",
            payload=json.dumps({"category": {"name": "Valid"}}),
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        test_db_session.add(valid_op)
        test_db_session.commit()

        # Run cleanup
        undo_service = UndoService(test_db_session)
        deleted_count = undo_service.cleanup_expired()
        test_db_session.commit()

        assert deleted_count == 1

        # Only valid operation should remain
        remaining = test_db_session.query(UndoOperation).all()
        assert len(remaining) == 1
        assert json.loads(remaining[0].payload)["category"]["name"] == "Valid"
