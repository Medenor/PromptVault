# PromptVault Setup Wizard

The **Setup Wizard** (`setup.py`) is the main entry point for deploying PromptVault. It provides a streamlined, interactive experience that orchestrates all setup components for a complete turnkey deployment.

## Features

- **Multiple Setup Modes**: Choose from Quick, Advanced, or Component-based setup
- **Interactive Wizard**: Step-by-step guidance with sensible defaults
- **Resume Support**: Continue from where you left off if interrupted
- **Non-interactive Mode**: Perfect for automation and CI/CD pipelines
- **Profile-based Configuration**: Development and production presets
- **Component Orchestration**: Automatically runs all setup scripts in the correct order

## Quick Start

### Interactive Setup (Recommended)

The easiest way to get started:

```bash
python scripts/setup/setup.py
```

This launches the interactive wizard that will guide you through:
1. Mode selection (Quick/Advanced/Component)
2. JWT key generation
3. Environment configuration
4. Database setup
5. Admin user creation
6. Application deployment

### Quick Setup (Fast Track)

Get running in minutes with sensible defaults:

```bash
python scripts/setup/setup.py --quick
```

Quick setup automatically:
- Uses SQLite database (no PostgreSQL required)
- Generates JWT keys
- Configures for development environment
- Sets up database with migrations
- Deploys with Docker Compose

Perfect for: Development, testing, quick demos

### Advanced Setup (Production)

Full customization for production deployments:

```bash
python scripts/setup/setup.py --advanced
```

Advanced setup provides:
- Profile selection (development/production)
- Database choice (PostgreSQL/SQLite)
- Interactive configuration prompts
- Security settings customization
- Production-ready defaults

Perfect for: Production deployments, custom configurations

## Setup Modes

### 1. Quick Setup Mode

**Purpose**: Get PromptVault running quickly with minimal configuration

**When to use**:
- First-time setup
- Development environments
- Testing and demos
- Learning the system

**What it does**:
1. Generates JWT keys automatically
2. Creates `.env` with development profile
3. Sets up SQLite database
4. Prompts for admin user creation
5. Deploys with Docker Compose
6. Shows access information

**Command**:
```bash
python scripts/setup/setup.py --quick
```

**Time required**: ~5 minutes

### 2. Advanced Setup Mode

**Purpose**: Full control over deployment configuration

**When to use**:
- Production deployments
- Custom database configurations
- Specific security requirements
- Multi-environment setups

**What it does**:
1. Profile selection (development/production)
2. Interactive JWT configuration
3. Full environment variable configuration
4. Database type selection and setup
5. Admin user creation
6. Deployment with customization

**Command**:
```bash
python scripts/setup/setup.py --advanced
```

**Time required**: ~15-30 minutes

### 3. Component Setup Mode

**Purpose**: Run individual setup scripts independently

**When to use**:
- Re-running specific steps
- Debugging setup issues
- Updating specific components
- Partial deployments

**Available components**:
- `jwt` - Generate JWT signing keys
- `env` - Configure environment variables
- `database` - Setup and initialize database
- `deploy` - Deploy the application

**Commands**:
```bash
# Run specific component
python scripts/setup/setup.py --component jwt
python scripts/setup/setup.py --component env
python scripts/setup/setup.py --component database
python scripts/setup/setup.py --component deploy

# Interactive component menu
python scripts/setup/setup.py
# Then select "Component Setup"
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--quick` | Quick setup with defaults (SQLite, auto-config) |
| `--advanced` | Advanced setup with full customization |
| `--component COMPONENT` | Run specific component (`jwt`, `env`, `database`, `deploy`) |
| `--config PATH` | Load configuration from YAML file |
| `--non-interactive` | Run without prompts (use defaults) |
| `--help` | Show help message and exit |

## Deployment Profiles

### Development Profile

**Characteristics**:
- SQLite database (file-based, no server required)
- Debug logging enabled
- Relaxed security settings (for easier testing)
- Local-only access by default
- Fast iteration and debugging

**Default settings**:
- `DATABASE_URL`: `sqlite:///./data/promptvault.db`
- `ENVIRONMENT`: `development`
- `LOG_LEVEL`: `DEBUG`
- `DB_ECHO`: `true` (SQL query logging)

**Use when**:
- Developing locally
- Running tests
- Learning the system
- Quick prototypes

### Production Profile

**Characteristics**:
- PostgreSQL database (recommended)
- Warning-level logging
- Strict security settings
- Production-optimized performance
- Comprehensive monitoring

**Default settings**:
- `DATABASE_URL`: `postgresql://...` (PostgreSQL)
- `ENVIRONMENT`: `production`
- `LOG_LEVEL`: `WARNING`
- `DB_ECHO`: `false`
- Strict password policies
- Rate limiting enabled

