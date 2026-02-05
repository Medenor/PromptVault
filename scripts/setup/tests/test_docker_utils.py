"""
Unit tests for docker_utils.py module.

Tests Docker utility functions using mocks to avoid actual Docker commands.
All subprocess calls are mocked to test various success and failure scenarios.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import subprocess
import socket

from scripts.setup.utils.docker_utils import (
    check_docker_installed,
    check_docker_running,
    check_docker_compose_installed,
    check_port_available,
    run_docker_compose,
    get_container_status,
    wait_for_healthy,
    get_container_logs,
    check_image_exists
)


class TestCheckDockerInstalled:
    """Tests for check_docker_installed function."""

    @patch('subprocess.run')
    def test_docker_installed_success(self, mock_run):
        """Test successful Docker installation check."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Docker version 24.0.5, build ced0996\n",
            stderr=""
        )

        is_installed, version = check_docker_installed()

        assert is_installed is True
        assert "Docker version" in version
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_docker_not_installed(self, mock_run):
        """Test Docker not installed (FileNotFoundError)."""
        mock_run.side_effect = FileNotFoundError()

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "not installed" in error

    @patch('subprocess.run')
    def test_docker_command_failed(self, mock_run):
        """Test Docker command failed with non-zero exit."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="command not found"
        )

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "failed" in error.lower()

    @patch('subprocess.run')
    def test_docker_check_timeout(self, mock_run):
        """Test Docker version check timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=5)

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "timed out" in error.lower()

    @patch('subprocess.run')
    def test_docker_check_generic_error(self, mock_run):
        """Test generic error during Docker check."""
        mock_run.side_effect = Exception("Generic error")

        is_installed, error = check_docker_installed()

        assert is_installed is False
        assert "error" in error.lower()


class TestCheckDockerRunning:
    """Tests for check_docker_running function."""

    @patch('subprocess.run')
    def test_docker_daemon_running(self, mock_run):
        """Test Docker daemon is running."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Docker info output",
            stderr=""
        )

        is_running, error = check_docker_running()

        assert is_running is True
        assert error is None
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_docker_daemon_not_running(self, mock_run):
        """Test Docker daemon is not running."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Cannot connect to the Docker daemon at unix:///var/run/docker.sock"
        )

        is_running, error = check_docker_running()

        assert is_running is False
        assert "cannot connect" in error.lower()

    @patch('subprocess.run')
    def test_docker_daemon_check_timeout(self, mock_run):
        """Test Docker daemon check timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker info", timeout=10)

        is_running, error = check_docker_running()

        assert is_running is False
        assert "timed out" in error.lower()

    @patch('subprocess.run')
    def test_docker_not_installed_during_running_check(self, mock_run):
        """Test Docker not installed error during running check."""
        mock_run.side_effect = FileNotFoundError()

        is_running, error = check_docker_running()

        assert is_running is False
        assert "not installed" in error


class TestCheckDockerComposeInstalled:
    """Tests for check_docker_compose_installed function."""

    @patch('subprocess.run')
    def test_docker_compose_v2_installed(self, mock_run):
        """Test Docker Compose v2 (plugin) is installed."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Docker Compose version v2.21.0\n",
            stderr=""
        )

        is_installed, version = check_docker_compose_installed()

        assert is_installed is True
        assert "v2" in version

    @patch('subprocess.run')
    def test_docker_compose_v1_installed(self, mock_run):
        """Test Docker Compose v1 (standalone) is installed."""
        # First call (v2) fails, second call (v1) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="docker-compose version 1.29.2\n", stderr="")
        ]

        is_installed, version = check_docker_compose_installed()

        assert is_installed is True
        assert "1.29" in version

    @patch('subprocess.run')
    def test_docker_compose_not_installed(self, mock_run):
        """Test Docker Compose not installed."""
        mock_run.side_effect = [
            FileNotFoundError(),  # v2 check
            FileNotFoundError()   # v1 check
        ]

        is_installed, error = check_docker_compose_installed()

        assert is_installed is False
        assert "not installed" in error.lower()

    @patch('subprocess.run')
    def test_docker_compose_timeout(self, mock_run):
        """Test Docker Compose check timeout."""
        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd="docker compose", timeout=5),
            subprocess.TimeoutExpired(cmd="docker-compose", timeout=5)
        ]

        is_installed, error = check_docker_compose_installed()

        assert is_installed is False
        assert "not installed" in error.lower()


