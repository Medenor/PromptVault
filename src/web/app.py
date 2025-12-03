# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse as FastAPIJSONResponse
from pydantic import ValidationError
import pydantic_core
import json
import os
import time
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Deque, Any
from collections import defaultdict, deque

from src.services.prompt_data_service_db import PromptDataService
from src.services.prompt_filter_service import PromptFilterService
from src.services.prompt_versioning_service import PromptVersioningService
from src.services.prompt_import_export_service import PromptImportExportService
from src.services.backup_service_db import BackupService
from src.services.exceptions import PromptVaultException
from src.services.logging_service import logging_service
from src.web.models import (
    PromptCreateRequest,
    PromptUpdateRequest,
    ExportRequest,
    ImportRequest,
    BackupCreateRequest,
    BackupCleanupRequest,
    BackupCompressRequest,
    VersionRevertRequest,
    FrontendLogEntry,
    BulkDeleteRequest,
    ExportFormat,
    ImportMode,
)
from src.web.validators import (
    sanitize_filename,
    validate_upload_file,
    create_secure_temp_file,
    get_file_extension_from_format,
)
from src.web.monitoring import ValidationMonitor
from src.web.routers import auth_router, admin_router, prompts_router
from src.web.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

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

app = FastAPI(
    title="PromptVault API",
    version="0.2.0",
    description="""
    PromptVault API with comprehensive authentication and authorization.

    Features:
    - JWT-based authentication (ES256 algorithm)
    - Role-based access control (viewer, editor, admin)
    - Session management and tracking
    - Password reset with secure tokens
    - Rate limiting on sensitive endpoints
    - Ownership-based authorization for prompts

    Security:
    - All passwords hashed with Argon2id
    - Tokens signed with ECDSA (ES256)
    - Account lockout protection
    - Token family tracking and reuse detection
    - Redis-backed rate limiting

    Authentication:
    - Include access token in Authorization header: "Bearer <token>"
    - Refresh tokens using /api/auth/refresh endpoint
    - Session limit: 5 concurrent sessions per user
    """,
    openapi_tags=[
        {
            "name": "Authentication",
            "description": "User authentication, registration, and session management",
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints for user and system management (admin role required)",
        },
        {
            "name": "Prompts",
            "description": "Prompt CRUD operations with authentication and authorization",
        },
        {
            "name": "Legacy",
            "description": "Deprecated endpoints - migrate to /api/prompts routes",
        },
    ],
)

validation_monitor: Optional[ValidationMonitor] = None

# ============================================================================
# RATE LIMITING SETUP
# ============================================================================
# Initialize rate limiter with Redis backend (falls back to in-memory if Redis unavailable)
# Rate limits are enforced per IP address or authenticated user ID
# Limits are configured in AuthConfig via environment variables
app.state.limiter = limiter

# Register rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

logger = logging_service.get_logger(__name__)
logger.info("Rate limiting initialized successfully")

# ============================================================================
# API ROUTERS REGISTRATION
# ============================================================================
# Register all API routers with appropriate prefixes:
# - /api/auth - Authentication endpoints (public + protected)
# - /api/admin - Admin endpoints (admin role required)
# - /api/prompts - Prompt CRUD with authentication
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")

logger.info("API routers registered: /api/auth, /api/admin, /api/prompts")
audit_logger = logging_service.get_audit_logger()
FRONTEND_LOG_WINDOW = 60.0
FRONTEND_LOG_LIMIT = 10
frontend_log_rate: Dict[str, Deque[float]] = defaultdict(deque)

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/web/templates")

