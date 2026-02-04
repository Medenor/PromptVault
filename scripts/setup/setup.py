#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
PromptVault Turnkey Setup Wizard

This is the main entry point for PromptVault deployment. It provides an
interactive wizard that orchestrates all setup components for a complete
turnkey deployment experience.

Features:
- Quick Setup: Get running in minutes with sensible defaults
- Advanced Setup: Full customization for production deployments
- Component Setup: Run individual setup scripts
- Resume Support: Continue from where you left off
- Configuration Profiles: Development and production presets
- Non-interactive Mode: Perfect for automation and CI/CD

Usage:
    # Interactive wizard (recommended for first-time setup)
    python scripts/setup/setup.py

    # Quick setup with defaults (SQLite, auto-config)
    python scripts/setup/setup.py --quick

    # Advanced setup with full customization
    python scripts/setup/setup.py --advanced

    # Run specific component
    python scripts/setup/setup.py --component jwt
    python scripts/setup/setup.py --component env
    python scripts/setup/setup.py --component database
    python scripts/setup/setup.py --component deploy

    # Non-interactive mode (use defaults)
    python scripts/setup/setup.py --quick --non-interactive

    # Load configuration from file
    python scripts/setup/setup.py --config config.yaml

Components:
    jwt       - Generate JWT signing keys
    env       - Configure environment variables
    database  - Setup and initialize database
    deploy    - Deploy the application

Profiles:
    development  - SQLite, debug logging, relaxed security
    production   - PostgreSQL, strict security, optimized settings
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

import click

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts" / "setup" / "utils"))

from console import SetupConsole


class SetupState:
    """
    Manages setup wizard state for resume capability.

    Tracks completed steps and configuration choices so users can
    resume setup if interrupted.
    """

    def __init__(self, state_file: Path):
        """
        Initialize setup state manager.

        Args:
            state_file: Path to state file (.setup_state.json)
        """
        self.state_file = state_file
        self.state: Dict[str, Any] = {
            'completed_steps': [],
            'mode': None,
            'profile': None,
            'config': {},
            'last_updated': None
        }

    def load(self) -> bool:
        """
        Load saved state from file.

        Returns:
            True if state was loaded, False if no saved state exists
        """
        if not self.state_file.exists():
            return False

        try:
            with open(self.state_file, 'r') as f:
                self.state = json.load(f)
            return True
        except Exception as e:
            # State file corrupted, ignore
            return False

    def save(self) -> None:
        """Save current state to file."""
        self.state['last_updated'] = datetime.now().isoformat()

        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            # Fail silently if we can't save state
            pass

    def mark_complete(self, step: str) -> None:
        """
        Mark a setup step as complete.

        Args:
            step: Step identifier (e.g., 'jwt', 'env', 'database', 'deploy')
        """
        if step not in self.state['completed_steps']:
            self.state['completed_steps'].append(step)
        self.save()

    def is_complete(self, step: str) -> bool:
        """
        Check if a step is already complete.

        Args:
            step: Step identifier

        Returns:
            True if step is complete, False otherwise
        """
        return step in self.state['completed_steps']

    def clear(self) -> None:
        """Clear saved state."""
        if self.state_file.exists():
            self.state_file.unlink()


