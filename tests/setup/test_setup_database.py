# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for database setup script.

Tests cover:
- PostgreSQLSetup class (connection, creation, migrations, schema)
- SQLiteSetup class (file creation, migrations, schema)
- Migration handling (Alembic execution)
- Schema verification
- Admin user creation
- CLI integration and flags
- Error handling for all failure scenarios
- Integration workflows
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from click.testing import CliRunner

# Import the module to test
from scripts.setup.setup_database import (
    PostgreSQLSetup,
    SQLiteSetup,
    create_admin_user,
    main,
    setup_postgresql,
    setup_sqlite,
    update_env_file,
)


class TestPostgreSQLSetupInitialization:
    """Test PostgreSQLSetup class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()

    def test_init_with_valid_parameters(self):
        """Test initialization with valid parameters."""
        pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

        assert pg_setup.host == "localhost"
        assert pg_setup.port == 5432
        assert pg_setup.database == "promptvault"
        assert pg_setup.user == "testuser"
        assert pg_setup.console == self.console

    def test_init_with_custom_host_port(self):
        """Test initialization with custom host and port."""
        pg_setup = PostgreSQLSetup(
            host="192.168.1.100",
            port=5433,
            database="testdb",
            user="testuser",
            console=self.console,
        )

        assert pg_setup.host == "192.168.1.100"
        assert pg_setup.port == 5433


class TestPostgreSQLSetupCheckServer:
    """Test PostgreSQL server connectivity checking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

    @patch("subprocess.run")
    def test_check_server_success_with_pg_isready(self, mock_run):
        """Test successful server check using pg_isready."""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.pg_setup.check_server()

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "pg_isready"
        assert "-h" in args
        assert "localhost" in args

    @patch("subprocess.run")
    def test_check_server_failure(self, mock_run):
        """Test server check failure."""
        mock_run.return_value = MagicMock(returncode=1)

        result = self.pg_setup.check_server()

        assert result is False

    @patch("subprocess.run")
    def test_check_server_pg_isready_not_found_fallback_to_psql(self, mock_run):
        """Test fallback to psql when pg_isready not found."""
        # First call (pg_isready) raises FileNotFoundError
        # Second call (psql) succeeds
        mock_run.side_effect = [
            FileNotFoundError("pg_isready not found"),
            MagicMock(returncode=0, stderr=""),
        ]

        result = self.pg_setup.check_server()

        assert result is True
        assert mock_run.call_count == 2

    @patch("subprocess.run")
    def test_check_server_timeout(self, mock_run):
        """Test server check timeout handling."""
        mock_run.side_effect = [
            subprocess.TimeoutExpired("pg_isready", 5),
            subprocess.TimeoutExpired("psql", 5),
        ]

        result = self.pg_setup.check_server()

        assert result is False


