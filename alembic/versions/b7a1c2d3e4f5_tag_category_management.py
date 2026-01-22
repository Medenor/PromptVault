# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""tag_category_management

Revision ID: b7a1c2d3e4f5
Revises: ccdab5b31836
Create Date: 2026-01-22 12:30:00.000000

"""
from typing import Sequence, Union, Set

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a1c2d3e4f5'
down_revision: Union[str, Sequence[str], None] = 'ccdab5b31836'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> Set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column['name'] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    category_columns = _column_names('categories')
    tag_columns = _column_names('tags')

    if 'color' not in category_columns:
        op.add_column('categories', sa.Column('color', sa.String(length=20), nullable=True))
    if 'updated_at' not in category_columns:
        op.add_column(
            'categories',
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
        )
    if 'sort_order' not in category_columns:
        op.add_column('categories', sa.Column('sort_order', sa.Integer(), nullable=True))

    if 'description' not in tag_columns:
        op.add_column('tags', sa.Column('description', sa.Text(), nullable=True))
    if 'color' not in tag_columns:
        op.add_column('tags', sa.Column('color', sa.String(length=20), nullable=True))
    if 'updated_at' not in tag_columns:
        op.add_column(
            'tags',
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
        )
    if 'parent_tag_id' not in tag_columns:
        with op.batch_alter_table('tags') as batch_op:
            batch_op.add_column(sa.Column('parent_tag_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_tags_parent_tag',
                'tags',
                ['parent_tag_id'],
                ['id'],
                ondelete='SET NULL',
            )
            batch_op.create_index('ix_tags_parent_tag_id', ['parent_tag_id'], unique=False)

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_categories_name_lower ON categories (lower(name))")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tags_name_lower ON tags (lower(name))")

    # Backfill updated_at for existing rows (SQLite cannot add non-constant defaults)
    op.execute("UPDATE categories SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    op.execute("UPDATE tags SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS uq_tags_name_lower")
    op.execute("DROP INDEX IF EXISTS uq_categories_name_lower")

    with op.batch_alter_table('tags') as batch_op:
        batch_op.drop_index('ix_tags_parent_tag_id')
        batch_op.drop_constraint('fk_tags_parent_tag', type_='foreignkey')
        batch_op.drop_column('parent_tag_id')
    op.execute('ALTER TABLE tags DROP COLUMN IF EXISTS updated_at')
    op.execute('ALTER TABLE tags DROP COLUMN IF EXISTS color')
    op.execute('ALTER TABLE tags DROP COLUMN IF EXISTS description')

    op.execute('ALTER TABLE categories DROP COLUMN IF EXISTS sort_order')
    op.execute('ALTER TABLE categories DROP COLUMN IF EXISTS updated_at')
    op.execute('ALTER TABLE categories DROP COLUMN IF EXISTS color')
