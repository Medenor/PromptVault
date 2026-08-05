# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_prompt_legacy_public

Adds ``prompts.legacy_public`` and grandfathers every row that existed before
this migration ran by setting it to True (view-only visibility for all
authenticated users until the owner/an admin opts the prompt into the new
private model). New prompts created after this migration default to False.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'prompts',
        sa.Column('legacy_public', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # Grandfather every row that existed before this migration ran.
    prompts = sa.table('prompts', sa.column('legacy_public', sa.Boolean()))
    op.execute(prompts.update().values(legacy_public=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('prompts', 'legacy_public')