def _resolve_data_locations(
    override_file: Optional[str] = None, override_dir: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
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

    data_file: Optional[str] = None
    data_dir: Optional[str] = None

    if data_file_env:
        data_file = os.path.abspath(data_file_env.strip())
        if not data_dir_env:
            data_dir_env = os.path.dirname(data_file)

    if data_dir_env:
        data_dir = os.path.abspath(data_dir_env.strip())
        if not data_file:
            data_file = os.path.join(data_dir, "prompts_data.json")

    return data_file, data_dir


def configure_services(
    data_file: Optional[str] = None, data_dir: Optional[str] = None
) -> None:
    """
    Initialize global service instances, honoring optional overrides.

    Args:
        data_file (Optional[str]): Explicit data file path.
        data_dir (Optional[str]): Explicit data directory path.
    """
    global data_service, filter_service, versioning_service, import_export_service, backup_service, validation_monitor

    resolved_file, resolved_dir = _resolve_data_locations(data_file, data_dir)

    # Initialize data service without data_file_path (database uses DATABASE_URL env var)
    data_service = PromptDataService()
    # Handle database service which may not have a data_file attribute
    if hasattr(data_service, 'data_file') and data_service.data_file:
        data_dir_base = resolved_dir or os.path.dirname(data_service.data_file)
    else:
        # For database service, use resolved_dir or default to "data"
        data_dir_base = resolved_dir or "data"
    logs_dir = os.path.join(data_dir_base, "logs")
    logging_service.configure_logging(log_dir=logs_dir)
    filter_service = PromptFilterService()
    versioning_service = PromptVersioningService()
    import_export_service = PromptImportExportService()
    backup_service = BackupService(resolved_dir)

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
    errors: Optional[List[str]] = None,
    client: Optional[str] = None,
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


@app.exception_handler(PromptVaultException)
async def promptvault_exception_handler(
    request: Request, exc: PromptVaultException
) -> JSONResponse:
    """Translate PromptVaultException into structured API responses."""
    log_extra = {
        "event": "api.error",
        "action": str(request.url.path),
        "resource_id": str(request.url.path),
        **exc.context,
    }
    log_method = getattr(logger, exc.log_level, logger.error)
    log_method(exc.message, extra=log_extra)

    if exc.context.get("backup_id"):
        audit_logger.error(
            "Audit: service failure",
            extra={
                "event": "audit.error",
                "resource_id": exc.context.get("backup_id"),
                "status": "failure",
            },
        )

    response_payload = exc.to_dict()
    request_id = logging_service.get_request_id()
    response_payload["request_id"] = request_id
    response = JSONResponse(status_code=exc.http_status, content=response_payload)
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all exception handler to ensure JSON responses."""
    logger.exception(
        "Unhandled server error",
        extra={"event": "api.error", "action": str(request.url.path)},
    )
    response_payload = {
        "error": "Internal server error.",
        "request_id": logging_service.get_request_id(),
    }
    response = JSONResponse(status_code=500, content=response_payload)
    request_id = logging_service.get_request_id()
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def _sanitize_text(value: Optional[str], max_length: int) -> Optional[str]:
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

    context_payload: Dict[str, Any] = {}
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


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Attach request IDs and emit structured request logs."""
    request_id = request.headers.get("X-Request-ID") or logging_service.generate_request_id()
    actor = (
        request.headers.get("X-PromptVault-Actor")
        or request.headers.get("X-Forwarded-User")
        or "anonymous"
    )
    start_time = time.perf_counter()
    with logging_service.request_context(request_id=request_id, actor=actor):
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "Unhandled exception during request",
                extra={
                    "event": "http.request.error",
                    "action": f"{request.method} {request.url.path}",
                    "resource_id": str(request.url.path),
                    "status": 500,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        logger.info(
            "Request handled",
            extra={
                "event": "http.request",
                "action": f"{request.method} {request.url.path}",
                "resource_id": str(request.url.path),
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            },
        )
        response.headers["X-Request-ID"] = request_id
        return response


# Custom validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with user-friendly messages."""
    errors = exc.errors()
    error_messages = []
    sanitized_errors = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

        # Sanitize error dict for JSON serialization
        sanitized_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": str(error.get("input"))[:100] if error.get("input") else None,
        }
        sanitized_errors.append(sanitized_error)

    record_validation_event(
        endpoint=str(request.url.path),
        success=False,
        errors=error_messages,
        client=request.client.host if request.client else None,
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": error_messages,
            "errors": sanitized_errors,
        },
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic ValidationError raised in endpoint functions."""
    errors = exc.errors()
    error_messages = []
    sanitized_errors = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

        # Sanitize error dict for JSON serialization
        sanitized_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": str(error.get("input"))[:100] if error.get("input") else None,
        }
        sanitized_errors.append(sanitized_error)

    record_validation_event(
        endpoint=str(request.url.path),
        success=False,
        errors=error_messages,
        client=request.client.host if request.client else None,
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": error_messages,
            "errors": sanitized_errors,
        },
    )


@app.exception_handler(pydantic_core.ValidationError)
async def pydantic_core_validation_exception_handler(
    request: Request, exc: pydantic_core.ValidationError
):
    """Handle pydantic_core ValidationError raised in endpoint functions."""
    errors = exc.errors()
    error_messages = []
    sanitized_errors = []

    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

        # Sanitize error dict for JSON serialization
        sanitized_error = {
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
            "input": str(error.get("input"))[:100] if error.get("input") else None,
        }
        sanitized_errors.append(sanitized_error)

    record_validation_event(
        endpoint=str(request.url.path),
        success=False,
        errors=error_messages,
        client=request.client.host if request.client else None,
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "details": error_messages,
            "errors": sanitized_errors,
        },
    )


def _parse_tags_field(tags: str) -> List[str]:
    """
    Normalize a comma-delimited tag string into a list with trimmed entries.

    Args:
        tags (str): Raw tag field from the form submission.

    Returns:
        List[str]: Cleaned tags with whitespace removed and empty values filtered out.
    """
    if not tags:
        return []
    normalized_tags = []
    for tag in tags.split(","):
        cleaned = tag.strip()
        if cleaned:
            normalized_tags.append(cleaned)
    return normalized_tags


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page"""
    prompts = data_service.load_prompts()
    categories = data_service.get_categories()
    tags = data_service.get_tags()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "prompts": prompts,
            "categories": categories,
            "tags": tags,
        },
    )