class TestPostgreSQLSetupCreateDatabase:
    """Test PostgreSQL database and user creation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

    @patch("subprocess.run")
    def test_create_database_success(self, mock_run):
        """Test successful database and user creation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is True
        # Should be called 4 times: create user, create db, grant privileges, grant schema
        assert mock_run.call_count == 4

    @patch("subprocess.run")
    def test_create_database_user_creation_failure(self, mock_run):
        """Test handling of user creation failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="ERROR: permission denied"
        )

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is False
        self.console.error.assert_called()

    @patch("subprocess.run")
    def test_create_database_already_exists(self, mock_run):
        """Test handling when database already exists."""
        # User creation succeeds, database creation shows "already exists"
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),  # user creation
            MagicMock(returncode=1, stderr="already exists"),  # db creation
            MagicMock(returncode=0, stderr=""),  # grant privileges
            MagicMock(returncode=0, stderr=""),  # grant schema
        ]

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is True

    @patch("subprocess.run")
    def test_create_database_timeout(self, mock_run):
        """Test handling of database creation timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("psql", 10)

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is False
        self.console.error.assert_called()

    @patch("subprocess.run")
    def test_create_database_environment_variable(self, mock_run):
        """Test that PGPASSWORD is set correctly in environment."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        self.pg_setup.create_database(admin_password="admin123", db_password="user123")

        # Check that PGPASSWORD was set in env
        for call_item in mock_run.call_args_list:
            env = call_item[1].get("env", {})
            if env:
                assert "PGPASSWORD" in env

    @patch("subprocess.run")
    def test_create_database_grant_privileges_failure(self, mock_run):
        """Test handling when granting privileges fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),  # user creation
            MagicMock(returncode=0, stderr=""),  # db creation
            MagicMock(
                returncode=1, stderr="ERROR: permission denied"
            ),  # grant privileges
        ]

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is False
        self.console.error.assert_called()

    @patch("subprocess.run")
    def test_create_database_schema_grant_failure_warning(self, mock_run):
        """Test that schema grant failure produces warning, not error."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),  # user creation
            MagicMock(returncode=0, stderr=""),  # db creation
            MagicMock(returncode=0, stderr=""),  # grant privileges
            MagicMock(returncode=1, stderr="ERROR: permission denied"),  # grant schema
        ]

        result = self.pg_setup.create_database(
            admin_password="admin123", db_password="user123"
        )

        assert result is True
        self.console.warning.assert_called()


class TestPostgreSQLSetupTestConnection:
    """Test PostgreSQL connection testing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

    @patch("subprocess.run")
    def test_connection_success(self, mock_run):
        """Test successful database connection."""
        mock_run.return_value = MagicMock(returncode=0)

        result = self.pg_setup.test_connection(password="user123")

        assert result is True
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_connection_failure(self, mock_run):
        """Test failed database connection."""
        mock_run.return_value = MagicMock(returncode=1)

        result = self.pg_setup.test_connection(password="wrongpass")

        assert result is False

    @patch("subprocess.run")
    def test_connection_timeout(self, mock_run):
        """Test connection timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("psql", 5)

        result = self.pg_setup.test_connection(password="user123")

        assert result is False

    @patch("subprocess.run")
    def test_connection_exception(self, mock_run):
        """Test connection exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = self.pg_setup.test_connection(password="user123")

        assert result is False


class TestPostgreSQLSetupRunMigrations:
    """Test PostgreSQL Alembic migration execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_success(self, mock_run, mock_chdir):
        """Test successful migration execution."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = self.pg_setup.run_migrations()

        assert result is True
        mock_chdir.assert_called_once()
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "alembic"
        assert args[1] == "upgrade"
        assert args[2] == "head"

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_failure(self, mock_run, mock_chdir):
        """Test migration failure handling."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="ERROR: Migration failed"
        )

        result = self.pg_setup.run_migrations()

        assert result is False
        self.console.error.assert_called()

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_timeout(self, mock_run, mock_chdir):
        """Test migration timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("alembic", 60)

        result = self.pg_setup.run_migrations()

        assert result is False
        self.console.error.assert_called()

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_exception(self, mock_run, mock_chdir):
        """Test migration exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        result = self.pg_setup.run_migrations()

        assert result is False
        self.console.error.assert_called()


class TestPostgreSQLSetupVerifySchema:
    """Test PostgreSQL schema verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.pg_setup = PostgreSQLSetup(
            host="localhost",
            port=5432,
            database="promptvault",
            user="testuser",
            console=self.console,
        )

    @patch("subprocess.run")
    def test_verify_schema_success(self, mock_run):
        """Test successful schema verification."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="users\nprompts\ntags\ncategories\n"
        )

        tables = self.pg_setup.verify_schema()

        assert len(tables) == 4
        assert "users" in tables
        assert "prompts" in tables
        assert "tags" in tables
        assert "categories" in tables

    @patch("subprocess.run")
    def test_verify_schema_empty_database(self, mock_run):
        """Test schema verification with empty database."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        tables = self.pg_setup.verify_schema()

        assert len(tables) == 0

    @patch("subprocess.run")
    def test_verify_schema_failure(self, mock_run):
        """Test schema verification failure."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="ERROR: connection failed"
        )

        tables = self.pg_setup.verify_schema()

        assert len(tables) == 0
        self.console.error.assert_called()

    @patch("subprocess.run")
    def test_verify_schema_exception(self, mock_run):
        """Test schema verification exception handling."""
        mock_run.side_effect = Exception("Unexpected error")

        tables = self.pg_setup.verify_schema()

        assert len(tables) == 0
        self.console.error.assert_called()

    @patch("subprocess.run")
    def test_verify_schema_with_whitespace(self, mock_run):
        """Test schema verification handles whitespace correctly."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="  users  \n  prompts  \n\n  tags  \n"
        )

        tables = self.pg_setup.verify_schema()

        assert len(tables) == 3
        assert "users" in tables
        assert "prompts" in tables
        assert "tags" in tables


