# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Middleware, static mounts, and exception handler wiring.

Split out of `app.py` so security headers, rate limiting, request logging,
and error translation can be reasoned about independently from routing
(`routing_setup.py`) and app construction (`factory.py`).
"""

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import pydantic_core
from slowapi.errors import RateLimitExceeded

from src.services.exceptions import PromptVaultException
from src.services.logging_service import logging_service
from src.web.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from src.web.middleware.security_headers import SecurityHeadersMiddleware

logger = logging_service.get_logger(__name__)
audit_logger = logging_service.get_audit_logger()


def _init_jwt_service_for_logging():
    """Initialize a JWTService instance used only for actor extraction in
    the request logging middleware. Returns None if initialization fails
    (e.g. keys not configured), in which case actors fall back to headers.
    """
    try:
        from src.services.auth.jwt_service import JWTService
        from src.config.auth_config import auth_settings

        jwt_service = JWTService(auth_settings)
        print("✓ JWT service initialized for logging middleware")
        logger.info("JWT service initialized for logging middleware")
        return jwt_service
    except Exception as e:
        print(f"✗ JWT service initialization failed: {e}")
        import traceback

        traceback.print_exc()
        logger.warning(f"JWT service initialization failed for logging: {e}")
        return None


def configure_middleware(app: FastAPI, record_validation_event) -> None:
    """Attach middleware, static mounts, and exception handlers to `app`.

    Args:
        app: The FastAPI application instance.
        record_validation_event: Callback used by validation error handlers
            to log validation failures to the ValidationMonitor.
    """
    # Security headers on all responses (HSTS, CSP, X-Frame-Options, etc.)
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("Security headers middleware initialized")
    print("✓ Security headers middleware added (HSTS, CSP, X-Frame-Options, etc.)")

    # Rate limiting (Redis-backed with slowapi, falls back to in-memory)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    logger.info("Rate limiting initialized successfully")

    jwt_service_for_logging = _init_jwt_service_for_logging()

    # Mount built assets first (higher priority for production builds)
    if os.path.exists("dist/static"):
        app.mount("/static/dist", StaticFiles(directory="dist/static"), name="dist")
    app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():
        """Serve the compiled Service Worker at the site root.

        A Service Worker's default scope is limited to its own path and below;
        serving it from the root (rather than /static/dist/sw.js) lets it control
        the whole app without requiring a Service-Worker-Allowed header.
        """
        sw_path = "dist/static/sw.js"
        if not os.path.exists(sw_path):
            raise HTTPException(status_code=404, detail="Service Worker not built")
        return FileResponse(sw_path, media_type="application/javascript")

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
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
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

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """Attach request IDs and emit structured request logs."""
        request_id = (
            request.headers.get("X-Request-ID")
            or logging_service.generate_request_id()
        )

        # Try to extract actor from JWT token
        actor = "anonymous"

        # Only attempt JWT decoding if service is available
        if jwt_service_for_logging:
            # Check for JWT in Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    token = auth_header.split(" ")[1]
                    payload = jwt_service_for_logging.validate_access_token(token)
                    actor = payload.get("username", "anonymous")
                    logger.debug(f"Extracted actor from Authorization header: {actor}")
                except Exception as e:
                    # Token invalid or expired, keep as anonymous
                    logger.debug(f"Failed to decode JWT from Authorization header: {e}")

            # Check for JWT in cookie if not in header
            if actor == "anonymous":
                access_token_cookie = request.cookies.get("access_token")
                if access_token_cookie:
                    try:
                        payload = jwt_service_for_logging.validate_access_token(
                            access_token_cookie
                        )
                        actor = payload.get("username", "anonymous")
                        logger.debug(f"Extracted actor from cookie: {actor}")
                    except Exception as e:
                        # Token invalid or expired, keep as anonymous
                        logger.debug(f"Failed to decode JWT from cookie: {e}")

        # Fallback to custom headers (for proxy/gateway scenarios)
        if actor == "anonymous":
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
            if os.getenv("ENV", "production") == "development":
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("text/html"):
                    response.headers["Cache-Control"] = (
                        "no-store, no-cache, must-revalidate, max-age=0"
                    )
                    response.headers["Pragma"] = "no-cache"
                    response.headers["Expires"] = "0"
            response.headers["X-Request-ID"] = request_id
            return response

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle Pydantic validation errors with user-friendly messages."""
        errors = exc.errors()
        error_messages = []
        sanitized_errors = []

        for error in errors:
            field = " -> ".join(str(loc) for loc in error["loc"] if loc != "body")
            message = error["msg"]
            error_messages.append(f"{field}: {message}")

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
    async def pydantic_validation_exception_handler(
        request: Request, exc: ValidationError
    ):
        """Handle Pydantic ValidationError raised in endpoint functions."""
        errors = exc.errors()
        error_messages = []
        sanitized_errors = []

        for error in errors:
            field = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_messages.append(f"{field}: {message}")

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
