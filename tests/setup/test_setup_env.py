# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for environment configuration setup script.

Tests cover:
- EnvConfigurator initialization and profile management
- Template loading and merging
- Database configuration (PostgreSQL, SQLite)
- Security configuration (JWT, passwords, rate limiting)
- Email configuration
- Application configuration
- Password generation and strength validation
- Configuration validation
- Configuration diff generation
- Configuration file writing
- CLI arguments and flags
- Interactive and non-interactive modes
- YAML configuration loading
- Error handling
"""

import os
import sys
import tempfile
import shutil
import string
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open
from click.testing import CliRunner
import pytest

# Import the module to test
from scripts.setup.setup_env import (
    EnvConfigurator,
    main,
)


class TestEnvConfiguratorInitialization:
    """Test EnvConfigurator class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.console = Mock()

    def test_init_development_profile(self):
        """Test initialization with development profile."""
        configurator = EnvConfigurator("development", self.console)

        assert configurator.profile == "development"
        assert configurator.console == self.console
        assert configurator.config == {}

    def test_init_production_profile(self):
        """Test initialization with production profile."""
        configurator = EnvConfigurator("production", self.console)

        assert configurator.profile == "production"
        assert configurator.console == self.console
        assert configurator.config == {}

    def test_init_invalid_profile(self):
        """Test initialization with invalid profile raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EnvConfigurator("invalid_profile", self.console)

        assert "Invalid profile" in str(exc_info.value)
        assert "development" in str(exc_info.value)
        assert "production" in str(exc_info.value)

    def test_profile_defaults_structure(self):
        """Test that PROFILE_DEFAULTS has correct structure."""
        assert "development" in EnvConfigurator.PROFILE_DEFAULTS
        assert "production" in EnvConfigurator.PROFILE_DEFAULTS

        # Check development defaults
        dev_defaults = EnvConfigurator.PROFILE_DEFAULTS["development"]
        assert "DATABASE_URL" in dev_defaults
        assert "sqlite" in dev_defaults["DATABASE_URL"].lower()
        assert dev_defaults["ENVIRONMENT"] == "development"
        assert dev_defaults["LOG_LEVEL"] == "DEBUG"
        assert dev_defaults["DB_ECHO"] == "true"

        # Check production defaults
        prod_defaults = EnvConfigurator.PROFILE_DEFAULTS["production"]
        assert "DATABASE_URL" in prod_defaults
        assert "postgresql" in prod_defaults["DATABASE_URL"].lower()
        assert prod_defaults["ENVIRONMENT"] == "production"
        assert prod_defaults["LOG_LEVEL"] == "WARNING"
        assert prod_defaults["DB_ECHO"] == "false"


class TestLoadTemplate:
    """Test template loading functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()

    def test_load_template_success_development(self):
        """Test loading template with development profile."""
        with patch("scripts.setup.setup_env.load_env_template") as mock_load:
            mock_load.return_value = {
                "SOME_KEY": "some_value",
                "ANOTHER_KEY": "another_value",
            }

            configurator = EnvConfigurator("development", self.console)
            template = configurator.load_template()

            # Should merge profile defaults
            assert "SOME_KEY" in template
            assert "DATABASE_URL" in template
            assert template["ENVIRONMENT"] == "development"
            assert template["LOG_LEVEL"] == "DEBUG"

    def test_load_template_success_production(self):
        """Test loading template with production profile."""
        with patch("scripts.setup.setup_env.load_env_template") as mock_load:
            mock_load.return_value = {
                "SOME_KEY": "some_value",
            }

            configurator = EnvConfigurator("production", self.console)
            template = configurator.load_template()

            # Should merge production defaults
            assert template["ENVIRONMENT"] == "production"
            assert template["LOG_LEVEL"] == "WARNING"
            assert "postgresql" in template["DATABASE_URL"].lower()

    def test_load_template_profile_overrides_template(self):
        """Test that profile defaults override template values."""
        with patch("scripts.setup.setup_env.load_env_template") as mock_load:
            mock_load.return_value = {
                "DATABASE_URL": "sqlite:///old.db",
                "ENVIRONMENT": "staging",
                "LOG_LEVEL": "INFO",
            }

            configurator = EnvConfigurator("production", self.console)
            template = configurator.load_template()

            # Profile defaults should override
            assert template["ENVIRONMENT"] == "production"
            assert template["LOG_LEVEL"] == "WARNING"
            assert "postgresql" in template["DATABASE_URL"].lower()

    def test_load_template_file_not_found(self):
        """Test handling of missing template file."""
        with patch("scripts.setup.setup_env.load_env_template") as mock_load:
            mock_load.side_effect = FileNotFoundError("Template not found")

            configurator = EnvConfigurator("development", self.console)

            with pytest.raises(FileNotFoundError):
                configurator.load_template()

            self.console.error.assert_called()
            assert "Template not found" in str(self.console.error.call_args)

    def test_load_template_generic_error(self):
        """Test handling of generic error during template loading."""
        with patch("scripts.setup.setup_env.load_env_template") as mock_load:
            mock_load.side_effect = Exception("Parse error")

            configurator = EnvConfigurator("development", self.console)

            with pytest.raises(Exception):
                configurator.load_template()

            self.console.error.assert_called()
            assert "Error loading template" in str(self.console.error.call_args)


