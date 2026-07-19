# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""EncryptionKeyConfig model for PromptVault.

Stores per-system encryption configuration metadata. Never stores the passphrase.
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text
from sqlalchemy.sql import func

from src.db.base import Base


class EncryptionKeyConfig(Base):
    """Encryption configuration model.

    Stores algorithm and KDF parameters for backup encryption.
    The passphrase itself is never stored.

    Attributes:
        id: UUID primary key
        is_enabled: Whether encryption is active for new backups
        algorithm: Encryption algorithm identifier (e.g. 'AES-256-GCM')
        kdf: Key derivation function (e.g. 'argon2id')
        kdf_time_cost: Argon2 time cost parameter
        kdf_memory_cost: Argon2 memory cost in KB
        kdf_parallelism: Argon2 parallelism
        key_version: Monotonically increasing version, incremented on rotation
        rotated_at: When last key rotation occurred
        created_at: When config was created
    """

    __tablename__ = "encryption_key_configs"

    id = Column(String(36), primary_key=True)
    is_enabled = Column(Boolean, nullable=False, default=False)
    algorithm = Column(String(20), nullable=False, default="AES-256-GCM")
    kdf = Column(String(20), nullable=False, default="argon2id")
    kdf_time_cost = Column(Integer, nullable=False, default=3)
    kdf_memory_cost = Column(Integer, nullable=False, default=65536)
    kdf_parallelism = Column(Integer, nullable=False, default=1)
    key_version = Column(Integer, nullable=False, default=1)
    rotated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Stored sentinel for passphrase verification during key rotation.
    # Encrypted with the active passphrase; never contains the passphrase itself.
    verification_salt = Column(String(32), nullable=True)
    verification_nonce = Column(String(24), nullable=True)
    verification_ciphertext = Column(Text, nullable=True)

    def __repr__(self):
        return f"<EncryptionKeyConfig(id='{self.id[:8]}...', enabled={self.is_enabled}, version={self.key_version})>"
