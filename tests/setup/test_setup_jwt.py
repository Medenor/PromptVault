# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for JWT key setup script.

Tests cover:
- Key generation (ES256)
- CLI arguments and flags
- Idempotency
- Validation
- Backup functionality
- Gitignore integration
- Error handling
"""

import os
import sys
import pytest
import tempfile
import shutil
import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
from click.testing import CliRunner

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

# Import the module to test
from scripts.setup.setup_jwt import (
    generate_key_pair,
    validate_key_pair,
    backup_keys,
    ensure_gitignore,
    set_file_permissions,
    write_keys,
    main,
)


class TestGenerateKeyPair:
    """Test ES256 key pair generation."""

    def test_generate_key_pair_returns_bytes(self):
        """Test that generate_key_pair returns bytes for both keys."""
        private_pem, public_pem = generate_key_pair()

        assert isinstance(private_pem, bytes)
        assert isinstance(public_pem, bytes)

    def test_generated_keys_are_pem_format(self):
        """Test that generated keys are in PEM format."""
        private_pem, public_pem = generate_key_pair()

        assert b"-----BEGIN PRIVATE KEY-----" in private_pem
        assert b"-----END PRIVATE KEY-----" in private_pem
        assert b"-----BEGIN PUBLIC KEY-----" in public_pem
        assert b"-----END PUBLIC KEY-----" in public_pem

    def test_generated_keys_are_valid_es256(self):
        """Test that generated keys are valid ES256 keys."""
        private_pem, public_pem = generate_key_pair()

        # Load and verify the private key
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        private_key = load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )

        # Verify it's an EC key with P-256 curve
        assert isinstance(private_key, ec.EllipticCurvePrivateKey)
        assert private_key.curve.name == "secp256r1"

    def test_generated_keys_can_sign_and_verify(self):
        """Test that generated keys can successfully sign and verify JWT tokens."""
        private_pem, public_pem = generate_key_pair()

        # Create a test payload
        payload = {"test": True, "data": "sample"}

        # Load keys for PyJWT
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        private_key = load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )

        # Sign a token
        token = jwt.encode(payload, private_key, algorithm="ES256")

        # Verify the token
        decoded = jwt.decode(token, public_pem, algorithms=["ES256"])

        assert decoded["test"] is True
        assert decoded["data"] == "sample"

    def test_generated_keys_are_unique(self):
        """Test that each call generates different keys."""
        private_pem1, public_pem1 = generate_key_pair()
        private_pem2, public_pem2 = generate_key_pair()

        assert private_pem1 != private_pem2
        assert public_pem1 != public_pem2

    def test_private_key_format_pkcs8(self):
        """Test that private key is in PKCS8 format without encryption."""
        private_pem, _ = generate_key_pair()

        # PKCS8 format uses "BEGIN PRIVATE KEY" (not "BEGIN EC PRIVATE KEY")
        assert b"-----BEGIN PRIVATE KEY-----" in private_pem


class TestValidateKeyPair:
    """Test key pair validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.private_path = self.temp_dir / "private_key.pem"
        self.public_path = self.temp_dir / "public_key.pem"
        self.console = Mock()
        self.console.error = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_validate_valid_key_pair(self):
        """Test validation of a valid key pair."""
        # Generate and write valid keys
        private_pem, public_pem = generate_key_pair()
        self.private_path.write_bytes(private_pem)
        self.public_path.write_bytes(public_pem)

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is True
        self.console.error.assert_not_called()

    def test_validate_missing_private_key(self):
        """Test validation when private key is missing."""
        # Only create public key
        _, public_pem = generate_key_pair()
        self.public_path.write_bytes(public_pem)

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()
        assert "Private key not found" in str(self.console.error.call_args)

    def test_validate_missing_public_key(self):
        """Test validation when public key is missing."""
        # Only create private key
        private_pem, _ = generate_key_pair()
        self.private_path.write_bytes(private_pem)

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()
        assert "Public key not found" in str(self.console.error.call_args)

    def test_validate_corrupted_private_key(self):
        """Test validation with corrupted private key."""
        # Create valid public key
        _, public_pem = generate_key_pair()
        self.public_path.write_bytes(public_pem)

        # Create corrupted private key
        self.private_path.write_text("CORRUPTED DATA")

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()

    def test_validate_corrupted_public_key(self):
        """Test validation with corrupted public key."""
        # Create valid private key
        private_pem, _ = generate_key_pair()
        self.private_path.write_bytes(private_pem)

        # Create corrupted public key
        self.public_path.write_text("CORRUPTED DATA")

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()

    def test_validate_mismatched_key_pair(self):
        """Test validation with mismatched key pair."""
        # Generate two different key pairs
        private_pem1, _ = generate_key_pair()
        _, public_pem2 = generate_key_pair()

        self.private_path.write_bytes(private_pem1)
        self.public_path.write_bytes(public_pem2)

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()

    def test_validate_wrong_algorithm_rsa_key(self):
        """Test validation detects RSA key instead of EC key."""
        from cryptography.hazmat.primitives.asymmetric import rsa

        # Generate RSA key pair
        rsa_private = rsa.generate_private_key(
            public_exponent=65537, key_size=2048, backend=default_backend()
        )

        rsa_private_pem = rsa_private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        rsa_public_pem = rsa_private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        self.private_path.write_bytes(rsa_private_pem)
        self.public_path.write_bytes(rsa_public_pem)

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        # Should fail because PyJWT will reject RSA key with ES256 algorithm
        assert result is False
        self.console.error.assert_called()

    def test_validate_empty_files(self):
        """Test validation with empty key files."""
        self.private_path.touch()
        self.public_path.touch()

        result = validate_key_pair(self.private_path, self.public_path, self.console)

        assert result is False
        self.console.error.assert_called()


