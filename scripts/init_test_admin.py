# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
"""
Initialize test admin account for AUTH-UI Playwright tests.

This script creates a test admin user if it doesn't already exist.
Use this before running Playwright UI tests.

Usage:
    python scripts/init_test_admin.py
    
Environment Variables:
    DATABASE_URL: Database connection string (defaults to SQLite)
    TEST_ADMIN_USERNAME: Username (default: test_admin_ui)
    TEST_ADMIN_EMAIL: Email (default: test_admin_ui@example.com)
    TEST_ADMIN_PASSWORD: Password (default: TestAdmin@Pass123456)
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from src.db.session import SessionLocal, engine
from src.db.base import Base
from src.db.models.user import User
from src.services.auth.password_service import PasswordService
from src.config.auth_config import auth_settings
from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)

# Test account configuration
TEST_ADMIN_USERNAME = os.getenv('TEST_ADMIN_USERNAME', 'test_admin_ui')
TEST_ADMIN_EMAIL = os.getenv('TEST_ADMIN_EMAIL', 'test_admin_ui@example.com')
TEST_ADMIN_PASSWORD = os.getenv('TEST_ADMIN_PASSWORD', 'TestAdmin@Pass123456')

TEST_USER_USERNAME = os.getenv('TEST_USER_USERNAME', 'test_user_ui')
TEST_USER_EMAIL = os.getenv('TEST_USER_EMAIL', 'test_user_ui@example.com')
TEST_USER_PASSWORD = os.getenv('TEST_USER_PASSWORD', 'TestUser@Pass123456')


def create_test_user(
    session: Session,
    username: str,
    email: str,
    password: str,
    role: str = "viewer",
) -> User:
    """Create a test user if it doesn't exist.
    
    Args:
        session: Database session
        username: Username
        email: Email address
        password: Plain password
        role: User role (viewer, editor, admin)
        
    Returns:
        User object (created or existing)
    """
    # Check if user already exists
    existing_user = session.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        logger.info(f"✓ Test user '{username}' already exists (ID: {existing_user.id})")
        return existing_user
    
    # Create password hash (policy/params from auth_settings)
    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password(password)
    
    # Create new user
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        
        logger.info(f"✓ Created test user '{username}' (role: {role}, ID: {user.id})")
        
        return user
    except IntegrityError as e:
        session.rollback()
        logger.error(f"✗ Failed to create test user '{username}': {e}")
        raise


def init_test_users():
    """Initialize test users for AUTH-UI tests."""
    logger.info("Initializing test users for AUTH-UI Playwright tests...")
    logger.info("")
    
    session = SessionLocal()
    
    try:
        # Create test admin user
        logger.info(f"Creating test admin user: {TEST_ADMIN_USERNAME}")
        admin_user = create_test_user(
            session,
            username=TEST_ADMIN_USERNAME,
            email=TEST_ADMIN_EMAIL,
            password=TEST_ADMIN_PASSWORD,
            role="admin"
        )
        
        logger.info("")
        logger.info(f"Creating test regular user: {TEST_USER_USERNAME}")
        
        # Create test regular user
        user = create_test_user(
            session,
            username=TEST_USER_USERNAME,
            email=TEST_USER_EMAIL,
            password=TEST_USER_PASSWORD,
            role="viewer"
        )
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Test users initialized successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Test Account Credentials:")
        logger.info("")
        logger.info("Admin User:")
        logger.info(f"  Username: {TEST_ADMIN_USERNAME}")
        logger.info(f"  Email: {TEST_ADMIN_EMAIL}")
        logger.info(f"  Password: {TEST_ADMIN_PASSWORD}")
        logger.info(f"  Role: admin")
        logger.info("")
        logger.info("Regular User:")
        logger.info(f"  Username: {TEST_USER_USERNAME}")
        logger.info(f"  Email: {TEST_USER_EMAIL}")
        logger.info(f"  Password: {TEST_USER_PASSWORD}")
        logger.info(f"  Role: viewer")
        logger.info("")
        logger.info("Usage:")
        logger.info(f"  npx playwright test scripts/playwright_auth_ui_tests.ts")
        logger.info("")
        
    except Exception as e:
        logger.error(f"✗ Error initializing test users: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    init_test_users()
