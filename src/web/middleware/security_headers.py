# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Security Headers Middleware for PromptVault.

This module provides middleware to add security-related HTTP headers to all responses,
protecting against common web vulnerabilities.

Security Headers:
    - Strict-Transport-Security (HSTS): Force HTTPS for 1 year
    - X-Content-Type-Options: Prevent MIME type sniffing
    - X-Frame-Options: Prevent clickjacking attacks
    - X-XSS-Protection: Enable XSS protection (legacy)
    - Content-Security-Policy: Control which resources can be loaded
    - Referrer-Policy: Control referrer information

Example:
    >>> from fastapi import FastAPI
    >>> from src.web.middleware.security_headers import SecurityHeadersMiddleware
    >>> app = FastAPI()
    >>> app.add_middleware(SecurityHeadersMiddleware)
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import os

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security-related HTTP headers to all responses.

    Headers added:
        - Strict-Transport-Security: HSTS header to enforce HTTPS
        - X-Content-Type-Options: Prevent MIME type sniffing (X-Content-Type-Options: nosniff)
        - X-Frame-Options: Prevent clickjacking (X-Frame-Options: DENY)
        - X-XSS-Protection: Enable XSS protection (X-XSS-Protection: 1; mode=block)
        - Content-Security-Policy: Restrict resource loading
        - Referrer-Policy: Control referrer information
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response.

        Args:
            request: HTTP request object
            call_next: Next middleware/handler callable

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Strict-Transport-Security (HSTS)
        # Force HTTPS for 1 year (31536000 seconds) and include subdomains
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # X-Content-Type-Options
        # Prevent browsers from MIME sniffing (guessing content type)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevent clickjacking attacks by not allowing embedding in frames
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection (legacy, but still useful for older browsers)
        # Enable XSS protection and block page if XSS detected
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy (CSP)
        # Strict CSP: self only for scripts, styles, and images
        # Allow inline styles and handlers for UI functionality
        # Note: Using 'unsafe-inline' for script-src-attr to allow onclick handlers
        # TODO: Refactor HTML to use event listeners for production hardening
        csp_header = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "script-src-attr 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' https://fonts.gstatic.com; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        if (
            os.getenv("ENV", "production") == "development"
            and os.getenv("USE_VITE_ASSETS", "false").lower() == "true"
        ):
            csp_header = csp_header.replace(
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com;",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com http://localhost:5173;",
            )
            csp_header = csp_header.replace(
                "connect-src 'self' https://fonts.gstatic.com;",
                "connect-src 'self' https://fonts.gstatic.com http://localhost:5173 ws://localhost:5173;",
            )
        response.headers["Content-Security-Policy"] = csp_header

        # Referrer-Policy
        # Only send referrer when navigating to same site (stricter than default)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Additional security headers
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        logger.debug("Security headers added to response")

        return response
