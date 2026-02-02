# Implementation Plan: Turnkey Deployment Solution

**Version:** 1.0
**Created:** 2026-02-02
**Status:** Draft
**Feature Request:** Streamlined Deployment Process

---

## Executive Summary

This plan outlines the implementation of a turnkey deployment solution for PromptVault that automates JWT key generation, environment configuration, database setup, and application startup. The solution will provide both an interactive CLI wizard and individual modular scripts that can be used independently.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Architecture Overview](#2-architecture-overview)
3. [Component Specifications](#3-component-specifications)
4. [Implementation Phases](#4-implementation-phases)
5. [File Structure](#5-file-structure)
6. [Detailed Implementation](#6-detailed-implementation)
7. [Testing Strategy](#7-testing-strategy)
8. [Rollback Plan](#8-rollback-plan)
9. [Documentation Updates](#9-documentation-updates)
10. [Security Considerations](#10-security-considerations)

---

## 1. Current State Analysis

### 1.1 Existing Deployment Process

The current deployment requires these manual steps:

| Step | Current Process | Pain Points |
|------|-----------------|-------------|
| JWT Keys | Run `scripts/generate_jwt_keys.py` manually | No validation, no directory creation |
| Environment | Copy `.env.example` to `.env`, edit manually | Easy to misconfigure, no validation |
| Database | Manual PostgreSQL/SQLite setup | Complex for PostgreSQL, error-prone |
| Migrations | Run `alembic upgrade head` manually | Timing issues with DB initialization |
| Startup | Run `docker-compose up -d` | No pre-flight checks |

### 1.2 Existing Scripts Inventory

| Script | Purpose | Reusability |
|--------|---------|-------------|
| `scripts/generate_jwt_keys.py` | Generate ES256 JWT key pairs | Can be enhanced |
| `scripts/pre-deploy-check.sh` | Validate deployment readiness | Can be integrated |
| `scripts/create_admin_user.py` | Create first admin user | Can be integrated |
| `scripts/migrate_json_to_db.py` | Migrate legacy JSON data | Optional integration, not needed for new deployments |

### 1.3 Configuration Requirements

From `.env.example`, the critical configuration variables are:

**Required for All Deployments:**
- `DATABASE_URL` - Database connection string
- `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` - JWT key locations
- `ENVIRONMENT` - development/testing/production

**Required for Production:**
- `POSTGRES_PASSWORD` - PostgreSQL password
- `SECRET_KEY` - Application secret
- SMTP configuration (for password reset)

**Optional with Sensible Defaults:**
- Rate limiting settings
- Session timeouts
- Password policy settings
- Logging configuration

---

## 2. Architecture Overview

### 2.1 Solution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TURNKEY DEPLOYMENT SYSTEM                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  setup.py (Main Entry Point)              │   │
│  │  - Interactive CLI wizard                                 │   │
│  │  - Orchestrates all components                            │   │
│  │  - Provides progress feedback                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐    │
│  │ setup_jwt.py     │ │ setup_env.py │ │ setup_database.py│    │
│  │ - Generate keys  │ │ - Configure  │ │ - Init database  │    │
│  │ - Validate keys  │ │ - Validate   │ │ - Run migrations │    │
│  │ - Backup keys    │ │ - Generate   │ │ - Create admin   │    │
│  └──────────────────┘ └──────────────┘ └──────────────────┘    │
│              │               │               │                  │
│              └───────────────┼───────────────┘                  │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  deploy.py (Deployment Runner)            │   │
│  │  - Pre-flight checks                                      │   │
│  │  - Docker Compose orchestration                           │   │
│  │  - Health verification                                    │   │
│  │  - Rollback on failure                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Shared Utilities: scripts/setup/utils/                         │
│  - console.py (Rich console output)                             │
│  - validators.py (Input validation)                             │
│  - config_parser.py (Configuration parsing)                     │
│  - docker_utils.py (Docker operations)                          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Deployment Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Interactive** | Full CLI wizard with prompts | First-time setup, users unfamiliar with config |
| **Automated** | Config file or environment-based | CI/CD, scripted deployments |
| **Partial** | Run individual components | Targeted updates (e.g., regenerate JWT keys) |

### 2.3 Technology Stack for Scripts

- **Python 3.11+** - Primary scripting language (consistent with codebase)
- **Rich** - Terminal formatting, progress bars, tables (already a dependency pattern)
- **Click** - CLI framework for argument parsing
- **PyYAML** - Configuration file parsing (optional setup config)
- **python-dotenv** - Environment file handling (already a dependency)

---

## 3. Component Specifications

### 3.1 JWT Key Generation (`scripts/setup/setup_jwt.py`)

**Purpose:** Automated, secure JWT key pair generation with validation.

**Features:**
| Feature | Description |
|---------|-------------|
| Key Generation | ES256 (ECDSA P-256) key pair generation using `cryptography` |
| Directory Management | Auto-create `secrets/jwt/` with correct permissions (700) |
| Key Validation | Verify generated keys can sign and verify tokens |
| Backup | Backup existing keys before regeneration |
| Git Protection | Verify `.gitignore` includes secrets directory |
| Idempotency | Skip generation if valid keys already exist (with --force override) |

**CLI Interface:**
```bash
# Interactive mode
python scripts/setup/setup_jwt.py

# Automated mode
python scripts/setup/setup_jwt.py --non-interactive --force

# Validation only
python scripts/setup/setup_jwt.py --validate-only

# Custom output directory
python scripts/setup/setup_jwt.py --output-dir /custom/path
```

**Output:**
```
secrets/
└── jwt/
    ├── private_key.pem    (chmod 600)
    └── public_key.pem     (chmod 644)
```

**Validation Checks:**
1. Private key file exists and is readable
2. Public key file exists and is readable
3. Key pair can sign and verify a test JWT
4. File permissions are secure (private key not world-readable)

---

### 3.2 Environment Configuration (`scripts/setup/setup_env.py`)

**Purpose:** Interactive environment configuration with validation.

**Features:**
| Feature | Description |
|---------|-------------|
| Template-Based | Generate `.env` from `.env.example` with user inputs |
| Validation | Validate each variable against expected patterns |
| Defaults | Provide sensible defaults for optional variables |
| Profiles | Support deployment profiles (development, production) |
| Secrets Generation | Auto-generate `SECRET_KEY` and database passwords |
| Diff Preview | Show differences before writing new configuration |

**Configuration Sections:**
```
1. Deployment Profile
   - development (SQLite, debug logging, no rate limiting)
   - production (PostgreSQL, minimal logging, full security)

2. Database Configuration
   - Database type (PostgreSQL/SQLite)
   - Connection parameters (host, port, user, password, database name)
   - Connection pool settings

3. Security Configuration
   - JWT settings (paths, expiration times)
   - Password policy
   - Rate limiting
   - Session management

4. Email Configuration (Optional)
   - SMTP settings for password reset functionality

5. Logging Configuration
   - Log levels
   - Audit logging
```

**CLI Interface:**
```bash
# Interactive wizard
python scripts/setup/setup_env.py

# From existing config
python scripts/setup/setup_env.py --from-file setup.yaml

# Non-interactive with profile
python scripts/setup/setup_env.py --non-interactive --profile production

# Validate existing .env
python scripts/setup/setup_env.py --validate-only
```

**Validation Rules:**
| Variable | Validation |
|----------|------------|
| `DATABASE_URL` | Valid URI format, connectivity test (optional) |
| `POSTGRES_PASSWORD` | Minimum 16 characters, complexity requirements |
| `SECRET_KEY` | Minimum 32 characters, high entropy |
| `JWT_*_PATH` | File exists and is readable |
| `SMTP_*` | Valid host/port format |
| `*_SECONDS` | Positive integer |

---

### 3.3 Database Setup (`scripts/setup/setup_database.py`)

**Purpose:** Automated database initialization and migration.

**Features:**
| Feature | Description |
|---------|-------------|
| Multi-Database | Support PostgreSQL and SQLite |
| Auto-Creation | Create database and user (PostgreSQL) |
| Migration Runner | Run Alembic migrations with retry logic |
| Health Check | Verify database connectivity and schema |
| Admin Setup | Integrate admin user creation |
| Rollback | Support migration rollback on failure |

**PostgreSQL Setup Flow:**
```
1. Check PostgreSQL connectivity
2. Create database if not exists
3. Create user with appropriate privileges
4. Test connection with new credentials
5. Run Alembic migrations
6. Verify schema integrity
7. Optionally create admin user
```

**SQLite Setup Flow:**
```
1. Create data directory if not exists
2. Initialize SQLite database file
3. Run Alembic migrations
4. Verify schema integrity
5. Optionally create admin user
```

**CLI Interface:**
```bash
# Interactive mode
python scripts/setup/setup_database.py

# PostgreSQL setup
python scripts/setup/setup_database.py --type postgresql \
    --host localhost --port 5432 \
    --database promptvault --user promptvault

# SQLite setup
python scripts/setup/setup_database.py --type sqlite \
    --path ./data/promptvault.db

# Migrations only
python scripts/setup/setup_database.py --migrate-only

# With admin user creation
python scripts/setup/setup_database.py --create-admin
```

**Schema Verification:**
- Check all expected tables exist
- Verify Alembic version matches latest migration
- Run integrity checks on foreign keys

---

### 3.4 Deployment Runner (`scripts/setup/deploy.py`)

**Purpose:** Orchestrate the complete deployment process.

**Features:**
| Feature | Description |
|---------|-------------|
| Pre-flight Checks | Validate system requirements before deployment |
| Service Orchestration | Manage Docker Compose lifecycle |
| Health Monitoring | Wait for services to be healthy |
| Failure Recovery | Automatic rollback on deployment failure |
| Progress Reporting | Real-time status updates |

**Pre-flight Checks:**
```
✓ Docker installed and running
✓ Docker Compose installed
✓ Required ports available (8001, 5432, 6379)
✓ Sufficient disk space
✓ JWT keys present and valid
✓ Environment file present and valid
✓ Database credentials valid
✓ No conflicting containers running
```

**Deployment Phases:**
```
Phase 1: Preparation
├── Backup current state (if upgrading)
├── Pull/build Docker images
└── Validate configuration

Phase 2: Infrastructure
├── Start database container
├── Wait for database health
├── Start Redis container
└── Wait for Redis health

Phase 3: Migrations
├── Run database migrations
└── Verify schema

Phase 4: Application
├── Start web container
├── Wait for health endpoint
└── Verify application functionality

Phase 5: Verification
├── Run smoke tests
├── Display access information
└── Log deployment completion
```

**CLI Interface:**
```bash
# Full deployment
python scripts/setup/deploy.py

# Dry run (show what would happen)
python scripts/setup/deploy.py --dry-run

# Skip specific phases
python scripts/setup/deploy.py --skip-backup --skip-migrations

# Rollback to previous state
python scripts/setup/deploy.py --rollback

# Force rebuild images
python scripts/setup/deploy.py --rebuild
```

---

### 3.5 Main Setup Wizard (`scripts/setup/setup.py`)

**Purpose:** Single entry point for turnkey deployment.

**Features:**
| Feature | Description |
|---------|-------------|
| Guided Wizard | Step-by-step setup with clear instructions |
| Mode Selection | Choose between quick setup and advanced configuration |
| Component Integration | Orchestrate all setup components |
| Resume Support | Resume interrupted setup from last checkpoint |
| Summary Report | Final deployment summary with access URLs |

**Wizard Flow:**
```
┌─────────────────────────────────────────────────────────────┐
│                   PromptVault Setup Wizard                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Welcome to PromptVault Setup!                              │
│                                                              │
│  This wizard will guide you through:                        │
│  1. JWT key generation                                       │
│  2. Environment configuration                                │
│  3. Database setup                                           │
│  4. Application deployment                                   │
│                                                              │
│  [Quick Setup] - Use recommended defaults                   │
│  [Advanced Setup] - Customize all settings                  │
│  [Component Setup] - Run individual components              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Quick Setup Flow:**
```
1. Detect environment (Docker available? PostgreSQL preferred?)
2. Generate JWT keys
3. Create .env with sensible defaults
4. Initialize database (SQLite for dev, PostgreSQL for prod)
5. Run migrations
6. Create admin user (interactive prompt)
7. Start services
8. Display access information
```

**CLI Interface:**
```bash
# Interactive wizard
python scripts/setup/setup.py

# Quick setup (minimal prompts)
python scripts/setup/setup.py --quick

# Advanced setup
python scripts/setup/setup.py --advanced

# Non-interactive with config file
python scripts/setup/setup.py --config setup.yaml --non-interactive

# Specific component
python scripts/setup/setup.py --component jwt
python scripts/setup/setup.py --component env
python scripts/setup/setup.py --component database
python scripts/setup/setup.py --component deploy
```

---

## 4. Implementation Phases

### Phase 1: Core Infrastructure (Week 1)

**Objective:** Establish shared utilities and base infrastructure.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Create `scripts/setup/` directory structure | High | 1 hour |
| Implement `utils/console.py` (Rich-based output) | High | 2 hours |
| Implement `utils/validators.py` (input validation) | High | 3 hours |
| Implement `utils/config_parser.py` (configuration) | High | 2 hours |
| Implement `utils/docker_utils.py` (Docker operations) | High | 3 hours |
| Add Click dependency to pyproject.toml | High | 15 minutes |
| Create unit tests for utilities | Medium | 3 hours |

**Deliverables:**
- Functional utility modules
- Unit test coverage > 80%
- Documentation for utility APIs

---

### Phase 2: JWT Key Generation (Week 1-2)

**Objective:** Complete JWT key generation automation.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Refactor existing `generate_jwt_keys.py` | High | 2 hours |
| Add key validation and testing | High | 2 hours |
| Implement backup functionality | Medium | 1 hour |
| Add CLI interface with Click | High | 2 hours |
| Implement permissions management | High | 1 hour |
| Add comprehensive error handling | High | 2 hours |
| Write unit and integration tests | High | 3 hours |
| Write user documentation | Medium | 1 hour |

**Deliverables:**
- `scripts/setup/setup_jwt.py`
- Test suite for JWT generation
- Documentation section

---

### Phase 3: Environment Configuration (Week 2)

**Objective:** Complete environment configuration automation.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Design configuration schema | High | 2 hours |
| Implement template parser | High | 3 hours |
| Implement interactive prompts | High | 4 hours |
| Implement validation engine | High | 4 hours |
| Add secrets generation | High | 2 hours |
| Implement diff preview | Medium | 2 hours |
| Add profile support (dev/prod) | Medium | 2 hours |
| Write unit and integration tests | High | 4 hours |
| Write user documentation | Medium | 2 hours |

**Deliverables:**
- `scripts/setup/setup_env.py`
- Configuration profiles
- Test suite
- Documentation section

---

### Phase 4: Database Setup (Week 2-3)

**Objective:** Complete database setup automation.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Implement PostgreSQL setup | High | 4 hours |
| Implement SQLite setup | High | 2 hours |
| Integrate Alembic migrations | High | 3 hours |
| Add health checks | High | 2 hours |
| Integrate admin user creation | High | 2 hours |
| Implement rollback functionality | Medium | 3 hours |
| Add schema verification | Medium | 2 hours |
| Write unit and integration tests | High | 4 hours |
| Write user documentation | Medium | 2 hours |

**Deliverables:**
- `scripts/setup/setup_database.py`
- Test suite
- Documentation section

---

### Phase 5: Deployment Runner (Week 3)

**Objective:** Complete deployment orchestration.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Implement pre-flight checks | High | 3 hours |
| Implement Docker Compose management | High | 4 hours |
| Add health monitoring | High | 3 hours |
| Implement failure recovery | High | 4 hours |
| Add progress reporting | Medium | 2 hours |
| Implement rollback functionality | High | 3 hours |
| Write integration tests | High | 4 hours |
| Write user documentation | Medium | 2 hours |

**Deliverables:**
- `scripts/setup/deploy.py`
- Integration test suite
- Documentation section

---

### Phase 6: Main Wizard (Week 3-4)

**Objective:** Complete main setup wizard and integration.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Design wizard flow | High | 2 hours |
| Implement Quick Setup mode | High | 4 hours |
| Implement Advanced Setup mode | High | 4 hours |
| Implement Component Setup mode | Medium | 2 hours |
| Add resume support | Medium | 3 hours |
| Implement summary reporting | Medium | 2 hours |
| Add YAML config file support | Medium | 2 hours |
| Write end-to-end tests | High | 6 hours |
| Write comprehensive documentation | High | 4 hours |

**Deliverables:**
- `scripts/setup/setup.py`
- End-to-end test suite
- Complete user documentation

---

### Phase 7: Documentation & Polish (Week 4)

**Objective:** Complete documentation and user experience refinements.

| Task | Priority | Estimated Effort |
|------|----------|------------------|
| Update README.md | High | 2 hours |
| Update DEPLOYMENT.md | High | 4 hours |
| Create QUICK_START.md | High | 2 hours |
| Add troubleshooting guide | Medium | 3 hours |
| Record demo GIF/video | Low | 2 hours |
| Final testing and bug fixes | High | 8 hours |
| Code review and cleanup | High | 4 hours |

**Deliverables:**
- Updated documentation
- Quick start guide
- Troubleshooting guide
- Demo materials

---

## 5. File Structure

### 5.1 New Files to Create

```
scripts/
└── setup/
    ├── __init__.py
    ├── setup.py              # Main entry point / wizard
    ├── setup_jwt.py          # JWT key generation
    ├── setup_env.py          # Environment configuration
    ├── setup_database.py     # Database initialization
    ├── deploy.py             # Deployment orchestration
    │
    ├── utils/
    │   ├── __init__.py
    │   ├── console.py        # Rich console utilities
    │   ├── validators.py     # Input validation functions
    │   ├── config_parser.py  # Configuration file handling
    │   └── docker_utils.py   # Docker operations
    │
    ├── templates/
    │   ├── env.development.template
    │   └── env.production.template
    │
    └── tests/
        ├── __init__.py
        ├── test_setup_jwt.py
        ├── test_setup_env.py
        ├── test_setup_database.py
        ├── test_deploy.py
        └── test_integration.py

docs/
├── QUICK_START.md            # New quick start guide
└── TROUBLESHOOTING.md        # New troubleshooting guide
```

### 5.2 Files to Modify

| File | Modification |
|------|--------------|
| `pyproject.toml` | Add `click` and `rich` dependencies |
| `README.md` | Update deployment section with new instructions |
| `docs/DEPLOYMENT.md` | Integrate new setup scripts documentation |
| `.gitignore` | Ensure `secrets/` is properly ignored |
| `.env.example` | Add comments for automated setup compatibility |

---

## 6. Detailed Implementation

### 6.1 Console Utilities (`utils/console.py`)

```python
"""
Rich-based console utilities for setup scripts.

Features:
- Consistent styling across all scripts
- Progress bars and spinners
- Status indicators
- Interactive prompts
- Table formatting
"""

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

class SetupConsole:
    """Unified console interface for setup scripts."""

    def __init__(self):
        self.console = Console()

    def header(self, title: str, subtitle: str = None):
        """Display a header panel."""
        pass

    def step(self, number: int, total: int, description: str):
        """Display a step indicator."""
        pass

    def success(self, message: str):
        """Display a success message."""
        pass

    def error(self, message: str):
        """Display an error message."""
        pass

    def warning(self, message: str):
        """Display a warning message."""
        pass

    def info(self, message: str):
        """Display an info message."""
        pass

    def prompt(self, message: str, default: str = None, password: bool = False) -> str:
        """Get user input."""
        pass

    def confirm(self, message: str, default: bool = False) -> bool:
        """Get yes/no confirmation."""
        pass

    def select(self, message: str, choices: list[str]) -> str:
        """Get selection from choices."""
        pass

    def table(self, title: str, headers: list[str], rows: list[list[str]]):
        """Display a table."""
        pass

    def spinner(self, message: str):
        """Context manager for spinner."""
        pass

    def progress(self, description: str, total: int):
        """Context manager for progress bar."""
        pass
```

### 6.2 Validators (`utils/validators.py`)

```python
"""
Input validation functions for setup scripts.

All validators return (is_valid: bool, error_message: str | None)
"""

import re
import os
from urllib.parse import urlparse

def validate_database_url(url: str) -> tuple[bool, str | None]:
    """Validate database URL format."""
    pass

def validate_password_strength(password: str, min_length: int = 16) -> tuple[bool, str | None]:
    """Validate password meets complexity requirements."""
    pass

def validate_port(port: int | str) -> tuple[bool, str | None]:
    """Validate port number is valid."""
    pass

def validate_hostname(hostname: str) -> tuple[bool, str | None]:
    """Validate hostname format."""
    pass

def validate_email(email: str) -> tuple[bool, str | None]:
    """Validate email format."""
    pass

def validate_path(path: str, must_exist: bool = False) -> tuple[bool, str | None]:
    """Validate file/directory path."""
    pass

def validate_jwt_key(path: str, key_type: str) -> tuple[bool, str | None]:
    """Validate JWT key file."""
    pass

def validate_env_file(path: str) -> tuple[bool, list[str]]:
    """Validate .env file, return list of issues."""
    pass
```

### 6.3 JWT Setup Script Structure

```python
#!/usr/bin/env python3
"""
JWT Key Generation Script

Usage:
    python scripts/setup/setup_jwt.py [OPTIONS]

Options:
    --output-dir PATH    Directory for keys (default: secrets/jwt)
    --force              Regenerate even if keys exist
    --validate-only      Only validate existing keys
    --backup             Backup existing keys before regeneration
    --non-interactive    No prompts, use defaults
"""

import click
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

@click.command()
@click.option('--output-dir', default='secrets/jwt', help='Output directory')
@click.option('--force', is_flag=True, help='Force regeneration')
@click.option('--validate-only', is_flag=True, help='Only validate')
@click.option('--backup', is_flag=True, help='Backup existing keys')
@click.option('--non-interactive', is_flag=True, help='No prompts')
def main(output_dir, force, validate_only, backup, non_interactive):
    """Generate or validate JWT keys for PromptVault."""

    # Implementation steps:
    # 1. Initialize console
    # 2. Check existing keys
    # 3. Backup if requested
    # 4. Generate new keys
    # 5. Set permissions
    # 6. Validate keys
    # 7. Report results
    pass

def generate_key_pair() -> tuple[bytes, bytes]:
    """Generate ES256 key pair."""
    pass

def validate_key_pair(private_path: Path, public_path: Path) -> bool:
    """Validate key pair can sign and verify."""
    pass

def backup_keys(output_dir: Path) -> Path:
    """Backup existing keys to timestamped directory."""
    pass

def ensure_gitignore(secrets_dir: Path):
    """Ensure secrets directory is in .gitignore."""
    pass

if __name__ == '__main__':
    main()
```

### 6.4 Environment Setup Script Structure

```python
#!/usr/bin/env python3
"""
Environment Configuration Script

Usage:
    python scripts/setup/setup_env.py [OPTIONS]

Options:
    --profile [dev|prod]    Configuration profile
    --from-file PATH        Load configuration from YAML
    --validate-only         Only validate existing .env
    --non-interactive       No prompts, use defaults
"""

import click
from pathlib import Path

@click.command()
@click.option('--profile', type=click.Choice(['development', 'production']))
@click.option('--from-file', type=click.Path(exists=True))
@click.option('--validate-only', is_flag=True)
@click.option('--non-interactive', is_flag=True)
def main(profile, from_file, validate_only, non_interactive):
    """Configure environment for PromptVault."""

    # Implementation steps:
    # 1. Initialize console
    # 2. Load template or existing config
    # 3. Determine profile
    # 4. Collect/validate configuration
    # 5. Generate secrets
    # 6. Write .env file
    # 7. Validate result
    pass

class EnvConfigurator:
    """Environment configuration manager."""

    def __init__(self, profile: str):
        self.profile = profile
        self.config = {}

    def load_template(self) -> dict:
        """Load template for profile."""
        pass

    def prompt_database(self) -> dict:
        """Interactive database configuration."""
        pass

    def prompt_security(self) -> dict:
        """Interactive security configuration."""
        pass

    def prompt_email(self) -> dict:
        """Interactive email configuration."""
        pass

    def generate_secrets(self) -> dict:
        """Generate secure random values."""
        pass

    def validate(self) -> list[str]:
        """Validate all configuration values."""
        pass

    def write(self, path: Path):
        """Write configuration to .env file."""
        pass

    def diff(self, existing: dict) -> str:
        """Show diff between existing and new config."""
        pass

if __name__ == '__main__':
    main()
```

### 6.5 Database Setup Script Structure

```python
#!/usr/bin/env python3
"""
Database Setup Script

Usage:
    python scripts/setup/setup_database.py [OPTIONS]

Options:
    --type [postgresql|sqlite]    Database type
    --host TEXT                   PostgreSQL host
    --port INTEGER                PostgreSQL port
    --database TEXT               Database name
    --user TEXT                   Database user
    --migrate-only                Only run migrations
    --create-admin                Create admin user after setup
    --non-interactive             No prompts
"""

import click
from pathlib import Path

@click.command()
@click.option('--type', 'db_type', type=click.Choice(['postgresql', 'sqlite']))
@click.option('--host', default='localhost')
@click.option('--port', default=5432, type=int)
@click.option('--database', default='promptvault')
@click.option('--user', default='promptvault')
@click.option('--migrate-only', is_flag=True)
@click.option('--create-admin', is_flag=True)
@click.option('--non-interactive', is_flag=True)
def main(db_type, host, port, database, user, migrate_only, create_admin, non_interactive):
    """Set up database for PromptVault."""

    # Implementation steps:
    # 1. Initialize console
    # 2. Determine database type
    # 3. Create database/user if needed
    # 4. Test connectivity
    # 5. Run migrations
    # 6. Verify schema
    # 7. Create admin if requested
    pass

class PostgreSQLSetup:
    """PostgreSQL database setup."""

    def __init__(self, host, port, database, user):
        pass

    def check_server(self) -> bool:
        """Check PostgreSQL server is running."""
        pass

    def create_database(self, admin_password: str) -> bool:
        """Create database and user."""
        pass

    def test_connection(self, password: str) -> bool:
        """Test connection with user credentials."""
        pass

    def run_migrations(self) -> bool:
        """Run Alembic migrations."""
        pass

    def verify_schema(self) -> list[str]:
        """Verify all expected tables exist."""
        pass

class SQLiteSetup:
    """SQLite database setup."""

    def __init__(self, path: Path):
        pass

    def create_database(self) -> bool:
        """Create SQLite database file."""
        pass

    def run_migrations(self) -> bool:
        """Run Alembic migrations."""
        pass

    def verify_schema(self) -> list[str]:
        """Verify all expected tables exist."""
        pass

if __name__ == '__main__':
    main()
```

### 6.6 Main Wizard Structure

```python
#!/usr/bin/env python3
"""
PromptVault Setup Wizard

Usage:
    python scripts/setup/setup.py [OPTIONS]

Options:
    --quick                Quick setup with defaults
    --advanced             Advanced configuration
    --component NAME       Run specific component (jwt, env, database, deploy)
    --config PATH          Configuration file path
    --non-interactive      No prompts
"""

import click
from pathlib import Path

@click.command()
@click.option('--quick', is_flag=True)
@click.option('--advanced', is_flag=True)
@click.option('--component', type=click.Choice(['jwt', 'env', 'database', 'deploy']))
@click.option('--config', type=click.Path(exists=True))
@click.option('--non-interactive', is_flag=True)
def main(quick, advanced, component, config, non_interactive):
    """PromptVault Setup Wizard."""

    wizard = SetupWizard(non_interactive=non_interactive)

    if component:
        wizard.run_component(component)
    elif quick:
        wizard.run_quick_setup()
    elif advanced:
        wizard.run_advanced_setup()
    else:
        wizard.run_interactive()

class SetupWizard:
    """Main setup wizard orchestrator."""

    def __init__(self, non_interactive: bool = False):
        self.non_interactive = non_interactive
        self.state_file = Path('.setup_state.json')

    def run_interactive(self):
        """Run full interactive wizard."""
        # 1. Welcome screen
        # 2. Mode selection
        # 3. Run selected mode
        pass

    def run_quick_setup(self):
        """Run quick setup with sensible defaults."""
        # 1. Detect environment
        # 2. Generate JWT keys
        # 3. Create default .env
        # 4. Setup SQLite database
        # 5. Run migrations
        # 6. Prompt for admin credentials
        # 7. Start services
        # 8. Show access info
        pass

    def run_advanced_setup(self):
        """Run advanced setup with full customization."""
        # 1. JWT configuration
        # 2. Environment configuration
        # 3. Database configuration
        # 4. Deployment options
        # 5. Execute setup
        # 6. Verify deployment
        pass

    def run_component(self, component: str):
        """Run a specific setup component."""
        pass

    def save_state(self):
        """Save wizard state for resume."""
        pass

    def load_state(self) -> dict | None:
        """Load saved wizard state."""
        pass

    def show_summary(self):
        """Show final deployment summary."""
        pass

if __name__ == '__main__':
    main()
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Component | Test Coverage |
|-----------|---------------|
| `utils/validators.py` | All validation functions with valid/invalid inputs |
| `utils/console.py` | Mock console output verification |
| `utils/config_parser.py` | Template parsing, variable substitution |
| `setup_jwt.py` | Key generation, validation, file operations |
| `setup_env.py` | Configuration parsing, validation, generation |
| `setup_database.py` | Connection testing, migration running |

### 7.2 Integration Tests

| Test Scenario | Description |
|---------------|-------------|
| Full Quick Setup | Run quick setup from scratch to running app |
| PostgreSQL Setup | Full PostgreSQL configuration and deployment |
| SQLite Setup | Full SQLite configuration and deployment |
| Key Rotation | Generate new keys with backup and validation |
| Config Migration | Upgrade .env from older version |
| Failed Recovery | Rollback after deployment failure |

### 7.3 Test Environment

```yaml
# docker-compose.test.yml
services:
  test-postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_PASSWORD: testpassword
    tmpfs:
      - /var/lib/postgresql/data

  test-redis:
    image: redis:7-alpine
    tmpfs:
      - /data
```

### 7.4 Test Commands

```bash
# Run unit tests
pytest scripts/setup/tests/ -v

# Run integration tests
pytest scripts/setup/tests/test_integration.py -v --slow

# Run with coverage
pytest scripts/setup/tests/ --cov=scripts/setup --cov-report=html
```

---

## 8. Rollback Plan

### 8.1 Automated Rollback Triggers

| Condition | Action |
|-----------|--------|
| Database migration fails | Revert to previous migration state |
| Service fails to start | Restore previous Docker images |
| Health check fails | Stop new services, restore backup |
| Configuration validation fails | Keep original .env, abort setup |

### 8.2 Manual Rollback Commands

```bash
# Restore database from backup
docker-compose exec db psql -U promptvault -d promptvault < backup.sql

# Restore previous configuration
cp .env.backup .env
docker-compose up -d

# Rollback migrations
docker-compose exec web alembic downgrade -1

# Restore JWT keys
cp -r secrets/jwt.backup/* secrets/jwt/
```

### 8.3 State Preservation

The wizard maintains state in `.setup_state.json`:

```json
{
  "started_at": "2026-02-02T10:00:00Z",
  "last_checkpoint": "database_setup",
  "completed_steps": ["jwt_generation", "env_configuration"],
  "backups": {
    "env": ".env.backup.20260202_100000",
    "jwt": "secrets/jwt.backup.20260202_100000"
  },
  "config": {
    "profile": "production",
    "database_type": "postgresql"
  }
}
```

---

## 9. Documentation Updates

### 9.1 New Documentation Files

**`docs/QUICK_START.md`:**
```markdown
# Quick Start Guide

Get PromptVault running in under 5 minutes.

## Prerequisites
- Docker and Docker Compose
- Python 3.11+

## One-Command Setup
\```bash
python scripts/setup/setup.py --quick
\```

This will:
1. Generate JWT keys
2. Create development configuration
3. Initialize SQLite database
4. Start the application

Access PromptVault at http://localhost:8001
```

**`docs/TROUBLESHOOTING.md`:**
- Common issues and solutions
- Debug commands
- Log locations
- How to report issues

### 9.2 README.md Updates

Add new "Quick Start" section:

```markdown
## Quick Start

### Automated Setup (Recommended)
\```bash
git clone https://github.com/username/PromptVault.git
cd PromptVault
python scripts/setup/setup.py
\```

### Manual Setup
See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed manual installation.
```

### 9.3 DEPLOYMENT.md Updates

- Add section for automated deployment
- Reference new setup scripts
- Update manual process as "alternative"
- Add troubleshooting references

---

## 10. Security Considerations

### 10.1 Secrets Handling

| Secret | Generation | Storage | Protection |
|--------|------------|---------|------------|
| JWT Private Key | `cryptography` library | `secrets/jwt/` (chmod 600) | .gitignore, file permissions |
| Database Password | `secrets.token_urlsafe(32)` | `.env` file | .gitignore, file permissions |
| SECRET_KEY | `secrets.token_urlsafe(64)` | `.env` file | .gitignore, file permissions |
| Admin Password | User-provided | Database (Argon2id hash) | Never stored in plaintext |

### 10.2 File Permissions

| File/Directory | Permissions | Rationale |
|----------------|-------------|-----------|
| `secrets/` | 700 | Only owner can access |
| `secrets/jwt/private_key.pem` | 600 | Only owner can read/write |
| `secrets/jwt/public_key.pem` | 644 | Public key can be world-readable |
| `.env` | 600 | Contains secrets |

### 10.3 Security Validations

The setup scripts enforce:

1. **Password Strength**
   - Minimum 16 characters for generated passwords
   - User-provided admin password follows policy (12+ chars, complexity)

2. **Key Security**
   - ES256 keys (ECDSA P-256) - NIST recommended
   - Keys never logged or displayed
   - Keys validated after generation

3. **Configuration Security**
   - Secrets validated for minimum entropy
   - HTTPS recommended for production (warning if HTTP)
   - Rate limiting enabled by default for production

4. **Deployment Security**
   - Non-root containers
   - Health checks before exposure
   - Secure defaults for all settings

---

## Appendix A: Configuration File Format

For automated deployments, a YAML configuration file can be used:

```yaml
# setup.yaml
profile: production

jwt:
  output_dir: secrets/jwt
  regenerate: false
  backup: true

database:
  type: postgresql
  host: localhost
  port: 5432
  name: promptvault
  user: promptvault
  # password: PROMPT (interactive) or from env var SETUP_DB_PASSWORD

environment:
  ENVIRONMENT: production
  LOG_LEVEL: WARNING
  # Additional overrides

admin:
  create: true
  username: admin
  email: admin@example.com
  # password: PROMPT (interactive) or from env var SETUP_ADMIN_PASSWORD

deploy:
  rebuild: false
  skip_backup: false
  wait_timeout: 120
```

---

## Appendix B: Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| E001 | Docker not installed | Install Docker |
| E002 | Docker daemon not running | Start Docker service |
| E003 | Port already in use | Change port or stop conflicting service |
| E004 | Database connection failed | Check database server and credentials |
| E005 | Migration failed | Check database state, review migration logs |
| E006 | JWT key generation failed | Check permissions, disk space |
| E007 | Invalid configuration | Review .env file, check validation errors |
| E008 | Health check timeout | Check container logs, increase timeout |
| E009 | Insufficient permissions | Run with appropriate permissions |
| E010 | Disk space insufficient | Free up disk space |

---

## Appendix C: Dependencies

### New Python Dependencies

```toml
# pyproject.toml additions
[project.dependencies]
click = ">=8.1.0"
rich = ">=13.0.0"

[project.optional-dependencies]
setup = [
    "click>=8.1.0",
    "rich>=13.0.0",
    "PyYAML>=6.0",
]
```

### System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.11 | 3.12 |
| Docker | 20.10 | 24.0+ |
| Docker Compose | 2.0 | 2.20+ |
| Disk Space | 2 GB | 5 GB |
| RAM | 2 GB | 4 GB |

---

## Appendix D: Success Criteria

The turnkey deployment solution will be considered complete when:

1. **Functionality**
   - [ ] Single command starts complete setup process
   - [ ] Interactive wizard guides users through all options
   - [ ] Non-interactive mode supports automated deployments
   - [ ] All individual components work standalone
   - [ ] Proper error handling and recovery

2. **Quality**
   - [ ] Unit test coverage > 80%
   - [ ] Integration tests pass for all deployment scenarios
   - [ ] No security vulnerabilities introduced
   - [ ] Performance: Setup completes in < 5 minutes

3. **Documentation**
   - [ ] Quick start guide is complete and accurate
   - [ ] All options documented with examples
   - [ ] Troubleshooting guide covers common issues
   - [ ] Existing documentation updated

4. **User Experience**
   - [ ] Clear progress indicators throughout setup
   - [ ] Helpful error messages with resolution steps
   - [ ] Successful deployment shows access information
   - [ ] Resume support for interrupted setups

---

*End of Implementation Plan*
