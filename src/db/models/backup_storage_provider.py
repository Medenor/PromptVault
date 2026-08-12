# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupStorageProvider model for PromptVault.

Tracks cloud storage provider configurations for backup upload/download.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.backup import Backup


class BackupStorageProvider(Base):
    """Cloud storage provider configuration model.

    Stores S3-compatible provider credentials (encrypted) and connection details.

    Attributes:
        id: UUID primary key
        name: Admin-given display name
        provider_type: 's3' (v1 only)
        endpoint_url: For S3-compatible providers (MinIO, etc.)
        bucket_name: S3 bucket name
        prefix: Key prefix within bucket
        region: AWS region (optional for S3-compatible)
        credentials_encrypted: AES-256-GCM encrypted JSON credentials blob
        credentials_salt: Argon2id salt for credential encryption
        credentials_nonce: GCM nonce for credential encryption
        enabled: Whether this provider is active
        created_at: When provider was configured
    """

    __tablename__ = "backup_storage_providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(20), nullable=False)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    prefix: Mapped[str | None] = mapped_column(String(512), nullable=True, default="")
    region: Mapped[str | None] = mapped_column(String(50), nullable=True)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    credentials_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    credentials_nonce: Mapped[str] = mapped_column(String(24), nullable=False)
    enabled: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    backups: Mapped[list["Backup"]] = relationship(
        "Backup",
        back_populates="storage_provider",
        foreign_keys="Backup.cloud_provider_id",
    )

    def __repr__(self):
        return f"<BackupStorageProvider(id='{self.id[:8]}...', name='{self.name}', type='{self.provider_type}')>"
