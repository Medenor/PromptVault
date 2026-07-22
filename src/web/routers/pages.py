# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""HTML page routes for serving authentication and admin templates.

This module provides GET routes that serve HTML pages for the user interface.
All routes use Jinja2 templates and return HTML responses.

Routes:
    Authentication Pages (Public):
    - GET /auth/login - Login page
    - GET /auth/register - Registration page
    - GET /auth/forgot-password - Forgot password page
    - GET /auth/reset-password - Password reset page

    Authentication Pages (Protected):
    - GET /auth/profile - User profile page (requires authentication)

    Admin Pages (Protected):
    - GET /admin/users - User management page (requires admin role)
    - GET /admin/sessions - Session management page (requires admin role)

Security:
    - Public pages are accessible without authentication
    - Profile page requires active user authentication
    - Admin pages require admin role via RBAC
    - All HTML responses use proper Content-Type headers

Example Usage:
    >>> # In browser or client
    >>> GET http://localhost:8000/auth/login
    >>> # Returns login.html template
    >>>
    >>> GET http://localhost:8000/auth/profile
    >>> Authorization: Bearer <access_token>
    >>> # Returns profile.html template
    >>>
    >>> GET http://localhost:8000/admin/users
    >>> Authorization: Bearer <admin_access_token>
    >>> # Returns users.html template