**Use when**:
- Deploying to production
- Handling real user data
- Security is critical
- High availability required

## Resume Support

The wizard automatically saves your progress to `.setup_state.json`. If setup is interrupted:

```bash
# Run the wizard again
python scripts/setup/setup.py

# It will detect the saved state and ask:
# "Found saved setup state from 2024-02-03T14:30:00"
# "Do you want to resume? [Y/n]"
```

The wizard will:
- Skip completed steps
- Resume from where you left off
- Preserve your configuration choices
- Clear state on successful completion

To start fresh (ignore saved state):
```bash
# Delete the state file
rm .setup_state.json

# Or answer "No" when prompted to resume
```

## Non-Interactive Mode

Perfect for automation, CI/CD, and scripted deployments:

```bash
# Quick setup without prompts
python scripts/setup/setup.py --quick --non-interactive

# Advanced setup with defaults
python scripts/setup/setup.py --advanced --non-interactive

# Component setup
python scripts/setup/setup.py --component jwt --non-interactive
```

**Behavior**:
- Uses profile defaults (no prompts)
- Auto-generates secure passwords
- Uses sensible defaults for all settings
- Exits with appropriate status codes
  - `0` = Success
  - `1` = Failure

**Example CI/CD usage**:
```yaml
# forgejo Actions
- name: Setup PromptVault
  run: |
    python scripts/setup/setup.py --quick --non-interactive

# GitLab CI
script:
  - python scripts/setup/setup.py --quick --non-interactive
```

## Configuration from File

Load configuration from a YAML file:

```bash
python scripts/setup/setup.py --config config.yaml --non-interactive
```

**Example `config.yaml`**:
```yaml
development:
  DATABASE_URL: sqlite:///./data/promptvault.db
  ENVIRONMENT: development
  LOG_LEVEL: DEBUG
  JWT_PRIVATE_KEY_PATH: secrets/jwt/private_key.pem
  JWT_PUBLIC_KEY_PATH: secrets/jwt/public_key.pem

production:
  DATABASE_URL: postgresql://user:pass@localhost:5432/promptvault
  ENVIRONMENT: production
  LOG_LEVEL: WARNING
  JWT_PRIVATE_KEY_PATH: /etc/promptvault/jwt/private_key.pem
  JWT_PUBLIC_KEY_PATH: /etc/promptvault/jwt/public_key.pem
```

## Component Details

### JWT Component

**Purpose**: Generate ES256 (ECDSA P-256) key pairs for JWT signing

**What it does**:
- Generates cryptographically secure key pairs
- Sets appropriate file permissions (600 for private, 644 for public)
- Validates keys by testing sign/verify operations
- Checks `.gitignore` configuration

**Output**:
- `secrets/jwt/private_key.pem` (keep secret!)
- `secrets/jwt/public_key.pem` (can be shared)

**Standalone usage**:
```bash
python scripts/setup/setup_jwt.py --help
```

### Environment Component

**Purpose**: Configure all environment variables with validation

**What it does**:
- Prompts for database configuration
- Configures security settings (JWT, passwords, rate limiting)
- Sets up email configuration (optional)
- Validates all settings
- Writes to `.env` file

**Output**:
- `.env` file with validated configuration

**Standalone usage**:
```bash
python scripts/setup/setup_env.py --help
```

### Database Component

**Purpose**: Setup and initialize the database

**What it does**:
- Creates PostgreSQL database and user (if PostgreSQL)
- Tests database connectivity
- Runs Alembic migrations (`upgrade head`)
- Verifies schema integrity

**Output**:
- Initialized database with latest schema
- Applied migrations

**Standalone usage**:
```bash
python scripts/setup/setup_database.py --help
```

### Deploy Component

**Purpose**: Deploy the application with Docker Compose

**What it does**:
- Runs pre-flight checks (Docker, ports, disk space)
- Creates database backup
- Starts infrastructure (PostgreSQL, Redis)
- Runs migrations
- Starts application
- Performs smoke tests
- Shows access information

**Output**:
- Running PromptVault instance on http://localhost:8001

**Standalone usage**:
```bash
python scripts/setup/deploy.py --help
```

## Setup Flow Diagram

### Quick Setup Flow
```
Start
  ↓
Generate JWT Keys
  ↓
Create .env (development)
  ↓
Setup SQLite Database
  ↓
Create Admin User (prompt)
  ↓
Deploy Application
  ↓
Show Access Information
  ↓
Complete!
```

### Advanced Setup Flow
```
Start
  ↓
Select Profile (dev/prod)
  ↓
JWT Configuration
  ↓
Environment Configuration (interactive)
  ↓
Select Database Type
  ↓
Database Setup
  ↓
Create Admin User (prompt)
  ↓
Review & Confirm
  ↓
Deploy Application
  ↓
Show Access Information
  ↓
Complete!
```

