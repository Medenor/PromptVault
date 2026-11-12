# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Regression tests: account lockout is enforced on every authenticated
dependency, including the bypass variants used by data routes.

Lockout used to be checked only at login and in ``get_current_active_user``.
A session token issued before a lockout (for example after repeated wrong 2FA
codes) therefore kept working on every route that used
``get_current_user_or_none`` or ``get_optional_user`` until it expired.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.web.dependencies import bypass
from src.web.dependencies.bypass import get_current_user_or_none
from src.web.dependencies.token import (
    enforce_account_not_locked,
    get_current_active_user,
    get_optional_user,
)


def _request(path: str = "/api/prompts") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
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
def user(test_db_session: Session) -> User:
    account = User(
        id="lockout-enforce-user",
        username="lockout_enforce_user",
        email="lockout-enforce-user@example.com",
        password_hash="placeholder",
        role="viewer",
        totp_enabled=False,
        is_active=True,
    )
    test_db_session.add(account)
    test_db_session.flush()
    return account


def _lock(user: User, *, delta: timedelta, naive: bool = False) -> None:
    locked_until = datetime.now(UTC) + delta
    user.locked_until = locked_until.replace(tzinfo=None) if naive else locked_until


class TestEnforceAccountNotLocked:
    def test_unlocked_user_passes(self, user):
        enforce_account_not_locked(user)

    def test_active_lock_raises_401_with_locked_challenge(self, user):
        _lock(user, delta=timedelta(minutes=10))

        with pytest.raises(HTTPException) as exc:
            enforce_account_not_locked(user)

        assert exc.value.status_code == 401
        assert "temporarily locked" in exc.value.detail
        assert "Account locked" in exc.value.headers["WWW-Authenticate"]

    def test_naive_datetime_from_sqlite_is_treated_as_utc(self, user):
        _lock(user, delta=timedelta(minutes=10), naive=True)

        with pytest.raises(HTTPException) as exc:
            enforce_account_not_locked(user)

        assert exc.value.status_code == 401

    def test_expired_lock_does_not_block(self, user):
        _lock(user, delta=timedelta(minutes=-1))
        enforce_account_not_locked(user)

    def test_expired_naive_lock_does_not_block(self, user):
        _lock(user, delta=timedelta(minutes=-1), naive=True)
        enforce_account_not_locked(user)


class TestBypassDependencyEnforcesLockout:
    @pytest.mark.asyncio
    async def test_locked_user_with_valid_token_gets_401(
        self, auth_enabled, test_db_session, user
    ):
        _lock(user, delta=timedelta(minutes=10))

        with pytest.raises(HTTPException) as exc:
            await get_current_user_or_none(
                request=_request(),
                authorization="Bearer t",
                access_token_cookie=None,
                jwt_service=_jwt_for(user),
                session=test_db_session,
            )

        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_lock_returns_the_user(
        self, auth_enabled, test_db_session, user
    ):
        _lock(user, delta=timedelta(minutes=-1))

        result = await get_current_user_or_none(
            request=_request(),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(user),
            session=test_db_session,
        )

        assert result is user

    @pytest.mark.asyncio
    async def test_auth_disabled_still_returns_none_even_if_locked(
        self, monkeypatch, test_db_session, user
    ):
        # Anonymous mode (AUTH_ENABLED=false) must keep short-circuiting.
        monkeypatch.setattr(
            bypass, "auth_settings", SimpleNamespace(auth_enabled=False)
        )
        _lock(user, delta=timedelta(minutes=10))

        result = await get_current_user_or_none(
            request=_request(),
            authorization="Bearer t",
            access_token_cookie=None,
            jwt_service=_jwt_for(user),
            session=test_db_session,
        )

        assert result is None


class TestOptionalUserEnforcesLockout:
    def test_locked_user_gets_401(self, monkeypatch, test_db_session, user):
        from src.web.dependencies import token

        monkeypatch.setattr(token, "_resolve_active_user", lambda s, uid: user)
        _lock(user, delta=timedelta(minutes=10))

        with pytest.raises(HTTPException) as exc:
            get_optional_user(
                request=_request(),
                authorization="Bearer t",
                jwt_service=_jwt_for(user),
                session=test_db_session,
            )

        assert exc.value.status_code == 401


class TestStrictDependencyStillEnforcesLockout:
    def test_locked_user_gets_401(self, test_db_session, user):
        _lock(user, delta=timedelta(minutes=10))

        with pytest.raises(HTTPException) as exc:
            get_current_active_user(
                request=_request(), user=user, session=test_db_session
            )

        assert exc.value.status_code == 401
        assert "temporarily locked" in exc.value.detail
