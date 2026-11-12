# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Regression tests: admin-mandated 2FA enrollment is enforced on every
authenticated dependency, including the bypass variants used by data routes.

Before this was covered, get_current_user_or_none / get_optional_user returned
the user without checking the role policy, so a non-enrolled user in a required
role could read and write prompts with a full token.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.repositories.totp_repository import TotpRepository
from src.web.dependencies import bypass
from src.web.dependencies.bypass import get_current_user_or_none
from src.web.dependencies.token import get_current_active_user, get_optional_user

ROLE = "viewer"


def _request(path: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [],
            "query_string": b"",
        }
    )


def _jwt_for(user: User) -> Mock:
    jwt = Mock()
    jwt.validate_access_token.return_value = {"sub": user.id, "family_id": "fam"}
    return jwt


@pytest.fixture
def auth_enabled(monkeypatch):
    monkeypatch.setattr(bypass, "auth_settings", SimpleNamespace(auth_enabled=True))


@pytest.fixture
def viewer(test_db_session: Session) -> User:
    user = User(
        id="totp-enforce-viewer",
        username="totp_enforce_viewer",
        email="totp-enforce-viewer@example.com",
        password_hash="placeholder",
        role=ROLE,
        totp_enabled=False,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture
def viewer_required(test_db_session: Session, viewer: User) -> User:
    TotpRepository(test_db_session).set_role_policy(ROLE, True, None)
    test_db_session.flush()
    return viewer


class TestBypassDependencyEnforcesEnrollment:
    @pytest.mark.asyncio
    async def test_non_enrolled_user_in_required_role_gets_403(
        self, auth_enabled, test_db_session, viewer_required
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user_or_none(
                request=_request("/api/prompts"),
                authorization="Bearer t",
                access_token_cookie=None,
                jwt_service=_jwt_for(viewer_required),
                session=test_db_session,
            )
        assert exc.value.status_code == 403
        # The frontend keys off this header to route the user to enrollment.
        assert exc.value.headers == {"X-TOTP-Enrollment-Required": "true"}

    @pytest.mark.asyncio
    async def test_exempt_enrollment_path_is_still_reachable(
        self, auth_enabled, test_db_session, viewer_required
    ):
        user = await get_current_user_or_none(
            request=_request("/api/auth/2fa/enroll"),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(viewer_required),
            session=test_db_session,
        )
        assert user is not None and user.id == viewer_required.id

    @pytest.mark.asyncio
    async def test_enrolled_user_in_required_role_is_allowed(
        self, auth_enabled, test_db_session, viewer_required
    ):
        viewer_required.totp_enabled = True
        test_db_session.flush()
        user = await get_current_user_or_none(
            request=_request("/api/prompts"),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(viewer_required),
            session=test_db_session,
        )
        assert user is not None

    @pytest.mark.asyncio
    async def test_non_required_role_is_allowed(
        self, auth_enabled, test_db_session, viewer
    ):
        user = await get_current_user_or_none(
            request=_request("/api/prompts"),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(viewer),
            session=test_db_session,
        )
        assert user is not None

    @pytest.mark.asyncio
    async def test_invalid_token_still_returns_none_not_403(
        self, auth_enabled, test_db_session, viewer_required
    ):
        jwt = Mock()
        jwt.validate_access_token.side_effect = ValueError("bad token")
        user = await get_current_user_or_none(
            request=_request("/api/prompts"),
            authorization="Bearer bad",
            access_token_cookie=None,
            jwt_service=jwt,
            session=test_db_session,
        )
        assert user is None


class TestOptionalUserEnforcesEnrollment:
    def test_non_enrolled_user_in_required_role_gets_403(
        self, monkeypatch, test_db_session, viewer_required
    ):
        # Session-revocation handling is covered elsewhere; stub the lookup so
        # this test isolates the enrollment-policy check.
        from src.web.dependencies import token

        monkeypatch.setattr(
            token, "_resolve_active_user", lambda s, uid: viewer_required
        )
        with pytest.raises(HTTPException) as exc:
            get_optional_user(
                request=_request("/api/prompts/1"),
                authorization="Bearer t",
                jwt_service=_jwt_for(viewer_required),
                session=test_db_session,
            )
        assert exc.value.status_code == 403


class TestStrictDependencyUnchanged:
    def test_active_user_dependency_still_gets_403(
        self, test_db_session, viewer_required
    ):
        with pytest.raises(HTTPException) as exc:
            get_current_active_user(
                request=_request("/api/prompts"),
                user=viewer_required,
                session=test_db_session,
            )
        assert exc.value.status_code == 403


class TestEnrollmentExemptionPathMatching:
    """The enrollment allowlist must survive harmless path variations."""

    @pytest.mark.asyncio
    async def test_trailing_slash_on_exempt_path_stays_reachable(
        self, auth_enabled, test_db_session, viewer_required
    ):
        user = await get_current_user_or_none(
            request=_request("/api/auth/me/"),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(viewer_required),
            session=test_db_session,
        )
        assert user is not None

    @pytest.mark.asyncio
    async def test_root_path_prefix_does_not_break_the_exemption(
        self, auth_enabled, test_db_session, viewer_required
    ):
        request = Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/promptvault/api/auth/2fa/enroll",
                "root_path": "/promptvault",
                "headers": [],
                "query_string": b"",
            }
        )
        user = await get_current_user_or_none(
            request=request,
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(viewer_required),
            session=test_db_session,
        )
        assert user is not None

    @pytest.mark.asyncio
    async def test_non_exempt_path_is_still_blocked_with_trailing_slash(
        self, auth_enabled, test_db_session, viewer_required
    ):
        with pytest.raises(HTTPException) as exc:
            await get_current_user_or_none(
                request=_request("/api/prompts/"),
                authorization="Bearer t",
                access_token_cookie=None,
                jwt_service=_jwt_for(viewer_required),
                session=test_db_session,
            )
        assert exc.value.status_code == 403


class TestEnrollmentPolicyLookupIsMemoised:
    def test_policy_is_queried_once_per_request(
        self, test_db_session, viewer_required, monkeypatch
    ):
        from src.web.dependencies import token

        calls = []
        original = token.TotpPolicyService.is_required_for

        def counting(self, role):
            calls.append(role)
            return original(self, role)

        monkeypatch.setattr(token.TotpPolicyService, "is_required_for", counting)
        request = _request("/api/prompts")

        for _ in range(3):
            with pytest.raises(HTTPException):
                token.enforce_totp_enrollment_policy(
                    viewer_required, request, test_db_session
                )

        assert calls == [ROLE]
