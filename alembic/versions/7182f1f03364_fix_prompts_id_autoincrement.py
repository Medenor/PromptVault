"""fix_prompts_id_autoincrement

Revision ID: 7182f1f03364
Revises: 134639ee25d5
Create Date: 2025-11-28 14:21:46.665682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7182f1f03364'
down_revision: Union[str, Sequence[str], None] = '134639ee25d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Skip sequence creation for SQLite - it uses AUTOINCREMENT automatically
    if op.get_bind().dialect.name != 'sqlite':
        # Create sequence for prompts.id auto-increment
        op.execute("CREATE SEQUENCE IF NOT EXISTS prompts_id_seq")

        # Set the sequence as default for prompts.id column
        op.execute("ALTER TABLE prompts ALTER COLUMN id SET DEFAULT nextval('prompts_id_seq')")

        # Update the sequence to start after the current max ID
        op.execute("SELECT setval('prompts_id_seq', COALESCE((SELECT MAX(id) FROM prompts), 0) + 1, false)")


def downgrade() -> None:
    """Downgrade schema."""
    pass
