# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Comprehensive tests for UndoService.

This test suite verifies:
1. Service instantiation & imports
2. Service methods (push, pop, get_history, clear_user_undo, cleanup_expired)
3. User-scoping (User A cannot access User B's operations)
4. Database persistence (operations survive service restart)
5. 50-operation limit enforcement
6. Expiration cleanup
7. JSON payload handling
"""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from src.db.models.undo_operation import UndoOperation
from src.services.undo_service import UndoService
from src.web.dependencies.undo import get_undo_service


class TestUndoServiceImports:
    """Test that UndoService imports correctly."""

    def test_import_undo_service(self):
        """Verify UndoService can be imported."""
        from src.services.undo_service import UndoService

        assert UndoService is not None

    def test_import_get_undo_service_dependency(self):
        """Verify get_undo_service can be imported from dependencies."""
        from src.web.dependencies import get_undo_service

        assert get_undo_service is not None

    def test_import_undo_operation_model(self):
        """Verify UndoOperation model can be imported."""
        from src.db.models.undo_operation import UndoOperation

        assert UndoOperation is not None


class TestUndoServiceInstantiation:
    """Test UndoService initialization."""

    def test_create_service(self, test_db_session: Session):
        """Test creating UndoService with default parameters."""
        service = UndoService(test_db_session)
        assert service is not None
        assert service.db == test_db_session
        assert service.max_operations_per_entity == 50
        assert service.expiration_days == 30

    def test_create_service_custom_params(self, test_db_session: Session):
        """Test creating UndoService with custom parameters."""
        service = UndoService(
            test_db_session, max_operations_per_entity=100, expiration_days=60
        )
        assert service.max_operations_per_entity == 100
        assert service.expiration_days == 60

    def test_get_undo_service_dependency(self, test_db_session: Session):
        """Test get_undo_service dependency function."""
        service = get_undo_service(db=test_db_session)
        assert isinstance(service, UndoService)
        assert service.db == test_db_session


class TestUndoServiceBasicOperations:
    """Test basic push/pop operations."""

    def test_push_operation(self, test_db_session: Session):
        """Test pushing an undo operation."""
        service = UndoService(test_db_session)

        payload = {"id": 1, "before": {"name": "Old Name", "color": "#FF0000"}}

        service.push(
            user_id="user-123",
            entity_type="category",
            operation="update",
            payload=payload,
        )
        test_db_session.commit()

        # Verify operation is in database
        op = test_db_session.query(UndoOperation).filter_by(user_id="user-123").first()
        assert op is not None
        assert op.entity_type == "category"
        assert op.operation == "update"
        assert json.loads(op.payload) == payload

    def test_pop_operation(self, test_db_session: Session):
        """Test popping the most recent undo operation."""
        service = UndoService(test_db_session)

        payload = {"id": 2, "before": {"name": "Category Name"}}

        service.push(
            user_id="user-456",
            entity_type="category",
            operation="delete",
            payload=payload,
        )
        test_db_session.commit()

        # Pop the operation
        result = service.pop(user_id="user-456", entity_type="category")
        test_db_session.commit()

        assert result is not None
        assert result["entity_type"] == "category"
        assert result["operation"] == "delete"
        assert result["payload"] == payload

        # Verify operation is removed from database
        count = (
            test_db_session.query(UndoOperation).filter_by(user_id="user-456").count()
        )
        assert count == 0

    def test_pop_returns_most_recent(self, test_db_session: Session):
        """Test that pop returns the most recent operation (LIFO)."""
        service = UndoService(test_db_session)

        # Push three operations
        service.push("user-789", "tag", "create", {"id": 1, "name": "Tag 1"})
        test_db_session.flush()

        service.push("user-789", "tag", "update", {"id": 2, "name": "Tag 2"})
        test_db_session.flush()

        service.push("user-789", "tag", "delete", {"id": 3, "name": "Tag 3"})
        test_db_session.commit()

        # Pop should return the last one pushed (delete)
        result = service.pop("user-789", "tag")
        assert result["operation"] == "delete"
        assert result["payload"]["id"] == 3

    def test_pop_empty_returns_none(self, test_db_session: Session):
        """Test that pop returns None when no operations exist."""
        service = UndoService(test_db_session)
        result = service.pop(user_id="nonexistent-user", entity_type="category")
        assert result is None


class TestUndoServiceUserScoping:
    """Test that operations are properly scoped to users."""

    def test_users_cannot_access_each_others_operations(self, test_db_session: Session):
        """Verify User A cannot access User B's undo operations."""
        service = UndoService(test_db_session)

        # User A pushes operations
        service.push("user-a", "category", "create", {"id": 1, "name": "A's Category"})
        service.push("user-a", "tag", "update", {"id": 2, "name": "A's Tag"})

        # User B pushes operations
        service.push("user-b", "category", "delete", {"id": 3, "name": "B's Category"})
        service.push("user-b", "tag", "create", {"id": 4, "name": "B's Tag"})

        test_db_session.commit()

        # User A pops - should only get their operations
        a_category_op = service.pop("user-a", "category")
        assert a_category_op is not None
        assert a_category_op["payload"]["name"] == "A's Category"

        a_tag_op = service.pop("user-a", "tag")
        assert a_tag_op is not None
        assert a_tag_op["payload"]["name"] == "A's Tag"

        # User B pops - should only get their operations
        b_category_op = service.pop("user-b", "category")
        assert b_category_op is not None
        assert b_category_op["payload"]["name"] == "B's Category"

        b_tag_op = service.pop("user-b", "tag")
        assert b_tag_op is not None
        assert b_tag_op["payload"]["name"] == "B's Tag"

        # No more operations for either user
        assert service.pop("user-a", "category") is None
        assert service.pop("user-b", "tag") is None

    def test_get_history_filtered_by_user(self, test_db_session: Session):
        """Test that get_history only returns operations for the specified user."""
        service = UndoService(test_db_session)

        # Create operations for two users
        service.push("user-x", "category", "create", {"id": 1})
        service.push("user-x", "category", "update", {"id": 2})
        service.push("user-y", "category", "delete", {"id": 3})
        test_db_session.commit()

        # Get history for user-x
        history_x = service.get_history("user-x")
        assert len(history_x) == 2
        assert all(op["entity_type"] == "category" for op in history_x)

        # Get history for user-y
        history_y = service.get_history("user-y")
        assert len(history_y) == 1
        assert history_y[0]["operation"] == "delete"


class TestUndoServicePersistence:
    """Test that operations persist in the database."""

    def test_operations_persist_across_service_instances(
        self, test_db_session: Session
    ):
        """Test that operations survive service restart."""
        # Create first service and push operation
        service1 = UndoService(test_db_session)
        payload = {"id": 100, "name": "Persistent Data"}
        service1.push("user-persist", "category", "update", payload)
        test_db_session.commit()

        # Create new service instance (simulating restart)
        service2 = UndoService(test_db_session)

        # Pop from new service - should retrieve the same operation
        result = service2.pop("user-persist", "category")
        assert result is not None
        assert result["payload"] == payload

    def test_database_contains_correct_user_ids(self, test_db_session: Session):
        """Test that undo_operations table has correct user_id values."""
        service = UndoService(test_db_session)

        service.push("user-db-1", "tag", "create", {"id": 1})
        service.push("user-db-2", "category", "delete", {"id": 2})
        service.push("user-db-1", "tag", "update", {"id": 3})
        test_db_session.commit()

        # Query database directly
        ops_user1 = (
            test_db_session.query(UndoOperation).filter_by(user_id="user-db-1").all()
        )
        ops_user2 = (
            test_db_session.query(UndoOperation).filter_by(user_id="user-db-2").all()
        )

        assert len(ops_user1) == 2
        assert len(ops_user2) == 1
        assert all(op.user_id == "user-db-1" for op in ops_user1)
        assert all(op.user_id == "user-db-2" for op in ops_user2)


class TestUndoServiceOperationLimit:
    """Test the 50-operation limit per user per entity type."""

    def test_enforces_50_operation_limit(self, test_db_session: Session):
        """Test that only 50 operations are kept per user per entity type."""
        service = UndoService(test_db_session)

        # Push 51 operations for same user/entity_type
        for i in range(51):
            service.push(
                user_id="user-limit",
                entity_type="category",
                operation="update",
                payload={"id": i, "iteration": i},
            )
            test_db_session.flush()

        test_db_session.commit()

        # Count operations in database
        count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-limit", entity_type="category")
            .count()
        )

        assert count == 50, f"Expected 50 operations, found {count}"

    def test_oldest_operation_is_deleted(self, test_db_session: Session):
        """Test that the oldest operation is deleted when limit is exceeded."""
        service = UndoService(test_db_session)

        # Push 51 operations with unique identifiers
        for i in range(51):
            service.push(
                user_id="user-fifo",
                entity_type="tag",
                operation="create",
                payload={"iteration": i},
            )
            test_db_session.flush()

        test_db_session.commit()

        # Get all remaining operations
        ops = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-fifo", entity_type="tag")
            .order_by(UndoOperation.created_at.asc())
            .all()
        )

        # First operation should be iteration 1 (iteration 0 was deleted)
        first_payload = json.loads(ops[0].payload)
        assert first_payload["iteration"] == 1

        # Last operation should be iteration 50
        last_payload = json.loads(ops[-1].payload)
        assert last_payload["iteration"] == 50

    def test_limit_per_entity_type_separate(self, test_db_session: Session):
        """Test that limit is enforced separately per entity type."""
        service = UndoService(test_db_session)

        # Push 30 category operations
        for i in range(30):
            service.push("user-multi", "category", "update", {"id": i})

        # Push 40 tag operations
        for i in range(40):
            service.push("user-multi", "tag", "create", {"id": i})

        test_db_session.commit()

        # Both should be within limits and stored separately
        category_count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-multi", entity_type="category")
            .count()
        )

        tag_count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-multi", entity_type="tag")
            .count()
        )

        assert category_count == 30
        assert tag_count == 40


