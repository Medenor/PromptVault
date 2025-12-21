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

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

from src.db.models.user import User
from src.web.dependencies.auth import (
    get_current_active_user,
    get_admin_user,
)
from src.web.utils.manifest import load_manifest, get_asset_path, is_production

# ============================================================================
# Router Configuration
# ============================================================================

router = APIRouter(tags=["Pages"])

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="src/web/templates")
templates.env.globals["load_manifest"] = load_manifest
templates.env.globals["get_asset_path"] = get_asset_path
templates.env.globals["is_production"] = is_production
templates.env.globals["is_dev"] = lambda: os.getenv("ENV", "production") == "development"
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

    Args:
        request: FastAPI request object (injected)

    Returns:
        HTMLResponse: Rendered login.html template

    Template:
        src/web/templates/auth/login.html
    """
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


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
        "auth/register.html",
        {"request": request}
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
        "auth/forgot_password.html",
        {"request": request}
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
        "auth/reset_password.html",
        {"request": request}
    )


# ============================================================================
# Authentication Pages (Protected)
# ============================================================================


@router.get("/auth/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    user: User = Depends(get_current_active_user)
):
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
        "auth/profile.html",
        {"request": request, "user": user}
    )


# ============================================================================
# Admin Pages (Protected)
# ============================================================================


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(
    request: Request,
    admin: User = Depends(get_admin_user)
):
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
        "admin/users.html",
        {"request": request, "user": admin}
    )


@router.get("/admin/sessions", response_class=HTMLResponse)
async def admin_sessions_page(
    request: Request,
    admin: User = Depends(get_admin_user)
):
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
        "admin/sessions.html",
        {"request": request, "user": admin}
    )
