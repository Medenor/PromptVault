# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared dependency-injection providers for the auth routers.

Extracted verbatim from the original ``auth.py`` module so the split auth
routers (registration / session / password / profile) can share one canonical
set of service providers without duplication. Behavior is unchanged.
"""

from fastapi import Depends
from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from src.db.repositories.totp_repository import TotpRepository
from src.db.repositories.user_repository import UserRepository
from src.db.session import get_db
from src.services.auth.auth_service import AuthService
from src.services.auth.jwt_service import JWTService
from src.services.auth.password_reset_service import PasswordResetService
from src.services.auth.password_service import PasswordService
from src.services.auth.totp_encryption_service import TotpEncryptionService
from src.services.auth.totp_service import TotpService
from src.web.dependencies.auth import get_auth_config

# ============================================================================
# Dependency Injection
# ============================================================================


def get_auth_service(
    session: Session = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
) -> AuthService:
    """Provide AuthService instance with dependencies.

    This dependency creates an AuthService instance with all required
    repositories and services injected.

    Args:
        session: Database session (injected)
        config: Authentication configuration (injected)

    Returns:
        AuthService: Configured authentication service instance
    """
    return AuthService(session, config)


def get_password_reset_service(
    session: Session = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
) -> PasswordResetService:
    """Provide PasswordResetService instance with dependencies.

    This dependency creates a PasswordResetService instance with all required
    repositories and services injected.

    Args:
        session: Database session (injected)
        config: Authentication configuration (injected)

    Returns:
        PasswordResetService: Configured password reset service instance
    """
    password_service = PasswordService(config)
    token_repository = PasswordResetTokenRepository(session)
    user_repository = UserRepository(session)

    return PasswordResetService(
        config=config,
        password_service=password_service,
        token_repository=token_repository,
        user_repository=user_repository,
    )


def get_jwt_service(
    config: AuthConfig = Depends(get_auth_config),
) -> JWTService:
    """Provide JWTService instance with dependencies.

    This dependency creates a JWTService instance for JWT token operations.

    Args:
        config: Authentication configuration (injected)

    Returns:
        JWTService: Configured JWT service instance
    """
    return JWTService(config)


def get_totp_service(
    session: Session = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
) -> TotpService:
    """Provide TotpService instance with dependencies.

    This dependency creates a TotpService instance with all required
    repositories and services injected.

    Args:
        session: Database session (injected)
        config: Authentication configuration (injected)

    Returns:
        TotpService: Configured TOTP 2FA service instance
    """
    totp_repository = TotpRepository(session)
    encryption_service = TotpEncryptionService(config)
    password_service = PasswordService(config)
    return TotpService(totp_repository, encryption_service, password_service)
