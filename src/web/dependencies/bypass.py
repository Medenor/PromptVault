# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Anonymous-mode (AUTH_ENABLED=false) bypass dependencies.

When authentication is disabled, these dependencies short-circuit to None so
that data endpoints remain publicly accessible. When auth is enabled they
enforce the normal requirements (active user / admin role). All callers must
guard ``user`` attribute accesses (``user.id``, ``user.username``) with
``if user:`` or ``user.id if user else None`` fallbacks.

Dependencies:
    - get_current_user_or_none(): Active user or None (bypass-friendly)
    - get_current_user_or_default(): Active user or the shared system user
    - require_role_or_bypass(): Role check or bypass (None) when disabled
    - get_user_or_bypass(): Any authenticated user or bypass (None)
    - get_admin_or_bypass(): Admin role or bypass (None)
    - get_editor_or_admin_or_bypass(): Editor/admin role or bypass (None)
    - has_valid_auth_cookie(): Best-effort stateless cookie check
"""

from collections.abc import Callable

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.config.auth_config import auth_settings
from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.db.session import get_db
from src.services.auth.jwt_service import JWTService
from src.web.dependencies.token import (
    _extract_bearer_or_cookie_token,
    enforce_account_not_locked,
    enforce_totp_enrollment_policy,
    get_jwt_service,
)


def _active_user_from_token(
    authorization: str | None,
    access_token_cookie: str | None,
    jwt_service: JWTService,
    session: Session,
) -> User | None:
    """Return the active user for a valid token, or None for any failure.

    Swallows every error on purpose: bypass dependencies never raise 401 for
    bad tokens. Policy checks that must raise (e.g. 2FA enrollment) happen in
    the caller, outside this function.
    """
    if not authorization and not access_token_cookie:
        return None

    try:
        try:
            token = _extract_bearer_or_cookie_token(authorization, access_token_cookie)
        except HTTPException:
            return None

        if not token:
            return None

        claims = jwt_service.validate_access_token(token)
        user_id = claims.get("sub")
        if not user_id:
            return None

        user_repo = UserRepository(session)
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None

        # Attach family_id from token for session identification (request-scoped,
        # not a persisted column on the User model).
        user.family_id = claims.get("family_id")  # type: ignore[attr-defined]
        return user
    except Exception:
        return None


async def get_current_user_or_none(
    request: Request,
    authorization: str | None = Header(None, description="Optional Bearer token"),
    access_token_cookie: str | None = Cookie(None, alias="access_token"),
    jwt_service: JWTService = Depends(get_jwt_service),
    session: Session = Depends(get_db),
) -> User | None:
    """Get the current active user, or None when auth is disabled/unauthenticated.

    This is the bypass-friendly variant of :func:`get_current_active_user` used
    on data endpoints that must remain accessible when ``AUTH_ENABLED=false``.

    Behavior:
        - ``AUTH_ENABLED=false``: returns ``None`` immediately (anonymous mode).
        - ``AUTH_ENABLED=true`` with no token: returns ``None``.
        - ``AUTH_ENABLED=true`` with a valid token: returns the active user.
        - Invalid/expired tokens: returns ``None`` (never raises 401).
        - Valid token, but the account is currently locked out: raises 401
          (same rule as :func:`get_current_active_user`).
        - Valid token, but the user's role requires 2FA and they have not
          enrolled: raises 403 (same rule as :func:`get_current_active_user`).

    Returns:
        Optional[User]: The authenticated user, or None.

    Raises:
        HTTPException: 401 when the account is locked out, 403 when 2FA
            enrollment is required by policy.
    """
    if not auth_settings.auth_enabled:
        return None

    user = _active_user_from_token(
        authorization, access_token_cookie, jwt_service, session
    )
    if user is None:
        return None

    # Outside the swallowing helper on purpose: these 401/403 responses must
    # reach the client rather than silently degrading to anonymous access.
    enforce_account_not_locked(user)
    enforce_totp_enrollment_policy(user, request, session)
    return user


async def get_current_user_or_default(
    user: User | None = Depends(get_current_user_or_none),
    session: Session = Depends(get_db),
) -> User:
    """Get the current user, falling back to the shared system user.

    Mutation endpoints (create/update/delete) need an owner to run under.
    When auth is enabled this simply requires a valid authenticated user
    (401 otherwise). When ``AUTH_ENABLED=false`` there is no logged-in user
    by design, so this resolves to the shared 'system' user instead of
    rejecting the request — anonymous/single-user deployments remain fully
    functional while still recording an owner for ownership checks and undo
    history. See constitution principle III: destructive endpoints must stay
    guarded by configuration (network exposure), not by disabling writes.

    Raises:
        HTTPException: 401 if auth is enabled but no user is authenticated.
    """
    if user:
        return user

    if auth_settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    return user_repo.get_or_create_default_user()


def require_role_or_bypass(allowed_roles: list[str] | None = None) -> Callable:
    """Create a dependency requiring role(s) when auth is enabled; bypass (None) when disabled.

    Mirrors :func:`src.web.dependencies.roles.require_role`, but short-circuits
    to ``None`` when ``auth_settings.auth_enabled`` is ``False`` instead of
    enforcing authentication. Pass ``allowed_roles=None`` to require any
    authenticated user without a role check.

    Args:
        allowed_roles: Role names permitted, or None to allow any authenticated user.

    Returns:
        Callable: FastAPI dependency function.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated; 403 if role check fails.
    """

    async def check_user_role_or_bypass(
        user: User | None = Depends(get_current_user_or_none),
    ) -> User | None:
        if not auth_settings.auth_enabled:
            return None
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if allowed_roles is not None and user.role not in allowed_roles:
            if len(allowed_roles) == 1:
                role_msg = f"'{allowed_roles[0]}' role"
            else:
                role_list = "', '".join(allowed_roles)
                role_msg = f"one of the following roles: '{role_list}'"
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This operation requires {role_msg}. Your role: '{user.role}'",
            )
        return user

    return check_user_role_or_bypass


async def get_user_or_bypass(
    user: User | None = Depends(get_current_user_or_none),
) -> User | None:
    """Require any authenticated user when auth is enabled; bypass (None) when disabled.

    For read endpoints over sensitive data (backups, schedules, audit logs)
    that must stay 401-guarded in normal deployments but remain accessible
    when ``AUTH_ENABLED=false``.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated.
    """
    return await require_role_or_bypass()(user)


def has_valid_auth_cookie(request: Request) -> bool:
    """Best-effort check for a valid access token in the request cookie.

    Validates the ``access_token`` cookie signature/expiration without
    performing a database lookup, so it is cheap and stateless. It is
    intentionally optimistic: any failure (missing cookie, expired, invalid
    signature) simply means "not authenticated".

    Note this does not check for session revocation (that requires a DB
    lookup) — callers relying on this for privacy-sensitive gating must pair
    it with a client-side check against an endpoint that does check revocation
    (e.g. ``/api/auth/me``).

    Args:
        request: FastAPI request object

    Returns:
        bool: True if the access_token cookie contains a valid JWT
    """
    token = request.cookies.get("access_token")
    if not token:
        return False

    try:
        jwt_service = JWTService(auth_settings)
        jwt_service.validate_access_token(token)
        return True
    except Exception:
        return False


async def get_admin_or_bypass(
    user: User | None = Depends(get_current_user_or_none),
) -> User | None:
    """Require admin when auth is enabled; bypass (None) when disabled.

    Replaces :func:`src.web.dependencies.roles.get_admin_user` on admin-only
    endpoints so they remain functional in anonymous mode. When
    ``AUTH_ENABLED=false`` this returns ``None`` without performing any role
    check.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated, 403 if not admin.
    """
    return await require_role_or_bypass(["admin"])(user)


async def get_editor_or_admin_or_bypass(
    user: User | None = Depends(get_current_user_or_none),
) -> User | None:
    """Require editor/admin when auth is enabled; bypass (None) when disabled.

    Replaces :func:`src.web.dependencies.roles.get_editor_or_admin_user` on
    editor endpoints so they remain functional in anonymous mode.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated, 403 if not editor/admin.
    """
    return await require_role_or_bypass(["admin", "editor"])(user)
