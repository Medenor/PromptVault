# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_prompt_shares_table

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'prompt_shares',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('grantee_user_id', sa.String(length=36), nullable=False),
        sa.Column(
            'permission',
            sa.Enum('read', 'edit', name='share_permission', native_enum=False, validate_strings=True),
            nullable=False,
        ),
        sa.Column('granted_by', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['prompt_id'], ['prompts.id'], name='fk_prompt_shares_prompt_id_prompts', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grantee_user_id'], ['users.id'], name='fk_prompt_shares_grantee_user_id_users', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], name='fk_prompt_shares_granted_by_users', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name='pk_prompt_shares'),
        sa.UniqueConstraint('prompt_id', 'grantee_user_id', name='uq_prompt_shares_prompt_grantee'),
    )
    op.create_index('idx_prompt_shares_grantee', 'prompt_shares', ['grantee_user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_prompt_shares_grantee', table_name='prompt_shares')
    op.drop_table('prompt_shares')