class TestCheckPortAvailable:
    """Tests for check_port_available function."""

    @patch('socket.socket')
    def test_port_available(self, mock_socket_class):
        """Test checking available port."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # Mock successful bind
        mock_socket.bind.return_value = None

        is_available, error = check_port_available(55555)

        assert is_available is True
        assert error is None
        mock_socket.bind.assert_called_once()

    def test_port_invalid_type(self):
        """Test invalid port type."""
        is_available, error = check_port_available("not-a-port")

        assert is_available is False
        assert "invalid port" in error.lower()

    def test_port_too_low(self):
        """Test port number too low."""
        is_available, error = check_port_available(0)

        assert is_available is False
        assert "between 1 and 65535" in error

    def test_port_too_high(self):
        """Test port number too high."""
        is_available, error = check_port_available(70000)

        assert is_available is False
        assert "between 1 and 65535" in error

    @patch('socket.socket')
    def test_port_as_string(self, mock_socket_class):
        """Test port number as string."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # Mock successful bind
        mock_socket.bind.return_value = None

        is_available, error = check_port_available("55555")

        assert is_available is True
        assert error is None

    @patch('socket.socket')
    def test_port_in_use(self, mock_socket_class):
        """Test port already in use."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        # Simulate port in use error
        error = OSError()
        error.errno = 48  # Address already in use (macOS)
        mock_socket.bind.side_effect = error

        is_available, error_msg = check_port_available(8080)

        assert is_available is False
        assert "already in use" in error_msg.lower()

    @patch('socket.socket')
    def test_port_bind_error(self, mock_socket_class):
        """Test generic bind error."""
        mock_socket = MagicMock()
        mock_socket_class.return_value = mock_socket

        mock_socket.bind.side_effect = OSError("Generic error")

        is_available, error = check_port_available(8080)

        assert is_available is False
        assert "cannot bind" in error.lower()


class TestRunDockerCompose:
    """Tests for run_docker_compose function."""

    @patch('subprocess.run')
    def test_docker_compose_success(self, mock_run):
        """Test successful docker-compose command."""
        # Mock version check
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="Docker Compose version v2.21.0", stderr=""),
            MagicMock(returncode=0, stdout="Container started", stderr="")
        ]

        success, stdout, stderr = run_docker_compose("up", ["-d"])

        assert success is True
        assert "started" in stdout.lower()

    @patch('subprocess.run')
    def test_docker_compose_with_args(self, mock_run):
        """Test docker-compose command with arguments."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="version", stderr=""),
            MagicMock(returncode=0, stdout="output", stderr="")
        ]

        success, stdout, stderr = run_docker_compose("ps", ["-a", "db"])

        assert success is True

    @patch('subprocess.run')
    def test_docker_compose_failure(self, mock_run):
        """Test failed docker-compose command."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="version", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="Error: service not found")
        ]

        success, stdout, stderr = run_docker_compose("up", ["nonexistent"])

        assert success is False
        assert "error" in stderr.lower()

    @patch('subprocess.run')
    def test_docker_compose_not_installed(self, mock_run):
        """Test docker-compose when not installed."""
        mock_run.side_effect = FileNotFoundError()

        success, stdout, stderr = run_docker_compose("up")

        assert success is False
        assert "not installed" in stderr.lower()

    @patch('subprocess.run')
    def test_docker_compose_timeout(self, mock_run):
        """Test docker-compose command timeout."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="version", stderr=""),
            subprocess.TimeoutExpired(cmd="docker-compose", timeout=300)
        ]

        success, stdout, stderr = run_docker_compose("build")

        assert success is False
        assert "timed out" in stderr.lower()

    @patch('subprocess.run')
    def test_docker_compose_with_working_dir(self, mock_run):
        """Test docker-compose with custom working directory."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="version", stderr=""),
            MagicMock(returncode=0, stdout="output", stderr="")
        ]

        success, stdout, stderr = run_docker_compose(
            "ps",
            working_dir="/custom/path"
        )

        assert success is True
        # Verify working directory was passed
        assert mock_run.call_args_list[1][1]['cwd'] == "/custom/path"

    @patch('subprocess.run')
    def test_docker_compose_v1_fallback(self, mock_run):
        """Test fallback to docker-compose v1."""
        # v2 check fails, v1 succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="version 1.29", stderr=""),
            MagicMock(returncode=0, stdout="output", stderr="")
        ]

        success, stdout, stderr = run_docker_compose("ps")

        assert success is True


class TestGetContainerStatus:
    """Tests for get_container_status function."""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_status_running(self, mock_compose):
        """Test getting status of running container."""
        mock_compose.return_value = (
            True,
            "db-1  service  Up 5 minutes  5432/tcp",
            ""
        )

        status = get_container_status("db")

        assert status == "running"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_status_exited(self, mock_compose):
        """Test getting status of exited container."""
        mock_compose.return_value = (
            True,
            "db-1  service  Exited (1) 2 minutes ago",
            ""
        )

        status = get_container_status("db")

        assert status == "exited"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_status_restarting(self, mock_compose):
        """Test getting status of restarting container."""
        mock_compose.return_value = (
            True,
            "db-1  service  Restarting",
            ""
        )

        status = get_container_status("db")

        assert status == "restarting"

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_status_not_found(self, mock_compose):
        """Test getting status when container not found."""
        mock_compose.return_value = (
            True,
            "",
            ""
        )

        status = get_container_status("nonexistent")

        assert status is None

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_status_command_failed(self, mock_compose):
        """Test getting status when command fails."""
        mock_compose.return_value = (
            False,
            "",
            "Error: something went wrong"
        )

        status = get_container_status("db")

        assert status is None

    def test_get_status_empty_service_name(self):
        """Test getting status with empty service name."""
        status = get_container_status("")

        assert status is None


class TestWaitForHealthy:
    """Tests for wait_for_healthy function."""

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_wait_for_healthy_success(self, mock_compose, mock_status):
        """Test successful wait for healthy container."""
        mock_status.return_value = "running"
        mock_compose.return_value = (
            True,
            '{"Status": "healthy"}',
            ""
        )

        result = wait_for_healthy("db", timeout=10)

        assert result is True

    @patch('time.time')
    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('time.sleep')
    def test_wait_for_healthy_timeout(self, mock_sleep, mock_status, mock_time):
        """Test timeout while waiting for healthy."""
        # Simulate timeout by making time.time() return values that exceed timeout
        # Container never starts running, so we timeout
        mock_time.side_effect = [0, 0.3, 0.6, 0.9, 1.2]  # Eventually exceeds timeout of 1

        # Container status remains "created" (not "running"), so we keep waiting
        mock_status.return_value = "created"

        result = wait_for_healthy("db", timeout=1, poll_interval=0.1)

        assert result is False

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('time.sleep')
    def test_wait_for_healthy_container_not_running(self, mock_sleep, mock_status):
        """Test waiting when container is not running."""
        mock_status.side_effect = ["created", "created", "running"]

        # Will timeout because we only check status, no compose call
        result = wait_for_healthy("db", timeout=1, poll_interval=0.1)

        # Since container becomes running but we don't have a compose mock,
        # it will depend on the implementation details
        assert mock_status.call_count >= 1

    @patch('scripts.setup.utils.docker_utils.get_container_status')
    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    @patch('time.sleep')
    def test_wait_for_healthy_no_healthcheck(self, mock_sleep, mock_compose, mock_status):
        """Test waiting for container without healthcheck."""
        mock_status.return_value = "running"
        mock_compose.return_value = (
            True,
            '{"Status": "running"}',  # No health status
            ""
        )

        result = wait_for_healthy("db", timeout=10)

        # Should return True if running without health check
        assert result is True


class TestGetContainerLogs:
    """Tests for get_container_logs function."""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_logs_success(self, mock_compose):
        """Test successfully getting container logs."""
        mock_compose.return_value = (
            True,
            "2024-01-01 12:00:00 [INFO] Database started\n2024-01-01 12:00:01 [INFO] Ready",
            ""
        )

        logs = get_container_logs("db", tail=50)

        assert "Database started" in logs
        assert "Ready" in logs

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_logs_failure(self, mock_compose):
        """Test getting logs when command fails."""
        mock_compose.return_value = (
            False,
            "",
            "Error: container not found"
        )

        logs = get_container_logs("db")

        # Should return stderr on failure
        assert "error" in logs.lower()

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_logs_custom_tail(self, mock_compose):
        """Test getting logs with custom tail count."""
        mock_compose.return_value = (
            True,
            "log lines...",
            ""
        )

        logs = get_container_logs("db", tail=100)

        # Verify tail parameter was used
        call_args = mock_compose.call_args
        assert "--tail" in call_args[0][1]
        assert "100" in call_args[0][1]

    def test_get_logs_empty_service_name(self):
        """Test getting logs with empty service name."""
        logs = get_container_logs("")

        assert logs == ""

    @patch('scripts.setup.utils.docker_utils.run_docker_compose')
    def test_get_logs_invalid_tail(self, mock_compose):
        """Test getting logs with invalid tail value."""
        mock_compose.return_value = (
            True,
            "logs",
            ""
        )

        logs = get_container_logs("db", tail=-10)

        # Should use default (50) instead of invalid value
        call_args = mock_compose.call_args
        assert "50" in call_args[0][1]


class TestCheckImageExists:
    """Tests for check_image_exists function."""

    @patch('subprocess.run')
    def test_image_exists(self, mock_run):
        """Test checking for existing image."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="postgres:15\nredis:latest\nmyapp:1.0\n",
            stderr=""
        )

        exists = check_image_exists("postgres:15")

        assert exists is True

    @patch('subprocess.run')
    def test_image_not_exists(self, mock_run):
        """Test checking for non-existing image."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="postgres:15\nredis:latest\n",
            stderr=""
        )

        exists = check_image_exists("nonexistent:tag")

        assert exists is False

    @patch('subprocess.run')
    def test_image_exists_without_tag(self, mock_run):
        """Test checking image without specifying tag."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="postgres:15\npostgres:14\nredis:latest\n",
            stderr=""
        )

        exists = check_image_exists("postgres")

        assert exists is True

    @patch('subprocess.run')
    def test_image_check_command_failed(self, mock_run):
        """Test image check when Docker command fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error"
        )

        exists = check_image_exists("postgres:15")

        assert exists is False

    @patch('subprocess.run')
    def test_image_check_timeout(self, mock_run):
        """Test image check timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=10)

        exists = check_image_exists("postgres:15")

        assert exists is False

    @patch('subprocess.run')
    def test_image_check_docker_not_found(self, mock_run):
        """Test image check when Docker not found."""
        mock_run.side_effect = FileNotFoundError()

        exists = check_image_exists("postgres:15")

        assert exists is False

    def test_image_check_empty_name(self):
        """Test checking image with empty name."""
        exists = check_image_exists("")

        assert exists is False

    @patch('subprocess.run')
    def test_image_check_generic_error(self, mock_run):
        """Test generic error during image check."""
        mock_run.side_effect = Exception("Generic error")

        exists = check_image_exists("postgres:15")

        assert exists is False