"""

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os

from src.config.auth_config import auth_settings
from src.db.models.user import User
from typing import Optional

from src.web.dependencies.auth import (
    get_current_active_user,
    get_admin_user,
    get_current_user_or_none,
)
from src.web.utils.manifest import load_manifest, get_asset_path, is_production


def _has_valid_auth_cookie(request: Request) -> bool:
    """Best-effort check for a valid access token in the request cookie.

    Document (browser) navigations such as the back/forward buttons send cookies
    but not the ``Authorization`` header. When a logged-in user navigates back to
    a public auth page (e.g. ``/auth/login``), the cached login page would
    otherwise be shown even though the session is still valid.

    This helper validates the ``access_token`` cookie signature/expiration without
    performing a database lookup, so it is cheap and stateless. It is intentionally
    optimistic: any failure (missing cookie, expired, invalid signature) simply
    means "not authenticated" and the public page is served normally.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if the access_token cookie contains a valid JWT
    """
    token = request.cookies.get("access_token")
    if not token:
        return False

    try:
        from src.services.auth.jwt_service import JWTService

        jwt_service = JWTService(auth_settings)
        jwt_service.validate_access_token(token)
        return True
    except Exception:
        return False


# ============================================================================
# Router Configuration
# ============================================================================

router = APIRouter(tags=["Pages"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="src/web/templates")
templates.env.globals["load_manifest"] = load_manifest
templates.env.globals["get_asset_path"] = get_asset_path
templates.env.globals["is_production"] = is_production
templates.env.globals["is_dev"] = (
    lambda: os.getenv("ENV", "production") == "development"
)
templates.env.globals["use_vite_assets"] = (
    lambda: os.getenv("USE_VITE_ASSETS", "false").lower() == "true"
)

# ============================================================================
# Authentication Pages (Public)
# ============================================================================


@router.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page.

    This is a public page accessible without authentication.
    Users can enter their credentials to log in.

    If a user with a valid session navigates here (e.g. via the browser
    back/forward buttons), they are redirected to the home page so that a
    stale login entry in the history cannot trap them on the login screen.

    Args:
        request: FastAPI request object (injected)

    Returns:
        HTMLResponse or RedirectResponse: Rendered login.html template, or a
        redirect to ``/`` when an authenticated session is detected

    Template:
        src/web/templates/auth/login.html
    """
    # Authenticated users should never get stuck on the login page when
    # navigating through browser history. Redirect them back to the app.
    if _has_valid_auth_cookie(request):
        return RedirectResponse(url="/", status_code=302)

    response = templates.TemplateResponse(
        request,
        "auth/login.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )
    # Prevent the browser (and intermediate caches) from caching the login
    # page so that back/forward navigation always re-evaluates auth state.
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve the registration page.

    This is a public page accessible without authentication.
    Users can create a new account.

    Args:
        request: FastAPI request object (injected)

    Returns:
        HTMLResponse: Rendered register.html template

    Template:
        src/web/templates/auth/register.html
    """
    return templates.TemplateResponse(
        request,
        "auth/register.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )


@router.get("/auth/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Serve the forgot password page.

    This is a public page accessible without authentication.
    Users can request a password reset link.

    Args:
        request: FastAPI request object (injected)

    Returns:
        HTMLResponse: Rendered forgot_password.html template

    Template:
        src/web/templates/auth/forgot_password.html
    """
    return templates.TemplateResponse(
        request,
        "auth/forgot_password.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )


@router.get("/auth/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Serve the password reset page.

    This is a public page accessible without authentication.
    Users arrive here via email link with a reset token in query params.

    Args:
        request: FastAPI request object (injected)

    Returns:
        HTMLResponse: Rendered reset_password.html template

    Template:
        src/web/templates/auth/reset_password.html

    Note:
        The reset token should be passed as a query parameter (e.g., ?token=abc123)
    """
    return templates.TemplateResponse(
        request,
        "auth/reset_password.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )


# ============================================================================
# Authentication Pages (Protected)
# ============================================================================


@router.get("/auth/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: User = Depends(get_current_active_user)):
    """Serve the user profile page.

    This page is protected and requires authentication.
    Users can view and update their profile information.

    Args:
        request: FastAPI request object (injected)
        user: Authenticated active user (injected)

    Returns:
        HTMLResponse: Rendered profile.html template

    Raises:
        HTTPException: 401 if not authenticated or account inactive

    Template:
        src/web/templates/auth/profile.html

    Template Context:
        - request: FastAPI request object
        - user: User model instance with profile data
    """
    return templates.TemplateResponse(
        request,
        "auth/profile.html",
        {"user": user, "auth_enabled": auth_settings.auth_enabled},
    )


@router.get("/profile", response_class=HTMLResponse)
async def profile_page_alias(
    request: Request, user: User = Depends(get_current_active_user)
):
    """Alias route for user profile page.

    Provides access to profile page at /profile as an alternative to /auth/profile.
    This is primarily for convenience and accessibility testing.

    Args:
        request: FastAPI request object (injected)
        user: Authenticated active user (injected)

    Returns:
        HTMLResponse: Rendered profile.html template

    Raises:
        HTTPException: 401 if not authenticated or account inactive

    Template:
        src/web/templates/auth/profile.html

    Template Context:
        - request: FastAPI request object
        - user: User model instance with profile data
    """
    return templates.TemplateResponse(
        request,
        "auth/profile.html",
        {"user": user, "auth_enabled": auth_settings.auth_enabled},
    )


# ============================================================================
# Tag/Category Management Pages (Protected)
# ============================================================================


def _require_auth_unless_disabled(
    user: Optional[User] = Depends(get_current_user_or_none),
) -> Optional[User]:
    """Require an authenticated user, unless auth is disabled entirely.

    Mirrors the API-side anonymous-mode bypass so page routes stay consistent
    with the data endpoints they render: when ``AUTH_ENABLED=false`` the page
    is served to anyone, otherwise a valid session is still required.
    """
    if user or not auth_settings.auth_enabled:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/manage-categories", response_class=HTMLResponse)
async def manage_categories_page(
    request: Request, user: Optional[User] = Depends(_require_auth_unless_disabled)
):
    """Serve the category management page (accessible without auth when disabled)."""
    return templates.TemplateResponse(
        request,
        "manage_categories.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )


@router.get("/manage-tags", response_class=HTMLResponse)
async def manage_tags_page(
    request: Request, user: Optional[User] = Depends(_require_auth_unless_disabled)
):
    """Serve the tag management page (accessible without auth when disabled)."""
    return templates.TemplateResponse(
        request,
        "manage_tags.html",
        {"auth_enabled": auth_settings.auth_enabled},
    )


# ============================================================================
# Import/Export & Backup Management Pages
# ============================================================================


@router.get("/import-export", response_class=HTMLResponse)
async def import_export_page(request: Request):
    """Import/Export management page"""
    from src.web import app as web_app

    data_service = web_app.data_service
    prompts = data_service.load_prompts()
    categories = data_service.get_categories()
    tags = data_service.get_tags()

    # Calculate statistics
    total_prompts = len(prompts)
    favorite_prompts = sum(
        1 for p in prompts.values() if p.get("data", {}).get("favorite", False)
    )
    unique_categories = len(
        set(p.get("data", {}).get("category", "No category") for p in prompts.values())
    )
    all_tags = set()
    for p in prompts.values():
        all_tags.update(p.get("data", {}).get("tags", []))
    unique_tags = len(all_tags)

    return templates.TemplateResponse(
        request,
        "import_export.html",
        {
            "total_prompts": total_prompts,
            "favorite_prompts": favorite_prompts,
            "total_categories": unique_categories,
            "total_tags": unique_tags,
            "auth_enabled": auth_settings.auth_enabled,
        },
    )


@router.get("/backup-management", response_class=HTMLResponse)
async def backup_management_page(request: Request):
    """Backup management page"""
    from src.web import app as web_app

    stats = web_app.backup_service.get_backup_stats()

    return templates.TemplateResponse(
        request,
        "backup_management.html",
        {
            "backup_stats": stats,
            "auth_enabled": auth_settings.auth_enabled,
        },
    )


# ============================================================================
# Admin Pages (Protected)
# ============================================================================


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, admin: User = Depends(get_admin_user)):
    """Serve the user management page.

    This page is protected and requires admin role.
    Admins can view, edit, and manage all users.

    Args:
        request: FastAPI request object (injected)
        admin: Authenticated admin user (injected)

    Returns:
        HTMLResponse: Rendered users.html template

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin

    Template:
        src/web/templates/admin/users.html

    Template Context:
        - request: FastAPI request object
        - user: Admin user instance (for header/navigation)
    """
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {"user": admin, "auth_enabled": auth_settings.auth_enabled},
    )


@router.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions_page(request: Request, admin: User = Depends(get_admin_user)):
    """Serve the session management page.

    This page is protected and requires admin role.
    Admins can view and manage all active sessions.

    Args:
        request: FastAPI request object (injected)
        admin: Authenticated admin user (injected)

    Returns:
        HTMLResponse: Rendered sessions.html template

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin

    Template:
        src/web/templates/admin/sessions.html

    Template Context:
        - request: FastAPI request object
        - user: Admin user instance (for header/navigation)
    """
    return templates.TemplateResponse(
        request,
        "admin/sessions.html",
        {"user": admin, "auth_enabled": auth_settings.auth_enabled},
    )