# ============================================================================
# LEGACY PROMPT ENDPOINTS (DEPRECATED - REMOVED)
# ============================================================================
# The following legacy endpoints have been REMOVED and replaced by the new
# authentication-aware routes registered via routers above.
#
# OLD ROUTES (removed):
# - GET    /api/prompts             -> Now handled by prompts_router with optional auth
# - POST   /api/prompts             -> Now handled by prompts_router with required auth
# - GET    /api/prompts/search      -> Now handled by prompts_router with optional auth
# - GET    /api/prompts/{id}        -> Now handled by prompts_router with optional auth
# - PUT    /api/prompts/{id}        -> Now handled by prompts_router with auth + ownership
# - DELETE /api/prompts/{id}        -> Now handled by prompts_router with auth + ownership
# - PUT    /api/prompts/{id}/favorite -> Now handled by prompts_router with auth + ownership
# - DELETE /api/prompts/bulk       -> Now handled by prompts_router with admin role
#
# NEW FEATURES:
# - Authentication for write operations
# - Ownership-based authorization (owner or admin can modify)
# - Public read with optional personalization when authenticated
# - Proper audit logging for all operations
# - Role-based access control (RBAC) for admin operations
#
# The old implementations are commented out below for reference.
# ============================================================================


# LEGACY PROMPT ROUTES - Removed and replaced by new authenticated routes
# The old implementations below have been commented out.
# All /api/prompts/* routes are now handled by the prompts_router (see routers/prompts.py)
#
# Key improvements in new implementation:
# 1. Authentication: Users must be authenticated for write operations
# 2. Authorization: Ownership checks - only owners and admins can modify prompts
# 3. Database: Uses proper ORM models (Prompt, Category, Tag) instead of JSON files
# 4. Security: Proper audit logging, rate limiting, and error handling
# 5. RBAC: Role-based access control for admin operations
#
# Migration guide for frontend developers:
# - All read operations (GET) remain public and work the same way
# - Write operations (POST, PUT, DELETE) now require Authorization header
# - Response format remains compatible for backward compatibility
# - Add "Authorization: Bearer <access_token>" header to authenticated requests
#
# Example authenticated request:
# ```
# POST /api/prompts
# Authorization: Bearer eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...
# Content-Type: application/x-www-form-urlencoded
#
# title=My Prompt&prompt=Content here&category=Test&tags=tag1,tag2
# ```


