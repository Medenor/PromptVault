# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""enhanced_backup_tables

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
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
    conn = op.get_bind()

    if not _table_exists(conn, "backup_storage_providers"):
        op.create_table(
            "backup_storage_providers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("provider_type", sa.String(20), nullable=False),
            sa.Column("endpoint_url", sa.Text(), nullable=True),
            sa.Column("bucket_name", sa.String(255), nullable=False),
            sa.Column("prefix", sa.String(512), nullable=True, server_default=""),
            sa.Column("region", sa.String(50), nullable=True),
            sa.Column("credentials_encrypted", sa.Text(), nullable=False),
            sa.Column("credentials_salt", sa.String(32), nullable=False),
            sa.Column("credentials_nonce", sa.String(24), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    backup_columns = [
        sa.Column("backup_kind", sa.String(20), nullable=False, server_default="full"),
        sa.Column("parent_backup_id", sa.String(36), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=True),
        sa.Column("integrity_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("encryption_salt", sa.String(32), nullable=True),
        sa.Column("encryption_nonce", sa.String(24), nullable=True),
        sa.Column("cloud_provider_id", sa.String(36), nullable=True),
        sa.Column("cloud_path", sa.Text(), nullable=True),
        sa.Column("cloud_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("delta_payload", sa.JSON(), nullable=True),
    ]

    for column in backup_columns:
        if not _column_exists(conn, "backups", column.name):
            op.add_column("backups", column)

    if _table_exists(conn, "backup_schedules") and not _column_exists(
        conn, "backup_schedules", "retention_days"
    ):
        # An earlier, pre-migration schema created this table with three
        # separate daily/weekly/monthly retention counters instead of a
        # single retention_days column. Reconcile existing rows onto the
        # column the current model expects, using the daily count (closest
        # equivalent) as the source value, defaulting to 30 when absent.
        has_daily_count = _column_exists(conn, "backup_schedules", "retention_daily_count")
        with op.batch_alter_table("backup_schedules") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "retention_days", sa.Integer(), nullable=False, server_default=sa.text("30")
                )
            )
        if has_daily_count:
            conn.execute(
                sa.text(
                    "UPDATE backup_schedules SET retention_days = retention_daily_count "
                    "WHERE retention_daily_count IS NOT NULL"
                )
            )
        with op.batch_alter_table("backup_schedules") as batch_op:
            for stale_col in (
                "retention_daily_count",
                "retention_weekly_count",
                "retention_monthly_count",
            ):
                if _column_exists(conn, "backup_schedules", stale_col):
                    batch_op.drop_column(stale_col)

    if not _table_exists(conn, "backup_schedules"):
        op.create_table(
            "backup_schedules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("frequency", sa.String(20), nullable=False),
            sa.Column("hour", sa.Integer(), nullable=False),
            sa.Column("minute", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("day_of_week", sa.Integer(), nullable=True),
            sa.Column("day_of_month", sa.Integer(), nullable=True),
            sa.Column(
                "retention_days", sa.Integer(), nullable=False, server_default=sa.text("30")
            ),
            sa.Column(
                "encrypt_scheduled_backups",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("cloud_provider_id", sa.String(36), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_run_status", sa.String(20), nullable=True),
            sa.ForeignKeyConstraint(
                ["cloud_provider_id"],
                ["backup_storage_providers.id"],
                name="fk_backup_schedules_cloud_provider_id",
            ),
        )

    if not _table_exists(conn, "backup_audit_log"):
        op.create_table(
            "backup_audit_log",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("operation", sa.String(50), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("backup_id", sa.String(36), nullable=True),
            sa.Column("performed_by", sa.String(100), nullable=True),
            sa.Column("detail", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["backup_id"],
                ["backups.id"],
                name="fk_backup_audit_log_backup_id",
            ),
        )

    if not _table_exists(conn, "encryption_key_configs"):
        op.create_table(
            "encryption_key_configs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "algorithm", sa.String(20), nullable=False, server_default="AES-256-GCM"
            ),
            sa.Column("kdf", sa.String(20), nullable=False, server_default="argon2id"),
            sa.Column("kdf_time_cost", sa.Integer(), nullable=False, server_default=sa.text("3")),
            sa.Column(
                "kdf_memory_cost", sa.Integer(), nullable=False, server_default=sa.text("65536")
            ),
            sa.Column(
                "kdf_parallelism", sa.Integer(), nullable=False, server_default=sa.text("1")
            ),
            sa.Column("key_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("verification_salt", sa.String(32), nullable=True),
            sa.Column("verification_nonce", sa.String(24), nullable=True),
            sa.Column("verification_ciphertext", sa.Text(), nullable=True),
        )
    else:
        encryption_columns = [
            sa.Column("verification_salt", sa.String(32), nullable=True),
            sa.Column("verification_nonce", sa.String(24), nullable=True),
            sa.Column("verification_ciphertext", sa.Text(), nullable=True),
        ]
        for column in encryption_columns:
            if not _column_exists(conn, "encryption_key_configs", column.name):
                op.add_column("encryption_key_configs", column)


def downgrade() -> None:
    op.drop_table("encryption_key_configs")
    op.drop_table("backup_audit_log")
    op.drop_table("backup_schedules")

    conn = op.get_bind()
    columns_to_drop = [
        "delta_payload", "tags", "cloud_uploaded_at", "cloud_path",
        "cloud_provider_id", "encryption_nonce", "encryption_salt",
        "is_encrypted", "integrity_verified_at", "checksum",
        "parent_backup_id", "backup_kind",
    ]
    for col in columns_to_drop:
        if _column_exists(conn, "backups", col):
            op.drop_column("backups", col)

    op.drop_table("backup_storage_providers")