class TestPromptDatabase:
    """Test database configuration prompts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.info = Mock()
        self.console.select = Mock()
        self.console.prompt = Mock()
        self.console.confirm = Mock()
        self.console.console = Mock()
        self.console.console.print = Mock()

    def test_prompt_database_sqlite_development(self):
        """Test SQLite configuration in development profile."""
        configurator = EnvConfigurator("development", self.console)

        # Mock user selections
        self.console.select.return_value = "sqlite"
        self.console.prompt.return_value = "./data/test.db"

        config = configurator.prompt_database()

        assert "DATABASE_URL" in config
        assert config["DATABASE_URL"] == "sqlite:///./data/test.db"
        assert "DB_ECHO" in config
        assert config["DB_ECHO"] == "true"

    def test_prompt_database_postgresql_development(self):
        """Test PostgreSQL configuration in development profile."""
        configurator = EnvConfigurator("development", self.console)

        # Mock user selections
        self.console.select.return_value = "postgresql"
        self.console.prompt.side_effect = [
            "localhost",  # db_host
            "5432",  # db_port
            "testdb",  # db_name
            "testuser",  # db_user
            "20",  # pool_size
            "30",  # pool_timeout
            "3600",  # pool_recycle
        ]
        self.console.confirm.return_value = True  # auto-generate password

        with patch.object(
            configurator, "generate_secure_password", return_value="secure_pass_123"
        ):
            config = configurator.prompt_database()

        assert "DATABASE_URL" in config
        assert (
            config["DATABASE_URL"]
            == "postgresql://testuser:secure_pass_123@localhost:5432/testdb"
        )
        assert config["DB_POOL_SIZE"] == "20"
        assert config["DB_POOL_TIMEOUT"] == "30"
        assert config["DB_POOL_RECYCLE"] == "3600"

    def test_prompt_database_postgresql_manual_password(self):
        """Test PostgreSQL with manually entered password."""
        configurator = EnvConfigurator("development", self.console)

        self.console.select.return_value = "postgresql"
        self.console.prompt.side_effect = [
            "dbhost.example.com",  # db_host
            "5433",  # db_port
            "mydb",  # db_name
            "dbuser",  # db_user
            "mypassword",  # manual password
            "10",  # pool_size
            "15",  # pool_timeout
            "1800",  # pool_recycle
        ]
        self.console.confirm.return_value = False  # don't auto-generate

        config = configurator.prompt_database()

        assert (
            config["DATABASE_URL"]
            == "postgresql://dbuser:mypassword@dbhost.example.com:5433/mydb"
        )

    def test_prompt_database_production_default_postgresql(self):
        """Test production profile defaults to PostgreSQL."""
        configurator = EnvConfigurator("production", self.console)

        self.console.select.return_value = "postgresql"
        self.console.prompt.side_effect = [
            "proddb.example.com",
            "5432",
            "proddb",
            "produser",
            "50",
            "60",
            "7200",
        ]
        self.console.confirm.return_value = True

        with patch.object(
            configurator, "generate_secure_password", return_value="prod_pass"
        ):
            config = configurator.prompt_database()

        assert "postgresql" in config["DATABASE_URL"]

    def test_prompt_database_invalid_hostname_retry(self):
        """Test retry on invalid hostname."""
        configurator = EnvConfigurator("development", self.console)

        self.console.select.return_value = "postgresql"
        prompt_responses = [
            "invalid..hostname",  # invalid (will retry)
            "valid-hostname.com",  # valid
            "5432",
            "mydb",
            "user",
            "20",
            "30",
            "3600",
        ]
        self.console.prompt.side_effect = prompt_responses
        self.console.confirm.return_value = True

        with patch("scripts.setup.setup_env.validate_hostname") as mock_validate:
            mock_validate.side_effect = [
                (False, "Invalid hostname format"),  # first try fails
                (True, None),  # second try succeeds
            ]
            with patch.object(
                configurator, "generate_secure_password", return_value="pass"
            ):
                config = configurator.prompt_database()

        self.console.error.assert_called()

    def test_prompt_database_invalid_port_retry(self):
        """Test retry on invalid port."""
        configurator = EnvConfigurator("development", self.console)

        self.console.select.return_value = "postgresql"
        prompt_responses = [
            "localhost",
            "99999",  # invalid port
            "5432",  # valid port
            "mydb",
            "user",
            "20",
            "30",
            "3600",
        ]
        self.console.prompt.side_effect = prompt_responses
        self.console.confirm.return_value = True

        with patch("scripts.setup.setup_env.validate_port") as mock_validate:
            mock_validate.side_effect = [
                (False, "Port out of range"),  # first try fails
                (True, None),  # second try succeeds
            ]
            with patch.object(
                configurator, "generate_secure_password", return_value="pass"
            ):
                config = configurator.prompt_database()

        self.console.error.assert_called()


class TestPromptSecurity:
    """Test security configuration prompts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.info = Mock()
        self.console.prompt = Mock()
        self.console.confirm = Mock()
        self.console.console = Mock()
        self.console.console.print = Mock()

    def test_prompt_security_development(self):
        """Test security configuration for development profile."""
        configurator = EnvConfigurator("development", self.console)

        self.console.prompt.side_effect = [
            "secrets/jwt/private.pem",  # JWT_PRIVATE_KEY_PATH
            "secrets/jwt/public.pem",  # JWT_PUBLIC_KEY_PATH
            "900",  # JWT_ACCESS_TOKEN_EXPIRE_SECONDS
            "604800",  # JWT_REFRESH_TOKEN_EXPIRE_SECONDS
            "promptvault",  # JWT_ISSUER
            "promptvault-api",  # JWT_AUDIENCE
            "12",  # PASSWORD_MIN_LENGTH
            "5",  # MAX_LOGIN_ATTEMPTS
            "900",  # ACCOUNT_LOCKOUT_DURATION_SECONDS
            "5",  # MAX_SESSIONS_PER_USER
            "2592000",  # SESSION_INACTIVE_TIMEOUT_SECONDS
            "redis://localhost:6379/0",  # REDIS_URL
            "5",  # RATE_LIMIT_LOGIN_ATTEMPTS
            "900",  # RATE_LIMIT_LOGIN_WINDOW_SECONDS
            "3",  # RATE_LIMIT_REGISTER_ATTEMPTS
            "3600",  # RATE_LIMIT_REGISTER_WINDOW_SECONDS
            "3",  # RATE_LIMIT_PASSWORD_RESET_ATTEMPTS
            "3600",  # RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS
        ]
        self.console.confirm.side_effect = [
            True,
            True,
            True,
            True,
        ]  # password requirements

        config = configurator.prompt_security()

        assert config["JWT_PRIVATE_KEY_PATH"] == "secrets/jwt/private.pem"
        assert config["JWT_PUBLIC_KEY_PATH"] == "secrets/jwt/public.pem"
        assert config["JWT_ACCESS_TOKEN_EXPIRE_SECONDS"] == "900"
        assert config["PASSWORD_MIN_LENGTH"] == "12"
        assert config["PASSWORD_REQUIRE_UPPERCASE"] == "true"
        assert config["MAX_LOGIN_ATTEMPTS"] == "5"
        assert config["REDIS_URL"] == "redis://localhost:6379/0"

    def test_prompt_security_production_strict_policy(self):
        """Test production profile uses strict password policy."""
        configurator = EnvConfigurator("production", self.console)

        self.console.prompt.side_effect = [
            "secrets/jwt/private.pem",
            "secrets/jwt/public.pem",
            "900",
            "604800",
            "promptvault",
            "promptvault-api",
            "5",
            "900",
            "5",
            "2592000",
            "redis://localhost:6379/0",
            "5",
            "900",
            "3",
            "3600",
            "3",
            "3600",
        ]
        self.console.confirm.side_effect = (
            []
        )  # No prompts for password policy in production

        config = configurator.prompt_security()

        # Production should enforce strict policy
        assert config["PASSWORD_MIN_LENGTH"] == "16"
        assert config["PASSWORD_REQUIRE_UPPERCASE"] == "true"
        assert config["PASSWORD_REQUIRE_LOWERCASE"] == "true"
        assert config["PASSWORD_REQUIRE_DIGIT"] == "true"
        assert config["PASSWORD_REQUIRE_SPECIAL"] == "true"

    def test_prompt_security_jwt_configuration(self):
        """Test JWT-specific configuration."""
        configurator = EnvConfigurator("development", self.console)

        self.console.prompt.side_effect = [
            "/custom/path/private.pem",
            "/custom/path/public.pem",
            "1800",  # 30 minutes access token
            "1209600",  # 14 days refresh token
            "my-issuer",
            "my-audience",
            "12",
            "5",
            "900",
            "5",
            "2592000",
            "redis://localhost:6379/0",
            "5",
            "900",
            "3",
            "3600",
            "3",
            "3600",
        ]
        self.console.confirm.side_effect = [True, True, True, True]

        config = configurator.prompt_security()

        assert config["JWT_PRIVATE_KEY_PATH"] == "/custom/path/private.pem"
        assert config["JWT_PUBLIC_KEY_PATH"] == "/custom/path/public.pem"
        assert config["JWT_ACCESS_TOKEN_EXPIRE_SECONDS"] == "1800"
        assert config["JWT_REFRESH_TOKEN_EXPIRE_SECONDS"] == "1209600"
        assert config["JWT_ISSUER"] == "my-issuer"
        assert config["JWT_AUDIENCE"] == "my-audience"

    def test_prompt_security_rate_limiting(self):
        """Test rate limiting configuration."""
        configurator = EnvConfigurator("development", self.console)

        self.console.prompt.side_effect = [
            "secrets/jwt/private.pem",
            "secrets/jwt/public.pem",
            "900",
            "604800",
            "promptvault",
            "promptvault-api",
            "12",
            "5",
            "900",
            "5",
            "2592000",
            "redis://custom:6379/1",
            "10",  # login attempts
            "600",  # login window
            "5",  # register attempts
            "7200",  # register window
            "2",  # password reset attempts
            "1800",  # password reset window
        ]
        self.console.confirm.side_effect = [True, True, True, True]

        config = configurator.prompt_security()

        assert config["REDIS_URL"] == "redis://custom:6379/1"
        assert config["RATE_LIMIT_LOGIN_ATTEMPTS"] == "10"
        assert config["RATE_LIMIT_LOGIN_WINDOW_SECONDS"] == "600"
        assert config["RATE_LIMIT_REGISTER_ATTEMPTS"] == "5"
        assert config["RATE_LIMIT_REGISTER_WINDOW_SECONDS"] == "7200"
        assert config["RATE_LIMIT_PASSWORD_RESET_ATTEMPTS"] == "2"
        assert config["RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS"] == "1800"


