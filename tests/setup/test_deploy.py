# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for deployment orchestration script.

Tests cover:
- DeploymentOrchestrator initialization
- Pre-flight checks (Docker, ports, config validation)
- Phase 1: Preparation (backup, image pull/build)
- Phase 2: Infrastructure (database, Redis startup)
- Phase 3: Migrations (Alembic execution)
- Phase 4: Application (web service startup)
- Phase 5: Verification (smoke tests, access info)
- Rollback functionality
- Dry run mode
- CLI integration and flags
- Error handling and recovery
- State persistence
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call
from click.testing import CliRunner
import tempfile

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from scripts.setup.deploy import DeploymentOrchestrator, main


class TestDeploymentOrchestratorInit:
    """Test DeploymentOrchestrator initialization."""

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        console = Mock()
        orchestrator = DeploymentOrchestrator(console=console)

        assert orchestrator.console == console
        assert orchestrator.dry_run is False
        assert orchestrator.skip_backup is False
        assert orchestrator.skip_migrations is False
        assert orchestrator.rebuild is False
        assert orchestrator.non_interactive is False
        assert orchestrator.working_dir is not None
        assert orchestrator.backup_file is None
        assert orchestrator.previous_containers == {}
        assert orchestrator.deployment_start_time is None
        assert orchestrator.phases_completed == []

    def test_initialization_with_options(self):
        """Test initialization with custom options."""
        console = Mock()
        working_dir = Path("/tmp/test")

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True,
            skip_backup=True,
            skip_migrations=True,
            rebuild=True,
            non_interactive=True,
            working_dir=working_dir
        )

        assert orchestrator.dry_run is True
        assert orchestrator.skip_backup is True
        assert orchestrator.skip_migrations is True
        assert orchestrator.rebuild is True
        assert orchestrator.non_interactive is True
        assert orchestrator.working_dir == working_dir


