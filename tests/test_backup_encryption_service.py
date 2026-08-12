# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for BackupEncryptionService."""

import os
import shutil
import tempfile

import pytest

from src.services.backup_encryption_service import (
    ARGON2_HASH_LEN,
    NONCE_BYTES,
    SALT_BYTES,
    BackupEncryptionService,
)


@pytest.fixture
def temp_file():
    path = os.path.join(tempfile.mkdtemp(), "test_backup.db")
    with open(path, "wb") as f:
        f.write(b"test backup content for encryption")
    yield path
    shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TestGetConfig:
    def test_returns_none_when_no_config(self, encryption_service):
        assert encryption_service.get_config() is None

    def test_returns_config_after_enable(self, encryption_service):
        encryption_service.enable("my-passphrase")
        config = encryption_service.get_config()
        assert config is not None
        assert config["is_enabled"] is True
        assert config["algorithm"] == "AES-256-GCM"
        assert config["kdf"] == "argon2id"
        assert config["key_version"] == 1
        assert config["rotated_at"] is None


class TestEnable:
    def test_enable_creates_config(self, encryption_service):
        result = encryption_service.enable("test-passphrase")
        assert result["is_enabled"] is True
        assert result["algorithm"] == "AES-256-GCM"
        assert result["key_version"] == 1

    def test_enable_updates_existing_config(self, encryption_service):
        encryption_service.enable("first-passphrase")
        result = encryption_service.enable("second-passphrase")
        assert result["is_enabled"] is True
        assert result["key_version"] == 1

    def test_enable_re_enable_after_disable(self, encryption_service):
        encryption_service.enable("pass1")
        encryption_service.disable()
        result = encryption_service.enable("pass2")
        assert result["is_enabled"] is True


class TestDisable:
    def test_disable_returns_none_when_no_config(self, encryption_service):
        assert encryption_service.disable() is None

    def test_disable_sets_is_enabled_false(self, encryption_service):
        encryption_service.enable("passphrase")
        result = encryption_service.disable()
        assert result["is_enabled"] is False

    def test_disable_preserves_other_fields(self, encryption_service):
        encryption_service.enable("passphrase")
        result = encryption_service.disable()
        assert result["algorithm"] == "AES-256-GCM"
        assert result["kdf"] == "argon2id"


class TestRotateKey:
    def test_rotate_key_increments_version(self, encryption_service):
        encryption_service.enable("old-pass")
        result = encryption_service.rotate_key("old-pass", "new-pass")
        assert result["key_version"] == 2
        assert result["rotated_at"] is not None

    def test_rotate_key_raises_when_no_config(self, encryption_service):
        with pytest.raises(ValueError, match="Encryption not configured"):
            encryption_service.rotate_key("old", "new")

    def test_rotate_key_raises_with_wrong_old_passphrase(self, encryption_service):
        encryption_service.enable("correct-pass")
        with pytest.raises(ValueError, match="old_passphrase verification failed"):
            encryption_service.rotate_key("wrong-pass", "new-pass")

    def test_rotate_key_multiple_times(self, encryption_service):
        encryption_service.enable("pass-v1")
        encryption_service.rotate_key("pass-v1", "pass-v2")
        result = encryption_service.rotate_key("pass-v2", "pass-v3")
        assert result["key_version"] == 3

    def test_rotate_key_raises_without_sentinel(
        self, encryption_service, patched_db_session
    ):
        import uuid

        from src.db.models.encryption_key_config import EncryptionKeyConfig

        with patched_db_session() as session:
            config = EncryptionKeyConfig(
                id=str(uuid.uuid4()),
                is_enabled=True,
                algorithm="AES-256-GCM",
                kdf="argon2id",
            )
            session.add(config)
            session.commit()

        with pytest.raises(ValueError, match="No verification sentinel"):
            encryption_service.rotate_key("old", "new")