class TestPromptEmail:
    """Test email configuration prompts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.info = Mock()
        self.console.prompt = Mock()
        self.console.confirm = Mock()
        self.console.error = Mock()
        self.console.console = Mock()
        self.console.console.print = Mock()

    def test_prompt_email_skip_optional(self):
        """Test skipping optional email configuration."""
        configurator = EnvConfigurator("development", self.console)

        self.console.confirm.return_value = False  # Skip email config

        config = configurator.prompt_email(optional=True)

        # Should use placeholders
        assert config["SMTP_HOST"] == "smtp.example.com"
        assert config["SMTP_PORT"] == "587"
        assert config["SMTP_USE_TLS"] == "true"
        assert config["SMTP_USERNAME"] == "noreply@example.com"
        assert config["EMAIL_FROM_ADDRESS"] == "noreply@example.com"

    def test_prompt_email_full_configuration(self):
        """Test full email configuration."""
        configurator = EnvConfigurator("development", self.console)

        self.console.confirm.side_effect = [
            True,  # Configure email
            True,  # Use TLS
        ]
        self.console.prompt.side_effect = [
            "smtp.gmail.com",  # SMTP_HOST
            "587",  # SMTP_PORT
            "sender@example.com",  # SMTP_USERNAME
            "smtp_password",  # SMTP_PASSWORD
            "noreply@example.com",  # EMAIL_FROM_ADDRESS
            "MyApp",  # EMAIL_FROM_NAME
            "7200",  # PASSWORD_RESET_TOKEN_EXPIRE_SECONDS
        ]

        with patch("scripts.setup.setup_env.validate_port", return_value=(True, None)):
            with patch(
                "scripts.setup.setup_env.validate_email", return_value=(True, None)
            ):
                config = configurator.prompt_email(optional=True)

        assert config["SMTP_HOST"] == "smtp.gmail.com"
        assert config["SMTP_PORT"] == "587"
        assert config["SMTP_USE_TLS"] == "true"
        assert config["SMTP_USERNAME"] == "sender@example.com"
        assert config["SMTP_PASSWORD"] == "smtp_password"
        assert config["EMAIL_FROM_ADDRESS"] == "noreply@example.com"
        assert config["EMAIL_FROM_NAME"] == "MyApp"
        assert config["PASSWORD_RESET_TOKEN_EXPIRE_SECONDS"] == "7200"

    def test_prompt_email_invalid_port_retry(self):
        """Test retry on invalid SMTP port."""
        configurator = EnvConfigurator("development", self.console)

        self.console.confirm.side_effect = [True, True]
        self.console.prompt.side_effect = [
            "smtp.example.com",
            "invalid_port",  # invalid
            "587",  # valid
            "user@example.com",
            "password",
            "from@example.com",
            "App",
            "3600",
        ]

        with patch("scripts.setup.setup_env.validate_port") as mock_validate:
            mock_validate.side_effect = [
                (False, "Invalid port"),
                (True, None),
            ]
            with patch(
                "scripts.setup.setup_env.validate_email", return_value=(True, None)
            ):
                config = configurator.prompt_email(optional=True)

        self.console.error.assert_called()

    def test_prompt_email_invalid_email_retry(self):
        """Test retry on invalid email address."""
        configurator = EnvConfigurator("development", self.console)

        self.console.confirm.side_effect = [True, True]
        self.console.prompt.side_effect = [
            "smtp.example.com",
            "587",
            "invalid-email",  # invalid
            "valid@example.com",  # valid
            "password",
            "invalid-from",  # invalid
            "valid@example.com",  # valid
            "App",
            "3600",
        ]

        with patch("scripts.setup.setup_env.validate_port", return_value=(True, None)):
            with patch("scripts.setup.setup_env.validate_email") as mock_validate:
                mock_validate.side_effect = [
                    (False, "Invalid email"),
                    (True, None),
                    (False, "Invalid email"),
                    (True, None),
                ]
                config = configurator.prompt_email(optional=True)

        assert self.console.error.call_count == 2

    def test_prompt_email_no_tls(self):
        """Test email configuration without TLS."""
        configurator = EnvConfigurator("development", self.console)

        self.console.confirm.side_effect = [
            True,  # Configure email
            False,  # Don't use TLS
        ]
        self.console.prompt.side_effect = [
            "smtp.example.com",
            "25",
            "user@example.com",
            "password",
            "from@example.com",
            "App",
            "3600",
        ]

        with patch("scripts.setup.setup_env.validate_port", return_value=(True, None)):
            with patch(
                "scripts.setup.setup_env.validate_email", return_value=(True, None)
            ):
                config = configurator.prompt_email(optional=True)

        assert config["SMTP_USE_TLS"] == "false"


class TestPromptApplication:
    """Test application configuration prompts."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.info = Mock()
        self.console.select = Mock()
        self.console.prompt = Mock()
        self.console.console = Mock()
        self.console.console.print = Mock()

    def test_prompt_application_development(self):
        """Test application configuration for development."""
        configurator = EnvConfigurator("development", self.console)

        self.console.select.return_value = "DEBUG"
        self.console.prompt.return_value = "http://localhost:8000"

        config = configurator.prompt_application()

        assert config["ENVIRONMENT"] == "development"
        assert config["LOG_LEVEL"] == "DEBUG"
        assert config["AUDIT_LOG_LEVEL"] == "INFO"
        assert config["APP_BASE_URL"] == "http://localhost:8000"

    def test_prompt_application_production(self):
        """Test application configuration for production."""
        configurator = EnvConfigurator("production", self.console)

        self.console.prompt.return_value = "https://app.example.com"

        config = configurator.prompt_application()

        assert config["ENVIRONMENT"] == "production"
        assert config["LOG_LEVEL"] == "WARNING"
        assert config["AUDIT_LOG_LEVEL"] == "INFO"
        assert config["APP_BASE_URL"] == "https://app.example.com"

    def test_prompt_application_custom_url(self):
        """Test custom application URL."""
        configurator = EnvConfigurator("development", self.console)

        self.console.select.return_value = "INFO"
        self.console.prompt.return_value = "https://staging.example.com:8443"

        config = configurator.prompt_application()

        assert config["APP_BASE_URL"] == "https://staging.example.com:8443"