class TestPreflightChecks:
    """Test pre-flight checks before deployment."""

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    def test_preflight_checks_all_pass(
        self, mock_port, mock_compose, mock_running, mock_installed
    ):
        """Test pre-flight checks when all checks pass."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_installed.return_value = (True, "20.10.0")
        mock_running.return_value = (True, "")
        mock_compose.return_value = (True, "v2.0.0")
        mock_port.return_value = (True, "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            # Create necessary files
            (working_dir / "docker-compose.yml").touch()
            (working_dir / "secrets" / "jwt").mkdir(parents=True)
            (working_dir / "secrets" / "jwt" / "private_key.pem").write_text(
                "-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----"
            )
            (working_dir / "secrets" / "jwt" / "public_key.pem").write_text(
                "-----BEGIN PUBLIC KEY-----\n" + "A" * 200 + "\n-----END PUBLIC KEY-----"
            )
            # Create .env file with DATABASE_URL (required by preflight checks)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.run_preflight_checks()

            assert result is True
            mock_installed.assert_called_once()
            mock_running.assert_called_once()
            mock_compose.assert_called_once()

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    def test_preflight_checks_docker_not_installed(
        self, mock_compose, mock_running, mock_installed
    ):
        """Test pre-flight checks when Docker is not installed."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_installed.return_value = (False, "not found")
        mock_running.return_value = (False, "Docker daemon not running")
        mock_compose.return_value = (False, "not found")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.run_preflight_checks()

            assert result is False

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    def test_preflight_checks_missing_compose_file(
        self, mock_port, mock_compose, mock_running, mock_installed
    ):
        """Test pre-flight checks when docker-compose.yml is missing."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_installed.return_value = (True, "20.10.0")
        mock_running.return_value = (True, "")
        mock_compose.return_value = (True, "v2.0.0")
        mock_port.return_value = (True, "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.run_preflight_checks()

            assert result is False

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    def test_preflight_checks_low_disk_space_fails(
        self, mock_port, mock_compose, mock_running, mock_installed
    ):
        """Test pre-flight checks fail when disk space is insufficient."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_installed.return_value = (True, "20.10.0")
        mock_running.return_value = (True, "")
        mock_compose.return_value = (True, "v2.0.0")
        mock_port.return_value = (True, "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            (working_dir / "docker-compose.yml").touch()
            (working_dir / "secrets" / "jwt").mkdir(parents=True)
            (working_dir / "secrets" / "jwt" / "private_key.pem").write_text(
                "-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----"
            )
            (working_dir / "secrets" / "jwt" / "public_key.pem").write_text(
                "-----BEGIN PUBLIC KEY-----\n" + "A" * 200 + "\n-----END PUBLIC KEY-----"
            )
            # Create .env file with DATABASE_URL (required by preflight checks)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            with patch.object(orchestrator, "_check_disk_space", return_value=0.5):
                result = orchestrator.run_preflight_checks()

            assert result is False


class TestPhase1Preparation:
    """Test Phase 1: Preparation."""

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.subprocess.run')
    def test_phase1_preparation_success(
        self, mock_subprocess, mock_compose, mock_status
    ):
        """Test successful Phase 1 execution."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_status.return_value = "running"
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="SQL backup",
            stderr=""
        )
        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            (working_dir / "data" / "backups").mkdir(parents=True)
            # Create .env file with DATABASE_URL (required for backup operations)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()

            result = orchestrator.phase1_preparation()

            assert result is True
            assert "preparation" in orchestrator.phases_completed

    def test_phase1_preparation_skip_backup(self):
        """Test Phase 1 with --skip-backup flag."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        with patch('scripts.setup.deploy.run_docker_compose') as mock_compose:
            mock_compose.return_value = (True, "", "")

            with tempfile.TemporaryDirectory() as tmpdir:
                working_dir = Path(tmpdir)

                orchestrator = DeploymentOrchestrator(
                    console=console,
                    skip_backup=True,
                    working_dir=working_dir
                )

                with patch('scripts.setup.deploy.get_container_status') as mock_status:
                    mock_status.return_value = "not running"

                    result = orchestrator.phase1_preparation()

                    assert result is True
                    console.info.assert_any_call("Skipping backup (--skip-backup flag)")

    def test_phase1_preparation_dry_run(self):
        """Test Phase 1 in dry-run mode."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        with patch('scripts.setup.deploy.get_container_status') as mock_status:
            mock_status.return_value = "not running"

            with tempfile.TemporaryDirectory() as tmpdir:
                working_dir = Path(tmpdir)

                orchestrator = DeploymentOrchestrator(
                    console=console,
                    dry_run=True,
                    working_dir=working_dir
                )

                result = orchestrator.phase1_preparation()

                assert result is True
                assert orchestrator.backup_file is None

    def test_phase1_preparation_backup_failure(self):
        """Test Phase 1 when backup creation fails."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            orchestrator._create_backup = Mock(return_value=False)

            result = orchestrator.phase1_preparation()

            assert result is False
            console.error.assert_any_call("Backup failed")

    def test_phase1_preparation_image_failure(self):
        """Test Phase 1 when pull/build images fails."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            orchestrator._create_backup = Mock(return_value=True)
            orchestrator._save_container_states = Mock()
            orchestrator._pull_or_build_images = Mock(return_value=False)

            result = orchestrator.phase1_preparation()

            assert result is False
            console.error.assert_any_call("Failed to pull/build images")


class TestPhase2Infrastructure:
    """Test Phase 2: Infrastructure."""

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase2_infrastructure_success(
        self, mock_compose, mock_wait
    ):
        """Test successful Phase 2 execution."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_wait.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase2_infrastructure()

            assert result is True
            assert "infrastructure" in orchestrator.phases_completed

            # Verify services were started
            calls = mock_compose.call_args_list
            assert any("db" in str(call) for call in calls)
            assert any("redis" in str(call) for call in calls)

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_logs')
    def test_phase2_infrastructure_db_unhealthy(
        self, mock_logs, mock_compose, mock_wait
    ):
        """Test Phase 2 when database fails health check."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_wait.return_value = False
        mock_logs.return_value = "Database error logs"

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase2_infrastructure()

            assert result is False
            assert "infrastructure" not in orchestrator.phases_completed


class TestPhase3Migrations:
    """Test Phase 3: Migrations."""

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_success(
        self, mock_compose, mock_subprocess
    ):
        """Test successful Phase 3 execution."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "1", "")
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="Running upgrade\nDone",
            stderr=""
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            # Create .env file with DATABASE_URL (required for migrations)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()

            result = orchestrator.phase3_migrations()

            assert result is True
            assert "migrations" in orchestrator.phases_completed

    def test_phase3_migrations_skip(self):
        """Test Phase 3 with --skip-migrations flag."""
        console = Mock()

        orchestrator = DeploymentOrchestrator(
            console=console,
            skip_migrations=True
        )

        result = orchestrator.phase3_migrations()

        assert result is True
        assert "migrations" in orchestrator.phases_completed
        console.info.assert_called_with("Skipping migrations (--skip-migrations flag)")

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_failure(
        self, mock_compose, mock_subprocess
    ):
        """Test Phase 3 when migrations fail."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "1", "")
        mock_subprocess.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Migration error"
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase3_migrations()

            assert result is False

    def test_phase3_migrations_dry_run(self):
        """Test Phase 3 in dry-run mode."""
        console = Mock()

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True
        )

        result = orchestrator.phase3_migrations()

        assert result is True
        console.info.assert_called_with("[DRY RUN] Would run: alembic upgrade head")


class TestPhase4Application:
    """Test Phase 4: Application."""

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase4_application_success(
        self, mock_compose, mock_wait
    ):
        """Test successful Phase 4 execution."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_wait.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase4_application()

            assert result is True
            assert "application" in orchestrator.phases_completed

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_logs')
    def test_phase4_application_unhealthy(
        self, mock_logs, mock_compose, mock_wait
    ):
        """Test Phase 4 when application fails health check."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_wait.return_value = False
        mock_logs.return_value = "Application error logs"

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase4_application()

            assert result is False


class TestPhase5Verification:
    """Test Phase 5: Verification."""

    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase5_verification_success(self, mock_compose, mock_httpx_get):
        """Test successful Phase 5 execution."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")

        # Mock httpx.get response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            assert result is True
            assert "verification" in orchestrator.phases_completed

    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase5_verification_smoke_tests_fail(self, mock_compose, mock_httpx_get):
        """Test Phase 5 when smoke tests fail (non-critical)."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (False, "", "Error")

        # Mock httpx to fail
        mock_httpx_get.side_effect = Exception("Connection failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            # Phase still succeeds even if smoke tests fail
            assert result is True


class TestRollback:
    """Test rollback functionality."""

    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.subprocess.run')
    def test_rollback_success(self, mock_subprocess, mock_compose):
        """Test successful rollback."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"
            # Create .env file with DATABASE_URL (required for rollback)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()
            orchestrator.backup_file = backup_file

            result = orchestrator.rollback()

            assert result is True

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_no_backup(self, mock_compose):
        """Test rollback when no backup exists."""
        console = Mock()

        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.rollback()

            # Should still succeed but warn about no backup
            assert result is True
            console.warning.assert_called_with("No backup file to restore from")

    def test_rollback_dry_run(self):
        """Test rollback in dry-run mode."""
        console = Mock()

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True
        )

        # Mock the internal methods
        orchestrator._stop_all_services = Mock(return_value=True)
        orchestrator._start_all_services = Mock(return_value=True)
        orchestrator._restore_backup = Mock(return_value=True)

        result = orchestrator.rollback()

        assert result is True


