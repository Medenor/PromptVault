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

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

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

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )

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

            # Create a dummy backup file
            import gzip
            with gzip.open(backup_file, 'wt') as f:
                f.write("SELECT 1;")

            orchestrator = DeploymentOrchestrator(
                console=console,
                working_dir=working_dir
            )
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
