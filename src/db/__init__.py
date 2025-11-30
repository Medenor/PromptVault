# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PromptVault database package.

This package provides database configuration, session management, ORM models,
and repository patterns for the PromptVault application.

Main Components:
    - config: Database configuration settings (DatabaseSettings, db_settings)
    - session: Session management (engine, get_db_session, get_db)
    - health: Database health checks (check_database_health, validate_database_schema)
    - models: SQLAlchemy ORM models (User, Prompt, PromptVersion, etc.)
    - base: SQLAlchemy declarative base

Quick Start:
    from src.db import get_db_session, db_settings
    from src.db.models import Prompt

    # Check database type
    if db_settings.is_sqlite:
        print("Using SQLite")

    # Use session context manager
    with get_db_session() as session:
        prompts = session.query(Prompt).all()
"""

# Configuration
from src.db.config import DatabaseSettings, db_settings

# Session management
from src.db.session import (
    engine,
    SessionLocal,
    get_db_session,
    get_db,
    create_all_tables,
    drop_all_tables,
)

# Health checks
from src.db.health import (
    check_database_health,
    get_database_info,
    check_tables_exist,
    validate_database_schema,
)

# Base and models
from src.db.base import Base

__all__ = [
    # Configuration
    "DatabaseSettings",
    "db_settings",
    # Session management
    "engine",
    "SessionLocal",
    "get_db_session",
    "get_db",
    "create_all_tables",
    "drop_all_tables",
    # Health checks
    "check_database_health",
    "get_database_info",
    "check_tables_exist",
    "validate_database_schema",
    # Base
    "Base",
]