class TestHelperMethods:
    """Test helper methods."""

    def test_check_disk_space(self):
        """Test disk space checking."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            disk_space = orchestrator._check_disk_space()

            assert isinstance(disk_space, float)
            assert disk_space > 0

    def test_validate_jwt_keys_valid(self):
        """Test JWT key validation with valid keys."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            jwt_dir = working_dir / "secrets" / "jwt"
            jwt_dir.mkdir(parents=True)

            private_key = jwt_dir / "private_key.pem"
            public_key = jwt_dir / "public_key.pem"

            private_key.write_text(
                "-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----"
            )
            public_key.write_text(
                "-----BEGIN PUBLIC KEY-----\n" + "A" * 200 + "\n-----END PUBLIC KEY-----"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is True

    def test_validate_jwt_keys_invalid(self):
        """Test JWT key validation with invalid keys."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            jwt_dir = working_dir / "secrets" / "jwt"
            jwt_dir.mkdir(parents=True)

            private_key = jwt_dir / "private_key.pem"
            public_key = jwt_dir / "public_key.pem"

            # Write invalid content (too short)
            private_key.write_text("invalid")
            public_key.write_text("invalid")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is False

    def test_validate_jwt_keys_missing_headers(self):
        """Test JWT key validation when PEM headers are missing."""
        console = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            jwt_dir = working_dir / "secrets" / "jwt"
            jwt_dir.mkdir(parents=True)

            private_key = jwt_dir / "private_key.pem"
            public_key = jwt_dir / "public_key.pem"

            private_key.write_text("A" * 200)
            public_key.write_text("A" * 200)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is False

    @patch('scripts.setup.deploy.get_container_status')
    def test_create_backup_db_not_running(self, mock_status):
        """Test backup creation when database is not running."""
        console = Mock()
        mock_status.return_value = "exited"

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator._create_backup()

            assert result is True
            console.warning.assert_called_with("Database not running, skipping backup")

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_pull_or_build_images_pull_fallback_build_fails(self, mock_compose):
        """Test image pull failure followed by build failure."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.side_effect = [
            (False, "", "Pull error"),
            (False, "", "Build error"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator._pull_or_build_images()

            assert result is False

    @patch('scripts.setup.deploy.get_container_status')
    def test_save_container_states(self, mock_status):
        """Test saving container states."""
        console = Mock()

        mock_status.side_effect = ["running", "running", "exited"]

        orchestrator = DeploymentOrchestrator(console=console)
        orchestrator._save_container_states()

        assert orchestrator.previous_containers["db"] == "running"
        assert orchestrator.previous_containers["redis"] == "running"
        assert orchestrator.previous_containers["web"] == "exited"

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_start_service_success(self, mock_compose):
        """Test starting a service successfully."""
        console = Mock()
        mock_compose.return_value = (True, "", "")

        orchestrator = DeploymentOrchestrator(console=console)
        result = orchestrator._start_service("web")

        assert result is True

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_start_service_failure(self, mock_compose):
        """Test starting a service that fails."""
        console = Mock()
        mock_compose.return_value = (False, "", "Error starting service")

        orchestrator = DeploymentOrchestrator(console=console)
        result = orchestrator._start_service("web")

        assert result is False

    def test_start_service_dry_run(self):
        """Test starting a service in dry-run mode."""
        console = Mock()

        orchestrator = DeploymentOrchestrator(console=console, dry_run=True)
        result = orchestrator._start_service("web")

        assert result is True
        console.info.assert_called_with("[DRY RUN] Would start service: web")


class TestCLI:
    """Test CLI integration."""

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    def test_cli_dry_run(self, mock_orchestrator_class):
        """Test CLI with --dry-run flag."""
        runner = CliRunner()

        # Mock the orchestrator instance and its methods
        mock_orchestrator = Mock()
        mock_orchestrator.run_preflight_checks.return_value = True
        mock_orchestrator.phase1_preparation.return_value = True
        mock_orchestrator.phase2_infrastructure.return_value = True
        mock_orchestrator.phase3_migrations.return_value = True
        mock_orchestrator.phase4_application.return_value = True
        mock_orchestrator.phase5_verification.return_value = True
        mock_orchestrator_class.return_value = mock_orchestrator

        result = runner.invoke(main, ['--dry-run', '--non-interactive'])

        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.output

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    def test_cli_rollback_cancelled(self, mock_orchestrator_class):
        """Test CLI rollback mode cancelled by user."""
        runner = CliRunner()

        # Simulate user saying 'no' to rollback confirmation
        result = runner.invoke(main, ['--rollback'], input='n\n')

        assert result.exit_code == 0
        assert "Rollback cancelled" in result.output

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    def test_cli_rollback_success(self, mock_orchestrator_class):
        """Test CLI rollback mode with successful rollback."""
        runner = CliRunner()

        mock_orchestrator = Mock()
        mock_orchestrator.rollback.return_value = True
        mock_orchestrator_class.return_value = mock_orchestrator

        result = runner.invoke(main, ['--rollback', '--non-interactive'])

        assert result.exit_code == 0
        assert mock_orchestrator.rollback.called

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    def test_cli_rollback_failure(self, mock_orchestrator_class):
        """Test CLI rollback mode with failed rollback."""
        runner = CliRunner()

        mock_orchestrator = Mock()
        mock_orchestrator.rollback.return_value = False
        mock_orchestrator_class.return_value = mock_orchestrator

        result = runner.invoke(main, ['--rollback', '--non-interactive'])

        assert result.exit_code == 1


class TestIntegration:
    """Test complete deployment workflows."""

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    def test_complete_deployment_workflow(
        self, mock_port, mock_compose_check, mock_running, mock_installed,
        mock_status, mock_compose, mock_wait, mock_subprocess
    ):
        """Test complete successful deployment workflow."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)
        console.confirm = Mock(return_value=True)

        # Setup mocks
        mock_installed.return_value = (True, "20.10.0")
        mock_running.return_value = (True, "")
        mock_compose_check.return_value = (True, "v2.0.0")
        mock_port.return_value = (True, "")
        mock_status.return_value = "running"
        mock_compose.return_value = (True, "PONG", "")
        mock_wait.return_value = True
        mock_subprocess.return_value = Mock(
            returncode=0,
            stdout="SQL backup",
            stderr=""
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            (working_dir / "docker-compose.yml").touch()
            (working_dir / "data" / "backups").mkdir(parents=True)
            (working_dir / "secrets" / "jwt").mkdir(parents=True)
            (working_dir / "secrets" / "jwt" / "private_key.pem").write_text(
                "-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----"
            )
            (working_dir / "secrets" / "jwt" / "public_key.pem").write_text(
                "-----BEGIN PUBLIC KEY-----\n" + "A" * 200 + "\n-----END PUBLIC KEY-----"
            )
            # Create .env file with DATABASE_URL (required by preflight checks)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            # Run all phases
            assert orchestrator.run_preflight_checks() is True
            assert orchestrator.phase1_preparation() is True
            assert orchestrator.phase2_infrastructure() is True
            assert orchestrator.phase3_migrations() is True
            assert orchestrator.phase4_application() is True
            assert orchestrator.phase5_verification() is True

            assert len(orchestrator.phases_completed) == 5

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_status')
    def test_deployment_failure_and_rollback(
        self, mock_status, mock_compose, mock_wait
    ):
        """Test deployment failure triggers rollback."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)
        console.confirm = Mock(return_value=True)

        mock_status.return_value = "not running"
        mock_compose.return_value = (True, "", "")
        mock_wait.return_value = False  # Simulate health check failure

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            # Phase 2 should fail
            result = orchestrator.phase2_infrastructure()

            assert result is False
            assert "infrastructure" not in orchestrator.phases_completed


class TestDryRunCompletion:
    """Test dry-run mode completion and behavior."""

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    def test_dry_run_completes_all_phases(
        self, mock_port, mock_compose_check, mock_running, mock_installed,
        mock_compose, mock_wait
    ):
        """Test that dry-run mode completes all 5 phases without errors."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        # Setup mocks
        mock_installed.return_value = (True, "20.10.0")
        mock_running.return_value = (True, "")
        mock_compose_check.return_value = (True, "v2.0.0")
        mock_port.return_value = (True, "")
        mock_compose.return_value = (True, "PONG", "")
        mock_wait.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            (working_dir / "docker-compose.yml").touch()
            (working_dir / "secrets" / "jwt").mkdir(parents=True)
            (working_dir / "secrets" / "jwt" / "private_key.pem").write_text(
                "-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----"
            )
            (working_dir / "secrets" / "jwt" / "public_key.pem").write_text(
                "-----BEGIN PUBLIC KEY-----\n" + "A" * 200 + "\n-----END PUBLIC KEY-----"
            )

            orchestrator = DeploymentOrchestrator(
                console=console,
                dry_run=True,
                working_dir=working_dir
            )

            # Run all phases
            assert orchestrator.phase1_preparation() is True
            assert orchestrator.phase2_infrastructure() is True
            assert orchestrator.phase3_migrations() is True
            assert orchestrator.phase4_application() is True
            assert orchestrator.phase5_verification() is True

            # Verify all phases were marked complete
            assert len(orchestrator.phases_completed) == 5

    def test_dry_run_exits_with_zero_code(self):
        """Test that dry-run mode exits with code 0."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True
        )

        result = orchestrator.phase1_preparation()

        assert result is True

    def test_dry_run_shows_dry_run_messages(self):
        """Test that dry-run mode shows [DRY RUN] messages for health checks."""
        console = Mock()

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True
        )

        result = orchestrator.phase3_migrations()

        assert result is True
        # Verify [DRY RUN] message was printed
        console.info.assert_called()
        call_args = [str(call) for call in console.info.call_args_list]
        assert any("[DRY RUN]" in str(call) for call in call_args)

    def test_dry_run_no_containers_started(self):
        """Test that no actual containers are started in dry-run mode."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        with patch('scripts.setup.deploy.get_container_status') as mock_status:
            mock_status.return_value = "not running"

            with tempfile.TemporaryDirectory() as tmpdir:
                working_dir = Path(tmpdir)

                orchestrator = DeploymentOrchestrator(
                    console=console,
                    dry_run=True,
                    working_dir=working_dir
                )

                result = orchestrator.phase1_preparation()

                assert result is True
                # In dry-run mode, no actual container operations should be performed
                # backup_file should remain None
                assert orchestrator.backup_file is None


class TestHealthCheckRetryLogic:
    """Test health check retry behavior and retry delays."""

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.time.sleep')
    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_health_check_succeeds_on_first_attempt(
        self, mock_compose, mock_httpx_get, mock_sleep, mock_subprocess
    ):
        """Test health check succeeds on first attempt."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            assert result is True
            # No retry delays should occur
            mock_sleep.assert_not_called()

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.time.sleep')
    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_health_check_succeeds_on_second_attempt(
        self, mock_compose, mock_httpx_get, mock_sleep, mock_subprocess
    ):
        """Test health check succeeds on second attempt after first failure."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")
        # First call fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_get.side_effect = [
            Exception("Connection refused"),
            mock_response
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            assert result is True
            # Should have slept once (2 second delay between attempts)
            mock_sleep.assert_called_with(2)

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.time.sleep')
    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_health_check_succeeds_on_third_attempt(
        self, mock_compose, mock_httpx_get, mock_sleep, mock_subprocess
    ):
        """Test health check succeeds on third attempt after two failures."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")
        # First two calls fail, third succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_get.side_effect = [
            Exception("Connection refused"),
            Exception("Connection refused"),
            mock_response
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            assert result is True
            # Should have slept twice (2 second delay between each attempt)
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(2)

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.time.sleep')
    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_health_check_fails_after_all_attempts_exhausted(
        self, mock_compose, mock_httpx_get, mock_sleep, mock_subprocess
    ):
        """Test health check fails after all 3 attempts exhausted."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")
        # All attempts fail
        mock_httpx_get.side_effect = Exception("Connection refused")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            # Phase still succeeds (smoke tests are non-critical)
            assert result is True
            # Should have slept after each of the first 2 failed attempts
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(2)

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.time.sleep')
    @patch('httpx.get')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_health_check_retry_delays_applied(
        self, mock_compose, mock_httpx_get, mock_sleep, mock_subprocess
    ):
        """Test that retry delays of 2 seconds are applied between attempts."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "PONG", "")
        # First attempt fails, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_httpx_get.side_effect = [
            Exception("Connection refused"),
            mock_response
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.phase5_verification()

            assert result is True
            # Verify sleep was called with 2 seconds
            mock_sleep.assert_called()
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 2  # 2 second delay


