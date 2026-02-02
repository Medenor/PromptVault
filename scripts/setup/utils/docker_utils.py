"""
Docker utility functions for setup scripts.

Provides functions for Docker operations including:
- Checking Docker installation and status
- Running Docker Compose commands
- Container management and monitoring
- Port availability checking

Usage Example:
    from utils.docker_utils import (
        check_docker_installed,
        check_docker_running,
        run_docker_compose,
        wait_for_healthy
    )

    # Verify Docker is available
    is_installed, version = check_docker_installed()
    if not is_installed:
        print(f"Error: {version}")
        exit(1)

    # Check if daemon is running
    is_running, error = check_docker_running()
    if not is_running:
        print(f"Error: {error}")
        exit(1)

    # Start services
    success, stdout, stderr = run_docker_compose("up", ["-d"], working_dir="/path/to/project")
    if not success:
        print(f"Failed to start services: {stderr}")
        exit(1)

    # Wait for service to be healthy
    if wait_for_healthy("db", timeout=120):
        print("Database is ready!")
    else:
        print("Database failed to become healthy")
"""

import socket
import subprocess
import time
from typing import Tuple


def check_docker_installed() -> Tuple[bool, str | None]:
    """
    Verify Docker is installed.

    Runs `docker --version` to check if Docker is available.

    Returns:
        Tuple of (is_installed, version_or_error)
        - (True, version) if Docker is installed
        - (False, error_message) if not installed

    Examples:
        >>> check_docker_installed()
        (True, "Docker version 24.0.5, build ced0996")
        >>> check_docker_installed()  # If not installed
        (False, "Docker is not installed or not in PATH")
    """
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        else:
            return False, f"Docker command failed: {result.stderr.strip()}"

    except FileNotFoundError:
        return False, "Docker is not installed or not in PATH"
    except subprocess.TimeoutExpired:
        return False, "Docker version check timed out"
    except Exception as e:
        return False, f"Error checking Docker installation: {str(e)}"


