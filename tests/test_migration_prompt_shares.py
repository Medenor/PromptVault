# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Migration round-trip tests for the ``prompt_shares`` table.

Exercises upgrade -> downgrade -> upgrade on SQLite (always) and PostgreSQL
(only when DATABASE_URL points at a Postgres instance), asserting the table,
constraints, and index appear and disappear as expected.
"""

import os
import tempfile

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import command

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

PG_DATABASE_URL = os.environ.get("DATABASE_URL", "")
PG_AVAILABLE = PG_DATABASE_URL.startswith("postgresql")


def _alembic_config(db_url: str) -> Config:
    cfg = Config(os.path.join(REPO_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(REPO_ROOT, "alembic"))
    cfg.set_main_option("sqlalchemy.url", db_url)
    return cfg


def _table_exists(engine, table_name: str) -> bool:
    inspector = sa.inspect(engine)
    return table_name in inspector.get_table_names()


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


def _run_roundtrip_body(cfg: Config, db_url: str) -> None:
    # Build the schema as of the revision just before ours directly via the
    # ORM metadata (Base.metadata.create_all()) rather than replaying the
    # full Alembic chain from empty: an unrelated pre-existing migration
    # (da013146c222) uses Postgres-only DDL ('DROP CONSTRAINT ... CASCADE')
    # that fails on SQLite, and this is not a regression to fix here — the
    # app itself never replays that chain on SQLite either (it provisions
    # dev/test databases via create_all_tables(), same as this helper).
    #
    # The ORM models already declare PromptShare and Prompt.legacy_public
    # (this feature's own additions), so create_all() brings them into
    # existence too; drop/undo them immediately so the migrations under test
    # have real work to do, without mutating the shared Base.metadata object
    # (which other tests in the same process rely on).
    import src.db.models  # noqa: F401 — populate Base.metadata
    from src.db.base import Base

    engine = sa.create_engine(db_url)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(sa.text("DROP TABLE prompt_shares"))
        conn.execute(sa.text("ALTER TABLE prompts DROP COLUMN legacy_public"))
    engine.dispose()
    command.stamp(cfg, "f1a2b3c4d5e6")

    # Upgrade to just before the shares migration, confirm table absent.
    engine = sa.create_engine(db_url)
    assert not _table_exists(engine, "prompt_shares")
    engine.dispose()

    # Upgrade through the shares migration.
    command.upgrade(cfg, "a1b2c3d4e5f6")
    engine = sa.create_engine(db_url)
    assert _table_exists(engine, "prompt_shares")

    inspector = sa.inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("prompt_shares")}
    assert columns == {
        "id",
        "prompt_id",
        "grantee_user_id",
        "permission",
        "granted_by",
        "created_at",
        "updated_at",
    }

    unique_constraints = inspector.get_unique_constraints("prompt_shares")
    assert any(
        uc["name"] == "uq_prompt_shares_prompt_grantee"
        and set(uc["column_names"]) == {"prompt_id", "grantee_user_id"}
        for uc in unique_constraints
    )

    indexes = inspector.get_indexes("prompt_shares")
    assert any(
        idx["name"] == "idx_prompt_shares_grantee"
        and idx["column_names"] == ["grantee_user_id"]
        for idx in indexes
    )
    engine.dispose()

    # Downgrade removes the table.
    command.downgrade(cfg, "f1a2b3c4d5e6")
    engine = sa.create_engine(db_url)
    assert not _table_exists(engine, "prompt_shares")
    engine.dispose()

    # Upgrade again — idempotent-looking round trip works.
    command.upgrade(cfg, "a1b2c3d4e5f6")
    engine = sa.create_engine(db_url)
    assert _table_exists(engine, "prompt_shares")
    engine.dispose()

    # Leave the schema at head for downstream migrations sharing this DB file.
    command.upgrade(cfg, "head")


def test_prompt_shares_migration_roundtrip_sqlite():
    """Upgrade -> downgrade -> upgrade of the prompt_shares migration on SQLite."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "migration_test.db")
        db_url = f"sqlite:///{db_path}"
        _run_roundtrip(db_url)


@pytest.mark.skipif(not PG_AVAILABLE, reason="DATABASE_URL is not a PostgreSQL URL")
def test_prompt_shares_migration_roundtrip_postgres():
    """Upgrade -> downgrade -> upgrade of the prompt_shares migration on PostgreSQL."""
    _run_roundtrip(PG_DATABASE_URL)