class TestManualRollback:
    """Test manual rollback functionality using --rollback flag."""

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_stops_containers(self, mock_compose, mock_subprocess):
        """Test that --rollback flag stops running containers."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"
            # Create .env file with DATABASE_URL (required for rollback)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()
            orchestrator.backup_file = backup_file

            result = orchestrator.rollback()

            assert result is True
            # Verify that docker-compose down was called (to stop containers)
            down_calls = [call for call in mock_compose.call_args_list
                         if 'down' in str(call)]
            assert len(down_calls) > 0

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_restores_backup(self, mock_compose, mock_subprocess):
        """Test that --rollback flag restores previous backup."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")
        mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"
            # Create .env file with DATABASE_URL (required for rollback)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            # Create a dummy backup file with SQL content
            import gzip
            backup_sql = "CREATE TABLE test (id INT);\nINSERT INTO test VALUES (1);"
            with gzip.open(backup_file, 'wt') as f:
                f.write(backup_sql)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()
            orchestrator.backup_file = backup_file

            result = orchestrator.rollback()

            assert result is True
            # Verify that psql was called to restore the backup
            assert mock_subprocess.called
            restore_calls = [call for call in mock_subprocess.call_args_list
                            if any("psql" in str(arg) for arg in call[0])]
            assert len(restore_calls) > 0

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_handles_missing_backup_gracefully(self, mock_compose):
        """Test that rollback handles non-existent state gracefully."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # No backup_file set

            result = orchestrator.rollback()

            assert result is True
            # Should display warning about missing backup
            console.warning.assert_called_with("No backup file to restore from")

    def test_rollback_confirmation_interactive_mode_yes(self):
        """Test rollback confirmation prompts work in interactive mode (user confirms)."""
        runner = CliRunner()

        with patch('scripts.setup.deploy.DeploymentOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.rollback.return_value = True
            mock_orchestrator_class.return_value = mock_orchestrator

            # Simulate user saying 'yes' to rollback confirmation
            result = runner.invoke(main, ['--rollback'], input='y\n')

            assert result.exit_code == 0
            # Verify that rollback was actually called
            assert mock_orchestrator.rollback.called

    def test_rollback_confirmation_interactive_mode_no(self):
        """Test rollback confirmation prompts work in interactive mode (user cancels)."""
        runner = CliRunner()

        # Simulate user saying 'no' to rollback confirmation
        result = runner.invoke(main, ['--rollback'], input='n\n')

        assert result.exit_code == 0
        assert "Rollback cancelled" in result.output

    def test_rollback_without_confirmation_non_interactive_mode(self):
        """Test that rollback works in non-interactive mode without confirmation."""
        runner = CliRunner()

        with patch('scripts.setup.deploy.DeploymentOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.rollback.return_value = True
            mock_orchestrator_class.return_value = mock_orchestrator

            # Run with --non-interactive flag (no prompts)
            result = runner.invoke(main, ['--rollback', '--non-interactive'])

            assert result.exit_code == 0
            # Verify rollback was called without prompting
            assert mock_orchestrator.rollback.called

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_restarts_all_services_after_restore(self, mock_compose):
        """Test that rollback restarts services after backup restoration."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"
            # Create .env file with DATABASE_URL (required for rollback)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()
            orchestrator.backup_file = backup_file

            with patch('scripts.setup.deploy.subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

                result = orchestrator.rollback()

                assert result is True
                # Verify that docker-compose up was called (to restart services)
                up_calls = [call for call in mock_compose.call_args_list
                           if 'up' in str(call)]
                assert len(up_calls) > 0

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_displays_success_message_on_completion(self, mock_compose):
        """Test that rollback displays success message upon completion."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"
            # Create .env file with DATABASE_URL (required for rollback)
            (working_dir / ".env").write_text(
                "DATABASE_URL=postgresql://promptvault:testpass@localhost:5432/promptvault\n"
            )

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            # Load database credentials (normally done in preflight checks)
            orchestrator._load_database_credentials()
            orchestrator.backup_file = backup_file

            with patch('scripts.setup.deploy.subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = Mock(returncode=0, stdout="", stderr="")

                result = orchestrator.rollback()

                assert result is True
                # Verify success message was displayed
                console.success.assert_called()
                success_calls = [call for call in console.success.call_args_list
                                if "Rollback completed" in str(call)]
                assert len(success_calls) > 0

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_failure_on_stop_services(self, mock_compose, mock_subprocess):
        """Test rollback handles failure to stop services."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        # First call to docker-compose down fails
        mock_compose.return_value = (False, "", "Failed to stop containers")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

            result = orchestrator.rollback()

            # Rollback should still attempt to continue despite stop failure
            # The method checks if docker-compose down succeeds, but continue anyway
            assert isinstance(result, bool)

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_failure_on_restore_backup(self, mock_compose):
        """Test rollback handles failure to restore backup."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        mock_compose.return_value = (True, "", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True)
            backup_file = backup_dir / "test-backup.sql.gz"

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
            orchestrator.backup_file = backup_file

            with patch('scripts.setup.deploy.subprocess.run') as mock_subprocess:
                # Simulate restore failure
                mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Restore failed")

                result = orchestrator.rollback()

                # Rollback should fail if restore fails
                assert result is False

    def test_rollback_cli_flag_with_failed_rollback(self):
        """Test CLI --rollback flag when rollback operation fails."""
        runner = CliRunner()

        with patch('scripts.setup.deploy.DeploymentOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.rollback.return_value = False
            mock_orchestrator_class.return_value = mock_orchestrator

            # Run rollback in non-interactive mode (fails)
            result = runner.invoke(main, ['--rollback', '--non-interactive'])

            assert result.exit_code == 1
            assert "Rollback failed" in result.output

    def test_rollback_dry_run_mode_no_actual_changes(self):
        """Test that rollback in dry-run mode makes no actual changes."""
        console = Mock()
        console.spinner = MagicMock()
        console.spinner.return_value.__enter__ = Mock(return_value=None)
        console.spinner.return_value.__exit__ = Mock(return_value=None)

        orchestrator = DeploymentOrchestrator(
            console=console,
            dry_run=True
        )

        orchestrator._stop_all_services = Mock(return_value=True)
        orchestrator._start_all_services = Mock(return_value=True)
        orchestrator._restore_backup = Mock(return_value=True)

        result = orchestrator.rollback()

        assert result is True
        # In dry-run mode, the methods should show [DRY RUN] messages
        console.info.assert_called()
        dry_run_calls = [call for call in console.info.call_args_list
                        if "[DRY RUN]" in str(call)]
        assert len(dry_run_calls) > 0
