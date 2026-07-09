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
    cursor = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in cursor]
    return column in columns


def _table_exists(conn, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.execute(
        sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table},
    )
    return cursor.fetchone() is not None


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
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

    backup_columns = [
        ("backup_kind", "ALTER TABLE backups ADD COLUMN backup_kind VARCHAR(20) NOT NULL DEFAULT 'full'"),
        ("parent_backup_id", "ALTER TABLE backups ADD COLUMN parent_backup_id VARCHAR(36)"),
        ("checksum", "ALTER TABLE backups ADD COLUMN checksum VARCHAR(64)"),
        ("integrity_verified_at", "ALTER TABLE backups ADD COLUMN integrity_verified_at DATETIME"),
        ("is_encrypted", "ALTER TABLE backups ADD COLUMN is_encrypted BOOLEAN NOT NULL DEFAULT 0"),
        ("encryption_salt", "ALTER TABLE backups ADD COLUMN encryption_salt VARCHAR(32)"),
        ("encryption_nonce", "ALTER TABLE backups ADD COLUMN encryption_nonce VARCHAR(24)"),
        ("cloud_provider_id", "ALTER TABLE backups ADD COLUMN cloud_provider_id VARCHAR(36)"),
        ("cloud_path", "ALTER TABLE backups ADD COLUMN cloud_path TEXT"),
        ("cloud_uploaded_at", "ALTER TABLE backups ADD COLUMN cloud_uploaded_at DATETIME"),
        ("tags", "ALTER TABLE backups ADD COLUMN tags JSON"),
        ("delta_payload", "ALTER TABLE backups ADD COLUMN delta_payload JSON"),
    ]

    for col_name, ddl in backup_columns:
        if not _column_exists(conn, "backups", col_name):
            conn.execute(sa.text(ddl))

    if not _table_exists(conn, "backup_schedules"):
        op.create_table(
            "backup_schedules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
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
                server_default=sa.text("0"),
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
            sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
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
            ("verification_salt", "ALTER TABLE encryption_key_configs ADD COLUMN verification_salt VARCHAR(32)"),
            ("verification_nonce", "ALTER TABLE encryption_key_configs ADD COLUMN verification_nonce VARCHAR(24)"),
            ("verification_ciphertext", "ALTER TABLE encryption_key_configs ADD COLUMN verification_ciphertext TEXT"),
        ]
        for col_name, ddl in encryption_columns:
            if not _column_exists(conn, "encryption_key_configs", col_name):
                conn.execute(sa.text(ddl))


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
            conn.execute(sa.text(f"ALTER TABLE backups DROP COLUMN {col}"))

    op.drop_table("backup_storage_providers")
