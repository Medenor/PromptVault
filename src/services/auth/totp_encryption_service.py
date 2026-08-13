# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""TOTP secret encryption service for PromptVault.

Encrypts TOTP secrets at rest with AES-256-GCM, using a key derived (via
HKDF) from a server-held symmetric key (AuthConfig.totp_encryption_key)
rather than a per-operation user passphrase. Unlike backup encryption, the
TOTP secret must be decryptable transparently on every login — there is no
user-supplied secret available at verification time (research.md §3).
"""

import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from src.config.auth_config import AuthConfig

NONCE_BYTES = 12
KEY_BYTES = 32
HKDF_INFO = b"promptvault-totp-secret-encryption"
HKDF_SALT = b"promptvault-totp-v1"


class TotpEncryptionService:
    """Service for encrypting/decrypting TOTP secrets at rest.

    Attributes:
        config: AuthConfig instance with totp_encryption_key
    """

    def __init__(self, config: AuthConfig):
        """Initialize the service and derive the AES-256-GCM key.

        Args:
            config: AuthConfig instance with totp_encryption_key set

        Raises:
            ValueError: If totp_encryption_key is empty
        """
        self.config = config
        if not config.totp_encryption_key:
            raise ValueError(
                "TOTP_ENCRYPTION_KEY must be set to use TotpEncryptionService"
            )
        self._key = self._derive_key(config.totp_encryption_key)

    @staticmethod
    def _derive_key(server_secret: str) -> bytes:
        """Derive a 256-bit AES key from the server secret via HKDF.

        Args:
            server_secret: The raw TOTP_ENCRYPTION_KEY value

        Returns:
            32-byte AES-256 key
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=KEY_BYTES,
            salt=HKDF_SALT,
            info=HKDF_INFO,
        )
        return hkdf.derive(server_secret.encode("utf-8"))

    def encrypt_secret(self, plaintext: str) -> tuple[str, str]:
        """Encrypt a TOTP secret.

        Args:
            plaintext: The base32 TOTP secret

        Returns:
            Tuple of (ciphertext_b64, nonce_hex)
        """
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = AESGCM(self._key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(ciphertext).decode("utf-8"), nonce.hex()

    def decrypt_secret(self, ciphertext_b64: str, nonce_hex: str) -> str:
        """Decrypt a TOTP secret.

        Args:
            ciphertext_b64: Base64-encoded ciphertext
            nonce_hex: Hex-encoded GCM nonce

        Returns:
            The decrypted base32 TOTP secret

        Raises:
            ValueError: If decryption fails (tampered/corrupt data or wrong key)
        """
        nonce = bytes.fromhex(nonce_hex)
        ciphertext = base64.b64decode(ciphertext_b64)
        try:
            plaintext = AESGCM(self._key).decrypt(nonce, ciphertext, None)
        except Exception as exc:
            raise ValueError(
                "TOTP secret decryption failed: corrupt data or wrong key"
            ) from exc
        return plaintext.decode("utf-8")
