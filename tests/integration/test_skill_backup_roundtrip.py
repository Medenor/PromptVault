# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skills survive backup and restore (User Story 5, SC-006, FR-026, FR-027).

Backups of the SQLite database are file copies, so skills are included with no
skill-specific backup code. These tests prove it, and prove that a backup taken
before the skills migration still restores and upgrades cleanly.
"""

import hashlib
import os
import shutil
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from alembic.config import Config
from fixtures.skills import build_fixtures as bf
from fixtures.skills.schema_helpers import pre_feature_metadata
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from alembic import command
from src.db.models import Prompt, SkillFile, SkillPackage
from src.services.skills.skill_service import SkillService

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REV_PRE_SKILLS = "d80fb5792dda"
USER = SimpleNamespace(id="backup-user", username="backup_user", role="user")


def _second_skill_zip() -> bytes:
    return bf.build_zip(
        [
            (
                "second/SKILL.md",
                "---\nname: second\ndescription: Another one.\n---\n# Second\n",
            ),
            ("second/data/blob.bin", bytes(range(256)) * 40),
            ("second/notes/ünï.txt", "unicode path"),
        ]
    )


@pytest.fixture
def file_db(db_backup_service, monkeypatch):
    """Session factory bound to the on-disk SQLite file the backup service reads.

    Also points ``SkillService`` at that same file, so skills imported in the
    test are part of what gets backed up.
    """
    from src.db import config as config_module

    db_url = config_module.db_settings.DATABASE_URL

    @contextmanager
    def _session():
        engine = create_engine(db_url)
        session = sessionmaker(bind=engine)()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()

    monkeypatch.setattr("src.services.skills.skill_service.get_db_session", _session)
    return _session


def _fingerprint(session_factory, skill_id: int) -> dict:
    """Everything stored for a skill: metadata plus every file's bytes."""
    with session_factory() as session:
        prompt = session.get(Prompt, skill_id)
        package = session.get(SkillPackage, skill_id)
        files = {
            row.path: (bytes(row.content), row.sha256, row.size, row.is_text)
            for row in session.query(SkillFile).filter_by(prompt_id=skill_id)
        }
        return {
            "item_type": prompt.item_type,
            "title": prompt.title,
            "prompt": prompt.prompt,
            "identifier": package.skill_identifier,
            "description": package.description,
            "warnings": list(package.format_warnings),
            "file_count": package.file_count,
            "total_bytes": package.total_bytes,
            "files": files,
        }


class TestSkillsRoundTrip:
    def test_restore_returns_every_skill_byte_for_byte(
        self, db_backup_service, file_db
    ):
        service = SkillService()
        first = service.import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)["id"]
        second = service.import_skill(_second_skill_zip(), "second.zip", USER)["id"]
        before = {i: _fingerprint(file_db, i) for i in (first, second)}
        exports_before = {
            i: service.export_skill(i, USER).archive.read() for i in (first, second)
        }
        assert before[second]["files"]["data/blob.bin"][3] is False  # binary

        backup_id = db_backup_service.create_backup("skills-roundtrip")
        assert backup_id is not None

        # Wipe the skills and add an unrelated prompt, then restore.
        service.delete_skill(first, USER)
        service.delete_skill(second, USER)
        with file_db() as session:
            session.add(Prompt(title="Unrelated", prompt="x"))
        with file_db() as session:
            assert session.query(SkillFile).count() == 0

        assert db_backup_service.restore_backup(backup_id) is True

        after = {i: _fingerprint(file_db, i) for i in (first, second)}
        assert after == before
        for skill_id, original in exports_before.items():
            assert service.export_skill(skill_id, USER).archive.read() == original
        with file_db() as session:
            # sha256 of every stored file still matches its content
            for row in session.query(SkillFile):
                assert hashlib.sha256(bytes(row.content)).hexdigest() == row.sha256
            assert session.query(Prompt).filter_by(title="Unrelated").count() == 0

    def test_prompts_and_skills_restore_side_by_side(self, db_backup_service, file_db):
        service = SkillService()
        with file_db() as session:
            session.add(Prompt(id=900, title="Plain prompt", prompt="plain body"))
        skill_id = service.import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)["id"]
        backup_id = db_backup_service.create_backup("mixed")

        with file_db() as session:
            session.query(Prompt).filter_by(id=900).update({"title": "Changed"})
        service.delete_skill(skill_id, USER)

        assert db_backup_service.restore_backup(backup_id) is True
        with file_db() as session:
            assert session.get(Prompt, 900).title == "Plain prompt"
            assert session.get(Prompt, 900).item_type == "prompt"
            assert session.get(Prompt, skill_id).item_type == "skill"