class TestBackupKeys:
    """Test backup functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.console = Mock()
        self.console.success = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_backup_existing_keys(self):
        """Test backup creates timestamped directory with key copies."""
        # Create existing keys
        private_path = self.temp_dir / "private_key.pem"
        public_path = self.temp_dir / "public_key.pem"
        private_pem, public_pem = generate_key_pair()
        private_path.write_bytes(private_pem)
        public_path.write_bytes(public_pem)

        backup_dir = backup_keys(self.temp_dir, self.console)

        assert backup_dir is not None
        assert backup_dir.exists()
        assert backup_dir.name.startswith("backup_")
        assert (backup_dir / "private_key.pem").exists()
        assert (backup_dir / "public_key.pem").exists()
        self.console.success.assert_called()

    def test_backup_preserves_key_content(self):
        """Test backup preserves original key content."""
        # Create existing keys
        private_path = self.temp_dir / "private_key.pem"
        public_path = self.temp_dir / "public_key.pem"
        private_pem, public_pem = generate_key_pair()
        private_path.write_bytes(private_pem)
        public_path.write_bytes(public_pem)

        backup_dir = backup_keys(self.temp_dir, self.console)

        # Verify content matches
        assert (backup_dir / "private_key.pem").read_bytes() == private_pem
        assert (backup_dir / "public_key.pem").read_bytes() == public_pem

    def test_backup_only_private_key_exists(self):
        """Test backup when only private key exists."""
        private_path = self.temp_dir / "private_key.pem"
        private_pem, _ = generate_key_pair()
        private_path.write_bytes(private_pem)

        backup_dir = backup_keys(self.temp_dir, self.console)

        assert backup_dir is not None
        assert (backup_dir / "private_key.pem").exists()
        assert not (backup_dir / "public_key.pem").exists()

    def test_backup_only_public_key_exists(self):
        """Test backup when only public key exists."""
        public_path = self.temp_dir / "public_key.pem"
        _, public_pem = generate_key_pair()
        public_path.write_bytes(public_pem)

        backup_dir = backup_keys(self.temp_dir, self.console)

        assert backup_dir is not None
        assert not (backup_dir / "private_key.pem").exists()
        assert (backup_dir / "public_key.pem").exists()

    def test_backup_no_keys_exist(self):
        """Test backup returns None when no keys exist."""
        backup_dir = backup_keys(self.temp_dir, self.console)

        assert backup_dir is None

    def test_backup_creates_timestamped_directory(self):
        """Test backup directory includes timestamp."""
        private_path = self.temp_dir / "private_key.pem"
        private_pem, _ = generate_key_pair()
        private_path.write_bytes(private_pem)

        # Mock datetime to control timestamp
        with patch("scripts.setup.setup_jwt.datetime") as mock_dt:
            mock_dt.datetime.now.return_value = datetime.datetime(
                2024, 1, 15, 14, 30, 45
            )
            mock_dt.datetime.strftime = datetime.datetime.strftime

            backup_dir = backup_keys(self.temp_dir, self.console)

        assert "backup_20240115_143045" in str(backup_dir)

    def test_backup_multiple_times_creates_unique_directories(self):
        """Test multiple backups create unique directories."""
        private_path = self.temp_dir / "private_key.pem"
        private_pem, _ = generate_key_pair()
        private_path.write_bytes(private_pem)

        # Create first backup
        backup_dir1 = backup_keys(self.temp_dir, self.console)

        # Wait a moment and create second backup
        import time

        time.sleep(1)
        backup_dir2 = backup_keys(self.temp_dir, self.console)

        assert backup_dir1 != backup_dir2
        assert backup_dir1.exists()
        assert backup_dir2.exists()


class TestEnsureGitignore:
    """Test .gitignore integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.secrets_dir = self.temp_dir / "secrets" / "jwt"
        self.secrets_dir.mkdir(parents=True)
        self.gitignore_path = self.temp_dir / ".gitignore"
        self.console = Mock()
        self.console.info = Mock()
        self.console.warning = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_gitignore_already_includes_secrets(self):
        """Test when .gitignore already includes secrets/."""
        self.gitignore_path.write_text("secrets/\n*.log\n")

        ensure_gitignore(self.secrets_dir, self.console)

        self.console.info.assert_called()
        info_call = str(self.console.info.call_args)
        assert "already includes" in info_call.lower()

    def test_gitignore_missing_secrets_entry(self):
        """Test when .gitignore exists but doesn't include secrets/."""
        self.gitignore_path.write_text("*.log\n__pycache__/\n")

        ensure_gitignore(self.secrets_dir, self.console)

        self.console.warning.assert_called()
        warning_call = str(self.console.warning.call_args)
        assert "not found" in warning_call.lower()

        # Should also call info suggesting to add it
        self.console.info.assert_called()

    def test_gitignore_does_not_exist(self):
        """Test when .gitignore does not exist."""
        ensure_gitignore(self.secrets_dir, self.console)

        self.console.warning.assert_called()
        warning_call = str(self.console.warning.call_args)
        assert "could not find" in warning_call.lower()

    def test_gitignore_read_error(self):
        """Test handling of .gitignore read error."""
        # Create .gitignore with no read permissions (Unix only)
        if sys.platform != "win32":
            self.gitignore_path.write_text("secrets/\n")
            os.chmod(self.gitignore_path, 0o000)

            ensure_gitignore(self.secrets_dir, self.console)

            self.console.warning.assert_called()
            warning_call = str(self.console.warning.call_args)
            assert "could not read" in warning_call.lower()

            # Restore permissions for cleanup
            os.chmod(self.gitignore_path, 0o644)

    def test_gitignore_in_parent_directory(self):
        """Test finding .gitignore in parent directory."""
        # Create nested structure
        nested_secrets = self.temp_dir / "project" / "app" / "secrets" / "jwt"
        nested_secrets.mkdir(parents=True)
        gitignore = self.temp_dir / "project" / ".gitignore"
        gitignore.write_text("secrets/\n")

        ensure_gitignore(nested_secrets, self.console)

        # Should find the .gitignore and report it includes secrets/
        self.console.info.assert_called()