class TestUndoServiceExpiration:
    """Test expiration and cleanup functionality."""

    def test_expired_operations_are_removed(self, test_db_session: Session):
        """Test that cleanup_expired removes old operations."""
        service = UndoService(test_db_session, expiration_days=30)

        # Create operation with expired timestamp
        expired_time = datetime.now(UTC) - timedelta(days=31)
        op = UndoOperation(
            user_id="user-expired",
            entity_type="category",
            operation="update",
            payload=json.dumps({"id": 1}),
            created_at=expired_time,
            expires_at=expired_time + timedelta(days=30),
        )
        test_db_session.add(op)

        # Create operation with valid timestamp
        service.push("user-valid", "category", "create", {"id": 2})
        test_db_session.commit()

        # Run cleanup
        deleted_count = service.cleanup_expired()
        test_db_session.commit()

        assert deleted_count == 1

        # Expired operation should be gone
        assert (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-expired")
            .count()
            == 0
        )

        # Valid operation should remain
        assert (
            test_db_session.query(UndoOperation).filter_by(user_id="user-valid").count()
            == 1
        )

    def test_cleanup_expired_returns_count(self, test_db_session: Session):
        """Test that cleanup_expired returns correct count."""
        service = UndoService(test_db_session)

        # Create 5 expired operations
        expired_time = datetime.now(UTC) - timedelta(days=35)
        for i in range(5):
            op = UndoOperation(
                user_id=f"user-{i}",
                entity_type="tag",
                operation="delete",
                payload=json.dumps({"id": i}),
                created_at=expired_time,
                expires_at=expired_time + timedelta(days=30),
            )
            test_db_session.add(op)

        test_db_session.commit()

        deleted = service.cleanup_expired()
        assert deleted == 5

    def test_expiration_timestamp_set_correctly(self, test_db_session: Session):
        """Test that expires_at is set to created_at + expiration_days."""
        service = UndoService(test_db_session, expiration_days=45)

        datetime.now(UTC)
        service.push("user-expire-check", "category", "create", {"id": 1})
        test_db_session.commit()
        datetime.now(UTC)

        op = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-expire-check")
            .first()
        )

        # Check that expires_at is approximately created_at + 45 days
        expected_expires = op.created_at + timedelta(days=45)
        time_diff = abs((op.expires_at - expected_expires).total_seconds())

        assert time_diff < 2, "expires_at should be created_at + 45 days"


