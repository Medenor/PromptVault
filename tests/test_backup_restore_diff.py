# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for compute_restore_diff and selective_restore in BackupService."""

import os
import sqlite3
import shutil
import tempfile

import pytest

from src.db.models import Backup, Prompt
from src.services.exceptions import BackupError


@pytest.fixture
def backup_with_sqlite_copy(db_backup_service, patched_db_session, temp_data_dir):
    backup_db_path = os.path.join(temp_data_dir, "backups", "test_backup.db")
    conn = sqlite3.connect(backup_db_path)
    conn.execute("""
        CREATE TABLE prompts (
            id INTEGER PRIMARY KEY,
            title TEXT,
            prompt TEXT,
            note TEXT,
            favorite INTEGER DEFAULT 0,
            category_id INTEGER,
            semantic_version TEXT
        )
    """)
    conn.execute("INSERT INTO prompts VALUES (1, 'Backup Prompt 1', 'Content B1', 'Note B1', 0, NULL, '1.0')")
    conn.execute("INSERT INTO prompts VALUES (2, 'Backup Prompt 2', 'Content B2', 'Note B2', 1, NULL, '1.0')")
    conn.execute("INSERT INTO prompts VALUES (3, 'Only In Backup', 'Content B3', 'Note B3', 0, NULL, '1.0')")
    conn.commit()
    conn.close()

    with patched_db_session() as session:
        backup = Backup(
            id="backup-diff-test",
            backup_type="sqlite_copy",
            filename="test_backup.db",
            storage_path=backup_db_path,
            size_bytes=os.path.getsize(backup_db_path),
            succeeded=True,
        )
        session.add(backup)
        session.commit()

    return db_backup_service


@pytest.fixture
def current_prompts(patched_db_session):
    with patched_db_session() as session:
        session.add(Prompt(id=1, title="Current Prompt 1", prompt="Content C1", note="Note C1"))
        session.add(Prompt(id=2, title="Backup Prompt 2", prompt="Content B2", note="Note B2"))
        session.add(Prompt(id=99, title="Only In Current", prompt="Content C99", note="Note C99"))
        session.commit()


class TestComputeRestoreDiff:
    def test_diff_shows_added_updated_deleted(
        self, backup_with_sqlite_copy, current_prompts
    ):
        diff = backup_with_sqlite_copy.compute_restore_diff("backup-diff-test")

        assert diff["backup_id"] == "backup-diff-test"
        assert diff["summary"]["added"] == 1
        assert diff["summary"]["updated"] == 1
        assert diff["summary"]["deleted"] == 1

        added_ids = {p["id"] for p in diff["changes"]["added"]}
        assert 3 in added_ids

        updated_ids = {p["id"] for p in diff["changes"]["updated"]}
        assert 1 in updated_ids

        deleted_ids = {p["id"] for p in diff["changes"]["deleted"]}
        assert 99 in deleted_ids

    def test_diff_updated_shows_before_after(
        self, backup_with_sqlite_copy, current_prompts
    ):
        diff = backup_with_sqlite_copy.compute_restore_diff("backup-diff-test")
        updated = [p for p in diff["changes"]["updated"] if p["id"] == 1][0]
        assert updated["before"]["title"] == "Current Prompt 1"
        assert updated["after"]["title"] == "Backup Prompt 1"

    def test_diff_no_changes_when_identical(self, db_backup_service, patched_db_session, temp_data_dir):
        with patched_db_session() as session:
            session.add(Prompt(id=1, title="Same", prompt="Same Content"))
            session.commit()

        backup_db_path = os.path.join(temp_data_dir, "backups", "identical.db")
        conn = sqlite3.connect(backup_db_path)
        conn.execute("""
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY, title TEXT, prompt TEXT,
                note TEXT, favorite INTEGER, category_id INTEGER, semantic_version TEXT
            )
        """)
        conn.execute("INSERT INTO prompts VALUES (1, 'Same', 'Same Content', NULL, 0, NULL, '1.0')")
        conn.commit()
        conn.close()

        with patched_db_session() as session:
            session.add(Backup(
                id="backup-identical", backup_type="sqlite_copy",
                filename="identical.db", storage_path=backup_db_path,
                succeeded=True,
            ))
            session.commit()

        diff = db_backup_service.compute_restore_diff("backup-identical")
        assert diff["summary"]["added"] == 0
        assert diff["summary"]["updated"] == 0
        assert diff["summary"]["deleted"] == 0

    def test_diff_raises_for_nonexistent_backup(self, db_backup_service):
        with pytest.raises(BackupError, match="Backup not found"):
            db_backup_service.compute_restore_diff("nonexistent-backup")

    def test_diff_raises_for_missing_file(self, db_backup_service, patched_db_session):
        with patched_db_session() as session:
            session.add(Backup(
                id="backup-no-file", backup_type="sqlite_copy",
                filename="missing.db", storage_path="/nonexistent/path.db",
                succeeded=True,
            ))
            session.commit()

        with pytest.raises(BackupError, match="Backup file not found"):
            db_backup_service.compute_restore_diff("backup-no-file")

    def test_diff_content_truncated_to_200_chars(
        self, db_backup_service, patched_db_session, temp_data_dir
    ):
        long_content = "A" * 500

        with patched_db_session() as session:
            session.add(Prompt(id=1, title="T", prompt="short"))
            session.commit()

        backup_db_path = os.path.join(temp_data_dir, "backups", "trunc.db")
        conn = sqlite3.connect(backup_db_path)
        conn.execute("""
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY, title TEXT, prompt TEXT,
                note TEXT, favorite INTEGER, category_id INTEGER, semantic_version TEXT
            )
        """)
        conn.execute(f"INSERT INTO prompts VALUES (1, 'T', '{long_content}', NULL, 0, NULL, '1.0')")
        conn.commit()
        conn.close()

        with patched_db_session() as session:
            session.add(Backup(
                id="backup-trunc", backup_type="sqlite_copy",
                filename="trunc.db", storage_path=backup_db_path,
                succeeded=True,
            ))
            session.commit()

        diff = db_backup_service.compute_restore_diff("backup-trunc")
        for change in diff["changes"]["updated"]:
            assert len(change["after"]["prompt"]) <= 200


