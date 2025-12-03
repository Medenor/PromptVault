# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Assign existing prompts to default system user.

This migration ensures all prompts have an owner by:
1. Creating a system admin user if it doesn't exist
2. Assigning all orphaned prompts (user_id = NULL) to this system user

Revision ID: ccdab5b31836
Revises: da013146c222
Create Date: 2025-12-03 08:53:56.459897
"""
from typing import Sequence, Union
from datetime import datetime, timezone
import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'ccdab5b31836'
down_revision: Union[str, Sequence[str], None] = 'da013146c222'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Assign orphaned prompts to a default system user.

    This migration:
    1. Checks if a system admin user exists
    2. Creates one if it doesn't exist
    3. Assigns all prompts with NULL user_id to this system user
    """
    connection = op.get_bind()

    # System admin user details
    system_user_id = '00000000-0000-0000-0000-000000000001'
    system_username = 'system_admin'
    system_email = 'system@promptvault.local'

    # Check if system user exists
    result = connection.execute(
        text("SELECT id FROM users WHERE id = :user_id"),
        {"user_id": system_user_id}
    )
    user_exists = result.fetchone() is not None

    # Create system user if it doesn't exist
    if not user_exists:
        # Note: password_hash is required but system user won't be used for login
        # We set a random unguessable hash
        dummy_hash = f"$argon2id$v=19$m=65536,t=3,p=4${str(uuid.uuid4())}"

        connection.execute(
            text("""
                INSERT INTO users (
                    id, username, email, password_hash, role,
                    is_active, email_verified, created_at
                )
                VALUES (
                    :id, :username, :email, :password_hash, :role,
                    :is_active, :email_verified, :created_at
                )
            """),
            {
                "id": system_user_id,
                "username": system_username,
                "email": system_email,
                "password_hash": dummy_hash,
                "role": "admin",
                "is_active": True,
                "email_verified": True,
                "created_at": datetime.now(timezone.utc),
            }
        )

    # Count orphaned prompts
    result = connection.execute(
        text("SELECT COUNT(*) FROM prompts WHERE user_id IS NULL")
    )
    orphaned_count = result.scalar()

    # Assign orphaned prompts to system user
    if orphaned_count > 0:
        connection.execute(
            text("""
                UPDATE prompts
                SET user_id = :user_id
                WHERE user_id IS NULL
            """),
            {"user_id": system_user_id}
        )

        print(f"Assigned {orphaned_count} orphaned prompts to system admin user")
    else:
        print("No orphaned prompts found - no action needed")


def downgrade() -> None:
    """Downgrade - set user_id back to NULL for system-assigned prompts.

    Note: This does NOT delete the system user as other data may reference it.
    """
    connection = op.get_bind()
    system_user_id = '00000000-0000-0000-0000-000000000001'

    # Set user_id back to NULL for prompts owned by system user
    connection.execute(
        text("""
            UPDATE prompts
            SET user_id = NULL
            WHERE user_id = :user_id
        """),
        {"user_id": system_user_id}
    )
