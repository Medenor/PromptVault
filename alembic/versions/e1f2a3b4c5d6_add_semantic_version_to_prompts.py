# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_semantic_version_to_prompts

Revision ID: e1f2a3b4c5d6
Revises: c8d9e0f1a2b3
Create Date: 2026-07-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('prompts', sa.Column('semantic_version', sa.String(20), nullable=True))
    op.add_column('prompt_versions', sa.Column('semantic_version', sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column('prompt_versions', 'semantic_version')
    op.drop_column('prompts', 'semantic_version')
