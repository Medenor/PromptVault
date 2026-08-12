# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.config.auth_config import auth_settings
from src.services.backup_service_db import BackupService
from src.services.logging_service import logging_service
from src.services.prompt_data_service_db import PromptDataService
from src.services.prompt_import_export_service import PromptImportExportService
from src.web.dependencies.auth import has_valid_auth_cookie
from src.web.factory import create_app
from src.web.middleware_setup import configure_middleware
from src.web.models import FrontendLogEntry
from src.web.monitoring import ValidationMonitor
from src.web.routers.backup import init_backup_router
from src.web.routing_setup import (
    configure_routing,
)  # noqa: F401
from src.web.startup import register_lifecycle_events
from src.web.utils.manifest import get_asset_path, is_production, load_manifest
from src.web.utils.version import get_app_version

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================
# This FastAPI application integrates:
# 1. Authentication & Authorization System (JWT-based with ES256)
# 2. Rate Limiting Middleware (Redis-backed with slowapi)
# 3. API Routers (auth, admin, prompts)
# 4. Legacy prompt management endpoints (deprecated, see migration notes below)
#
# MIGRATION NOTES FOR DEVELOPERS:
# - New authentication system is now active at /api/auth/* endpoints
# - Protected endpoints require JWT access token in Authorization header
# - Admin endpoints require admin role (checked via JWT claims)
# - Rate limiting is enforced on all authentication endpoints
# - Legacy prompt routes (lines 478-1520) are DEPRECATED but kept for compatibility
# - Migrate to new prompt routes at /api/prompts/* which include:
#   * Authentication and authorization
#   * Ownership-based access control
#   * Public read with optional personalization
#
# AUTHENTICATION SYSTEM OVERVIEW:
# - JWT tokens use ES256 (ECDSA) algorithm for security
# - Access tokens: 15 minutes (configurable via AUTH_ACCESS_TOKEN_EXPIRE_MINUTES)
# - Refresh tokens: 7 days (configurable via AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
# - Session tracking with token family and reuse detection
# - Account lockout: 5 failed attempts, 15-minute lockout
# - Password policy: 12 chars min, complexity requirements
# - Rate limiting: Login (5/15min), Register (3/hour), Password Reset (3/hour)
#
# PROTECTED ROUTES:
# - /api/auth/me - Get current user (requires access token)
# - /api/auth/change-password - Change password (requires access token)
# - /api/auth/sessions - List sessions (requires access token)
# - /api/auth/sessions/{id} - Revoke session (requires access token)
# - /api/admin/* - All admin routes (requires admin role)
# - /api/prompts POST/PUT/DELETE - Write operations (requires authentication)
#
# PUBLIC ROUTES:
# - /api/auth/register - Register new user
# - /api/auth/login - Login with credentials
# - /api/auth/refresh - Refresh access token
# - /api/auth/logout - Logout (revoke session)
# - /api/auth/password-reset/request - Request password reset email
# - /api/auth/password-reset/confirm - Confirm password reset with token
# - /api/prompts GET - Read prompts (optional auth for personalization)
#
# API DOCUMENTATION:
# - OpenAPI docs: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - All endpoints include comprehensive documentation with examples
# ============================================================================

app = create_app()

data_service: PromptDataService | None = None
import_export_service: PromptImportExportService | None = None
backup_service: BackupService | None = None
validation_monitor: ValidationMonitor | None = None
logger = logging_service.get_logger(__name__)

configure_routing(app)
register_lifecycle_events(app)


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint for monitoring and load balancers.

    Returns:
        JSON response with status and timestamp
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PromptVault API",
    }


