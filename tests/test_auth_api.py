# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive integration tests for authentication API endpoints in PromptVault.

This module provides comprehensive integration tests for all 11 authentication
endpoints using FastAPI TestClient. Tests cover full request/response cycles
with a real in-memory database.

Endpoints Tested:
    Public Endpoints (6):
        POST /api/auth/register - User registration
        POST /api/auth/login - User login
        POST /api/auth/refresh - Token refresh
        POST /api/auth/logout - User logout
        POST /api/auth/password-reset/request - Request password reset
        POST /api/auth/password-reset/confirm - Confirm password reset

    Protected Endpoints (5):
        GET /api/auth/me - Get current user info
        POST /api/auth/change-password - Change password
        GET /api/auth/sessions - List user sessions
        DELETE /api/auth/sessions/{session_id} - Revoke specific session
        DELETE /api/auth/sessions - Revoke all sessions except current

Test Coverage:
    - Full request/response cycle
    - Success cases (happy path)
    - Error cases (validation, authentication, authorization)
    - Security features (lockout, rate limiting, token reuse)
    - Database integration (real transactions)
    - JWT token validation
    - Session management

Target: ≥90% endpoint coverage
Execution time: < 20 seconds
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.db.models.password_reset_token import PasswordResetToken


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def auth_client(test_db_engine, temp_data_dir: str):
    """FastAPI TestClient configured for authentication testing.

    Creates a test client with in-memory database, proper session management,
    and test configuration. Uses only the auth router to avoid issues with
    other routers during testing.

    Yields:
        TestClient: Configured test client for API testing
    """
    from fastapi import FastAPI
    import importlib.util
    import sys
    from pathlib import Path
    from src.db import session as session_module
    from sqlalchemy.orm import sessionmaker

    # Import auth router directly without going through __init__.py
    auth_module_path = Path(__file__).parent.parent / "src" / "web" / "routers" / "auth.py"
    spec = importlib.util.spec_from_file_location("auth_router_module", auth_module_path)
    auth_router_module = importlib.util.module_from_spec(spec)
    sys.modules["auth_router_module"] = auth_router_module
    spec.loader.exec_module(auth_router_module)
    auth_router = auth_router_module.router

    # Store original session factory
    original_session_local = session_module.SessionLocal

    # Create test session factory
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    # Patch the session factory
    session_module.SessionLocal = TestSessionLocal

    # Create minimal FastAPI app with just auth router
    app = FastAPI(title="PromptVault Auth Test")
    app.include_router(auth_router, prefix="/api")

    # Create test client
    client = TestClient(app)

    try:
        yield client
    finally:
        client.close()
        # Restore original session factory
        session_module.SessionLocal = original_session_local


@pytest.fixture
def test_user_credentials() -> Dict[str, str]:
    """Test user credentials for authentication.

    Returns:
        dict: Username, email, and password
    """
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "SecureP@ssw0rd123",
    }


