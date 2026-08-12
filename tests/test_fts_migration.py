# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Migration round-trip tests for full-text search (revision c3d4e5f6a7b8).

Verifies: upgrade -> downgrade -> upgrade replays cleanly on SQLite (always)
and PostgreSQL (only when DATABASE_URL points at Postgres, per T009's
cross-dialect matrix); the SQLite FTS5 table/triggers exist after upgrade
and are gone after downgrade; and the backfill populated existing rows.
"""

import os
import tempfile
import uuid

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PG_DATABASE_URL = os.environ.get("DATABASE_URL", "")
PG_AVAILABLE = PG_DATABASE_URL.startswith("postgresql")

PRE_MIGRATION_REVISION = "b2c3d4e5f6a7"  # add_prompt_legacy_public (just before)
TARGET_REVISION = "c3d4e5f6a7b8"  # full_text_search


def _alembic_config(db_url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _insert_prompt(engine, title: str, prompt_body: str = "content") -> None:
    with engine.begin() as conn:
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
        conn.execute(
            sa.text(
                "INSERT INTO prompts (title, prompt, favorite, user_id, legacy_public) "
                "VALUES (:title, :prompt_body, false, :user_id, false)"
            ),
            {"title": title, "prompt_body": prompt_body, "user_id": user_id},
        )


def _seed_pre_fts_schema(db_url: str, cfg: Config) -> None:
    """Build the schema as of revision b2c3d4e5f6a7 without replaying history.

    Mirrors test_migration_prompt_legacy_public._seed_pre_legacy_public_schema:
    an unrelated earlier migration uses Postgres-only DDL that fails on
    SQLite, so a from-empty ``alembic upgrade`` replay is not viable. Create
    every table via ORM metadata (matches the app's own SQLite provisioning
    via Base.metadata.create_all()), then stamp Alembic at
    b2c3d4e5f6a7 so upgrade()/downgrade() only exercise the FTS migration.
    """
    import src.db.models  # noqa: F401 -- populate Base.metadata
    from src.db.base import Base

    engine = sa.create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    engine.dispose()
    command.stamp(cfg, PRE_MIGRATION_REVISION)


def _run_roundtrip(db_url: str) -> None:
    # alembic/env.py overrides the Config's sqlalchemy.url with the
    # src.db.config.db_settings singleton's DATABASE_URL (already constructed
    # at import time), so the singleton must be patched directly.
    from src.db.config import db_settings

    cfg = _alembic_config(db_url)
    original_url = db_settings.DATABASE_URL
    db_settings.DATABASE_URL = db_url
    try:
        _run_roundtrip_body(cfg, db_url)
    finally:
        db_settings.DATABASE_URL = original_url


def _is_sqlite(db_url: str) -> bool:
    return db_url.startswith("sqlite")


def _run_roundtrip_body(cfg: Config, db_url: str) -> None:
    _seed_pre_fts_schema(db_url, cfg)

    # Seed a row before the FTS migration runs, to prove the backfill step.
    engine = sa.create_engine(db_url)
    _insert_prompt(
        engine, "pre-existing-title", "pre-existing unique_backfill_token body"
    )
    engine.dispose()

    # Upgrade through the FTS migration.
    command.upgrade(cfg, TARGET_REVISION)
    engine = sa.create_engine(db_url)

    if _is_sqlite(db_url):
        inspector = sa.inspect(engine)
        table_names = inspector.get_table_names()
        assert "prompts_fts" in table_names

        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT rowid FROM prompts_fts WHERE prompts_fts MATCH 'unique_backfill_token'"
                )
            ).fetchall()
        assert len(rows) == 1  # backfill populated the pre-existing row
    else:
        inspector = sa.inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("prompts")}
        assert "search_vector" in columns

        with engine.connect() as conn:
            rows = conn.execute(
                sa.text(
                    "SELECT id FROM prompts WHERE search_vector @@ to_tsquery('simple', 'unique_backfill_token')"
                )
            ).fetchall()
        assert len(rows) == 1  # backfill (implicit via generated column)
    engine.dispose()

    # Downgrade removes the FTS objects.
    command.downgrade(cfg, PRE_MIGRATION_REVISION)
    engine = sa.create_engine(db_url)
    if _is_sqlite(db_url):
        inspector = sa.inspect(engine)
        assert "prompts_fts" not in inspector.get_table_names()
    else:
        inspector = sa.inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("prompts")}
        assert "search_vector" not in columns
    engine.dispose()

    # Upgrade again — round trip works.
    command.upgrade(cfg, TARGET_REVISION)
    engine = sa.create_engine(db_url)
    if _is_sqlite(db_url):
        inspector = sa.inspect(engine)
        assert "prompts_fts" in inspector.get_table_names()
    else:
        inspector = sa.inspect(engine)
        columns = {c["name"] for c in inspector.get_columns("prompts")}
        assert "search_vector" in columns
    engine.dispose()

    command.upgrade(cfg, "head")


def test_fts_migration_roundtrip_sqlite():
    """Upgrade -> downgrade -> upgrade of the FTS migration on SQLite."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "fts_migration_test.db")
        db_url = f"sqlite:///{db_path}"
        _run_roundtrip(db_url)


@pytest.mark.skipif(not PG_AVAILABLE, reason="DATABASE_URL is not a PostgreSQL URL")
def test_fts_migration_roundtrip_postgres():
    """Upgrade -> downgrade -> upgrade of the FTS migration on PostgreSQL."""
    _run_roundtrip(PG_DATABASE_URL)