@app.get("/api/categories")
async def get_categories():
    """Get all categories"""
    categories = data_service.get_categories()
    return {"categories": categories}


@app.get("/api/tags")
async def get_tags():
    """Get all tags with usage counts"""
    tags_with_counts = data_service.get_tags_with_counts()
    return {"tags": tags_with_counts}


# Import/Export endpoints
@app.get("/import-export", response_class=HTMLResponse)
async def import_export_page(request: Request):
    """Import/Export management page"""
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
        "import_export.html",
        {
            "request": request,
            "total_prompts": total_prompts,
            "favorite_prompts": favorite_prompts,
            "total_categories": unique_categories,
            "total_tags": unique_tags,
        },
    )


@app.post("/api/export")
async def export_prompts(
    format: str = Form(...),
    filename: str = Form("promptvault_export"),
    include_favorites: bool = Form(False),
    include_metadata: bool = Form(True),
):
    """Export prompts in specified format with validation and secure file handling."""
    try:
        # Validate format enum first
        try:
            format_enum = ExportFormat(format.lower())
        except ValueError:
            record_validation_event(
                endpoint="/api/export",
                success=False,
                errors=[f"Invalid format '{format}'"],
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation failed",
                    "details": [f"Invalid format '{format}'. Must be one of: csv, markdown, json"],
                },
            )

        # Validate using Pydantic model
        validated_data = ExportRequest(
            format=format_enum,
            filename=filename,
            include_favorites=include_favorites,
            include_metadata=include_metadata,
        )

        prompts = data_service.load_prompts()

        # Filter prompts if needed
        if validated_data.include_favorites:
            prompts = {
                k: v
                for k, v in prompts.items()
                if v.get("data", {}).get("favorite", False)
            }

        # Convert to list format for export service
        prompt_list = [(int(k), v) for k, v in prompts.items()]

        # Sanitize filename and add proper extension
        safe_filename = sanitize_filename(validated_data.filename)
        file_extension = get_file_extension_from_format(validated_data.format.value)
        final_filename = f"{safe_filename}{file_extension}"

        # Create secure temporary file
        temp_file = create_secure_temp_file(final_filename)

        success = False
        if validated_data.format == ExportFormat.CSV:
            success = import_export_service.export_to_csv(temp_file, prompt_list)
        elif validated_data.format == ExportFormat.MARKDOWN:
            success = import_export_service.export_to_markdown(temp_file, prompt_list)
        elif validated_data.format == ExportFormat.JSON:
            # Export as JSON
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_prompts": len(prompt_list),
                "prompts": {k: v for k, v in prompt_list},
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            success = True

        if success:
            logging_service.log_audit_event(
                action="export.prompts",
                resource_type="export",
                resource_id=final_filename,
                format=validated_data.format.value,
                prompt_count=len(prompt_list),
                include_favorites=validated_data.include_favorites,
                include_metadata=validated_data.include_metadata,
            )
            # Return file for download
            record_validation_event(endpoint="/api/export", success=True)
            return FileResponse(
                temp_file, media_type="application/octet-stream", filename=final_filename
            )
        else:
            # Clean up temp file on failure
            if os.path.exists(temp_file):
                os.remove(temp_file)
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to export in {validated_data.format.value} format"},
            )

    except ValidationError as e:
        record_validation_event(
            endpoint="/api/export",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )
    except Exception as e:
        # Clean up temp file on error
        if "temp_file" in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(
            status_code=500, content={"error": f"Export failed: {str(e)}"}
        )


