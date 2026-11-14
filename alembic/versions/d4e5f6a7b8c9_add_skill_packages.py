# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_skill_packages

Adds skills as a second item type next to prompts (feature 011).

- ``prompts.item_type`` (``'prompt'`` | ``'skill'``, default ``'prompt'``),
  with a check constraint and an index. Existing rows become prompts through
  the server default, so no data migration is needed.
- ``skill_packages``: one row per skill (identifier, description, totals,
  format warnings).
- ``skill_files``: one row per stored file, content as BLOB/BYTEA, unique per
  (prompt_id, case-folded path).

Why no ``batch_alter_table`` on SQLite: batch mode rebuilds ``prompts`` (copy,
drop, rename), and dropping the table silently drops the FTS5 sync triggers
created by ``c3d4e5f6a7b8_full_text_search``. The column is therefore added
with an inline column CHECK, which SQLite supports in ``ADD COLUMN`` and can
later remove again with ``DROP COLUMN``.

The downgrade refuses to run while skill rows exist, so skills are never
silently turned into prompts.

Revision ID: d4e5f6a7b8c9
Revises: d80fb5792dda
Create Date: 2026-11-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'd80fb5792dda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CHECK_NAME = "ck_prompts_item_type"
_CHECK_SQL = "item_type IN ('prompt', 'skill')"


def _table_exists(conn, table: str) -> bool:
    """Check if a table exists."""
    return table in sa.inspect(conn).get_table_names()


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return False
    return column in [col["name"] for col in inspector.get_columns(table)]


def _index_exists(conn, table: str, index: str) -> bool:
    """Check if an index exists on a table."""
    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return False
    return index in [ix["name"] for ix in inspector.get_indexes(table)]


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    if not _column_exists(conn, "prompts", "item_type"):
        if conn.dialect.name == "sqlite":
            op.execute(
                sa.text(
                    "ALTER TABLE prompts ADD COLUMN item_type VARCHAR(16) "
                    f"NOT NULL DEFAULT 'prompt' CONSTRAINT {_CHECK_NAME} "
                    f"CHECK ({_CHECK_SQL})"
                )
            )
        else:
            op.add_column(
                "prompts",
                sa.Column(
                    "item_type",
                    sa.String(16),
                    nullable=False,
                    server_default="prompt",
                ),
            )
            op.create_check_constraint(op.f(_CHECK_NAME), "prompts", _CHECK_SQL)

    if not _index_exists(conn, "prompts", "idx_prompts_item_type"):
        op.create_index("idx_prompts_item_type", "prompts", ["item_type"])

    if not _table_exists(conn, "skill_packages"):
        op.create_table(
            "skill_packages",
            sa.Column("prompt_id", sa.Integer(), nullable=False),
            sa.Column("skill_identifier", sa.String(64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("total_bytes", sa.BigInteger(), nullable=False),
            sa.Column("file_count", sa.Integer(), nullable=False),
            sa.Column(
                "format_warnings",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column("source_archive_name", sa.String(255), nullable=False),
            sa.Column(
                "files_updated_at", sa.DateTime(timezone=True), nullable=False
            ),
            sa.ForeignKeyConstraint(
                ["prompt_id"],
                ["prompts.id"],
                name="fk_skill_packages_prompt_id_prompts",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("prompt_id", name="pk_skill_packages"),
        )
        op.create_index(
            "ix_skill_packages_skill_identifier",
            "skill_packages",
            ["skill_identifier"],
        )

    if not _table_exists(conn, "skill_files"):
        op.create_table(
            "skill_files",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("prompt_id", sa.Integer(), nullable=False),
            sa.Column("path", sa.String(1024), nullable=False),
            sa.Column("path_folded", sa.String(1024), nullable=False),
            sa.Column("size", sa.BigInteger(), nullable=False),
            sa.Column("sha256", sa.String(64), nullable=False),
            sa.Column(
                "is_text", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.ForeignKeyConstraint(
                ["prompt_id"],
                ["prompts.id"],
                name="fk_skill_files_prompt_id_prompts",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "prompt_id", "path_folded", name="uq_skill_files_prompt_path"
            ),
        )
        op.create_index("idx_skill_files_prompt", "skill_files", ["prompt_id"])


def downgrade() -> None:
    """Downgrade schema.

    Raises:
        RuntimeError: If skill rows exist, so skills are not turned into prompts.
    """
    conn = op.get_bind()

    if _column_exists(conn, "prompts", "item_type"):
        skill_rows = conn.execute(
            sa.text("SELECT COUNT(*) FROM prompts WHERE item_type = 'skill'")
        ).scalar()
        if skill_rows:
            raise RuntimeError(
                f"Cannot downgrade: {skill_rows} skill(s) exist. Delete or export "
                "them first, otherwise they would silently become prompts."
            )

    if _table_exists(conn, "skill_files"):
        op.drop_table("skill_files")
    if _table_exists(conn, "skill_packages"):
        op.drop_table("skill_packages")

    if _index_exists(conn, "prompts", "idx_prompts_item_type"):
        op.drop_index("idx_prompts_item_type", table_name="prompts")
    if _column_exists(conn, "prompts", "item_type"):
        if conn.dialect.name != "sqlite":
            op.drop_constraint(op.f(_CHECK_NAME), "prompts", type_="check")
        op.drop_column("prompts", "item_type")
