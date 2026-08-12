# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""full_text_search

Adds native, index-backed full-text search over prompts.title/prompt/note.

- SQLite: an FTS5 external-content virtual table (``prompts_fts``) kept in
  sync by AFTER INSERT/UPDATE/DELETE triggers, backfilled from existing rows.
- PostgreSQL: a generated ``search_vector`` tsvector column (weighted
  title=A, prompt=B, note=C) with a GIN index; sync is automatic (generated
  column), backfill is implicit when the column is added.

One-time index build runs synchronously as part of this migration and may
take several seconds to minutes on large vaults (the app does not serve
requests until it completes).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    dialect = op.get_bind().dialect.name

    if dialect == 'sqlite':
        op.execute(
            """
            CREATE VIRTUAL TABLE prompts_fts USING fts5(
                title, prompt, note,
                content='prompts', content_rowid='id'
            )
            """
        )

        op.execute(
            """
            CREATE TRIGGER prompts_fts_ai AFTER INSERT ON prompts BEGIN
                INSERT INTO prompts_fts(rowid, title, prompt, note)
                VALUES (new.id, new.title, new.prompt, new.note);
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER prompts_fts_ad AFTER DELETE ON prompts BEGIN
                INSERT INTO prompts_fts(prompts_fts, rowid, title, prompt, note)
                VALUES ('delete', old.id, old.title, old.prompt, old.note);
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER prompts_fts_au AFTER UPDATE ON prompts BEGIN
                INSERT INTO prompts_fts(prompts_fts, rowid, title, prompt, note)
                VALUES ('delete', old.id, old.title, old.prompt, old.note);
                INSERT INTO prompts_fts(rowid, title, prompt, note)
                VALUES (new.id, new.title, new.prompt, new.note);
            END
            """
        )

        # Backfill from existing rows.
        op.execute(
            """
            INSERT INTO prompts_fts(rowid, title, prompt, note)
            SELECT id, title, prompt, note FROM prompts
            """
        )
    else:
        # Generated column is implicitly backfilled for existing rows when
        # added, and stays in sync automatically going forward (no trigger).
        op.execute(
            """
            ALTER TABLE prompts ADD COLUMN search_vector tsvector
            GENERATED ALWAYS AS (
                setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(prompt, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(note, '')), 'C')
            ) STORED
            """
        )
        op.execute(
            "CREATE INDEX idx_prompts_search_vector ON prompts USING GIN (search_vector)"
        )


def downgrade() -> None:
    """Downgrade schema."""
    dialect = op.get_bind().dialect.name

    if dialect == 'sqlite':
        op.execute("DROP TRIGGER IF EXISTS prompts_fts_ai")
        op.execute("DROP TRIGGER IF EXISTS prompts_fts_ad")
        op.execute("DROP TRIGGER IF EXISTS prompts_fts_au")
        op.execute("DROP TABLE IF EXISTS prompts_fts")
    else:
        op.execute("DROP INDEX IF EXISTS idx_prompts_search_vector")
        op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS search_vector")
