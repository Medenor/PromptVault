# PromptVault Quick Start Guide

Get PromptVault running in under 5 minutes with this streamlined setup guide.

## Prerequisites

Before you begin, ensure you have:

- **Docker** and **Docker Compose** installed
- **Python 3.11+** (for running setup scripts)
- **Git** (for cloning the repository)

## One-Command Setup

For the fastest setup with sensible defaults:

```bash
git clone https://codeberg.org/medenor/promptvault.git && \
cd PromptVault && \
python scripts/setup/setup.py --quick
```

This single command will handle everything automatically.

## Quick Setup Walkthrough

If you prefer to understand each step, follow this guide:

### Step 1: Clone Repository

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
```

### Step 2: Run Setup Wizard

```bash
python scripts/setup/setup.py --quick
```

The setup wizard will automatically:
- Generate secure JWT signing keys
- Create environment configuration file (.env)
- Initialize SQLite database
- Set up Docker containers
- Apply database migrations

**Note:** The wizard is interactive and will prompt you to create an admin account.

### Step 3: Access PromptVault

Open your browser and navigate to:

```
http://localhost:8001
```

### Step 4: First Login

After setup completes, create your admin user:

```bash
python scripts/create_admin_user.py
```

Follow the prompts to set:
- Username
- Email
- Password (minimum 12 characters with complexity requirements)

Then log in with your credentials at `http://localhost:8001`

## What Gets Set Up

The quick setup automatically configures:

**JWT Keys**
- ES256 private and public keys for secure authentication
- Stored in `secrets/jwt/` (never committed to Git)

**SQLite Database**
- Lightweight embedded database at `data/promptvault.db`
- Perfect for development and small deployments
- All tables and indexes created automatically

**Development Configuration**
- Debug logging enabled
- SQLite as database backend
- Relaxed security settings for development
- Environment variables in `.env` file

**Admin User Account**
- Full administrative privileges
- Can manage users, prompts, categories, and tags
- Access to system-wide features and backups

**Running Application**
- Web interface at `http://localhost:8001`
- API endpoints at `http://localhost:8001/api`
- API documentation at `http://localhost:8001/docs`
- Health check at `http://localhost:8001/api/health`

## Access Information

Once setup is complete:

**URL:** `http://localhost:8001`

**Default Ports:**
- Web Application: 8001
- PostgreSQL (if used): 5432
- Redis: 6379

**Useful Commands:**

```bash
# View application logs
docker-compose logs -f web

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Check service status
docker-compose ps
```

## Common Next Steps

### Importing Existing Prompts

If you have prompts in CSV, Markdown, or JSON format:

1. Navigate to **Import/Export** in the web interface
2. Select your file format
3. Upload and preview your prompts
4. Confirm import

Alternatively, use the migration script for JSON files:

```bash
python scripts/migrate_json_to_db.py
```

### Creating New Prompts

1. Click the **+ New Prompt** button
2. Fill in prompt details:
   - Title
   - Content
   - Category
   - Tags
3. Save with a commit message (for version control)

### Setting Up Teams

As an admin, you can create and manage users:

1. Navigate to **Admin > User Management**
2. Click **Create User**
3. Assign roles:
   - **Viewer**: Read-only access
   - **Editor**: Full CRUD operations
   - **Admin**: User management + all features

### Configuring Backups

Enable automatic backups for data protection:

1. Navigate to **Backup Management**
2. Click **Create Backup** to test manual backup
3. Configure automatic pre-operation backups (enabled by default)
4. Set up backup retention policies for cleanup

## Advanced Setup Options

For production deployments with PostgreSQL, custom configuration, and full security:

```bash
python scripts/setup/setup.py --advanced
```

This mode provides:
- PostgreSQL database setup
- Production security settings
- Custom environment configuration
- SSL/TLS options
- Email configuration for password resets

## Links to Full Documentation

**Production Deployment:**
- [Deployment Guide](DEPLOYMENT.md) - Complete production setup instructions
- [Authentication Security](AUTHENTICATION_SECURITY.md) - Security best practices

**Development:**
- [README](../README.md) - Project overview and features
- [Testing Guide](TESTING.md) - Running tests and coverage

**Troubleshooting:**
- [Deployment Guide > Troubleshooting](DEPLOYMENT.md#troubleshooting) - Common issues and solutions
- [Health Checks](DEPLOYMENT.md#health-checks) - Verify deployment status

**Features:**
- [Version Control](VERSION_CONTROL.md) - Git-like versioning for prompts
- [API Documentation](AUTHENTICATION_API.md) - Complete API reference

## Troubleshooting

### Setup Script Not Found

**Problem:** `python scripts/setup/setup.py` fails with "No such file or directory"

**Solution:** Ensure you're in the PromptVault root directory:

```bash
cd PromptVault
ls scripts/setup/setup.py  # Should exist
```

### Port Already in Use

**Problem:** "address already in use" error on port 8001

**Solution:** Either stop the conflicting service or change the port in `docker-compose.yml`:

```yaml
ports:
  - "8002:8000"  # Use 8002 instead
```

### Database Connection Failed

**Problem:** Application can't connect to database

**Solution:** Verify Docker containers are running:

```bash
docker-compose ps
docker-compose logs db
```

If PostgreSQL isn't starting, check the password in `.env` matches `docker-compose.yml`.

### JWT Keys Missing

**Problem:** Authentication fails with "JWT key not found"

**Solution:** Regenerate JWT keys:

```bash
python scripts/setup/setup.py --component jwt
```

### Permission Denied Errors

**Problem:** Docker containers fail with permission errors

**Solution:** Fix data directory permissions:

```bash
sudo chown -R $(id -u):$(id -g) ./data
```

## Need Help?

**Issues & Bug Reports:**
- [Codeberg Issues](https://codeberg.org/medenor/promptvault/issues)

**Documentation:**
- [Full Documentation](DEPLOYMENT.md) - Comprehensive deployment guide
- [README](../README.md) - Project overview and architecture

**Community:**
- [Codeberg Profile](https://codeberg.org/medenor) - Contact maintainer

---

**Ready to get started?** Run the setup wizard:

```bash
python scripts/setup/setup.py --quick
```

Welcome to PromptVault!
