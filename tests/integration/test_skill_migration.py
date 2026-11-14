# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Migration d4e5f6a7b8c9 (skill packages): upgrade, constraints, downgrade guard.

Runs on SQLite always and on PostgreSQL when ``TEST_DATABASE_URL`` (or
``DATABASE_URL``) points at one. The SQLite leg also proves the FTS5 sync
triggers survive both directions (why the migration avoids batch mode).
"""

import os
import tempfile
import uuid

import pytest
import sqlalchemy as sa
from alembic.config import Config
from fixtures.skills.schema_helpers import FEATURE_TABLES, pre_feature_metadata
from sqlalchemy.exc import IntegrityError

from alembic import command

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PG_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
PG_AVAILABLE = PG_URL.startswith("postgresql")

REV_PRE_FTS = "b2c3d4e5f6a7"
REV_FTS = "c3d4e5f6a7b8"
REV_PRE_SKILLS = "d80fb5792dda"
REV_SKILLS = "d4e5f6a7b8c9"


def _alembic_config(db_url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _insert_user(conn) -> str:
    user_id = str(uuid.uuid4())
    conn.execute(
        sa.text(
            "INSERT INTO users (id, username, email, password_hash, role) "
            "VALUES (:id, :username, :email, 'x', 'user')"
        ),
        {
            "id": user_id,
            "username": f"user_{user_id[:8]}",
            "email": f"{user_id[:8]}@example.com",
        },
    )
    return user_id


def _insert_prompt(engine, title: str, body: str, item_type: str | None = None) -> int:
    with engine.begin() as conn:
        user_id = _insert_user(conn)
        columns = "title, prompt, favorite, user_id, legacy_public"
        values = ":title, :body, false, :user_id, false"
        params = {"title": title, "body": body, "user_id": user_id}
        if item_type is not None:
            columns += ", item_type"
            values += ", :item_type"
            params["item_type"] = item_type
        conn.execute(
            sa.text(f"INSERT INTO prompts ({columns}) VALUES ({values})"), params
        )
        return conn.execute(
            sa.text("SELECT id FROM prompts WHERE title = :title"), {"title": title}
        ).scalar_one()


def _columns(engine, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(engine).get_columns(table)}


def _sqlite_triggers(engine) -> set[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
        )
        return {row[0] for row in rows}


def _fts_hits(engine, token: str) -> int:
    with engine.connect() as conn:
        return len(
            conn.execute(
                sa.text("SELECT rowid FROM prompts_fts WHERE prompts_fts MATCH :t"),
                {"t": token},
            ).fetchall()
        )


def _run(db_url: str) -> None:
    # alembic/env.py overrides the Config URL with the db_settings singleton.
    from src.db.config import db_settings

    cfg = _alembic_config(db_url)
    original = db_settings.DATABASE_URL
    db_settings.DATABASE_URL = db_url
    try:
        _run_body(cfg, db_url)
    finally:
        db_settings.DATABASE_URL = original


def _run_body(cfg: Config, db_url: str) -> None:
    is_sqlite = db_url.startswith("sqlite")
    engine = sa.create_engine(db_url)
    pre_feature_metadata().create_all(bind=engine)
    engine.dispose()

    # Bring the search layer to its real state (FTS5 triggers on SQLite).
    command.stamp(cfg, REV_PRE_FTS)
    command.upgrade(cfg, REV_FTS)
    command.stamp(cfg, REV_PRE_SKILLS)

    engine = sa.create_engine(db_url)
    assert "item_type" not in _columns(engine, "prompts")
    assert not FEATURE_TABLES & set(sa.inspect(engine).get_table_names())
    legacy_id = _insert_prompt(engine, "legacy-prompt", "pre-existing legacy_token")
    engine.dispose()

    # ---- upgrade -------------------------------------------------------
    command.upgrade(cfg, REV_SKILLS)
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    assert "item_type" in _columns(engine, "prompts")
    assert FEATURE_TABLES <= set(inspector.get_table_names())
    assert any(
        ix["name"] == "idx_prompts_item_type" for ix in inspector.get_indexes("prompts")
    )
    assert _columns(engine, "skill_packages") == {
        "prompt_id",
        "skill_identifier",
        "description",
        "total_bytes",
        "file_count",
        "format_warnings",
        "source_archive_name",
        "files_updated_at",
    }
    assert _columns(engine, "skill_files") == {
        "id",
        "prompt_id",
        "path",
        "path_folded",
        "size",
        "sha256",
        "is_text",
        "content",
    }
    assert any(
        uc["name"] == "uq_skill_files_prompt_path"
        and set(uc["column_names"]) == {"prompt_id", "path_folded"}
        for uc in inspector.get_unique_constraints("skill_files")
    )

    with engine.connect() as conn:
        item_type = conn.execute(
            sa.text("SELECT item_type FROM prompts WHERE id = :i"), {"i": legacy_id}
        ).scalar_one()
    assert item_type == "prompt"  # SC-005: existing rows become prompts

    with pytest.raises(IntegrityError):
        _insert_prompt(engine, "bad-type", "x", item_type="foo")

    if is_sqlite:
        assert {"prompts_fts_ai", "prompts_fts_ad", "prompts_fts_au"} <= (
            _sqlite_triggers(engine)
        )
        _insert_prompt(engine, "after-upgrade", "fresh_upgrade_token")
        assert _fts_hits(engine, "fresh_upgrade_token") == 1  # triggers still sync
        assert _fts_hits(engine, "legacy_token") == 1

    # Skill rows: file uniqueness is case-insensitive via path_folded.
    skill_id = _insert_prompt(engine, "a-skill", "skill body", item_type="skill")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO skill_files (prompt_id, path, path_folded, size, sha256, "
                "is_text, content) VALUES (:p, 'A.md', 'a.md', 1, :h, true, :c)"
            ),
            {"p": skill_id, "h": "0" * 64, "c": b"x"},
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO skill_files (prompt_id, path, path_folded, size, sha256, "
                "is_text, content) VALUES (:p, 'a.md', 'a.md', 1, :h, true, :c)"
            ),
            {"p": skill_id, "h": "0" * 64, "c": b"y"},
        )
    engine.dispose()

    # ---- downgrade is refused while a skill exists ----------------------
    with pytest.raises(RuntimeError, match="skill"):
        command.downgrade(cfg, REV_PRE_SKILLS)
    engine = sa.create_engine(db_url)
    assert "item_type" in _columns(engine, "prompts")  # nothing was changed
    assert FEATURE_TABLES <= set(sa.inspect(engine).get_table_names())

    with engine.begin() as conn:  # raw connection: no FK cascade PRAGMA on SQLite
        conn.execute(
            sa.text("DELETE FROM skill_files WHERE prompt_id = :i"), {"i": skill_id}
        )
        conn.execute(sa.text("DELETE FROM prompts WHERE id = :i"), {"i": skill_id})
    engine.dispose()

    # ---- downgrade without skills ---------------------------------------
    command.downgrade(cfg, REV_PRE_SKILLS)
    engine = sa.create_engine(db_url)
    assert "item_type" not in _columns(engine, "prompts")
    assert not FEATURE_TABLES & set(sa.inspect(engine).get_table_names())
    assert conn_scalar(engine, "SELECT COUNT(*) FROM prompts") >= 1
    if is_sqlite:
        assert {"prompts_fts_ai", "prompts_fts_ad", "prompts_fts_au"} <= (
            _sqlite_triggers(engine)
        )
        _insert_prompt(engine, "after-downgrade", "fresh_downgrade_token")
        assert _fts_hits(engine, "fresh_downgrade_token") == 1
    engine.dispose()

    # ---- upgrade again is clean ----------------------------------------
    command.upgrade(cfg, "head")
    engine = sa.create_engine(db_url)
    assert "item_type" in _columns(engine, "prompts")
    assert FEATURE_TABLES <= set(sa.inspect(engine).get_table_names())
    engine.dispose()


def conn_scalar(engine, sql: str):
    with engine.connect() as conn:
        return conn.execute(sa.text(sql)).scalar_one()


def test_skill_migration_sqlite():
    """Upgrade, constraints, downgrade guard and FTS triggers on SQLite."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        _run(f"sqlite:///{os.path.join(tmp_dir, 'skill_migration.db')}")


@pytest.mark.skipif(not PG_AVAILABLE, reason="no PostgreSQL URL configured")
def test_skill_migration_postgres():
    """Same checks against a throwaway PostgreSQL database.

    The migration leaves tables behind, so they are dropped afterwards to keep
    the other PostgreSQL-backed fixtures (which expect an empty database) valid.
    """
    from src.db.base import Base

    try:
        _run(PG_URL)
    finally:
        engine = sa.create_engine(PG_URL)
        try:
            Base.metadata.drop_all(bind=engine)
            with engine.begin() as conn:
                conn.execute(sa.text("DROP TABLE IF EXISTS alembic_version"))
        finally:
            engine.dispose()