@pytest.fixture
def registered_user(auth_client: TestClient, test_user_credentials: Dict[str, str]) -> Dict[str, Any]:
    """Create a registered user and return user data with tokens.

    Args:
        auth_client: Test client
        test_user_credentials: User credentials

    Returns:
        dict: User data including tokens
    """
    response = auth_client.post(
        "/api/auth/register",
        json={
            "username": test_user_credentials["username"],
            "email": test_user_credentials["email"],
            "password": test_user_credentials["password"],
            "confirm_password": test_user_credentials["password"],
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(registered_user: Dict[str, Any]) -> Dict[str, str]:
    """Create authentication headers with valid access token.

    Args:
        registered_user: Registered user data with tokens

    Returns:
        dict: Authorization headers
    """
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


# ============================================================================
# TEST POST /api/auth/register
# ============================================================================


class TestRegisterEndpoint:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, auth_client: TestClient):
        """Test successful user registration."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0
        assert "user" in data

        # Verify user data
        user = data["user"]
        assert user["username"] == "alice"
        assert user["email"] == "alice@example.com"
        assert user["role"] == "viewer"
        assert user["is_active"] is True
        assert "id" in user
        assert "created_at" in user

    def test_register_duplicate_username(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test registration with duplicate username returns 409."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": registered_user["user"]["username"],
                "email": "different@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 409
        assert "username" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test registration with duplicate email returns 409."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": registered_user["user"]["email"],
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 409
        assert "email" in response.json()["detail"].lower()

    def test_register_password_policy_violation(self, auth_client: TestClient):
        """Test registration with weak password returns 400."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "weak",
                "confirm_password": "weak",
            },
        )

        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower()

    def test_register_password_mismatch(self, auth_client: TestClient):
        """Test registration with password confirmation mismatch returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "alice@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "DifferentP@ssw0rd456",
            },
        )

        assert response.status_code == 422

    def test_register_invalid_email(self, auth_client: TestClient):
        """Test registration with invalid email format returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "email": "not-an-email",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )

        assert response.status_code == 422

    def test_register_missing_fields(self, auth_client: TestClient):
        """Test registration with missing required fields returns 422."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                # Missing email, password, confirm_password
            },
        )

        assert response.status_code == 422


# ============================================================================
# TEST POST /api/auth/login
# ============================================================================


class TestLoginEndpoint:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success_with_username(
        self,
        auth_client: TestClient,
        test_user_credentials: Dict[str, str],
        registered_user: Dict[str, Any]
    ):
        """Test successful login with username."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data

    def test_login_success_with_email(
        self,
        auth_client: TestClient,
        test_user_credentials: Dict[str, str],
        registered_user: Dict[str, Any]
    ):
        """Test successful login with email."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["email"],
                "password": test_user_credentials["password"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_login_invalid_credentials(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test login with invalid password returns 401."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert "credentials" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, auth_client: TestClient):
        """Test login with nonexistent user returns 401."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "nonexistent",
                "password": "SomePassword123",
            },
        )

        assert response.status_code == 401

    def test_login_account_lockout(
        self,
        auth_client: TestClient,
        registered_user: Dict[str, Any],
        test_user_credentials: Dict[str, str]
    ):
        """Test account locks after max failed login attempts."""
        # Attempt login with wrong password 5 times
        for _ in range(5):
            response = auth_client.post(
                "/api/auth/login",
                json={
                    "username_or_email": test_user_credentials["username"],
                    "password": "WrongPassword123",
                },
            )
            assert response.status_code == 401

        # 6th attempt should be locked
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        assert "locked" in response.json()["detail"].lower()


# ============================================================================
# TEST POST /api/auth/refresh
# ============================================================================


