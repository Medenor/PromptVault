# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for SharingRepository.

Covers upsert (create + update-in-place), revoke, both lookup directions,
permission_for hit/miss, and cascade/SET NULL behavior on prompt/user
deletion per data-model.md's lifecycle table.
"""

from sqlalchemy.orm import Session

from src.db.models import Prompt, PromptShare, User
from src.db.repositories.sharing_repository import SharingRepository


def test_upsert_creates_new_grant(
    sharing_repo: SharingRepository, test_prompt: Prompt, second_user: User
):
    share = sharing_repo.upsert(
        prompt_id=test_prompt.id,
        grantee_user_id=second_user.id,
        permission="read",
        granted_by=test_prompt.user_id,
    )

    assert share.id is not None
    assert share.prompt_id == test_prompt.id
    assert share.grantee_user_id == second_user.id
    assert share.permission == "read"
    assert share.granted_by == test_prompt.user_id


def test_upsert_updates_in_place_no_duplicate(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    second_user: User,
):
    first = sharing_repo.upsert(
        prompt_id=test_prompt.id,
        grantee_user_id=second_user.id,
        permission="read",
        granted_by=test_prompt.user_id,
    )
    second = sharing_repo.upsert(
        prompt_id=test_prompt.id,
        grantee_user_id=second_user.id,
        permission="edit",
        granted_by=test_prompt.user_id,
    )

    assert first.id == second.id
    assert second.permission == "edit"

    all_shares = (
        test_db_session.query(PromptShare)
        .filter(
            PromptShare.prompt_id == test_prompt.id,
            PromptShare.grantee_user_id == second_user.id,
        )
        .all()
    )
    assert len(all_shares) == 1


def test_revoke_removes_grant(
    sharing_repo: SharingRepository, test_prompt: Prompt, second_user: User
):
    sharing_repo.upsert(
        prompt_id=test_prompt.id,
        grantee_user_id=second_user.id,
        permission="read",
        granted_by=test_prompt.user_id,
    )

    result = sharing_repo.revoke(test_prompt.id, second_user.id)

    assert result is True
    assert sharing_repo.permission_for(test_prompt.id, second_user.id) is None


def test_revoke_nonexistent_grant_returns_false(
    sharing_repo: SharingRepository, test_prompt: Prompt, second_user: User
):
    result = sharing_repo.revoke(test_prompt.id, second_user.id)

    assert result is False


def test_list_for_prompt(
    sharing_repo: SharingRepository,
    test_prompt: Prompt,
    second_user: User,
    third_user: User,
):
    sharing_repo.upsert(test_prompt.id, second_user.id, "read", test_prompt.user_id)
    sharing_repo.upsert(test_prompt.id, third_user.id, "edit", test_prompt.user_id)

    shares = sharing_repo.list_for_prompt(test_prompt.id)

    assert len(shares) == 2
    grantee_ids = {s.grantee_user_id for s in shares}
    assert grantee_ids == {second_user.id, third_user.id}


def test_list_for_prompt_empty(sharing_repo: SharingRepository, test_prompt: Prompt):
    assert sharing_repo.list_for_prompt(test_prompt.id) == []


def test_list_for_grantee(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    test_category,
    second_user: User,
):
    other_prompt = Prompt(
        title="Other Prompt",
        prompt="Other content",
        category_id=test_category.id,
        favorite=False,
        user_id=test_prompt.user_id,
    )
    test_db_session.add(other_prompt)
    test_db_session.flush()

    sharing_repo.upsert(test_prompt.id, second_user.id, "read", test_prompt.user_id)
    sharing_repo.upsert(other_prompt.id, second_user.id, "edit", test_prompt.user_id)

    shares = sharing_repo.list_for_grantee(second_user.id)

    assert len(shares) == 2
    prompt_ids = {s.prompt_id for s in shares}
    assert prompt_ids == {test_prompt.id, other_prompt.id}


def test_permission_for_hit(
    sharing_repo: SharingRepository, test_prompt: Prompt, second_user: User
):
    sharing_repo.upsert(test_prompt.id, second_user.id, "edit", test_prompt.user_id)

    assert sharing_repo.permission_for(test_prompt.id, second_user.id) == "edit"


def test_permission_for_miss(
    sharing_repo: SharingRepository, test_prompt: Prompt, third_user: User
):
    assert sharing_repo.permission_for(test_prompt.id, third_user.id) is None


def test_cascade_on_prompt_delete(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    second_user: User,
):
    sharing_repo.upsert(test_prompt.id, second_user.id, "read", test_prompt.user_id)
    prompt_id = test_prompt.id

    test_db_session.delete(test_prompt)
    test_db_session.flush()

    remaining = (
        test_db_session.query(PromptShare)
        .filter(PromptShare.prompt_id == prompt_id)
        .all()
    )
    assert remaining == []


def test_cascade_on_grantee_delete(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    second_user: User,
):
    sharing_repo.upsert(test_prompt.id, second_user.id, "read", test_prompt.user_id)
    grantee_id = second_user.id

    test_db_session.delete(second_user)
    test_db_session.flush()

    remaining = (
        test_db_session.query(PromptShare)
        .filter(PromptShare.grantee_user_id == grantee_id)
        .all()
    )
    assert remaining == []


def test_granted_by_set_null_on_grantor_delete(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    test_user: User,
    second_user: User,
    third_user: User,
):
    # third_user grants on behalf of test_user's prompt (simulating an admin
    # grant), so the grant itself has a distinct owner (test_prompt) from its
    # grantor (third_user) — deleting third_user must not cascade the grant,
    # only null out granted_by. ON DELETE SET NULL is DB-enforced, not an ORM
    # relationship cascade (there is deliberately no relationship cascade
    # configured on granted_by/granted_by_user), so this must go through a
    # real connection with foreign_keys pragma on and a raw DELETE — the
    # shared test_db_session fixture's engine does not enable FK enforcement
    # (see test_db_engine in conftest.py), and an ORM session.delete() alone
    # would not trigger DB-level ON DELETE behavior anyway.
    from sqlalchemy import text

    share = sharing_repo.upsert(
        test_prompt.id, second_user.id, "read", granted_by=third_user.id
    )
    share_id = share.id
    test_db_session.flush()
    test_db_session.commit()

    connection = test_db_session.connection()
    connection.execute(text("PRAGMA foreign_keys=ON"))
    connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": third_user.id})
    test_db_session.commit()

    refreshed = (
        test_db_session.query(PromptShare).filter(PromptShare.id == share_id).first()
    )
    assert refreshed is not None
    test_db_session.refresh(refreshed)
    assert refreshed.granted_by is None


def test_grantee_deactivation_leaves_share_untouched(
    sharing_repo: SharingRepository,
    test_db_session: Session,
    test_prompt: Prompt,
    second_user: User,
):
    share = sharing_repo.upsert(
        test_prompt.id, second_user.id, "read", test_prompt.user_id
    )
    share_id = share.id

    second_user.is_active = False
    test_db_session.flush()

    refreshed = (
        test_db_session.query(PromptShare).filter(PromptShare.id == share_id).first()
    )
    assert refreshed is not None
    assert refreshed.permission == "read"


# ---------------------------------------------------------------------------
# PromptRepository.search()/count() visibility scoping (US2, T030)
# ---------------------------------------------------------------------------


def _make_prompt(session: Session, category, owner_id, title, legacy_public=False, favorite=False):
    prompt = Prompt(
        title=title,
        prompt="content",
        category_id=category.id,
        favorite=favorite,
        legacy_public=legacy_public,
        user_id=owner_id,
    )
    session.add(prompt)
    session.flush()
    return prompt


class TestPromptVisibilityScoping:
    def test_search_returns_owned_shared_and_legacy_public_no_duplicates(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        test_user: User,
        second_user: User,
        third_user: User,
    ):
        owned = _make_prompt(test_db_session, test_category, second_user.id, "Owned by second")
        shared = _make_prompt(test_db_session, test_category, third_user.id, "Shared with second")
        legacy = _make_prompt(
            test_db_session, test_category, third_user.id, "Legacy public", legacy_public=True
        )
        private_other = _make_prompt(
            test_db_session, test_category, third_user.id, "Private, not shared"
        )
        sharing_repo.upsert(shared.id, second_user.id, "read", third_user.id)

        results = prompt_repo.search(visible_to_user_id=second_user.id)
        result_ids = {p.id for p in results}

        assert owned.id in result_ids
        assert shared.id in result_ids
        assert legacy.id in result_ids
        assert private_other.id not in result_ids
        assert len(result_ids) == len(results)  # no duplicates

    def test_search_shared_only_excludes_legacy_public_and_owned(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        second_user: User,
        third_user: User,
    ):
        owned = _make_prompt(test_db_session, test_category, second_user.id, "Owned")
        shared = _make_prompt(test_db_session, test_category, third_user.id, "Shared")
        legacy = _make_prompt(
            test_db_session, test_category, third_user.id, "Legacy", legacy_public=True
        )
        sharing_repo.upsert(shared.id, second_user.id, "read", third_user.id)

        results = prompt_repo.search(visible_to_user_id=second_user.id, shared_only=True)
        result_ids = {p.id for p in results}

        assert result_ids == {shared.id}
        assert owned.id not in result_ids
        assert legacy.id not in result_ids

    def test_search_honors_query_category_tags_with_visibility(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        second_user: User,
        third_user: User,
    ):
        matching = _make_prompt(
            test_db_session, test_category, third_user.id, "Findable Title"
        )
        non_matching = _make_prompt(
            test_db_session, test_category, third_user.id, "Other Title"
        )
        sharing_repo.upsert(matching.id, second_user.id, "read", third_user.id)
        sharing_repo.upsert(non_matching.id, second_user.id, "read", third_user.id)

        results = prompt_repo.search(
            query="Findable", visible_to_user_id=second_user.id
        )
        result_ids = {p.id for p in results}

        assert result_ids == {matching.id}

    def test_search_pagination_within_visible_set(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        second_user: User,
        third_user: User,
    ):
        for i in range(5):
            p = _make_prompt(test_db_session, test_category, third_user.id, f"Page prompt {i}")
            sharing_repo.upsert(p.id, second_user.id, "read", third_user.id)

        page1 = prompt_repo.search(visible_to_user_id=second_user.id, limit=2, offset=0)
        page2 = prompt_repo.search(visible_to_user_id=second_user.id, limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert {p.id for p in page1}.isdisjoint({p.id for p in page2})

    def test_favorite_filter_restricted_to_owned_when_visibility_scoped(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        second_user: User,
        third_user: User,
    ):
        owned_favorite = _make_prompt(
            test_db_session, test_category, second_user.id, "Owned favorite", favorite=True
        )
        shared_favorite = _make_prompt(
            test_db_session, test_category, third_user.id, "Shared favorite", favorite=True
        )
        sharing_repo.upsert(shared_favorite.id, second_user.id, "read", third_user.id)

        results = prompt_repo.search(
            favorite=True, visible_to_user_id=second_user.id
        )
        result_ids = {p.id for p in results}

        assert result_ids == {owned_favorite.id}
        assert shared_favorite.id not in result_ids

    def test_search_count_consistency(
        self,
        prompt_repo,
        sharing_repo: SharingRepository,
        test_db_session: Session,
        test_category,
        second_user: User,
        third_user: User,
    ):
        for i in range(3):
            p = _make_prompt(test_db_session, test_category, third_user.id, f"Count prompt {i}")
            sharing_repo.upsert(p.id, second_user.id, "edit", third_user.id)

        search_results = prompt_repo.search(visible_to_user_id=second_user.id)
        count_result = prompt_repo.count(visible_to_user_id=second_user.id)

        assert len(search_results) == count_result

    def test_none_visible_to_user_id_is_unscoped(
        self,
        prompt_repo,
        test_db_session: Session,
        test_category,
        third_user: User,
    ):
        private_prompt = _make_prompt(
            test_db_session, test_category, third_user.id, "Fully private"
        )

        results = prompt_repo.search(visible_to_user_id=None)
        result_ids = {p.id for p in results}

        assert private_prompt.id in result_ids
