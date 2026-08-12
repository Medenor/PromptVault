# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""End-to-end round-trip tests for BackupService (SQLite): create backup,
mutate the live database, restore, and verify the data matches the
pre-mutation snapshot exactly.

These exercise the real create_backup -> restore_backup path (VACUUM INTO,
sqlite3 Connection.backup()) rather than mocking file I/O, since this is the
data-loss-class code path called out in Phase 6 of the refactor plan. They
are a regression guard to run before/after extracting backup_service_db.py
into separate creation/restore/dump-strategy modules.
"""

import os
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Prompt
from src.services.exceptions import BackupError


def _prompt_snapshot(session):
    return {
        p.id: (p.title, p.prompt, p.note, p.favorite)
        for p in session.query(Prompt).all()
    }


@pytest.fixture
def onfile_db_session(db_backup_service, monkeypatch):
    """Session factory bound to the same on-disk SQLite file that
    db_backup_service reads DATABASE_URL from, so writes made through this
    fixture are visible to _create_sqlite_backup's VACUUM INTO and are
    actually overwritten by _restore_sqlite_backup's Connection.backup().

    db_backup_service.create_backup/restore_backup dispose and reopen
    src.db.session.engine directly, so each yielded session here is opened
    fresh per use rather than reusing a long-lived engine/connection that
    restore could invalidate out from under us.
    """
    from src.db import config as config_module

    db_url = config_module.db_settings.DATABASE_URL

    @contextmanager
    def _session():
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()

    return _session


class TestSqliteFullRoundtrip:
    def test_create_then_restore_preserves_exact_state(
        self, db_backup_service, onfile_db_session
    ):
        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Alpha", prompt="Alpha body", note="n1"))
            session.add(Prompt(id=2, title="Beta", prompt="Beta body", note="n2"))
            session.commit()

        with onfile_db_session() as session:
            pre_mutation_snapshot = _prompt_snapshot(session)

        backup_id = db_backup_service.create_backup("roundtrip")
        assert backup_id is not None

        # Mutate the live DB after the backup was taken.
        with onfile_db_session() as session:
            session.query(Prompt).filter_by(id=1).update({"title": "Mutated"})
            session.add(Prompt(id=3, title="Gamma", prompt="Gamma body", note="n3"))
            session.commit()

        with onfile_db_session() as session:
            mutated_snapshot = _prompt_snapshot(session)
        assert mutated_snapshot != pre_mutation_snapshot

        assert db_backup_service.restore_backup(backup_id) is True

        with onfile_db_session() as session:
            restored_snapshot = _prompt_snapshot(session)

        assert restored_snapshot == pre_mutation_snapshot

    def test_restore_creates_pre_restore_safety_backup(
        self, db_backup_service, onfile_db_session
    ):
        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Alpha", prompt="Alpha body"))
            session.commit()

        backup_id = db_backup_service.create_backup("roundtrip-safety")

        with onfile_db_session() as session:
            session.query(Prompt).filter_by(id=1).update({"title": "Changed"})
            session.commit()

        backups_before = {b["backup_id"] for b in db_backup_service.list_backups()}
        assert db_backup_service.restore_backup(backup_id) is True
        backups_after = {b["backup_id"] for b in db_backup_service.list_backups()}

        new_backups = backups_after - backups_before
        assert any(bid.startswith("backup_pre_restore_") for bid in new_backups)

    def test_restore_nonexistent_backup_raises_and_does_not_mutate_db(
        self, db_backup_service, onfile_db_session
    ):
        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Alpha", prompt="Alpha body"))
            session.commit()

        with onfile_db_session() as session:
            before = _prompt_snapshot(session)

        with pytest.raises(BackupError, match="Backup not found"):
            db_backup_service.restore_backup("does-not-exist")

        with onfile_db_session() as session:
            after = _prompt_snapshot(session)
        assert before == after

    def test_encrypted_backup_round_trip_preserves_state(
        self, db_backup_service, onfile_db_session
    ):
        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Secret", prompt="Secret body"))
            session.commit()

        with onfile_db_session() as session:
            pre_mutation_snapshot = _prompt_snapshot(session)

        backup_id = db_backup_service.create_backup(
            "encrypted-roundtrip", encrypt=True, passphrase="correct horse battery"
        )
        assert backup_id is not None

        with onfile_db_session() as session:
            session.query(Prompt).filter_by(id=1).update({"title": "Tampered"})
            session.commit()

        assert (
            db_backup_service.restore_backup(
                backup_id, passphrase="correct horse battery"
            )
            is True
        )

        with onfile_db_session() as session:
            restored_snapshot = _prompt_snapshot(session)
        assert restored_snapshot == pre_mutation_snapshot

    def test_encrypted_backup_restore_wrong_passphrase_fails_cleanly(
        self, db_backup_service, onfile_db_session
    ):
        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Secret", prompt="Secret body"))
            session.commit()

        backup_id = db_backup_service.create_backup(
            "encrypted-wrong-pass", encrypt=True, passphrase="right passphrase"
        )

        with pytest.raises(BackupError, match="Decryption failed"):
            db_backup_service.restore_backup(backup_id, passphrase="wrong passphrase")

    def test_compressed_backup_round_trip_preserves_state(
        self, db_backup_service, onfile_db_session
    ):
        import gzip
        import shutil as shutil_mod

        with onfile_db_session() as session:
            session.add(Prompt(id=1, title="Zipped", prompt="Zipped body"))
            session.commit()

        with onfile_db_session() as session:
            pre_mutation_snapshot = _prompt_snapshot(session)

        backup_id = db_backup_service.create_backup("compressed-roundtrip")
        info = db_backup_service.get_backup_info(backup_id)
        storage_path = info["storage_path"]

        compressed_path = storage_path + ".gz"
        with open(storage_path, "rb") as src, gzip.open(compressed_path, "wb") as dst:
            shutil_mod.copyfileobj(src, dst)
        os.remove(storage_path)

        info["storage_path"] = compressed_path
        info["filename"] = os.path.basename(compressed_path)
        db_backup_service._update_backup_record(backup_id, info)

        with onfile_db_session() as session:
            session.query(Prompt).filter_by(id=1).update({"title": "Changed"})
            session.commit()

        assert db_backup_service.restore_backup(backup_id) is True

        with onfile_db_session() as session:
            restored_snapshot = _prompt_snapshot(session)
        assert restored_snapshot == pre_mutation_snapshot


class TestPgRestoreDispatch:
    """PostgreSQL round-trip requires a live pg server, so verify only the
    dispatch/command-construction path here with subprocess mocked."""

    def test_restore_pg_backup_invokes_psql_with_expected_args(
        self, db_backup_service, patched_db_session, temp_data_dir, monkeypatch
    ):
        from src.db import config as config_module
        from src.db.models import Backup

        monkeypatch.setattr(
            config_module.db_settings,
            "DATABASE_URL",
            "postgresql://user:pass@localhost/testdb",
        )

        dump_path = os.path.join(temp_data_dir, "backups", "pgbackup.sql")
        os.makedirs(os.path.dirname(dump_path), exist_ok=True)
        with open(dump_path, "w", encoding="utf-8") as fh:
            fh.write("-- fake dump\n")

        with patched_db_session() as session:
            session.add(
                Backup(
                    id="pg-backup-1",
                    backup_type="pg_dump",
                    filename="pgbackup.sql",
                    storage_path=dump_path,
                    succeeded=True,
                )
            )
            session.commit()

        captured_cmd = {}

        class FakeResult:
            stderr = ""

        def fake_run(cmd, check, capture_output, text):
            captured_cmd["cmd"] = cmd
            return FakeResult()

        monkeypatch.setattr("subprocess.run", fake_run)
        monkeypatch.setattr(
            db_backup_service, "create_backup", lambda *a, **k: "pre-restore-fake"
        )

        assert db_backup_service.restore_backup("pg-backup-1") is True
        assert captured_cmd["cmd"][0] == "psql"
        assert dump_path in captured_cmd["cmd"]
