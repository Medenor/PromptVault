# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pytest fixtures exposing the skill archive builders.

Imported by ``tests/conftest.py`` so every suite can request them.
"""

from collections.abc import Callable

import pytest
from fixtures.skills import build_fixtures as bf
from fixtures.skills.api_helpers import SkillApi


@pytest.fixture
def skill_zip_valid_wrapped() -> bytes:
    return bf.valid_wrapped()


@pytest.fixture
def skill_zip_valid_root() -> bytes:
    return bf.valid_root_level()


@pytest.fixture
def skill_zip_no_frontmatter() -> bytes:
    return bf.no_frontmatter()


@pytest.fixture
def skill_zip_bad_name() -> bytes:
    return bf.bad_name()


@pytest.fixture
def skill_zip_with_clutter() -> bytes:
    return bf.with_clutter()


@pytest.fixture
def skill_zip_non_utf8() -> bytes:
    return bf.non_utf8_skill_md()


@pytest.fixture
def make_skill_zip() -> Callable[..., bytes]:
    """Factory: ``make_skill_zip([(name, content), ...], symlinks=..., compression=...)``."""
    return bf.build_zip


@pytest.fixture
def skill_api(api_client_context) -> SkillApi:
    """TestClient (auth enabled, in-memory database) with skill helpers."""
    return SkillApi(client=api_client_context["client"])


@pytest.fixture
def skill_owner(skill_api: SkillApi) -> dict:
    return skill_api.make_user("skill-owner-id", "skill_owner")


@pytest.fixture
def skill_other(skill_api: SkillApi) -> dict:
    return skill_api.make_user("skill-other-id", "skill_other")


@pytest.fixture
def skill_admin(skill_api: SkillApi) -> dict:
    return skill_api.make_user("skill-admin-id", "skill_admin", role="admin")


@pytest.fixture
def skill_owner_session(skill_api: SkillApi) -> dict:
    """Owner headers backed by a real login session (see ``SkillApi.login``)."""
    return skill_api.login("skill-owner-id", "skill_owner")


@pytest.fixture
def skill_audit(monkeypatch) -> list[dict]:
    """Record every ``log_audit_event`` call as a dict (metadata only)."""
    from src.services.logging_service import logging_service

    events: list[dict] = []

    def _record(**kwargs):
        events.append(kwargs)

    monkeypatch.setattr(logging_service, "log_audit_event", _record)
    return events