class TestSelectiveRestoreSkipsSkills:
    def test_selective_restore_never_touches_a_skill_row(
        self, db_backup_service, file_db
    ):
        service = SkillService()
        skill_id = service.import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)["id"]
        backup_id = db_backup_service.create_backup("selective")

        with file_db() as session:
            row = session.get(Prompt, skill_id)
            row.prompt = "locally edited text"
        result = db_backup_service.selective_restore(backup_id, [skill_id])

        assert result["count"] == 0
        with file_db() as session:
            assert session.get(Prompt, skill_id).prompt == "locally edited text"
            assert session.query(SkillFile).filter_by(prompt_id=skill_id).count() == 3

    def test_selective_restore_does_not_recreate_a_deleted_skill_as_a_prompt(
        self, db_backup_service, file_db
    ):
        service = SkillService()
        skill_id = service.import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)["id"]
        backup_id = db_backup_service.create_backup("selective-deleted")
        service.delete_skill(skill_id, USER)

        result = db_backup_service.selective_restore(backup_id, [skill_id])

        assert result["count"] == 0
        with file_db() as session:
            assert session.get(Prompt, skill_id) is None

    def test_restore_diff_leaves_skills_out(self, db_backup_service, file_db):
        """A skill in the backup is not offered as an 'added' prompt-style change."""
        SkillService().import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)
        backup_id = db_backup_service.create_backup("diff")

        diff = db_backup_service.compute_restore_diff(backup_id)

        assert diff["summary"] == {"added": 0, "updated": 0, "deleted": 0}
        assert "pdf-tools" not in str(diff)


class TestPreFeatureBackup:
    def test_a_backup_from_before_skills_restores_and_upgrades(
        self, db_backup_service, file_db, monkeypatch, tmp_path
    ):
        from src.db import config as config_module

        live_url = config_module.db_settings.DATABASE_URL
        old_path = tmp_path / "pre_feature.db"
        old_url = f"sqlite:///{old_path}"

        # A database exactly as it was before this migration, with prompts in it.
        engine = create_engine(old_url)
        pre_feature_metadata().create_all(bind=engine)
        with engine.begin() as conn:
            for i in range(1, 4):
                conn.execute(
                    sa.text(
                        "INSERT INTO prompts (id, title, prompt, favorite, legacy_public)"
                        " VALUES (:i, :t, :p, false, false)"
                    ),
                    {"i": i, "t": f"Old prompt {i}", "p": f"body {i}"},
                )
        engine.dispose()
        cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
        monkeypatch.setattr(config_module.db_settings, "DATABASE_URL", old_url)
        command.stamp(cfg, REV_PRE_SKILLS)

        backup_id = db_backup_service.create_backup("pre-feature")
        assert backup_id is not None

        # Restore it over the live (current-schema) database.
        monkeypatch.setattr(config_module.db_settings, "DATABASE_URL", live_url)
        assert db_backup_service.restore_backup(backup_id) is True

        live_engine = create_engine(live_url)
        try:
            columns = {
                c["name"] for c in sa.inspect(live_engine).get_columns("prompts")
            }
            assert "item_type" not in columns  # really the old schema

            command.upgrade(cfg, "head")

            columns = {
                c["name"] for c in sa.inspect(live_engine).get_columns("prompts")
            }
            assert "item_type" in columns
            with live_engine.connect() as conn:
                types = conn.execute(
                    sa.text("SELECT DISTINCT item_type FROM prompts")
                ).fetchall()
                count = conn.execute(
                    sa.text("SELECT COUNT(*) FROM prompts")
                ).scalar_one()
            assert [row[0] for row in types] == ["prompt"]
            assert count == 3
            assert {"skill_packages", "skill_files"} <= set(
                sa.inspect(live_engine).get_table_names()
            )
        finally:
            live_engine.dispose()


PG_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
PG_READY = (
    PG_URL.startswith("postgresql")
    and shutil.which("pg_dump") is not None
    and shutil.which("psql") is not None
)


@pytest.mark.skipif(not PG_READY, reason="needs a PostgreSQL URL plus pg_dump and psql")
class TestPostgresRoundTrip:
    """SC-006 on PostgreSQL: skills (BYTEA contents) survive pg_dump and psql restore."""

    @pytest.fixture
    def pg_db(self, monkeypatch):
        from src.db import config as config_module
        from src.db.base import Base

        monkeypatch.setattr(config_module.db_settings, "DATABASE_URL", PG_URL)
        engine = create_engine(PG_URL)
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

        @contextmanager
        def _session():
            session = sessionmaker(bind=engine)()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        with _session() as session:
            from src.db.models import User

            session.add(
                User(
                    id=USER.id,
                    username=USER.username,
                    email="backup_user@example.com",
                    password_hash="x",
                    role="user",
                )
            )
        monkeypatch.setattr(
            "src.services.skills.skill_service.get_db_session", _session
        )
        yield _session
        Base.metadata.drop_all(engine)
        engine.dispose()

    def test_pg_dump_and_restore_return_every_skill_byte_for_byte(
        self, pg_db, tmp_path
    ):
        from src.services.backup_dump_strategy import PostgresDumpStrategy

        service = SkillService()
        first = service.import_skill(bf.valid_wrapped(), "pdf-tools.zip", USER)["id"]
        second = service.import_skill(_second_skill_zip(), "second.zip", USER)["id"]
        before = {i: _fingerprint(pg_db, i) for i in (first, second)}
        export_before = service.export_skill(first, USER).archive.read()
        assert before[second]["files"]["data/blob.bin"][3] is False  # binary

        strategy = PostgresDumpStrategy()
        dump_path = str(tmp_path / "skills.sql")
        strategy.dump(dump_path)

        service.delete_skill(first, USER)
        service.delete_skill(second, USER)
        with pg_db() as session:
            assert session.query(SkillFile).count() == 0

        assert strategy.restore("pg-skills", dump_path) is True

        assert {i: _fingerprint(pg_db, i) for i in (first, second)} == before
        assert service.export_skill(first, USER).archive.read() == export_before
        with pg_db() as session:
            for row in session.query(SkillFile):
                assert hashlib.sha256(bytes(row.content)).hexdigest() == row.sha256
