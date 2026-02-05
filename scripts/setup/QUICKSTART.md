# PromptVault Quick Start Guide

Get PromptVault running in 5 minutes with the setup wizard.

## Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose
- Git (for cloning the repository)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/promptvault.git
cd promptvault
```

### 2. Install Dependencies

```bash
# Using pip
pip install -r requirements.txt

# Or using the project
pip install -e .
```

### 3. Run the Setup Wizard

```bash
python scripts/setup/setup.py
```

The wizard will guide you through:
- Choosing setup mode (Quick/Advanced/Component)
- Generating JWT keys
- Configuring environment
- Setting up database
- Creating admin user
- Deploying the application

### 4. Choose Quick Setup (Recommended)

When prompted, select **Quick Setup** for the fastest experience:

```
Select Setup Mode:

  1. Quick Setup - Get running in minutes (SQLite, auto-config)
     Perfect for: Development, testing, quick demos

  2. Advanced Setup - Full customization (PostgreSQL, production-ready)
     Perfect for: Production deployments, custom configurations

  3. Component Setup - Run individual setup scripts
     Perfect for: Re-running specific steps, debugging

Choose your setup mode: quick
```

### 5. Follow the Prompts

Quick setup will:
- ✓ Generate JWT keys automatically
- ✓ Create `.env` with development defaults
- ✓ Setup SQLite database
- ✓ Prompt for admin username and email
- ✓ Deploy with Docker Compose

### 6. Access PromptVault

Once setup completes, open your browser to:

```
http://localhost:8001
```

API Documentation:
```
http://localhost:8001/docs
```

## Alternative: One-Command Setup

For completely automated setup:

```bash
python scripts/setup/setup.py --quick --non-interactive
```

This uses all defaults without prompts.

## Creating Your Admin User

After deployment, create your admin account:

```bash
python scripts/create_admin.py --username admin --email admin@example.com
```

You'll be prompted to set a password.

## Managing Your Instance

### View Logs

```bash
docker-compose logs -f
```

### Stop Services

```bash
docker-compose down
```

### Restart Services

```bash
docker-compose restart
```

### Check Status

```bash
docker-compose ps
```

## Troubleshooting

### Port Already in Use

If port 8001 is already in use, edit `docker-compose.yml`:

```yaml
services:
  web:
    ports:
      - "8002:8000"  # Changed from 8001 to 8002
```

### Docker Not Running

Start Docker:
- **macOS/Windows**: Start Docker Desktop
- **Linux**: `sudo systemctl start docker`

### Setup Failed

Run individual components:

```bash
# JWT keys
python scripts/setup/setup.py --component jwt

# Environment
python scripts/setup/setup.py --component env

# Database
python scripts/setup/setup.py --component database

# Deploy
python scripts/setup/setup.py --component deploy
```

### Resume Interrupted Setup

The wizard automatically saves progress. Just run it again:

```bash
python scripts/setup/setup.py
```

Choose "Yes" when asked to resume.

## Production Deployment

For production, use Advanced Setup:

```bash
python scripts/setup/setup.py --advanced
```

This provides:
- PostgreSQL database (recommended)
- Strict security settings
- Production-optimized configuration
- Email configuration
- Full customization

## Configuration File

For automated deployments, use a configuration file:

```bash
# Copy example config
cp scripts/setup/templates/config.example.yaml my-config.yaml

# Edit your configuration
nano my-config.yaml

# Run setup with config
python scripts/setup/setup.py --config my-config.yaml --non-interactive
```

## Next Steps

After setup:

1. **Create admin user**: `python scripts/create_admin.py`
2. **Log in**: http://localhost:8001
3. **Create your first prompt**: Start organizing!
4. **Invite team members**: Manage users in settings
5. **Backup your data**: `docker-compose exec db pg_dump ...`

## Getting Help

- **Documentation**: See `scripts/setup/SETUP_WIZARD_README.md`
- **Component Help**: `python scripts/setup/setup.py --help`
- **Individual Scripts**:
  - `python scripts/setup/setup_jwt.py --help`
  - `python scripts/setup/setup_env.py --help`
  - `python scripts/setup/setup_database.py --help`
  - `python scripts/setup/deploy.py --help`

## Summary

```bash
# Quick Start (5 minutes)
git clone <repo>
cd promptvault
pip install -e .
python scripts/setup/setup.py --quick
python scripts/create_admin.py
# Open http://localhost:8001

# Or One Command
python scripts/setup/setup.py --quick --non-interactive
```

Happy prompting! 🚀