class TestUndoServiceGetHistory:
    """Test get_history method."""

    def test_get_history_returns_recent_operations(self, test_db_session: Session):
        """Test that get_history returns operations without deleting them."""
        service = UndoService(test_db_session)

        # Push 5 operations
        for i in range(5):
            service.push("user-history", "category", "update", {"id": i})
        test_db_session.commit()

        # Get history
        history = service.get_history("user-history")

        assert len(history) == 5

        # Operations should still be in database
        count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-history")
            .count()
        )
        assert count == 5

    def test_get_history_respects_limit(self, test_db_session: Session):
        """Test that get_history respects the limit parameter."""
        service = UndoService(test_db_session)

        # Push 20 operations
        for i in range(20):
            service.push("user-limit-history", "tag", "create", {"id": i})
        test_db_session.commit()

        # Get only 10 most recent
        history = service.get_history("user-limit-history", limit=10)

        assert len(history) == 10

    def test_get_history_orders_by_most_recent(self, test_db_session: Session):
        """Test that get_history returns operations in reverse chronological order."""
        service = UndoService(test_db_session)

        # Push operations with unique identifiers
        for i in range(3):
            service.push("user-order", "category", "update", {"iteration": i})
            test_db_session.flush()
        test_db_session.commit()

        history = service.get_history("user-order")

        # Most recent should be first
        assert history[0]["payload"]["iteration"] == 2
        assert history[1]["payload"]["iteration"] == 1
        assert history[2]["payload"]["iteration"] == 0

    def test_get_history_filters_by_entity_type(self, test_db_session: Session):
        """Test that get_history can filter by entity_type."""
        service = UndoService(test_db_session)

        service.push("user-filter", "category", "create", {"type": "category"})
        service.push("user-filter", "tag", "update", {"type": "tag"})
        service.push("user-filter", "category", "delete", {"type": "category"})
        test_db_session.commit()

        # Filter by category
        category_history = service.get_history("user-filter", entity_type="category")
        assert len(category_history) == 2
        assert all(op["entity_type"] == "category" for op in category_history)

        # Filter by tag
        tag_history = service.get_history("user-filter", entity_type="tag")
        assert len(tag_history) == 1
        assert tag_history[0]["entity_type"] == "tag"