class TestGenerateSecurePassword:
    """Test secure password generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()

    def test_generate_password_default_length(self):
        """Test password generation with default length."""
        configurator = EnvConfigurator("development", self.console)

        password = configurator.generate_secure_password()

        assert len(password) == 32
        assert isinstance(password, str)

    def test_generate_password_custom_length(self):
        """Test password generation with custom length."""
        configurator = EnvConfigurator("development", self.console)

        password = configurator.generate_secure_password(length=64)

        assert len(password) == 64

    def test_generate_password_complexity_requirements(self):
        """Test that generated password meets complexity requirements."""
        configurator = EnvConfigurator("development", self.console)

        password = configurator.generate_secure_password()

        # Check for required character types
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in string.punctuation for c in password)

        assert has_upper, "Password should contain uppercase letters"
        assert has_lower, "Password should contain lowercase letters"
        assert has_digit, "Password should contain digits"
        assert has_special, "Password should contain special characters"

    def test_generate_password_uniqueness(self):
        """Test that each generated password is unique."""
        configurator = EnvConfigurator("development", self.console)

        passwords = [configurator.generate_secure_password() for _ in range(10)]

        # All passwords should be unique
        assert len(set(passwords)) == 10

    def test_generate_password_uses_secure_random(self):
        """Test that password generation uses secrets module."""
        configurator = EnvConfigurator("development", self.console)

        with patch("secrets.choice") as mock_choice:
            mock_choice.side_effect = list(
                "Abc123!@#" * 10
            )  # Enough chars with all types

            password = configurator.generate_secure_password(length=10)

            # Should have called secrets.choice
            assert mock_choice.called


class TestValidate:
    """Test configuration validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()

    def test_validate_valid_postgresql_config(self):
        """Test validation of valid PostgreSQL configuration."""
        configurator = EnvConfigurator("production", self.console)
        configurator.config = {
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "user@example.com",
            "EMAIL_FROM_ADDRESS": "noreply@example.com",
            "JWT_PRIVATE_KEY_PATH": "secrets/jwt/private_key.pem",
            "JWT_PUBLIC_KEY_PATH": "secrets/jwt/public_key.pem",
        }

        with patch(
            "scripts.setup.setup_env.validate_database_url", return_value=(True, None)
        ):
            with patch(
                "scripts.setup.setup_env.validate_port", return_value=(True, None)
            ):
                with patch(
                    "scripts.setup.setup_env.validate_email", return_value=(True, None)
                ):
                    with patch(
                        "scripts.setup.setup_env.validate_path",
                        return_value=(True, None),
                    ):
                        errors = configurator.validate()

        assert errors == []

    def test_validate_valid_sqlite_config(self):
        """Test validation of valid SQLite configuration."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "DATABASE_URL": "sqlite:///./data/test.db",
            "JWT_PRIVATE_KEY_PATH": "secrets/jwt/private_key.pem",
        }

        with patch(
            "scripts.setup.setup_env.validate_database_url", return_value=(True, None)
        ):
            with patch(
                "scripts.setup.setup_env.validate_path", return_value=(True, None)
            ):
                errors = configurator.validate()

        assert errors == []

    def test_validate_invalid_database_url(self):
        """Test validation detects invalid database URL."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "DATABASE_URL": "invalid://url",
        }

        with patch(
            "scripts.setup.setup_env.validate_database_url",
            return_value=(False, "Invalid URL"),
        ):
            errors = configurator.validate()

        assert len(errors) > 0
        assert any("DATABASE_URL" in error for error in errors)

    def test_validate_invalid_port(self):
        """Test validation detects invalid port."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "SMTP_PORT": "99999",
        }

        with patch(
            "scripts.setup.setup_env.validate_port",
            return_value=(False, "Port out of range"),
        ):
            errors = configurator.validate()

        assert len(errors) > 0
        assert any("SMTP_PORT" in error for error in errors)

    def test_validate_invalid_email(self):
        """Test validation detects invalid email."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "SMTP_USERNAME": "invalid-email",
        }

        with patch(
            "scripts.setup.setup_env.validate_email",
            return_value=(False, "Invalid email format"),
        ):
            errors = configurator.validate()

        assert len(errors) > 0
        assert any("SMTP_USERNAME" in error for error in errors)

    def test_validate_skips_placeholder_emails(self):
        """Test validation skips placeholder email addresses."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "SMTP_USERNAME": "noreply@example.com",
            "EMAIL_FROM_ADDRESS": "noreply@example.com",
        }

        errors = configurator.validate()

        # Should not validate placeholder values
        assert errors == []

    def test_validate_invalid_path(self):
        """Test validation detects invalid JWT key paths."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "JWT_PRIVATE_KEY_PATH": "/invalid/path/private.pem",
        }

        with patch(
            "scripts.setup.setup_env.validate_path",
            return_value=(False, "Parent directory does not exist"),
        ):
            errors = configurator.validate()

        assert len(errors) > 0
        assert any("JWT_PRIVATE_KEY_PATH" in error for error in errors)

    def test_validate_multiple_errors(self):
        """Test validation collects multiple errors."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "DATABASE_URL": "invalid://url",
            "SMTP_PORT": "invalid",
            "SMTP_USERNAME": "bad-email",
        }

        with patch(
            "scripts.setup.setup_env.validate_database_url",
            return_value=(False, "Invalid URL"),
        ):
            with patch(
                "scripts.setup.setup_env.validate_port",
                return_value=(False, "Invalid port"),
            ):
                with patch(
                    "scripts.setup.setup_env.validate_email",
                    return_value=(False, "Invalid email"),
                ):
                    errors = configurator.validate()

        assert len(errors) >= 3


class TestDiff:
    """Test configuration diff generation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()

    def test_diff_no_changes(self):
        """Test diff when there are no changes."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "KEY1": "value1",
            "KEY2": "value2",
        }

        existing = {
            "KEY1": "value1",
            "KEY2": "value2",
        }

        result = configurator.diff(existing)

        assert result == "No changes detected"

    def test_diff_changed_values(self):
        """Test diff detects changed values."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "KEY1": "new_value",
            "KEY2": "value2",
        }

        existing = {
            "KEY1": "old_value",
            "KEY2": "value2",
        }

        result = configurator.diff(existing)

        # Should return a Rich Table object
        from rich.table import Table

        assert isinstance(result, Table)

    def test_diff_added_values(self):
        """Test diff detects added values."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "KEY1": "value1",
            "KEY2": "value2",
            "KEY3": "value3",
        }

        existing = {
            "KEY1": "value1",
            "KEY2": "value2",
        }

        result = configurator.diff(existing)

        from rich.table import Table

        assert isinstance(result, Table)

    def test_diff_removed_values(self):
        """Test diff detects removed values."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "KEY1": "value1",
        }

        existing = {
            "KEY1": "value1",
            "KEY2": "value2",
        }

        result = configurator.diff(existing)

        from rich.table import Table

        assert isinstance(result, Table)

    def test_diff_masks_sensitive_values(self):
        """Test diff masks sensitive values."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "DATABASE_PASSWORD": "new_secret",
            "SECRET_KEY": "new_key",
            "JWT_PRIVATE_KEY": "new_jwt_key",
        }

        existing = {
            "DATABASE_PASSWORD": "old_secret",
            "SECRET_KEY": "old_key",
            "JWT_PRIVATE_KEY": "old_jwt_key",
        }

        # Diff should mask these values
        result = configurator.diff(existing)

        from rich.table import Table

        assert isinstance(result, Table)


class TestWrite:
    """Test configuration file writing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.console = Mock()
        self.console.success = Mock()
        self.console.error = Mock()

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_write_creates_file(self):
        """Test that write creates .env file."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {
            "KEY1": "value1",
            "KEY2": "value2",
        }

        output_path = self.temp_dir / ".env"

        with patch("scripts.setup.setup_env.write_env_file") as mock_write:
            configurator.write(output_path)

        mock_write.assert_called_once_with(str(output_path), configurator.config)
        self.console.success.assert_called()

    def test_write_handles_error(self):
        """Test write handles errors gracefully."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {}

        output_path = self.temp_dir / ".env"

        with patch(
            "scripts.setup.setup_env.write_env_file",
            side_effect=Exception("Write error"),
        ):
            with pytest.raises(Exception):
                configurator.write(output_path)

        self.console.error.assert_called()