class TestSQLiteSetupInitialization:
    """Test SQLiteSetup class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()

    def test_init_with_valid_path(self):
        """Test initialization with valid database path."""
        sqlite_setup = SQLiteSetup(path="./data/promptvault.db", console=self.console)

        assert sqlite_setup.path == Path("./data/promptvault.db")
        assert sqlite_setup.console == self.console

    def test_init_with_absolute_path(self):
        """Test initialization with absolute path."""
        sqlite_setup = SQLiteSetup(path="/tmp/test.db", console=self.console)

        assert sqlite_setup.path == Path("/tmp/test.db")


class TestSQLiteSetupCreateDatabase:
    """Test SQLite database file creation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_database_new_file(self):
        """Test creating a new database file."""
        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)

        result = sqlite_setup.create_database()

        assert result is True
        assert os.path.exists(self.db_path)
        self.console.success.assert_called()

    def test_create_database_existing_file(self):
        """Test handling of existing database file."""
        # Create file first
        Path(self.db_path).touch()

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        result = sqlite_setup.create_database()

        assert result is True
        self.console.info.assert_called()

    def test_create_database_with_subdirectories(self):
        """Test creating database with nested parent directories."""
        nested_path = os.path.join(self.temp_dir, "sub1", "sub2", "test.db")
        sqlite_setup = SQLiteSetup(path=nested_path, console=self.console)

        result = sqlite_setup.create_database()

        assert result is True
        assert os.path.exists(nested_path)

    @patch("pathlib.Path.touch")
    def test_create_database_permission_error(self, mock_touch):
        """Test handling of permission errors."""
        mock_touch.side_effect = PermissionError("Permission denied")

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        result = sqlite_setup.create_database()

        assert result is False
        self.console.error.assert_called()

    @patch("pathlib.Path.mkdir")
    def test_create_database_general_exception(self, mock_mkdir):
        """Test handling of general exceptions."""
        mock_mkdir.side_effect = Exception("Unexpected error")

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        result = sqlite_setup.create_database()

        assert result is False
        self.console.error.assert_called()


class TestSQLiteSetupRunMigrations:
    """Test SQLite Alembic migration execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.sqlite_setup = SQLiteSetup(path="./data/test.db", console=self.console)

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_success(self, mock_run, mock_chdir):
        """Test successful migration execution."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        result = self.sqlite_setup.run_migrations()

        assert result is True
        mock_chdir.assert_called_once()
        mock_run.assert_called_once()

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_failure(self, mock_run, mock_chdir):
        """Test migration failure handling."""
        mock_run.return_value = MagicMock(
            returncode=1, stderr="ERROR: Migration failed"
        )

        result = self.sqlite_setup.run_migrations()

        assert result is False
        self.console.error.assert_called()

    @patch("os.chdir")
    @patch("subprocess.run")
    def test_migrations_timeout(self, mock_run, mock_chdir):
        """Test migration timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("alembic", 60)

        result = self.sqlite_setup.run_migrations()

        assert result is False
        self.console.error.assert_called()


class TestSQLiteSetupVerifySchema:
    """Test SQLite schema verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_verify_schema_success(self):
        """Test successful schema verification."""
        import sqlite3

        # Create database with tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        cursor.execute("CREATE TABLE prompts (id INTEGER PRIMARY KEY)")
        cursor.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        tables = sqlite_setup.verify_schema()

        assert len(tables) == 3
        assert "users" in tables
        assert "prompts" in tables
        assert "tags" in tables

    def test_verify_schema_file_not_found(self):
        """Test schema verification with non-existent file."""
        sqlite_setup = SQLiteSetup(path="/nonexistent/test.db", console=self.console)
        tables = sqlite_setup.verify_schema()

        assert len(tables) == 0
        self.console.error.assert_called()

    def test_verify_schema_empty_database(self):
        """Test schema verification with empty database."""
        import sqlite3

        # Create empty database
        conn = sqlite3.connect(self.db_path)
        conn.close()

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        tables = sqlite_setup.verify_schema()

        assert len(tables) == 0

    def test_verify_schema_excludes_sqlite_internal_tables(self):
        """Test that sqlite internal tables are excluded."""
        import sqlite3

        # Create database with user table and sqlite internal tables
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        # sqlite_master and sqlite_sequence are internal
        conn.commit()
        conn.close()

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        tables = sqlite_setup.verify_schema()

        # Should not include sqlite_ prefixed tables
        for table in tables:
            assert not table.startswith("sqlite_")

    @patch("sqlite3.connect")
    def test_verify_schema_exception(self, mock_connect):
        """Test schema verification exception handling."""
        mock_connect.side_effect = Exception("Database error")

        sqlite_setup = SQLiteSetup(path=self.db_path, console=self.console)
        tables = sqlite_setup.verify_schema()

        assert len(tables) == 0
        self.console.error.assert_called()


