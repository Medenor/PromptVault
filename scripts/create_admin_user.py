#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Create Admin User Script

This script creates the first admin user for PromptVault. It provides
an interactive CLI interface with password validation and confirmation.

Usage:
    python scripts/create_admin_user.py

Features:
    - Interactive prompts for username, email, and password
    - Password policy validation
    - Password confirmation
    - Duplicate username/email detection
    - Direct database insertion (bypasses API)
    - Verification of successful creation

Security:
    - Passwords are hashed using Argon2id before storage
    - No passwords are logged or displayed
    - Uses the same password service as the API
"""

import sys
import getpass
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from src.config.auth_config import auth_settings
from src.db.session import SessionLocal
from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.services.auth.password_service import PasswordService
from src.services.exceptions import PasswordPolicyError


def print_banner():
    """Print welcome banner."""
    print("=" * 60)
    print("PromptVault - Create Admin User")
    print("=" * 60)
    print()


def print_password_policy():
    """Print password policy requirements."""
    print("Password Policy Requirements:")
    print(f"  - Minimum length: {auth_settings.password_min_length} characters")
    if auth_settings.password_require_uppercase:
        print("  - At least one uppercase letter (A-Z)")
    if auth_settings.password_require_lowercase:
        print("  - At least one lowercase letter (a-z)")
    if auth_settings.password_require_digit:
        print("  - At least one digit (0-9)")
    if auth_settings.password_require_special:
        print("  - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    print()


def get_input(prompt: str, validator=None, allow_empty: bool = False) -> str:
    """Get user input with optional validation.

    Args:
        prompt: Input prompt text
        validator: Optional validation function that raises ValueError on invalid input
        allow_empty: Whether to allow empty input

    Returns:
        Validated user input

    Raises:
        KeyboardInterrupt: If user cancels input
    """
    while True:
        try:
            value = input(prompt).strip()

            if not value and not allow_empty:
                print("  Error: This field cannot be empty.")
                continue

            if validator:
                try:
                    validator(value)
                except (ValueError, PasswordPolicyError) as e:
                    print(f"  Error: {e}")
                    continue

            return value

        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)


def validate_username(username: str) -> None:
    """Validate username format.

    Args:
        username: Username to validate

    Raises:
        ValueError: If username is invalid
    """
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters long")
    if len(username) > 100:
        raise ValueError("Username must be at most 100 characters long")
    if not username.replace("_", "").replace("-", "").replace(".", "").isalnum():
        raise ValueError("Username can only contain letters, numbers, underscores, hyphens, and periods")


def validate_email(email: str) -> None:
    """Validate email format.

    Args:
        email: Email to validate

    Raises:
        ValueError: If email is invalid
    """
    if "@" not in email or "." not in email.split("@")[1]:
        raise ValueError("Invalid email format")
    if len(email) > 255:
        raise ValueError("Email must be at most 255 characters long")


def get_password(password_service: PasswordService) -> str:
    """Get and validate password with confirmation.

    Args:
        password_service: Password service for validation

    Returns:
        Validated password

    Raises:
        KeyboardInterrupt: If user cancels input
    """
    while True:
        try:
            password = getpass.getpass("Password: ")

            if not password:
                print("  Error: Password cannot be empty.")
                continue

            # Validate password
            try:
                password_service.validate_password_policy(password)
            except PasswordPolicyError as e:
                print(f"  Error: {e}")
                continue

            # Confirm password
            confirm = getpass.getpass("Confirm Password: ")

            if password != confirm:
                print("  Error: Passwords do not match. Please try again.")
                continue

            return password

        except KeyboardInterrupt:
            print("\n\nOperation cancelled by user.")
            sys.exit(0)


def create_admin_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    password_service: PasswordService
) -> User:
    """Create admin user in database.

    Args:
        db: Database session
        username: Admin username
        email: Admin email
        password: Admin password (will be hashed)
        password_service: Password service for hashing

    Returns:
        Created User object

    Raises:
        ValueError: If username or email already exists
    """
    user_repo = UserRepository(db)

    # Check for existing username
    existing_user = user_repo.get_by_username(username)
    if existing_user:
        raise ValueError(f"Username '{username}' already exists")

    # Check for existing email
    existing_user = user_repo.get_by_email(email)
    if existing_user:
        raise ValueError(f"Email '{email}' already exists")

    # Hash password
    password_hash = password_service.hash_password(password)

    # Create user
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role='admin',
        is_active=True,
        email_verified=True  # Auto-verify first admin
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def main():
    """Main entry point."""
    print_banner()

    # Initialize services
    password_service = PasswordService(auth_settings)

    print("This script will create the first admin user for PromptVault.")
    print("Please provide the following information:")
    print()

    # Get username
    print("Username:")
    username = get_input("  > ", validator=validate_username)

    # Get email
    print("\nEmail:")
    email = get_input("  > ", validator=validate_email)

    # Get password
    print("\nPassword:")
    print_password_policy()
    password = get_password(password_service)

    # Confirm creation
    print("\n" + "-" * 60)
    print("Please review the information:")
    print(f"  Username: {username}")
    print(f"  Email:    {email}")
    print(f"  Role:     admin")
    print("-" * 60)

    confirm = input("\nCreate this admin user? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y']:
        print("\nOperation cancelled.")
        sys.exit(0)

    # Create user in database
    print("\nCreating admin user...")
    try:
        db = SessionLocal()
        try:
            user = create_admin_user(db, username, email, password, password_service)
            print("\n✓ Admin user created successfully!")
            print(f"  User ID:  {user.id}")
            print(f"  Username: {user.username}")
            print(f"  Email:    {user.email}")
            print(f"  Role:     {user.role}")
            print(f"\n✓ You can now login with these credentials.")
            sys.exit(0)

        finally:
            db.close()

    except ValueError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
