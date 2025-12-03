# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive integration tests for SessionRepository.

This module provides extensive test coverage for the SessionRepository class,
testing all database operations including:
- Session creation with all fields (user_id, family_id, JTI, metadata)
- Token family tracking and rotation
- Session revocation (individual and family-wide)
- Token reuse detection through family tracking
- Active session counting and retrieval
- Expired session cleanup
- Oldest session retrieval for session limit enforcement
- Edge cases and error handling

Target: 90%+ repository coverage
Uses in-memory SQLite for fast, isolated tests
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.db.repositories.session_repository import SessionRepository


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def session_repository(test_db_session: Session) -> SessionRepository:
    """Create a SessionRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        SessionRepository: Repository for session operations
    """
    return SessionRepository(test_db_session)


@pytest.fixture
def test_user(test_db_session: Session) -> User:
    """Create a test user for sessions.

    Returns:
        User: Test user with proper password hash
    """
    user = User(
        username="sessionuser",
        email="session@example.com",
        display_name="Session Test User",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$somehash",
        role="viewer",
        email_verified=False,
        is_active=True,
        failed_login_attempts=0
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture
def sample_session(
    test_db_session: Session,
    test_user: User
) -> UserSession:
    """Create a sample session for testing.

    Args:
        test_db_session: Database session
        test_user: Test user fixture

    Returns:
        UserSession: Test session with all fields populated
    """
    session = UserSession(
        user_id=test_user.id,
        family_id="family-abc-123",
        refresh_token_jti="jti-xyz-456",
        device_info="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        ip_address="192.168.1.100",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        is_revoked=False
    )
    test_db_session.add(session)
    test_db_session.flush()
    return session


@pytest.fixture
def multiple_sessions(
    test_db_session: Session,
    test_user: User
) -> list[UserSession]:
    """Create multiple sessions for testing.

    Creates 4 sessions with different states (each family is unique):
    - 3 active sessions in different families
    - 1 revoked session

    Args:
        test_db_session: Database session
        test_user: Test user fixture

    Returns:
        list[UserSession]: List of 4 sessions with various configurations
    """
    now = datetime.now(timezone.utc)
    sessions = [
        UserSession(
            user_id=test_user.id,
            family_id="family-1",
            refresh_token_jti="jti-1",
            device_info="Device 1",
            ip_address="192.168.1.1",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        ),
        UserSession(
            user_id=test_user.id,
            family_id="family-2",
            refresh_token_jti="jti-2",
            device_info="Device 2",
            ip_address="192.168.1.2",
            expires_at=now + timedelta(days=6),
            is_revoked=False
        ),
        UserSession(
            user_id=test_user.id,
            family_id="family-3",
            refresh_token_jti="jti-3",
            device_info="Device 3",
            ip_address="192.168.1.3",
            expires_at=now + timedelta(days=5),
            is_revoked=False
        ),
        UserSession(
            user_id=test_user.id,
            family_id="family-revoked",
            refresh_token_jti="jti-revoked",
            device_info="Device Revoked",
            ip_address="192.168.1.99",
            expires_at=now + timedelta(days=7),
            is_revoked=True
        ),
    ]
    test_db_session.add_all(sessions)
    test_db_session.flush()
    return sessions


# ============================================================================
# CREATE SESSION TESTS
# ============================================================================


class TestSessionCreation:
    """Tests for session creation operations."""

    def test_create_session_basic(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test basic session creation with required fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-test",
            refresh_token_jti="jti-test",
            expires_at=expires_at
        )

        assert session.id is not None
        assert session.user_id == test_user.id
        assert session.family_id == "family-test"
        assert session.refresh_token_jti == "jti-test"
        assert session.expires_at is not None

    def test_create_session_all_fields(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test session creation with all optional fields."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-full",
            refresh_token_jti="jti-full",
            expires_at=expires_at,
            device_info="Mozilla/5.0 (Macintosh; Intel Mac OS X)",
            ip_address="10.0.0.1"
        )

        assert session.user_id == test_user.id
        assert session.family_id == "family-full"
        assert session.refresh_token_jti == "jti-full"
        assert session.device_info == "Mozilla/5.0 (Macintosh; Intel Mac OS X)"
        assert session.ip_address == "10.0.0.1"
        assert session.expires_at is not None

    def test_create_session_default_values(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test that default values are applied correctly."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-defaults",
            refresh_token_jti="jti-defaults",
            expires_at=expires_at
        )

        # Check defaults from model
        assert session.is_revoked is False
        assert session.device_info is None
        assert session.ip_address is None

    def test_create_session_timestamps(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test that timestamps are automatically set."""
        before_create = datetime.now(timezone.utc)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-time",
            refresh_token_jti="jti-time",
            expires_at=expires_at
        )

        after_create = datetime.now(timezone.utc)

        assert session.created_at is not None
        assert session.last_used_at is not None

        # Handle timezone-naive timestamps from SQLite
        created_with_tz = session.created_at.replace(tzinfo=timezone.utc) if session.created_at.tzinfo is None else session.created_at
        last_used_with_tz = session.last_used_at.replace(tzinfo=timezone.utc) if session.last_used_at.tzinfo is None else session.last_used_at

        # Allow 2 second tolerance for timestamp comparison
        assert abs((created_with_tz - before_create).total_seconds()) < 2
        assert abs((last_used_with_tz - before_create).total_seconds()) < 2

    def test_create_session_generates_uuid(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test that session ID is automatically generated as UUID."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session1 = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-uuid-1",
            refresh_token_jti="jti-uuid-1",
            expires_at=expires_at
        )
        session2 = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-uuid-2",
            refresh_token_jti="jti-uuid-2",
            expires_at=expires_at
        )

        assert session1.id != session2.id
        assert len(session1.id) == 36  # UUID format
        assert len(session2.id) == 36

    def test_create_session_stores_ipv4(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test storing IPv4 address."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-ipv4",
            refresh_token_jti="jti-ipv4",
            expires_at=expires_at,
            ip_address="192.168.0.1"
        )

        assert session.ip_address == "192.168.0.1"

    def test_create_session_stores_ipv6(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test storing IPv6 address."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-ipv6",
            refresh_token_jti="jti-ipv6",
            expires_at=expires_at,
            ip_address="2001:0db8:85a3:0000:0000:8a2e:0370:7334"
        )

        assert session.ip_address == "2001:0db8:85a3:0000:0000:8a2e:0370:7334"


# ============================================================================
# RETRIEVE SESSION TESTS
# ============================================================================


class TestSessionRetrieval:
    """Tests for session retrieval operations."""

    def test_get_by_family_id(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test retrieving session by family_id."""
        retrieved = session_repository.get_by_family_id(sample_session.family_id)

        assert retrieved is not None
        assert retrieved.id == sample_session.id
        assert retrieved.family_id == sample_session.family_id

    def test_get_by_family_id_not_found(
        self,
        session_repository: SessionRepository
    ):
        """Test that non-existent family_id returns None."""
        result = session_repository.get_by_family_id("non-existent-family")
        assert result is None

    def test_get_by_family_id_unique_constraint(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession]
    ):
        """Test get_by_family_id with unique family_id constraint."""
        # Each family_id is unique, so get_by_family_id should return exactly one session
        result = session_repository.get_by_family_id("family-1")
        assert result is not None
        assert result.family_id == "family-1"
        assert result.refresh_token_jti == "jti-1"

    def test_get_by_jti(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test retrieving session by refresh token JTI."""
        retrieved = session_repository.get_by_jti(sample_session.refresh_token_jti)

        assert retrieved is not None
        assert retrieved.id == sample_session.id
        assert retrieved.refresh_token_jti == sample_session.refresh_token_jti

    def test_get_by_jti_not_found(
        self,
        session_repository: SessionRepository
    ):
        """Test that non-existent JTI returns None."""
        result = session_repository.get_by_jti("non-existent-jti")
        assert result is None

    def test_get_by_jti_with_revoked_session(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession]
    ):
        """Test retrieving revoked session by JTI still works."""
        # Last session is revoked
        revoked_session = multiple_sessions[-1]
        assert revoked_session.is_revoked is True

        retrieved = session_repository.get_by_jti(revoked_session.refresh_token_jti)
        assert retrieved is not None
        assert retrieved.is_revoked is True


# ============================================================================
# GET USER SESSIONS TESTS
# ============================================================================


class TestGetUserSessions:
    """Tests for retrieving user sessions."""

    def test_get_user_sessions_all(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test retrieving all sessions for a user (active_only=False)."""
        sessions = session_repository.get_user_sessions(
            test_user.id,
            active_only=False
        )

        assert len(sessions) == 4  # All sessions including revoked

    def test_get_user_sessions_active_only(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test retrieving only active sessions (active_only=True)."""
        sessions = session_repository.get_user_sessions(
            test_user.id,
            active_only=True
        )

        assert len(sessions) == 3  # 3 active sessions
        assert all(not s.is_revoked for s in sessions)

    def test_get_user_sessions_empty(
        self,
        session_repository: SessionRepository
    ):
        """Test retrieving sessions for user with no sessions."""
        sessions = session_repository.get_user_sessions(
            "non-existent-user",
            active_only=True
        )

        assert sessions == []

    def test_get_user_sessions_default_active_only(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test that active_only defaults to True."""
        sessions = session_repository.get_user_sessions(test_user.id)

        assert len(sessions) == 3  # Only active sessions
        assert all(not s.is_revoked for s in sessions)


# ============================================================================
# COUNT USER SESSIONS TESTS
# ============================================================================


class TestCountUserSessions:
    """Tests for counting user sessions."""

    def test_count_user_sessions_all(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test counting all sessions including revoked."""
        count = session_repository.count_user_sessions(
            test_user.id,
            active_only=False
        )

        assert count == 4

    def test_count_user_sessions_active_only(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test counting only active sessions."""
        count = session_repository.count_user_sessions(
            test_user.id,
            active_only=True
        )

        assert count == 3

    def test_count_user_sessions_zero(
        self,
        session_repository: SessionRepository
    ):
        """Test counting sessions for user with no sessions."""
        count = session_repository.count_user_sessions(
            "non-existent-user",
            active_only=True
        )

        assert count == 0

    def test_count_user_sessions_default_active_only(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test that active_only defaults to True for count."""
        count = session_repository.count_user_sessions(test_user.id)

        assert count == 3  # Only active sessions


# ============================================================================
# TOKEN ROTATION TESTS
# ============================================================================


class TestTokenRotation:
    """Tests for token rotation (update_session_token)."""

    def test_update_session_token_success(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test successful token rotation updates JTI and last_used_at."""
        old_jti = sample_session.refresh_token_jti
        old_last_used = sample_session.last_used_at

        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)

        updated = session_repository.update_session_token(
            sample_session.family_id,
            "new-jti-123"
        )

        assert updated is not None
        assert updated.refresh_token_jti == "new-jti-123"
        assert updated.refresh_token_jti != old_jti

        # last_used_at should be updated
        assert updated.last_used_at is not None
        # SQLite might not have microsecond precision, so check it's >= old value
        if old_last_used is not None:
            old_with_tz = old_last_used.replace(tzinfo=timezone.utc) if old_last_used.tzinfo is None else old_last_used
            new_with_tz = updated.last_used_at.replace(tzinfo=timezone.utc) if updated.last_used_at.tzinfo is None else updated.last_used_at
            assert new_with_tz >= old_with_tz

    def test_update_session_token_not_found(
        self,
        session_repository: SessionRepository
    ):
        """Test token rotation on non-existent family_id returns None."""
        result = session_repository.update_session_token(
            "non-existent-family",
            "new-jti"
        )

        assert result is None

    def test_update_session_token_updates_last_used_at(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test that update_session_token updates last_used_at timestamp."""
        before_update = datetime.now(timezone.utc)

        updated = session_repository.update_session_token(
            sample_session.family_id,
            "rotated-jti"
        )

        after_update = datetime.now(timezone.utc)

        assert updated is not None
        assert updated.last_used_at is not None

        last_used_with_tz = updated.last_used_at.replace(tzinfo=timezone.utc) if updated.last_used_at.tzinfo is None else updated.last_used_at

        # Check timestamp is within expected range (allow 2s tolerance)
        assert abs((last_used_with_tz - before_update).total_seconds()) < 2


# ============================================================================
# REVOKE SESSION TESTS
# ============================================================================


class TestRevokeSession:
    """Tests for session revocation."""

    def test_revoke_session_success(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test successful session revocation."""
        assert sample_session.is_revoked is False

        result = session_repository.revoke_session(sample_session.family_id)

        assert result is True
        assert sample_session.is_revoked is True

    def test_revoke_session_not_found(
        self,
        session_repository: SessionRepository
    ):
        """Test revoking non-existent session returns False."""
        result = session_repository.revoke_session("non-existent-family")
        assert result is False

    def test_revoke_session_idempotent(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test that revoking an already revoked session is idempotent."""
        # Revoke first time
        result1 = session_repository.revoke_session(sample_session.family_id)
        assert result1 is True
        assert sample_session.is_revoked is True

        # Revoke again
        result2 = session_repository.revoke_session(sample_session.family_id)
        assert result2 is True  # Should still return True
        assert sample_session.is_revoked is True


# ============================================================================
# REVOKE ALL USER SESSIONS TESTS
# ============================================================================


class TestRevokeAllUserSessions:
    """Tests for revoking all user sessions."""

    def test_revoke_all_user_sessions(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession],
        test_db_session: Session
    ):
        """Test revoking all active sessions for a user."""
        count = session_repository.revoke_all_user_sessions(test_user.id)

        assert count == 3  # 3 active sessions revoked

        # Expire in-memory objects and re-query from database
        test_db_session.expire_all()

        # Verify all sessions are now revoked
        sessions = session_repository.get_user_sessions(
            test_user.id,
            active_only=False
        )
        assert all(s.is_revoked for s in sessions)

    def test_revoke_all_user_sessions_no_sessions(
        self,
        session_repository: SessionRepository
    ):
        """Test revoking sessions for user with no sessions."""
        count = session_repository.revoke_all_user_sessions("non-existent-user")
        assert count == 0

    def test_revoke_all_user_sessions_already_revoked(
        self,
        session_repository: SessionRepository,
        test_user: User,
        multiple_sessions: list[UserSession]
    ):
        """Test revoking when all sessions already revoked."""
        # Revoke all first time
        count1 = session_repository.revoke_all_user_sessions(test_user.id)
        assert count1 == 3

        # Try revoking again
        count2 = session_repository.revoke_all_user_sessions(test_user.id)
        assert count2 == 0  # No active sessions to revoke


# ============================================================================
# REVOKE TOKEN FAMILY TESTS
# ============================================================================


class TestRevokeTokenFamily:
    """Tests for revoking entire token family (for reuse detection)."""

    def test_revoke_token_family(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession],
        test_db_session: Session
    ):
        """Test revoking a token family (one session per family due to UNIQUE constraint)."""
        # Each family_id is unique, so family-1 has exactly 1 session
        count = session_repository.revoke_token_family("family-1")

        assert count == 1

        # Expire in-memory objects and re-query from database
        test_db_session.expire_all()

        # Verify the session in family is revoked
        session1 = session_repository.get_by_jti("jti-1")
        assert session1.is_revoked is True

    def test_revoke_token_family_not_found(
        self,
        session_repository: SessionRepository
    ):
        """Test revoking non-existent family returns 0."""
        count = session_repository.revoke_token_family("non-existent-family")
        assert count == 0

    def test_revoke_token_family_another_family(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession],
        test_db_session: Session
    ):
        """Test revoking another family."""
        count = session_repository.revoke_token_family("family-2")

        assert count == 1

        # Expire in-memory objects and re-query from database
        test_db_session.expire_all()

        session = session_repository.get_by_jti("jti-2")
        assert session.is_revoked is True

    def test_revoke_token_family_already_revoked(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession]
    ):
        """Test revoking already revoked family."""
        count = session_repository.revoke_token_family("family-revoked")
        assert count == 0  # Already revoked

    def test_revoke_token_family_idempotent(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession]
    ):
        """Test that family revocation is idempotent."""
        # Revoke first time
        count1 = session_repository.revoke_token_family("family-1")
        assert count1 == 1

        # Revoke again
        count2 = session_repository.revoke_token_family("family-1")
        assert count2 == 0  # No active sessions to revoke


# ============================================================================
# EXPIRED SESSION TESTS
# ============================================================================


class TestExpiredSessions:
    """Tests for expired session handling and cleanup."""

    def test_get_expired_sessions(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test retrieving expired sessions."""
        now = datetime.now(timezone.utc)

        # Create expired sessions
        expired1 = UserSession(
            user_id=test_user.id,
            family_id="family-exp-1",
            refresh_token_jti="jti-exp-1",
            expires_at=now - timedelta(days=1),
            is_revoked=False
        )
        expired2 = UserSession(
            user_id=test_user.id,
            family_id="family-exp-2",
            refresh_token_jti="jti-exp-2",
            expires_at=now - timedelta(hours=1),
            is_revoked=False
        )
        # Create active session
        active = UserSession(
            user_id=test_user.id,
            family_id="family-active",
            refresh_token_jti="jti-active",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        )
        test_db_session.add_all([expired1, expired2, active])
        test_db_session.flush()

        expired_sessions = session_repository.get_expired_sessions()

        assert len(expired_sessions) >= 2
        expired_jtis = [s.refresh_token_jti for s in expired_sessions]
        assert "jti-exp-1" in expired_jtis
        assert "jti-exp-2" in expired_jtis

    def test_get_expired_sessions_with_limit(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test retrieving expired sessions with limit."""
        now = datetime.now(timezone.utc)

        # Create multiple expired sessions
        for i in range(5):
            session = UserSession(
                user_id=test_user.id,
                family_id=f"family-exp-{i}",
                refresh_token_jti=f"jti-exp-{i}",
                expires_at=now - timedelta(days=i+1),
                is_revoked=False
            )
            test_db_session.add(session)
        test_db_session.flush()

        expired_sessions = session_repository.get_expired_sessions(limit=3)

        assert len(expired_sessions) == 3

    def test_cleanup_expired_sessions(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test cleanup_expired_sessions (alias for delete_expired_sessions)."""
        now = datetime.now(timezone.utc)

        # Create expired and active sessions
        expired = UserSession(
            user_id=test_user.id,
            family_id="family-cleanup",
            refresh_token_jti="jti-cleanup",
            expires_at=now - timedelta(days=1),
            is_revoked=False
        )
        active = UserSession(
            user_id=test_user.id,
            family_id="family-keep",
            refresh_token_jti="jti-keep",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        )
        test_db_session.add_all([expired, active])
        test_db_session.flush()

        deleted_count = session_repository.cleanup_expired_sessions()

        assert deleted_count >= 1

        # Verify expired session is deleted
        result = session_repository.get_by_jti("jti-cleanup")
        assert result is None

        # Verify active session still exists
        result = session_repository.get_by_jti("jti-keep")
        assert result is not None

    def test_delete_expired_sessions(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test deleting all expired sessions."""
        now = datetime.now(timezone.utc)

        # Create multiple expired sessions
        for i in range(3):
            session = UserSession(
                user_id=test_user.id,
                family_id=f"family-del-{i}",
                refresh_token_jti=f"jti-del-{i}",
                expires_at=now - timedelta(days=i+1),
                is_revoked=False
            )
            test_db_session.add(session)
        test_db_session.flush()

        deleted_count = session_repository.delete_expired_sessions()

        assert deleted_count >= 3


# ============================================================================
# GET OLDEST SESSION TESTS
# ============================================================================


class TestGetOldestSession:
    """Tests for retrieving oldest active session."""

    def test_get_oldest_user_session(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test retrieving oldest active session by created_at."""
        now = datetime.now(timezone.utc)

        # Create sessions with different created_at times
        # Note: We can't directly set created_at (it's server_default)
        # So we create them sequentially
        session1 = UserSession(
            user_id=test_user.id,
            family_id="family-old-1",
            refresh_token_jti="jti-old-1",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        )
        test_db_session.add(session1)
        test_db_session.flush()

        # Small delay to ensure different timestamps
        import time
        time.sleep(0.01)

        session2 = UserSession(
            user_id=test_user.id,
            family_id="family-old-2",
            refresh_token_jti="jti-old-2",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        )
        test_db_session.add(session2)
        test_db_session.flush()

        oldest = session_repository.get_oldest_user_session(test_user.id)

        assert oldest is not None
        assert oldest.refresh_token_jti == "jti-old-1"

    def test_get_oldest_user_session_excludes_revoked(
        self,
        session_repository: SessionRepository,
        test_user: User,
        test_db_session: Session
    ):
        """Test that oldest session excludes revoked sessions."""
        now = datetime.now(timezone.utc)

        # Create oldest session but revoked
        revoked = UserSession(
            user_id=test_user.id,
            family_id="family-old-revoked",
            refresh_token_jti="jti-old-revoked",
            expires_at=now + timedelta(days=7),
            is_revoked=True
        )
        test_db_session.add(revoked)
        test_db_session.flush()

        # Small delay
        import time
        time.sleep(0.01)

        # Create newer but active session
        active = UserSession(
            user_id=test_user.id,
            family_id="family-old-active",
            refresh_token_jti="jti-old-active",
            expires_at=now + timedelta(days=7),
            is_revoked=False
        )
        test_db_session.add(active)
        test_db_session.flush()

        oldest = session_repository.get_oldest_user_session(test_user.id)

        assert oldest is not None
        assert oldest.refresh_token_jti == "jti-old-active"
        assert oldest.is_revoked is False

    def test_get_oldest_user_session_no_sessions(
        self,
        session_repository: SessionRepository
    ):
        """Test retrieving oldest session for user with no sessions."""
        result = session_repository.get_oldest_user_session("non-existent-user")
        assert result is None


# ============================================================================
# RELATIONSHIP LOADING TESTS
# ============================================================================


class TestRelationshipLoading:
    """Tests for relationship loading."""

    def test_session_user_relationship(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test loading user relationship from session."""
        # Access user relationship
        user = sample_session.user

        assert user is not None
        assert user.id == sample_session.user_id
        assert isinstance(user, User)


# ============================================================================
# EDGE CASES AND ERROR HANDLING TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_operations_on_non_existent_session(
        self,
        session_repository: SessionRepository
    ):
        """Test that operations on non-existent session handle gracefully."""
        fake_family = "non-existent-family"
        fake_jti = "non-existent-jti"

        # Should return None or 0, not raise exceptions
        assert session_repository.get_by_family_id(fake_family) is None
        assert session_repository.get_by_jti(fake_jti) is None
        assert session_repository.update_session_token(fake_family, "new-jti") is None
        assert session_repository.revoke_session(fake_family) is False
        assert session_repository.revoke_token_family(fake_family) == 0

    def test_count_method(
        self,
        session_repository: SessionRepository,
        multiple_sessions: list[UserSession]
    ):
        """Test count method from base repository."""
        count = session_repository.count()
        assert count >= len(multiple_sessions)

    def test_exists_method(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test exists method from base repository."""
        assert session_repository.exists(sample_session.id) is True
        assert session_repository.exists("non-existent-id") is False

    def test_get_by_id_from_base(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test get_by_id method inherited from base repository."""
        retrieved = session_repository.get_by_id(sample_session.id)

        assert retrieved is not None
        assert retrieved.id == sample_session.id

    def test_delete_session(
        self,
        session_repository: SessionRepository,
        sample_session: UserSession
    ):
        """Test deleting session using base repository delete method."""
        session_id = sample_session.id
        result = session_repository.delete(session_id)

        assert result is True
        assert session_repository.get_by_id(session_id) is None

    def test_long_device_info(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test creating session with maximum length device info."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        long_device_info = "a" * 500  # Max length from model

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-long",
            refresh_token_jti="jti-long",
            expires_at=expires_at,
            device_info=long_device_info
        )

        assert session.device_info == long_device_info

    def test_session_with_far_future_expiration(
        self,
        session_repository: SessionRepository,
        test_user: User
    ):
        """Test creating session with far future expiration."""
        far_future = datetime.now(timezone.utc) + timedelta(days=365)

        session = session_repository.create_session(
            user_id=test_user.id,
            family_id="family-future",
            refresh_token_jti="jti-future",
            expires_at=far_future
        )

        assert session.expires_at is not None
        expires_with_tz = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
        # Allow some tolerance for timestamp storage
        assert abs((expires_with_tz - far_future).total_seconds()) < 2

    def test_multiple_users_different_sessions(
        self,
        session_repository: SessionRepository,
        test_db_session: Session
    ):
        """Test that sessions are properly isolated between users."""
        # Create two users
        user1 = User(
            username="user1",
            email="user1@example.com",
            password_hash="hash1",
            role="viewer"
        )
        user2 = User(
            username="user2",
            email="user2@example.com",
            password_hash="hash2",
            role="viewer"
        )
        test_db_session.add_all([user1, user2])
        test_db_session.flush()

        # Create sessions for each user
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        session1 = session_repository.create_session(
            user_id=user1.id,
            family_id="family-user1",
            refresh_token_jti="jti-user1",
            expires_at=expires_at
        )
        session2 = session_repository.create_session(
            user_id=user2.id,
            family_id="family-user2",
            refresh_token_jti="jti-user2",
            expires_at=expires_at
        )

        # Verify isolation
        user1_sessions = session_repository.get_user_sessions(user1.id)
        user2_sessions = session_repository.get_user_sessions(user2.id)

        assert len(user1_sessions) == 1
        assert len(user2_sessions) == 1
        assert user1_sessions[0].user_id == user1.id
        assert user2_sessions[0].user_id == user2.id
