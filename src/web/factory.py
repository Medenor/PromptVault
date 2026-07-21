# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI application factory.

Builds the bare `FastAPI` instance (title, version, description, OpenAPI
tags). Middleware, routers, and startup/shutdown events are wired up
separately by `middleware_setup`, `routing_setup`, and `startup` so each
concern can be reasoned about independently.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Construct the PromptVault FastAPI application shell."""
    return FastAPI(
        title="PromptVault API",
        version="1.11.0",
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
