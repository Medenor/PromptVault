# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database configuration for PromptVault.

This module provides database configuration settings using Pydantic BaseSettings.
Supports both PostgreSQL (production) and SQLite (development/testing) with
environment variable-based configuration.

Environment Variables:
    DATABASE_URL: Database connection string (default: SQLite at ./data/promptvault.db)
    DB_POOL_SIZE: Connection pool size for PostgreSQL (default: 20)
    DB_POOL_TIMEOUT: Connection pool timeout in seconds (default: 30)
    DB_POOL_RECYCLE: Connection pool recycle time in seconds (default: 3600)
    DB_ECHO: Enable SQL query logging (default: False)

Example URLs:
    SQLite: sqlite:///./data/promptvault.db
    PostgreSQL: postgresql://user:password@localhost:5432/promptvault
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings.

    Attributes:
        DATABASE_URL: SQLAlchemy database URL
        DB_POOL_SIZE: Connection pool size (PostgreSQL only)
        DB_POOL_TIMEOUT: Connection timeout in seconds
        DB_POOL_RECYCLE: Time to recycle connections in seconds
        DB_ECHO: Enable SQLAlchemy query logging for debugging
    """
    DATABASE_URL: str = "sqlite:///./data/promptvault.db"
    DB_POOL_SIZE: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

    @property
    def is_sqlite(self) -> bool:
        """Check if using SQLite database.

        Returns:
            True if DATABASE_URL points to SQLite, False otherwise
        """
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        """Check if using PostgreSQL database.

        Returns:
            True if DATABASE_URL points to PostgreSQL, False otherwise
        """
        return self.DATABASE_URL.startswith("postgresql")

    @property
    def database_type(self) -> str:
        """Get database type as string.

        Returns:
            'sqlite', 'postgresql', or 'unknown'
        """
        if self.is_sqlite:
            return "sqlite"
        elif self.is_postgresql:
            return "postgresql"
        return "unknown"

    def get_engine_kwargs(self) -> dict:
        """Get SQLAlchemy engine configuration kwargs.

        Returns appropriate engine configuration based on database type.
        SQLite uses different connection pooling than PostgreSQL.

        Returns:
            dict: Engine configuration kwargs for create_engine()
        """
        base_kwargs = {
            "echo": self.DB_ECHO,
            "pool_pre_ping": True,  # Verify connections before using
        }

        if self.is_sqlite:
            # SQLite-specific configuration
            # Use StaticPool for in-memory, NullPool for file-based
            if ":memory:" in self.DATABASE_URL:
                base_kwargs["poolclass"] = None  # Will use StaticPool by default
            else:
                # For file-based SQLite, use default pool settings
                base_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            # PostgreSQL-specific configuration
            base_kwargs.update({
                "pool_size": self.DB_POOL_SIZE,
                "pool_recycle": self.DB_POOL_RECYCLE,
                "pool_timeout": self.DB_POOL_TIMEOUT,
            })

        return base_kwargs


# Global database settings instance
# This will be imported and used throughout the application
db_settings = DatabaseSettings()
