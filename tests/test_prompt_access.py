# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for the prompt access-resolution helper.

Exercises the six-branch effective-permission resolution table from
data-model.md directly: admin, owner, read-grant, edit-grant,
legacy_public-only, and no-access, plus the auth-disabled pass-through.
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.db.models import Prompt, User
from src.db.repositories.sharing_repository import SharingRepository
from src.web.routers.prompts_shared import check_prompt_access, effective_permission

# AUTH_ENABLED=true is set by conftest.py before any src.* import, so
# auth_settings.auth_enabled is True by default here — AuthConfig is a
# frozen Pydantic model, so per-test overrides go through monkeypatch on the
# module-level reference each check_prompt_access() call resolves, not
# attribute mutation on the singleton itself.


@pytest.fixture
def admin_user(test_db_session: Session) -> User:
    user = User(
        id="admin-user-id",
        username="admin_user",
        email="admin@example.com",
        password_hash="x",
        role="admin",
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


def test_admin_gets_owner_level(
    test_db_session: Session, test_prompt: Prompt, admin_user: User
):
    assert effective_permission(test_prompt, admin_user, test_db_session) == "owner"


def test_owner_gets_owner_level(
    test_db_session: Session, test_prompt: Prompt, test_user: User
):
    assert effective_permission(test_prompt, test_user, test_db_session) == "owner"


def test_read_grantee_gets_read_level(
    test_db_session: Session, test_prompt: Prompt, second_user: User
):
    SharingRepository(test_db_session).upsert(
        test_prompt.id, second_user.id, "read", test_prompt.user_id
    )

    assert effective_permission(test_prompt, second_user, test_db_session) == "read"


def test_edit_grantee_gets_edit_level(
    test_db_session: Session, test_prompt: Prompt, second_user: User
):
    SharingRepository(test_db_session).upsert(
        test_prompt.id, second_user.id, "edit", test_prompt.user_id
    )

    assert effective_permission(test_prompt, second_user, test_db_session) == "edit"


def test_legacy_public_only_gets_read_never_edit(
    test_db_session: Session, legacy_public_prompt, third_user: User
):
    prompt = legacy_public_prompt()

    assert effective_permission(prompt, third_user, test_db_session) == "read"


def test_no_access_returns_none(
    test_db_session: Session, test_prompt: Prompt, third_user: User
):
    assert effective_permission(test_prompt, third_user, test_db_session) is None


def test_none_user_returns_none(test_db_session: Session, test_prompt: Prompt):
    assert effective_permission(test_prompt, None, test_db_session) is None


# ---------------------------------------------------------------------------
# check_prompt_access: same matrix, exercised through the raising wrapper
# ---------------------------------------------------------------------------


def test_check_prompt_access_admin_passes_owner_level(
    test_db_session: Session, test_prompt: Prompt, admin_user: User
):
    check_prompt_access(test_prompt, admin_user, "owner", test_db_session)


def test_check_prompt_access_owner_passes_owner_level(
    test_db_session: Session, test_prompt: Prompt, test_user: User
):
    check_prompt_access(test_prompt, test_user, "owner", test_db_session)


def test_check_prompt_access_read_grantee_passes_read_fails_edit(
    test_db_session: Session, test_prompt: Prompt, second_user: User
):
    SharingRepository(test_db_session).upsert(
        test_prompt.id, second_user.id, "read", test_prompt.user_id
    )

    check_prompt_access(test_prompt, second_user, "read", test_db_session)
    with pytest.raises(HTTPException) as exc_info:
        check_prompt_access(test_prompt, second_user, "edit", test_db_session)
    assert exc_info.value.status_code == 403


def test_check_prompt_access_edit_grantee_passes_edit_fails_owner(
    test_db_session: Session, test_prompt: Prompt, second_user: User
):
    SharingRepository(test_db_session).upsert(
        test_prompt.id, second_user.id, "edit", test_prompt.user_id
    )

    check_prompt_access(test_prompt, second_user, "edit", test_db_session)
    with pytest.raises(HTTPException) as exc_info:
        check_prompt_access(test_prompt, second_user, "owner", test_db_session)
    assert exc_info.value.status_code == 403


def test_check_prompt_access_legacy_public_passes_read_fails_edit(
    test_db_session: Session, legacy_public_prompt, third_user: User
):
    prompt = legacy_public_prompt()

    check_prompt_access(prompt, third_user, "read", test_db_session)
    with pytest.raises(HTTPException) as exc_info:
        check_prompt_access(prompt, third_user, "edit", test_db_session)
    assert exc_info.value.status_code == 403


def test_check_prompt_access_no_access_raises_403(
    test_db_session: Session, test_prompt: Prompt, third_user: User
):
    with pytest.raises(HTTPException) as exc_info:
        check_prompt_access(test_prompt, third_user, "read", test_db_session)
    assert exc_info.value.status_code == 403


def test_check_prompt_access_auth_disabled_is_noop(
    test_db_session: Session, test_prompt: Prompt, third_user: User, monkeypatch
):
    from src.web.routers import prompts_shared

    # AuthConfig is frozen (attribute assignment on the real singleton would
    # raise), so swap in a lightweight stand-in that only carries the flag
    # this helper reads, scoped to prompts_shared's module-level reference.
    class _Disabled:
        auth_enabled = False

    monkeypatch.setattr(prompts_shared, "auth_settings", _Disabled())

    # No exception, even though third_user has no grant or ownership.
    check_prompt_access(test_prompt, third_user, "owner", test_db_session)