class TestUpdateEnvFile:
    """Test environment file update functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.env_path = os.path.join(self.temp_dir, ".env")

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch(
        "scripts.setup.setup_database.project_root",
        new_callable=lambda: tempfile.mkdtemp(),
    )
    def test_update_env_file_create_new(self, mock_project_root):
        """Test creating new .env file."""
        # Temporarily override project_root
        import scripts.setup.setup_database as sdb

        original_root = sdb.project_root
        sdb.project_root = Path(self.temp_dir)

        try:
            database_url = "postgresql://user:pass@localhost/db"
            update_env_file(database_url)

            env_path = Path(self.temp_dir) / ".env"
            assert env_path.exists()

            with open(env_path) as f:
                content = f.read()
            assert "DATABASE_URL=postgresql://user:pass@localhost/db" in content
        finally:
            sdb.project_root = original_root

    def test_update_env_file_update_existing(self):
        """Test updating existing .env file."""
        import scripts.setup.setup_database as sdb

        original_root = sdb.project_root
        sdb.project_root = Path(self.temp_dir)

        try:
            # Create existing .env
            env_path = Path(self.temp_dir) / ".env"
            with open(env_path, "w") as f:
                f.write("DATABASE_URL=old_url\n")
                f.write("OTHER_VAR=value\n")

            new_url = "postgresql://user:pass@localhost/newdb"
            update_env_file(new_url)

            with open(env_path) as f:
                content = f.read()

            assert f"DATABASE_URL={new_url}" in content
            assert "OTHER_VAR=value" in content
        finally:
            sdb.project_root = original_root

    def test_update_env_file_add_to_existing(self):
        """Test adding DATABASE_URL to existing .env without it."""
        import scripts.setup.setup_database as sdb

        original_root = sdb.project_root
        sdb.project_root = Path(self.temp_dir)

        try:
            # Create .env without DATABASE_URL
            env_path = Path(self.temp_dir) / ".env"
            with open(env_path, "w") as f:
                f.write("OTHER_VAR=value\n")

            new_url = "sqlite:///data/test.db"
            update_env_file(new_url)

            with open(env_path) as f:
                content = f.read()

            assert f"DATABASE_URL={new_url}" in content
            assert "OTHER_VAR=value" in content
        finally:
            sdb.project_root = original_root


class TestCreateAdminUser:
    """Test admin user creation integration."""

    @patch("subprocess.run")
    def test_create_admin_user_success(self, mock_run):
        """Test successful admin user creation."""
        mock_run.return_value = MagicMock(returncode=0)

        # Should not raise exception
        create_admin_user()

        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "create_admin_user.py" in args[1]

    @patch("subprocess.run")
    def test_create_admin_user_failure(self, mock_run):
        """Test admin user creation failure."""
        mock_run.return_value = MagicMock(returncode=1)

        with pytest.raises(SystemExit) as exc_info:
            create_admin_user()

        assert exc_info.value.code == 1

    @patch("subprocess.run")
    def test_create_admin_user_exception(self, mock_run):
        """Test admin user creation exception handling."""
        mock_run.side_effect = Exception("Script not found")

        with pytest.raises(SystemExit) as exc_info:
            create_admin_user()

        assert exc_info.value.code == 1


class TestMainCLI:
    """Test main CLI function and argument parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("scripts.setup.setup_database.setup_postgresql")
    @patch("scripts.setup.setup_database.db_settings")
    def test_main_with_postgresql_type(self, mock_db_settings, mock_setup_pg):
        """Test main with --type postgresql."""
        mock_db_settings.database_type = "postgresql"

        self.runner.invoke(
            main, ["--type", "postgresql", "--non-interactive", "--migrate-only"]
        )

        mock_setup_pg.assert_called_once()

    @patch("scripts.setup.setup_database.setup_sqlite")
    @patch("scripts.setup.setup_database.db_settings")
    def test_main_with_sqlite_type(self, mock_db_settings, mock_setup_sqlite):
        """Test main with --type sqlite."""
        mock_db_settings.database_type = "sqlite"

        self.runner.invoke(
            main, ["--type", "sqlite", "--non-interactive", "--migrate-only"]
        )

        mock_setup_sqlite.assert_called_once()

    @patch("scripts.setup.setup_database.db_settings")
    def test_main_migrate_only_uses_current_db_type(self, mock_db_settings):
        """Test --migrate-only uses current DATABASE_URL type."""
        mock_db_settings.database_type = "postgresql"

        with patch("scripts.setup.setup_database.setup_postgresql") as mock_setup:
            self.runner.invoke(main, ["--migrate-only"])
            mock_setup.assert_called_once()

    def test_main_non_interactive_requires_type(self):
        """Test that non-interactive mode requires --type."""
        result = self.runner.invoke(main, ["--non-interactive"])

        assert result.exit_code != 0

    @patch("scripts.setup.setup_database.db_settings")
    def test_main_unknown_database_type_error(self, mock_db_settings):
        """Test error handling for unknown database type."""
        mock_db_settings.database_type = "unknown"
        mock_db_settings.DATABASE_URL = "invalid://url"

        result = self.runner.invoke(main, ["--migrate-only"])

        assert result.exit_code == 1

    @patch("scripts.setup.setup_database.setup_postgresql")
    @patch("scripts.setup.setup_database.db_settings")
    def test_main_with_host_port_database_user_flags(
        self, mock_db_settings, mock_setup
    ):
        """Test main with custom host, port, database, and user."""
        mock_db_settings.database_type = "postgresql"

        self.runner.invoke(
            main,
            [
                "--type",
                "postgresql",
                "--host",
                "192.168.1.100",
                "--port",
                "5433",
                "--database",
                "testdb",
                "--user",
                "testuser",
                "--migrate-only",
            ],
        )

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args
        # Check that custom values were passed
        assert call_args[0][1] == "192.168.1.100"  # host
        assert call_args[0][2] == 5433  # port
        assert call_args[0][3] == "testdb"  # database
        assert call_args[0][4] == "testuser"  # user

    @patch("scripts.setup.setup_database.setup_postgresql")
    @patch("scripts.setup.setup_database.db_settings")
    def test_main_with_create_admin_flag(self, mock_db_settings, mock_setup):
        """Test main with --create-admin flag."""
        mock_db_settings.database_type = "postgresql"

        self.runner.invoke(
            main, ["--type", "postgresql", "--migrate-only", "--create-admin"]
        )

        mock_setup.assert_called_once()
        call_args = mock_setup.call_args
        assert call_args[0][6] is True  # create_admin


