# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for Docker utility functions."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from scripts.setup.utils.docker_utils import (
    check_docker_installed,
    check_docker_running,
    check_docker_compose_installed,
    check_port_available,
    run_docker_compose,
    get_container_status,
    wait_for_healthy,
    get_container_logs,
    check_image_exists,
)


class TestCheckDockerInstalled:
    """Test Docker installation check."""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_installed(self, mock_run):
        """Test when Docker is installed."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker version 24.0.5, build ced0996"
        mock_run.return_value = mock_result

        is_installed, version = check_docker_installed()

        assert is_installed is True
        assert "Docker version" in version
        mock_run.assert_called_once()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_not_installed(self, mock_run):
        """Test when Docker is not installed."""
        mock_run.side_effect = FileNotFoundError()

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "not installed" in error

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_command_failed(self, mock_run):
        """Test when Docker command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Command failed"
        mock_run.return_value = mock_result

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "failed" in error.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_timeout(self, mock_run):
        """Test when Docker command times out."""
        mock_run.side_effect = TimeoutError()

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "timeout" in error.lower() or "error" in error.lower()


class TestCheckDockerRunning:
    """Test Docker daemon running check."""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_running(self, mock_run):
        """Test when Docker daemon is running."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        is_running, error = check_docker_running()

        assert is_running is True
        assert error is None

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_not_running(self, mock_run):
        """Test when Docker daemon is not running."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Cannot connect to the Docker daemon"
        mock_run.return_value = mock_result

        is_running, error = check_docker_running()

        assert is_running is False
        assert "daemon" in error.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_command_not_found(self, mock_run):
        """Test when Docker command not found."""
        mock_run.side_effect = FileNotFoundError()

        is_running, error = check_docker_running()

        assert is_running is False
        assert "not installed" in error.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_info_timeout(self, mock_run):
        """Test when docker info times out."""
        mock_run.side_effect = TimeoutError()

        is_running, error = check_docker_running()

        assert is_running is False
        assert "timeout" in error.lower() or "error" in error.lower()


