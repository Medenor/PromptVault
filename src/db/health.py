# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database health check utilities for PromptVault.

This module provides functions to check database connectivity and health status.
Used for application startup validation and monitoring endpoints.
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import logging
from typing import Dict, Any

from src.db.session import engine
from src.db.config import db_settings

logger = logging.getLogger(__name__)


def check_database_health() -> bool:
    """Check if database is accessible and responsive.

    Performs a simple SELECT 1 query to verify database connectivity.
    This is useful for application startup checks and health monitoring.

    Returns:
        bool: True if database is accessible, False otherwise

    Example:
        if not check_database_health():
            logger.error("Database is not available!")
            sys.exit(1)
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database health check: PASSED")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database health check: FAILED - {e}")
        return False
    except Exception as e:
        logger.error(f"Database health check: FAILED (unexpected error) - {e}")
        return False


def get_database_info() -> Dict[str, Any]:
    """Get database connection information and status.

    Returns diagnostic information about the database connection,
    useful for debugging and monitoring.

    Returns:
        dict: Database information including type, URL (sanitized), and health status

    Example:
        info = get_database_info()
        logger.info(f"Database: {info['type']}, Healthy: {info['healthy']}")
    """
    # Sanitize database URL (remove password)
    sanitized_url = db_settings.DATABASE_URL
    if "@" in sanitized_url:
        # Format: postgresql://user:password@host:port/db
        # Replace password with asterisks
        parts = sanitized_url.split(":")
        if len(parts) >= 3:
            password_part = parts[2].split("@")[0]
            sanitized_url = sanitized_url.replace(password_part, "****")

    info = {
        "type": db_settings.database_type,
        "url": sanitized_url,
        "pool_size": db_settings.DB_POOL_SIZE if db_settings.is_postgresql else "N/A",
        "echo": db_settings.DB_ECHO,
        "healthy": check_database_health(),
    }

    return info


def check_tables_exist() -> Dict[str, bool]:
    """Check if all expected database tables exist.

    Verifies that the database schema has been properly initialized
    via Alembic migrations or create_all_tables().

    Returns:
        dict: Table names mapped to existence status (True/False)

    Example:
        tables = check_tables_exist()
        if not all(tables.values()):
            logger.error(f"Missing tables: {[k for k, v in tables.items() if not v]}")
    """
    expected_tables = [
        "users",
        "categories",
        "tags",
        "prompts",
        "prompt_versions",
        "prompt_branches",
        "prompt_tags",
        "backups",
    ]

    table_status = {}

    try:
        with engine.connect() as conn:
            # Query to check if tables exist (works for both PostgreSQL and SQLite)
            if db_settings.is_postgresql:
                query = text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
            else:  # SQLite
                query = text("""
                    SELECT name as table_name
                    FROM sqlite_master
                    WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                """)

            result = conn.execute(query)
            existing_tables = {row[0] for row in result}

            for table in expected_tables:
                table_status[table] = table in existing_tables

        missing_count = sum(1 for exists in table_status.values() if not exists)
        if missing_count == 0:
            logger.info("All expected tables exist")
        else:
            logger.warning(f"{missing_count} tables missing from database schema")

    except Exception as e:
        logger.error(f"Failed to check table existence: {e}")
        # Mark all as False if we can't check
        table_status = {table: False for table in expected_tables}

    return table_status


def validate_database_schema() -> bool:
    """Comprehensive database schema validation.

    Checks database health and verifies all expected tables exist.

    Returns:
        bool: True if database is healthy and all tables exist, False otherwise

    Example:
        if not validate_database_schema():
            logger.error("Database schema validation failed! Run: alembic upgrade head")
    """
    # Check basic connectivity
    if not check_database_health():
        logger.error("Database schema validation failed: database not accessible")
        return False

    # Check all tables exist
    table_status = check_tables_exist()
    all_tables_exist = all(table_status.values())

    if not all_tables_exist:
        missing = [table for table, exists in table_status.items() if not exists]
        logger.error(f"Database schema validation failed: missing tables: {missing}")
        return False

    logger.info("Database schema validation: PASSED")
    return True