def check_docker_running() -> Tuple[bool, str | None]:
    """
    Verify Docker daemon is running.

    Runs `docker info` to check if the Docker daemon is accessible.

    Returns:
        Tuple of (is_running, error_message)
        - (True, None) if Docker daemon is running
        - (False, error_message) if not running

    Examples:
        >>> check_docker_running()
        (True, None)
        >>> check_docker_running()  # If daemon not running
        (False, "Cannot connect to the Docker daemon. Is the docker daemon running?")
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True, None
        else:
            error_msg = result.stderr.strip()
            if "Cannot connect to the Docker daemon" in error_msg:
                return False, "Cannot connect to the Docker daemon. Is the docker daemon running?"
            return False, f"Docker daemon check failed: {error_msg}"

    except FileNotFoundError:
        return False, "Docker is not installed or not in PATH"
    except subprocess.TimeoutExpired:
        return False, "Docker daemon check timed out"
    except Exception as e:
        return False, f"Error checking Docker daemon: {str(e)}"


def check_docker_compose_installed() -> Tuple[bool, str | None]:
    """
    Verify Docker Compose is installed.

    Tries both `docker-compose` and `docker compose` commands to check availability.

    Returns:
        Tuple of (is_installed, version_or_error)
        - (True, version) if Docker Compose is installed
        - (False, error_message) if not installed

    Examples:
        >>> check_docker_compose_installed()
        (True, "Docker Compose version v2.21.0")
        >>> check_docker_compose_installed()  # If not installed
        (False, "Docker Compose is not installed")
    """
    # Try docker compose (v2 - plugin)
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass

    # Try docker-compose (v1 - standalone)
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    except Exception:
        pass

    return False, "Docker Compose is not installed (tried both 'docker compose' and 'docker-compose')"


def check_port_available(port: int) -> Tuple[bool, str | None]:
    """
    Check if a port is available for binding.

    Attempts to bind to the specified port to verify it's not in use.

    Args:
        port: Port number to check

    Returns:
        Tuple of (is_available, error_message)
        - (True, None) if port is available
        - (False, error_message) if port is in use

    Examples:
        >>> check_port_available(8080)
        (True, None)
        >>> check_port_available(80)
        (False, "Port 80 is already in use")
    """
    if not isinstance(port, int):
        try:
            port = int(port)
        except (ValueError, TypeError):
            return False, f"Invalid port number: {port}"

    if port < 1 or port > 65535:
        return False, f"Port must be between 1 and 65535, got {port}"

    # Try to bind to the port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # SO_REUSEADDR allows reusing addresses in TIME_WAIT state
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True, None
    except OSError as e:
        sock.close()
        if e.errno == 48 or e.errno == 98:  # Address already in use (macOS/Linux)
            return False, f"Port {port} is already in use"
        return False, f"Cannot bind to port {port}: {str(e)}"
    except Exception as e:
        sock.close()
        return False, f"Error checking port {port}: {str(e)}"


def run_docker_compose(
    command: str,
    args: list[str] | None = None,
    capture_output: bool = True,
    working_dir: str | None = None
) -> Tuple[bool, str, str]:
    """
    Execute docker-compose commands.

    Supports both `docker-compose` (v1) and `docker compose` (v2) commands.
    Automatically detects which version is available and uses it.

    Args:
        command: Docker Compose command to run (e.g., "up", "down", "ps")
        args: Optional list of additional arguments
        capture_output: Whether to capture stdout/stderr (default: True)
        working_dir: Working directory for the command (default: current directory)

    Returns:
        Tuple of (success, stdout, stderr)
        - success: True if command succeeded (exit code 0)
        - stdout: Standard output from the command
        - stderr: Standard error from the command

    Examples:
        >>> run_docker_compose("ps", ["-a"])
        (True, "container output...", "")
        >>> run_docker_compose("up", ["-d", "db"])
        (True, "", "")
        >>> run_docker_compose("invalid")
        (False, "", "unknown command: invalid")
    """
    if args is None:
        args = []

    # Determine which Docker Compose command to use
    compose_cmd = None

    # Try docker compose (v2 - plugin)
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            compose_cmd = ["docker", "compose"]
    except Exception:
        pass

    # Fall back to docker-compose (v1 - standalone)
    if compose_cmd is None:
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                compose_cmd = ["docker-compose"]
        except Exception:
            pass

    # If neither is available, return error
    if compose_cmd is None:
        return False, "", "Docker Compose is not installed or not available"

    # Build the full command
    full_cmd = compose_cmd + [command] + args

    # Execute the command
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=capture_output,
            text=True,
            cwd=working_dir,
            timeout=300  # 5 minute timeout for long operations
        )

        success = result.returncode == 0
        stdout = result.stdout if capture_output else ""
        stderr = result.stderr if capture_output else ""

        return success, stdout, stderr

    except subprocess.TimeoutExpired:
        return False, "", "Docker Compose command timed out after 5 minutes"
    except FileNotFoundError:
        return False, "", "Docker Compose command not found"
    except Exception as e:
        return False, "", f"Error running Docker Compose command: {str(e)}"


def get_container_status(service_name: str, working_dir: str | None = None) -> str | None:
    """
    Get the status of a Docker Compose service container.

    Runs `docker-compose ps` to retrieve the status of a specific service.

    Args:
        service_name: Name of the service to check
        working_dir: Working directory containing docker-compose.yml

    Returns:
        Status string (e.g., "running", "exited", "restarting") or None if not found

    Examples:
        >>> get_container_status("db")
        "running"
        >>> get_container_status("nonexistent")
        None
    """
    if not service_name:
        return None

    # Run docker-compose ps for the specific service
    success, stdout, stderr = run_docker_compose(
        "ps",
        ["-a", service_name],
        capture_output=True,
        working_dir=working_dir
    )

    if not success:
        return None

    # Parse the output to extract status
    lines = stdout.strip().split('\n')

    # Skip header lines and find the service
    for line in lines:
        if service_name in line:
            # Status is typically in the format:
            # NAME              SERVICE  STATUS
            # or for older versions:
            # Name   Command   State   Ports
            parts = line.split()

            # Try to find status indicators
            line_lower = line.lower()
            if "up" in line_lower or "running" in line_lower:
                return "running"
            elif "exit" in line_lower:
                return "exited"
            elif "restarting" in line_lower:
                return "restarting"
            elif "paused" in line_lower:
                return "paused"
            elif "created" in line_lower:
                return "created"

            # If we can't determine status but found the service, return unknown
            return "unknown"

    return None


def wait_for_healthy(
    service_name: str,
    timeout: int = 120,
    working_dir: str | None = None,
    poll_interval: int = 2
) -> bool:
    """
    Wait for a Docker Compose service to become healthy.

    Polls the container's health status until it becomes "healthy" or timeout occurs.
    Requires the service to have a HEALTHCHECK defined in docker-compose.yml.

    Args:
        service_name: Name of the service to wait for
        timeout: Maximum time to wait in seconds (default: 120)
        working_dir: Working directory containing docker-compose.yml
        poll_interval: Time between health checks in seconds (default: 2)

    Returns:
        True if service became healthy, False if timeout or error occurred

    Examples:
        >>> wait_for_healthy("db", timeout=60)
        True
        >>> wait_for_healthy("slow_service", timeout=10)
        False
    """
    if timeout <= 0:
        timeout = 120

    if poll_interval <= 0:
        poll_interval = 2

    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check if container is running first
        status = get_container_status(service_name, working_dir)

        if status is None:
            # Container doesn't exist
            time.sleep(poll_interval)
            continue

        if status != "running":
            # Container not running yet
            time.sleep(poll_interval)
            continue

        # Container is running, check health status
        try:
            # Get detailed container info using docker inspect
            success, stdout, stderr = run_docker_compose(
                "ps",
                ["--format", "json", service_name],
                capture_output=True,
                working_dir=working_dir
            )

            if success and stdout:
                # Check if health status is present
                output_lower = stdout.lower()
                if "healthy" in output_lower:
                    return True
                elif "unhealthy" in output_lower:
                    # Container is unhealthy, continue waiting
                    time.sleep(poll_interval)
                    continue
                else:
                    # No health check defined, just check if running
                    # If container is running without health check, consider it healthy
                    return True

            time.sleep(poll_interval)

        except Exception:
            time.sleep(poll_interval)
            continue

    # Timeout reached
    return False


def get_container_logs(
    service_name: str,
    tail: int = 50,
    working_dir: str | None = None
) -> str:
    """
    Get logs from a Docker Compose service container.

    Retrieves the last N lines of logs from the specified service.

    Args:
        service_name: Name of the service to get logs from
        tail: Number of lines to retrieve (default: 50)
        working_dir: Working directory containing docker-compose.yml

    Returns:
        Log output as string, or empty string if error occurred

    Examples:
        >>> get_container_logs("db", tail=100)
        "2024-01-01 12:00:00 [INFO] Database started\\n..."
        >>> get_container_logs("nonexistent")
        ""
    """
    if not service_name:
        return ""

    if tail <= 0:
        tail = 50

    # Run docker-compose logs
    success, stdout, stderr = run_docker_compose(
        "logs",
        ["--tail", str(tail), service_name],
        capture_output=True,
        working_dir=working_dir
    )

    if success:
        return stdout
    else:
        # Return stderr if there was an error (might contain useful info)
        return stderr if stderr else ""


def check_image_exists(image_name: str) -> bool:
    """
    Check if a Docker image exists locally.

    Runs `docker images` to search for the specified image.

    Args:
        image_name: Name of the image to check (e.g., "postgres:15", "myapp:latest")

    Returns:
        True if image exists locally, False otherwise

    Examples:
        >>> check_image_exists("postgres:15")
        True
        >>> check_image_exists("nonexistent:tag")
        False
    """
    if not image_name:
        return False

    try:
        # Use docker images with format to get just the repository:tag
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return False

        # Parse output to find the image
        images = result.stdout.strip().split('\n')

        # Handle both full names (repo:tag) and partial matches
        for image in images:
            if image == image_name:
                return True
            # Also check without tag if only repo name provided
            if ':' not in image_name and image.startswith(f"{image_name}:"):
                return True

        return False

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    except Exception:
        return False
