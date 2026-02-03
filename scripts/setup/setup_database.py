#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Database Setup Script

This script provides automated database setup for PromptVault with support for
both PostgreSQL and SQLite databases. It handles database creation, user setup,
migration execution, and schema verification.

Usage:
    # PostgreSQL setup (interactive)
    python scripts/setup/setup_database.py --type postgresql

    # PostgreSQL setup (non-interactive)
    python scripts/setup/setup_database.py --type postgresql \
        --host localhost --port 5432 --database promptvault \
        --user promptvault --non-interactive

    # SQLite setup
    python scripts/setup/setup_database.py --type sqlite

    # Run migrations only
    python scripts/setup/setup_database.py --migrate-only

    # Create admin user after setup
    python scripts/setup/setup_database.py --type postgresql --create-admin

Features:
    - PostgreSQL and SQLite support
    - Database creation and user setup (PostgreSQL)
    - Connection testing
    - Alembic migration execution
    - Schema integrity verification
    - Admin user creation integration
    - Interactive and non-interactive modes
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, List
import click

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Import SetupConsole directly to avoid validators module import issues
import sys
sys.path.insert(0, str(project_root / "scripts" / "setup" / "utils"))
from console import SetupConsole

from src.db.config import db_settings


class PostgreSQLSetup:
    """PostgreSQL database setup handler.

    Handles PostgreSQL-specific setup including database creation, user setup,
    connection testing, and schema verification.

    Attributes:
        host: PostgreSQL server hostname
        port: PostgreSQL server port
        database: Database name to create
        user: Database user to create
        console: SetupConsole instance for user feedback
    """

    def __init__(self, host: str, port: int, database: str, user: str, console: SetupConsole):
        """Initialize PostgreSQL setup.

        Args:
            host: PostgreSQL server hostname
            port: PostgreSQL server port
            database: Database name
            user: Database user name
            console: SetupConsole for output
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.console = console

    def check_server(self) -> bool:
        """Check if PostgreSQL server is running and accessible.

        Returns:
            True if server is accessible, False otherwise
        """
        try:
            # Use pg_isready to check server status
            result = subprocess.run(
                ["pg_isready", "-h", self.host, "-p", str(self.port)],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # pg_isready not found or timed out, try psql
            try:
                result = subprocess.run(
                    [
                        "psql",
                        "-h", self.host,
                        "-p", str(self.port),
                        "-U", "postgres",
                        "-c", "SELECT 1;",
                        "-d", "postgres"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env={**os.environ, "PGPASSWORD": ""}
                )
                return "FATAL" not in result.stderr or "connection" in result.stderr
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

    def create_database(self, admin_password: str, db_password: str) -> bool:
        """Create database and user with appropriate permissions.

        Args:
            admin_password: PostgreSQL admin (postgres user) password
            db_password: Password for the new database user

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create user
            create_user_sql = f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '{self.user}') THEN
                    CREATE USER {self.user} WITH PASSWORD '{db_password}';
                END IF;
            END
            $$;
            """

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", "postgres",
                    "-d", "postgres",
                    "-c", create_user_sql
                ],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PGPASSWORD": admin_password}
            )

            if result.returncode != 0:
                self.console.error(f"Failed to create user: {result.stderr}")
                return False

            # Create database
            create_db_sql = f"""
            SELECT 'CREATE DATABASE {self.database}'
            WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{self.database}')\\gexec
            """

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", "postgres",
                    "-d", "postgres",
                    "-c", create_db_sql
                ],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PGPASSWORD": admin_password}
            )

            if result.returncode != 0 and "already exists" not in result.stderr:
                self.console.error(f"Failed to create database: {result.stderr}")
                return False

            # Grant privileges
            grant_sql = f"""
            GRANT ALL PRIVILEGES ON DATABASE {self.database} TO {self.user};
            """

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", "postgres",
                    "-d", "postgres",
                    "-c", grant_sql
                ],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PGPASSWORD": admin_password}
            )

            if result.returncode != 0:
                self.console.error(f"Failed to grant privileges: {result.stderr}")
                return False

            # Grant schema privileges (needed for creating tables)
            schema_grant_sql = f"""
            GRANT ALL ON SCHEMA public TO {self.user};
            """

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", "postgres",
                    "-d", self.database,
                    "-c", schema_grant_sql
                ],
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ, "PGPASSWORD": admin_password}
            )

            if result.returncode != 0:
                self.console.warning(f"Could not grant schema privileges: {result.stderr}")

            return True

        except subprocess.TimeoutExpired:
            self.console.error("Database creation timed out")
            return False
        except Exception as e:
            self.console.error(f"Unexpected error creating database: {e}")
            return False

    def test_connection(self, password: str) -> bool:
        """Test database connection with credentials.

        Args:
            password: Database user password

        Returns:
            True if connection successful, False otherwise
        """
        try:
            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", self.user,
                    "-d", self.database,
                    "-c", "SELECT 1;"
                ],
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "PGPASSWORD": password}
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

    def run_migrations(self) -> bool:
        """Run Alembic migrations to create/update schema.

        Returns:
            True if migrations successful, False otherwise
        """
        try:
            # Change to project root for alembic
            os.chdir(project_root)

            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                self.console.error(f"Migration failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            self.console.error("Migration timed out")
            return False
        except Exception as e:
            self.console.error(f"Unexpected error running migrations: {e}")
            return False

    def verify_schema(self) -> List[str]:
        """Verify that all expected tables exist.

        Returns:
            List of table names found in the database
        """
        try:
            # Get database password from environment or prompt
            password = os.environ.get("PGPASSWORD", "")

            result = subprocess.run(
                [
                    "psql",
                    "-h", self.host,
                    "-p", str(self.port),
                    "-U", self.user,
                    "-d", self.database,
                    "-t",  # Tuples only
                    "-c", "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
                ],
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "PGPASSWORD": password}
            )

            if result.returncode != 0:
                self.console.error(f"Failed to query tables: {result.stderr}")
                return []

            # Parse table names
            tables = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            return tables

        except Exception as e:
            self.console.error(f"Error verifying schema: {e}")
            return []


class SQLiteSetup:
    """SQLite database setup handler.

    Handles SQLite-specific setup including database file creation,
    migration execution, and schema verification.

    Attributes:
        path: Path to SQLite database file
        console: SetupConsole instance for user feedback
    """

    def __init__(self, path: str, console: SetupConsole):
        """Initialize SQLite setup.

        Args:
            path: Path to SQLite database file
            console: SetupConsole for output
        """
        self.path = Path(path)
        self.console = console

    def create_database(self) -> bool:
        """Create SQLite database file and parent directories.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories if they don't exist
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # SQLite database will be created automatically on first connection
            # Just verify we can write to the location
            if self.path.exists():
                self.console.info(f"SQLite database already exists at {self.path}")
            else:
                # Touch the file to verify we can create it
                self.path.touch()
                self.console.success(f"SQLite database file created at {self.path}")

            return True

        except PermissionError:
            self.console.error(f"Permission denied: Cannot create database at {self.path}")
            return False
        except Exception as e:
            self.console.error(f"Failed to create database: {e}")
            return False

    def run_migrations(self) -> bool:
        """Run Alembic migrations to create/update schema.

        Returns:
            True if migrations successful, False otherwise
        """
        try:
            # Change to project root for alembic
            os.chdir(project_root)

            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                self.console.error(f"Migration failed: {result.stderr}")
                return False

            return True

        except subprocess.TimeoutExpired:
            self.console.error("Migration timed out")
            return False
        except Exception as e:
            self.console.error(f"Unexpected error running migrations: {e}")
            return False

    def verify_schema(self) -> List[str]:
        """Verify that all expected tables exist.

        Returns:
            List of table names found in the database
        """
        try:
            import sqlite3

            if not self.path.exists():
                self.console.error(f"Database file not found: {self.path}")
                return []

            conn = sqlite3.connect(str(self.path))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [row[0] for row in cursor.fetchall() if not row[0].startswith('sqlite_')]

            conn.close()
            return tables

        except Exception as e:
            self.console.error(f"Error verifying schema: {e}")
            return []