@app.get("/api/health")
async def api_health():
    """Health check endpoint for container monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "PromptVault API",
    }


@app.get("/api/validation/stats")
async def get_validation_stats():
    """Return validation monitoring snapshot."""
    if not validation_monitor:
        return JSONResponse(
            status_code=503,
            content={"error": "Validation monitoring not initialized"},
        )

    return JSONResponse(content=validation_monitor.snapshot())


FRONTEND_LOG_WINDOW = 60.0
FRONTEND_LOG_LIMIT = 10
frontend_log_rate: dict[str, deque[float]] = defaultdict(deque)

# Templates
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
templates.env.globals["app_version"] = get_app_version()


def _resolve_data_locations(
    override_file: str | None = None, override_dir: str | None = None
) -> tuple[str | None, str | None]:
    """
    Determine data file and directory locations, allowing environment overrides.

    Args:
        override_file (Optional[str]): Explicit data file path.
        override_dir (Optional[str]): Explicit data directory path.

    Returns:
        Tuple[Optional[str], Optional[str]]: Absolute paths for data file and directory.
    """
    data_file_env = override_file or os.getenv("PROMPTVAULT_DATA_FILE")
    data_dir_env = override_dir or os.getenv("PROMPTVAULT_DATA_DIR")

    data_file: str | None = None
    data_dir: str | None = None

    if data_file_env:
        data_file = os.path.abspath(data_file_env.strip())
        if not data_dir_env:
            data_dir_env = os.path.dirname(data_file)

    if data_dir_env:
        data_dir = os.path.abspath(data_dir_env.strip())
        if not data_file:
            data_file = os.path.join(data_dir, "prompts_data.json")

    return data_file, data_dir


def _warn_if_backup_dir_database_mismatch(backups_dir: str) -> None:
    """Warn when PROMPTVAULT_DATA_DIR and DATABASE_URL point at unrelated trees.

    Backup files (under PROMPTVAULT_DATA_DIR/backups) and backup metadata rows
    (in the DATABASE_URL database) are written to independently-configured
    locations. If they drift apart across restarts (e.g. DATABASE_URL changed
    to point at a different SQLite file while PROMPTVAULT_DATA_DIR stayed the
    same), existing backups' files survive on disk but their DB rows vanish,
    causing restores to fail with a spurious "backup file not found" error.
    This is a best-effort sanity check, not a hard failure, since the two
    settings are legitimately independent for non-SQLite databases.
    """
    from src.db.config import db_settings

    if not db_settings.is_sqlite:
        return

    db_url = db_settings.DATABASE_URL
    if not db_url.startswith("sqlite:///") or ":memory:" in db_url:
        return

    db_path = db_url.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    data_dir = os.path.dirname(os.path.abspath(backups_dir))
    db_dir = os.path.dirname(db_path)

    if os.path.abspath(db_dir) != os.path.abspath(data_dir):
        logger.warning(
            "PROMPTVAULT_DATA_DIR and DATABASE_URL point at different "
            f"directories (backups dir: {data_dir}, database dir: {db_dir}). "
            "Backup files and their database records may drift out of sync "
            "across restarts, causing restores to fail with 'backup file not "
            "found'. Ensure both settings are derived from the same source."
        )


def configure_services(
    data_file: str | None = None, data_dir: str | None = None
) -> None:
    """
    Initialize global service instances, honoring optional overrides.

    Args:
        data_file (Optional[str]): Explicit data file path.
        data_dir (Optional[str]): Explicit data directory path.
    """
    global data_service, import_export_service, backup_service, validation_monitor

    resolved_file, resolved_dir = _resolve_data_locations(data_file, data_dir)

    # Initialize data service without data_file_path (database uses DATABASE_URL env var)
    data_service = PromptDataService()
    # Handle database service which may not have a data_file attribute
    if hasattr(data_service, "data_file") and data_service.data_file:
        data_dir_base = resolved_dir or os.path.dirname(data_service.data_file)
    else:
        # For database service, use resolved_dir or default to "data"
        data_dir_base = resolved_dir or "data"
    logs_dir = os.path.join(data_dir_base, "logs")
    logging_service.configure_logging(log_dir=logs_dir)
    import_export_service = PromptImportExportService()
    backup_service = BackupService(resolved_dir)
    _warn_if_backup_dir_database_mismatch(backup_service.backups_dir)

    # The backup router caches its own module-level service reference at
    # wiring time (see init_backup_router) rather than reading this module's
    # `backup_service` global per-request. Without re-syncing it here, a
    # caller that re-runs configure_services() with a different data_dir
    # (e.g. test fixtures isolating to a temp directory) leaves the router
    # bound to whatever backup_service existed at the first import-time
    # call — which previously caused test-created backups to be written to
    # the real, non-isolated default data directory. Only the service
    # reference is re-synced; validation_monitor/record_validation_event
    # wiring is set up once at first import and does not vary per call.
    from src.web.routers import backup as backup_router_module

    backup_router_module._backup_service = backup_service

    # Initialize validation monitor using the data directory for persistence
    logs_base = resolved_dir or "data"
    logs_dir = os.path.join(logs_base, "logs")
    metrics_file = os.path.join(logs_dir, "validation_metrics.json")
    validation_monitor = ValidationMonitor(metrics_file)


# Initialize services using environment configuration (if provided)
configure_services()


def _is_frontend_rate_limited(client_ip: str) -> bool:
    """Return True if the client has exceeded telemetry limits."""
    now = time.monotonic()
    bucket = frontend_log_rate[client_ip]
    while bucket and now - bucket[0] > FRONTEND_LOG_WINDOW:
        bucket.popleft()
    if len(bucket) >= FRONTEND_LOG_LIMIT:
        return True
    bucket.append(now)
    return False


def record_validation_event(
    endpoint: str,
    success: bool,
    errors: list[str] | None = None,
    client: str | None = None,
) -> None:
    """
    Record a validation success or failure for monitoring.

    Args:
        endpoint: API path identifier.
        success: Whether validation passed.
        errors: Optional list of error strings.
        client: Optional client identification (ip/user-agent).
    """
    if not validation_monitor:
        return

    try:
        validation_monitor.record_event(
            endpoint=endpoint, success=success, errors=errors, client=client
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "Validation monitor failed to record event",
            extra={
                "event": "validation.monitor.error",
                "action": endpoint,
                "resource_id": endpoint,
                "status": "failure",
            },
            exc_info=exc,
        )


init_backup_router(backup_service, validation_monitor, record_validation_event)

# Security headers, rate limiting, static mounts, request logging, and
# exception/validation handlers are wired up together here since several of
# them (the validation handlers) depend on record_validation_event above.
configure_middleware(app, record_validation_event)


def _sanitize_text(value: str | None, max_length: int) -> str | None:
    if not value:
        return None
    return value.strip()[:max_length]


@app.post("/api/logs/frontend")
async def log_frontend_error(entry: FrontendLogEntry, request: Request):
    """Accept client-side error reports with basic rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    if _is_frontend_rate_limited(client_ip):
        return JSONResponse(
            status_code=429,
            content={"error": "Too many error reports. Please slow down."},
        )

    context_payload: dict[str, Any] = {}
    for key, value in entry.context.items():
        if isinstance(value, str):
            context_payload[key] = value[:200]
        else:
            context_payload[key] = value

    logger.warning(
        "Frontend error reported",
        extra={
            "event": "frontend.error",
            "component": entry.component,
            "action": entry.action,
            "severity": entry.severity,
            "error_message": _sanitize_text(entry.message, 500),
            "stacktrace": _sanitize_text(entry.stack, 2000),
            "url": _sanitize_text(entry.url, 500),
            "client": client_ip,
            "context": context_payload,
        },
    )
    return {"success": True}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page - redirects to login if not authenticated, otherwise shows prompts.

    This endpoint checks for authentication via the Authorization header or cookies.
    Unauthenticated users are redirected to /auth/login.
    Authenticated users see the main prompt management interface.

    Args:
        request: FastAPI request object

    Returns:
        RedirectResponse to /auth/login if not authenticated
        HTMLResponse with index.html if authenticated
    """
    from fastapi.responses import RedirectResponse

    # In anonymous mode, serve the app directly without requiring authentication.
    if not auth_settings.auth_enabled:
        assert data_service is not None, "configure_services() must run before requests"
        prompts = data_service.load_prompts()
        categories = data_service.get_categories()
        tags = data_service.get_tags()

        return templates.TemplateResponse(
            request,
            "index.html",
            {
                "prompts": prompts,
                "categories": categories,
                "tags": tags,
                "auth_enabled": False,
            },
        )

    # Validate the access token cookie's signature/expiration statelessly (no
    # DB lookup). This catches the common cases (missing/expired/tampered
    # cookie) before any HTML is sent, avoiding the redirect flash. It does
    # NOT catch admin-revoked-but-unexpired sessions — that requires a DB
    # lookup and is handled by the client-side /api/auth/me check instead
    # (see the inline skeleton in index.html), preserving the privacy
    # guarantee that revoked sessions never see prompt data.
    if not has_valid_auth_cookie(request):
        # No/invalid authentication, redirect to login.
        # Mark the redirect as non-cacheable so that browser history
        # navigation (back/forward) always re-evaluates auth state and
        # does not replay a stale redirect to the login page.
        redirect = RedirectResponse(url="/auth/login", status_code=302)
        redirect.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        redirect.headers["Pragma"] = "no-cache"
        redirect.headers["Expires"] = "0"
        # Clear the stale/expired cookie. Without this, an expired
        # access_token cookie keeps getting resent, and the login page's
        # bfcache guard (redirectIfAuthenticated in auth.ts, which trusts
        # localStorage's access_token independently of cookie validity)
        # bounces the user straight back to "/", creating a redirect loop.
        redirect.delete_cookie(key="access_token", path="/")
        return redirect

    # User is authenticated, show the main app. The client-side /api/auth/me
    # check (see index.ts checkAdminAccess) still runs to catch
    # admin-revoked-but-unexpired sessions; until it resolves, the prompt
    # grid shows a skeleton placeholder rather than real data.
    assert data_service is not None, "configure_services() must run before requests"
    prompts = data_service.load_prompts()
    categories = data_service.get_categories()
    tags = data_service.get_tags()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "prompts": prompts,
            "categories": categories,
            "tags": tags,
            "auth_enabled": True,
        },
    )