class TestUndoServiceClearUserUndo:
    """Test clear_user_undo method."""

    def test_clear_user_undo_removes_all_operations(self, test_db_session: Session):
        """Test that clear_user_undo removes all operations for a user."""
        service = UndoService(test_db_session)

        # Create operations for user
        service.push("user-clear", "category", "create", {"id": 1})
        service.push("user-clear", "tag", "update", {"id": 2})
        service.push("user-clear", "category", "delete", {"id": 3})
        test_db_session.commit()

        # Clear all operations
        deleted = service.clear_user_undo("user-clear")
        test_db_session.commit()

        assert deleted == 3

        # Verify no operations remain
        count = (
            test_db_session.query(UndoOperation).filter_by(user_id="user-clear").count()
        )
        assert count == 0

    def test_clear_user_undo_doesnt_affect_other_users(self, test_db_session: Session):
        """Test that clearing one user's undo doesn't affect others."""
        service = UndoService(test_db_session)

        # Create operations for two users
        service.push("user-keep", "category", "create", {"id": 1})
        service.push("user-remove", "category", "update", {"id": 2})
        test_db_session.commit()

        # Clear user-remove
        service.clear_user_undo("user-remove")
        test_db_session.commit()

        # user-keep should still have their operation
        assert (
            test_db_session.query(UndoOperation).filter_by(user_id="user-keep").count()
            == 1
        )
        assert (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-remove")
            .count()
            == 0
        )

    def test_clear_user_undo_returns_zero_when_empty(self, test_db_session: Session):
        """Test that clear_user_undo returns 0 when no operations exist."""
        service = UndoService(test_db_session)
        deleted = service.clear_user_undo("nonexistent-user")
        assert deleted == 0