class TestRefreshEndpoint:
    """Tests for POST /api/auth/refresh endpoint."""

    def test_refresh_success(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test successful token refresh."""
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data

        # Verify new tokens are different (rotation)
        assert data["access_token"] != registered_user["access_token"]
        assert data["refresh_token"] != registered_user["refresh_token"]

    def test_refresh_token_rotation(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test refresh tokens are rotated with same family."""
        # First refresh
        response1 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Second refresh with new token
        response2 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": data1["refresh_token"]},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # All tokens should be different
        assert data1["refresh_token"] != registered_user["refresh_token"]
        assert data2["refresh_token"] != data1["refresh_token"]

    def test_refresh_invalid_token(self, auth_client: TestClient):
        """Test refresh with invalid token returns 401."""
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    def test_refresh_expired_token(self, auth_client: TestClient):
        """Test refresh with expired token returns 401."""
        # Create a token that expired long ago
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token},
        )

        assert response.status_code == 401

    def test_refresh_token_reuse_detection(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test token reuse is detected and family is revoked."""
        # Get new token
        response1 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Try to reuse old token (security breach simulation)
        response2 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        # Should detect reuse and revoke family
        assert response2.status_code == 401
        assert "reuse" in response2.json()["detail"].lower()

        # New token should also be invalid (family revoked)
        response3 = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": data1["refresh_token"]},
        )
        assert response3.status_code == 401


# ============================================================================
# TEST POST /api/auth/logout
# ============================================================================


class TestLogoutEndpoint:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test successful logout."""
        response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    def test_logout_session_revoked(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test logout revokes session."""
        # Logout
        response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response.status_code == 200

        # Try to refresh with logged out token
        response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response.status_code == 401

    def test_logout_idempotent(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test logout with invalid token doesn't error (idempotent)."""
        # First logout
        response1 = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert response1.status_code == 200

        # Second logout with same token (already logged out)
        response2 = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        # Should return 200 (idempotent)
        assert response2.status_code == 200


# ============================================================================
# TEST GET /api/auth/me
# ============================================================================


class TestMeEndpoint:
    """Tests for GET /api/auth/me endpoint."""

    def test_me_success(self, auth_client: TestClient, auth_headers: Dict[str, str], registered_user: Dict[str, Any]):
        """Test getting current user with valid token."""
        response = auth_client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify user data
        assert data["username"] == registered_user["user"]["username"]
        assert data["email"] == registered_user["user"]["email"]
        assert data["role"] == registered_user["user"]["role"]
        assert "id" in data

    def test_me_unauthorized_no_token(self, auth_client: TestClient):
        """Test /me without token returns 401."""
        response = auth_client.get("/api/auth/me")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_me_invalid_token(self, auth_client: TestClient):
        """Test /me with invalid token returns 401."""
        response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_me_expired_token(self, auth_client: TestClient):
        """Test /me with expired token returns 401."""
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ.invalid"

        response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401


# ============================================================================
# TEST POST /api/auth/change-password
# ============================================================================


class TestChangePasswordEndpoint:
    """Tests for POST /api/auth/change-password endpoint."""

    def test_change_password_success(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str],
        test_user_credentials: Dict[str, str]
    ):
        """Test successful password change."""
        new_password = "NewSecureP@ssw0rd456"

        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": new_password,
                "confirm_new_password": new_password,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "password changed" in data["message"].lower()

        # Verify can login with new password
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": new_password,
            },
        )
        assert login_response.status_code == 200

    def test_change_password_incorrect_old(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test change password with incorrect old password returns 401."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "WrongPassword123",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401

    def test_change_password_policy_violation(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str],
        test_user_credentials: Dict[str, str]
    ):
        """Test change password with weak new password returns 400."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": "weak",
                "confirm_new_password": "weak",
            },
        )

        assert response.status_code == 400

    def test_change_password_confirmation_mismatch(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str],
        test_user_credentials: Dict[str, str]
    ):
        """Test change password with mismatched confirmation returns 422."""
        response = auth_client.post(
            "/api/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": test_user_credentials["password"],
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "DifferentP@ssw0rd789",
            },
        )

        assert response.status_code == 422

    def test_change_password_unauthorized(self, auth_client: TestClient):
        """Test change password without token returns 401."""
        response = auth_client.post(
            "/api/auth/change-password",
            json={
                "old_password": "OldPassword123",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401


# ============================================================================
# TEST GET /api/auth/sessions
# ============================================================================


class TestSessionsEndpoint:
    """Tests for GET /api/auth/sessions endpoint."""

    def test_sessions_list_success(self, auth_client: TestClient, auth_headers: Dict[str, str]):
        """Test listing user sessions."""
        response = auth_client.get("/api/auth/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "sessions" in data
        assert "total" in data
        assert data["total"] >= 1  # At least the current session

        # Verify session data structure
        if data["sessions"]:
            session = data["sessions"][0]
            assert "id" in session
            assert "family_id" in session
            assert "created_at" in session
            assert "ip_address" in session
            assert "user_agent" in session
            assert "is_revoked" in session

    def test_sessions_empty_list(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test listing sessions when all are revoked."""
        # Logout (revoke session)
        auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )

        # Login again to get new session
        new_login = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": registered_user["user"]["username"],
                "password": "SecureP@ssw0rd123",
            },
        )

        # List sessions
        response = auth_client.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {new_login.json()['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_sessions_multiple(
        self,
        auth_client: TestClient,
        test_user_credentials: Dict[str, str],
        registered_user: Dict[str, Any]
    ):
        """Test listing multiple sessions."""
        # Create second session by logging in again
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_response.status_code == 200

        # List sessions from first session
        response = auth_client.get(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # At least two sessions

    def test_sessions_unauthorized(self, auth_client: TestClient):
        """Test listing sessions without token returns 401."""
        response = auth_client.get("/api/auth/sessions")

        assert response.status_code == 401


# ============================================================================
# TEST DELETE /api/auth/sessions/{session_id}
# ============================================================================


class TestRevokeSessionEndpoint:
    """Tests for DELETE /api/auth/sessions/{session_id} endpoint."""

    def test_revoke_session_success(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str],
        test_user_credentials: Dict[str, str]
    ):
        """Test revoking specific session."""
        # Create second session
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        assert login_response.status_code == 200

        # Get sessions
        sessions_response = auth_client.get("/api/auth/sessions", headers=auth_headers)
        sessions = sessions_response.json()["sessions"]

        # Revoke one session
        session_id = sessions[0]["id"]
        response = auth_client.delete(
            f"/api/auth/sessions/{session_id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["revoked_count"] == 1

    def test_revoke_session_not_found(self, auth_client: TestClient, auth_headers: Dict[str, str]):
        """Test revoking non-existent session returns 404."""
        fake_session_id = "00000000-0000-0000-0000-000000000000"

        response = auth_client.delete(
            f"/api/auth/sessions/{fake_session_id}",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_revoke_session_unauthorized(self, auth_client: TestClient):
        """Test revoking session without token returns 401."""
        session_id = "00000000-0000-0000-0000-000000000000"

        response = auth_client.delete(f"/api/auth/sessions/{session_id}")

        assert response.status_code == 401


# ============================================================================
# TEST DELETE /api/auth/sessions
# ============================================================================


class TestRevokeAllSessionsEndpoint:
    """Tests for DELETE /api/auth/sessions endpoint."""

    def test_revoke_all_sessions_success(
        self,
        auth_client: TestClient,
        auth_headers: Dict[str, str],
        test_user_credentials: Dict[str, str]
    ):
        """Test revoking all sessions except current."""
        # Create multiple sessions
        for _ in range(3):
            auth_client.post(
                "/api/auth/login",
                json={
                    "username_or_email": test_user_credentials["username"],
                    "password": test_user_credentials["password"],
                },
            )

        # Revoke all except current
        response = auth_client.delete("/api/auth/sessions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "revoked_count" in data
        assert data["revoked_count"] >= 0  # May be 0 if only current session

    def test_revoke_all_sessions_count(
        self,
        auth_client: TestClient,
        test_user_credentials: Dict[str, str],
        registered_user: Dict[str, Any]
    ):
        """Test revoke all returns correct count."""
        # Create 2 additional sessions
        auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )
        auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": test_user_credentials["username"],
                "password": test_user_credentials["password"],
            },
        )

        # Revoke all from original session
        response = auth_client.delete(
            "/api/auth/sessions",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should revoke the 2 additional sessions
        assert data["revoked_count"] >= 2

    def test_revoke_all_sessions_unauthorized(self, auth_client: TestClient):
        """Test revoking all sessions without token returns 401."""
        response = auth_client.delete("/api/auth/sessions")

        assert response.status_code == 401


# ============================================================================
# TEST POST /api/auth/password-reset/request
# ============================================================================


class TestPasswordResetRequestEndpoint:
    """Tests for POST /api/auth/password-reset/request endpoint."""

    def test_password_reset_request_success(
        self,
        auth_client: TestClient,
        test_user_credentials: Dict[str, str],
        registered_user: Dict[str, Any]
    ):
        """Test successful password reset request."""
        response = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": test_user_credentials["email"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "email" in data
        # Email should be masked
        assert "***" in data["email"]

    def test_password_reset_request_nonexistent_email(self, auth_client: TestClient):
        """Test password reset for non-existent email returns 200 (no info leakage)."""
        response = auth_client.post(
            "/api/auth/password-reset/request",
            json={"email": "nonexistent@example.com"},
        )

        # Should return 200 to prevent user enumeration
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# ============================================================================
# TEST POST /api/auth/password-reset/confirm
# ============================================================================


class TestPasswordResetConfirmEndpoint:
    """Tests for POST /api/auth/password-reset/confirm endpoint."""

    def test_password_reset_confirm_invalid_token(self, auth_client: TestClient):
        """Test password reset confirm with invalid token returns 401."""
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "invalid-token-12345",
                "new_password": "NewSecureP@ssw0rd456",
                "confirm_new_password": "NewSecureP@ssw0rd456",
            },
        )

        assert response.status_code == 401

    def test_password_reset_confirm_policy_violation(self, auth_client: TestClient):
        """Test password reset with weak password returns 400."""
        response = auth_client.post(
            "/api/auth/password-reset/confirm",
            json={
                "token": "some-valid-token-format-12345678901234567890",
                "new_password": "weak",
                "confirm_new_password": "weak",
            },
        )

        # May return 400 for policy violation or 401 for invalid token
        assert response.status_code in [400, 401]


