# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BackupStorageProvider model for PromptVault.

Tracks cloud storage provider configurations for backup upload/download.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.db.base import Base


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

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(20), nullable=False)
    endpoint_url = Column(Text, nullable=True)
    bucket_name = Column(String(255), nullable=False)
    prefix = Column(String(512), nullable=True, default="")
    region = Column(String(50), nullable=True)
    credentials_encrypted = Column(Text, nullable=False)
    credentials_salt = Column(String(32), nullable=False)
    credentials_nonce = Column(String(24), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    backups = relationship(
        "Backup",
        back_populates="storage_provider",
        foreign_keys="Backup.cloud_provider_id",
    )

    def __repr__(self):
        return f"<BackupStorageProvider(id='{self.id[:8]}...', name='{self.name}', type='{self.provider_type}')>"