class TestSelectiveRestore:
    def test_selective_restore_existing_prompts(
        self, backup_with_sqlite_copy, current_prompts
    ):
        result = backup_with_sqlite_copy.selective_restore(
            "backup-diff-test",
            prompt_ids=[1],
            created_by="tester",
        )
        assert result["restored"] is True
        assert result["count"] == 1
        assert result["pre_restore_backup_id"] is not None

    def test_selective_restore_creates_new_prompt(
        self, backup_with_sqlite_copy, current_prompts
    ):
        result = backup_with_sqlite_copy.selective_restore(
            "backup-diff-test",
            prompt_ids=[3],
            created_by="tester",
        )
        assert result["restored"] is True
        assert result["count"] == 1

    def test_selective_restore_multiple_prompts(
        self, backup_with_sqlite_copy, current_prompts
    ):
        result = backup_with_sqlite_copy.selective_restore(
            "backup-diff-test",
            prompt_ids=[1, 2, 3],
            created_by="tester",
        )
        assert result["count"] == 3

    def test_selective_restore_skips_unknown_ids(
        self, backup_with_sqlite_copy, current_prompts
    ):
        result = backup_with_sqlite_copy.selective_restore(
            "backup-diff-test",
            prompt_ids=[999],
            created_by="tester",
        )
        assert result["count"] == 0

    def test_selective_restore_raises_for_nonexistent_backup(
        self, db_backup_service
    ):
        with pytest.raises(BackupError, match="Backup not found"):
            db_backup_service.selective_restore("nonexistent", prompt_ids=[1])

    def test_selective_restore_creates_safety_backup(
        self, backup_with_sqlite_copy, current_prompts
    ):
        result = backup_with_sqlite_copy.selective_restore(
            "backup-diff-test",
            prompt_ids=[1],
            created_by="tester",
        )
        assert result["pre_restore_backup_id"] is not None

        backups = backup_with_sqlite_copy.list_backups()
        backup_ids = [b["backup_id"] for b in backups]
        assert result["pre_restore_backup_id"] in backup_ids


class TestExtractPromptsFromBackup:
    def test_extract_from_sqlite_copy(self, db_backup_service, temp_data_dir):
        backup_path = os.path.join(temp_data_dir, "extract_test.db")
        conn = sqlite3.connect(backup_path)
        conn.execute("""
            CREATE TABLE prompts (
                id INTEGER PRIMARY KEY, title TEXT, prompt TEXT,
                note TEXT, favorite INTEGER, category_id INTEGER, semantic_version TEXT
            )
        """)
        conn.execute("INSERT INTO prompts VALUES (1, 'Test', 'Content', 'Note', 1, 5, '2.0')")
        conn.commit()
        conn.close()

        prompts = db_backup_service._extract_prompts_from_backup(backup_path, "sqlite_copy")
        assert len(prompts) == 1
        assert prompts[0]["id"] == 1
        assert prompts[0]["title"] == "Test"
        assert prompts[0]["prompt"] == "Content"
        assert prompts[0]["favorite"] is True
        assert prompts[0]["category_id"] == 5
        assert prompts[0]["semantic_version"] == "2.0"

    def test_extract_from_corrupt_file_returns_empty(self, db_backup_service, temp_data_dir):
        backup_path = os.path.join(temp_data_dir, "corrupt.db")
        with open(backup_path, "wb") as f:
            f.write(b"not a sqlite database")

        prompts = db_backup_service._extract_prompts_from_backup(backup_path, "sqlite_copy")
        assert prompts == []

    def test_extract_unknown_type_returns_empty(self, db_backup_service):
        prompts = db_backup_service._extract_prompts_from_backup("/any/path", "unknown_type")
        assert prompts == []
