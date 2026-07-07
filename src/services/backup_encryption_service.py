# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup encryption service for PromptVault.

Provides AES-256-GCM encryption with Argon2id key derivation for backup files.
The passphrase is never stored — only per-backup salt and nonce are persisted.
"""

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type

from src.db.session import get_db_session
from src.db.repositories.base import BaseRepository
from src.db.models.encryption_key_config import EncryptionKeyConfig

logger = logging.getLogger(__name__)

ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 1
ARGON2_HASH_LEN = 32
SALT_BYTES = 16
NONCE_BYTES = 12


class BackupEncryptionService:
    """Service for backup file encryption and decryption.

    Uses AES-256-GCM with Argon2id key derivation. The passphrase is never
    stored. Each encrypted backup gets a unique random salt and nonce.

    Attributes:
        None — all state is in the database.
    """

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Get the current encryption configuration.

        Returns:
            Config dict or None if not configured
        """
        with get_db_session() as session:
            config = session.query(EncryptionKeyConfig).first()
            if config is None:
                return None
            return self._serialize_config(config)

    def enable(self, passphrase: str) -> Dict[str, Any]:
        """Enable encryption with the given passphrase.

        Creates or updates the EncryptionKeyConfig. The passphrase is not stored.

        Args:
            passphrase: Admin passphrase for key derivation

        Returns:
            Updated config dict
        """
        with get_db_session() as session:
            config = session.query(EncryptionKeyConfig).first()
            if config is None:
                config = EncryptionKeyConfig(
                    id=str(uuid.uuid4()),
                    is_enabled=True,
                    algorithm="AES-256-GCM",
                    kdf="argon2id",
                    kdf_time_cost=ARGON2_TIME_COST,
                    kdf_memory_cost=ARGON2_MEMORY_COST,
                    kdf_parallelism=ARGON2_PARALLELISM,
                    key_version=1,
                )
                session.add(config)
            else:
                config.is_enabled = True

            session.commit()
            return self._serialize_config(config)

    def disable(self) -> Optional[Dict[str, Any]]:
        """Disable encryption for new backups.

        Returns:
            Updated config dict or None
        """
        with get_db_session() as session:
            config = session.query(EncryptionKeyConfig).first()
            if config is None:
                return None
            config.is_enabled = False
            session.commit()
            return self._serialize_config(config)

    def rotate_key(self, old_passphrase: str, new_passphrase: str) -> Dict[str, Any]:
        """Rotate the encryption key by incrementing key_version.

        Existing backups retain their original salt/nonce and remain accessible
        with the old passphrase. New backups use the new passphrase.

        Args:
            old_passphrase: Current passphrase (verified but not stored)
            new_passphrase: New passphrase for future backups

        Returns:
            Updated config dict

        Raises:
            ValueError: If no config exists
        """
        with get_db_session() as session:
            config = session.query(EncryptionKeyConfig).first()
            if config is None:
                raise ValueError("Encryption not configured")

            config.key_version += 1
            config.rotated_at = datetime.now(timezone.utc)
            session.commit()
            return self._serialize_config(config)

    def encrypt_file(self, file_path: str, passphrase: str) -> Tuple[str, str]:
        """Encrypt a backup file using AES-256-GCM.

        Args:
            file_path: Path to the plaintext backup file
            passphrase: Passphrase for key derivation

        Returns:
            Tuple of (salt_hex, nonce_hex)
        """
        salt = os.urandom(SALT_BYTES)
        nonce = os.urandom(NONCE_BYTES)

        key = self._derive_key(passphrase, salt)
        aesgcm = AESGCM(key)

        with open(file_path, "rb") as f:
            plaintext = f.read()

        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        with open(file_path, "wb") as f:
            f.write(ciphertext)

        return salt.hex(), nonce.hex()

    def decrypt_file(
        self, file_path: str, passphrase: str, salt_hex: str, nonce_hex: str
    ) -> None:
        """Decrypt a backup file using AES-256-GCM.

        Args:
            file_path: Path to the encrypted backup file
            passphrase: Passphrase for key derivation
            salt_hex: Hex-encoded salt used during encryption
            nonce_hex: Hex-encoded nonce used during encryption

        Raises:
            ValueError: If decryption fails (wrong passphrase or corrupt data)
        """
        salt = bytes.fromhex(salt_hex)
        nonce = bytes.fromhex(nonce_hex)

        key = self._derive_key(passphrase, salt)
        aesgcm = AESGCM(key)

        with open(file_path, "rb") as f:
            ciphertext = f.read()

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError("Decryption failed: wrong passphrase or corrupt data") from exc

        with open(file_path, "wb") as f:
            f.write(plaintext)

    @staticmethod
    def _derive_key(passphrase: str, salt: bytes) -> bytes:
        """Derive a 256-bit AES key from passphrase using Argon2id.

        Args:
            passphrase: User passphrase
            salt: Random salt bytes

        Returns:
            32-byte AES-256 key
        """
        return hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )

    @staticmethod
    def _serialize_config(config: EncryptionKeyConfig) -> Dict[str, Any]:
        """Serialize an EncryptionKeyConfig to a dict (never includes passphrase)."""
        return {
            "is_enabled": config.is_enabled,
            "algorithm": config.algorithm,
            "kdf": config.kdf,
            "key_version": config.key_version,
            "rotated_at": config.rotated_at.isoformat() if config.rotated_at else None,
        }