def update_env_file(database_url: str):
    """Update .env file with database URL.

    Args:
        database_url: Database connection URL to write
    """
    env_path = project_root / ".env"

    if not env_path.exists():
        # Create new .env file
        with open(env_path, 'w') as f:
            f.write(f"DATABASE_URL={database_url}\n")
        return

    # Read existing .env
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Update or add DATABASE_URL
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("DATABASE_URL="):
            lines[i] = f"DATABASE_URL={database_url}\n"
            updated = True
            break

    if not updated:
        lines.append(f"DATABASE_URL={database_url}\n")

    # Write back
    with open(env_path, 'w') as f:
        f.writelines(lines)


@click.command()
@click.option(
    '--type',
    'db_type',
    type=click.Choice(['postgresql', 'sqlite'], case_sensitive=False),
    help='Database type to set up'
)
@click.option(
    '--host',
    default='localhost',
    help='PostgreSQL host (default: localhost)'
)
@click.option(
    '--port',
    default=5432,
    type=int,
    help='PostgreSQL port (default: 5432)'
)
@click.option(
    '--database',
    default='promptvault',
    help='Database name (default: promptvault)'
)
@click.option(
    '--user',
    default='promptvault',
    help='Database user (default: promptvault)'
)
@click.option(
    '--migrate-only',
    is_flag=True,
    help='Only run migrations (skip database creation)'
)
@click.option(
    '--create-admin',
    is_flag=True,
    help='Create admin user after setup'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='Run in non-interactive mode (no prompts)'
)
def main(
    db_type: Optional[str],
    host: str,
    port: int,
    database: str,
    user: str,
    migrate_only: bool,
    create_admin: bool,
    non_interactive: bool
):
    """PromptVault Database Setup Tool

    Automates database creation, migration, and initial setup for both
    PostgreSQL and SQLite databases.
    """
    console = SetupConsole()

    console.header(
        "PromptVault Database Setup",
        "Automated database configuration and initialization"
    )

    # Determine database type
    if migrate_only:
        # Use current database configuration
        console.info("Running migrations only (using current DATABASE_URL)")
        db_type = db_settings.database_type

        if db_type == "unknown":
            console.error(f"Unknown database type in DATABASE_URL: {db_settings.DATABASE_URL}")
            sys.exit(1)
    else:
        if not db_type:
            if non_interactive:
                console.error("--type is required in non-interactive mode")
                sys.exit(1)
            db_type = console.select(
                "Select database type:",
                choices=['postgresql', 'sqlite']
            )

    console.info(f"Database type: {db_type}")
    print()  # Empty line for spacing

    # Setup based on database type
    if db_type == 'postgresql':
        setup_postgresql(
            console, host, port, database, user,
            migrate_only, create_admin, non_interactive
        )
    elif db_type == 'sqlite':
        setup_sqlite(console, migrate_only, create_admin, non_interactive)
    else:
        console.error(f"Unsupported database type: {db_type}")
        sys.exit(1)