class SetupWizard:
    """
    Main setup wizard that orchestrates all deployment components.

    Provides multiple setup modes:
    - Quick Setup: Minimal prompts, sensible defaults
    - Advanced Setup: Full customization
    - Component Setup: Run individual scripts
    """

    def __init__(self, non_interactive: bool = False, config_file: Optional[str] = None):
        """
        Initialize the setup wizard.

        Args:
            non_interactive: If True, run without user prompts
            config_file: Optional path to YAML configuration file
        """
        self.console = SetupConsole()
        self.non_interactive = non_interactive
        self.config_file = config_file
        self.state = SetupState(project_root / '.setup_state.json')
        self.scripts_dir = project_root / "scripts" / "setup"

        # Configuration
        self.mode: Optional[str] = None
        self.profile: str = 'development'
        self.admin_username: Optional[str] = None
        self.admin_email: Optional[str] = None

    def run_interactive(self) -> int:
        """
        Run the interactive setup wizard.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        # Welcome screen
        self.show_welcome()

        # Check for saved state
        if self.state.load():
            self.console.console.print()
            self.console.info(f"Found saved setup state from {self.state.state['last_updated']}")

            if self.console.confirm("Do you want to resume?", default=True):
                self.console.success("Resuming setup...")
                self.mode = self.state.state.get('mode')
                self.profile = self.state.state.get('profile', 'development')
            else:
                self.console.info("Starting fresh setup...")
                self.state.clear()

        # Mode selection (if not resuming)
        if not self.mode:
            self.mode = self.select_mode()
            self.state.state['mode'] = self.mode
            self.state.save()

        # Run selected mode
        if self.mode == 'quick':
            return self.run_quick_setup()
        elif self.mode == 'advanced':
            return self.run_advanced_setup()
        elif self.mode == 'component':
            return self.run_component_menu()
        else:
            self.console.error(f"Unknown mode: {self.mode}")
            return 1

    def show_welcome(self) -> None:
        """Display welcome screen with overview."""
        self.console.header(
            "PromptVault Setup Wizard",
            "Complete deployment automation for your PromptVault instance"
        )

        self.console.info("This wizard will guide you through:")
        self.console.console.print("  1. JWT key generation for secure authentication")
        self.console.console.print("  2. Environment configuration with validation")
        self.console.console.print("  3. Database setup and initialization")
        self.console.console.print("  4. Application deployment with Docker")
        self.console.console.print()

    def select_mode(self) -> str:
        """
        Prompt user to select setup mode.

        Returns:
            Selected mode identifier ('quick', 'advanced', or 'component')
        """
        self.console.console.print("[bold cyan]Select Setup Mode:[/bold cyan]")
        self.console.console.print()
        self.console.console.print("  1. [bold]Quick Setup[/bold] - Get running in minutes (SQLite, auto-config)")
        self.console.console.print("     Perfect for: Development, testing, quick demos")
        self.console.console.print()
        self.console.console.print("  2. [bold]Advanced Setup[/bold] - Full customization (PostgreSQL, production-ready)")
        self.console.console.print("     Perfect for: Production deployments, custom configurations")
        self.console.console.print()
        self.console.console.print("  3. [bold]Component Setup[/bold] - Run individual setup scripts")
        self.console.console.print("     Perfect for: Re-running specific steps, debugging")
        self.console.console.print()

        choice = self.console.select(
            "Choose your setup mode",
            choices=["quick", "advanced", "component"]
        )

        return choice

    def run_quick_setup(self) -> int:
        """
        Run quick setup with sensible defaults.

        Quick setup flow:
        1. Generate JWT keys (if not exist)
        2. Create .env with development profile defaults
        3. Setup SQLite database
        4. Create admin user
        5. Deploy application
        6. Show access information

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.console.header(
            "Quick Setup",
            "Automated setup with sensible defaults for development"
        )

        self.console.info("Quick setup will:")
        self.console.console.print("  - Use SQLite database (no PostgreSQL required)")
        self.console.console.print("  - Generate secure JWT keys automatically")
        self.console.console.print("  - Configure for development environment")
        self.console.console.print("  - Deploy with Docker Compose")
        self.console.console.print()

        if not self.non_interactive:
            if not self.console.confirm("Continue with quick setup?", default=True):
                return 0

        self.console.console.print()
        self.profile = 'development'
        self.state.state['profile'] = self.profile
        self.state.save()

        # Step 1: Generate JWT keys
        if not self.state.is_complete('jwt'):
            self.console.step(1, 6, "Generating JWT keys")
            if not self.run_jwt_setup():
                self.console.error("JWT key generation failed")
                return 1
            self.state.mark_complete('jwt')
            self.console.console.print()
        else:
            self.console.info("JWT keys already generated (skipping)")
            self.console.console.print()

        # Step 2: Create environment configuration
        if not self.state.is_complete('env'):
            self.console.step(2, 6, "Creating environment configuration")
            if not self.run_env_setup(profile='development', non_interactive=True):
                self.console.error("Environment configuration failed")
                return 1
            self.state.mark_complete('env')
            self.console.console.print()
        else:
            self.console.info("Environment already configured (skipping)")
            self.console.console.print()

        # Step 3: Setup SQLite database
        if not self.state.is_complete('database'):
            self.console.step(3, 6, "Setting up SQLite database")
            if not self.run_database_setup(db_type='sqlite'):
                self.console.error("Database setup failed")
                return 1
            self.state.mark_complete('database')
            self.console.console.print()
        else:
            self.console.info("Database already setup (skipping)")
            self.console.console.print()

        # Step 4: Create admin user
        if not self.state.is_complete('admin'):
            self.console.step(4, 6, "Creating admin user")
            if not self.create_admin_user():
                self.console.error("Admin user creation failed")
                return 1
            self.state.mark_complete('admin')
            self.console.console.print()
        else:
            self.console.info("Admin user already created (skipping)")
            self.console.console.print()

        # Step 5: Deploy application
        if not self.state.is_complete('deploy'):
            self.console.step(5, 6, "Deploying application")
            if not self.run_deploy(non_interactive=True):
                self.console.error("Deployment failed")
                return 1
            self.state.mark_complete('deploy')
            self.console.console.print()
        else:
            self.console.info("Application already deployed (skipping)")
            self.console.console.print()

        # Step 6: Show success summary
        self.console.step(6, 6, "Setup complete!")
        self.show_success_summary()

        # Clear state on successful completion
        self.state.clear()

        return 0

    def run_advanced_setup(self) -> int:
        """
        Run advanced setup with full customization.

        Advanced setup flow:
        1. Select deployment profile (development/production)
        2. JWT configuration
        3. Interactive environment configuration
        4. Database selection (PostgreSQL/SQLite)
        5. Admin user creation
        6. Deployment

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.console.header(
            "Advanced Setup",
            "Full customization for production deployments"
        )

        # Select profile
        if not self.state.state.get('profile'):
            self.console.console.print("[bold cyan]Select Deployment Profile:[/bold cyan]")
            self.console.console.print()
            self.console.console.print("  [bold]Development[/bold] - SQLite, debug logging, relaxed security")
            self.console.console.print("  [bold]Production[/bold]  - PostgreSQL recommended, strict security")
            self.console.console.print()

            self.profile = self.console.select(
                "Choose profile",
                choices=["development", "production"]
            )
            self.state.state['profile'] = self.profile
            self.state.save()
        else:
            self.profile = self.state.state['profile']
            self.console.info(f"Using profile: {self.profile}")

        self.console.console.print()

        # Step 1: JWT Configuration
        if not self.state.is_complete('jwt'):
            self.console.step(1, 6, "JWT Key Configuration")
            self.console.console.print()

            if not self.non_interactive:
                if self.console.confirm("Generate JWT keys now?", default=True):
                    if not self.run_jwt_setup():
                        self.console.error("JWT key generation failed")
                        return 1
                    self.state.mark_complete('jwt')
                else:
                    self.console.info("Skipping JWT generation (you can run it later)")
            else:
                if not self.run_jwt_setup():
                    self.console.error("JWT key generation failed")
                    return 1
                self.state.mark_complete('jwt')

            self.console.console.print()
        else:
            self.console.info("JWT keys already configured (skipping)")
            self.console.console.print()

        # Step 2: Environment Configuration
        if not self.state.is_complete('env'):
            self.console.step(2, 6, "Environment Configuration")
            self.console.console.print()

            if not self.run_env_setup(profile=self.profile, non_interactive=self.non_interactive):
                self.console.error("Environment configuration failed")
                return 1
            self.state.mark_complete('env')
            self.console.console.print()
        else:
            self.console.info("Environment already configured (skipping)")
            self.console.console.print()

        # Step 3: Database Configuration
        if not self.state.is_complete('database'):
            self.console.step(3, 6, "Database Configuration")
            self.console.console.print()

            if not self.non_interactive:
                if self.profile == 'production':
                    self.console.info("Production profile: PostgreSQL recommended")
                    db_choice = self.console.select(
                        "Select database type",
                        choices=["postgresql", "sqlite"]
                    )
                else:
                    self.console.info("Development profile: SQLite is default")
                    db_choice = self.console.select(
                        "Select database type",
                        choices=["sqlite", "postgresql"]
                    )
            else:
                db_choice = 'postgresql' if self.profile == 'production' else 'sqlite'

            self.console.console.print()

            if not self.run_database_setup(db_type=db_choice):
                self.console.error("Database setup failed")
                return 1
            self.state.mark_complete('database')
            self.console.console.print()
        else:
            self.console.info("Database already configured (skipping)")
            self.console.console.print()

        # Step 4: Admin User Creation
        if not self.state.is_complete('admin'):
            self.console.step(4, 6, "Admin User Creation")
            self.console.console.print()

            if not self.create_admin_user():
                self.console.error("Admin user creation failed")
                return 1
            self.state.mark_complete('admin')
            self.console.console.print()
        else:
            self.console.info("Admin user already created (skipping)")
            self.console.console.print()

        # Step 5: Deployment Configuration
        if not self.state.is_complete('deploy_config'):
            self.console.step(5, 6, "Deployment Configuration")
            self.console.console.print()

            if not self.non_interactive:
                self.console.info("Review deployment settings:")
                self.console.console.print(f"  Profile: {self.profile}")
                self.console.console.print(f"  Database: {db_choice}")
                self.console.console.print()

                if not self.console.confirm("Deploy now?", default=True):
                    self.console.info("Deployment postponed")
                    self.console.console.print()
                    self.console.info("To deploy later, run:")
                    self.console.console.print("  python scripts/setup/deploy.py")
                    return 0

            self.state.mark_complete('deploy_config')

        # Step 6: Deploy
        if not self.state.is_complete('deploy'):
            self.console.step(6, 6, "Deploying Application")
            self.console.console.print()

            if not self.run_deploy(non_interactive=self.non_interactive):
                self.console.error("Deployment failed")
                return 1
            self.state.mark_complete('deploy')
            self.console.console.print()
        else:
            self.console.info("Application already deployed (skipping)")
            self.console.console.print()

        # Show success summary
        self.show_success_summary()

        # Clear state on successful completion
        self.state.clear()

        return 0

    def run_component_menu(self) -> int:
        """
        Show component menu and run selected component.

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.console.header(
            "Component Setup",
            "Run individual setup scripts"
        )

        component = self.console.select(
            "Select component to run",
            choices=["jwt", "env", "database", "deploy", "exit"]
        )

        if component == "exit":
            return 0

        self.console.console.print()
        return self.run_component(component)

    def run_component(self, component: str) -> int:
        """
        Run a specific setup component.

        Args:
            component: Component name ('jwt', 'env', 'database', or 'deploy')

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        if component == 'jwt':
            return 0 if self.run_jwt_setup() else 1
        elif component == 'env':
            return 0 if self.run_env_setup(non_interactive=self.non_interactive) else 1
        elif component == 'database':
            return 0 if self.run_database_setup(non_interactive=self.non_interactive) else 1
        elif component == 'deploy':
            return 0 if self.run_deploy(non_interactive=self.non_interactive) else 1
        else:
            self.console.error(f"Unknown component: {component}")
            return 1

    def run_jwt_setup(self) -> bool:
        """
        Run JWT key generation script.

        Returns:
            True if successful, False otherwise
        """
        script_path = self.scripts_dir / "setup_jwt.py"

        with self.console.spinner("Generating JWT keys..."):
            result = subprocess.run(
                [sys.executable, str(script_path), "--non-interactive"],
                cwd=project_root,
                capture_output=True,
                text=True
            )

        if result.returncode == 0:
            self.console.success("JWT keys generated successfully")
            return True
        else:
            self.console.error("JWT key generation failed")
            if result.stderr:
                self.console.console.print(result.stderr, style="red")
            return False

    def run_env_setup(self, profile: str = 'development', non_interactive: bool = False) -> bool:
        """
        Run environment configuration script.

        Args:
            profile: Deployment profile ('development' or 'production')
            non_interactive: If True, use defaults without prompts

        Returns:
            True if successful, False otherwise
        """
        script_path = self.scripts_dir / "setup_env.py"

        args = [
            sys.executable,
            str(script_path),
            "--profile", profile
        ]

        if non_interactive:
            args.append("--non-interactive")

        result = subprocess.run(
            args,
            cwd=project_root,
            capture_output=not non_interactive,
            text=True
        )

        if result.returncode == 0:
            self.console.success("Environment configuration completed")
            return True
        else:
            self.console.error("Environment configuration failed")
            if result.stderr:
                self.console.console.print(result.stderr, style="red")
            return False

    def run_database_setup(self, db_type: Optional[str] = None, non_interactive: bool = False) -> bool:
        """
        Run database setup script.

        Args:
            db_type: Database type ('sqlite' or 'postgresql'), None for interactive
            non_interactive: If True, use defaults without prompts

        Returns:
            True if successful, False otherwise
        """
        script_path = self.scripts_dir / "setup_database.py"

        args = [sys.executable, str(script_path)]

        if db_type:
            args.extend(["--type", db_type])

        if non_interactive or (db_type == "sqlite"):
            args.append("--non-interactive")

        result = subprocess.run(
            args,
            cwd=project_root,
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            self.console.success("Database setup completed")
            return True
        else:
            self.console.error("Database setup failed")
            return False

    def create_admin_user(self) -> bool:
        """
        Prompt for and create admin user.

        Returns:
            True if successful, False otherwise
        """
        self.console.info("Create an administrator account")
        self.console.console.print()

        if self.non_interactive:
            self.console.warning("Non-interactive mode: Skipping admin user creation")
            self.console.info("Create an admin user later with:")
            self.console.console.print("  python scripts/create_admin_user.py")
            return True

        # Get admin credentials
        self.admin_username = self.console.prompt("Admin username", default="admin")
        self.admin_email = self.console.prompt("Admin email", default="admin@example.com")

        # For now, just save the information
        # The actual user creation should be done after deployment
        self.console.success(f"Admin user '{self.admin_username}' will be created")
        self.console.info("Note: Create the user after deployment with:")
        self.console.console.print(f"  python scripts/create_admin_user.py --username {self.admin_username} --email {self.admin_email}")

        return True

    def run_deploy(self, non_interactive: bool = False) -> bool:
        """
        Run deployment script.

        Args:
            non_interactive: If True, deploy without prompts

        Returns:
            True if successful, False otherwise
        """
        script_path = self.scripts_dir / "deploy.py"

        args = [sys.executable, str(script_path)]

        if non_interactive:
            args.append("--non-interactive")

        result = subprocess.run(
            args,
            cwd=project_root,
            capture_output=False,
            text=True
        )

        if result.returncode == 0:
            self.console.success("Deployment completed successfully")
            return True
        else:
            self.console.error("Deployment failed")
            return False

    def show_success_summary(self) -> None:
        """Display final success summary with access information."""
        self.console.console.print()
        self.console.console.print("[bold green]" + "=" * 70 + "[/bold green]")
        self.console.console.print("[bold green]Setup Completed Successfully![/bold green]")
        self.console.console.print("[bold green]" + "=" * 70 + "[/bold green]")
        self.console.console.print()

        # Access information
        self.console.console.print("[bold cyan]Access Your PromptVault Instance:[/bold cyan]")
        self.console.console.print()
        self.console.console.print("  Web Interface:  http://localhost:8001")
        self.console.console.print("  API Endpoint:   http://localhost:8001/api")
        self.console.console.print("  API Docs:       http://localhost:8001/docs")
        self.console.console.print()

        if self.admin_username:
            self.console.console.print("[bold cyan]Admin Credentials:[/bold cyan]")
            self.console.console.print()
            self.console.console.print(f"  Username: {self.admin_username}")
            self.console.console.print(f"  Email:    {self.admin_email}")
            self.console.console.print()

        # Useful commands
        self.console.console.print("[bold cyan]Useful Commands:[/bold cyan]")
        self.console.console.print()
        self.console.console.print("  View logs:        docker-compose logs -f")
        self.console.console.print("  Stop services:    docker-compose down")
        self.console.console.print("  Restart services: docker-compose restart")
        self.console.console.print("  Check status:     docker-compose ps")
        self.console.console.print()

        # Next steps
        self.console.console.print("[bold cyan]Next Steps:[/bold cyan]")
        self.console.console.print()
        self.console.console.print("  1. Open http://localhost:8001 in your browser")

        if self.admin_username:
            self.console.console.print(f"  2. Create admin user: python scripts/create_admin_user.py --username {self.admin_username}")
            self.console.console.print("  3. Log in with your admin credentials")
            self.console.console.print("  4. Start organizing your prompts!")
        else:
            self.console.console.print("  2. Create an admin user: python scripts/create_admin_user.py")
            self.console.console.print("  3. Log in with your credentials")
            self.console.console.print("  4. Start organizing your prompts!")

        self.console.console.print()
        self.console.console.print("[bold green]" + "=" * 70 + "[/bold green]")
        self.console.console.print()


@click.command()
@click.option(
    '--quick',
    is_flag=True,
    help='Quick setup with defaults (SQLite, auto-config)'
)
@click.option(
    '--advanced',
    is_flag=True,
    help='Advanced setup with full customization'
)
@click.option(
    '--component',
    type=click.Choice(['jwt', 'env', 'database', 'deploy']),
    help='Run specific component only'
)
@click.option(
    '--config',
    type=click.Path(exists=True),
    help='Load configuration from YAML file'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='Run without prompts (use defaults)'
)
def main(quick: bool, advanced: bool, component: Optional[str], config: Optional[str], non_interactive: bool):
    """
    PromptVault Turnkey Setup Wizard

    Complete deployment automation with multiple setup modes.

    Examples:

      # Interactive wizard (recommended)
      python scripts/setup/setup.py

      # Quick setup for development
      python scripts/setup/setup.py --quick

      # Production setup with customization
      python scripts/setup/setup.py --advanced

      # Run specific component
      python scripts/setup/setup.py --component jwt

      # Automated setup from config file
      python scripts/setup/setup.py --config config.yaml --non-interactive
    """
    wizard = SetupWizard(non_interactive=non_interactive, config_file=config)

    try:
        # Determine mode
        if quick:
            wizard.mode = 'quick'
            exit_code = wizard.run_quick_setup()
        elif advanced:
            wizard.mode = 'advanced'
            exit_code = wizard.run_advanced_setup()
        elif component:
            exit_code = wizard.run_component(component)
        else:
            # Interactive mode selection
            exit_code = wizard.run_interactive()

        sys.exit(exit_code)

    except KeyboardInterrupt:
        wizard.console.console.print()
        wizard.console.warning("Setup interrupted by user")
        wizard.console.info("Run the wizard again to resume from where you left off")
        sys.exit(1)
    except Exception as e:
        wizard.console.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
