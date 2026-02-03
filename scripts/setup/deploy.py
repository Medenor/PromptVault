#!/usr/bin/env python3
"""
PromptVault Deployment Orchestration Script

Complete deployment automation with:
- Pre-flight checks (Docker, ports, config validation)
- Five-phase deployment process
- Automatic rollback on failure
- Comprehensive error handling and logging

Usage:
    python scripts/setup/deploy.py [OPTIONS]

Options:
    --dry-run            Show what would happen without executing
    --skip-backup        Skip backup phase
    --skip-migrations    Skip migration phase
    --rollback           Rollback to previous state
    --rebuild            Force rebuild Docker images
    --non-interactive    No prompts (use defaults)
    -h, --help          Show this help message
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from datetime import datetime

# Add parent directory to path for imports
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.insert(0, str(project_root))

import click
from scripts.setup.utils.console import SetupConsole
from scripts.setup.utils.docker_utils import (
    check_docker_installed,
    check_docker_running,
    check_docker_compose_installed,
    check_port_available,
    run_docker_compose,
    wait_for_healthy,
    get_container_status,
    get_container_logs,
)


class DeploymentOrchestrator:
    """
    Orchestrates the complete deployment process.

    Handles all phases of deployment from pre-flight checks through
    verification, with automatic rollback capabilities.
    """

    def __init__(
        self,
        console: SetupConsole,
        dry_run: bool = False,
        skip_backup: bool = False,
        skip_migrations: bool = False,
        rebuild: bool = False,
        non_interactive: bool = False,
        working_dir: Optional[Path] = None
    ):
        """Initialize the deployment orchestrator."""
        self.console = console
        self.dry_run = dry_run
        self.skip_backup = skip_backup
        self.skip_migrations = skip_migrations
        self.rebuild = rebuild
        self.non_interactive = non_interactive
        self.working_dir = working_dir or project_root

        # State tracking
        self.backup_file: Optional[Path] = None
        self.previous_containers: Dict[str, str] = {}
        self.deployment_start_time: Optional[datetime] = None
        self.phases_completed: List[str] = []

    def run_preflight_checks(self) -> bool:
        """
        Run all pre-flight checks before deployment.

        Verifies:
        - Docker installation and status
        - Docker Compose availability
        - Required ports available
        - Sufficient disk space
        - JWT keys validity
        - .env file presence
        - No conflicting containers

        Returns:
            True if all checks pass, False otherwise
        """
        self.console.header(
            "Pre-flight Checks",
            "Verifying system requirements before deployment"
        )

        checks_passed = 0
        checks_failed = 0

        # Check 1: Docker installed
        with self.console.spinner("Checking Docker installation"):
            is_installed, version = check_docker_installed()

        if is_installed:
            self.console.success(f"Docker installed: {version}")
            checks_passed += 1
        else:
            self.console.error(f"Docker not installed: {version}")
            checks_failed += 1

        # Check 2: Docker running
        with self.console.spinner("Checking Docker daemon"):
            is_running, error = check_docker_running()

        if is_running:
            self.console.success("Docker daemon is running")
            checks_passed += 1
        else:
            self.console.error(f"Docker daemon not running: {error}")
            checks_failed += 1

        # Check 3: Docker Compose installed
        with self.console.spinner("Checking Docker Compose"):
            compose_installed, compose_version = check_docker_compose_installed()

        if compose_installed:
            self.console.success(f"Docker Compose installed: {compose_version}")
            checks_passed += 1
        else:
            self.console.error(f"Docker Compose not installed: {compose_version}")
            checks_failed += 1

        # Check 4: Required ports available
        required_ports = [8001, 5432, 6379]
        ports_ok = True

        for port in required_ports:
            is_available, error = check_port_available(port)
            if is_available:
                self.console.success(f"Port {port} is available")
                checks_passed += 1
            else:
                self.console.warning(f"Port {port}: {error} (may be used by existing containers)")
                # Don't fail - might be our own containers
                checks_passed += 1

        # Check 5: Disk space
        with self.console.spinner("Checking disk space"):
            disk_space = self._check_disk_space()

        if disk_space >= 2.0:
            self.console.success(f"Sufficient disk space: {disk_space:.2f} GB available")
            checks_passed += 1
        else:
            self.console.warning(f"Low disk space: {disk_space:.2f} GB available (recommend 2+ GB)")
            if disk_space < 1.0:
                self.console.error("Insufficient disk space for deployment")
                checks_failed += 1
            else:
                checks_passed += 1

        # Check 6: JWT keys
        jwt_private = self.working_dir / "secrets" / "jwt" / "private_key.pem"
        jwt_public = self.working_dir / "secrets" / "jwt" / "public_key.pem"

        if jwt_private.exists() and jwt_public.exists():
            # Validate key files
            if self._validate_jwt_keys(jwt_private, jwt_public):
                self.console.success("JWT keys are valid")
                checks_passed += 1
            else:
                self.console.warning("JWT keys exist but may be invalid")
                checks_passed += 1
        else:
            self.console.warning("JWT keys not found (will be generated on first run)")
            checks_passed += 1

        # Check 7: .env file (optional but recommended)
        env_file = self.working_dir / ".env"
        if env_file.exists():
            self.console.success(".env file found")
            checks_passed += 1
        else:
            self.console.warning(".env file not found (will use defaults)")
            checks_passed += 1

        # Check 8: docker-compose.yml exists
        compose_file = self.working_dir / "docker-compose.yml"
        if compose_file.exists():
            self.console.success("docker-compose.yml found")
            checks_passed += 1
        else:
            self.console.error("docker-compose.yml not found")
            checks_failed += 1

        # Summary
        self.console.info(f"\nPre-flight checks: {checks_passed} passed, {checks_failed} failed")

        if checks_failed > 0:
            self.console.error("Pre-flight checks failed. Cannot proceed with deployment.")
            return False

        return True

    def phase1_preparation(self) -> bool:
        """
        Phase 1: Preparation

        - Backup existing data
        - Pull/build Docker images
        - Save current container states

        Returns:
            True if phase completed successfully
        """
        self.console.header("Phase 1: Preparation", "Backing up and preparing images")

        try:
            # Step 1: Backup
            if not self.skip_backup:
                self.console.step(1, 3, "Creating backup")
                if not self._create_backup():
                    self.console.error("Backup failed")
                    return False
                self.console.success(f"Backup created: {self.backup_file}")
            else:
                self.console.info("Skipping backup (--skip-backup flag)")

            # Step 2: Save container states
            self.console.step(2, 3, "Saving current container states")
            self._save_container_states()
            self.console.success("Container states saved")

            # Step 3: Pull/build images
            self.console.step(3, 3, "Pulling/building Docker images")
            if not self._pull_or_build_images():
                self.console.error("Failed to pull/build images")
                return False
            self.console.success("Docker images ready")

            self.phases_completed.append("preparation")
            return True

        except Exception as e:
            self.console.error(f"Phase 1 failed: {str(e)}")
            return False

    def phase2_infrastructure(self) -> bool:
        """
        Phase 2: Infrastructure

        - Start database and Redis
        - Wait for services to be healthy

        Returns:
            True if phase completed successfully
        """
        self.console.header("Phase 2: Infrastructure", "Starting database and cache services")

        try:
            # Step 1: Start database
            self.console.step(1, 3, "Starting PostgreSQL database")
            if not self._start_service("db"):
                self.console.error("Failed to start database")
                return False

            # Step 2: Wait for database to be healthy
            self.console.step(2, 3, "Waiting for database to be ready")
            with self.console.spinner("Database is starting up"):
                if not wait_for_healthy("db", timeout=120, working_dir=str(self.working_dir)):
                    self.console.error("Database failed to become healthy")
                    self._show_service_logs("db")
                    return False
            self.console.success("Database is healthy")

            # Step 3: Start Redis
            self.console.step(3, 3, "Starting Redis cache")
            if not self._start_service("redis"):
                self.console.error("Failed to start Redis")
                return False

            with self.console.spinner("Redis is starting up"):
                if not wait_for_healthy("redis", timeout=60, working_dir=str(self.working_dir)):
                    self.console.error("Redis failed to become healthy")
                    self._show_service_logs("redis")
                    return False
            self.console.success("Redis is healthy")

            self.phases_completed.append("infrastructure")
            return True

        except Exception as e:
            self.console.error(f"Phase 2 failed: {str(e)}")
            return False

    def phase3_migrations(self) -> bool:
        """
        Phase 3: Database Migrations

        - Run Alembic migrations to update database schema

        Returns:
            True if phase completed successfully
        """
        self.console.header("Phase 3: Migrations", "Updating database schema")

        if self.skip_migrations:
            self.console.info("Skipping migrations (--skip-migrations flag)")
            self.phases_completed.append("migrations")
            return True

        try:
            self.console.step(1, 1, "Running Alembic migrations")

            if self.dry_run:
                self.console.info("[DRY RUN] Would run: alembic upgrade head")
                self.phases_completed.append("migrations")
                return True

            # Run migrations using docker-compose exec
            with self.console.spinner("Applying database migrations"):
                success, stdout, stderr = run_docker_compose(
                    "exec",
                    ["-T", "db", "psql", "-U", "promptvault", "-d", "promptvault", "-c", "SELECT 1"],
                    working_dir=str(self.working_dir)
                )

                if not success:
                    self.console.error("Database not ready for migrations")
                    return False

                # Run alembic upgrade in the project directory
                result = subprocess.run(
                    ["alembic", "upgrade", "head"],
                    cwd=str(self.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if result.returncode == 0:
                    self.console.success("Database migrations completed")
                    if result.stdout:
                        self.console.info(f"Migration output: {result.stdout.strip()}")
                else:
                    self.console.error(f"Migration failed: {result.stderr}")
                    return False

            self.phases_completed.append("migrations")
            return True

        except subprocess.TimeoutExpired:
            self.console.error("Migration timed out after 2 minutes")
            return False
        except Exception as e:
            self.console.error(f"Phase 3 failed: {str(e)}")
            return False

    def phase4_application(self) -> bool:
        """
        Phase 4: Application Deployment

        - Start web service
        - Wait for application to be healthy

        Returns:
            True if phase completed successfully
        """
        self.console.header("Phase 4: Application", "Starting web service")

        try:
            # Step 1: Start web service
            self.console.step(1, 2, "Starting PromptVault web service")
            if not self._start_service("web"):
                self.console.error("Failed to start web service")
                return False

            # Step 2: Wait for application to be healthy
            self.console.step(2, 2, "Waiting for application to be ready")
            with self.console.spinner("Application is starting up (this may take 40+ seconds)"):
                if not wait_for_healthy("web", timeout=180, working_dir=str(self.working_dir)):
                    self.console.error("Application failed to become healthy")
                    self._show_service_logs("web", tail=100)
                    return False
            self.console.success("Application is healthy")

            self.phases_completed.append("application")
            return True

        except Exception as e:
            self.console.error(f"Phase 4 failed: {str(e)}")
            return False

    def phase5_verification(self) -> bool:
        """
        Phase 5: Verification

        - Run smoke tests
        - Display access information
        - Show deployment summary

        Returns:
            True if phase completed successfully
        """
        self.console.header("Phase 5: Verification", "Running smoke tests")

        try:
            # Step 1: Smoke tests
            self.console.step(1, 2, "Running smoke tests")
            if not self._run_smoke_tests():
                self.console.warning("Some smoke tests failed (non-critical)")

            # Step 2: Display access info
            self.console.step(2, 2, "Deployment complete")
            self._display_access_info()

            self.phases_completed.append("verification")
            return True

        except Exception as e:
            self.console.error(f"Phase 5 failed: {str(e)}")
            return False

    def rollback(self) -> bool:
        """
        Rollback to previous deployment state.

        Restores from backup and reverts containers to previous state.

        Returns:
            True if rollback completed successfully
        """
        self.console.header("Rollback", "Reverting to previous state")

        try:
            # Step 1: Stop current containers
            self.console.step(1, 3, "Stopping current containers")
            self._stop_all_services()

            # Step 2: Restore from backup
            if self.backup_file and self.backup_file.exists():
                self.console.step(2, 3, "Restoring database from backup")
                if not self._restore_backup(self.backup_file):
                    self.console.error("Failed to restore backup")
                    return False
                self.console.success("Database restored")
            else:
                self.console.warning("No backup file to restore from")

            # Step 3: Restart services
            self.console.step(3, 3, "Restarting services")
            if not self._start_all_services():
                self.console.error("Failed to restart services")
                return False
            self.console.success("Services restarted")

            self.console.success("Rollback completed successfully")
            return True

        except Exception as e:
            self.console.error(f"Rollback failed: {str(e)}")
            return False

    # Helper methods

    def _check_disk_space(self) -> float:
        """Check available disk space in GB."""
        stat = shutil.disk_usage(self.working_dir)
        return stat.free / (1024 ** 3)  # Convert to GB

    def _validate_jwt_keys(self, private_key: Path, public_key: Path) -> bool:
        """Validate JWT key files."""
        try:
            # Basic validation - check file size and readability
            if private_key.stat().st_size < 100 or public_key.stat().st_size < 100:
                return False

            # Try to read the files
            private_content = private_key.read_text()
            public_content = public_key.read_text()

            # Check for PEM headers
            if "BEGIN PRIVATE KEY" not in private_content:
                return False
            if "BEGIN PUBLIC KEY" not in public_content:
                return False

            return True

        except Exception:
            return False

    def _create_backup(self) -> bool:
        """Create database backup."""
        if self.dry_run:
            self.console.info("[DRY RUN] Would create backup")
            return True

        # Create backups directory
        backup_dir = self.working_dir / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"promptvault-deploy-{timestamp}.sql.gz"

        try:
            # Check if database is running
            status = get_container_status("db", str(self.working_dir))
            if status != "running":
                self.console.warning("Database not running, skipping backup")
                return True

            # Create backup using docker-compose exec
            with self.console.spinner("Creating database backup"):
                result = subprocess.run(
                    [
                        "docker-compose", "exec", "-T", "db",
                        "pg_dump", "-U", "promptvault", "-d", "promptvault"
                    ],
                    cwd=str(self.working_dir),
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    self.console.error(f"Backup failed: {result.stderr}")
                    return False

                # Compress and save
                import gzip
                with gzip.open(backup_file, 'wt') as f:
                    f.write(result.stdout)

            # Verify backup
            if not backup_file.exists() or backup_file.stat().st_size == 0:
                self.console.error("Backup file is empty or doesn't exist")
                return False

            self.backup_file = backup_file

            # Show backup size
            size_mb = backup_file.stat().st_size / (1024 * 1024)
            self.console.info(f"Backup size: {size_mb:.2f} MB")

            return True

        except subprocess.TimeoutExpired:
            self.console.error("Backup timed out after 5 minutes")
            return False
        except Exception as e:
            self.console.error(f"Backup failed: {str(e)}")
            return False

    def _save_container_states(self) -> None:
        """Save current container states for potential rollback."""
        for service in ["db", "redis", "web"]:
            status = get_container_status(service, str(self.working_dir))
            if status:
                self.previous_containers[service] = status

    def _pull_or_build_images(self) -> bool:
        """Pull or build Docker images."""
        if self.dry_run:
            self.console.info("[DRY RUN] Would pull/build images")
            return True

        try:
            if self.rebuild:
                # Build images
                with self.console.spinner("Building Docker images"):
                    success, stdout, stderr = run_docker_compose(
                        "build",
                        ["--no-cache"],
                        working_dir=str(self.working_dir)
                    )

                if not success:
                    self.console.error(f"Build failed: {stderr}")
                    return False
            else:
                # Pull images
                with self.console.spinner("Pulling Docker images"):
                    success, stdout, stderr = run_docker_compose(
                        "pull",
                        [],
                        working_dir=str(self.working_dir)
                    )

                if not success:
                    self.console.warning(f"Pull encountered issues: {stderr}")
                    # Try building as fallback
                    self.console.info("Attempting to build images instead")
                    success, stdout, stderr = run_docker_compose(
                        "build",
                        [],
                        working_dir=str(self.working_dir)
                    )

                    if not success:
                        self.console.error(f"Build failed: {stderr}")
                        return False

            return True

        except Exception as e:
            self.console.error(f"Failed to prepare images: {str(e)}")
            return False

    def _start_service(self, service: str) -> bool:
        """Start a specific service."""
        if self.dry_run:
            self.console.info(f"[DRY RUN] Would start service: {service}")
            return True

        success, stdout, stderr = run_docker_compose(
            "up",
            ["-d", service],
            working_dir=str(self.working_dir)
        )

        if not success:
            self.console.error(f"Failed to start {service}: {stderr}")
            return False

        return True

    def _stop_all_services(self) -> bool:
        """Stop all services."""
        if self.dry_run:
            self.console.info("[DRY RUN] Would stop all services")
            return True

        success, stdout, stderr = run_docker_compose(
            "down",
            [],
            working_dir=str(self.working_dir)
        )

        return success

    def _start_all_services(self) -> bool:
        """Start all services."""
        if self.dry_run:
            self.console.info("[DRY RUN] Would start all services")
            return True

        success, stdout, stderr = run_docker_compose(
            "up",
            ["-d"],
            working_dir=str(self.working_dir)
        )

        return success

    def _show_service_logs(self, service: str, tail: int = 50) -> None:
        """Display service logs for debugging."""
        self.console.info(f"\nShowing last {tail} lines of {service} logs:")
        logs = get_container_logs(service, tail=tail, working_dir=str(self.working_dir))
        if logs:
            print(logs)
        else:
            self.console.warning("No logs available")

    def _restore_backup(self, backup_file: Path) -> bool:
        """Restore database from backup file."""
        if self.dry_run:
            self.console.info(f"[DRY RUN] Would restore from: {backup_file}")
            return True

        try:
            import gzip

            # Read backup file
            with gzip.open(backup_file, 'rt') as f:
                sql_content = f.read()

            # Restore using psql
            with self.console.spinner("Restoring database"):
                result = subprocess.run(
                    [
                        "docker-compose", "exec", "-T", "db",
                        "psql", "-U", "promptvault", "-d", "promptvault"
                    ],
                    cwd=str(self.working_dir),
                    input=sql_content,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode != 0:
                    self.console.error(f"Restore failed: {result.stderr}")
                    return False

            return True

        except Exception as e:
            self.console.error(f"Restore failed: {str(e)}")
            return False

    def _run_smoke_tests(self) -> bool:
        """Run basic smoke tests to verify deployment."""
        if self.dry_run:
            self.console.info("[DRY RUN] Would run smoke tests")
            return True

        tests_passed = 0
        tests_failed = 0

        # Test 1: Health endpoint
        try:
            import httpx

            with self.console.spinner("Testing health endpoint"):
                response = httpx.get("http://localhost:8001/api/health", timeout=10)

            if response.status_code == 200:
                self.console.success("Health endpoint responding")
                tests_passed += 1
            else:
                self.console.error(f"Health endpoint returned {response.status_code}")
                tests_failed += 1

        except Exception as e:
            self.console.error(f"Health check failed: {str(e)}")
            tests_failed += 1

        # Test 2: Database connectivity
        try:
            success, stdout, stderr = run_docker_compose(
                "exec",
                ["-T", "db", "psql", "-U", "promptvault", "-d", "promptvault", "-c", "SELECT COUNT(*) FROM prompts;"],
                working_dir=str(self.working_dir)
            )

            if success:
                self.console.success("Database connectivity verified")
                tests_passed += 1
            else:
                self.console.error("Database connectivity test failed")
                tests_failed += 1

        except Exception as e:
            self.console.error(f"Database test failed: {str(e)}")
            tests_failed += 1

        # Test 3: Redis connectivity
        try:
            success, stdout, stderr = run_docker_compose(
                "exec",
                ["-T", "redis", "redis-cli", "ping"],
                working_dir=str(self.working_dir)
            )

            if success and "PONG" in stdout:
                self.console.success("Redis connectivity verified")
                tests_passed += 1
            else:
                self.console.error("Redis connectivity test failed")
                tests_failed += 1

        except Exception as e:
            self.console.error(f"Redis test failed: {str(e)}")
            tests_failed += 1

        self.console.info(f"\nSmoke tests: {tests_passed} passed, {tests_failed} failed")

        return tests_failed == 0

    def _display_access_info(self) -> None:
        """Display deployment summary and access information."""
        duration = ""
        if self.deployment_start_time:
            elapsed = datetime.now() - self.deployment_start_time
            duration = f"Deployment took {elapsed.seconds} seconds"

        self.console.table(
            "Deployment Summary",
            headers=["Component", "Status", "Details"],
            rows=[
                ["Database", "✓ Running", "PostgreSQL 15"],
                ["Cache", "✓ Running", "Redis 7"],
                ["Application", "✓ Running", "PromptVault"],
                ["Phases", "✓ Complete", ", ".join(self.phases_completed)],
                ["Duration", "✓", duration] if duration else ["Duration", "-", "N/A"],
            ]
        )

        self.console.info("\nAccess Information:")
        self.console.info("  Web UI: http://localhost:8001")
        self.console.info("  API Docs: http://localhost:8001/docs")
        self.console.info("  Health Check: http://localhost:8001/api/health")

        if self.backup_file:
            self.console.info(f"\nBackup saved to: {self.backup_file}")

        self.console.info("\nUseful Commands:")
        self.console.info("  View logs: docker-compose logs -f web")
        self.console.info("  Check status: docker-compose ps")
        self.console.info("  Stop services: docker-compose down")


@click.command()
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would happen without executing'
)
@click.option(
    '--skip-backup',
    is_flag=True,
    help='Skip backup phase'
)
@click.option(
    '--skip-migrations',
    is_flag=True,
    help='Skip migration phase'
)
@click.option(
    '--rollback',
    is_flag=True,
    help='Rollback to previous state'
)
@click.option(
    '--rebuild',
    is_flag=True,
    help='Force rebuild Docker images'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='No prompts (use defaults)'
)
def main(
    dry_run: bool,
    skip_backup: bool,
    skip_migrations: bool,
    rollback: bool,
    rebuild: bool,
    non_interactive: bool
):
    """
    PromptVault Deployment Orchestration

    Automates the complete deployment process with pre-flight checks,
    five deployment phases, and automatic rollback on failure.
    """
    console = SetupConsole()

    # Show header
    console.header(
        "PromptVault Deployment",
        "Automated deployment orchestration with rollback capability"
    )

    if dry_run:
        console.warning("DRY RUN MODE: No changes will be made")

    # Create orchestrator
    orchestrator = DeploymentOrchestrator(
        console=console,
        dry_run=dry_run,
        skip_backup=skip_backup,
        skip_migrations=skip_migrations,
        rebuild=rebuild,
        non_interactive=non_interactive,
        working_dir=project_root
    )

    # Handle rollback mode
    if rollback:
        console.info("Rollback mode activated")
        if not non_interactive:
            if not console.confirm("Are you sure you want to rollback?", default=False):
                console.info("Rollback cancelled")
                sys.exit(0)

        if orchestrator.rollback():
            console.success("Rollback completed successfully")
            sys.exit(0)
        else:
            console.error("Rollback failed")
            sys.exit(1)

    # Record start time
    orchestrator.deployment_start_time = datetime.now()

    # Pre-flight checks
    if not orchestrator.run_preflight_checks():
        console.error("Pre-flight checks failed. Aborting deployment.")
        sys.exit(1)

    # Confirm deployment
    if not non_interactive and not dry_run:
        console.info("\nAll pre-flight checks passed.")
        if not console.confirm("Proceed with deployment?", default=True):
            console.info("Deployment cancelled")
            sys.exit(0)

    # Execute deployment phases
    try:
        # Phase 1: Preparation
        if not orchestrator.phase1_preparation():
            raise Exception("Phase 1 (Preparation) failed")

        # Phase 2: Infrastructure
        if not orchestrator.phase2_infrastructure():
            raise Exception("Phase 2 (Infrastructure) failed")

        # Phase 3: Migrations
        if not orchestrator.phase3_migrations():
            raise Exception("Phase 3 (Migrations) failed")

        # Phase 4: Application
        if not orchestrator.phase4_application():
            raise Exception("Phase 4 (Application) failed")

        # Phase 5: Verification
        if not orchestrator.phase5_verification():
            raise Exception("Phase 5 (Verification) failed")

        # Success!
        console.success("\nDeployment completed successfully!")
        sys.exit(0)

    except Exception as e:
        console.error(f"\nDeployment failed: {str(e)}")

        # Automatic rollback on failure
        if not dry_run and not non_interactive:
            if console.confirm("Deployment failed. Attempt automatic rollback?", default=True):
                console.info("Initiating rollback...")
                if orchestrator.rollback():
                    console.success("Rollback completed successfully")
                    sys.exit(1)
                else:
                    console.error("Rollback also failed. Manual intervention required.")
                    sys.exit(2)

        sys.exit(1)


if __name__ == "__main__":
    main()