class TestEncryptDecryptFile:
    def test_encrypt_returns_salt_and_nonce(self, encryption_service, temp_file):
        salt_hex, nonce_hex = encryption_service.encrypt_file(temp_file, "passphrase")
        assert len(salt_hex) == SALT_BYTES * 2
        assert len(nonce_hex) == NONCE_BYTES * 2

    def test_encrypt_decrypt_roundtrip(self, encryption_service, temp_file):
        original = open(temp_file, "rb").read()
        salt_hex, nonce_hex = encryption_service.encrypt_file(temp_file, "my-pass")
        encryption_service.decrypt_file(temp_file, "my-pass", salt_hex, nonce_hex)
        assert open(temp_file, "rb").read() == original

    def test_decrypt_with_wrong_passphrase_raises(self, encryption_service, temp_file):
        salt_hex, nonce_hex = encryption_service.encrypt_file(temp_file, "correct")
        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt_file(temp_file, "wrong", salt_hex, nonce_hex)

    def test_encrypt_produces_different_ciphertext_each_time(
        self, encryption_service, temp_file
    ):
        content = open(temp_file, "rb").read()
        salt1, nonce1 = encryption_service.encrypt_file(temp_file, "pass")
        encrypted1 = open(temp_file, "rb").read()
        open(temp_file, "wb").write(content)
        salt2, nonce2 = encryption_service.encrypt_file(temp_file, "pass")
        encrypted2 = open(temp_file, "rb").read()
        assert encrypted1 != encrypted2

    def test_decrypt_with_corrupt_data_raises(self, encryption_service, temp_file):
        salt_hex, nonce_hex = encryption_service.encrypt_file(temp_file, "pass")
        with open(temp_file, "wb") as f:
            f.write(b"corrupted data")
        with pytest.raises(ValueError, match="Decryption failed"):
            encryption_service.decrypt_file(temp_file, "pass", salt_hex, nonce_hex)

    def test_encrypt_empty_file(self, encryption_service):
        path = os.path.join(tempfile.mkdtemp(), "empty.db")
        with open(path, "wb") as f:
            f.write(b"")
        salt_hex, nonce_hex = encryption_service.encrypt_file(path, "pass")
        encryption_service.decrypt_file(path, "pass", salt_hex, nonce_hex)
        assert open(path, "rb").read() == b""
        shutil.rmtree(os.path.dirname(path), ignore_errors=True)


class TestDeriveKey:
    def test_derive_key_returns_32_bytes(self):
        salt = os.urandom(SALT_BYTES)
        key = BackupEncryptionService._derive_key("passphrase", salt)
        assert len(key) == ARGON2_HASH_LEN

    def test_derive_key_deterministic(self):
        salt = os.urandom(SALT_BYTES)
        key1 = BackupEncryptionService._derive_key("pass", salt)
        key2 = BackupEncryptionService._derive_key("pass", salt)
        assert key1 == key2

    def test_derive_key_different_passphrases(self):
        salt = os.urandom(SALT_BYTES)
        key1 = BackupEncryptionService._derive_key("pass1", salt)
        key2 = BackupEncryptionService._derive_key("pass2", salt)
        assert key1 != key2

    def test_derive_key_different_salts(self):
        salt1 = os.urandom(SALT_BYTES)
        salt2 = os.urandom(SALT_BYTES)
        key1 = BackupEncryptionService._derive_key("pass", salt1)
        key2 = BackupEncryptionService._derive_key("pass", salt2)
        assert key1 != key2


class TestVerificationSentinel:
    def test_make_and_verify_sentinel(self):
        salt, nonce, ct = BackupEncryptionService._make_verification_sentinel("pass")
        BackupEncryptionService._verify_passphrase("pass", salt, nonce, ct)

    def test_verify_wrong_passphrase_raises(self):
        salt, nonce, ct = BackupEncryptionService._make_verification_sentinel("correct")
        with pytest.raises(ValueError, match="old_passphrase verification failed"):
            BackupEncryptionService._verify_passphrase("wrong", salt, nonce, ct)


class TestSerializeConfig:
    def test_serialize_config_never_includes_passphrase(self, encryption_service):
        encryption_service.enable("secret-passphrase")
        config = encryption_service.get_config()
        assert "passphrase" not in config
        assert "verification_salt" not in config
        assert "verification_nonce" not in config
        assert "verification_ciphertext" not in config