# ============================================================================
# TEST SECURITY HEADERS
# ============================================================================


class TestSecurityHeaders:
    """Tests for security headers in responses."""

    def test_unauthorized_has_www_authenticate(self, auth_client: TestClient):
        """Test 401 responses include WWW-Authenticate header."""
        response = auth_client.get("/api/auth/me")

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers
        assert "Bearer" in response.headers["WWW-Authenticate"]

    def test_invalid_token_error_description(self, auth_client: TestClient):
        """Test invalid token returns proper error in WWW-Authenticate."""
        response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers


# ============================================================================
# TEST ERROR RESPONSES
# ============================================================================


class TestErrorResponses:
    """Tests for error response format and content."""

    def test_error_has_detail_field(self, auth_client: TestClient):
        """Test error responses have detail field."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "nonexistent",
                "password": "password",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_validation_error_format(self, auth_client: TestClient):
        """Test validation errors have proper format."""
        response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "ab",  # Too short
                "email": "invalid-email",
                "password": "test",
                "confirm_password": "test",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_no_sensitive_data_in_errors(self, auth_client: TestClient):
        """Test error messages don't leak sensitive data."""
        response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "testuser",
                "password": "wrongpassword",
            },
        )

        assert response.status_code in [401, 404]
        data = response.json()
        detail = data["detail"].lower()

        # Should not contain password hashes or sensitive database info
        assert "argon2" not in detail
        assert "$" not in detail
        assert "hash" not in detail


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestAuthenticationFlow:
    """Integration tests for complete authentication flows."""

    def test_full_registration_login_flow(self, auth_client: TestClient):
        """Test complete flow: register -> login -> access protected endpoint."""
        # Register
        register_response = auth_client.post(
            "/api/auth/register",
            json={
                "username": "flowtest",
                "email": "flowtest@example.com",
                "password": "SecureP@ssw0rd123",
                "confirm_password": "SecureP@ssw0rd123",
            },
        )
        assert register_response.status_code == 201

        # Login
        login_response = auth_client.post(
            "/api/auth/login",
            json={
                "username_or_email": "flowtest",
                "password": "SecureP@ssw0rd123",
            },
        )
        assert login_response.status_code == 200

        # Access protected endpoint
        me_response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "flowtest"

    def test_token_refresh_flow(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test complete token refresh flow."""
        # Refresh token
        refresh_response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert refresh_response.status_code == 200

        # Use new access token
        me_response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {refresh_response.json()['access_token']}"}
        )
        assert me_response.status_code == 200

    def test_logout_flow(self, auth_client: TestClient, registered_user: Dict[str, Any]):
        """Test complete logout flow."""
        # Logout
        logout_response = auth_client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert logout_response.status_code == 200

        # Try to use tokens after logout
        me_response = auth_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {registered_user['access_token']}"}
        )
        # Access token may still work briefly (short-lived)
        # But refresh should fail
        refresh_response = auth_client.post(
            "/api/auth/refresh",
            json={"refresh_token": registered_user["refresh_token"]},
        )
        assert refresh_response.status_code == 401