class TestCheckDockerComposeInstalled:
    """Test Docker Compose installation check."""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_compose_v2_installed(self, mock_run):
        """Test when Docker Compose v2 is installed."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker Compose version v2.21.0"
        mock_run.return_value = mock_result

        is_installed, version = check_docker_compose_installed()

        assert is_installed is True
        assert "v2" in version or "version" in version.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_compose_v1_installed(self, mock_run):
        """Test when Docker Compose v1 is installed."""
        # First call (v2) fails, second call (v1) succeeds
        mock_result_v2 = Mock()
        mock_result_v2.returncode = 1

        mock_result_v1 = Mock()
        mock_result_v1.returncode = 0
        mock_result_v1.stdout = "docker-compose version 1.29.2"

        mock_run.side_effect = [mock_result_v2, mock_result_v1]

        is_installed, version = check_docker_compose_installed()

        assert is_installed is True
        assert "version" in version.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_docker_compose_not_installed(self, mock_run):
        """Test when Docker Compose is not installed."""
        mock_run.side_effect = FileNotFoundError()

        is_installed, error = check_docker_compose_installed()

        assert is_installed is False
        assert "not installed" in error.lower()


class TestCheckPortAvailable:
    """Test port availability check."""

    def test_port_available(self):
        """Test checking an available port."""
        # Use a high port number that's likely available
        is_available, error = check_port_available(54321)

        # Port might be in use in test environment, so we just check the function runs
        assert isinstance(is_available, bool)

    def test_port_invalid_type(self):
        """Test with invalid port type."""
        is_available, error = check_port_available("not-a-number")

        assert is_available is False
        assert "invalid" in error.lower()

    def test_port_below_minimum(self):
        """Test port below minimum."""
        is_available, error = check_port_available(0)

        assert is_available is False
        assert "between 1 and 65535" in error

    def test_port_above_maximum(self):
        """Test port above maximum."""
        is_available, error = check_port_available(70000)

        assert is_available is False
        assert "between 1 and 65535" in error

    def test_port_negative(self):
        """Test negative port."""
        is_available, error = check_port_available(-1)

        assert is_available is False
        assert error is not None

    def test_port_string_valid(self):
        """Test valid port as string."""
        is_available, error = check_port_available("54322")

        assert isinstance(is_available, bool)


class TestRunDockerCompose:
    """Test running Docker Compose commands."""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_v2(self, mock_run):
        """Test running Docker Compose v2 command."""
        # First call checks for v2 (succeeds)
        mock_version_check = Mock()
        mock_version_check.returncode = 0
        mock_version_check.stdout = "Docker Compose version v2.21.0"

        # Second call runs the actual command
        mock_command = Mock()
        mock_command.returncode = 0
        mock_command.stdout = "Container started"
        mock_command.stderr = ""

        mock_run.side_effect = [mock_version_check, mock_command]

        success, stdout, stderr = run_docker_compose("up", ["-d"])

        assert success is True
        assert "Container started" in stdout

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_v1(self, mock_run):
        """Test running Docker Compose v1 command."""
        # First call checks for v2 (fails)
        mock_v2_check = Mock()
        mock_v2_check.returncode = 1

        # Second call checks for v1 (succeeds)
        mock_v1_check = Mock()
        mock_v1_check.returncode = 0
        mock_v1_check.stdout = "docker-compose version 1.29.2"

        # Third call runs the actual command
        mock_command = Mock()
        mock_command.returncode = 0
        mock_command.stdout = "Services started"
        mock_command.stderr = ""

        mock_run.side_effect = [Exception(), mock_v1_check, mock_command]

        success, stdout, stderr = run_docker_compose("ps")

        assert success is True

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_command_failed(self, mock_run):
        """Test when Docker Compose command fails."""
        # Version check succeeds
        mock_version_check = Mock()
        mock_version_check.returncode = 0

        # Command fails
        mock_command = Mock()
        mock_command.returncode = 1
        mock_command.stdout = ""
        mock_command.stderr = "Error: container not found"

        mock_run.side_effect = [mock_version_check, mock_command]

        success, stdout, stderr = run_docker_compose("stop", ["nonexistent"])

        assert success is False
        assert "Error" in stderr or stderr == ""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_not_installed(self, mock_run):
        """Test when Docker Compose is not installed."""
        mock_run.side_effect = Exception()

        success, stdout, stderr = run_docker_compose("ps")

        assert success is False
        assert "not installed" in stderr.lower() or "not available" in stderr.lower()

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_with_working_dir(self, mock_run):
        """Test running Docker Compose with working directory."""
        mock_version_check = Mock()
        mock_version_check.returncode = 0

        mock_command = Mock()
        mock_command.returncode = 0
        mock_command.stdout = "OK"
        mock_command.stderr = ""

        mock_run.side_effect = [mock_version_check, mock_command]

        success, stdout, stderr = run_docker_compose(
            "ps",
            working_dir="/path/to/project"
        )

        assert success is True

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_run_docker_compose_with_args(self, mock_run):
        """Test running Docker Compose with additional arguments."""
        mock_version_check = Mock()
        mock_version_check.returncode = 0

        mock_command = Mock()
        mock_command.returncode = 0
        mock_command.stdout = "Services started"
        mock_command.stderr = ""

        mock_run.side_effect = [mock_version_check, mock_command]

        success, stdout, stderr = run_docker_compose("up", ["-d", "--build"])

        assert success is True


class TestGetContainerStatus:
    """Test getting container status."""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_running_container_status(self, mock_compose):
        """Test getting status of running container."""
        mock_compose.return_value = (
            True,
            "NAME          SERVICE     STATUS\ndb_container  db          Up 5 minutes",
            ""
        )

        status = get_container_status("db")

        assert status == "running"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_exited_container_status(self, mock_compose):
        """Test getting status of exited container."""
        mock_compose.return_value = (
            True,
            "NAME          SERVICE     STATUS\napp_container app         Exit 1",
            ""
        )

        status = get_container_status("app")

        assert status == "exited"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_restarting_container_status(self, mock_compose):
        """Test getting status of restarting container."""
        mock_compose.return_value = (
            True,
            "NAME          SERVICE     STATUS\nweb_container web         Restarting",
            ""
        )

        status = get_container_status("web")

        assert status == "restarting"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_nonexistent_container_status(self, mock_compose):
        """Test getting status of nonexistent container."""
        mock_compose.return_value = (True, "NAME  SERVICE  STATUS\n", "")

        status = get_container_status("nonexistent")

        assert status is None

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_container_status_command_failed(self, mock_compose):
        """Test when docker-compose ps fails."""
        mock_compose.return_value = (False, "", "Error")

        status = get_container_status("db")

        assert status is None

    def test_get_container_status_empty_name(self):
        """Test with empty container name."""
        status = get_container_status("")

        assert status is None


class TestWaitForHealthy:
    """Test waiting for container to become healthy."""

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    @patch('scripts.setup.utils.docker_utils.time.sleep')
    def test_wait_for_healthy_success(self, mock_sleep, mock_compose, mock_status):
        """Test waiting for container that becomes healthy."""
        mock_status.return_value = "running"
        mock_compose.return_value = (True, '{"Health": "healthy"}', "")

        result = wait_for_healthy("db", timeout=10, poll_interval=1)

        assert result is True

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.time.sleep')
    def test_wait_for_healthy_timeout(self, mock_sleep, mock_status):
        """Test waiting for container that times out."""
        mock_status.return_value = None

        result = wait_for_healthy("db", timeout=1, poll_interval=1)

        assert result is False

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    @patch('scripts.setup.utils.docker_utils.time.sleep')
    def test_wait_for_healthy_no_healthcheck(self, mock_sleep, mock_compose, mock_status):
        """Test waiting for container without healthcheck."""
        mock_status.return_value = "running"
        mock_compose.return_value = (True, '{"Status": "running"}', "")

        result = wait_for_healthy("db", timeout=10, poll_interval=1)

        # Container running without healthcheck should be considered healthy
        assert result is True

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.time.sleep')
    def test_wait_for_healthy_not_running(self, mock_sleep, mock_status):
        """Test waiting for container that's not running."""
        mock_status.return_value = "exited"

        result = wait_for_healthy("db", timeout=2, poll_interval=1)

        assert result is False

    @patch('scripts.setup.utils.docker_utils.get_container_health_status')
    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.time.sleep')
    def test_wait_for_healthy_becomes_unhealthy(self, mock_sleep, mock_status, mock_health):
        """Test waiting for container that becomes unhealthy."""
        mock_status.return_value = "running"
        mock_health.return_value = "unhealthy"

        result = wait_for_healthy("db", timeout=2, poll_interval=1)

        assert result is False

    def test_wait_for_healthy_invalid_timeout(self):
        """Test with invalid timeout value."""
        with patch('scripts.setup.utils.docker_utils.get_container_status') as mock_status:
            mock_status.return_value = None
            result = wait_for_healthy("db", timeout=0, poll_interval=1)
            assert result is False

    def test_wait_for_healthy_invalid_poll_interval(self):
        """Test with invalid poll interval."""
        with patch('scripts.setup.utils.docker_utils.get_container_status') as mock_status:
            mock_status.return_value = None
            result = wait_for_healthy("db", timeout=1, poll_interval=0)
            assert result is False