class TestUndoServiceJSONHandling:
    """Test JSON payload serialization and deserialization."""

    def test_complex_json_payload(self, test_db_session: Session):
        """Test that complex JSON payloads are stored and retrieved correctly."""
        service = UndoService(test_db_session)

        complex_payload = {
            "id": 42,
            "before": {
                "name": "Test Category",
                "description": "A description with special chars: <>&'\"",
                "color": "#FF5733",
                "metadata": {"nested": {"deeply": ["array", "of", "values"]}},
            },
            "prompt_ids": [1, 2, 3, 4, 5],
            "timestamp": "2024-01-30T12:00:00Z",
        }

        service.push("user-json", "category", "update", complex_payload)
        test_db_session.commit()

        result = service.pop("user-json", "category")

        assert result["payload"] == complex_payload

    def test_unicode_in_payload(self, test_db_session: Session):
        """Test that Unicode characters are handled correctly."""
        service = UndoService(test_db_session)

        unicode_payload = {
            "name": "Тест 测试 テスト 🎉",
            "description": "Unicode: émojis 🚀 中文 日本語",
        }

        service.push("user-unicode", "tag", "create", unicode_payload)
        test_db_session.commit()

        result = service.pop("user-unicode", "tag")
        assert result["payload"] == unicode_payload

    def test_non_serializable_payload_raises_error(self, test_db_session: Session):
        """Test that non-JSON-serializable payloads raise ValueError."""
        service = UndoService(test_db_session)

        # Create non-serializable object
        class NonSerializable:
            pass

        invalid_payload = {"object": NonSerializable()}

        with pytest.raises(ValueError, match="Payload must be JSON-serializable"):
            service.push("user-error", "category", "create", invalid_payload)

    def test_corrupted_json_is_handled(self, test_db_session: Session):
        """Test that corrupted JSON in database is handled gracefully."""
        service = UndoService(test_db_session)

        # Manually insert corrupted JSON into database
        corrupted_op = UndoOperation(
            user_id="user-corrupt",
            entity_type="category",
            operation="update",
            payload="{ invalid json !!!",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )
        test_db_session.add(corrupted_op)
        test_db_session.commit()

        # Pop should return None and delete corrupted operation
        result = service.pop("user-corrupt", "category")
        test_db_session.commit()

        assert result is None

        # Corrupted operation should be removed
        count = (
            test_db_session.query(UndoOperation)
            .filter_by(user_id="user-corrupt")
            .count()
        )
        assert count == 0


class TestUndoServiceEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_payload(self, test_db_session: Session):
        """Test that empty payload is handled correctly."""
        service = UndoService(test_db_session)

        empty_payload = {}
        service.push("user-empty", "category", "create", empty_payload)
        test_db_session.commit()

        result = service.pop("user-empty", "category")
        assert result["payload"] == empty_payload

    def test_very_large_payload(self, test_db_session: Session):
        """Test that large payloads are handled correctly."""
        service = UndoService(test_db_session)

        # Create a large payload (1000 prompt IDs)
        large_payload = {
            "prompt_ids": list(range(1000)),
            "metadata": {f"key_{i}": f"value_{i}" for i in range(100)},
        }

        service.push("user-large", "category", "delete", large_payload)
        test_db_session.commit()

        result = service.pop("user-large", "category")
        assert result["payload"] == large_payload

    def test_multiple_entity_types_same_user(self, test_db_session: Session):
        """Test that different entity types are tracked separately."""
        service = UndoService(test_db_session)

        service.push("user-multi-type", "category", "create", {"category_data": 1})
        service.push("user-multi-type", "tag", "update", {"tag_data": 2})
        test_db_session.commit()

        # Pop category
        cat_result = service.pop("user-multi-type", "category")
        assert cat_result["payload"]["category_data"] == 1

        # Pop tag
        tag_result = service.pop("user-multi-type", "tag")
        assert tag_result["payload"]["tag_data"] == 2

        # Both should now be empty
        assert service.pop("user-multi-type", "category") is None
        assert service.pop("user-multi-type", "tag") is None