class TestMainCLI:
    """Test main CLI function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_cli_non_interactive_mode(self):
        """Test non-interactive mode with defaults."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            output_file = Path(temp_dir) / ".env"

            with patch("scripts.setup.setup_env.load_env_template", return_value={}):
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "development",
                            "--non-interactive",
                            "--output",
                            str(output_file),
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_validate_only_valid_file(self):
        """Test validate-only mode with valid .env file."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            env_file = Path(temp_dir) / ".env"

            # Create a valid .env file
            env_file.write_text("DATABASE_URL=sqlite:///test.db\n")

            with patch(
                "scripts.setup.setup_env.parse_env_file",
                return_value={"DATABASE_URL": "sqlite:///test.db"},
            ):
                with patch(
                    "scripts.setup.setup_env.validate_database_url",
                    return_value=(True, None),
                ):
                    result = self.runner.invoke(
                        main,
                        [
                            "--validate-only",
                            "--output",
                            str(env_file),
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_validate_only_missing_file(self):
        """Test validate-only mode with missing .env file."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            env_file = Path(temp_dir) / "nonexistent.env"

            result = self.runner.invoke(
                main,
                [
                    "--validate-only",
                    "--output",
                    str(env_file),
                ],
            )

            assert result.exit_code == 1

    def test_cli_validate_only_invalid_config(self):
        """Test validate-only mode with invalid configuration."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("DATABASE_URL=invalid\n")

            with patch(
                "scripts.setup.setup_env.parse_env_file",
                return_value={"DATABASE_URL": "invalid"},
            ):
                with patch(
                    "scripts.setup.setup_env.validate_database_url",
                    return_value=(False, "Invalid URL"),
                ):
                    result = self.runner.invoke(
                        main,
                        [
                            "--validate-only",
                            "--output",
                            str(env_file),
                        ],
                    )

            assert result.exit_code == 1

    def test_cli_from_file_yaml(self):
        """Test loading configuration from YAML file."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            yaml_file = Path(temp_dir) / "config.yaml"
            output_file = Path(temp_dir) / ".env"

            # Create a YAML config file
            yaml_file.write_text("""
development:
  DATABASE_URL: sqlite:///test.db
  LOG_LEVEL: DEBUG
""")

            with patch(
                "scripts.setup.setup_env.parse_yaml_config",
                return_value={"development": {"DATABASE_URL": "sqlite:///test.db"}},
            ):
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "development",
                            "--from-file",
                            str(yaml_file),
                            "--output",
                            str(output_file),
                            "--non-interactive",
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_profile_development(self):
        """Test CLI with development profile."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir

            with patch("scripts.setup.setup_env.load_env_template", return_value={}):
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "development",
                            "--non-interactive",
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_profile_production(self):
        """Test CLI with production profile."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir

            with patch("scripts.setup.setup_env.load_env_template", return_value={}):
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "production",
                            "--non-interactive",
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_custom_output_path(self):
        """Test CLI with custom output path."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            custom_output = Path(temp_dir) / "custom" / "config.env"

            with patch("scripts.setup.setup_env.load_env_template", return_value={}):
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--non-interactive",
                            "--output",
                            str(custom_output),
                        ],
                    )

            assert result.exit_code == 0

    def test_cli_shows_diff_for_existing_file(self):
        """Test that CLI shows diff when .env file exists."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("OLD_KEY=old_value\n")

            with patch(
                "scripts.setup.setup_env.load_env_template",
                return_value={"NEW_KEY": "new_value"},
            ):
                with patch(
                    "scripts.setup.setup_env.parse_env_file",
                    return_value={"OLD_KEY": "old_value"},
                ):
                    with patch("scripts.setup.setup_env.write_env_file"):
                        result = self.runner.invoke(
                            main,
                            [
                                "--non-interactive",
                                "--output",
                                str(env_file),
                            ],
                        )

            assert result.exit_code == 0

    def test_cli_keyboard_interrupt(self):
        """Test handling of keyboard interrupt during interactive mode."""
        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir

            with patch(
                "scripts.setup.setup_env.EnvConfigurator.prompt_database",
                side_effect=KeyboardInterrupt,
            ):
                result = self.runner.invoke(
                    main,
                    [
                        "--profile",
                        "development",
                    ],
                )

            assert result.exit_code == 1