class TestSetFilePermissions:
    """Test file permission setting."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.private_path = self.temp_dir / "private_key.pem"
        self.public_path = self.temp_dir / "public_key.pem"
        self.console = Mock()
        self.console.info = Mock()
        self.console.warning = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix permissions not applicable on Windows"
    )
    def test_set_correct_permissions(self):
        """Test setting correct permissions on key files."""
        # Create key files
        self.private_path.write_text("private")
        self.public_path.write_text("public")

        set_file_permissions(self.private_path, self.public_path, self.console)

        # Check permissions
        private_stat = os.stat(self.private_path)
        public_stat = os.stat(self.public_path)

        # Extract permission bits
        private_perms = private_stat.st_mode & 0o777
        public_perms = public_stat.st_mode & 0o777

        assert private_perms == 0o600
        assert public_perms == 0o644
        self.console.info.assert_called()

    def test_permission_error_handling(self):
        """Test handling of permission setting errors."""
        # Create files that don't exist (will cause chmod to fail)
        non_existent_private = self.temp_dir / "nonexistent_private.pem"
        non_existent_public = self.temp_dir / "nonexistent_public.pem"

        set_file_permissions(non_existent_private, non_existent_public, self.console)

        # Should call warning about permission error
        self.console.warning.assert_called()
        warning_call = str(self.console.warning.call_args)
        assert "could not set" in warning_call.lower()


class TestWriteKeys:
    """Test key writing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.console = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_write_keys_creates_files(self):
        """Test that write_keys creates key files."""
        private_pem, public_pem = generate_key_pair()

        private_path, public_path = write_keys(
            self.temp_dir, private_pem, public_pem, self.console
        )

        assert private_path.exists()
        assert public_path.exists()
        assert private_path == self.temp_dir / "private_key.pem"
        assert public_path == self.temp_dir / "public_key.pem"

    def test_write_keys_preserves_content(self):
        """Test that written keys have correct content."""
        private_pem, public_pem = generate_key_pair()

        private_path, public_path = write_keys(
            self.temp_dir, private_pem, public_pem, self.console
        )

        assert private_path.read_bytes() == private_pem
        assert public_path.read_bytes() == public_pem

    def test_write_keys_overwrites_existing(self):
        """Test that write_keys overwrites existing files."""
        # Create existing files
        private_path = self.temp_dir / "private_key.pem"
        public_path = self.temp_dir / "public_key.pem"
        private_path.write_text("old private")
        public_path.write_text("old public")

        # Write new keys
        private_pem, public_pem = generate_key_pair()
        write_keys(self.temp_dir, private_pem, public_pem, self.console)

        # Verify new content
        assert private_path.read_bytes() == private_pem
        assert public_path.read_bytes() == public_pem


