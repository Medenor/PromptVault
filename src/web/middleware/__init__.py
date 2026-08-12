# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Middleware package for PromptVault web application.

This package contains middleware components for the FastAPI application,
including rate limiting, authentication, and other request processing logic.
"""

from src.web.middleware.rate_limit import (
    add_rate_limit_headers,
    auth_login_limit,
    auth_register_limit,
    bulk_limit,
    expensive_limit,
    get_rate_limit_key,
    limiter,
    password_reset_limit,
    rate_limit_exceeded_handler,
    read_limit,
    write_limit,
)

__all__ = [
    "limiter",
    "get_rate_limit_key",
    "auth_login_limit",
    "auth_register_limit",
    "password_reset_limit",
    "read_limit",
    "write_limit",
    "expensive_limit",
    "bulk_limit",
    "rate_limit_exceeded_handler",
    "add_rate_limit_headers",
]
