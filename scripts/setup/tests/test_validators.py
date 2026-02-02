"""
Unit tests for validators.py module.

Tests all validation functions with valid and invalid inputs,
including edge cases for each validator.
"""

import pytest
import tempfile
from pathlib import Path

from scripts.setup.utils.validators import (
    validate_database_url,
    validate_password_strength,
    validate_port,
    validate_hostname,
    validate_email,
    validate_path,
    validate_jwt_key,
    validate_env_file
)


class TestDatabaseURLValidator:
    """Tests for validate_database_url function."""

    def test_valid_postgresql_url(self):
        """Test valid PostgreSQL database URL."""
        url = "postgresql://user:password@localhost:5432/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is True
        assert error is None

    def test_valid_postgresql_url_with_special_chars(self):
        """Test PostgreSQL URL with special characters in password."""
        url = "postgresql://user:p@ssw0rd!@localhost:5432/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is True
        assert error is None

    def test_valid_sqlite_url_absolute(self):
        """Test valid SQLite URL with absolute path."""
        url = "sqlite:////tmp/database.db"
        is_valid, error = validate_database_url(url)
        assert is_valid is True
        assert error is None

    def test_valid_sqlite_url_relative(self):
        """Test valid SQLite URL with relative path."""
        url = "sqlite:///./data.db"
        is_valid, error = validate_database_url(url)
        assert is_valid is True
        assert error is None

    def test_empty_url(self):
        """Test empty database URL."""
        is_valid, error = validate_database_url("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_url(self):
        """Test None as database URL."""
        is_valid, error = validate_database_url(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_unsupported_scheme(self):
        """Test unsupported database scheme."""
        url = "mysql://user:password@localhost:3306/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "unsupported" in error.lower()
        assert "mysql" in error.lower()

    def test_postgresql_missing_username(self):
        """Test PostgreSQL URL without username."""
        url = "postgresql://:password@localhost:5432/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "username" in error.lower()

    def test_postgresql_missing_password(self):
        """Test PostgreSQL URL without password."""
        url = "postgresql://user@localhost:5432/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "password" in error.lower()

    def test_postgresql_missing_hostname(self):
        """Test PostgreSQL URL without hostname."""
        url = "postgresql://user:password@:5432/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "hostname" in error.lower()

    def test_postgresql_missing_port(self):
        """Test PostgreSQL URL without port."""
        url = "postgresql://user:password@localhost/mydb"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "port" in error.lower()

    def test_postgresql_missing_database(self):
        """Test PostgreSQL URL without database name."""
        url = "postgresql://user:password@localhost:5432/"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "database name" in error.lower()

    def test_sqlite_missing_path(self):
        """Test SQLite URL without path."""
        url = "sqlite://"
        is_valid, error = validate_database_url(url)
        assert is_valid is False
        assert "path" in error.lower()

    def test_invalid_url_format(self):
        """Test completely invalid URL format."""
        url = "not-a-url"
        is_valid, error = validate_database_url(url)
        assert is_valid is False


class TestPasswordStrengthValidator:
    """Tests for validate_password_strength function."""

    def test_valid_strong_password(self):
        """Test valid strong password."""
        password = "Abcd1234!@#$efgh"
        is_valid, error = validate_password_strength(password)
        assert is_valid is True
        assert error is None

    def test_valid_password_minimum_length(self):
        """Test password with exact minimum length."""
        password = "Abcdefgh12345678!"
        is_valid, error = validate_password_strength(password, min_length=17)
        assert is_valid is True
        assert error is None

    def test_empty_password(self):
        """Test empty password."""
        is_valid, error = validate_password_strength("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_password(self):
        """Test None as password."""
        is_valid, error = validate_password_strength(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_password_too_short(self):
        """Test password shorter than minimum length."""
        password = "Short1!"
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert "at least 16 characters" in error

    def test_password_missing_uppercase(self):
        """Test password without uppercase letter."""
        password = "abcd1234!@#$efgh"
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_password_missing_lowercase(self):
        """Test password without lowercase letter."""
        password = "ABCD1234!@#$EFGH"
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert "lowercase" in error.lower()

    def test_password_missing_digit(self):
        """Test password without digit."""
        password = "Abcd!@#$efghijkl"
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert "digit" in error.lower()

    def test_password_missing_special_char(self):
        """Test password without special character."""
        password = "Abcd1234efghijkl"
        is_valid, error = validate_password_strength(password)
        assert is_valid is False
        assert "special character" in error.lower()

    def test_custom_minimum_length(self):
        """Test password validation with custom minimum length."""
        password = "Ab1!efgh"  # 8 characters
        is_valid, error = validate_password_strength(password, min_length=8)
        assert is_valid is True
        assert error is None

    def test_various_special_characters(self):
        """Test password with various special characters."""
        special_chars = "!@#$%^&*()_+-=[]{};<>?/|`~"
        for char in special_chars:
            password = f"Abcd1234{char}efghijkl"
            is_valid, error = validate_password_strength(password)
            assert is_valid is True, f"Failed for special char: {char}"


class TestPortValidator:
    """Tests for validate_port function."""

    def test_valid_port_as_int(self):
        """Test valid port number as integer."""
        is_valid, error = validate_port(8080)
        assert is_valid is True
        assert error is None

    def test_valid_port_as_string(self):
        """Test valid port number as string."""
        is_valid, error = validate_port("8080")
        assert is_valid is True
        assert error is None

    def test_port_1(self):
        """Test minimum valid port (1)."""
        is_valid, error = validate_port(1)
        assert is_valid is True
        assert error is None

    def test_port_65535(self):
        """Test maximum valid port (65535)."""
        is_valid, error = validate_port(65535)
        assert is_valid is True
        assert error is None

    def test_port_0(self):
        """Test invalid port 0."""
        is_valid, error = validate_port(0)
        assert is_valid is False
        assert "between 1 and 65535" in error

    def test_port_negative(self):
        """Test negative port number."""
        is_valid, error = validate_port(-100)
        assert is_valid is False
        assert "between 1 and 65535" in error

    def test_port_too_large(self):
        """Test port number exceeding maximum."""
        is_valid, error = validate_port(70000)
        assert is_valid is False
        assert "between 1 and 65535" in error

    def test_port_invalid_string(self):
        """Test non-numeric string as port."""
        is_valid, error = validate_port("not-a-port")
        assert is_valid is False
        assert "valid number" in error.lower()

    def test_port_none(self):
        """Test None as port."""
        is_valid, error = validate_port(None)
        assert is_valid is False
        assert "valid number" in error.lower()

    def test_common_ports(self):
        """Test common port numbers."""
        common_ports = [80, 443, 3000, 5432, 27017, 6379]
        for port in common_ports:
            is_valid, error = validate_port(port)
            assert is_valid is True, f"Failed for port: {port}"


class TestHostnameValidator:
    """Tests for validate_hostname function."""

    def test_localhost(self):
        """Test localhost hostname."""
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
        is_valid, error = validate_hostname("api.example.com")
        assert is_valid is True
        assert error is None

    def test_valid_ipv4(self):
        """Test valid IPv4 address."""
        is_valid, error = validate_hostname("192.168.1.1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv4_localhost(self):
        """Test IPv4 localhost."""
        is_valid, error = validate_hostname("127.0.0.1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv6_localhost(self):
        """Test IPv6 localhost."""
        is_valid, error = validate_hostname("::1")
        assert is_valid is True
        assert error is None

    def test_valid_ipv6(self):
        """Test valid IPv6 address."""
        is_valid, error = validate_hostname("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert is_valid is True
        assert error is None

    def test_empty_hostname(self):
        """Test empty hostname."""
        is_valid, error = validate_hostname("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_hostname(self):
        """Test None as hostname."""
        is_valid, error = validate_hostname(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_invalid_ipv4_octet(self):
        """Test IPv4 with invalid octet value."""
        is_valid, error = validate_hostname("192.168.1.256")
        assert is_valid is False
        assert "exceeds 255" in error

    def test_hostname_too_long(self):
        """Test hostname exceeding maximum length."""
        long_hostname = "a" * 260
        is_valid, error = validate_hostname(long_hostname)
        assert is_valid is False
        assert "exceeds maximum length" in error

    def test_label_too_long(self):
        """Test hostname with label exceeding 63 characters."""
        long_label = "a" * 64 + ".example.com"
        is_valid, error = validate_hostname(long_label)
        assert is_valid is False
        # The regex pattern fails first, so we get the format error
        assert "invalid hostname format" in error.lower() or "exceeds maximum length" in error.lower()

    def test_hostname_with_hyphen(self):
        """Test valid hostname with hyphens."""
        is_valid, error = validate_hostname("my-server.example.com")
        assert is_valid is True
        assert error is None

    def test_hostname_starting_with_hyphen(self):
        """Test invalid hostname starting with hyphen."""
        is_valid, error = validate_hostname("-server.example.com")
        assert is_valid is False

    def test_hostname_ending_with_hyphen(self):
        """Test invalid hostname ending with hyphen."""
        is_valid, error = validate_hostname("server-.example.com")
        assert is_valid is False


class TestEmailValidator:
    """Tests for validate_email function."""

    def test_valid_email_simple(self):
        """Test simple valid email address."""
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_subdomain(self):
        """Test email with subdomain."""
        is_valid, error = validate_email("user@mail.example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_plus(self):
        """Test email with plus sign."""
        is_valid, error = validate_email("user+tag@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_dots(self):
        """Test email with dots in local part."""
        is_valid, error = validate_email("first.last@example.com")
        assert is_valid is True
        assert error is None

    def test_valid_email_with_hyphen(self):
        """Test email with hyphen in domain."""
        is_valid, error = validate_email("user@my-domain.com")
        assert is_valid is True
        assert error is None

    def test_empty_email(self):
        """Test empty email."""
        is_valid, error = validate_email("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_email(self):
        """Test None as email."""
        is_valid, error = validate_email(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_email_missing_at(self):
        """Test email without @ symbol."""
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False
        assert "invalid email format" in error.lower()

    def test_email_missing_domain(self):
        """Test email without domain."""
        is_valid, error = validate_email("user@")
        assert is_valid is False
        assert "invalid email format" in error.lower()

    def test_email_missing_local_part(self):
        """Test email without local part."""
        is_valid, error = validate_email("@example.com")
        assert is_valid is False
        assert "invalid email format" in error.lower()

    def test_email_consecutive_dots(self):
        """Test email with consecutive dots."""
        is_valid, error = validate_email("user..name@example.com")
        assert is_valid is False
        assert "consecutive dots" in error.lower()

    def test_email_local_part_starts_with_dot(self):
        """Test email with local part starting with dot."""
        is_valid, error = validate_email(".user@example.com")
        assert is_valid is False
        assert "cannot start" in error.lower()

    def test_email_local_part_ends_with_dot(self):
        """Test email with local part ending with dot."""
        is_valid, error = validate_email("user.@example.com")
        assert is_valid is False
        assert "cannot start or end with a dot" in error.lower()

    def test_email_local_part_too_long(self):
        """Test email with local part exceeding 64 characters."""
        long_local = "a" * 65 + "@example.com"
        is_valid, error = validate_email(long_local)
        assert is_valid is False
        assert "local part" in error.lower()
        assert "64" in error

    def test_email_domain_too_long(self):
        """Test email with domain exceeding 253 characters."""
        long_domain = "user@" + "a" * 250 + ".com"
        is_valid, error = validate_email(long_domain)
        assert is_valid is False
        assert "domain" in error.lower()


class TestPathValidator:
    """Tests for validate_path function."""

    def test_valid_absolute_path(self):
        """Test valid absolute path."""
        is_valid, error = validate_path("/tmp/test.txt")
        assert is_valid is True
        assert error is None

    def test_valid_relative_path(self):
        """Test valid relative path."""
        is_valid, error = validate_path("./test.txt")
        assert is_valid is True
        assert error is None

    def test_empty_path(self):
        """Test empty path."""
        is_valid, error = validate_path("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_path(self):
        """Test None as path."""
        is_valid, error = validate_path(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_path_must_exist_valid(self, tmp_path):
        """Test existing path with must_exist=True."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        is_valid, error = validate_path(str(test_file), must_exist=True)
        assert is_valid is True
        assert error is None

    def test_path_must_exist_missing(self):
        """Test non-existing path with must_exist=True."""
        is_valid, error = validate_path("/nonexistent/path/file.txt", must_exist=True)
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_path_parent_does_not_exist(self):
        """Test path with non-existing parent directory."""
        is_valid, error = validate_path("/nonexistent/directory/file.txt")
        assert is_valid is False
        assert "parent directory does not exist" in error.lower()

    def test_path_in_existing_directory(self, tmp_path):
        """Test path in existing directory without must_exist."""
        test_file = tmp_path / "newfile.txt"

        is_valid, error = validate_path(str(test_file))
        assert is_valid is True
        assert error is None


class TestJWTKeyValidator:
    """Tests for validate_jwt_key function."""

    def test_valid_ec_private_key(self, tmp_path):
        """Test valid EC private key."""
        key_file = tmp_path / "private.pem"
        key_file.write_text("""-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIIGlRNkcKR16+LhAQbBqeJQbsmJ0g3CQ8zfGCKfEq+b6oAoGCCqGSM49
AwEHoUQDQgAEqQPgSJN+JQvBMJcLRr/TLmkPjU6qvVJKIvSl8pI7GqBQ2lGQ5xLB
S7rQKjWlwKmJ9TQkJLxEGQHVqPyQeLf3Ww==
-----END EC PRIVATE KEY-----""")

        is_valid, error = validate_jwt_key(str(key_file), "private")
        assert is_valid is True
        assert error is None

    def test_valid_pkcs8_private_key(self, tmp_path):
        """Test valid PKCS#8 private key."""
        key_file = tmp_path / "private.pem"
        key_file.write_text("""-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgCKZk/lGpZqwx5Cts
+zfMWYFSRMvDOqO+SkVL1vXr6SChRANCAARH7QlQUq1EwXiFm6P2FqT6PwDAGF4H
hZCwA4KKA2Y5N+TRtfJxLMvOPp2pVGz2gH4gCQQZKDcPxMvPz0A3dQiP
-----END PRIVATE KEY-----""")

        is_valid, error = validate_jwt_key(str(key_file), "private")
        assert is_valid is True
        assert error is None

    def test_valid_public_key(self, tmp_path):
        """Test valid public key."""
        key_file = tmp_path / "public.pem"
        key_file.write_text("""-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEqQPgSJN+JQvBMJcLRr/TLmkPjU6q
vVJKIvSl8pI7GqBQ2lGQ5xLBS7rQKjWlwKmJ9TQkJLxEGQHVqPyQeLf3Ww==
-----END PUBLIC KEY-----""")

        is_valid, error = validate_jwt_key(str(key_file), "public")
        assert is_valid is True
        assert error is None

    def test_empty_key_path(self):
        """Test empty key path."""
        is_valid, error = validate_jwt_key("", "private")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_key_path(self):
        """Test None as key path."""
        is_valid, error = validate_jwt_key(None, "private")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_invalid_key_type(self, tmp_path):
        """Test invalid key type."""
        key_file = tmp_path / "key.pem"
        key_file.write_text("content")

        is_valid, error = validate_jwt_key(str(key_file), "invalid")
        assert is_valid is False
        assert "invalid key type" in error.lower()

    def test_key_file_not_found(self):
        """Test non-existent key file."""
        is_valid, error = validate_jwt_key("/nonexistent/key.pem", "private")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_empty_key_file(self, tmp_path):
        """Test empty key file."""
        key_file = tmp_path / "empty.pem"
        key_file.write_text("")

        is_valid, error = validate_jwt_key(str(key_file), "private")
        assert is_valid is False
        assert "empty" in error.lower()

    def test_invalid_private_key_format(self, tmp_path):
        """Test invalid private key format."""
        key_file = tmp_path / "invalid.pem"
        key_file.write_text("This is not a valid PEM key")

        is_valid, error = validate_jwt_key(str(key_file), "private")
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_invalid_public_key_format(self, tmp_path):
        """Test invalid public key format."""
        key_file = tmp_path / "invalid.pem"
        key_file.write_text("This is not a valid PEM key")

        is_valid, error = validate_jwt_key(str(key_file), "public")
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_key_with_invalid_base64(self, tmp_path):
        """Test key with invalid base64 content."""
        key_file = tmp_path / "bad.pem"
        key_file.write_text("""-----BEGIN PRIVATE KEY-----
This is not base64!!!
-----END PRIVATE KEY-----""")

        is_valid, error = validate_jwt_key(str(key_file), "private")
        assert is_valid is False
        assert "invalid characters" in error.lower()


class TestEnvFileValidator:
    """Tests for validate_env_file function."""

    def test_valid_env_file(self, tmp_path):
        """Test valid .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""# Comment line
DATABASE_URL=postgresql://localhost/db
API_KEY=secret-key-123
DEBUG=true
""")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is True
        assert error is None

    def test_empty_env_file(self, tmp_path):
        """Test empty .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is True
        assert error is None

    def test_env_file_comments_only(self, tmp_path):
        """Test .env file with only comments."""
        env_file = tmp_path / ".env"
        env_file.write_text("""# Comment 1
# Comment 2
# Comment 3
""")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is True
        assert error is None

    def test_empty_path(self):
        """Test empty path."""
        is_valid, error = validate_env_file("")
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_none_path(self):
        """Test None as path."""
        is_valid, error = validate_env_file(None)
        assert is_valid is False
        assert "cannot be empty" in error.lower()

    def test_file_not_found(self):
        """Test non-existent file."""
        is_valid, error = validate_env_file("/nonexistent/.env")
        assert is_valid is False
        assert "does not exist" in error.lower()

    def test_missing_equals_sign(self, tmp_path):
        """Test .env file with missing = separator."""
        env_file = tmp_path / ".env"
        env_file.write_text("INVALID_LINE")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        assert "missing '=' separator" in error.lower()

    def test_empty_variable_name(self, tmp_path):
        """Test .env file with empty variable name."""
        env_file = tmp_path / ".env"
        env_file.write_text("=value")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        assert "empty variable name" in error.lower()

    def test_invalid_variable_name(self, tmp_path):
        """Test .env file with invalid variable name."""
        env_file = tmp_path / ".env"
        env_file.write_text("invalid-name=value")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        assert "invalid variable name" in error.lower()

    def test_lowercase_variable_name(self, tmp_path):
        """Test .env file with lowercase variable name (should warn)."""
        env_file = tmp_path / ".env"
        env_file.write_text("lowercase=value")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_mixed_case_variable_name(self, tmp_path):
        """Test .env file with mixed case variable name."""
        env_file = tmp_path / ".env"
        env_file.write_text("Mixed_Case=value")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        assert "uppercase" in error.lower()

    def test_env_file_with_whitespace(self, tmp_path):
        """Test .env file with extra whitespace (should be valid)."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
DATABASE_URL = postgresql://localhost/db
  API_KEY=secret-key-123
DEBUG=true
""")

        is_valid, error = validate_env_file(str(env_file))
        # The validator should handle whitespace gracefully
        # Since the key extraction strips whitespace
        assert is_valid is True

    def test_multiple_issues(self, tmp_path):
        """Test .env file with multiple validation issues."""
        env_file = tmp_path / ".env"
        env_file.write_text("""VALID_KEY=value
missing_separator
=empty_key
invalid-key=value
""")

        is_valid, error = validate_env_file(str(env_file))
        assert is_valid is False
        # Should report multiple issues
        assert "line" in error.lower()
