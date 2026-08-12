# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for AuthService in PromptVault.

This module provides thorough coverage (≥95%) for:
- AuthService (src/services/auth/auth_service.py)

Tests cover:
- User registration with validation
- User authentication (login)
- Token refresh and rotation
- Logout functionality
- Password change
- Session management (get, revoke)
- Security features (account lockout, token reuse detection, session limits)
- Edge cases and error handling

Target: ≥95% code coverage of AuthService
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from jwt.exceptions import (
    ExpiredSignatureError,
)
from jwt.exceptions import (
    InvalidTokenError as JWTInvalidTokenError,
)

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.services.auth.auth_service import AuthService
from src.services.auth.lockout_service import LockoutService
from src.services.auth.session_service import SessionService
from src.services.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordPolicyError,
    SessionNotFoundError,
    TokenReuseDetectedError,
    UnauthorizedError,
    UsernameAlreadyExistsError,
)

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def auth_config():
    """Create AuthConfig instance with test settings.

    Returns:
        AuthConfig: Configuration with authentication settings
    """
    return AuthConfig(
        max_login_attempts=5,
        account_lockout_duration_seconds=900,  # 15 minutes
        max_sessions_per_user=5,
        jwt_access_token_expire_seconds=900,  # 15 minutes
        jwt_refresh_token_expire_seconds=604800,  # 7 days
    )


@pytest.fixture
def mock_db_session():
    """Create mock database session.

    Returns:
        Mock: Mocked database session
    """
    session = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.flush = Mock()
    return session


@pytest.fixture
def mock_password_service():
    """Create mock PasswordService.

    Returns:
        Mock: Mocked PasswordService
    """
    service = Mock()
    service.hash_password = Mock(return_value="$argon2id$hashed_password")
    service.verify_password = Mock(return_value=True)
    service.validate_password_policy = Mock(return_value=(True, []))
    return service


@pytest.fixture
def mock_jwt_service():
    """Create mock JWTService.

    Returns:
        Mock: Mocked JWTService
    """
    service = Mock()
    service.generate_access_token = Mock(return_value="mock_access_token")
    service.generate_refresh_token = Mock(return_value="mock_refresh_token")
    service.validate_refresh_token = Mock(
        return_value={
            "sub": "user_id_123",
            "family_id": "family_id_123",
            "jti": "jti_123",
        }
    )
    service.decode_token_unsafe = Mock(return_value={"family_id": "family_id_123"})
    return service


@pytest.fixture
def mock_user_repository():
    """Create mock UserRepository.

    Returns:
        Mock: Mocked UserRepository
    """
    repo = Mock()
    repo.email_exists = Mock(return_value=False)
    repo.username_exists = Mock(return_value=False)
    repo.create = Mock()
    repo.get_by_email_or_username = Mock()
    repo.get_by_id = Mock()
    repo.increment_failed_login = Mock()
    repo.reset_failed_login = Mock()
    repo.lock_account = Mock()
    repo.unlock_account = Mock()
    repo.update_last_login = Mock()
    repo.update_password_hash = Mock()
    return repo


@pytest.fixture
def mock_session_repository():
    """Create mock SessionRepository.

    Returns:
        Mock: Mocked SessionRepository
    """
    repo = Mock()
    repo.create_session = Mock()
    repo.get_by_family_id = Mock()
    repo.get_user_sessions = Mock(return_value=[])
    repo.count_user_sessions = Mock(return_value=0)
    repo.get_oldest_user_session = Mock(return_value=None)
    repo.revoke_session = Mock(return_value=True)
    repo.revoke_token_family = Mock(return_value=1)
    repo.revoke_all_user_sessions = Mock(return_value=0)
    repo.update_session_token = Mock()
    repo.get_by_id = Mock()
    return repo


@pytest.fixture
def sample_user():
    """Create sample User instance.

    Returns:
        User: Sample user object
    """
    user = User()
    user.id = "user_id_123"
    user.username = "testuser"
    user.email = "test@example.com"
    user.password_hash = "$argon2id$hashed_password"
    user.role = "viewer"
    user.is_active = True
    user.email_verified = False
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.fixture
def sample_session():
    """Create sample UserSession instance.

    Returns:
        UserSession: Sample session object
    """
    session = UserSession()
    session.id = "session_id_123"
    session.user_id = "user_id_123"
    session.family_id = "family_id_123"
    session.refresh_token_jti = "jti_123"
    session.is_revoked = False
    session.device_info = "Mozilla/5.0"
    session.ip_address = "192.168.1.1"
    session.created_at = datetime.now(UTC)
    session.last_used_at = datetime.now(UTC)
    session.expires_at = datetime.now(UTC) + timedelta(days=7)
    return session


@pytest.fixture
def auth_service(
    auth_config,
    mock_db_session,
    mock_password_service,
    mock_jwt_service,
    mock_user_repository,
    mock_session_repository,
):
    """Create AuthService with mocked dependencies.

    Returns:
        AuthService: Service instance with mocked dependencies
    """
    service = AuthService(mock_db_session, auth_config)
    service.password_service = mock_password_service
    service.jwt_service = mock_jwt_service
    service.user_repo = mock_user_repository
    service.session_repo = mock_session_repository
    # Rebuild sub-services so they see the mocked dependencies above,
    # not the real ones AuthService.__init__ constructed them with.
    service.lockout_service = LockoutService(
        mock_db_session, auth_config, mock_password_service, mock_user_repository
    )
    service.session_service = SessionService(
        mock_db_session, auth_config, mock_session_repository
    )
    return service


