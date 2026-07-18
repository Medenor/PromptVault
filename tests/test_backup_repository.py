# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for BackupRepository."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from src.db.models.backup import Backup


def _make_backup(session, *, created_at, tag=None, kind="full"):
    backup = Backup(
        id=str(uuid.uuid4()),
        backup_type="sqlite_copy",
        filename=f"backup-{created_at.isoformat()}.db",
        storage_path=f"/data/backups/backup-{created_at.isoformat()}.db",
        created_at=created_at,
        backup_kind=kind,
        tags=[tag] if tag else [],
    )
    session.add(backup)
    session.flush()
    return backup


@pytest.fixture
def seeded_backups(test_db_session):
    now = datetime.now(timezone.utc)
    backups = {
        "oldest": _make_backup(
            test_db_session, created_at=now - timedelta(days=10), tag="weekly", kind="full"
        ),
        "middle": _make_backup(
            test_db_session, created_at=now - timedelta(days=5), tag="daily", kind="incremental"
        ),
        "newest": _make_backup(
            test_db_session, created_at=now - timedelta(days=1), tag="daily", kind="full"
        ),
    }
    test_db_session.commit()
    return backups


class TestListBackups:
    def test_list_backups_with_no_filters_returns_all_newest_first(
        self, backup_repo, seeded_backups
    ):
        result = backup_repo.list_backups()
        assert [b.id for b in result] == [
            seeded_backups["newest"].id,
            seeded_backups["middle"].id,
            seeded_backups["oldest"].id,
        ]

    def test_list_backups_with_tag_filter_returns_matching_only(
        self, backup_repo, seeded_backups
    ):
        result = backup_repo.list_backups(tag="weekly")
        assert [b.id for b in result] == [seeded_backups["oldest"].id]

    def test_list_backups_with_start_date_filter_excludes_older(
        self, backup_repo, seeded_backups
    ):
        cutoff = datetime.now(timezone.utc) - timedelta(days=6)
        result = backup_repo.list_backups(start_date=cutoff)
        ids = {b.id for b in result}
        assert ids == {seeded_backups["middle"].id, seeded_backups["newest"].id}

    def test_list_backups_with_end_date_filter_excludes_newer(
        self, backup_repo, seeded_backups
    ):
        cutoff = datetime.now(timezone.utc) - timedelta(days=6)
        result = backup_repo.list_backups(end_date=cutoff)
        assert [b.id for b in result] == [seeded_backups["oldest"].id]

    def test_list_backups_with_kind_filter_returns_matching_only(
        self, backup_repo, seeded_backups
    ):
        result = backup_repo.list_backups(kind="incremental")
        assert [b.id for b in result] == [seeded_backups["middle"].id]

    def test_list_backups_with_combined_filters_intersects(self, backup_repo, seeded_backups):
        result = backup_repo.list_backups(tag="daily", kind="full")
        assert [b.id for b in result] == [seeded_backups["newest"].id]

    def test_list_backups_respects_limit_and_offset(self, backup_repo, seeded_backups):
        result = backup_repo.list_backups(limit=1, offset=1)
        assert [b.id for b in result] == [seeded_backups["middle"].id]


class TestGetAllForCleanup:
    def test_get_all_for_cleanup_returns_all_ordered_oldest_first(
        self, backup_repo, seeded_backups
    ):
        result = backup_repo.get_all_for_cleanup()
        assert [b.id for b in result] == [
            seeded_backups["oldest"].id,
            seeded_backups["middle"].id,
            seeded_backups["newest"].id,
        ]

    def test_get_all_for_cleanup_returns_empty_list_when_no_backups(self, backup_repo):
        assert backup_repo.get_all_for_cleanup() == []


class TestCountWithFilters:
    def test_count_with_filters_with_no_filters_counts_all(self, backup_repo, seeded_backups):
        assert backup_repo.count_with_filters() == 3

    def test_count_with_filters_with_tag_filter(self, backup_repo, seeded_backups):
        assert backup_repo.count_with_filters(tag="daily") == 2

    def test_count_with_filters_with_date_range(self, backup_repo, seeded_backups):
        cutoff = datetime.now(timezone.utc) - timedelta(days=6)
        assert backup_repo.count_with_filters(start_date=cutoff) == 2

    def test_count_with_filters_with_kind_filter(self, backup_repo, seeded_backups):
        assert backup_repo.count_with_filters(kind="full") == 2

    def test_count_with_filters_with_combined_filters(self, backup_repo, seeded_backups):
        assert backup_repo.count_with_filters(tag="daily", kind="incremental") == 1
