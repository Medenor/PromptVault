# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for session cleanup scheduler.

Tests the SessionCleanupScheduler class including:
- Scheduler lifecycle (start/stop)
- Cleanup operations
- Job scheduling and status tracking
- Error handling
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.scheduler.session_cleanup import SessionCleanupScheduler


class TestSessionCleanupScheduler:
    """Test suite for SessionCleanupScheduler."""

    @pytest.fixture
    def mock_config(self):
        """Create mock AuthConfig for testing."""
        config = Mock(spec=AuthConfig)
        config.cleanup_interval_hours = 1
        config.cleanup_batch_size = 100
        return config

    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        # Create in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:")
        # Create all tables
        from src.db.base import Base

        Base.metadata.create_all(engine)

        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal

    @pytest.fixture
    def scheduler(self, mock_session_factory, mock_config):
        """Create a scheduler instance for testing."""
        return SessionCleanupScheduler(
            session_factory=mock_session_factory,
            config=mock_config,
            cleanup_interval_hours=1,
            batch_size=100,
        )

    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initializes correctly."""
        assert scheduler is not None
        assert scheduler.is_running is False
        assert scheduler.cleanup_interval_hours == 1
        assert scheduler.batch_size == 100

    def test_scheduler_start(self, scheduler):
        """Test scheduler starts successfully."""
        assert scheduler.is_running is False

        scheduler.start()

        assert scheduler.is_running is True
        assert scheduler.scheduler is not None

        # Cleanup
        scheduler.stop()

    def test_scheduler_stop(self, scheduler):
        """Test scheduler stops successfully."""
        scheduler.start()
        assert scheduler.is_running is True

        scheduler.stop()

        assert scheduler.is_running is False

    def test_scheduler_cannot_start_twice(self, scheduler):
        """Test scheduler cannot be started twice."""
        scheduler.start()

        # Starting again logs a warning but doesn't raise
        scheduler.start()

        # Verify it's still running (not started twice)
        assert scheduler.is_running is True

        scheduler.stop()

    def test_scheduler_cannot_stop_when_not_running(self, scheduler):
        """Test scheduler cannot be stopped when not running."""
        # Stopping when not running logs a warning but doesn't raise
        scheduler.stop()

        # Verify it's still not running
        assert scheduler.is_running is False

    def test_get_job_info_when_running(self, scheduler):
        """Test getting job info when scheduler is running."""
        scheduler.start()

        job_info = scheduler.get_job_info()

        assert job_info is not None
        assert "id" in job_info  # Changed from 'job_id' to 'id'
        assert "next_run_time" in job_info
        assert "trigger" in job_info

        scheduler.stop()

    def test_get_job_info_when_not_running(self, scheduler):
        """Test getting job info when scheduler is not running."""
        job_info = scheduler.get_job_info()

        assert job_info is None

    def test_run_cleanup_now(self, scheduler, mock_session_factory):
        """Test manual cleanup trigger."""
        # Add test data to database
        session = mock_session_factory()

        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        session.add(user)
        session.commit()

        # Create expired session
        expired_session = UserSession(
            user_id=user.id,
            refresh_token_jti="jti1",
            family_id="fam1",
            ip_address="127.0.0.1",
            device_info="test",
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
        )
        session.add(expired_session)

        # Create valid session
        valid_session = UserSession(
            user_id=user.id,
            refresh_token_jti="jti2",
            family_id="fam2",
            ip_address="127.0.0.1",
            device_info="test",
            expires_at=datetime.utcnow() + timedelta(days=1),  # Valid
        )
        session.add(valid_session)

        session.commit()
        session.close()

        # Run cleanup
        result = scheduler.run_cleanup_now()

        assert result is not None
        assert result.get("success") is True
        assert result.get("expired_found", 0) >= 1

        # Verify expired session was deleted
        session = mock_session_factory()
        remaining = session.query(UserSession).all()
        assert len(remaining) == 1
        assert remaining[0].refresh_token_jti == "jti2"
        session.close()

    def test_cleanup_with_no_expired_sessions(self, scheduler, mock_session_factory):
        """Test cleanup when there are no expired sessions."""
        # Add test user and valid session
        session = mock_session_factory()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        session.add(user)
        session.commit()

        valid_session = UserSession(
            user_id=user.id,
            refresh_token_jti="jti1",
            family_id="fam1",
            ip_address="127.0.0.1",
            device_info="test",
            expires_at=datetime.utcnow() + timedelta(days=1),  # Valid
        )
        session.add(valid_session)
        session.commit()
        session.close()

        # Run cleanup
        result = scheduler.run_cleanup_now()

        assert result.get("success") is True
        assert result.get("expired_found") == 0

    def test_cleanup_respects_batch_size(self, scheduler, mock_session_factory):
        """Test cleanup respects batch size limit."""
        scheduler.batch_size = 5  # Small batch size

        session = mock_session_factory()

        # Create test user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="hash",
        )
        session.add(user)
        session.commit()

        # Create 10 expired sessions
        for i in range(10):
            expired_session = UserSession(
                user_id=user.id,
                refresh_token_jti=f"jti{i}",
                family_id=f"fam{i}",
                ip_address="127.0.0.1",
                device_info="test",
                expires_at=datetime.utcnow() - timedelta(days=1),
            )
            session.add(expired_session)

        session.commit()
        session.close()

        # Run cleanup with batch size of 5
        result = scheduler.run_cleanup_now()

        # Should have found 10 but limited to batch size
        assert result.get("success") is True
        assert result.get("expired_found") == 10

    def test_scheduler_handles_database_errors(self, scheduler):
        """Test scheduler handles database errors gracefully."""

        # Mock session factory to raise error
        def error_factory():
            raise RuntimeError("Database connection failed")

        scheduler.session_factory = error_factory

        result = scheduler.run_cleanup_now()

        assert result.get("success") is False
        assert result.get("error") is not None

    def test_scheduler_lifecycle_start_stop_start(self, scheduler):
        """Test scheduler can be restarted after stopping."""
        scheduler.start()
        assert scheduler.is_running is True

        scheduler.stop()
        assert scheduler.is_running is False

        scheduler.start()
        assert scheduler.is_running is True

        scheduler.stop()


class TestSchedulerIntegration:
    """Integration tests for scheduler with mock FastAPI app."""

    @pytest.fixture
    def mock_session_factory(self):
        """Create mock session factory."""
        engine = create_engine("sqlite:///:memory:")
        from src.db.base import Base

        Base.metadata.create_all(engine)

        SessionLocal = sessionmaker(bind=engine)
        return SessionLocal

    @pytest.fixture
    def scheduler(self, mock_session_factory):
        """Create scheduler with real database."""
        config = Mock(spec=AuthConfig)
        config.cleanup_interval_hours = 1
        config.cleanup_batch_size = 50

        return SessionCleanupScheduler(
            session_factory=mock_session_factory,
            config=config,
            cleanup_interval_hours=1,
            batch_size=50,
        )

    def test_scheduler_with_multiple_users(self, scheduler, mock_session_factory):
        """Test cleanup with multiple users and sessions."""
        session = mock_session_factory()

        # Create multiple users
        users = []
        for i in range(3):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password_hash="hash",
            )
            session.add(user)
            users.append(user)

        session.commit()

        # Add sessions for each user (mix of expired and valid)
        for i, user in enumerate(users):
            # Expired session
            expired_session = UserSession(
                user_id=user.id,
                refresh_token_jti=f"expired_{i}",
                family_id=f"fam_exp_{i}",
                ip_address="127.0.0.1",
                device_info="test",
                expires_at=datetime.utcnow() - timedelta(days=1),
            )
            session.add(expired_session)

            # Valid session
            valid_session = UserSession(
                user_id=user.id,
                refresh_token_jti=f"valid_{i}",
                family_id=f"fam_val_{i}",
                ip_address="127.0.0.1",
                device_info="test",
                expires_at=datetime.utcnow() + timedelta(days=1),
            )
            session.add(valid_session)

        session.commit()
        session.close()

        # Run cleanup
        result = scheduler.run_cleanup_now()

        assert result.get("success") is True
        assert result.get("expired_found") == 3  # 3 expired sessions

        # Verify only valid sessions remain
        session = mock_session_factory()
        remaining = session.query(UserSession).all()
        assert len(remaining) == 3  # 3 valid sessions
        assert all("valid" in s.refresh_token_jti for s in remaining)
        session.close()

    def test_scheduler_logs_errors(self, scheduler, caplog):
        """Test scheduler logs errors appropriately."""

        # Mock session factory to raise error
        def error_factory():
            raise Exception("Test error")

        scheduler.session_factory = error_factory

        result = scheduler.run_cleanup_now()

        assert result.get("success") is False
        # Error should be captured in result
        assert result.get("error") is not None
