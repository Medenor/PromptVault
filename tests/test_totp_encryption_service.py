# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for TotpEncryptionService.

Covers:
- Round-trip encrypt/decrypt of TOTP secrets
- Tamper detection (GCM authentication)
- Missing-key configuration error
"""

from unittest.mock import patch

import pytest

from src.config.auth_config import AuthConfig
from src.services.auth.totp_encryption_service import TotpEncryptionService


@pytest.fixture
def auth_config():
    """AuthConfig with a TOTP encryption key set."""
    with patch.dict(
        "os.environ", {"TOTP_ENCRYPTION_KEY": "test-server-secret-value-12345"}
    ):
        yield AuthConfig()


@pytest.fixture
def encryption_service(auth_config):
    return TotpEncryptionService(auth_config)


class TestInitialization:
    def test_missing_key_raises(self):
        config = AuthConfig(totp_encryption_key="")
        with pytest.raises(ValueError, match="TOTP_ENCRYPTION_KEY"):
            TotpEncryptionService(config)

    def test_derives_32_byte_key(self, encryption_service):
        assert len(encryption_service._key) == 32


class TestRoundTrip:
    def test_encrypt_decrypt_round_trip(self, encryption_service):
        secret = "JBSWY3DPEHPK3PXP"
        ciphertext_b64, nonce_hex = encryption_service.encrypt_secret(secret)
        decrypted = encryption_service.decrypt_secret(ciphertext_b64, nonce_hex)
        assert decrypted == secret

    def test_ciphertext_differs_from_plaintext(self, encryption_service):
        secret = "JBSWY3DPEHPK3PXP"
        ciphertext_b64, _ = encryption_service.encrypt_secret(secret)
        assert ciphertext_b64 != secret

    def test_unique_nonce_per_encryption(self, encryption_service):
        secret = "JBSWY3DPEHPK3PXP"
        _, nonce1 = encryption_service.encrypt_secret(secret)
        _, nonce2 = encryption_service.encrypt_secret(secret)
        assert nonce1 != nonce2

    def test_different_secrets_produce_different_ciphertext(self, encryption_service):
        ct1, _ = encryption_service.encrypt_secret("JBSWY3DPEHPK3PXP")
        ct2, _ = encryption_service.encrypt_secret("KRSXG5CTORQWG5A")
        assert ct1 != ct2


class TestTamperDetection:
    def test_tampered_ciphertext_raises(self, encryption_service):
        ciphertext_b64, nonce_hex = encryption_service.encrypt_secret(
            "JBSWY3DPEHPK3PXP"
        )
        tampered = ciphertext_b64[:-4] + ("AAAA" if ciphertext_b64[-4:] != "AAAA" else "BBBB")
        with pytest.raises(ValueError, match="decryption failed"):
            encryption_service.decrypt_secret(tampered, nonce_hex)

    def test_tampered_nonce_raises(self, encryption_service):
        ciphertext_b64, nonce_hex = encryption_service.encrypt_secret(
            "JBSWY3DPEHPK3PXP"
        )
        tampered_nonce = ("0" if nonce_hex[0] != "0" else "1") + nonce_hex[1:]
        with pytest.raises(ValueError, match="decryption failed"):
            encryption_service.decrypt_secret(ciphertext_b64, tampered_nonce)

    def test_wrong_key_cannot_decrypt(self, auth_config):
        service_a = TotpEncryptionService(auth_config)
        ciphertext_b64, nonce_hex = service_a.encrypt_secret("JBSWY3DPEHPK3PXP")

        other_config = AuthConfig(totp_encryption_key="a-completely-different-secret")
        service_b = TotpEncryptionService(other_config)

        with pytest.raises(ValueError, match="decryption failed"):
            service_b.decrypt_secret(ciphertext_b64, nonce_hex)
