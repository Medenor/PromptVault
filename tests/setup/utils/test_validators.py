# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for validation utility functions."""

import pytest
import tempfile
import os
from pathlib import Path
from scripts.setup.utils.validators import (
    validate_database_url,
    validate_password_strength,
    validate_port,
    validate_hostname,
    validate_email,
    validate_path,
    validate_jwt_key,
    validate_env_file,
)


class TestValidateDatabaseUrl:
    """Test database URL validation."""

    def test_valid_postgresql_url(self):
        """Test valid PostgreSQL URL."""
        is_valid, error = validate_database_url(
            "postgresql://user:pass@localhost:5432/database"
        )
        assert is_valid is True
        assert error is None

    def test_valid_sqlite_url_absolute(self):
        """Test valid SQLite URL with absolute path."""
        is_valid, error = validate_database_url("sqlite:///./data.db")
        assert is_valid is True
        assert error is None

    def test_valid_sqlite_url_relative(self):
        """Test valid SQLite URL with relative path."""
        is_valid, error = validate_database_url("sqlite://./relative.db")
        assert is_valid is True
        assert error is None

    def test_empty_url(self):
        """Test empty URL returns error."""
        is_valid, error = validate_database_url("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_url(self):
        """Test None URL returns error."""
        is_valid, error = validate_database_url(None)
        assert is_valid is False
        assert error is not None

    def test_unsupported_scheme(self):
        """Test unsupported database scheme."""
        is_valid, error = validate_database_url("mysql://localhost/db")
        assert is_valid is False
        assert "unsupported" in error.lower()

    def test_postgresql_missing_username(self):
        """Test PostgreSQL URL missing username."""
        is_valid, error = validate_database_url("postgresql://:pass@localhost:5432/db")
        assert is_valid is False
        assert "username" in error.lower()

    def test_postgresql_missing_password(self):
        """Test PostgreSQL URL missing password."""
        is_valid, error = validate_database_url("postgresql://user@localhost:5432/db")
        assert is_valid is False
        assert "password" in error.lower()

    def test_postgresql_missing_hostname(self):
        """Test PostgreSQL URL missing hostname."""
        is_valid, error = validate_database_url("postgresql://user:pass@:5432/db")
        assert is_valid is False
        assert "hostname" in error.lower()

    def test_postgresql_missing_port(self):
        """Test PostgreSQL URL missing port."""
        is_valid, error = validate_database_url("postgresql://user:pass@localhost/db")
        assert is_valid is False
        assert "port" in error.lower()

    def test_postgresql_missing_database_name(self):
        """Test PostgreSQL URL missing database name."""
        is_valid, error = validate_database_url("postgresql://user:pass@localhost:5432/")
        assert is_valid is False
        assert "database name" in error.lower()

    def test_sqlite_missing_path(self):
        """Test SQLite URL missing path."""
        is_valid, error = validate_database_url("sqlite://")
        assert is_valid is False
        assert "path" in error.lower()

    def test_invalid_url_format(self):
        """Test completely invalid URL format."""
        is_valid, error = validate_database_url("not-a-url")
        assert is_valid is False
        assert error is not None


class TestValidatePasswordStrength:
    """Test password strength validation."""

    def test_valid_strong_password(self):
        """Test valid strong password."""
        is_valid, error = validate_password_strength("MyStr0ng!Password123")
        assert is_valid is True
        assert error is None

    def test_password_minimum_length(self):
        """Test password at minimum length."""
        is_valid, error = validate_password_strength("Abcde1!234567890")  # 16 chars
        assert is_valid is True
        assert error is None

    def test_password_too_short(self):
        """Test password below minimum length."""
        is_valid, error = validate_password_strength("Short1!")
        assert is_valid is False
        assert "16 characters" in error

    def test_password_missing_uppercase(self):
        """Test password missing uppercase letter."""
        is_valid, error = validate_password_strength("lowercase123!@#$")
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_missing_lowercase(self):
        """Test password missing lowercase letter."""
        is_valid, error = validate_password_strength("UPPERCASE123!@#$")
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_missing_digit(self):
        """Test password missing digit."""
        is_valid, error = validate_password_strength("NoDigitsHere!@#$")
        assert is_valid is False
        assert "digit" in error.lower()

    def test_password_missing_special_char(self):
        """Test password missing special character."""
        is_valid, error = validate_password_strength("NoSpecialChar123")
        assert is_valid is False
        assert "special character" in error.lower()

    def test_empty_password(self):
        """Test empty password."""
        is_valid, error = validate_password_strength("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_password(self):
        """Test None password."""
        is_valid, error = validate_password_strength(None)
        assert is_valid is False
        assert error is not None

    def test_custom_minimum_length(self):
        """Test custom minimum length."""
        is_valid, error = validate_password_strength("Ab1!", min_length=4)
        assert is_valid is True
        assert error is None

    def test_password_with_all_special_chars(self):
        """Test password with various special characters."""
        special_chars = "!@#$%^&*()_+-=[]{}';:,.<>?/\\|`~"
        for char in special_chars:
            password = f"ValidPass123{char}more"
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Failed for special char: {char}"


class TestValidatePort:
    """Test port number validation."""

    def test_valid_port_int(self):
        """Test valid port as integer."""
        is_valid, error = validate_port(8080)
        assert is_valid is True
        assert error is None

    def test_valid_port_string(self):
        """Test valid port as string."""
        is_valid, error = validate_port("443")
        assert is_valid is True
        assert error is None

    def test_port_minimum(self):
        """Test port at minimum value."""
        is_valid, error = validate_port(1)
        assert is_valid is True
        assert error is None

    def test_port_maximum(self):
        """Test port at maximum value."""
        is_valid, error = validate_port(65535)
        assert is_valid is True
        assert error is None

    def test_port_below_minimum(self):
        """Test port below minimum."""
        is_valid, error = validate_port(0)
        assert is_valid is False
        assert "between 1 and 65535" in error

    def test_port_above_maximum(self):
        """Test port above maximum."""
        is_valid, error = validate_port(70000)
        assert is_valid is False
        assert "between 1 and 65535" in error

    def test_port_negative(self):
        """Test negative port number."""
        is_valid, error = validate_port(-1)
        assert is_valid is False
        assert error is not None

    def test_port_invalid_string(self):
        """Test invalid port string."""
        is_valid, error = validate_port("not-a-number")
        assert is_valid is False
        assert "valid number" in error.lower()

    def test_port_none(self):
        """Test None port."""
        is_valid, error = validate_port(None)
        assert is_valid is False
        assert error is not None


class TestValidateHostname:
    """Test hostname validation."""

    def test_localhost(self):
        """Test localhost."""
        is_valid, error = validate_hostname("localhost")
        assert is_valid is True
        assert error is None

    def test_valid_domain(self):
        """Test valid domain name."""
        is_valid, error = validate_hostname("example.com")
        assert is_valid is True
        assert error is None

    def test_valid_subdomain(self):
        """Test valid subdomain."""
        is_valid, error = validate_hostname("sub.example.com")
        assert is_valid is True
        assert error is None

    def test_valid_ipv4(self):
        """Test valid IPv4 address."""
        is_valid, error = validate_hostname("192.168.1.1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv6_localhost(self):
        """Test valid IPv6 localhost."""
        is_valid, error = validate_hostname("::1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv6(self):
        """Test valid IPv6 address."""
        is_valid, error = validate_hostname("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert is_valid is True
        assert error is None

    def test_ipv4_invalid_octet(self):
        """Test IPv4 with invalid octet."""
        is_valid, error = validate_hostname("192.168.1.256")
        assert is_valid is False
        assert "255" in error

    def test_empty_hostname(self):
        """Test empty hostname."""
        is_valid, error = validate_hostname("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_hostname(self):
        """Test None hostname."""
        is_valid, error = validate_hostname(None)
        assert is_valid is False
        assert error is not None

    def test_hostname_too_long(self):
        """Test hostname exceeding maximum length."""
        long_hostname = "a" * 254
        is_valid, error = validate_hostname(long_hostname)
        assert is_valid is False
        assert "253" in error

    def test_hostname_with_hyphens(self):
        """Test hostname with hyphens."""
        is_valid, error = validate_hostname("my-server.example-domain.com")
        assert is_valid is True
        assert error is None

    def test_hostname_starting_with_hyphen(self):
        """Test hostname starting with hyphen."""
        is_valid, error = validate_hostname("-invalid.com")
        assert is_valid is False
        assert error is not None

    def test_hostname_ending_with_hyphen(self):
        """Test hostname ending with hyphen."""
        is_valid, error = validate_hostname("invalid-.com")
        assert is_valid is False
        assert error is not None

    def test_hostname_label_too_long(self):
        """Test hostname with label exceeding 63 characters."""
        long_label = "a" * 64
        hostname = f"{long_label}.example.com"
        is_valid, error = validate_hostname(hostname)
        assert is_valid is False
        assert "63" in error


class TestValidateEmail:
    """Test email validation."""

    def test_valid_email(self):
        """Test valid email address."""
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_subdomain(self):
        """Test valid email with subdomain."""
        is_valid, error = validate_email("user@mail.example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_plus(self):
        """Test valid email with plus sign."""
        is_valid, error = validate_email("user+tag@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_dots(self):
        """Test valid email with dots in local part."""
        is_valid, error = validate_email("first.last@example.com")
        assert is_valid is True
        assert error is None

    def test_empty_email(self):
        """Test empty email."""
        is_valid, error = validate_email("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_email(self):
        """Test None email."""
        is_valid, error = validate_email(None)
        assert is_valid is False
        assert error is not None

    def test_email_missing_at(self):
        """Test email missing @ symbol."""
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_email_missing_domain(self):
        """Test email missing domain."""
        is_valid, error = validate_email("user@")
        assert is_valid is False
        assert error is not None

    def test_email_missing_local_part(self):
        """Test email missing local part."""
        is_valid, error = validate_email("@example.com")
        assert is_valid is False
        assert error is not None

    def test_email_local_part_too_long(self):
        """Test email with local part exceeding 64 characters."""
        long_local = "a" * 65
        is_valid, error = validate_email(f"{long_local}@example.com")
        assert is_valid is False
        assert "64" in error

    def test_email_domain_too_long(self):
        """Test email with domain exceeding 253 characters."""
        long_domain = "a" * 254
        is_valid, error = validate_email(f"user@{long_domain}.com")
        assert is_valid is False
        assert "253" in error

    def test_email_consecutive_dots(self):
        """Test email with consecutive dots."""
        is_valid, error = validate_email("user..name@example.com")
        assert is_valid is False
        assert "consecutive dots" in error.lower()

    def test_email_starting_with_dot(self):
        """Test email starting with dot."""
        is_valid, error = validate_email(".user@example.com")
        assert is_valid is False
        assert "dot" in error.lower()

    def test_email_ending_with_dot(self):
        """Test email ending with dot in local part."""
        is_valid, error = validate_email("user.@example.com")
        assert is_valid is False
        assert "dot" in error.lower()


class TestValidatePath:
    """Test path validation."""

    def test_valid_path_no_existence_check(self):
        """Test valid path without existence check."""
        is_valid, error = validate_path("/tmp/test.txt")
        assert is_valid is True
        assert error is None

    def test_valid_relative_path(self):
        """Test valid relative path."""
        is_valid, error = validate_path("./config/settings.yml")
        assert is_valid is True
        assert error is None

    def test_empty_path(self):
        """Test empty path."""
        is_valid, error = validate_path("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_path(self):
        """Test None path."""
        is_valid, error = validate_path(None)
        assert is_valid is False
        assert error is not None

    def test_existing_path(self):
        """Test existing path with must_exist=True."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            is_valid, error = validate_path(tmp_path, must_exist=True)
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_nonexistent_path_with_must_exist(self):
        """Test nonexistent path with must_exist=True."""
        is_valid, error = validate_path("/nonexistent/path/file.txt", must_exist=True)
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_path_with_nonexistent_parent(self):
        """Test path with nonexistent parent directory."""
        is_valid, error = validate_path("/nonexistent/parent/file.txt", must_exist=False)
        assert is_valid is False
        assert "parent" in error.lower()


class TestValidateJwtKey:
    """Test JWT key validation."""

    def test_valid_ec_private_key(self):
        """Test valid EC private key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp.write("-----BEGIN EC PRIVATE KEY-----\n")
            tmp.write("MHcCAQEEIIGlRHnRQUSMPxd5JPbN4Pt3VfxaJi75uyNf8qRpWNYGoAoGCCqGSM49\n")
            tmp.write("-----END EC PRIVATE KEY-----\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "private")
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_valid_pkcs8_private_key(self):
        """Test valid PKCS#8 private key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp.write("-----BEGIN PRIVATE KEY-----\n")
            tmp.write("MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgabc123xyz\n")
            tmp.write("-----END PRIVATE KEY-----\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "private")
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_valid_public_key(self):
        """Test valid public key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp.write("-----BEGIN PUBLIC KEY-----\n")
            tmp.write("MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE123abc\n")
            tmp.write("-----END PUBLIC KEY-----\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "public")
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_empty_key_path(self):
        """Test empty key path."""
        is_valid, error = validate_jwt_key("", "private")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_key_path(self):
        """Test None key path."""
        is_valid, error = validate_jwt_key(None, "private")
        assert is_valid is False
        assert error is not None

    def test_invalid_key_type(self):
        """Test invalid key type."""
        is_valid, error = validate_jwt_key("/path/to/key.pem", "invalid")
        assert is_valid is False
        assert "invalid key type" in error.lower()

    def test_nonexistent_key_file(self):
        """Test nonexistent key file."""
        is_valid, error = validate_jwt_key("/nonexistent/key.pem", "private")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_key_path_is_directory(self):
        """Test key path pointing to directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = validate_jwt_key(tmpdir, "private")
            assert is_valid is False
            assert "not a file" in error.lower()

    def test_empty_key_file(self):
        """Test empty key file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "private")
            assert is_valid is False
            assert "empty" in error.lower()
        finally:
            os.unlink(tmp_path)

    def test_invalid_pem_format_private(self):
        """Test invalid PEM format for private key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp.write("This is not a valid PEM file\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "private")
            assert is_valid is False
            assert "invalid" in error.lower()
        finally:
            os.unlink(tmp_path)

    def test_invalid_pem_format_public(self):
        """Test invalid PEM format for public key."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.pem') as tmp:
            tmp.write("Not a PEM file\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_jwt_key(tmp_path, "public")
            assert is_valid is False
            assert "invalid" in error.lower()
        finally:
            os.unlink(tmp_path)


class TestValidateEnvFile:
    """Test .env file validation."""

    def test_valid_env_file(self):
        """Test valid .env file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("DATABASE_URL=postgresql://localhost/db\n")
            tmp.write("DEBUG=false\n")
            tmp.write("# Comment line\n")
            tmp.write("\n")
            tmp.write("SECRET_KEY=abc123\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_env_file(tmp_path)
            assert is_valid is True
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_empty_env_file(self):
        """Test empty .env file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp_path = tmp.name

        try:
            is_valid, error = validate_env_file(tmp_path)
            assert is_valid is True  # Empty file is valid
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_env_file_missing_equals(self):
        """Test .env file with line missing equals sign."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("DATABASE_URL=postgresql://localhost/db\n")
            tmp.write("INVALID_LINE\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_env_file(tmp_path)
            assert is_valid is False
            assert "=" in error
        finally:
            os.unlink(tmp_path)

    def test_env_file_empty_variable_name(self):
        """Test .env file with empty variable name."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("=value\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_env_file(tmp_path)
            assert is_valid is False
            assert "empty variable name" in error.lower()
        finally:
            os.unlink(tmp_path)

    def test_env_file_invalid_variable_name(self):
        """Test .env file with invalid variable name."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("invalid-name=value\n")
            tmp_path = tmp.name

        try:
            is_valid, error = validate_env_file(tmp_path)
            assert is_valid is False
            assert "invalid variable name" in error.lower()
        finally:
            os.unlink(tmp_path)

    def test_env_file_nonexistent(self):
        """Test nonexistent .env file."""
        is_valid, error = validate_env_file("/nonexistent/.env")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_env_file_is_directory(self):
        """Test .env path pointing to directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, error = validate_env_file(tmpdir)
            assert is_valid is False
            assert "not a file" in error.lower()

    def test_empty_path(self):
        """Test empty path."""
        is_valid, error = validate_env_file("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_path(self):
        """Test None path."""
        is_valid, error = validate_env_file(None)
        assert is_valid is False
        assert error is not None