class TestGetContainerLogs:
    """Test getting container logs."""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_container_logs_success(self, mock_compose):
        """Test getting logs successfully."""
        mock_compose.return_value = (
            True,
            "2024-01-01 12:00:00 [INFO] Database started\n",
            ""
        )

        logs = get_container_logs("db", tail=50)

        assert "Database started" in logs

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_container_logs_failed(self, mock_compose):
        """Test when getting logs fails."""
        mock_compose.return_value = (False, "", "Error: container not found")

        logs = get_container_logs("nonexistent")

        assert "Error" in logs or logs == ""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_container_logs_custom_tail(self, mock_compose):
        """Test getting logs with custom tail value."""
        mock_compose.return_value = (True, "Log line\n", "")

        logs = get_container_logs("db", tail=100)

        assert logs == "Log line\n"

    def test_get_container_logs_empty_name(self):
        """Test with empty container name."""
        logs = get_container_logs("")

        assert logs == ""

    def test_get_container_logs_invalid_tail(self):
        """Test with invalid tail value."""
        with patch('scripts.setup.utils.docker_utils.run_docker_compose') as mock_compose:
            mock_compose.return_value = (True, "Logs\n", "")
            logs = get_container_logs("db", tail=0)
            # Should use default tail value
            assert isinstance(logs, str)


class TestCheckImageExists:
    """Test checking if Docker image exists."""

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_image_exists_exact_match(self, mock_run):
        """Test when image exists with exact name match."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "postgres:15\nredis:latest\nmyapp:1.0\n"
        mock_run.return_value = mock_result

        exists = check_image_exists("postgres:15")

        assert exists is True

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_image_exists_without_tag(self, mock_run):
        """Test when image exists without specifying tag."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "postgres:15\npostgres:14\nredis:latest\n"
        mock_run.return_value = mock_result

        exists = check_image_exists("postgres")

        assert exists is True

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_image_not_exists(self, mock_run):
        """Test when image does not exist."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "postgres:15\nredis:latest\n"
        mock_run.return_value = mock_result

        exists = check_image_exists("nonexistent:tag")

        assert exists is False

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_check_image_command_failed(self, mock_run):
        """Test when docker images command fails."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        exists = check_image_exists("postgres:15")

        assert exists is False

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_check_image_docker_not_found(self, mock_run):
        """Test when Docker is not installed."""
        mock_run.side_effect = FileNotFoundError()

        exists = check_image_exists("postgres:15")

        assert exists is False

    def test_check_image_empty_name(self):
        """Test with empty image name."""
        exists = check_image_exists("")

        assert exists is False

    @patch('scripts.setup.utils.docker_utils.subprocess.run')
    def test_check_image_timeout(self, mock_run):
        """Test when command times out."""
        mock_run.side_effect = TimeoutError()

        exists = check_image_exists("postgres:15")

        assert exists is False
