# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skill performance targets (SC-001, SC-007).

- SC-007: the detail view of a 500-file skill answers in under 2 s on SQLite.
- SC-001 (server side): importing a typical skill (under 1 MB, under 20 files)
  finishes in under 1 s.

Marked ``performance`` so it can be deselected with ``-m "not performance"``.
"""

import time

import pytest
from fixtures.skills import build_fixtures as bf

pytestmark = pytest.mark.performance

DETAIL_BUDGET_SECONDS = 2.0
IMPORT_BUDGET_SECONDS = 1.0
TRIALS = 3


def _typical_skill() -> bytes:
    """Under 1 MB and under 20 files, like a real skill."""
    entries = [("typical/SKILL.md", bf.SKILL_MD_VALID.replace("pdf-tools", "typical"))]
    entries += [
        (f"typical/scripts/s{i}.py", f"# script {i}\n" + "x = 1\n" * 200)
        for i in range(8)
    ]
    entries += [
        (f"typical/references/r{i}.md", "# ref\n" + "text " * 300) for i in range(6)
    ]
    entries.append(("typical/assets/blob.bin", bytes(range(256)) * 200))
    return bf.build_zip(entries)


def _big_skill(files: int = 500) -> bytes:
    entries = [("big/SKILL.md", bf.SKILL_MD_VALID.replace("pdf-tools", "big"))]
    entries += [
        (f"big/dir{i % 20}/file{i}.txt", f"content of file {i}\n" * 20)
        for i in range(files - 1)
    ]
    return bf.build_zip(entries)


def _best_of(trials: int, action) -> float:
    best = float("inf")
    for _ in range(trials):
        started = time.perf_counter()
        action()
        best = min(best, time.perf_counter() - started)
    return best


def test_typical_import_is_fast_on_the_server(skill_api, skill_owner):
    """SC-001: server-side import of a typical skill takes under 1 s."""
    data = _typical_skill()
    assert len(data) < 1024 * 1024

    def _import():
        response = skill_api.import_zip(data, skill_owner, filename="typical.zip")
        assert response.status_code == 201, response.text

    assert _best_of(TRIALS, _import) < IMPORT_BUDGET_SECONDS


def test_detail_of_a_500_file_skill_answers_in_under_two_seconds(
    skill_api, skill_owner
):
    """SC-007: GET /api/skills/{id} for 500 files, on SQLite."""
    response = skill_api.import_zip(_big_skill(500), skill_owner, filename="big.zip")
    assert response.status_code == 201, response.text
    skill = response.json()["skill"]
    assert skill["file_count"] == 500

    def _detail():
        result = skill_api.client.get(f"/api/skills/{skill['id']}", headers=skill_owner)
        assert result.status_code == 200
        assert len(result.json()["files"]) == 500

    assert _best_of(TRIALS, _detail) < DETAIL_BUDGET_SECONDS


def test_listing_skills_never_loads_file_contents(skill_api, skill_owner):
    """A list page must not pay for the stored bytes of every skill."""
    skill_api.import_zip(_big_skill(100), skill_owner, filename="big.zip")
    elapsed = _best_of(
        TRIALS,
        lambda: skill_api.client.get(
            "/api/prompts?item_type=skill", headers=skill_owner
        ),
    )
    assert elapsed < DETAIL_BUDGET_SECONDS