class TestSetupPostgreSQL:
    """Test setup_postgresql function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        # Mock spinner context manager
        spinner_mock = MagicMock()
        spinner_mock.__enter__ = Mock()
        spinner_mock.__exit__ = Mock(return_value=False)
        self.console.spinner = Mock(return_value=spinner_mock)
        # Mock other console methods
        self.console.step = Mock()
        self.console.success = Mock()
        self.console.info = Mock()
        self.console.error = Mock()
        self.console.table = Mock()

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    def test_setup_postgresql_migrate_only(self, mock_create_admin, mock_pg_class):
        """Test PostgreSQL setup with migrate_only flag."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = True
        mock_pg_instance.verify_schema.return_value = ["users", "prompts"]
        mock_pg_class.return_value = mock_pg_instance

        setup_postgresql(
            console=self.console,
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            migrate_only=True,
            create_admin=False,
            non_interactive=False,
        )

        mock_pg_instance.run_migrations.assert_called_once()
        mock_pg_instance.verify_schema.assert_called_once()
        mock_create_admin.assert_not_called()

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    def test_setup_postgresql_with_admin_creation(
        self, mock_create_admin, mock_pg_class
    ):
        """Test PostgreSQL setup with admin user creation."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = True
        mock_pg_instance.verify_schema.return_value = ["users", "prompts"]
        mock_pg_class.return_value = mock_pg_instance

        setup_postgresql(
            console=self.console,
            host="localhost",
            port=5432,
            database="testdb",
            user="testuser",
            migrate_only=True,
            create_admin=True,
            non_interactive=False,
        )

        mock_create_admin.assert_called_once()

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    def test_setup_postgresql_migration_failure_exits(self, mock_pg_class):
        """Test that migration failure causes system exit."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = False
        mock_pg_class.return_value = mock_pg_instance

        with pytest.raises(SystemExit):
            setup_postgresql(
                console=self.console,
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                migrate_only=True,
                create_admin=False,
                non_interactive=False,
            )

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    def test_setup_postgresql_no_tables_exits(self, mock_pg_class):
        """Test that zero tables causes system exit."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = True
        mock_pg_instance.verify_schema.return_value = []
        mock_pg_class.return_value = mock_pg_instance

        with pytest.raises(SystemExit):
            setup_postgresql(
                console=self.console,
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                migrate_only=True,
                create_admin=False,
                non_interactive=False,
            )

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    @patch("scripts.setup.setup_database.update_env_file")
    def test_setup_postgresql_full_workflow_non_interactive_fails(
        self, mock_update_env, mock_pg_class
    ):
        """Test that full setup in non-interactive mode fails."""
        mock_pg_instance = MagicMock()
        mock_pg_class.return_value = mock_pg_instance

        with pytest.raises(SystemExit):
            setup_postgresql(
                console=self.console,
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                migrate_only=False,
                create_admin=False,
                non_interactive=True,
            )


class TestSetupSQLite:
    """Test setup_sqlite function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        # Mock spinner context manager
        spinner_mock = MagicMock()
        spinner_mock.__enter__ = Mock()
        spinner_mock.__exit__ = Mock(return_value=False)
        self.console.spinner = Mock(return_value=spinner_mock)
        # Mock other console methods
        self.console.step = Mock()
        self.console.success = Mock()
        self.console.info = Mock()
        self.console.error = Mock()
        self.console.table = Mock()
        self.console.prompt = Mock(return_value="./data/test.db")

    @patch("scripts.setup.setup_database.SQLiteSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    @patch("scripts.setup.setup_database.db_settings")
    def test_setup_sqlite_migrate_only(
        self, mock_db_settings, mock_create_admin, mock_sqlite_class
    ):
        """Test SQLite setup with migrate_only flag."""
        mock_db_settings.DATABASE_URL = "sqlite:///data/test.db"
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.run_migrations.return_value = True
        mock_sqlite_instance.verify_schema.return_value = ["users", "prompts"]
        mock_sqlite_class.return_value = mock_sqlite_instance

        setup_sqlite(
            console=self.console,
            migrate_only=True,
            create_admin=False,
            non_interactive=False,
        )

        mock_sqlite_instance.run_migrations.assert_called_once()
        mock_sqlite_instance.verify_schema.assert_called_once()
        mock_create_admin.assert_not_called()

    @patch("scripts.setup.setup_database.SQLiteSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    @patch("scripts.setup.setup_database.update_env_file")
    def test_setup_sqlite_full_workflow_non_interactive(
        self, mock_update_env, mock_create_admin, mock_sqlite_class
    ):
        """Test full SQLite setup in non-interactive mode."""
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.path = Mock()
        mock_sqlite_instance.path.absolute.return_value = "/tmp/test.db"
        mock_sqlite_instance.create_database.return_value = True
        mock_sqlite_instance.run_migrations.return_value = True
        mock_sqlite_instance.verify_schema.return_value = ["users", "prompts"]
        mock_sqlite_class.return_value = mock_sqlite_instance

        setup_sqlite(
            console=self.console,
            migrate_only=False,
            create_admin=False,
            non_interactive=True,
        )

        mock_sqlite_instance.create_database.assert_called_once()
        mock_update_env.assert_called_once()

    @patch("scripts.setup.setup_database.SQLiteSetup")
    def test_setup_sqlite_create_database_failure_exits(self, mock_sqlite_class):
        """Test that database creation failure causes system exit."""
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.create_database.return_value = False
        mock_sqlite_class.return_value = mock_sqlite_instance

        with pytest.raises(SystemExit):
            setup_sqlite(
                console=self.console,
                migrate_only=False,
                create_admin=False,
                non_interactive=True,
            )

    @patch("scripts.setup.setup_database.SQLiteSetup")
    def test_setup_sqlite_migration_failure_exits(self, mock_sqlite_class):
        """Test that migration failure causes system exit."""
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.run_migrations.return_value = False
        mock_sqlite_class.return_value = mock_sqlite_instance

        with pytest.raises(SystemExit):
            setup_sqlite(
                console=self.console,
                migrate_only=True,
                create_admin=False,
                non_interactive=False,
            )


class TestIntegrationWorkflows:
    """Test complete integration workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    def test_postgresql_migrate_only_workflow(self, mock_create_admin, mock_pg_class):
        """Test complete PostgreSQL migrate-only workflow."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = True
        mock_pg_instance.verify_schema.return_value = [
            "users",
            "prompts",
            "tags",
            "categories",
        ]
        mock_pg_class.return_value = mock_pg_instance

        with patch("scripts.setup.setup_database.db_settings") as mock_db:
            mock_db.database_type = "postgresql"
            result = self.runner.invoke(main, ["--migrate-only"])

            assert result.exit_code == 0

    @patch("scripts.setup.setup_database.SQLiteSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    @patch("scripts.setup.setup_database.update_env_file")
    def test_sqlite_full_setup_workflow(
        self, mock_update_env, mock_create_admin, mock_sqlite_class
    ):
        """Test complete SQLite setup workflow."""
        mock_sqlite_instance = MagicMock()
        mock_sqlite_instance.path = Mock()
        mock_sqlite_instance.path.absolute.return_value = "/tmp/test.db"
        mock_sqlite_instance.create_database.return_value = True
        mock_sqlite_instance.run_migrations.return_value = True
        mock_sqlite_instance.verify_schema.return_value = [
            "users",
            "prompts",
            "tags",
            "categories",
        ]
        mock_sqlite_class.return_value = mock_sqlite_instance

        result = self.runner.invoke(main, ["--type", "sqlite", "--non-interactive"])

        assert result.exit_code == 0
        mock_sqlite_instance.create_database.assert_called_once()
        mock_sqlite_instance.run_migrations.assert_called_once()
        mock_sqlite_instance.verify_schema.assert_called_once()

    @patch("scripts.setup.setup_database.PostgreSQLSetup")
    @patch("scripts.setup.setup_database.create_admin_user")
    def test_postgresql_with_admin_creation_workflow(
        self, mock_create_admin, mock_pg_class
    ):
        """Test PostgreSQL setup with admin user creation."""
        mock_pg_instance = MagicMock()
        mock_pg_instance.run_migrations.return_value = True
        mock_pg_instance.verify_schema.return_value = ["users", "prompts"]
        mock_pg_class.return_value = mock_pg_instance

        with patch("scripts.setup.setup_database.db_settings") as mock_db:
            mock_db.database_type = "postgresql"
            result = self.runner.invoke(main, ["--migrate-only", "--create-admin"])

            assert result.exit_code == 0
            mock_create_admin.assert_called_once()
