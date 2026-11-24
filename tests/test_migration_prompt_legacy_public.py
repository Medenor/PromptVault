# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Migration round-trip tests for ``prompts.legacy_public``.

Verifies the grandfathering data migration: rows that existed before the
migration ran land ``legacy_public=True``; a row inserted after upgrade
defaults to ``False``. Also exercises upgrade -> downgrade -> upgrade on
SQLite (always) and PostgreSQL (only when DATABASE_URL points at Postgres).
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

PRE_MIGRATION_REVISION = "a1b2c3d4e5f6"  # add_prompt_shares_table (just before)
TARGET_REVISION = "b2c3d4e5f6a7"  # add_prompt_legacy_public


def _alembic_config(db_url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _insert_prompt(engine, title: str) -> int:
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
        result = conn.execute(
            sa.text(
                "INSERT INTO prompts (title, prompt, favorite, user_id) "
                "VALUES (:title, 'content', false, :user_id) RETURNING id"
            ),
            {"title": title, "user_id": user_id},
        )
        return int(result.scalar_one())


def _get_legacy_public(engine, title: str):
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT legacy_public FROM prompts WHERE title = :title"),
            {"title": title},
        ).first()
        return bool(row[0]) if row is not None else None


def _run_roundtrip(db_url: str) -> None:
    # alembic/env.py overrides the Config's sqlalchemy.url with the
    # src.db.config.db_settings singleton's DATABASE_URL (already constructed
    # at import time), so the singleton must be patched directly — setting
    # the DATABASE_URL env var alone has no effect on it.
    from src.db.config import db_settings

    cfg = _alembic_config(db_url)
    original_url = db_settings.DATABASE_URL
    db_settings.DATABASE_URL = db_url
    try:
        _run_roundtrip_body(cfg, db_url)
    finally:
        db_settings.DATABASE_URL = original_url


def _seed_pre_legacy_public_schema(db_url: str, cfg: Config) -> None:
    """Build the schema as of revision a1b2c3d4e5f6 without replaying history.

    Mirrors test_migration_prompt_shares._seed_pre_shares_schema: an
    unrelated pre-existing migration (da013146c222) uses Postgres-only DDL
    that fails on SQLite, so a from-empty ``alembic upgrade`` replay is not
    viable here — same as the app itself, which provisions SQLite DBs via
    Base.metadata.create_all() rather than replaying the full chain. Create
    every table via ORM metadata (prompt_shares included, since it precedes
    this migration), stripping the legacy_public column this feature's own
    models already declare, then stamp Alembic at a1b2c3d4e5f6 so upgrade()/
    downgrade() only exercise the migration under test.
    """
    import src.db.models  # noqa: F401 -- populate Base.metadata
    from src.db.base import Base

    engine = sa.create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    # legacy_public does not exist yet at this revision; the ORM model
    # already declares it (this feature's own addition), so drop it back off
    # the freshly created table — SQLite 3.35+ supports DROP COLUMN natively.
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE prompts DROP COLUMN legacy_public"))
    engine.dispose()
    command.stamp(cfg, PRE_MIGRATION_REVISION)


def _run_roundtrip_body(cfg: Config, db_url: str) -> None:
    # Seed a row before the legacy_public migration runs.
    _seed_pre_legacy_public_schema(db_url, cfg)
    engine = sa.create_engine(db_url)
    _insert_prompt(engine, "pre-existing-prompt")
    engine.dispose()

    # Upgrade through the legacy_public migration — pre-existing row is grandfathered.
    command.upgrade(cfg, TARGET_REVISION)
    engine = sa.create_engine(db_url)
    assert _get_legacy_public(engine, "pre-existing-prompt") is True

    # A row inserted after upgrade defaults to False.
    _insert_prompt(engine, "post-migration-prompt")
    assert _get_legacy_public(engine, "post-migration-prompt") is False
    engine.dispose()

    # Downgrade removes the column.
    command.downgrade(cfg, PRE_MIGRATION_REVISION)
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("prompts")}
    assert "legacy_public" not in columns
    engine.dispose()

    # Upgrade again — round trip works.
    command.upgrade(cfg, TARGET_REVISION)
    engine = sa.create_engine(db_url)
    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("prompts")}
    assert "legacy_public" in columns
    engine.dispose()

    command.upgrade(cfg, "head")


def test_legacy_public_migration_roundtrip_sqlite():
    """Upgrade -> downgrade -> upgrade of the legacy_public migration on SQLite."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "migration_test.db")
        db_url = f"sqlite:///{db_path}"
        _run_roundtrip(db_url)


@pytest.mark.skipif(not PG_AVAILABLE, reason="DATABASE_URL is not a PostgreSQL URL")
def test_legacy_public_migration_roundtrip_postgres():
    """Upgrade -> downgrade -> upgrade of the legacy_public migration on PostgreSQL."""
    _run_roundtrip(PG_DATABASE_URL)