## Post-Setup Steps

After successful setup, you can:

### 1. Access PromptVault

Open your browser to:
- **Web Interface**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **API Endpoint**: http://localhost:8001/api

### 2. Create Admin User

The wizard prompts for admin credentials but doesn't create the user automatically. Create it after deployment:

```bash
python scripts/create_admin.py --username admin --email admin@example.com
```

### 3. Manage Services

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Check status
docker-compose ps

# View specific service logs
docker-compose logs -f web
```

### 4. Backup Database

```bash
# PostgreSQL backup
docker-compose exec db pg_dump -U promptvault promptvault > backup.sql

# SQLite backup
cp data/promptvault.db data/promptvault.db.backup
```

## Troubleshooting

### Wizard Stuck or Interrupted

If the wizard is interrupted:
1. Run it again: `python scripts/setup/setup.py`
2. Choose "Yes" to resume from saved state
3. Or delete `.setup_state.json` to start fresh

### Component Failed

Run the failed component individually:

```bash
# If JWT setup failed
python scripts/setup/setup.py --component jwt

# If environment setup failed
python scripts/setup/setup.py --component env

# If database setup failed
python scripts/setup/setup.py --component database

# If deployment failed
python scripts/setup/setup.py --component deploy
```

### Import Errors

Ensure dependencies are installed:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Or if using setup tools
pip install -e .
```

### Docker Issues

Check Docker is running:

```bash
# Check Docker status
docker ps

# Check Docker Compose
docker-compose version

# View Docker logs
docker-compose logs
```

### Port Already in Use

Change the port in `docker-compose.yml`:

```yaml
services:
  web:
    ports:
      - "8002:8000"  # Changed from 8001 to 8002
```

### Database Connection Failed

Check database status:

```bash
# PostgreSQL
docker-compose exec db psql -U promptvault -c "SELECT 1"

# Check database logs
docker-compose logs db
```

## Advanced Usage

### Custom JWT Key Location

```bash
# Generate keys in custom location
python scripts/setup/setup_jwt.py --output-dir /etc/promptvault/jwt

# Update .env to reference custom location
JWT_PRIVATE_KEY_PATH=/etc/promptvault/jwt/private_key.pem
JWT_PUBLIC_KEY_PATH=/etc/promptvault/jwt/public_key.pem
```

### Multiple Environments

```bash
# Development setup
python scripts/setup/setup.py --quick
# Uses .env

# Production setup (separate directory)
cd /opt/promptvault
python scripts/setup/setup.py --advanced --non-interactive --config prod-config.yaml
# Uses .env in production directory
```

### Automated Testing

```bash
# Run setup in test mode
python scripts/setup/setup.py --quick --non-interactive

# Run tests
pytest

# Cleanup
docker-compose down -v
rm .env .setup_state.json
```

## Files Created by Setup

The wizard creates the following files:

| File | Purpose | Location |
|------|---------|----------|
| `secrets/jwt/private_key.pem` | JWT private key (keep secret!) | Project root |
| `secrets/jwt/public_key.pem` | JWT public key | Project root |
| `.env` | Environment configuration | Project root |
| `.setup_state.json` | Wizard state for resume | Project root |
| `data/promptvault.db` | SQLite database (if SQLite) | Project root |
| `data/backups/*.sql.gz` | Database backups | Project root |

**Important**: Never commit these files to version control!

## Security Considerations

1. **Keep Private Keys Secret**
   - Never commit `private_key.pem` to Git
   - Ensure `secrets/` is in `.gitignore`
   - Set appropriate file permissions (600)

2. **Secure .env File**
   - Contains sensitive credentials
   - Should not be committed to Git
   - Use `.env.example` as template

3. **Production Deployments**
   - Always use PostgreSQL in production
   - Enable HTTPS/TLS for web access
   - Use strong passwords (auto-generated recommended)
   - Enable all security features (rate limiting, etc.)
   - Regular backups

4. **Database Security**
   - Use strong database passwords
   - Restrict database access to localhost
   - Regular security updates

## Integration with Other Scripts

The setup wizard integrates seamlessly with other PromptVault scripts:

```bash
# After setup, create admin user
python scripts/create_admin.py

# Run migrations manually
alembic upgrade head

# Deploy without wizard
python scripts/setup/deploy.py

# Pre-deployment checks
bash scripts/pre-deploy-check.sh
```

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review individual component documentation:
   - `scripts/setup/setup_jwt.py --help`
   - `scripts/setup/setup_env.py --help`
   - `scripts/setup/setup_database.py --help`
   - `scripts/setup/deploy.py --help`
3. Check Codeberg issues or create a new one
4. Review Docker logs: `docker-compose logs -f`

## License

This script is part of PromptVault and is subject to the Mozilla Public License v2.0.