def setup_postgresql(
    console: SetupConsole,
    host: str,
    port: int,
    database: str,
    user: str,
    migrate_only: bool,
    create_admin: bool,
    non_interactive: bool
):
    """Set up PostgreSQL database.

    Args:
        console: SetupConsole for output
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        migrate_only: Skip database creation
        create_admin: Create admin user after setup
        non_interactive: No prompts
    """
    pg_setup = PostgreSQLSetup(host, port, database, user, console)

    if not migrate_only:
        # Step 1: Check server connectivity
        console.step(1, 5, "Checking PostgreSQL server connectivity")
        with console.spinner(f"Connecting to PostgreSQL at {host}:{port}..."):
            if not pg_setup.check_server():
                console.error(f"Cannot connect to PostgreSQL server at {host}:{port}")
                console.info("Please ensure PostgreSQL is running and accessible")
                sys.exit(1)
        console.success(f"PostgreSQL server is accessible at {host}:{port}")
        print()

        # Step 2: Create database and user
        console.step(2, 5, "Creating database and user")

        if non_interactive:
            console.error("Non-interactive mode requires existing database")
            console.info("Please create database manually or run without --non-interactive")
            sys.exit(1)

        console.info(f"Creating database '{database}' and user '{user}'")
        console.warning("This requires PostgreSQL admin credentials")

        admin_password = console.prompt("PostgreSQL admin (postgres) password", password=True)
        db_password = console.prompt(f"Password for user '{user}'", password=True)

        with console.spinner("Creating database and user..."):
            if not pg_setup.create_database(admin_password, db_password):
                console.error("Failed to create database and user")
                sys.exit(1)

        console.success(f"Database '{database}' and user '{user}' created")
        print()

        # Step 3: Test connection
        console.step(3, 5, "Testing database connection")
        with console.spinner("Testing connection..."):
            if not pg_setup.test_connection(db_password):
                console.error("Failed to connect to database with new credentials")
                sys.exit(1)
        console.success("Database connection successful")
        print()

        # Update .env file
        database_url = f"postgresql://{user}:{db_password}@{host}:{port}/{database}"
        console.info("Updating .env file with database URL")
        update_env_file(database_url)
        console.success(".env file updated")
        print()

        # Reload database settings
        os.environ["DATABASE_URL"] = database_url
    else:
        console.info("Skipping database creation (--migrate-only)")
        print()

    # Step 4: Run migrations
    step_num = 4 if not migrate_only else 1
    total_steps = 5 if not migrate_only else 2
    console.step(step_num, total_steps, "Running database migrations")

    with console.spinner("Applying Alembic migrations..."):
        if not pg_setup.run_migrations():
            console.error("Failed to run migrations")
            sys.exit(1)
    console.success("Database migrations completed")
    print()

    # Step 5: Verify schema
    console.step(step_num + 1, total_steps, "Verifying database schema")
    tables = pg_setup.verify_schema()

    if not tables:
        console.error("No tables found in database")
        sys.exit(1)

    console.success(f"Found {len(tables)} tables in database")

    # Display tables
    expected_tables = [
        'alembic_version', 'backups', 'categories', 'password_reset_tokens',
        'prompt_branches', 'prompt_tags', 'prompt_versions', 'prompts',
        'tags', 'undo_operations', 'user_sessions', 'users'
    ]

    console.table(
        "Database Tables",
        headers=["Table Name", "Status"],
        rows=[
            [table, "[green]✓[/green]" if table in tables else "[red]✗[/red]"]
            for table in expected_tables
        ]
    )

    console.success("PostgreSQL database setup complete!")
    print()

    # Create admin user if requested
    if create_admin:
        console.info("Creating admin user...")
        print()
        create_admin_user()