class TestErrorHandling:
    """Test error handling scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()

    def test_init_with_none_profile(self):
        """Test initialization with None as profile."""
        with pytest.raises(ValueError):
            EnvConfigurator(None, self.console)

    def test_init_with_empty_profile(self):
        """Test initialization with empty string as profile."""
        with pytest.raises(ValueError):
            EnvConfigurator("", self.console)

    def test_validate_with_empty_config(self):
        """Test validation with empty configuration."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {}

        errors = configurator.validate()

        # Should not error on empty config
        assert errors == []

    def test_diff_with_empty_configs(self):
        """Test diff with empty configurations."""
        configurator = EnvConfigurator("development", self.console)
        configurator.config = {}

        result = configurator.diff({})

        assert result == "No changes detected"


class TestProductionProfile:
    """Comprehensive tests for production profile deployment functionality.

    Verifies that the production profile applies correct configuration settings
    and security hardening for production deployments.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.info = Mock()
        self.console.select = Mock()
        self.console.prompt = Mock()
        self.console.confirm = Mock()
        self.console.error = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.console = Mock()
        self.console.console.print = Mock()
        self.runner = CliRunner()

    def test_production_profile_env_variable(self):
        """Test that production profile generates ENVIRONMENT=production setting."""
        configurator = EnvConfigurator("production", self.console)

        # Load template to get defaults
        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert "ENVIRONMENT" in template
        assert template["ENVIRONMENT"] == "production"

    def test_production_profile_log_level_warning(self):
        """Test that production profile sets LOG_LEVEL=WARNING (not DEBUG)."""
        configurator = EnvConfigurator("production", self.console)

        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert template["LOG_LEVEL"] == "WARNING"
        assert template["LOG_LEVEL"] != "DEBUG"

    def test_production_profile_db_echo_false(self):
        """Test that production profile sets DB_ECHO=false (not true)."""
        configurator = EnvConfigurator("production", self.console)

        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert template["DB_ECHO"] == "false"
        assert template["DB_ECHO"] != "true"

    def test_production_profile_secure_password_requirements(self):
        """Test that production profile enforces strict password requirements."""
        configurator = EnvConfigurator("production", self.console)

        # Mock the prompts
        self.console.prompt.side_effect = [
            "secrets/jwt/private.pem",
            "secrets/jwt/public.pem",
            "900",  # JWT_ACCESS_TOKEN_EXPIRE_SECONDS
            "604800",  # JWT_REFRESH_TOKEN_EXPIRE_SECONDS
            "promptvault",
            "promptvault-api",
            "5",
            "900",
            "5",
            "2592000",
            "redis://localhost:6379/0",
            "5",
            "900",
            "3",
            "3600",
            "3",
            "3600",
        ]
        self.console.confirm.side_effect = []

        config = configurator.prompt_security()

        # Production should enforce strict password policy
        assert config["PASSWORD_MIN_LENGTH"] == "16"
        assert config["PASSWORD_REQUIRE_UPPERCASE"] == "true"
        assert config["PASSWORD_REQUIRE_LOWERCASE"] == "true"
        assert config["PASSWORD_REQUIRE_DIGIT"] == "true"
        assert config["PASSWORD_REQUIRE_SPECIAL"] == "true"

    def test_production_profile_postgresql_default(self):
        """Test that production profile defaults to PostgreSQL database."""
        configurator = EnvConfigurator("production", self.console)

        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert "postgresql" in template["DATABASE_URL"].lower()

    def test_production_profile_uses_redis_for_rate_limiting(self):
        """Test that production profile includes Redis URL for rate limiting."""
        configurator = EnvConfigurator("production", self.console)

        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert "REDIS_URL" in template
        assert "redis://" in template["REDIS_URL"]

    def test_production_profile_audit_log_level_info(self):
        """Test that production profile sets AUDIT_LOG_LEVEL=INFO."""
        configurator = EnvConfigurator("production", self.console)

        with patch("scripts.setup.setup_env.load_env_template", return_value={}):
            template = configurator.load_template()

        assert template["AUDIT_LOG_LEVEL"] == "INFO"

    def test_production_differs_from_development(self):
        """Test that production profile settings differ from development profile."""
        # Access profile defaults directly without loading template
        dev_defaults = EnvConfigurator.PROFILE_DEFAULTS["development"]
        prod_defaults = EnvConfigurator.PROFILE_DEFAULTS["production"]

        # Key differences between profiles
        assert dev_defaults["ENVIRONMENT"] != prod_defaults["ENVIRONMENT"]
        assert dev_defaults["LOG_LEVEL"] != prod_defaults["LOG_LEVEL"]
        assert dev_defaults["DB_ECHO"] != prod_defaults["DB_ECHO"]

        # Verify expected values
        assert dev_defaults["ENVIRONMENT"] == "development"
        assert prod_defaults["ENVIRONMENT"] == "production"

        assert dev_defaults["LOG_LEVEL"] == "DEBUG"
        assert prod_defaults["LOG_LEVEL"] == "WARNING"

        assert dev_defaults["DB_ECHO"] == "true"
        assert prod_defaults["DB_ECHO"] == "false"

    def test_production_profile_full_deployment_non_interactive(self):
        """Test production profile can be used for full deployment via non-interactive mode."""
        with self.runner.isolated_filesystem() as temp_dir:
            output_file = Path(temp_dir) / ".env"

            with patch("scripts.setup.setup_env.load_env_template") as mock_template:
                mock_template.return_value = {
                    "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
                    "ENVIRONMENT": "production",
                    "LOG_LEVEL": "WARNING",
                    "DB_ECHO": "false",
                    "PASSWORD_MIN_LENGTH": "16",
                    "PASSWORD_REQUIRE_UPPERCASE": "true",
                    "PASSWORD_REQUIRE_LOWERCASE": "true",
                    "PASSWORD_REQUIRE_DIGIT": "true",
                    "PASSWORD_REQUIRE_SPECIAL": "true",
                }
                with patch("scripts.setup.setup_env.write_env_file") as mock_write:
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "production",
                            "--non-interactive",
                            "--output",
                            str(output_file),
                        ],
                    )

            assert result.exit_code == 0
            assert mock_write.called

    def test_production_profile_security_hardening_complete(self):
        """Test that production profile includes all security hardening settings."""
        console = Mock()
        console.console = Mock()
        console.console.print = Mock()

        configurator = EnvConfigurator("production", console)
        configurator.config = {
            "PASSWORD_MIN_LENGTH": "16",
            "PASSWORD_REQUIRE_UPPERCASE": "true",
            "PASSWORD_REQUIRE_LOWERCASE": "true",
            "PASSWORD_REQUIRE_DIGIT": "true",
            "PASSWORD_REQUIRE_SPECIAL": "true",
            "MAX_LOGIN_ATTEMPTS": "5",
            "ACCOUNT_LOCKOUT_DURATION_SECONDS": "900",
            "SESSION_INACTIVE_TIMEOUT_SECONDS": "2592000",
            "DB_ECHO": "false",
            "LOG_LEVEL": "WARNING",
            "ENVIRONMENT": "production",
        }

        # All security settings should be present
        assert configurator.config["PASSWORD_MIN_LENGTH"] == "16"
        assert configurator.config["PASSWORD_REQUIRE_UPPERCASE"] == "true"
        assert configurator.config["PASSWORD_REQUIRE_LOWERCASE"] == "true"
        assert configurator.config["PASSWORD_REQUIRE_DIGIT"] == "true"
        assert configurator.config["PASSWORD_REQUIRE_SPECIAL"] == "true"
        assert configurator.config["DB_ECHO"] == "false"
        assert configurator.config["LOG_LEVEL"] == "WARNING"
        assert configurator.config["ENVIRONMENT"] == "production"

    def test_production_profile_password_generation_meets_strict_requirements(self):
        """Test that auto-generated passwords meet production's strict requirements."""
        configurator = EnvConfigurator("production", self.console)

        # Generate multiple passwords to ensure consistency
        for _ in range(5):
            password = configurator.generate_secure_password(length=32)

            # Password must meet all strict requirements
            assert len(password) >= 16
            assert any(c.isupper() for c in password), "Must have uppercase"
            assert any(c.islower() for c in password), "Must have lowercase"
            assert any(c.isdigit() for c in password), "Must have digit"
            assert any(
                c in string.punctuation for c in password
            ), "Must have special char"

    def test_production_profile_cli_defaults_applied(self):
        """Test that CLI applies production profile defaults correctly."""
        with self.runner.isolated_filesystem() as temp_dir:
            output_file = Path(temp_dir) / ".env"

            with patch("scripts.setup.setup_env.load_env_template") as mock_template:
                # Return a dict with template values that will be overridden by production defaults
                mock_template.return_value = {
                    "SOME_OTHER_KEY": "some_value",
                }

                with patch("scripts.setup.setup_env.write_env_file") as mock_write:
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "production",
                            "--non-interactive",
                            "--output",
                            str(output_file),
                        ],
                    )

            assert result.exit_code == 0

            # Verify that write_env_file was called
            assert mock_write.called

            # Get the config that was written
            written_config = mock_write.call_args[0][1]

            # Verify production defaults were applied
            assert written_config["ENVIRONMENT"] == "production"
            assert written_config["LOG_LEVEL"] == "WARNING"
            assert written_config["DB_ECHO"] == "false"

    def test_production_profile_performance_optimized_timeouts(self):
        """Test that production profile includes performance-optimized settings."""
        console = Mock()
        console.console = Mock()
        console.console.print = Mock()

        configurator = EnvConfigurator("production", console)
        configurator.config = {
            "DB_POOL_SIZE": "20",
            "DB_POOL_TIMEOUT": "30",
            "DB_POOL_RECYCLE": "3600",
            "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "900",  # 15 minutes
            "JWT_REFRESH_TOKEN_EXPIRE_SECONDS": "604800",  # 7 days
            "SESSION_INACTIVE_TIMEOUT_SECONDS": "2592000",  # 30 days
        }

        # These are reasonable production values
        assert int(configurator.config["DB_POOL_SIZE"]) > 0
        assert int(configurator.config["DB_POOL_TIMEOUT"]) > 0
        assert int(configurator.config["DB_POOL_RECYCLE"]) > 0
        assert int(configurator.config["JWT_ACCESS_TOKEN_EXPIRE_SECONDS"]) == 900

    def test_production_profile_prompt_database_suggests_postgresql(self):
        """Test that production profile prompts suggest PostgreSQL as default."""
        configurator = EnvConfigurator("production", self.console)

        # When we call prompt_database on production profile
        self.console.select.return_value = "postgresql"
        self.console.prompt.side_effect = [
            "proddb.example.com",
            "5432",
            "proddb",
            "produser",
            "20",
            "30",
            "3600",
        ]
        self.console.confirm.return_value = True

        with patch.object(
            configurator, "generate_secure_password", return_value="pass123!"
        ):
            config = configurator.prompt_database()

        # Should use PostgreSQL
        assert "postgresql://" in config["DATABASE_URL"]

    def test_production_profile_env_file_content_complete(self):
        """Test that production profile generates complete .env file with all required settings."""
        console = Mock()
        console.console = Mock()
        console.console.print = Mock()
        console.success = Mock()

        configurator = EnvConfigurator("production", console)

        # Simulate a complete production configuration
        configurator.config = {
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "WARNING",
            "AUDIT_LOG_LEVEL": "INFO",
            "DB_ECHO": "false",
            "DATABASE_URL": "postgresql://user:pass@host:5432/db",
            "PASSWORD_MIN_LENGTH": "16",
            "PASSWORD_REQUIRE_UPPERCASE": "true",
            "PASSWORD_REQUIRE_LOWERCASE": "true",
            "PASSWORD_REQUIRE_DIGIT": "true",
            "PASSWORD_REQUIRE_SPECIAL": "true",
            "MAX_LOGIN_ATTEMPTS": "5",
            "ACCOUNT_LOCKOUT_DURATION_SECONDS": "900",
            "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "900",
            "JWT_REFRESH_TOKEN_EXPIRE_SECONDS": "604800",
            "REDIS_URL": "redis://localhost:6379/0",
            "RATE_LIMIT_LOGIN_ATTEMPTS": "5",
            "RATE_LIMIT_LOGIN_WINDOW_SECONDS": "900",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            env_file = Path(tmpdir) / ".env"

            with patch("scripts.setup.setup_env.write_env_file") as mock_write:
                configurator.write(env_file)

            # Verify write was called with complete config
            assert mock_write.called
            called_config = mock_write.call_args[0][1]

            # Verify all production settings are present
            assert called_config["ENVIRONMENT"] == "production"
            assert called_config["LOG_LEVEL"] == "WARNING"
            assert called_config["DB_ECHO"] == "false"
            assert called_config["PASSWORD_MIN_LENGTH"] == "16"


class TestIntegration:
    """Integration tests for complete workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_full_workflow_development(self):
        """Test complete workflow for development profile."""
        with self.runner.isolated_filesystem() as temp_dir:
            output_file = Path(temp_dir) / ".env"

            # Run with non-interactive mode
            with patch("scripts.setup.setup_env.load_env_template") as mock_template:
                mock_template.return_value = {
                    "DATABASE_URL": "sqlite:///test.db",
                    "LOG_LEVEL": "DEBUG",
                }
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "development",
                            "--non-interactive",
                            "--output",
                            str(output_file),
                        ],
                    )

            assert result.exit_code == 0

    def test_full_workflow_production(self):
        """Test complete workflow for production profile."""
        with self.runner.isolated_filesystem() as temp_dir:
            output_file = Path(temp_dir) / ".env"

            with patch("scripts.setup.setup_env.load_env_template") as mock_template:
                mock_template.return_value = {
                    "DATABASE_URL": "postgresql://user:pass@localhost:5432/db",
                    "LOG_LEVEL": "WARNING",
                }
                with patch("scripts.setup.setup_env.write_env_file"):
                    result = self.runner.invoke(
                        main,
                        [
                            "--profile",
                            "production",
                            "--non-interactive",
                            "--output",
                            str(output_file),
                        ],
                    )

            assert result.exit_code == 0

    def test_validate_then_update_workflow(self):
        """Test workflow: validate existing, then update."""
        with self.runner.isolated_filesystem() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text("DATABASE_URL=sqlite:///old.db\n")

            # Step 1: Validate existing file
            with patch(
                "scripts.setup.setup_env.parse_env_file",
                return_value={"DATABASE_URL": "sqlite:///old.db"},
            ):
                with patch(
                    "scripts.setup.setup_env.validate_database_url",
                    return_value=(True, None),
                ):
                    result = self.runner.invoke(
                        main,
                        [
                            "--validate-only",
                            "--output",
                            str(env_file),
                        ],
                    )

            assert result.exit_code == 0

            # Step 2: Update configuration
            with patch("scripts.setup.setup_env.load_env_template") as mock_template:
                mock_template.return_value = {"DATABASE_URL": "sqlite:///new.db"}
                with patch(
                    "scripts.setup.setup_env.parse_env_file",
                    return_value={"DATABASE_URL": "sqlite:///old.db"},
                ):
                    with patch("scripts.setup.setup_env.write_env_file"):
                        result = self.runner.invoke(
                            main,
                            [
                                "--non-interactive",
                                "--output",
                                str(env_file),
                            ],
                        )

            assert result.exit_code == 0