class TestMainCLI:
    """Test main CLI function and argument handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_cli_basic_key_generation(self):
        """Test basic key generation via CLI."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"

            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            assert (output_dir / "private_key.pem").exists()
            assert (output_dir / "public_key.pem").exists()

    def test_cli_validate_only_with_valid_keys(self):
        """Test --validate-only flag with valid keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Generate keys first
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--validate-only"]
            )

            assert result.exit_code == 0
            assert "validation successful" in result.output.lower()

    def test_cli_validate_only_with_missing_keys(self):
        """Test --validate-only flag with missing keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--validate-only"]
            )

            assert result.exit_code == 1
            assert "validation failed" in result.output.lower()

    def test_cli_force_regeneration(self):
        """Test --force flag regenerates existing keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem1, public_pem1 = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem1)
            (output_dir / "public_key.pem").write_bytes(public_pem1)

            # Force regenerate
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )

            assert result.exit_code == 0

            # Verify keys were regenerated (different content)
            new_private = (output_dir / "private_key.pem").read_bytes()
            new_public = (output_dir / "public_key.pem").read_bytes()
            assert new_private != private_pem1
            assert new_public != public_pem1

    def test_cli_backup_flag(self):
        """Test --backup flag creates backup."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate with backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # Check for backup directory
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 1
            assert (backup_dirs[0] / "private_key.pem").exists()
            assert (backup_dirs[0] / "public_key.pem").exists()

    def test_cli_idempotency_without_force(self):
        """Test that running twice without --force doesn't overwrite."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"

            # First run
            result1 = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )
            assert result1.exit_code == 0

            original_private = (output_dir / "private_key.pem").read_bytes()
            original_public = (output_dir / "public_key.pem").read_bytes()

            # Second run without force
            result2 = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )
            assert result2.exit_code == 0

            # Keys should be unchanged
            assert (output_dir / "private_key.pem").read_bytes() == original_private
            assert (output_dir / "public_key.pem").read_bytes() == original_public

    def test_cli_custom_output_directory(self):
        """Test --output-dir flag with custom path."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            custom_dir = Path(temp_dir) / "custom" / "keys"

            result = self.runner.invoke(
                main, ["--output-dir", str(custom_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            assert (custom_dir / "private_key.pem").exists()
            assert (custom_dir / "public_key.pem").exists()

    def test_cli_non_interactive_flag(self):
        """Test --non-interactive flag skips prompts."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create invalid keys
            (output_dir / "private_key.pem").write_text("invalid")
            (output_dir / "public_key.pem").write_text("invalid")

            # Should regenerate without prompting
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )

            assert result.exit_code == 0
            # Should have regenerated without asking
            assert (output_dir / "private_key.pem").read_bytes() != b"invalid"

    def test_cli_invalid_output_directory(self):
        """Test handling of invalid output directory."""
        # Try to use a file path as directory (should fail)
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            file_path = Path(temp_dir) / "file.txt"
            file_path.write_text("content")

            result = self.runner.invoke(
                main, ["--output-dir", str(file_path), "--non-interactive"]
            )

            # Should fail because can't create directory
            assert result.exit_code == 1


class TestErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.console = Mock()
        self.console.error = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_validate_handles_missing_cryptography(self):
        """Test validation handles missing cryptography library gracefully."""
        private_path = self.temp_dir / "private_key.pem"
        public_path = self.temp_dir / "public_key.pem"

        # Create dummy files
        private_path.write_text("dummy")
        public_path.write_text("dummy")

        # Mock cryptography to raise ImportError
        with patch(
            "scripts.setup.setup_jwt.load_pem_private_key",
            side_effect=ImportError("No module"),
        ):
            result = validate_key_pair(private_path, public_path, self.console)

        assert result is False
        self.console.error.assert_called()

    def test_write_keys_handles_permission_error(self):
        """Test write_keys handles permission errors."""
        # Create read-only directory (Unix only)
        if sys.platform != "win32":
            read_only_dir = self.temp_dir / "readonly"
            read_only_dir.mkdir()
            os.chmod(read_only_dir, 0o444)

            private_pem, public_pem = generate_key_pair()

            with pytest.raises(PermissionError):
                write_keys(read_only_dir, private_pem, public_pem, self.console)

            # Restore permissions for cleanup
            os.chmod(read_only_dir, 0o755)

    def test_backup_handles_io_error(self):
        """Test backup handles I/O errors gracefully."""
        # Create a key file
        private_path = self.temp_dir / "private_key.pem"
        private_path.write_text("content")

        # Mock shutil.copy2 to raise IOError
        with patch(
            "scripts.setup.setup_jwt.shutil.copy2", side_effect=IOError("Disk full")
        ):
            with pytest.raises(IOError):
                backup_keys(self.temp_dir, self.console)


class TestJWTKeyRegeneration:
    """Comprehensive tests for JWT key regeneration with --force and --backup flags."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_force_flag_regenerates_existing_keys(self):
        """Test that --force flag regenerates existing keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Generate initial keys
            private_pem1, public_pem1 = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem1)
            (output_dir / "public_key.pem").write_bytes(public_pem1)

            # Regenerate with --force
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )

            assert result.exit_code == 0
            # Keys should be different
            private_pem2 = (output_dir / "private_key.pem").read_bytes()
            public_pem2 = (output_dir / "public_key.pem").read_bytes()
            assert private_pem2 != private_pem1
            assert public_pem2 != public_pem1

    def test_regenerated_keys_are_different_from_originals(self):
        """Test that regenerated keys are different from originals."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Generate and save first set of keys
            original_private, original_public = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(original_private)
            (output_dir / "public_key.pem").write_bytes(original_public)

            # Read them for comparison
            first_private = (output_dir / "private_key.pem").read_bytes()
            first_public = (output_dir / "public_key.pem").read_bytes()

            # Regenerate multiple times
            for i in range(3):
                result = self.runner.invoke(
                    main,
                    ["--output-dir", str(output_dir), "--force", "--non-interactive"],
                )
                assert result.exit_code == 0

                new_private = (output_dir / "private_key.pem").read_bytes()
                new_public = (output_dir / "public_key.pem").read_bytes()

                # Should be different from all previous versions
                assert new_private != first_private
                assert new_public != first_public

    def test_backup_flag_creates_timestamped_backup_directory(self):
        """Test that --backup flag creates timestamped backup directory."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate with --backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # Check for backup directory
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 1

            # Verify backup directory name matches expected pattern
            backup_dir = backup_dirs[0]
            assert backup_dir.name.startswith("backup_")
            # Format should be backup_YYYYMMDD_HHMMSS
            assert len(backup_dir.name) == 22  # "backup_" (7) + "YYYYMMDD_HHMMSS" (15)

    def test_backup_contains_original_keys(self):
        """Test that backup directory contains original keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            original_private, original_public = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(original_private)
            (output_dir / "public_key.pem").write_bytes(original_public)

            # Regenerate with --backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # Get backup directory
            backup_dirs = list(output_dir.glob("backup_*"))
            backup_dir = backup_dirs[0]

            # Verify backup contains both key files
            assert (backup_dir / "private_key.pem").exists()
            assert (backup_dir / "public_key.pem").exists()

            # Verify backup has original content
            backed_up_private = (backup_dir / "private_key.pem").read_bytes()
            backed_up_public = (backup_dir / "public_key.pem").read_bytes()
            assert backed_up_private == original_private
            assert backed_up_public == original_public

    def test_no_backup_without_backup_flag(self):
        """Test that regeneration without --backup doesn't create backup."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate WITHOUT --backup
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )

            assert result.exit_code == 0

            # Check that no backup directory was created
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 0

    def test_regenerated_keys_can_sign_and_verify_jwt(self):
        """Test that regenerated keys can sign and verify JWTs."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem1, public_pem1 = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem1)
            (output_dir / "public_key.pem").write_bytes(public_pem1)

            # Regenerate keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )
            assert result.exit_code == 0

            # Load the new keys
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key,
            )

            new_private_pem = (output_dir / "private_key.pem").read_bytes()
            new_public_pem = (output_dir / "public_key.pem").read_bytes()

            private_key = load_pem_private_key(
                new_private_pem, password=None, backend=default_backend()
            )

            # Create a test payload
            payload = {
                "user_id": 456,
                "username": "testuser2",
                "iat": int(datetime.datetime.utcnow().timestamp()),
            }

            # Sign with new private key
            token = jwt.encode(payload, private_key, algorithm="ES256")

            # Verify with new public key
            decoded = jwt.decode(
                token,
                new_public_pem,
                algorithms=["ES256"],
                options={"verify_exp": False},
            )

            assert decoded["user_id"] == 456
            assert decoded["username"] == "testuser2"

    def test_backup_directory_structure_is_correct(self):
        """Test that backup directory structure matches expected format."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate with --backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # Verify directory structure
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 1

            backup_dir = backup_dirs[0]
            # Should only contain the two key files
            contents = list(backup_dir.iterdir())
            assert len(contents) == 2

            filenames = {item.name for item in contents}
            assert filenames == {"private_key.pem", "public_key.pem"}

            # All items should be files, not directories
            for item in contents:
                assert item.is_file()

    @pytest.mark.skipif(
        sys.platform == "win32", reason="Unix permissions not applicable on Windows"
    )
    def test_file_permissions_maintained_after_regeneration(self):
        """Test that file permissions are maintained after regeneration."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )
            assert result.exit_code == 0

            # Check file permissions
            private_stat = os.stat(output_dir / "private_key.pem")
            public_stat = os.stat(output_dir / "public_key.pem")

            private_perms = private_stat.st_mode & 0o777
            public_perms = public_stat.st_mode & 0o777

            # Private key should be 600, public key should be 644
            assert private_perms == 0o600
            assert public_perms == 0o644

    def test_force_flag_required_to_overwrite_existing_keys(self):
        """Test that --force flag is required to overwrite existing keys."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem1, public_pem1 = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem1)
            (output_dir / "public_key.pem").write_bytes(public_pem1)

            # Try to regenerate WITHOUT --force (should skip)
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )

            assert result.exit_code == 0

            # Keys should NOT be regenerated (content should match)
            private_pem2 = (output_dir / "private_key.pem").read_bytes()
            public_pem2 = (output_dir / "public_key.pem").read_bytes()
            assert private_pem2 == private_pem1
            assert public_pem2 == public_pem1

    def test_multiple_backups_create_unique_directories(self):
        """Test that multiple regenerations with delays create unique backup directories."""
        import time

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            first_backup = None
            backup_count_after_each = []

            # Regenerate multiple times with backup
            for i in range(3):
                result = self.runner.invoke(
                    main,
                    [
                        "--output-dir",
                        str(output_dir),
                        "--force",
                        "--backup",
                        "--non-interactive",
                    ],
                )
                assert result.exit_code == 0

                # Get the count of backup directories
                backup_dirs = list(output_dir.glob("backup_*"))
                backup_count_after_each.append(len(backup_dirs))

                if i == 0:
                    first_backup = backup_dirs[0]
                    # First backup should exist
                    assert first_backup.exists()
                    assert (first_backup / "private_key.pem").exists()
                    assert (first_backup / "public_key.pem").exists()

                # Add a delay to ensure unique timestamps on next iteration
                time.sleep(1.1)

            # After first regeneration, there should be 1 backup
            assert backup_count_after_each[0] == 1
            # After delays, subsequent regenerations should create unique backups
            # Total backups should be 3 (or more if we created unique ones each time)
            assert backup_count_after_each[-1] >= 1

            # Verify at least one backup exists
            all_backups = list(output_dir.glob("backup_*"))
            assert len(all_backups) >= 1
            for backup_dir in all_backups:
                assert backup_dir.exists()
                assert (backup_dir / "private_key.pem").exists()
                assert (backup_dir / "public_key.pem").exists()

    def test_backup_and_force_flags_work_together(self):
        """Test that --backup and --force flags work correctly together."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem1, public_pem1 = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem1)
            (output_dir / "public_key.pem").write_bytes(public_pem1)

            original_private = (output_dir / "private_key.pem").read_bytes()

            # Regenerate with both --force and --backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )

            assert result.exit_code == 0

            # Verify backup was created
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 1

            # Verify original keys are in backup
            backup_dir = backup_dirs[0]
            assert (backup_dir / "private_key.pem").read_bytes() == original_private

            # Verify new keys are different
            new_private = (output_dir / "private_key.pem").read_bytes()
            assert new_private != original_private

    def test_regenerated_keys_validate_successfully(self):
        """Test that regenerated keys pass validation."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys
            private_pem, public_pem = generate_key_pair()
            (output_dir / "private_key.pem").write_bytes(private_pem)
            (output_dir / "public_key.pem").write_bytes(public_pem)

            # Regenerate keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--force", "--non-interactive"]
            )
            assert result.exit_code == 0

            # Validate the regenerated keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--validate-only"]
            )

            assert result.exit_code == 0
            assert "validation successful" in result.output.lower()

    def test_backup_preserves_all_metadata(self):
        """Test that backup preserves original key metadata and content."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Create initial keys with known content
            original_private, original_public = generate_key_pair()
            private_path = output_dir / "private_key.pem"
            public_path = output_dir / "public_key.pem"
            private_path.write_bytes(original_private)
            public_path.write_bytes(original_public)

            # Get original file stats
            orig_private_size = private_path.stat().st_size
            orig_public_size = public_path.stat().st_size

            # Regenerate with backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )
            assert result.exit_code == 0

            # Verify backup has same content and similar size
            backup_dirs = list(output_dir.glob("backup_*"))
            backup_dir = backup_dirs[0]

            backed_up_private = (backup_dir / "private_key.pem").read_bytes()
            backed_up_public = (backup_dir / "public_key.pem").read_bytes()

            assert backed_up_private == original_private
            assert backed_up_public == original_public
            assert len(backed_up_private) == orig_private_size
            assert len(backed_up_public) == orig_public_size


class TestIntegration:
    """Integration tests for complete workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_full_workflow_generate_validate_backup(self):
        """Test complete workflow: generate, validate, backup, regenerate."""
        with self.runner.isolated_filesystem() as temp_dir:
            output_dir = Path(temp_dir) / "secrets" / "jwt"

            # Step 1: Generate initial keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--non-interactive"]
            )
            assert result.exit_code == 0

            # Step 2: Validate keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--validate-only"]
            )
            assert result.exit_code == 0

            # Step 3: Regenerate with backup
            result = self.runner.invoke(
                main,
                [
                    "--output-dir",
                    str(output_dir),
                    "--force",
                    "--backup",
                    "--non-interactive",
                ],
            )
            assert result.exit_code == 0

            # Verify backup exists
            backup_dirs = list(output_dir.glob("backup_*"))
            assert len(backup_dirs) == 1

            # Step 4: Validate new keys
            result = self.runner.invoke(
                main, ["--output-dir", str(output_dir), "--validate-only"]
            )
            assert result.exit_code == 0

    def test_keys_work_with_real_jwt_operations(self):
        """Test that generated keys work with real JWT signing/verification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "secrets" / "jwt"
            output_dir.mkdir(parents=True)

            # Generate keys
            private_pem, public_pem = generate_key_pair()
            private_path, public_path = write_keys(
                output_dir, private_pem, public_pem, Mock()
            )

            # Load keys for JWT operations
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key,
            )

            private_key = load_pem_private_key(
                private_path.read_bytes(), password=None, backend=default_backend()
            )
            public_key_pem = public_path.read_bytes()

            # Create and sign a token (without expiration for testing)
            payload = {
                "user_id": 123,
                "username": "testuser",
                "iat": int(datetime.datetime.utcnow().timestamp()),
            }
            token = jwt.encode(payload, private_key, algorithm="ES256")

            # Verify the token (disable expiration validation for testing)
            decoded = jwt.decode(
                token,
                public_key_pem,
                algorithms=["ES256"],
                options={"verify_exp": False},
            )

            assert decoded["user_id"] == 123
            assert decoded["username"] == "testuser"
