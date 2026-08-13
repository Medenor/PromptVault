# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""add_totp_2fa

Revision ID: d80fb5792dda
Revises: c3d4e5f6a7b8
Create Date: 2026-08-13 10:49:39.880299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd80fb5792dda'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    inspector = sa.inspect(conn)
    if table not in inspector.get_table_names():
        return False
    columns = [col["name"] for col in inspector.get_columns(table)]
    return column in columns


def _table_exists(conn, table: str) -> bool:
    """Check if a table exists."""
    inspector = sa.inspect(conn)
    return table in inspector.get_table_names()


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    if not _column_exists(conn, "users", "totp_enabled"):
        op.add_column(
            "users",
            sa.Column(
                "totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )

    if not _table_exists(conn, "totp_credentials"):
        op.create_table(
            "totp_credentials",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("secret_ciphertext", sa.String(), nullable=False),
            sa.Column("secret_nonce", sa.String(32), nullable=False),
            sa.Column(
                "confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("last_used_step", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_totp_credentials_user_id_users",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("user_id", name="uq_totp_credentials_user_id"),
        )
        op.create_index(
            "ix_totp_credentials_user_id", "totp_credentials", ["user_id"]
        )

    if not _table_exists(conn, "totp_recovery_codes"):
        op.create_table(
            "totp_recovery_codes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("batch_id", sa.String(36), nullable=False),
            sa.Column("code_hash", sa.String(255), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_totp_recovery_codes_user_id_users",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_totp_recovery_codes_user_id", "totp_recovery_codes", ["user_id"]
        )
        op.create_index(
            "ix_totp_recovery_codes_batch_id", "totp_recovery_codes", ["batch_id"]
        )
        op.create_index(
            "ix_totp_recovery_codes_user_batch",
            "totp_recovery_codes",
            ["user_id", "batch_id"],
        )

    if not _table_exists(conn, "totp_login_challenges"):
        op.create_table(
            "totp_login_challenges",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name="fk_totp_login_challenges_user_id_users",
                ondelete="CASCADE",
            ),
        )
        op.create_index(
            "ix_totp_login_challenges_user_id", "totp_login_challenges", ["user_id"]
        )
        op.create_index(
            "ix_totp_login_challenges_expires_at",
            "totp_login_challenges",
            ["expires_at"],
        )
        op.create_index(
            "ix_totp_login_challenges_user_consumed",
            "totp_login_challenges",
            ["user_id", "consumed_at"],
        )

    if not _table_exists(conn, "totp_role_policies"):
        op.create_table(
            "totp_role_policies",
            sa.Column("role", sa.String(50), primary_key=True),
            sa.Column(
                "required", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("updated_by_user_id", sa.String(36), nullable=True),
            sa.ForeignKeyConstraint(
                ["updated_by_user_id"],
                ["users.id"],
                name="fk_totp_role_policies_updated_by_user_id_users",
                ondelete="SET NULL",
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    conn = op.get_bind()

    if _table_exists(conn, "totp_role_policies"):
        op.drop_table("totp_role_policies")

    if _table_exists(conn, "totp_login_challenges"):
        op.drop_table("totp_login_challenges")

    if _table_exists(conn, "totp_recovery_codes"):
        op.drop_table("totp_recovery_codes")

    if _table_exists(conn, "totp_credentials"):
        op.drop_table("totp_credentials")

    if _column_exists(conn, "users", "totp_enabled"):
        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_column("totp_enabled")