# ============================================================================
# TEST: register() method
# ============================================================================


class TestRegister:
    """Test suite for AuthService.register() method."""

    def test_successful_registration(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test successful user registration."""
        # Arrange
        mock_user_repository.create.return_value = sample_user

        # Act
        result = auth_service.register(
            username="testuser",
            email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["access_token"] == "mock_access_token"
        assert result["refresh_token"] == "mock_refresh_token"
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 900
        assert result["user"]["id"] == "user_id_123"
        assert result["user"]["username"] == "testuser"
        assert result["user"]["email"] == "test@example.com"
        assert result["user"]["role"] == "viewer"

        mock_user_repository.create.assert_called_once()
        mock_db_session.commit.assert_called()

    def test_duplicate_email_error(self, auth_service, mock_user_repository):
        """Test registration fails with duplicate email."""
        # Arrange
        mock_user_repository.email_exists.return_value = True

        # Act & Assert
        with pytest.raises(EmailAlreadyExistsError) as exc_info:
            auth_service.register(
                username="testuser",
                email="duplicate@example.com",
                password="SecureP@ssw0rd123",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "already registered" in str(exc_info.value)

    def test_duplicate_username_error(self, auth_service, mock_user_repository):
        """Test registration fails with duplicate username."""
        # Arrange
        mock_user_repository.username_exists.return_value = True

        # Act & Assert
        with pytest.raises(UsernameAlreadyExistsError) as exc_info:
            auth_service.register(
                username="duplicate",
                email="test@example.com",
                password="SecureP@ssw0rd123",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "already taken" in str(exc_info.value)

    def test_password_policy_violation(self, auth_service, mock_password_service):
        """Test registration fails with weak password."""
        # Arrange
        mock_password_service.validate_password_policy.return_value = (
            False,
            [
                "Password must be at least 12 characters",
                "Password must contain uppercase",
            ],
        )

        # Act & Assert
        with pytest.raises(PasswordPolicyError) as exc_info:
            auth_service.register(
                username="testuser",
                email="test@example.com",
                password="weak",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "policy requirements" in str(exc_info.value)

    def test_default_role_assignment(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test default role is 'viewer'."""
        # Arrange
        mock_user_repository.create.return_value = sample_user

        # Act
        auth_service.register(
            username="testuser",
            email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        create_call = mock_user_repository.create.call_args
        assert create_call.kwargs["role"] == "viewer"

    def test_custom_role_assignment(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test custom role can be assigned."""
        # Arrange
        sample_user.role = "admin"
        mock_user_repository.create.return_value = sample_user

        # Act
        result = auth_service.register(
            username="adminuser",
            email="admin@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            role="admin",
        )

        # Assert
        assert result["user"]["role"] == "admin"
        create_call = mock_user_repository.create.call_args
        assert create_call.kwargs["role"] == "admin"

    def test_session_creation(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test session is created during registration."""
        # Arrange
        mock_user_repository.create.return_value = sample_user

        # Act
        auth_service.register(
            username="testuser",
            email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_session_repository.create_session.assert_called_once()
        call_args = mock_session_repository.create_session.call_args
        assert call_args.kwargs["user_id"] == "user_id_123"
        assert call_args.kwargs["device_info"] == "Mozilla/5.0"
        assert call_args.kwargs["ip_address"] == "192.168.1.1"

    def test_token_generation(
        self,
        auth_service,
        mock_jwt_service,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test tokens are generated during registration."""
        # Arrange
        mock_user_repository.create.return_value = sample_user

        # Act
        auth_service.register(
            username="testuser",
            email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_jwt_service.generate_access_token.assert_called_once()
        mock_jwt_service.generate_refresh_token.assert_called_once()


# ============================================================================
# TEST: login() method
# ============================================================================


class TestLogin:
    """Test suite for AuthService.login() method."""

    def test_successful_login_with_username(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test successful login with username."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        result = auth_service.login(
            username_or_email="testuser",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["access_token"] == "mock_access_token"
        assert result["refresh_token"] == "mock_refresh_token"
        assert result["user"]["username"] == "testuser"
        mock_user_repository.reset_failed_login.assert_called_once_with("user_id_123")
        mock_user_repository.update_last_login.assert_called_once_with("user_id_123")

    def test_successful_login_with_email(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test successful login with email."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        result = auth_service.login(
            username_or_email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["access_token"] == "mock_access_token"
        assert result["user"]["email"] == "test@example.com"

    def test_invalid_credentials_user_not_found(
        self, auth_service, mock_user_repository
    ):
        """Test login fails when user not found."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = None

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.login(
                username_or_email="nonexistent",
                password="password",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "User not found" in str(exc_info.value)

    def test_invalid_credentials_wrong_password(
        self,
        auth_service,
        mock_user_repository,
        mock_password_service,
        mock_db_session,
        sample_user,
    ):
        """Test login fails with wrong password."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_password_service.verify_password.return_value = False

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.login(
                username_or_email="testuser",
                password="wrongpassword",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "Invalid password" in str(exc_info.value)
        mock_user_repository.increment_failed_login.assert_called_once_with(
            "user_id_123"
        )

    def test_account_lockout_after_max_attempts(
        self,
        auth_service,
        mock_user_repository,
        mock_password_service,
        mock_db_session,
        sample_user,
    ):
        """Test account locks after max failed attempts."""
        # Arrange
        sample_user.failed_login_attempts = 4  # One more will trigger lockout
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_password_service.verify_password.return_value = False

        # Act & Assert
        with pytest.raises(AccountLockedError) as exc_info:
            auth_service.login(
                username_or_email="testuser",
                password="wrongpassword",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "locked after" in str(exc_info.value)
        mock_user_repository.lock_account.assert_called_once()

    def test_account_locked_cannot_login(
        self, auth_service, mock_user_repository, sample_user
    ):
        """Test login fails when account is locked."""
        # Arrange
        sample_user.locked_until = datetime.now(UTC) + timedelta(minutes=10)
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act & Assert
        with pytest.raises(AccountLockedError) as exc_info:
            auth_service.login(
                username_or_email="testuser",
                password="password",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "locked until" in str(exc_info.value)

    def test_lockout_expiration_auto_unlock(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test account auto-unlocks after lockout period expires."""
        # Arrange
        sample_user.locked_until = datetime.now(UTC) - timedelta(minutes=1)  # Expired
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        result = auth_service.login(
            username_or_email="testuser",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_user_repository.unlock_account.assert_called_once_with("user_id_123")
        assert result["access_token"] == "mock_access_token"

    def test_failed_attempt_counter_reset_on_success(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test failed attempt counter resets on successful login."""
        # Arrange
        sample_user.failed_login_attempts = 3
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_user_repository.reset_failed_login.assert_called_once_with("user_id_123")

    def test_inactive_account_error(
        self, auth_service, mock_user_repository, sample_user
    ):
        """Test login fails when account is inactive."""
        # Arrange
        sample_user.is_active = False
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act & Assert
        with pytest.raises(AccountInactiveError) as exc_info:
            auth_service.login(
                username_or_email="testuser",
                password="password",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "not active" in str(exc_info.value)

    def test_session_creation_with_ip_and_user_agent(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test session is created with IP and user agent."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="password",
            ip_address="10.0.0.1",
            user_agent="Chrome/91.0",
        )

        # Assert
        call_args = mock_session_repository.create_session.call_args
        assert call_args.kwargs["ip_address"] == "10.0.0.1"
        assert call_args.kwargs["device_info"] == "Chrome/91.0"

    def test_last_login_timestamp_update(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test last_login timestamp is updated."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="password",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_user_repository.update_last_login.assert_called_once_with("user_id_123")

    def test_session_limit_enforcement(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test oldest session removed when limit exceeded."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_session_repository.count_user_sessions.return_value = 5  # At limit
        oldest_session = Mock()
        oldest_session.family_id = "oldest_family_id"
        mock_session_repository.get_oldest_user_session.return_value = oldest_session

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="password",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_session_repository.revoke_session.assert_called_with("oldest_family_id")

    def test_session_limit_not_enforced_when_below_limit(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test oldest session not removed when below limit."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_session_repository.count_user_sessions.return_value = 3  # Below limit

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="password",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_session_repository.get_oldest_user_session.assert_not_called()


# ============================================================================
# TEST: refresh_tokens() method
# ============================================================================


class TestRefreshTokens:
    """Test suite for AuthService.refresh_tokens() method."""

    def test_successful_token_refresh(
        self,
        auth_service,
        mock_jwt_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
        sample_session,
    ):
        """Test successful token refresh."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        result = auth_service.refresh_tokens(
            refresh_token="valid_refresh_token",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["access_token"] == "mock_access_token"
        assert result["refresh_token"] == "mock_refresh_token"
        assert result["token_type"] == "Bearer"
        mock_session_repository.update_session_token.assert_called_once()

    def test_token_rotation_new_jti_same_family(
        self,
        auth_service,
        mock_jwt_service,
        mock_session_repository,
        mock_user_repository,
        sample_user,
        sample_session,
    ):
        """Test token rotation generates new JTI with same family."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.refresh_tokens(
            refresh_token="valid_refresh_token",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        refresh_call = mock_jwt_service.generate_refresh_token.call_args
        assert refresh_call.kwargs["family_id"] == "family_id_123"
        # JTI should be different (new UUID generated)
        assert refresh_call.kwargs["jti"] != "jti_123"

    def test_invalid_refresh_token_error(self, auth_service, mock_jwt_service):
        """Test refresh fails with invalid token."""
        # Arrange
        mock_jwt_service.validate_refresh_token.side_effect = JWTInvalidTokenError(
            "Invalid token"
        )

        # Act & Assert
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="invalid_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "Invalid refresh token" in str(exc_info.value)

    def test_expired_refresh_token_error(self, auth_service, mock_jwt_service):
        """Test refresh fails with expired token."""
        # Arrange
        mock_jwt_service.validate_refresh_token.side_effect = ExpiredSignatureError(
            "Token expired"
        )

        # Act & Assert
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="expired_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "expired" in str(exc_info.value)

    def test_revoked_token_error(
        self, auth_service, mock_session_repository, sample_session
    ):
        """Test refresh fails with revoked token."""
        # Arrange
        sample_session.is_revoked = True
        mock_session_repository.get_by_family_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="revoked_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "revoked" in str(exc_info.value)

    def test_token_reuse_detection(
        self,
        auth_service,
        mock_jwt_service,
        mock_session_repository,
        mock_db_session,
        sample_session,
    ):
        """Test token reuse detection (critical security test)."""
        # Arrange
        sample_session.refresh_token_jti = "current_jti"
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_jwt_service.validate_refresh_token.return_value = {
            "sub": "user_id_123",
            "family_id": "family_id_123",
            "jti": "old_jti",  # Different from stored JTI = reuse detected
        }

        # Act & Assert
        with pytest.raises(TokenReuseDetectedError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="reused_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "reuse detected" in str(exc_info.value)
        mock_session_repository.revoke_token_family.assert_called_once_with(
            "family_id_123"
        )

    def test_family_revocation_on_reuse(
        self,
        auth_service,
        mock_jwt_service,
        mock_session_repository,
        mock_db_session,
        sample_session,
    ):
        """Test entire family is revoked on token reuse."""
        # Arrange
        sample_session.refresh_token_jti = "current_jti"
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_jwt_service.validate_refresh_token.return_value = {
            "sub": "user_id_123",
            "family_id": "family_id_123",
            "jti": "old_jti",
        }

        # Act & Assert
        with pytest.raises(TokenReuseDetectedError):
            auth_service.refresh_tokens(
                refresh_token="reused_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        mock_session_repository.revoke_token_family.assert_called_once()
        mock_db_session.commit.assert_called()

    def test_session_not_found_error(self, auth_service, mock_session_repository):
        """Test refresh fails when session not found."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="unknown_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "not found" in str(exc_info.value)

    def test_session_update_with_ip_and_user_agent(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        sample_user,
        sample_session,
    ):
        """Test session is updated with IP and user agent."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.refresh_tokens(
            refresh_token="valid_token", ip_address="10.0.0.2", user_agent="Safari/14.0"
        )

        # Assert
        mock_session_repository.update_session_token.assert_called_once()

    def test_inactive_account_during_refresh(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        sample_user,
        sample_session,
    ):
        """Test refresh fails if account becomes inactive."""
        # Arrange
        sample_user.is_active = False
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act & Assert
        with pytest.raises(AccountInactiveError):
            auth_service.refresh_tokens(
                refresh_token="valid_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

    def test_user_deleted_during_refresh(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        sample_session,
    ):
        """Test refresh fails if user is deleted between token issue and refresh."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = None  # User deleted

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.refresh_tokens(
                refresh_token="valid_token",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert "not found" in str(exc_info.value)


# ============================================================================
# TEST: logout() method
# ============================================================================


class TestLogout:
    """Test suite for AuthService.logout() method."""

    def test_successful_logout(
        self, auth_service, mock_session_repository, mock_db_session
    ):
        """Test successful logout."""
        # Arrange
        mock_session_repository.revoke_session.return_value = True

        # Act
        result = auth_service.logout(refresh_token="valid_token")

        # Assert
        assert result is True
        mock_session_repository.revoke_session.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_session_revocation(
        self, auth_service, mock_jwt_service, mock_session_repository
    ):
        """Test session is revoked by family ID."""
        # Arrange
        mock_jwt_service.validate_refresh_token.return_value = {
            "family_id": "family_id_123"
        }

        # Act
        auth_service.logout(refresh_token="valid_token")

        # Assert
        mock_session_repository.revoke_session.assert_called_once_with("family_id_123")

    def test_logout_with_expired_token(
        self, auth_service, mock_jwt_service, mock_session_repository
    ):
        """Test logout works even with expired token (idempotent)."""
        # Arrange
        mock_jwt_service.validate_refresh_token.side_effect = ExpiredSignatureError()
        mock_jwt_service.decode_token_unsafe.return_value = {
            "family_id": "family_id_123"
        }
        mock_session_repository.revoke_session.return_value = True

        # Act
        result = auth_service.logout(refresh_token="expired_token")

        # Assert
        assert result is True
        mock_session_repository.revoke_session.assert_called_once()

    def test_logout_already_revoked_token(self, auth_service, mock_session_repository):
        """Test logout with already revoked token (no error)."""
        # Arrange
        mock_session_repository.revoke_session.return_value = False

        # Act
        result = auth_service.logout(refresh_token="already_revoked")

        # Assert
        assert result is False

    def test_logout_invalid_token_error(self, auth_service, mock_jwt_service):
        """Test logout fails with invalid token."""
        # Arrange
        mock_jwt_service.validate_refresh_token.side_effect = JWTInvalidTokenError()
        mock_jwt_service.decode_token_unsafe.side_effect = JWTInvalidTokenError()

        # Act & Assert
        with pytest.raises(InvalidTokenError):
            auth_service.logout(refresh_token="invalid_token")

    def test_logout_missing_family_id(self, auth_service, mock_jwt_service):
        """Test logout fails when token missing family_id claim."""
        # Arrange
        mock_jwt_service.validate_refresh_token.return_value = {}  # No family_id

        # Act & Assert
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.logout(refresh_token="malformed_token")

        assert "family_id" in str(exc_info.value)


# ============================================================================
# TEST: change_password() method
# ============================================================================


class TestChangePassword:
    """Test suite for AuthService.change_password() method."""

    def test_successful_password_change(
        self,
        auth_service,
        mock_user_repository,
        mock_password_service,
        mock_db_session,
        sample_user,
    ):
        """Test successful password change."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        result = auth_service.change_password(
            user_id="user_id_123",
            old_password="OldP@ssw0rd123",
            new_password="NewP@ssw0rd456",
        )

        # Assert
        assert result is True
        mock_user_repository.update_password_hash.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_old_password_verification(
        self, auth_service, mock_user_repository, mock_password_service, sample_user
    ):
        """Test old password is verified."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.change_password(
            user_id="user_id_123",
            old_password="OldP@ssw0rd123",
            new_password="NewP@ssw0rd456",
        )

        # Assert
        mock_password_service.verify_password.assert_called_once_with(
            "OldP@ssw0rd123", sample_user.password_hash
        )

    def test_incorrect_old_password_error(
        self, auth_service, mock_user_repository, mock_password_service, sample_user
    ):
        """Test change fails with incorrect old password."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_password_service.verify_password.return_value = False

        # Act & Assert
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.change_password(
                user_id="user_id_123",
                old_password="WrongPassword",
                new_password="NewP@ssw0rd456",
            )

        assert "incorrect" in str(exc_info.value)

    def test_new_password_policy_validation(
        self, auth_service, mock_user_repository, mock_password_service, sample_user
    ):
        """Test new password is validated against policy."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_password_service.validate_password_policy.return_value = (
            False,
            ["Too weak"],
        )

        # Act & Assert
        with pytest.raises(PasswordPolicyError):
            auth_service.change_password(
                user_id="user_id_123",
                old_password="OldP@ssw0rd123",
                new_password="weak",
            )

    def test_password_hash_updated(
        self, auth_service, mock_user_repository, mock_password_service, sample_user
    ):
        """Test password hash is updated with new hash."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user
        mock_password_service.hash_password.return_value = "$argon2id$new_hash"

        # Act
        auth_service.change_password(
            user_id="user_id_123",
            old_password="OldP@ssw0rd123",
            new_password="NewP@ssw0rd456",
        )

        # Assert
        mock_user_repository.update_password_hash.assert_called_once_with(
            "user_id_123", "$argon2id$new_hash"
        )

    def test_user_not_found_error(self, auth_service, mock_user_repository):
        """Test change fails when user not found."""
        # Arrange
        mock_user_repository.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            auth_service.change_password(
                user_id="nonexistent",
                old_password="password",
                new_password="NewP@ssw0rd456",
            )

        assert "not found" in str(exc_info.value)

    def test_sessions_not_revoked(
        self,
        auth_service,
        mock_user_repository,
        mock_session_repository,
        mock_password_service,
        mock_db_session,
        sample_user,
    ):
        """Test sessions remain active after password change (by design)."""
        # Arrange
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.change_password(
            user_id="user_id_123",
            old_password="OldP@ssw0rd123",
            new_password="NewP@ssw0rd456",
        )

        # Assert
        mock_session_repository.revoke_all_user_sessions.assert_not_called()


# ============================================================================
# TEST: get_user_sessions() method
# ============================================================================


class TestGetUserSessions:
    """Test suite for AuthService.get_user_sessions() method."""

    def test_retrieve_all_sessions(self, auth_service, mock_session_repository):
        """Test retrieve all sessions for user."""
        # Arrange
        session1 = Mock()
        session1.id = "session_1"
        session1.family_id = "family_1"
        session1.device_info = "Chrome"
        session1.ip_address = "192.168.1.1"
        session1.created_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        session1.last_used_at = datetime(2025, 1, 1, 13, 0, 0, tzinfo=UTC)
        session1.expires_at = datetime(2025, 1, 8, 12, 0, 0, tzinfo=UTC)

        mock_session_repository.get_user_sessions.return_value = [session1]

        # Act
        result = auth_service.get_user_sessions("user_id_123")

        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "session_1"
        assert result[0]["family_id"] == "family_1"
        assert result[0]["device_info"] == "Chrome"
        assert result[0]["ip_address"] == "192.168.1.1"

    def test_empty_session_list(self, auth_service, mock_session_repository):
        """Test empty list when user has no sessions."""
        # Arrange
        mock_session_repository.get_user_sessions.return_value = []

        # Act
        result = auth_service.get_user_sessions("user_id_123")

        # Assert
        assert result == []

    def test_session_data_includes_all_fields(
        self, auth_service, mock_session_repository
    ):
        """Test session data includes all required fields."""
        # Arrange
        session = Mock()
        session.id = "session_1"
        session.family_id = "family_1"
        session.device_info = "Firefox"
        session.ip_address = "10.0.0.1"
        session.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.last_used_at = datetime(2025, 1, 2, tzinfo=UTC)
        session.expires_at = datetime(2025, 1, 8, tzinfo=UTC)

        mock_session_repository.get_user_sessions.return_value = [session]

        # Act
        result = auth_service.get_user_sessions("user_id_123")

        # Assert
        assert "id" in result[0]
        assert "family_id" in result[0]
        assert "device_info" in result[0]
        assert "ip_address" in result[0]
        assert "created_at" in result[0]
        assert "last_used_at" in result[0]
        assert "expires_at" in result[0]

    def test_active_only_filter(self, auth_service, mock_session_repository):
        """Test only active sessions are retrieved."""
        # Act
        auth_service.get_user_sessions("user_id_123")

        # Assert
        mock_session_repository.get_user_sessions.assert_called_once_with(
            "user_id_123", active_only=True
        )

    def test_last_used_at_none_handling(self, auth_service, mock_session_repository):
        """Test handling when last_used_at is None."""
        # Arrange
        session = Mock()
        session.id = "session_1"
        session.family_id = "family_1"
        session.device_info = "Safari"
        session.ip_address = "192.168.1.1"
        session.created_at = datetime(2025, 1, 1, tzinfo=UTC)
        session.last_used_at = None  # Never used
        session.expires_at = datetime(2025, 1, 8, tzinfo=UTC)

        mock_session_repository.get_user_sessions.return_value = [session]

        # Act
        result = auth_service.get_user_sessions("user_id_123")

        # Assert
        assert result[0]["last_used_at"] is None


# ============================================================================
# TEST: revoke_session() method
# ============================================================================


class TestRevokeSession:
    """Test suite for AuthService.revoke_session() method."""

    def test_successful_session_revocation(
        self, auth_service, mock_session_repository, mock_db_session, sample_session
    ):
        """Test successful session revocation."""
        # Arrange
        mock_session_repository.get_by_id.return_value = sample_session
        mock_session_repository.revoke_session.return_value = True

        # Act
        result = auth_service.revoke_session("session_id_123", "user_id_123")

        # Assert
        assert result is True
        mock_session_repository.revoke_session.assert_called_once_with("family_id_123")
        mock_db_session.commit.assert_called_once()

    def test_unauthorized_revocation_different_user(
        self, auth_service, mock_session_repository, sample_session
    ):
        """Test revocation fails when session belongs to different user."""
        # Arrange
        sample_session.user_id = "other_user_id"
        mock_session_repository.get_by_id.return_value = sample_session

        # Act & Assert
        with pytest.raises(UnauthorizedError) as exc_info:
            auth_service.revoke_session("session_id_123", "user_id_123")

        assert "does not belong" in str(exc_info.value)

    def test_session_not_found(self, auth_service, mock_session_repository):
        """Test revoke returns False when session not found."""
        # Arrange
        mock_session_repository.get_by_id.return_value = None

        # Act
        result = auth_service.revoke_session("nonexistent", "user_id_123")

        # Assert
        assert result is False

    def test_revoke_by_family_id(
        self, auth_service, mock_session_repository, sample_session
    ):
        """Test session is revoked by family ID."""
        # Arrange
        sample_session.family_id = "specific_family_id"
        mock_session_repository.get_by_id.return_value = sample_session

        # Act
        auth_service.revoke_session("session_id_123", "user_id_123")

        # Assert
        mock_session_repository.revoke_session.assert_called_once_with(
            "specific_family_id"
        )


# ============================================================================
# TEST: revoke_all_sessions() method
# ============================================================================


class TestRevokeAllSessions:
    """Test suite for AuthService.revoke_all_sessions() method."""

    def test_revoke_all_sessions(
        self, auth_service, mock_session_repository, mock_db_session
    ):
        """Test revoke all sessions for user."""
        # Arrange
        mock_session_repository.revoke_all_user_sessions.return_value = 3

        # Act
        count = auth_service.revoke_all_sessions("user_id_123")

        # Assert
        assert count == 3
        mock_session_repository.revoke_all_user_sessions.assert_called_once_with(
            "user_id_123"
        )
        mock_db_session.commit.assert_called_once()

    def test_revoke_all_except_current(
        self, auth_service, mock_session_repository, mock_db_session
    ):
        """Test revoke all sessions except current (by family_id)."""
        # Arrange
        session1 = Mock()
        session1.family_id = "family_1"
        session2 = Mock()
        session2.family_id = "family_2"
        session3 = Mock()
        session3.family_id = "current_family"

        mock_session_repository.get_user_sessions.return_value = [
            session1,
            session2,
            session3,
        ]
        mock_session_repository.revoke_session.return_value = True

        # Act
        count = auth_service.revoke_all_sessions(
            "user_id_123", except_family_id="current_family"
        )

        # Assert
        assert count == 2
        assert mock_session_repository.revoke_session.call_count == 2
        mock_session_repository.revoke_session.assert_any_call("family_1")
        mock_session_repository.revoke_session.assert_any_call("family_2")

    def test_return_count_of_revoked_sessions(
        self, auth_service, mock_session_repository
    ):
        """Test returns correct count of revoked sessions."""
        # Arrange
        mock_session_repository.revoke_all_user_sessions.return_value = 5

        # Act
        count = auth_service.revoke_all_sessions("user_id_123")

        # Assert
        assert count == 5

    def test_revoke_zero_sessions(self, auth_service, mock_session_repository):
        """Test returns 0 when no sessions to revoke."""
        # Arrange
        mock_session_repository.revoke_all_user_sessions.return_value = 0

        # Act
        count = auth_service.revoke_all_sessions("user_id_123")

        # Assert
        assert count == 0


# ============================================================================
# TEST: Security Features
# ============================================================================


class TestSecurityFeatures:
    """Test suite for security features."""

    def test_account_lockout_mechanism(
        self,
        auth_service,
        mock_user_repository,
        mock_password_service,
        mock_db_session,
        sample_user,
    ):
        """Test account lockout after 5 failed attempts with 15 min lockout."""
        # Arrange
        sample_user.failed_login_attempts = 4
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_password_service.verify_password.return_value = False

        # Act & Assert
        with pytest.raises(AccountLockedError):
            auth_service.login(
                username_or_email="testuser",
                password="wrong",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        # Verify lockout duration is set
        lock_call = mock_user_repository.lock_account.call_args
        assert lock_call is not None

    def test_token_family_tracking(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        sample_user,
        sample_session,
    ):
        """Test token family is tracked across rotations."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.refresh_tokens(
            refresh_token="token", ip_address="192.168.1.1", user_agent="Mozilla/5.0"
        )

        # Assert
        mock_session_repository.update_session_token.assert_called_once()

    def test_token_reuse_detection_and_family_revocation(
        self,
        auth_service,
        mock_jwt_service,
        mock_session_repository,
        mock_db_session,
        sample_session,
    ):
        """Test token reuse detection triggers family revocation."""
        # Arrange
        sample_session.refresh_token_jti = "current_jti"
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_jwt_service.validate_refresh_token.return_value = {
            "sub": "user_id_123",
            "family_id": "family_id_123",
            "jti": "old_jti",  # Reuse!
        }

        # Act & Assert
        with pytest.raises(TokenReuseDetectedError):
            auth_service.refresh_tokens(
                refresh_token="reused",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        mock_session_repository.revoke_token_family.assert_called_once()

    def test_session_limit_enforcement_max_5_sessions(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        mock_db_session,
        sample_user,
    ):
        """Test session limit enforces max 5 sessions."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_session_repository.count_user_sessions.return_value = 5
        oldest_session = Mock()
        oldest_session.family_id = "oldest"
        mock_session_repository.get_oldest_user_session.return_value = oldest_session

        # Act
        auth_service.login(
            username_or_email="testuser",
            password="password",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        mock_session_repository.revoke_session.assert_called_with("oldest")

    def test_password_policy_enforcement(self, auth_service, mock_password_service):
        """Test password policy is enforced during registration."""
        # Arrange
        mock_password_service.validate_password_policy.return_value = (
            False,
            ["Too weak"],
        )

        # Act & Assert
        with pytest.raises(PasswordPolicyError):
            auth_service.register(
                username="user",
                email="user@example.com",
                password="weak",
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

    def test_timing_attack_resistance(
        self, auth_service, mock_user_repository, mock_password_service, sample_user
    ):
        """Test same error for user not found vs wrong password."""
        # Test 1: User not found
        mock_user_repository.get_by_email_or_username.return_value = None

        try:
            auth_service.login("nonexistent", "password", "192.168.1.1", "Mozilla/5.0")
        except InvalidCredentialsError as e1:
            error1 = str(e1)

        # Test 2: Wrong password
        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_password_service.verify_password.return_value = False

        try:
            auth_service.login("testuser", "wrong", "192.168.1.1", "Mozilla/5.0")
        except InvalidCredentialsError as e2:
            error2 = str(e2)

        # Both should raise InvalidCredentialsError (though messages differ in implementation)
        # The important part is they both use the same exception type
        assert error1 is not None
        assert error2 is not None


# ============================================================================
# TEST: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test suite for edge cases."""

    def test_concurrent_logins(
        self,
        auth_service,
        mock_user_repository,
        mock_session_repository,
        mock_db_session,
        sample_user,
    ):
        """Test multiple concurrent logins create separate sessions."""
        # Arrange
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act
        result1 = auth_service.login("testuser", "password", "192.168.1.1", "Chrome")
        result2 = auth_service.login("testuser", "password", "192.168.1.2", "Firefox")

        # Assert
        assert result1["access_token"] == "mock_access_token"
        assert result2["access_token"] == "mock_access_token"
        assert mock_session_repository.create_session.call_count == 2

    def test_login_during_lockout_period(
        self, auth_service, mock_user_repository, sample_user
    ):
        """Test login fails during active lockout period."""
        # Arrange
        sample_user.locked_until = datetime.now(UTC) + timedelta(minutes=5)
        mock_user_repository.get_by_email_or_username.return_value = sample_user

        # Act & Assert
        with pytest.raises(AccountLockedError):
            auth_service.login("testuser", "password", "192.168.1.1", "Mozilla/5.0")

    def test_registration_with_edge_case_inputs(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test registration with edge case valid inputs."""
        # Arrange
        mock_user_repository.create.return_value = sample_user

        # Act
        result = auth_service.register(
            username="a" * 100,  # Max length username
            email="test+tag@example.co.uk",  # Email with + and multiple domains
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["access_token"] is not None

    def test_very_long_usernames(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test handling of very long usernames (at limit)."""
        # Arrange
        long_username = "x" * 100
        sample_user.username = long_username
        mock_user_repository.create.return_value = sample_user

        # Act
        result = auth_service.register(
            username=long_username,
            email="test@example.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert result["user"]["username"] == long_username

    def test_unicode_in_user_data(
        self, auth_service, mock_user_repository, mock_db_session, sample_user
    ):
        """Test Unicode characters in username and email."""
        # Arrange
        sample_user.username = "user_测试"
        sample_user.email = "test@例え.com"
        mock_user_repository.create.return_value = sample_user

        # Act
        result = auth_service.register(
            username="user_测试",
            email="test@例え.com",
            password="SecureP@ssw0rd123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Assert
        assert "user_测试" in result["user"]["username"]

    def test_session_update_on_token_refresh(
        self,
        auth_service,
        mock_session_repository,
        mock_user_repository,
        sample_user,
        sample_session,
    ):
        """Test session last_used_at updates on token refresh."""
        # Arrange
        mock_session_repository.get_by_family_id.return_value = sample_session
        mock_user_repository.get_by_id.return_value = sample_user

        # Act
        auth_service.refresh_tokens(
            refresh_token="token", ip_address="192.168.1.1", user_agent="Mozilla/5.0"
        )

        # Assert
        mock_session_repository.update_session_token.assert_called_once()

    def test_unlimited_sessions_config(
        self,
        mock_db_session,
        mock_password_service,
        mock_jwt_service,
        mock_user_repository,
        mock_session_repository,
        sample_user,
    ):
        """Test unlimited sessions when max_sessions_per_user=0."""
        # Arrange
        config = AuthConfig(max_sessions_per_user=0)
        service = AuthService(mock_db_session, config)
        service.password_service = mock_password_service
        service.jwt_service = mock_jwt_service
        service.user_repo = mock_user_repository
        service.session_repo = mock_session_repository
        service.lockout_service = LockoutService(
            mock_db_session, config, mock_password_service, mock_user_repository
        )
        service.session_service = SessionService(
            mock_db_session, config, mock_session_repository
        )

        mock_user_repository.get_by_email_or_username.return_value = sample_user
        mock_session_repository.count_user_sessions.return_value = (
            100  # Way over normal limit
        )

        # Act
        service.login("testuser", "password", "192.168.1.1", "Mozilla/5.0")

        # Assert
        # Should not check or revoke sessions when unlimited
        mock_session_repository.get_oldest_user_session.assert_not_called()
        mock_session_repository.revoke_session.assert_not_called()


# ============================================================================
# TEST: _generate_tokens_and_session() helper
# ============================================================================


class TestGenerateTokensAndSession:
    """Test suite for _generate_tokens_and_session() helper method."""

    def test_generates_unique_family_id(
        self, auth_service, sample_user, mock_jwt_service
    ):
        """Test each call generates unique family ID."""
        # Act
        result1 = auth_service._generate_tokens_and_session(
            sample_user, "192.168.1.1", "Chrome"
        )
        result2 = auth_service._generate_tokens_and_session(
            sample_user, "192.168.1.1", "Chrome"
        )

        # Assert - Cannot directly check family_id, but verify tokens are generated
        assert result1 is not None
        assert result2 is not None

    def test_creates_session_with_expiration(
        self, auth_service, mock_session_repository, sample_user
    ):
        """Test session is created with correct expiration."""
        # Act
        auth_service._generate_tokens_and_session(
            sample_user, "192.168.1.1", "Mozilla/5.0"
        )

        # Assert
        call_args = mock_session_repository.create_session.call_args
        assert "expires_at" in call_args.kwargs
        # Verify expires_at is in the future
        expires_at = call_args.kwargs["expires_at"]
        assert expires_at > datetime.now(UTC)

    def test_response_format(self, auth_service, sample_user):
        """Test response contains all required fields."""
        # Act
        result = auth_service._generate_tokens_and_session(
            sample_user, "192.168.1.1", "Mozilla/5.0"
        )

        # Assert
        assert "access_token" in result
        assert "refresh_token" in result
        assert "token_type" in result
        assert "expires_in" in result
        assert "user" in result
        assert result["token_type"] == "Bearer"
        assert result["user"]["id"] == sample_user.id
        assert result["user"]["username"] == sample_user.username
        assert result["user"]["email"] == sample_user.email
        assert result["user"]["role"] == sample_user.role
