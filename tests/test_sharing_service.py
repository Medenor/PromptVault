# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Service-layer tests for prompt sharing.

Two concerns:

1. ``PromptDataService.grant_share`` validation: self-share, owner-as-grantee,
   inactive/unknown grantee all rejected with the same generic
   ``ShareGrantError``; upsert semantics (create then update-in-place).
2. The authz-matrix from data-model.md, parametrized across 5 actors (owner,
   grantee-read, grantee-edit, stranger, admin) x the actions gated by
   ``check_prompt_access`` (view, edit, grant-share/un-grandfather which are
   both owner-level actions).
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.db.models import Prompt, User
from src.db.repositories.sharing_repository import SharingRepository
from src.services.exceptions import ShareGrantError
from src.services.prompt_data_service_db import PromptDataService
from src.web.routers.prompts_shared import check_prompt_access


@pytest.fixture
def admin_user(test_db_session: Session) -> User:
    user = User(
        id="svc-admin-id",
        username="svc_admin",
        email="svc_admin@example.com",
        password_hash="x",
        role="admin",
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture
def db_data_service_unpatched(monkeypatch, test_db_engine) -> PromptDataService:
    """PromptDataService pointed at the test engine (grant_share only)."""
    from sqlalchemy.orm import sessionmaker
    from src.db import session as session_module

    TestSessionLocal = sessionmaker(bind=test_db_engine)
    monkeypatch.setattr(session_module, "SessionLocal", TestSessionLocal)
    return PromptDataService()


# ---------------------------------------------------------------------------
# grant_share validations
# ---------------------------------------------------------------------------


class TestGrantShareValidation:
    def test_self_share_refused(
        self, db_data_service_unpatched, test_prompt: Prompt, test_user: User
    ):
        with pytest.raises(ShareGrantError):
            db_data_service_unpatched.grant_share(
                prompt_id=test_prompt.id,
                identifier=test_user.username,
                permission="read",
                acting_user=test_user,
            )

    def test_owner_as_grantee_refused(
        self,
        db_data_service_unpatched,
        test_prompt: Prompt,
        test_user: User,
        second_user: User,
    ):
        # second_user (not the owner) attempts to grant access *to* the owner.
        with pytest.raises(ShareGrantError):
            db_data_service_unpatched.grant_share(
                prompt_id=test_prompt.id,
                identifier=test_user.username,
                permission="read",
                acting_user=second_user,
            )

    def test_unknown_grantee_refused(
        self, db_data_service_unpatched, test_prompt: Prompt, test_user: User
    ):
        with pytest.raises(ShareGrantError):
            db_data_service_unpatched.grant_share(
                prompt_id=test_prompt.id,
                identifier="no-such-user-at-all",
                permission="read",
                acting_user=test_user,
            )

    def test_inactive_grantee_refused(
        self,
        db_data_service_unpatched,
        test_db_session: Session,
        test_prompt: Prompt,
        test_user: User,
        second_user: User,
    ):
        second_user.is_active = False
        test_db_session.flush()
        test_db_session.commit()

        with pytest.raises(ShareGrantError):
            db_data_service_unpatched.grant_share(
                prompt_id=test_prompt.id,
                identifier=second_user.username,
                permission="read",
                acting_user=test_user,
            )

    def test_nonexistent_prompt_refused(
        self, db_data_service_unpatched, test_user: User
    ):
        with pytest.raises(ShareGrantError):
            db_data_service_unpatched.grant_share(
                prompt_id=999999,
                identifier=test_user.username,
                permission="read",
                acting_user=test_user,
            )

    def test_upsert_creates_then_updates_in_place(
        self,
        db_data_service_unpatched,
        test_db_session: Session,
        test_prompt: Prompt,
        test_user: User,
        second_user: User,
    ):
        test_db_session.commit()

        first = db_data_service_unpatched.grant_share(
            prompt_id=test_prompt.id,
            identifier=second_user.username,
            permission="read",
            acting_user=test_user,
        )
        assert first["permission"] == "read"

        second = db_data_service_unpatched.grant_share(
            prompt_id=test_prompt.id,
            identifier=second_user.username,
            permission="edit",
            acting_user=test_user,
        )
        assert second["permission"] == "edit"

        from src.db.session import SessionLocal
        from src.db.models import PromptShare

        session = SessionLocal()
        try:
            all_shares = (
                session.query(PromptShare)
                .filter(
                    PromptShare.prompt_id == test_prompt.id,
                    PromptShare.grantee_user_id == second_user.id,
                )
                .all()
            )
            assert len(all_shares) == 1
        finally:
            session.close()


# ---------------------------------------------------------------------------
# Authz matrix: 5 actors x actions gated by check_prompt_access
# ---------------------------------------------------------------------------

ACTORS = ["owner", "grantee_read", "grantee_edit", "stranger", "admin"]

# (action label, required level) — mirrors data-model.md's action table.
ACTIONS = [
    ("view", "read"),
    ("edit_content", "edit"),
    ("grant_share", "owner"),
    ("un_grandfather", "owner"),
]

EXPECTED = {
    # actor -> effective level
    "owner": "owner",
    "grantee_read": "read",
    "grantee_edit": "edit",
    "stranger": None,
    "admin": "owner",
}

_LEVEL_RANK = {"read": 0, "edit": 1, "owner": 2}


@pytest.fixture
def actor_map(
    test_db_session: Session,
    test_prompt: Prompt,
    test_user: User,
    second_user: User,
    third_user: User,
    admin_user: User,
):
    SharingRepository(test_db_session).upsert(
        test_prompt.id, second_user.id, "read", test_user.id
    )
    # third_user plays both grantee_edit (via a second grant target) and
    # stranger is a distinct, ungranted user — reuse admin_user's session-only
    # identity for the edit grantee to keep fixtures minimal.
    from src.db.models import User as UserModel

    edit_grantee = UserModel(
        id="svc-edit-grantee-id",
        username="svc_edit_grantee",
        email="svc_edit_grantee@example.com",
        password_hash="x",
        role="user",
    )
    test_db_session.add(edit_grantee)
    test_db_session.flush()
    SharingRepository(test_db_session).upsert(
        test_prompt.id, edit_grantee.id, "edit", test_user.id
    )

    return {
        "owner": test_user,
        "grantee_read": second_user,
        "grantee_edit": edit_grantee,
        "stranger": third_user,
        "admin": admin_user,
    }


@pytest.mark.parametrize("actor_key", ACTORS)
@pytest.mark.parametrize("action_label,required_level", ACTIONS)
def test_authz_matrix(
    actor_key, action_label, required_level, actor_map, test_db_session, test_prompt
):
    actor = actor_map[actor_key]
    expected_level = EXPECTED[actor_key]

    should_pass = (
        expected_level is not None
        and _LEVEL_RANK[expected_level] >= _LEVEL_RANK[required_level]
    )

    if should_pass:
        check_prompt_access(test_prompt, actor, required_level, test_db_session)
    else:
        with pytest.raises(HTTPException) as exc_info:
            check_prompt_access(test_prompt, actor, required_level, test_db_session)
        assert exc_info.value.status_code == 403