def setup_sqlite(
    console: SetupConsole,
    migrate_only: bool,
    create_admin: bool,
    non_interactive: bool
):
    """Set up SQLite database.

    Args:
        console: SetupConsole for output
        migrate_only: Skip database creation
        create_admin: Create admin user after setup
        non_interactive: No prompts
    """
    # Determine database path
    if migrate_only:
        # Use current DATABASE_URL
        db_url = db_settings.DATABASE_URL
        db_path = db_url.replace("sqlite:///", "")
    else:
        default_path = "./data/promptvault.db"
        if non_interactive:
            db_path = default_path
        else:
            db_path = console.prompt(
                "SQLite database file path",
                default=default_path
            )

    console.info(f"Database path: {db_path}")
    print()

    sqlite_setup = SQLiteSetup(db_path, console)

    if not migrate_only:
        # Step 1: Create database file
        console.step(1, 3, "Creating SQLite database file")
        if not sqlite_setup.create_database():
            console.error("Failed to create database file")
            sys.exit(1)
        print()

        # Convert to absolute path for DATABASE_URL
        abs_db_path = str(sqlite_setup.path.absolute())

        # Update .env file
        database_url = f"sqlite:///{abs_db_path}"
        console.info("Updating .env file with database URL")
        update_env_file(database_url)
        console.success(".env file updated")
        print()

        # Reload database settings
        os.environ["DATABASE_URL"] = database_url
    else:
        console.info("Skipping database creation (--migrate-only)")
        print()

    # Step 2: Run migrations
    step_num = 2 if not migrate_only else 1
    total_steps = 3 if not migrate_only else 2
    console.step(step_num, total_steps, "Running database migrations")

    with console.spinner("Applying Alembic migrations..."):
        if not sqlite_setup.run_migrations():
            console.error("Failed to run migrations")
            sys.exit(1)
    console.success("Database migrations completed")
    print()

    # Step 3: Verify schema
    console.step(step_num + 1, total_steps, "Verifying database schema")
    tables = sqlite_setup.verify_schema()

    if not tables:
        console.error("No tables found in database")
        sys.exit(1)

    console.success(f"Found {len(tables)} tables in database")

    # Display tables
    expected_tables = [
        'alembic_version', 'backups', 'categories', 'password_reset_tokens',
        'prompt_branches', 'prompt_tags', 'prompt_versions', 'prompts',
        'tags', 'undo_operations', 'user_sessions', 'users'
    ]

    console.table(
        "Database Tables",
        headers=["Table Name", "Status"],
        rows=[
            [table, "[green]✓[/green]" if table in tables else "[red]✗[/red]"]
            for table in expected_tables
        ]
    )

    console.success("SQLite database setup complete!")
    print()

    # Create admin user if requested
    if create_admin:
        console.info("Creating admin user...")
        print()
        create_admin_user()


def create_admin_user():
    """Create admin user using existing script."""
    try:
        # Import and run the create_admin_user script
        admin_script = project_root / "scripts" / "create_admin_user.py"

        result = subprocess.run(
            [sys.executable, str(admin_script)],
            cwd=str(project_root)
        )

        if result.returncode != 0:
            print("\nAdmin user creation failed or was cancelled.")
            sys.exit(result.returncode)
    except Exception as e:
        print(f"\nError running admin user creation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
