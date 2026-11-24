#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Environment Configuration Setup Script

This script provides interactive configuration for PromptVault environment variables,
with support for multiple deployment profiles (development, production).

Features:
- Interactive prompts for configuration values
- Auto-generate secure secrets (SECRET_KEY, passwords)
- Validate all configuration using validators.py
- Support deployment profiles with different defaults
- Load configuration from YAML file
- Show diff between existing and new configuration
- Write validated configuration to .env file

Usage:
    python scripts/setup/setup_env.py
    python scripts/setup/setup_env.py --profile production
    python scripts/setup/setup_env.py --from-file config.yaml
    python scripts/setup/setup_env.py --validate-only
    python scripts/setup/setup_env.py --non-interactive
"""

import os
import sys
import secrets
import string
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from urllib.parse import quote_plus, urlsplit

import click

# Add scripts directory to path to import utilities
script_dir = Path(__file__).resolve().parent
setup_utils_dir = script_dir / "utils"
sys.path.insert(0, str(setup_utils_dir))

from console import SetupConsole
from validators import (
    validate_database_url,
    validate_port,
    validate_hostname,
    validate_email,
    validate_password_strength,
    validate_path,
)
from config_parser import (
    parse_env_file,
    parse_yaml_config,
    load_env_template,
    write_env_file,
)


class EnvConfigurator:
    """
    Manages environment configuration for different deployment profiles.

    Handles interactive prompts, validation, secret generation, and
    configuration file writing with profile-specific defaults.
    """

    # Former hardcoded production database password. Rejected by validate().
    LEGACY_DEFAULT_DB_PASSWORD = 'changeme'

    # Profile-specific defaults
    PROFILE_DEFAULTS = {
        'development': {
            'DATABASE_URL': 'sqlite:///./data/promptvault.db',
            'ENVIRONMENT': 'development',
            'LOG_LEVEL': 'DEBUG',
            'AUDIT_LOG_LEVEL': 'INFO',
            'DB_ECHO': 'true',
            'REDIS_URL': 'redis://localhost:6379/0',
        },
        'production': {
            # No DATABASE_URL default: production requires an operator-supplied
            # URL (prompted for, or provided via --from-file / .env.example).
            'ENVIRONMENT': 'production',
            'LOG_LEVEL': 'WARNING',
            'AUDIT_LOG_LEVEL': 'INFO',
            'DB_ECHO': 'false',
            'REDIS_URL': 'redis://localhost:6379/0',
        }
    }

    def __init__(self, profile: str, console: SetupConsole):
        """
        Initialize configurator with a deployment profile.

        Args:
            profile: Deployment profile name ('development' or 'production')
            console: SetupConsole instance for user interaction
        """
        self.profile = profile
        self.console = console
        self.config: Dict[str, str] = {}

        if profile not in self.PROFILE_DEFAULTS:
            raise ValueError(f"Invalid profile: {profile}. Must be 'development' or 'production'")

    def load_template(self) -> Dict[str, str]:
        """
        Load .env.example as template and merge with profile defaults.

        Returns:
            Dictionary containing template configuration with profile defaults
        """
        try:
            template = load_env_template()

            # Merge profile defaults
            for key, value in self.PROFILE_DEFAULTS[self.profile].items():
                template[key] = value

            # .env.example carries the development database URL; production must
            # not inherit it, so validate() demands an operator-supplied one.
            if self.profile == 'production':
                template.pop('DATABASE_URL', None)

            return template
        except FileNotFoundError as e:
            self.console.error(f"Template not found: {e}")
            raise
        except Exception as e:
            self.console.error(f"Error loading template: {e}")
            raise

    def prompt_database(self) -> Dict[str, str]:
        """
        Interactive prompts for database configuration.

        Returns:
            Dictionary with database configuration values
        """
        config = {}

        self.console.info("Database Configuration")
        self.console.console.print()

        if self.profile == 'development':
            self.console.info("Development profile: Using SQLite database")
            db_type = self.console.select(
                "Select database type",
                choices=["sqlite", "postgresql"]
            )
        else:
            self.console.info("Production profile: PostgreSQL recommended")
            db_type = self.console.select(
                "Select database type",
                choices=["postgresql", "sqlite"]
            )

        if db_type == "sqlite":
            # SQLite configuration
            db_path = self.console.prompt(
                "SQLite database path",
                default="./data/promptvault.db"
            )
            config['DATABASE_URL'] = f"sqlite:///{db_path}"

        else:
            # PostgreSQL configuration
            self.console.console.print()
            self.console.info("PostgreSQL Configuration")

            db_host = self.console.prompt("Database host", default="localhost")
            while True:
                is_valid, error = validate_hostname(db_host)
                if is_valid:
                    break
                self.console.error(f"Invalid hostname: {error}")
                db_host = self.console.prompt("Database host", default="localhost")

            db_port = self.console.prompt("Database port", default="5432")
            while True:
                is_valid, error = validate_port(db_port)
                if is_valid:
                    break
                self.console.error(f"Invalid port: {error}")
                db_port = self.console.prompt("Database port", default="5432")

            db_name = self.console.prompt("Database name", default="promptvault")
            db_user = self.console.prompt("Database user", default="promptvault")

            # Database password
            self.console.console.print()
            if self.console.confirm("Auto-generate secure database password?", default=True):
                db_password = self.generate_secure_password(32)
                self.console.success(f"Generated password: {db_password}")
            else:
                db_password = self.console.prompt("Database password", password=True)

            config['DATABASE_URL'] = f"postgresql://{db_user}:{quote_plus(db_password)}@{db_host}:{db_port}/{db_name}"

            # PostgreSQL pool settings
            config['DB_POOL_SIZE'] = self.console.prompt("Connection pool size", default="20")
            config['DB_POOL_TIMEOUT'] = self.console.prompt("Pool timeout (seconds)", default="30")
            config['DB_POOL_RECYCLE'] = self.console.prompt("Pool recycle time (seconds)", default="3600")

        # Common database settings
        config['DB_ECHO'] = self.PROFILE_DEFAULTS[self.profile]['DB_ECHO']

        self.console.console.print()
        return config

    def prompt_security(self) -> Dict[str, str]:
        """
        Interactive prompts for security configuration.

        Returns:
            Dictionary with security configuration values
        """
        config = {}

        self.console.info("Security Configuration")
        self.console.console.print()

        # JWT keys
        self.console.info("JWT Key Configuration")
        default_private = "secrets/jwt/private_key.pem"
        default_public = "secrets/jwt/public_key.pem"

        config['JWT_PRIVATE_KEY_PATH'] = self.console.prompt(
            "JWT private key path",
            default=default_private
        )
        config['JWT_PUBLIC_KEY_PATH'] = self.console.prompt(
            "JWT public key path",
            default=default_public
        )

        # JWT token expiration
        self.console.console.print()
        self.console.info("JWT Token Expiration")
        config['JWT_ACCESS_TOKEN_EXPIRE_SECONDS'] = self.console.prompt(
            "Access token expiration (seconds)",
            default="900"  # 15 minutes
        )
        config['JWT_REFRESH_TOKEN_EXPIRE_SECONDS'] = self.console.prompt(
            "Refresh token expiration (seconds)",
            default="604800"  # 7 days
        )

        # JWT issuer/audience
        config['JWT_ISSUER'] = self.console.prompt(
            "JWT issuer",
            default="promptvault"
        )
        config['JWT_AUDIENCE'] = self.console.prompt(
            "JWT audience",
            default="promptvault-api"
        )

        # Password policy
        self.console.console.print()
        self.console.info("Password Policy")
        if self.profile == 'production':
            self.console.info("Production profile: Using strict password policy")
            config['PASSWORD_MIN_LENGTH'] = "16"
            config['PASSWORD_REQUIRE_UPPERCASE'] = "true"
            config['PASSWORD_REQUIRE_LOWERCASE'] = "true"
            config['PASSWORD_REQUIRE_DIGIT'] = "true"
            config['PASSWORD_REQUIRE_SPECIAL'] = "true"
        else:
            config['PASSWORD_MIN_LENGTH'] = self.console.prompt(
                "Minimum password length",
                default="12"
            )
            config['PASSWORD_REQUIRE_UPPERCASE'] = str(self.console.confirm(
                "Require uppercase letter?",
                default=True
            )).lower()
            config['PASSWORD_REQUIRE_LOWERCASE'] = str(self.console.confirm(
                "Require lowercase letter?",
                default=True
            )).lower()
            config['PASSWORD_REQUIRE_DIGIT'] = str(self.console.confirm(
                "Require digit?",
                default=True
            )).lower()
            config['PASSWORD_REQUIRE_SPECIAL'] = str(self.console.confirm(
                "Require special character?",
                default=True
            )).lower()

        # Account security
        self.console.console.print()
        self.console.info("Account Security")
        config['MAX_LOGIN_ATTEMPTS'] = self.console.prompt(
            "Max login attempts before lockout",
            default="5"
        )
        config['ACCOUNT_LOCKOUT_DURATION_SECONDS'] = self.console.prompt(
            "Account lockout duration (seconds)",
            default="900"  # 15 minutes
        )
        config['MAX_SESSIONS_PER_USER'] = self.console.prompt(
            "Max sessions per user (0 = unlimited)",
            default="5"
        )
        config['SESSION_INACTIVE_TIMEOUT_SECONDS'] = self.console.prompt(
            "Session inactive timeout (seconds)",
            default="2592000"  # 30 days
        )

        # Rate limiting
        self.console.console.print()
        self.console.info("Rate Limiting")
        config['REDIS_URL'] = self.console.prompt(
            "Redis URL for rate limiting",
            default="redis://localhost:6379/0"
        )

        config['RATE_LIMIT_LOGIN_ATTEMPTS'] = self.console.prompt(
            "Login rate limit attempts",
            default="5"
        )
        config['RATE_LIMIT_LOGIN_WINDOW_SECONDS'] = self.console.prompt(
            "Login rate limit window (seconds)",
            default="900"
        )
        config['RATE_LIMIT_REGISTER_ATTEMPTS'] = self.console.prompt(
            "Registration rate limit attempts",
            default="3"
        )
        config['RATE_LIMIT_REGISTER_WINDOW_SECONDS'] = self.console.prompt(
            "Registration rate limit window (seconds)",
            default="3600"
        )
        config['RATE_LIMIT_PASSWORD_RESET_ATTEMPTS'] = self.console.prompt(
            "Password reset rate limit attempts",
            default="3"
        )
        config['RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS'] = self.console.prompt(
            "Password reset rate limit window (seconds)",
            default="3600"
        )

        self.console.console.print()
        return config

    def prompt_email(self, optional: bool = True) -> Dict[str, str]:
        """
        Interactive prompts for email configuration.

        Args:
            optional: If True, user can skip email configuration

        Returns:
            Dictionary with email configuration values
        """
        config = {}

        self.console.info("Email Configuration (for password reset)")
        self.console.console.print()

        if optional:
            if not self.console.confirm("Configure email settings?", default=False):
                # Use placeholder values
                config['SMTP_HOST'] = "smtp.example.com"
                config['SMTP_PORT'] = "587"
                config['SMTP_USE_TLS'] = "true"
                config['SMTP_USERNAME'] = "noreply@example.com"
                config['SMTP_PASSWORD'] = "changeme"
                config['EMAIL_FROM_ADDRESS'] = "noreply@example.com"
                config['EMAIL_FROM_NAME'] = "PromptVault"
                config['PASSWORD_RESET_TOKEN_EXPIRE_SECONDS'] = "3600"
                return config

        # SMTP configuration
        config['SMTP_HOST'] = self.console.prompt("SMTP host", default="smtp.example.com")

        smtp_port = self.console.prompt("SMTP port", default="587")
        while True:
            is_valid, error = validate_port(smtp_port)
            if is_valid:
                break
            self.console.error(f"Invalid port: {error}")
            smtp_port = self.console.prompt("SMTP port", default="587")
        config['SMTP_PORT'] = smtp_port

        config['SMTP_USE_TLS'] = str(self.console.confirm(
            "Use TLS?",
            default=True
        )).lower()

        smtp_user = self.console.prompt("SMTP username", default="noreply@example.com")
        while True:
            is_valid, error = validate_email(smtp_user)
            if is_valid:
                break
            self.console.error(f"Invalid email: {error}")
            smtp_user = self.console.prompt("SMTP username", default="noreply@example.com")
        config['SMTP_USERNAME'] = smtp_user

        config['SMTP_PASSWORD'] = self.console.prompt("SMTP password", password=True)

        # Email sender
        self.console.console.print()
        from_addr = self.console.prompt("From email address", default=smtp_user)
        while True:
            is_valid, error = validate_email(from_addr)
            if is_valid:
                break
            self.console.error(f"Invalid email: {error}")
            from_addr = self.console.prompt("From email address", default=smtp_user)
        config['EMAIL_FROM_ADDRESS'] = from_addr

        config['EMAIL_FROM_NAME'] = self.console.prompt(
            "From name",
            default="PromptVault"
        )

        # Password reset token expiration
        config['PASSWORD_RESET_TOKEN_EXPIRE_SECONDS'] = self.console.prompt(
            "Password reset token expiration (seconds)",
            default="3600"  # 1 hour
        )

        self.console.console.print()
        return config

    def prompt_application(self) -> Dict[str, str]:
        """
        Interactive prompts for application configuration.

        Returns:
            Dictionary with application configuration values
        """
        config = {}

        self.console.info("Application Configuration")
        self.console.console.print()

        # Environment
        config['ENVIRONMENT'] = self.PROFILE_DEFAULTS[self.profile]['ENVIRONMENT']
        self.console.info(f"Environment: {config['ENVIRONMENT']}")

        # Logging
        config['LOG_LEVEL'] = self.console.select(
            "Log level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        ) if self.profile == 'development' else self.PROFILE_DEFAULTS[self.profile]['LOG_LEVEL']

        config['AUDIT_LOG_LEVEL'] = self.PROFILE_DEFAULTS[self.profile]['AUDIT_LOG_LEVEL']

        # Application URL
        config['APP_BASE_URL'] = self.console.prompt(
            "Application base URL",
            default="http://localhost:8000"
        )

        self.console.console.print()
        return config

    def generate_secure_password(self, length: int = 32) -> str:
        """
        Generate a secure random password.

        Args:
            length: Password length (default: 32)

        Returns:
            Secure random password string
        """
        # Character sets for password generation
        chars = string.ascii_letters + string.digits + string.punctuation

        # Use secrets module for cryptographically strong random
        password = ''.join(secrets.choice(chars) for _ in range(length))

        # Ensure password meets complexity requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in string.punctuation for c in password)

        # Regenerate if doesn't meet requirements (very unlikely)
        if not (has_upper and has_lower and has_digit and has_special):
            return self.generate_secure_password(length)

        return password

    def validate(self) -> List[str]:
        """
        Validate all configuration values.

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        # Validate database URL
        if 'DATABASE_URL' in self.config:
            is_valid, error = validate_database_url(self.config['DATABASE_URL'])
            if not is_valid:
                errors.append(f"DATABASE_URL: {error}")

        # Production must carry an operator-supplied database URL, and must
        # never accept the legacy hardcoded password default.
        if self.profile == 'production':
            db_url = self.config.get('DATABASE_URL', '')
            if not db_url:
                errors.append(
                    "DATABASE_URL: required for the production profile. "
                    "Provide a database URL with your own credentials "
                    "(run interactively, or set it in the config file)."
                )
            elif urlsplit(db_url).password == self.LEGACY_DEFAULT_DB_PASSWORD:
                errors.append(
                    "DATABASE_URL: uses the legacy default password 'changeme', "
                    "which is not allowed in production. Use your own credentials."
                )

        # Validate ports
        for port_key in ['SMTP_PORT', 'DB_POOL_SIZE']:
            if port_key in self.config:
                is_valid, error = validate_port(self.config[port_key])
                if not is_valid:
                    errors.append(f"{port_key}: {error}")

        # Validate email addresses
        for email_key in ['SMTP_USERNAME', 'EMAIL_FROM_ADDRESS']:
            if email_key in self.config:
                email_value = self.config[email_key]
                # Skip validation for placeholder values
                if email_value and email_value != "noreply@example.com":
                    is_valid, error = validate_email(email_value)
                    if not is_valid:
                        errors.append(f"{email_key}: {error}")

        # Validate JWT key paths exist (if not placeholder)
        for key_path_key in ['JWT_PRIVATE_KEY_PATH', 'JWT_PUBLIC_KEY_PATH']:
            if key_path_key in self.config:
                path_value = self.config[key_path_key]
                # Validate parent directory exists
                is_valid, error = validate_path(path_value, must_exist=False)
                if not is_valid:
                    errors.append(f"{key_path_key}: {error}")

        return errors

    def diff(self, existing: Dict[str, str]) -> str:
        """
        Generate diff between existing and new configuration.

        Args:
            existing: Existing configuration dictionary

        Returns:
            Human-readable diff string
        """
        from rich.text import Text
        from rich.table import Table

        # Create table for diff
        table = Table(
            title="Configuration Changes",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Setting", style="cyan")
        table.add_column("Old Value", style="yellow")
        table.add_column("New Value", style="green")

        # Find all keys
        all_keys = set(existing.keys()) | set(self.config.keys())

        changes_found = False
        for key in sorted(all_keys):
            old_value = existing.get(key, "[not set]")
            new_value = self.config.get(key, "[not set]")

            if old_value != new_value:
                changes_found = True

                # Mask sensitive values
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key']):
                    if old_value != "[not set]":
                        old_value = "********"
                    if new_value != "[not set]":
                        new_value = "********"

                table.add_row(key, old_value, new_value)

        if not changes_found:
            return "No changes detected"

        return table

    def write(self, path: Path) -> None:
        """
        Write configuration to .env file.

        Args:
            path: Path where the .env file should be written
        """
        try:
            write_env_file(str(path), self.config)
            self.console.success(f"Configuration written to: {path}")
        except Exception as e:
            self.console.error(f"Failed to write configuration: {e}")
            raise


@click.command()
@click.option(
    '--profile',
    type=click.Choice(['development', 'production']),
    default='development',
    help='Configuration profile (default: development)'
)
@click.option(
    '--from-file',
    type=click.Path(exists=True),
    help='Load configuration from YAML file'
)
@click.option(
    '--validate-only',
    is_flag=True,
    help='Only validate existing .env without making changes'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='Non-interactive mode, use defaults'
)
@click.option(
    '--output',
    type=click.Path(),
    default='.env',
    help='Output file path (default: .env)'
)
def main(profile: str, from_file: Optional[str], validate_only: bool, non_interactive: bool, output: str):
    """
    Interactive Environment Configuration Setup.

    Configure PromptVault environment variables with validation,
    profile support, and secure secret generation.
    """
    console = SetupConsole()

    # Display header
    console.header(
        "PromptVault Environment Setup",
        f"Interactive configuration for {profile} deployment"
    )

    # Resolve output path
    project_root = Path(__file__).resolve().parent.parent.parent
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    # VALIDATE-ONLY mode
    if validate_only:
        console.step(1, 1, "Validating existing .env file")

        if not output_path.exists():
            console.error(f"File not found: {output_path}")
            sys.exit(1)

        try:
            existing_config = parse_env_file(str(output_path))
            console.success(f"Loaded {len(existing_config)} configuration values")

            # Create configurator to use validation
            configurator = EnvConfigurator(profile, console)
            configurator.config = existing_config

            # Validate
            errors = configurator.validate()
            if errors:
                console.error("Validation errors found:")
                for error in errors:
                    console.console.print(f"  - {error}", style="red")
                sys.exit(1)
            else:
                console.success("All configuration values are valid")
                sys.exit(0)

        except Exception as e:
            console.error(f"Validation failed: {e}")
            sys.exit(1)

    # FROM-FILE mode
    if from_file:
        console.step(1, 3, f"Loading configuration from {from_file}")

        try:
            yaml_config = parse_yaml_config(from_file)
            console.success(f"Loaded configuration from {from_file}")

            # Create configurator and set config
            configurator = EnvConfigurator(profile, console)

            # Convert YAML config to flat dict
            # Assume flat structure or profile-based structure
            if profile in yaml_config:
                configurator.config = yaml_config[profile]
            else:
                configurator.config = yaml_config

        except Exception as e:
            console.error(f"Failed to load configuration: {e}")
            sys.exit(1)

    # INTERACTIVE mode
    else:
        configurator = EnvConfigurator(profile, console)

        if non_interactive:
            console.warning("Non-interactive mode: using profile defaults")
            try:
                configurator.config = configurator.load_template()
            except Exception as e:
                console.error(f"Failed to load template: {e}")
                sys.exit(1)
        else:
            # Interactive prompts
            console.info(f"Starting interactive configuration for {profile} profile")
            console.console.print()

            try:
                # Prompt for each section
                console.step(1, 4, "Database Configuration")
                configurator.config.update(configurator.prompt_database())

                console.step(2, 4, "Security Configuration")
                configurator.config.update(configurator.prompt_security())

                console.step(3, 4, "Email Configuration")
                configurator.config.update(configurator.prompt_email(optional=True))

                console.step(4, 4, "Application Configuration")
                configurator.config.update(configurator.prompt_application())

            except KeyboardInterrupt:
                console.console.print()
                console.warning("Configuration cancelled by user")
                sys.exit(1)

    # Validate configuration
    console.console.print()
    console.info("Validating configuration...")

    errors = configurator.validate()
    if errors:
        console.error("Configuration validation failed:")
        for error in errors:
            console.console.print(f"  - {error}", style="red")

        # Production never proceeds with an invalid configuration, even interactively.
        if non_interactive or profile == 'production':
            sys.exit(1)
        if not console.confirm("Continue anyway?", default=False):
            sys.exit(1)
    else:
        console.success("Configuration validation passed")

    # Show diff if file exists
    if output_path.exists():
        console.console.print()
        console.info("Comparing with existing configuration...")

        try:
            existing_config = parse_env_file(str(output_path))
            diff = configurator.diff(existing_config)

            if isinstance(diff, str) and diff == "No changes detected":
                console.info(diff)
            else:
                console.console.print(diff)
        except Exception as e:
            console.warning(f"Could not load existing configuration: {e}")

    # Confirm before writing
    if not non_interactive:
        console.console.print()
        if not console.confirm("Write configuration to .env file?", default=True):
            console.info("Configuration cancelled")
            sys.exit(0)

    # Write configuration
    console.console.print()
    console.info("Writing configuration...")

    try:
        configurator.write(output_path)
        console.success("Configuration file created successfully!")
    except Exception as e:
        console.error(f"Failed to write configuration: {e}")
        sys.exit(1)

    # Success summary
    console.console.print()
    console.console.print("[bold green]Environment setup completed successfully![/bold green]")
    console.console.print()

    # Next steps
    console.info("Next steps:")
    console.console.print("  1. Review the generated .env file")
    console.console.print("  2. Generate JWT keys: python scripts/setup/setup_jwt.py")
    console.console.print("  3. Initialize the database: alembic upgrade head")
    console.console.print("  4. Start the application: uvicorn app.main:app")
    console.console.print()

    console.warning("IMPORTANT: Never commit the .env file to version control")
    console.console.print()

    sys.exit(0)


if __name__ == "__main__":
    main()
