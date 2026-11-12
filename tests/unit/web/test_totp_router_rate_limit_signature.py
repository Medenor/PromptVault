# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Regression guard for rate-limited 2FA handlers (FR-018).

slowapi injects ``X-RateLimit-*`` headers into a ``response: Response``
argument when the handler returns a Pydantic model instead of a Response. If
that parameter is missing, the request succeeds in tests (where the limiter is
disabled and the decorator is a no-op) but returns HTTP 500 in any deployment
with rate limiting enabled:

    Exception: parameter `response` must be an instance of starlette.responses.Response

Found live: POST /api/auth/2fa/enroll returned 500 on every call with the
limiter on. This test keeps all rate-limited 2FA handlers declaring it.
"""

import inspect

import pytest
from fastapi import Response

from src.web.routers import auth_totp_router

RATE_LIMITED_HANDLERS = [
    auth_totp_router.enroll_totp,
    auth_totp_router.verify_totp,
    auth_totp_router.disable_totp,
    auth_totp_router.regenerate_totp_recovery_codes,
]


@pytest.mark.parametrize("handler", RATE_LIMITED_HANDLERS, ids=lambda h: h.__name__)
def test_rate_limited_handler_declares_response_parameter(handler):
    parameters = inspect.signature(handler).parameters

    assert "response" in parameters, (
        f"{handler.__name__} is rate limited but has no `response: Response` "
        "parameter; slowapi will raise a 500 when the limiter is enabled"
    )
    assert parameters["response"].annotation is Response
