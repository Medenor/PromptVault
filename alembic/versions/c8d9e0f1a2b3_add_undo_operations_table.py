# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_undo_operations_table

Revision ID: c8d9e0f1a2b3
Revises: b7a1c2d3e4f5
Create Date: 2026-01-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7a1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create undo_operations table
    op.create_table(
        'undo_operations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('operation', sa.String(length=20), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_undo_operations_user_id_users', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name='pk_undo_operations')
    )

    # Create indexes for efficient querying
    op.create_index('ix_undo_operations_user_created', 'undo_operations', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_undo_operations_expires_at', 'undo_operations', ['expires_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index('ix_undo_operations_expires_at', table_name='undo_operations')
    op.drop_index('ix_undo_operations_user_created', table_name='undo_operations')

    # Drop the table
    op.drop_table('undo_operations')