@app.post("/api/import")
async def import_prompts(
    file: UploadFile = File(...),
    mode: str = Form("append"),
    validate_data: bool = Form(True),
):
    """Import prompts from uploaded file with comprehensive security validation."""
    temp_file_path = None
    try:
        # Validate request parameters
        validated_params = ImportRequest(
            mode=ImportMode(mode.lower()),
            validate_data=validate_data,
        )

        # Comprehensive file upload validation
        is_valid, error_message = await validate_upload_file(file)
        if not is_valid:
            record_validation_event(
                endpoint="/api/import",
                success=False,
                errors=[error_message],
            )
            return JSONResponse(
                status_code=400,
                content={"error": error_message},
            )

        # Create secure temporary file
        temp_file_path = create_secure_temp_file(file.filename)

        # Write uploaded content to secure temp file
        content = await file.read()
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)

        imported_prompts = []

        # Determine format from filename
        filename = file.filename.lower()
        if filename.endswith(".csv"):
            imported_prompts = import_export_service.import_from_csv(temp_file_path)
        elif filename.endswith((".md", ".markdown")):
            imported_prompts = import_export_service.import_from_markdown(temp_file_path)
        elif filename.endswith(".json"):
            # Import from JSON
            with open(temp_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "prompts" in data:
                    # Handle exported JSON format
                    for prompt_id, prompt_info in data["prompts"].items():
                        imported_prompts.append(prompt_info["data"])
                else:
                    # Handle direct JSON format - ensure it's a list
                    if isinstance(data, list):
                        imported_prompts = data
                    elif isinstance(data, dict):
                        # Single prompt object, wrap in list
                        imported_prompts = [data]
                    else:
                        raise ValueError(
                            "Invalid JSON format: expected array or object"
                        )

        # Validate if requested
        if validated_params.validate_data:
            valid_prompts = []
            for prompt in imported_prompts:
                if prompt.get("title") and prompt.get("prompt"):
                    valid_prompts.append(prompt)
            imported_prompts = valid_prompts

        # Import based on mode
        added_count = 0
        if validated_params.mode == ImportMode.REPLACE:
            # Create automatic backup before replacing all data
            backup_id = backup_service.create_backup("pre_replace_import")
            if backup_id:
                audit_logger.info(
                    "Automatic backup created before replace import",
                    extra={
                        "event": "backup.auto",
                        "action": "backup_before_replace_import",
                        "resource_id": "import",
                        "backup_id": backup_id,
                    },
                )

            # Clear existing data
            data_service.clear_all_prompts()

        for prompt_data in imported_prompts:
            if validated_params.mode == ImportMode.MERGE:
                # Check if prompt with same title exists
                existing_prompts = data_service.load_prompts()
                exists = any(
                    p.get("data", {}).get("title") == prompt_data.get("title")
                    for p in existing_prompts.values()
                )
                if not exists:
                    data_service.create_prompt(prompt_data)
                    added_count += 1
            elif validated_params.mode == ImportMode.REPLACE:
                # Replace mode: add all prompts (existing data already cleared)
                data_service.create_prompt(prompt_data)
                added_count += 1
            else:
                # Append mode: add all prompts
                data_service.create_prompt(prompt_data)
                added_count += 1

        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        record_validation_event(
            endpoint="/api/import",
            success=True,
        )
        logging_service.log_audit_event(
            action="import.prompts",
            resource_type="import",
            resource_id="import",
            imported_count=len(imported_prompts),
            added_count=added_count,
            mode=validated_params.mode.value,
        )

        return JSONResponse(
            content={
                "success": True,
                "imported_count": len(imported_prompts),
                "added_count": added_count,
                "mode": validated_params.mode.value,
            }
        )

    except ValidationError as e:
        # Clean up temp file on validation error
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        record_validation_event(
            endpoint="/api/import",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )
    except Exception as e:
        # Clean up temp file on error
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return JSONResponse(
            status_code=500, content={"error": f"Import failed: {str(e)}"}
        )


@app.get("/api/import-export/stats")
async def get_import_export_stats():
    """Get current import/export statistics"""
    try:
        prompts = data_service.load_prompts()
        categories = data_service.get_categories()
        tags = data_service.get_tags()

        # Calculate statistics - handle both wrapped and unwrapped structures
        total_prompts = len(prompts)
        favorite_prompts = 0
        unique_categories = set()
        all_tags = set()

        for prompt_info in prompts.values():
            # Handle both wrapped (with 'data') and unwrapped structures
            if "data" in prompt_info:
                prompt_data = prompt_info["data"]
            else:
                prompt_data = prompt_info

            # Count favorites
            if prompt_data.get("favorite", False):
                favorite_prompts += 1

            # Collect categories
            unique_categories.add(prompt_data.get("category", "No category"))

            # Collect tags
            prompt_tags = prompt_data.get("tags", [])
            if isinstance(prompt_tags, list):
                all_tags.update(prompt_tags)

        return JSONResponse(
            content={
                "total_prompts": total_prompts,
                "favorite_prompts": favorite_prompts,
                "total_categories": len(unique_categories),
                "total_tags": len(all_tags),
                "categories": list(unique_categories),
                "tags": list(all_tags),
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"Failed to get statistics: {str(e)}"}
        )


# Backup Management Endpoints
@app.get("/backup-management", response_class=HTMLResponse)
async def backup_management_page(request: Request):
    """Backup management page"""
    # Get backup statistics
    stats = backup_service.get_backup_stats()

    return templates.TemplateResponse(
        "backup_management.html", {"request": request, "backup_stats": stats}
    )


@app.get("/api/backups")
async def get_backups():
    """Get list of all backups"""
    backups = backup_service.list_backups()
    return {"backups": backups}


@app.post("/api/backups")
async def create_manual_backup(name: str = Form(None)):
    """Create a manual backup with validation."""
    try:
        # Validate using Pydantic model
        validated_data = BackupCreateRequest(name=name)

        backup_id = backup_service.create_backup(validated_data.name)
        if backup_id:
            record_validation_event(
                endpoint="/api/backups",
                success=True,
            )
            return {"success": True, "backup_id": backup_id}
        else:
            return JSONResponse(
                status_code=500, content={"error": "Failed to create backup"}
            )

    except ValidationError as e:
        record_validation_event(
            endpoint="/api/backups",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )


@app.post("/api/backups/{backup_id}/restore")
async def restore_backup(backup_id: str):
    """Restore from a specific backup."""
    # Note: backup_id validation happens in service layer via _resolve_backup_path
    success = backup_service.restore_backup(backup_id)
    if success:
        return {"success": True}
    else:
        return JSONResponse(
            status_code=500, content={"error": "Failed to restore backup"}
        )


@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a specific backup."""
    try:
        backup_info = backup_service.get_backup_info(backup_id)
        deleted = backup_service.delete_backup(backup_id)
        if deleted:
            return {"success": True}

        if backup_info:
            return JSONResponse(
                status_code=500, content={"error": "Failed to delete backup"}
            )
        return JSONResponse(status_code=404, content={"error": "Backup not found"})

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"Failed to delete backup: {str(e)}"}
        )


@app.post("/api/backups/cleanup")
async def cleanup_backups(retention_days: int = Form(30)):
    """Clean up old backups with validation."""
    try:
        # Validate using Pydantic model
        validated_data = BackupCleanupRequest(retention_days=retention_days)

        removed_count = backup_service.cleanup_old_backups(validated_data.retention_days)
        record_validation_event(
            endpoint="/api/backups/cleanup",
            success=True,
        )
        return {"success": True, "removed_count": removed_count}

    except ValidationError as e:
        record_validation_event(
            endpoint="/api/backups/cleanup",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )


@app.post("/api/backups/compress")
async def compress_backups(days_threshold: int = Form(7)):
    """Compress old backups with validation."""
    try:
        # Validate using Pydantic model
        validated_data = BackupCompressRequest(days_threshold=days_threshold)

        compressed_count = backup_service.compress_old_backups(validated_data.days_threshold)
        record_validation_event(
            endpoint="/api/backups/compress",
            success=True,
        )
        return {"success": True, "compressed_count": compressed_count}

    except ValidationError as e:
        record_validation_event(
            endpoint="/api/backups/compress",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )


@app.get("/api/backups/stats")
async def get_backup_stats():
    """Get backup statistics"""
    stats = backup_service.get_backup_stats()
    return stats


@app.get("/api/validation/stats")
async def get_validation_stats():
    """Return validation monitoring snapshot."""
    if not validation_monitor:
        return JSONResponse(
            status_code=503,
            content={"error": "Validation monitoring not initialized"},
        )

    return JSONResponse(content=validation_monitor.snapshot())


# Version Control Endpoints
@app.get("/api/prompts/{prompt_id}/versions")
async def get_version_history(prompt_id: str):
    """Get version history for a specific prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    # Sort by timestamp (newest first)
    sorted_versions = sorted(
        versions, key=lambda v: v.get("timestamp", ""), reverse=True
    )

    # Return version metadata without full data to reduce payload
    version_list = []
    for version in sorted_versions:
        version_list.append(
            {
                "version_id": version.get("version_id"),
                "timestamp": version.get("timestamp"),
                "author": version.get("author"),
                "message": version.get("message"),
                "parents": version.get("parents", []),
            }
        )

    return JSONResponse(content={"versions": version_list})


@app.get("/api/prompts/{prompt_id}/versions/compare")
async def compare_versions(prompt_id: str, v1: str = None, v2: str = None):
    """Compare two versions of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    if not v1 or not v2:
        return JSONResponse(
            status_code=400,
            content={"error": "Both v1 and v2 version IDs are required"},
        )

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    # Find both versions
    version1 = None
    version2 = None
    for version in versions:
        if version.get("version_id") == v1:
            version1 = version
        if version.get("version_id") == v2:
            version2 = version

    if not version1 or not version2:
        return JSONResponse(
            status_code=404, content={"error": "One or both versions not found"}
        )

    # Compare the data
    data1 = version1.get("data", {})
    data2 = version2.get("data", {})

    diff = {"v1_id": v1, "v2_id": v2, "changes": {}}

    # Compare each field
    fields = ["title", "prompt", "category", "tags", "note"]
    for field in fields:
        val1 = data1.get(field)
        val2 = data2.get(field)
        if val1 != val2:
            diff["changes"][field] = {"old": val1, "new": val2}

    return JSONResponse(content=diff)


@app.get("/api/prompts/{prompt_id}/versions/{version_id}")
async def get_specific_version(prompt_id: str, version_id: str):
    """Get a specific version of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    # Find the specific version
    for version in versions:
        if version.get("version_id") == version_id:
            return JSONResponse(content=version)

    return JSONResponse(status_code=404, content={"error": "Version not found"})


@app.post("/api/prompts/{prompt_id}/versions/{version_id}/revert")
async def revert_to_version(
    prompt_id: str,
    version_id: str,
    commit_message: str = Form("Revert to previous version"),
):
    """Revert a prompt to a specific version with validation."""
    try:
        # Validate commit message
        validated_data = VersionRevertRequest(commit_message=commit_message)

        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})
    except ValidationError as e:
        record_validation_event(
            endpoint="/api/prompts/version/revert",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    # Find the version to revert to
    version_to_revert = None
    for version in versions:
        if version.get("version_id") == version_id:
            version_to_revert = version
            break

    if not version_to_revert:
        return JSONResponse(status_code=404, content={"error": "Version not found"})

    # Get the data from the version to revert to
    reverted_data = version_to_revert.get("data", {}).copy()

    # Create a new version with the reverted data
    success = data_service.revert_prompt_to_version(
        prompt_id_int, reverted_data, validated_data.commit_message
    )

    if success:
        new_versions = data_service.get_prompt_versions(prompt_id_int)
        new_version_id = new_versions[-1].get("version_id") if new_versions else None
        record_validation_event(
            endpoint="/api/prompts/version/revert",
            success=True,
        )
        return JSONResponse(
            content={
                "success": True,
                "message": f"Reverted to version {version_id}",
                "new_version_id": new_version_id,
            }
        )
    else:
        return JSONResponse(
            status_code=500, content={"error": "Failed to revert version"}
        )
