# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication services for PromptVault.

This package provides secure authentication and authorization services including
password hashing, JWT token management, session handling, user authentication,
and password reset functionality.

Services available:
    - PasswordService: Argon2id password hashing and policy validation
    - JWTService: ES256 JWT token generation and validation
    - AuthService: Complete authentication flow (register, login, refresh, logout)
    - PasswordResetService: Secure password reset flow with email
    - LockoutService: Failed-login tracking and account lockout enforcement
    - SessionService: Session-cap enforcement and session listing/revocation

Usage:
    from src.services.auth import AuthService, PasswordService
    from src.config import auth_settings
    from src.db import get_db_session

    with get_db_session() as session:
        auth_service = AuthService(session, auth_settings)
        result = auth_service.login("alice", "password", "192.168.1.1", "Mozilla/5.0")
"""

from src.services.auth.password_service import PasswordService
from src.services.auth.jwt_service import JWTService
from src.services.auth.lockout_service import LockoutService
from src.services.auth.session_service import SessionService
from src.services.auth.auth_service import AuthService
from src.services.auth.password_reset_service import PasswordResetService

__all__ = [
    "PasswordService",
    "JWTService",
    "LockoutService",
    "SessionService",
    "AuthService",
    "PasswordResetService",
]
