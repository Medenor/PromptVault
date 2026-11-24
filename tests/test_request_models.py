# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for request model validation and sanitization."""

import pytest
from pydantic import ValidationError

from src.web.models import admin_requests, auth_requests


def test_register_request_normalizes_email():
    request = auth_requests.RegisterRequest(
        username="valid_user",
        email="USER@Example.com",
        password="StrongP@ssw0rd123",
        confirm_password="StrongP@ssw0rd123",
    )
    assert request.email == "user@example.com"


def test_register_request_rejects_username_only_underscores():
    with pytest.raises(ValidationError):
        auth_requests.RegisterRequest(
            username="___",
            email="user@example.com",
            password="StrongP@ssw0rd123",
            confirm_password="StrongP@ssw0rd123",
        )


def test_register_request_rejects_password_mismatch():
    with pytest.raises(ValidationError):
        auth_requests.RegisterRequest(
            username="valid_user",
            email="user@example.com",
            password="StrongP@ssw0rd123",
            confirm_password="StrongP@ssw0rd124",
        )


def test_login_request_lowercases_email():
    request = auth_requests.LoginRequest(
        username_or_email="USER@Example.com",
        password="StrongP@ssw0rd123",
    )
    assert request.username_or_email == "user@example.com"


def test_refresh_token_request_requires_jwt_format():
    with pytest.raises(ValidationError):
        auth_requests.RefreshTokenRequest(refresh_token="not-a-jwt")


@pytest.mark.parametrize(
    ("model", "field", "extra"),
    [
        (auth_requests.RefreshTokenRequest, "refresh_token", {}),
        (auth_requests.LogoutRequest, "refresh_token", {}),
        (
            auth_requests.TotpChallengeExchangeRequest,
            "challenge_token",
            {"code": "123456"},
        ),
    ],
)
def test_jwt_body_fields_reject_oversized_tokens(model, field, extra):
    segment = "a" * auth_requests.MAX_JWT_LENGTH
    with pytest.raises(ValidationError):
        model(**{field: f"{segment}.{segment}.sig", **extra})


def test_change_password_request_rejects_same_password():
    with pytest.raises(ValidationError):
        auth_requests.ChangePasswordRequest(
            old_password="SameP@ssw0rd123",
            new_password="SameP@ssw0rd123",
            confirm_new_password="SameP@ssw0rd123",
        )


def test_password_reset_confirm_rejects_blank_token():
    with pytest.raises(ValidationError):
        auth_requests.PasswordResetConfirmRequest(
            token="   ",
            new_password="NewP@ssw0rd123",
            confirm_new_password="NewP@ssw0rd123",
        )


def test_revoke_session_request_normalizes_uuid():
    request = auth_requests.RevokeSessionRequest(
        session_id="550E8400-E29B-41D4-A716-446655440000"
    )
    assert request.session_id == "550e8400-e29b-41d4-a716-446655440000"


def test_update_profile_requires_field():
    with pytest.raises(ValidationError):
        auth_requests.UpdateProfileRequest()


def test_admin_create_user_rejects_invalid_username():
    with pytest.raises(ValidationError):
        admin_requests.CreateUserRequest(
            username="bad name",
            email="user@example.com",
            password="StrongP@ssw0rd123",
            confirm_password="StrongP@ssw0rd123",
            role="viewer",
            email_verified=False,
        )


def test_admin_create_user_rejects_invalid_email():
    with pytest.raises(ValidationError):
        admin_requests.CreateUserRequest(
            username="valid_user",
            email="invalid-email",
            password="StrongP@ssw0rd123",
            confirm_password="StrongP@ssw0rd123",
            role="viewer",
            email_verified=False,
        )


def test_admin_create_user_rejects_password_missing_special():
    with pytest.raises(ValidationError):
        admin_requests.CreateUserRequest(
            username="valid_user",
            email="user@example.com",
            password="StrongPassw0rd123",
            confirm_password="StrongPassw0rd123",
            role="viewer",
            email_verified=False,
        )


def test_admin_create_user_rejects_confirm_mismatch():
    with pytest.raises(ValidationError):
        admin_requests.CreateUserRequest(
            username="valid_user",
            email="user@example.com",
            password="StrongP@ssw0rd123",
            confirm_password="StrongP@ssw0rd124",
            role="viewer",
            email_verified=False,
        )


def test_admin_update_user_rejects_invalid_role():
    with pytest.raises(ValidationError):
        admin_requests.UpdateUserRequest(role="invalid-role")


def test_admin_user_list_params_trim_search():
    params = admin_requests.UserListParams(search="   ")
    assert params.search is None
