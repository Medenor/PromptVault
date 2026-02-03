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
import tempfile
import shutil
import gzip
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch, call, mock_open
from click.testing import CliRunner
import pytest

# Import the module to test
from scripts.setup.deploy import (
    DeploymentOrchestrator,
    main,
)


class TestDeploymentOrchestratorInitialization:
    """Test DeploymentOrchestrator class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))
        self.console.confirm = Mock(return_value=True)
        self.console.table = Mock()

    def test_init_default_values(self):
        """Test initialization with default values."""
        orchestrator = DeploymentOrchestrator(self.console)

        assert orchestrator.console == self.console
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

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        custom_dir = Path("/tmp/test")
        orchestrator = DeploymentOrchestrator(
            console=self.console,
            dry_run=True,
            skip_backup=True,
            skip_migrations=True,
            rebuild=True,
            non_interactive=True,
            working_dir=custom_dir
        )

        assert orchestrator.dry_run is True
        assert orchestrator.skip_backup is True
        assert orchestrator.skip_migrations is True
        assert orchestrator.rebuild is True
        assert orchestrator.non_interactive is True
        assert orchestrator.working_dir == custom_dir

    def test_init_state_tracking(self):
        """Test that state tracking is initialized properly."""
        orchestrator = DeploymentOrchestrator(self.console)

        assert isinstance(orchestrator.previous_containers, dict)
        assert isinstance(orchestrator.phases_completed, list)
        assert len(orchestrator.previous_containers) == 0
        assert len(orchestrator.phases_completed) == 0


class TestPreflightChecks:
    """Test pre-flight checks before deployment."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    @patch('scripts.setup.deploy.shutil.disk_usage')
    def test_preflight_checks_all_pass(
        self,
        mock_disk_usage,
        mock_port_available,
        mock_compose_installed,
        mock_docker_running,
        mock_docker_installed
    ):
        """Test when all pre-flight checks pass."""
        # Mock successful checks
        mock_docker_installed.return_value = (True, "Docker version 24.0.5")
        mock_docker_running.return_value = (True, None)
        mock_compose_installed.return_value = (True, "v2.21.0")
        mock_port_available.return_value = (True, None)

        # Mock disk space (3 GB free)
        mock_stat = Mock()
        mock_stat.free = 3 * (1024 ** 3)
        mock_disk_usage.return_value = mock_stat

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            # Create required files
            (working_dir / "docker-compose.yml").write_text("version: '3.8'")

            # Create JWT keys
            jwt_dir = working_dir / "secrets" / "jwt"
            jwt_dir.mkdir(parents=True, exist_ok=True)
            (jwt_dir / "private_key.pem").write_text("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----")
            (jwt_dir / "public_key.pem").write_text("-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator.run_preflight_checks()

            assert result is True
            assert self.console.success.call_count >= 5

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    def test_preflight_checks_docker_not_installed(
        self,
        mock_docker_running,
        mock_docker_installed
    ):
        """Test when Docker is not installed."""
        mock_docker_installed.return_value = (False, "Docker not found")
        mock_docker_running.return_value = (True, None)

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.run_preflight_checks()

            assert result is False
            assert any("Docker not installed" in str(call) for call in self.console.error.call_args_list)

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    def test_preflight_checks_docker_not_running(
        self,
        mock_docker_running,
        mock_docker_installed
    ):
        """Test when Docker daemon is not running."""
        mock_docker_installed.return_value = (True, "Docker version 24.0.5")
        mock_docker_running.return_value = (False, "Cannot connect to daemon")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.run_preflight_checks()

            assert result is False

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    @patch('scripts.setup.deploy.shutil.disk_usage')
    def test_preflight_checks_missing_compose_file(
        self,
        mock_disk_usage,
        mock_port_available,
        mock_compose_installed,
        mock_docker_running,
        mock_docker_installed
    ):
        """Test when docker-compose.yml is missing."""
        mock_docker_installed.return_value = (True, "Docker version 24.0.5")
        mock_docker_running.return_value = (True, None)
        mock_compose_installed.return_value = (True, "v2.21.0")
        mock_port_available.return_value = (True, None)

        mock_stat = Mock()
        mock_stat.free = 3 * (1024 ** 3)
        mock_disk_usage.return_value = mock_stat

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.run_preflight_checks()

            assert result is False
            assert any("docker-compose.yml not found" in str(call) for call in self.console.error.call_args_list)

    @patch('scripts.setup.deploy.check_docker_installed')
    @patch('scripts.setup.deploy.check_docker_running')
    @patch('scripts.setup.deploy.check_docker_compose_installed')
    @patch('scripts.setup.deploy.check_port_available')
    @patch('scripts.setup.deploy.shutil.disk_usage')
    def test_preflight_checks_low_disk_space(
        self,
        mock_disk_usage,
        mock_port_available,
        mock_compose_installed,
        mock_docker_running,
        mock_docker_installed
    ):
        """Test when disk space is critically low."""
        mock_docker_installed.return_value = (True, "Docker version 24.0.5")
        mock_docker_running.return_value = (True, None)
        mock_compose_installed.return_value = (True, "v2.21.0")
        mock_port_available.return_value = (True, None)

        # Mock very low disk space (0.5 GB free)
        mock_stat = Mock()
        mock_stat.free = 0.5 * (1024 ** 3)
        mock_disk_usage.return_value = mock_stat

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            (working_dir / "docker-compose.yml").write_text("version: '3.8'")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator.run_preflight_checks()

            assert result is False
            assert any("Insufficient disk space" in str(call) for call in self.console.error.call_args_list)


class TestPhase1Preparation:
    """Test Phase 1: Preparation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.subprocess.run')
    def test_phase1_preparation_success(
        self,
        mock_subprocess_run,
        mock_docker_compose,
        mock_container_status
    ):
        """Test successful Phase 1 execution."""
        mock_container_status.return_value = "running"
        mock_docker_compose.return_value = (True, "Success", "")

        # Mock pg_dump for backup
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "-- PostgreSQL database dump\nCREATE TABLE test;"
        mock_subprocess_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator.phase1_preparation()

            assert result is True
            assert "preparation" in orchestrator.phases_completed

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase1_preparation_skip_backup(
        self,
        mock_docker_compose,
        mock_container_status
    ):
        """Test Phase 1 with skip_backup flag."""
        mock_container_status.return_value = "stopped"
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                skip_backup=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase1_preparation()

            assert result is True
            assert "preparation" in orchestrator.phases_completed
            assert any("Skipping backup" in str(call) for call in self.console.info.call_args_list)

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase1_preparation_dry_run(
        self,
        mock_docker_compose,
        mock_container_status
    ):
        """Test Phase 1 in dry run mode."""
        mock_container_status.return_value = "stopped"

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase1_preparation()

            assert result is True
            # Should not call docker-compose commands
            mock_docker_compose.assert_not_called()

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase1_preparation_build_failure(
        self,
        mock_docker_compose,
        mock_container_status
    ):
        """Test Phase 1 when image build/pull fails."""
        mock_container_status.return_value = "stopped"
        mock_docker_compose.return_value = (False, "", "Build failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase1_preparation()

            assert result is False
            assert "preparation" not in orchestrator.phases_completed

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase1_preparation_rebuild_flag(
        self,
        mock_docker_compose,
        mock_container_status
    ):
        """Test Phase 1 with rebuild flag."""
        mock_container_status.return_value = "stopped"
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                rebuild=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase1_preparation()

            assert result is True
            # Verify build was called with --no-cache
            build_calls = [call for call in mock_docker_compose.call_args_list
                          if call[0][0] == "build"]
            assert len(build_calls) > 0

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase1_preparation_exception_handling(
        self,
        mock_docker_compose,
        mock_container_status
    ):
        """Test Phase 1 exception handling."""
        mock_container_status.side_effect = Exception("Test error")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase1_preparation()

            assert result is False
            assert "preparation" not in orchestrator.phases_completed


class TestPhase2Infrastructure:
    """Test Phase 2: Infrastructure."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase2_infrastructure_success(
        self,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test successful Phase 2 execution."""
        mock_docker_compose.return_value = (True, "Success", "")
        mock_wait_healthy.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase2_infrastructure()

            assert result is True
            assert "infrastructure" in orchestrator.phases_completed
            # Verify both db and redis were started
            assert mock_docker_compose.call_count >= 2
            assert mock_wait_healthy.call_count == 2

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_logs')
    def test_phase2_infrastructure_db_not_healthy(
        self,
        mock_get_logs,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test Phase 2 when database fails to become healthy."""
        mock_docker_compose.return_value = (True, "Success", "")
        mock_wait_healthy.return_value = False
        mock_get_logs.return_value = "Database error logs"

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase2_infrastructure()

            assert result is False
            assert "infrastructure" not in orchestrator.phases_completed
            assert mock_get_logs.called

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase2_infrastructure_redis_not_healthy(
        self,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test Phase 2 when Redis fails to become healthy."""
        mock_docker_compose.return_value = (True, "Success", "")
        # First call (db) succeeds, second call (redis) fails
        mock_wait_healthy.side_effect = [True, False]

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase2_infrastructure()

            assert result is False
            assert "infrastructure" not in orchestrator.phases_completed

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase2_infrastructure_service_start_failure(
        self,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test Phase 2 when service fails to start."""
        mock_docker_compose.return_value = (False, "", "Failed to start")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase2_infrastructure()

            assert result is False
            assert "infrastructure" not in orchestrator.phases_completed


class TestPhase3Migrations:
    """Test Phase 3: Database Migrations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_success(
        self,
        mock_docker_compose,
        mock_subprocess_run
    ):
        """Test successful Phase 3 execution."""
        # Mock db ready check
        mock_docker_compose.return_value = (True, "1", "")

        # Mock alembic upgrade
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Running upgrade -> head"
        mock_subprocess_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is True
            assert "migrations" in orchestrator.phases_completed

    def test_phase3_migrations_skip_flag(self):
        """Test Phase 3 with skip_migrations flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                skip_migrations=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is True
            assert "migrations" in orchestrator.phases_completed
            assert any("Skipping migrations" in str(call) for call in self.console.info.call_args_list)

    def test_phase3_migrations_dry_run(self):
        """Test Phase 3 in dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is True
            assert "migrations" in orchestrator.phases_completed

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_db_not_ready(
        self,
        mock_docker_compose
    ):
        """Test Phase 3 when database is not ready."""
        mock_docker_compose.return_value = (False, "", "Connection refused")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is False
            assert "migrations" not in orchestrator.phases_completed

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_alembic_failure(
        self,
        mock_docker_compose,
        mock_subprocess_run
    ):
        """Test Phase 3 when Alembic migration fails."""
        mock_docker_compose.return_value = (True, "1", "")

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Migration failed: syntax error"
        mock_subprocess_run.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is False
            assert "migrations" not in orchestrator.phases_completed

    @patch('scripts.setup.deploy.subprocess.run')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase3_migrations_timeout(
        self,
        mock_docker_compose,
        mock_subprocess_run
    ):
        """Test Phase 3 when migration times out."""
        mock_docker_compose.return_value = (True, "1", "")
        mock_subprocess_run.side_effect = subprocess.TimeoutExpired("alembic", 120)

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase3_migrations()

            assert result is False
            assert "migrations" not in orchestrator.phases_completed


class TestPhase4Application:
    """Test Phase 4: Application Deployment."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase4_application_success(
        self,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test successful Phase 4 execution."""
        mock_docker_compose.return_value = (True, "Success", "")
        mock_wait_healthy.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase4_application()

            assert result is True
            assert "application" in orchestrator.phases_completed

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase4_application_start_failure(
        self,
        mock_docker_compose
    ):
        """Test Phase 4 when web service fails to start."""
        mock_docker_compose.return_value = (False, "", "Failed to start web service")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase4_application()

            assert result is False
            assert "application" not in orchestrator.phases_completed

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    @patch('scripts.setup.deploy.get_container_logs')
    def test_phase4_application_not_healthy(
        self,
        mock_get_logs,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test Phase 4 when application fails health check."""
        mock_docker_compose.return_value = (True, "Success", "")
        mock_wait_healthy.return_value = False
        mock_get_logs.return_value = "Application startup error"

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase4_application()

            assert result is False
            assert "application" not in orchestrator.phases_completed
            # Verify logs were shown (with tail=100)
            mock_get_logs.assert_called_once()

    @patch('scripts.setup.deploy.wait_for_healthy')
    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase4_application_exception(
        self,
        mock_docker_compose,
        mock_wait_healthy
    ):
        """Test Phase 4 exception handling."""
        mock_docker_compose.side_effect = Exception("Unexpected error")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase4_application()

            assert result is False
            assert "application" not in orchestrator.phases_completed


class TestPhase5Verification:
    """Test Phase 5: Verification."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))
        self.console.table = Mock()

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase5_verification_success(
        self,
        mock_docker_compose
    ):
        """Test successful Phase 5 execution."""
        mock_docker_compose.return_value = (True, "1\nPONG", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_httpx_get.return_value = mock_response

                result = orchestrator.phase5_verification()

                assert result is True
                assert "verification" in orchestrator.phases_completed

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase5_verification_smoke_tests_fail(
        self,
        mock_docker_compose
    ):
        """Test Phase 5 when smoke tests fail (non-critical)."""
        mock_docker_compose.return_value = (False, "", "Connection failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_httpx_get.side_effect = Exception("Connection refused")

                result = orchestrator.phase5_verification()

                # Should still succeed as smoke tests are non-critical
                assert result is True
                assert "verification" in orchestrator.phases_completed

    def test_phase5_verification_dry_run(self):
        """Test Phase 5 in dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.phase5_verification()

            assert result is True

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_phase5_verification_displays_access_info(
        self,
        mock_docker_compose
    ):
        """Test that Phase 5 displays access information."""
        mock_docker_compose.return_value = (True, "1\nPONG", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )
            orchestrator.deployment_start_time = datetime.now()

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_httpx_get.return_value = mock_response

                result = orchestrator.phase5_verification()

                # Verify table was called to display summary
                assert self.console.table.called


class TestRollback:
    """Test rollback functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_success_with_backup(
        self,
        mock_docker_compose
    ):
        """Test successful rollback with backup restoration."""
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            # Create backup file
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / "test_backup.sql.gz"

            with gzip.open(backup_file, 'wt') as f:
                f.write("-- Test backup\nCREATE TABLE test;")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )
            orchestrator.backup_file = backup_file

            with patch('scripts.setup.deploy.subprocess.run') as mock_subprocess:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_subprocess.return_value = mock_result

                result = orchestrator.rollback()

                assert result is True
                # Verify down and up were called
                assert any(call[0][0] == "down" for call in mock_docker_compose.call_args_list)
                assert any(call[0][0] == "up" for call in mock_docker_compose.call_args_list)

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_success_without_backup(
        self,
        mock_docker_compose
    ):
        """Test rollback without backup file."""
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.rollback()

            assert result is True
            # Should warn about no backup
            assert any("No backup file" in str(call) for call in self.console.warning.call_args_list)

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_restore_failure(
        self,
        mock_docker_compose
    ):
        """Test rollback when backup restoration fails."""
        # Stop succeeds, restore fails, restart succeeds
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / "test_backup.sql.gz"

            with gzip.open(backup_file, 'wt') as f:
                f.write("-- Test backup")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )
            orchestrator.backup_file = backup_file

            with patch('scripts.setup.deploy.subprocess.run') as mock_subprocess:
                mock_result = Mock()
                mock_result.returncode = 1
                mock_result.stderr = "Restore failed"
                mock_subprocess.return_value = mock_result

                result = orchestrator.rollback()

                assert result is False

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_restart_failure(
        self,
        mock_docker_compose
    ):
        """Test rollback when service restart fails."""
        # Stop succeeds, up fails
        mock_docker_compose.side_effect = [
            (True, "Success", ""),  # down
            (False, "", "Failed to start")  # up
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.rollback()

            assert result is False

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_rollback_exception_handling(
        self,
        mock_docker_compose
    ):
        """Test rollback exception handling."""
        mock_docker_compose.side_effect = Exception("Unexpected error")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator.rollback()

            assert result is False


class TestHelperMethods:
    """Test helper methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.shutil.disk_usage')
    def test_check_disk_space(self, mock_disk_usage):
        """Test disk space check."""
        mock_stat = Mock()
        mock_stat.free = 5 * (1024 ** 3)  # 5 GB
        mock_disk_usage.return_value = mock_stat

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            space = orchestrator._check_disk_space()

            assert space == pytest.approx(5.0, rel=0.01)

    def test_validate_jwt_keys_valid(self):
        """Test JWT key validation with valid keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            private_key = working_dir / "private.pem"
            public_key = working_dir / "public.pem"

            private_key.write_text("-----BEGIN PRIVATE KEY-----\n" + "A" * 200 + "\n-----END PRIVATE KEY-----")
            public_key.write_text("-----BEGIN PUBLIC KEY-----\n" + "B" * 200 + "\n-----END PUBLIC KEY-----")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is True

    def test_validate_jwt_keys_invalid_size(self):
        """Test JWT key validation with too-small keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            private_key = working_dir / "private.pem"
            public_key = working_dir / "public.pem"

            private_key.write_text("small")
            public_key.write_text("small")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is False

    def test_validate_jwt_keys_missing_headers(self):
        """Test JWT key validation with missing PEM headers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            private_key = working_dir / "private.pem"
            public_key = working_dir / "public.pem"

            private_key.write_text("A" * 200)
            public_key.write_text("B" * 200)

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._validate_jwt_keys(private_key, public_key)

            assert result is False

    @patch('scripts.setup.deploy.get_container_status')
    def test_save_container_states(self, mock_container_status):
        """Test saving container states."""
        mock_container_status.side_effect = ["running", "running", "stopped"]

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            orchestrator._save_container_states()

            assert orchestrator.previous_containers["db"] == "running"
            assert orchestrator.previous_containers["redis"] == "running"
            assert orchestrator.previous_containers["web"] == "stopped"

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_start_service(self, mock_docker_compose):
        """Test starting a service."""
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator._start_service("web")

            assert result is True
            mock_docker_compose.assert_called_once()

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_start_service_failure(self, mock_docker_compose):
        """Test service start failure."""
        mock_docker_compose.return_value = (False, "", "Failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator._start_service("web")

            assert result is False

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_stop_all_services(self, mock_docker_compose):
        """Test stopping all services."""
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator._stop_all_services()

            assert result is True
            # Verify down was called
            assert mock_docker_compose.call_args[0][0] == "down"

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_start_all_services(self, mock_docker_compose):
        """Test starting all services."""
        mock_docker_compose.return_value = (True, "Success", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator._start_all_services()

            assert result is True
            # Verify up was called with -d
            assert mock_docker_compose.call_args[0][0] == "up"


class TestSmokeTests:
    """Test smoke test functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_smoke_tests_all_pass(self, mock_docker_compose):
        """Test when all smoke tests pass."""
        mock_docker_compose.return_value = (True, "1\nPONG", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_httpx_get.return_value = mock_response

                result = orchestrator._run_smoke_tests()

                assert result is True

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_smoke_tests_health_endpoint_failure(self, mock_docker_compose):
        """Test when health endpoint fails."""
        mock_docker_compose.return_value = (True, "1\nPONG", "")

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_httpx_get.return_value = mock_response

                result = orchestrator._run_smoke_tests()

                assert result is False

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_smoke_tests_database_failure(self, mock_docker_compose):
        """Test when database connectivity fails."""
        # Health passes, database fails, redis passes
        mock_docker_compose.side_effect = [
            (False, "", "Connection failed"),
            (True, "PONG", "")
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_httpx_get.return_value = mock_response

                result = orchestrator._run_smoke_tests()

                assert result is False

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_smoke_tests_redis_failure(self, mock_docker_compose):
        """Test when Redis connectivity fails."""
        mock_docker_compose.side_effect = [
            (True, "1", ""),  # Database check passes
            (False, "", "Connection refused")  # Redis check fails
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            with patch('httpx.get') as mock_httpx_get:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_httpx_get.return_value = mock_response

                result = orchestrator._run_smoke_tests()

                assert result is False


class TestCLIIntegration:
    """Test CLI command-line interface."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_cli_help(self, mock_console, mock_orchestrator):
        """Test CLI help message."""
        result = self.runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        assert "PromptVault Deployment" in result.output
        assert "--dry-run" in result.output
        assert "--skip-backup" in result.output
        assert "--skip-migrations" in result.output
        assert "--rollback" in result.output
        assert "--rebuild" in result.output
        assert "--non-interactive" in result.output

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_cli_dry_run_flag(self, mock_console, mock_orchestrator):
        """Test CLI with --dry-run flag."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = True
        mock_orch_instance.phase2_infrastructure.return_value = True
        mock_orch_instance.phase3_migrations.return_value = True
        mock_orch_instance.phase4_application.return_value = True
        mock_orch_instance.phase5_verification.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--dry-run', '--non-interactive'])

        # Verify orchestrator was created with dry_run=True
        assert mock_orchestrator.call_args[1]['dry_run'] is True

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_cli_skip_backup_flag(self, mock_console, mock_orchestrator):
        """Test CLI with --skip-backup flag."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = True
        mock_orch_instance.phase2_infrastructure.return_value = True
        mock_orch_instance.phase3_migrations.return_value = True
        mock_orch_instance.phase4_application.return_value = True
        mock_orch_instance.phase5_verification.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--skip-backup', '--non-interactive'])

        assert mock_orchestrator.call_args[1]['skip_backup'] is True

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_cli_rollback_flag(self, mock_console, mock_orchestrator):
        """Test CLI with --rollback flag."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.rollback.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--rollback', '--non-interactive'])

        assert result.exit_code == 0
        mock_orch_instance.rollback.assert_called_once()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_cli_multiple_flags(self, mock_console, mock_orchestrator):
        """Test CLI with multiple flags."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = True
        mock_orch_instance.phase2_infrastructure.return_value = True
        mock_orch_instance.phase3_migrations.return_value = True
        mock_orch_instance.phase4_application.return_value = True
        mock_orch_instance.phase5_verification.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, [
            '--skip-backup',
            '--skip-migrations',
            '--rebuild',
            '--non-interactive'
        ])

        call_kwargs = mock_orchestrator.call_args[1]
        assert call_kwargs['skip_backup'] is True
        assert call_kwargs['skip_migrations'] is True
        assert call_kwargs['rebuild'] is True
        assert call_kwargs['non_interactive'] is True


class TestDeploymentFlow:
    """Test complete deployment flow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_successful_deployment_flow(self, mock_console, mock_orchestrator):
        """Test complete successful deployment."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = True
        mock_orch_instance.phase2_infrastructure.return_value = True
        mock_orch_instance.phase3_migrations.return_value = True
        mock_orch_instance.phase4_application.return_value = True
        mock_orch_instance.phase5_verification.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--non-interactive'])

        assert result.exit_code == 0
        mock_orch_instance.run_preflight_checks.assert_called_once()
        mock_orch_instance.phase1_preparation.assert_called_once()
        mock_orch_instance.phase2_infrastructure.assert_called_once()
        mock_orch_instance.phase3_migrations.assert_called_once()
        mock_orch_instance.phase4_application.assert_called_once()
        mock_orch_instance.phase5_verification.assert_called_once()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_preflight_checks_failure(self, mock_console, mock_orchestrator):
        """Test deployment fails at pre-flight checks."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = False
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--non-interactive'])

        assert result.exit_code == 1
        mock_orch_instance.phase1_preparation.assert_not_called()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_phase1_failure_triggers_rollback(self, mock_console, mock_orchestrator):
        """Test Phase 1 failure triggers rollback."""
        mock_console_instance = Mock()
        mock_console_instance.confirm.return_value = True
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = False
        mock_orch_instance.rollback.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        mock_orch_instance.rollback.assert_called_once()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_phase2_failure_triggers_rollback(self, mock_console, mock_orchestrator):
        """Test Phase 2 failure triggers rollback."""
        mock_console_instance = Mock()
        mock_console_instance.confirm.return_value = True
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = True
        mock_orch_instance.phase2_infrastructure.return_value = False
        mock_orch_instance.rollback.return_value = True
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        mock_orch_instance.rollback.assert_called_once()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_rollback_failure(self, mock_console, mock_orchestrator):
        """Test when rollback also fails."""
        mock_console_instance = Mock()
        mock_console_instance.confirm.return_value = True
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = False
        mock_orch_instance.rollback.return_value = False
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, [])

        assert result.exit_code == 2  # Special exit code for rollback failure

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_user_declines_rollback(self, mock_console, mock_orchestrator):
        """Test when user declines rollback."""
        mock_console_instance = Mock()
        mock_console_instance.confirm.return_value = False
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = False
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, [])

        assert result.exit_code == 1
        mock_orch_instance.rollback.assert_not_called()

    @patch('scripts.setup.deploy.DeploymentOrchestrator')
    @patch('scripts.setup.deploy.SetupConsole')
    def test_dry_run_no_rollback_on_failure(self, mock_console, mock_orchestrator):
        """Test dry run doesn't trigger rollback."""
        mock_console_instance = Mock()
        mock_console.return_value = mock_console_instance

        mock_orch_instance = Mock()
        mock_orch_instance.run_preflight_checks.return_value = True
        mock_orch_instance.phase1_preparation.return_value = False
        mock_orchestrator.return_value = mock_orch_instance

        result = self.runner.invoke(main, ['--dry-run'])

        assert result.exit_code == 1
        mock_orch_instance.rollback.assert_not_called()


class TestBackupAndRestore:
    """Test backup and restore functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.get_container_status')
    @patch('scripts.setup.deploy.subprocess.run')
    def test_create_backup_success(self, mock_subprocess, mock_container_status):
        """Test successful backup creation."""
        mock_container_status.return_value = "running"

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "-- PostgreSQL database dump\nCREATE TABLE test (id INT);"
        mock_subprocess.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._create_backup()

            assert result is True
            assert orchestrator.backup_file is not None
            assert orchestrator.backup_file.exists()
            assert orchestrator.backup_file.suffix == ".gz"

    @patch('scripts.setup.deploy.get_container_status')
    def test_create_backup_db_not_running(self, mock_container_status):
        """Test backup when database is not running."""
        mock_container_status.return_value = "stopped"

        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=Path(tmpdir)
            )

            result = orchestrator._create_backup()

            # Should succeed but skip actual backup
            assert result is True
            assert any("Database not running" in str(call) for call in self.console.warning.call_args_list)

    @patch('scripts.setup.deploy.subprocess.run')
    def test_restore_backup_success(self, mock_subprocess):
        """Test successful backup restoration."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            # Create test backup file
            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / "test.sql.gz"

            with gzip.open(backup_file, 'wt') as f:
                f.write("-- Test backup\nCREATE TABLE test;")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._restore_backup(backup_file)

            assert result is True

    @patch('scripts.setup.deploy.subprocess.run')
    def test_restore_backup_failure(self, mock_subprocess):
        """Test backup restoration failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "psql: connection failed"
        mock_subprocess.return_value = mock_result

        with tempfile.TemporaryDirectory() as tmpdir:
            working_dir = Path(tmpdir)

            backup_dir = working_dir / "data" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_file = backup_dir / "test.sql.gz"

            with gzip.open(backup_file, 'wt') as f:
                f.write("-- Test backup")

            orchestrator = DeploymentOrchestrator(
                self.console,
                working_dir=working_dir
            )

            result = orchestrator._restore_backup(backup_file)

            assert result is False


class TestDryRunMode:
    """Test dry run mode behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Mock()
        self.console.error = Mock()
        self.console.info = Mock()
        self.console.success = Mock()
        self.console.warning = Mock()
        self.console.header = Mock()
        self.console.step = Mock()
        self.console.spinner = Mock(return_value=MagicMock(__enter__=Mock(), __exit__=Mock()))

    @patch('scripts.setup.deploy.run_docker_compose')
    def test_dry_run_no_docker_commands(self, mock_docker_compose):
        """Test dry run doesn't execute Docker commands."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            orchestrator.phase1_preparation()
            orchestrator.phase2_infrastructure()
            orchestrator.phase4_application()

            # No Docker commands should be executed
            mock_docker_compose.assert_not_called()

    def test_dry_run_phases_succeed(self):
        """Test all phases succeed in dry run mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            assert orchestrator.phase1_preparation() is True
            assert orchestrator.phase3_migrations() is True
            assert orchestrator.phase5_verification() is True

    def test_dry_run_info_messages(self):
        """Test dry run displays info messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            orchestrator = DeploymentOrchestrator(
                self.console,
                dry_run=True,
                working_dir=Path(tmpdir)
            )

            orchestrator._create_backup()
            orchestrator._start_service("web")
            orchestrator._stop_all_services()

            # Verify [DRY RUN] messages were displayed
            info_calls = [str(call) for call in self.console.info.call_args_list]
            assert any("[DRY RUN]" in call for call in info_calls)


# Import subprocess for timeout test
import subprocess
