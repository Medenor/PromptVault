# PromptVault Deployment Guide

This guide covers deploying PromptVault with database support using Docker, Docker Compose, or manual deployment.

## Table of Contents

- [🚀 Automated Setup (Recommended)](#-automated-setup-recommended)
  - [Setup Wizard Modes](#setup-wizard-modes)
  - [Quick Setup](#quick-setup)
  - [Advanced Setup](#advanced-setup)
  - [Component Setup](#component-setup)
  - [Non-Interactive Setup](#non-interactive-setup)
- [⚠️ Pre-Deployment Checklist](#-pre-deployment-checklist)
- [Quick Start with Docker Compose](#quick-start-with-docker-compose)
- [JWT Key Generation](#jwt-key-generation)
- [Docker Deployment](#docker-deployment)
- [Manual Deployment](#manual-deployment)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Migration from JSON](#migration-from-json)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Automated Setup (Recommended)

PromptVault includes a comprehensive setup wizard that automates the entire deployment process, from JWT key generation to application startup. This is the **fastest and most reliable** way to deploy PromptVault.

### Prerequisites

- Docker and Docker Compose installed
- Python 3.14+ installed
- Git installed

### Setup Wizard Modes

The setup wizard provides three modes to match your needs:

#### Quick Setup

Perfect for development and testing. Gets you running in under 5 minutes with sensible defaults:

```bash
pip install -e ".[setup]"   # installs the wizard's dependencies (click, rich, httpx)
python scripts/setup/setup.py --quick
```

**What it does:**

- ✅ Generates JWT keys (ES256) automatically
- ✅ Creates development configuration (SQLite database)
- ✅ Initializes database and runs migrations
- ✅ Prompts for admin user credentials
- ✅ Starts all services (web, database, Redis)
- ✅ Verifies health and displays access information

**Access:** http://localhost:8001

#### Advanced Setup

Full customization for production deployments:

```bash
python scripts/setup/setup.py --advanced
```

**What it configures:**

- JWT key generation (with custom paths)
- Environment configuration (development vs production profiles)
- Database selection (PostgreSQL or SQLite)
- Security settings (passwords, rate limiting, session management)
- Email configuration (SMTP for password reset)
- Admin user creation
- Full deployment with health checks

**Production features:**

- PostgreSQL with connection pooling
- Strict password policies
- Rate limiting enabled
- Full audit logging
- Email notifications

#### Component Setup

Run individual setup components independently:

```bash
# JWT keys only
python scripts/setup/setup.py --component jwt

# Environment configuration only
python scripts/setup/setup.py --component env

# Database setup only
python scripts/setup/setup.py --component database

# Deployment only
python scripts/setup/setup.py --component deploy
```

**Use cases:**

- Regenerate JWT keys
- Update environment configuration
- Re-run database migrations
- Redeploy without changing configuration

#### Non-Interactive Setup

For CI/CD pipelines and automation:

```bash
# Quick setup without prompts
python scripts/setup/setup.py --quick --non-interactive

# Advanced setup with config file
python scripts/setup/setup.py --config config.yaml --non-interactive
```

**Example config.yaml:**

```yaml
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

environment:
  ENVIRONMENT: production
  LOG_LEVEL: WARNING

admin:
  create: true
  username: admin
  email: admin@example.com

deploy:
  rebuild: false
  skip_backup: false
  wait_timeout: 120
```

### Individual Setup Scripts

You can also use the individual setup scripts directly:

**JWT Key Generation:**

```bash
# Generate keys with defaults
python scripts/setup/setup_jwt.py

# Validate existing keys
python scripts/setup/setup_jwt.py --validate-only

# Force regeneration with backup
python scripts/setup/setup_jwt.py --force --backup
```

**Environment Configuration:**

```bash
# Interactive configuration
python scripts/setup/setup_env.py

# Use development profile
python scripts/setup/setup_env.py --profile development

# Use production profile
python scripts/setup/setup_env.py --profile production

# Validate existing .env
python scripts/setup/setup_env.py --validate-only
```

**Database Setup:**

```bash
# SQLite setup
python scripts/setup/setup_database.py --type sqlite --non-interactive

# PostgreSQL setup
python scripts/setup/setup_database.py --type postgresql \
    --host localhost --port 5432 \
    --database promptvault --user promptvault

# Migrations only
python scripts/setup/setup_database.py --migrate-only

# With admin user creation
python scripts/setup/setup_database.py --type sqlite --create-admin
```

**Deployment:**

```bash
# Full deployment
python scripts/setup/deploy.py

# Dry run (test without executing)
python scripts/setup/deploy.py --dry-run

# Skip backup and migrations
python scripts/setup/deploy.py --skip-backup --skip-migrations

# Rollback to previous state
python scripts/setup/deploy.py --rollback
```

### Troubleshooting

If you encounter issues with the automated setup:

1. **Check Prerequisites:** Ensure Docker, Docker Compose, and Python 3.14+ are installed
2. **View Logs:** Check `.setup_state.json` for the last completed step
3. **Resume Setup:** The wizard can resume from the last checkpoint
4. **Component Retry:** Run individual components to isolate issues
5. **Manual Fallback:** Use the manual installation method below

For detailed troubleshooting, see **[Troubleshooting Guide](TROUBLESHOOTING.md)**.

---

## ⚠️ Pre-Deployment Checklist

**BEFORE upgrading PromptVault to a new version, ALWAYS:**

### 1. **Backup Your Database** (CRITICAL)

```bash
# PostgreSQL backup (-T: no pseudo-terminal, which would corrupt a piped dump)
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > \
  data/backups/promptvault-backup-$(date +%Y%m%d_%H%M%S).sql.gz

# SQLite backup (if applicable)
cp data/promptvault.db data/backups/promptvault-backup-$(date +%Y%m%d_%H%M%S).db
```

### 2. **Verify Backup Integrity**

```bash
# Restore the newest backup into a throwaway database inside the db container
# (no psql needed on the host, and the live database is not touched)
BACKUP=$(ls -t data/backups/promptvault-backup-*.sql.gz | head -1)
docker-compose exec -T db psql -U promptvault -d postgres -c "CREATE DATABASE test_promptvault;"
gunzip -c "$BACKUP" | docker-compose exec -T db psql -U promptvault -d test_promptvault -q
docker-compose exec -T db psql -U promptvault -d test_promptvault -tAc "SELECT COUNT(*) FROM prompts;"
docker-compose exec -T db psql -U promptvault -d postgres -c "DROP DATABASE test_promptvault;"

# Verify file size (should be reasonable, not empty)
ls -lh "$BACKUP"
```

The prompt count must match the live database. `psql` inside the `db` container connects over the local socket, which the `postgres` image trusts without a password. That is convenient here, but it also means a `psql` test run inside the `db` container can never prove that a password is correct (see [Changing the Database Password](#changing-the-database-password)).

### 3. **Document Current State and Tag the Running Image**

```bash
# Save the running image's tag so a rollback does not need a rebuild.
# Use the container's image ID: the `:latest` tag may already point at a newer build.
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update

# Save the image list and the compose configuration
docker-compose images > backup_images_$(date +%Y%m%d).txt
docker-compose config > backup_compose_$(date +%Y%m%d).yml
chmod 600 backup_compose_*.yml
```

`docker-compose config` prints the resolved configuration, **including `POSTGRES_PASSWORD` in clear text**. Keep that file private (`chmod 600`), never commit it, and delete it once the update is verified.

### 4. **Test Migration Path**

```bash
# Never deploy directly to production first
# Always test on staging/dev environment first
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml exec web alembic upgrade head
```

### 5. **Review Release Notes**

Check `CHANGELOG.md` for breaking changes or migration instructions specific to your target version.

### Disaster Recovery - Restore from Backup

If something goes wrong after upgrade:

```bash
# Stop application
docker-compose stop web

# Restore database from backup
docker-compose exec -T db psql -U promptvault postgres -c "DROP DATABASE promptvault;"
docker-compose exec -T db psql -U promptvault postgres -c "CREATE DATABASE promptvault;"
gunzip -c data/backups/promptvault-backup-YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T db psql -U promptvault -d promptvault

# Restart application
docker-compose up -d web

# Verify restoration
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

---

## 📦 Updating PromptVault

### Pre-Update Requirements

**BEFORE updating to a new version:**

1. ✅ Read `CHANGELOG.md` for breaking changes or migration notes
2. ✅ Backup your database (see Pre-Deployment Checklist above)
3. ✅ Test on staging environment first (if available)
4. ✅ Plan for potential downtime (usually < 5 minutes)

### Update with Docker Compose (Recommended)

This is the safest approach with proper database migration handling. The build step rebuilds both the `web` and `docs` images, and step 6 recreates both containers, so the documentation portal (default: <http://localhost:7876>) stays in step with the application.

If your production settings live in a separate `.env.production` (recommended, see [Production Environment File](#production-environment-file)), add `--env-file .env.production` to **every** `docker-compose` command below. Without it, Compose reads `.env` and your development values (such as `ENVIRONMENT=development` or `DISABLE_RATE_LIMITING=true`) replace the production ones.

```bash
# 1. Pull latest code from main branch
git checkout main
git pull origin main

# 2. Create database backup (CRITICAL!) and tag the running image for rollback
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > \
  data/backups/promptvault-backup-$(date +%Y%m%d_%H%M%S).sql.gz
  
# Tag by the container's image ID, not `:latest`, which may already be a newer build
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update

# 3. Build new Docker image with latest code
docker-compose build --no-cache

# 4. Stop web service (keep db/redis running)
docker-compose stop web
docker-compose rm web

# 5. Ensure database is fully ready
docker-compose up -d db redis
sleep 15  # CRITICAL: Give database time to initialize

# 6. Start the updated web and docs services
# The docs portal is compiled into its image, so it only shows the new
# release notes once the docs container is recreated from the rebuilt image.
docker-compose up -d web docs

# 7. Run pending database migrations
# NOTE: This MUST happen after starting the web service
docker-compose exec web alembic upgrade head

# 8. Verify update was successful
docker-compose logs web | head -50
curl http://localhost:8001/api/health
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

### Important: Database Migrations

**Why is the sleep command critical?**

When you restart the database container, it needs time to:

- Initialize the PostgreSQL cluster
- Load all data from persistent volumes
- Become fully responsive to connections

If migrations run too soon, they may:

- ❌ Appear to succeed but silently fail
- ❌ Not actually apply, leaving schema out of sync
- ❌ Cause API errors like "column does not exist"

**Solution:** Always include `sleep 15` between starting database and running migrations.

**Verify migrations ran:**

```bash
# Check which migrations were applied
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 5;"

# Expected: Should show latest migration versions (e.g., b7a1c2d3e4f5, c8d9e0f1a2b3)
```

### One-Command Update (Quick)

For experienced users, here's a single command that handles everything:

```bash
git checkout main && git pull && \
docker-compose build --no-cache && \
docker-compose stop web && docker-compose rm web && \
docker-compose up -d && sleep 15 && \
docker-compose exec web alembic upgrade head && \
docker-compose logs web --tail=20
```

### Manual Deployment Update

If running without Docker Compose:

```bash
# 1. Pull latest code
git pull origin main

# 2. Backup database
pg_dump -U promptvault -d promptvault | gzip > backup-$(date +%Y%m%d_%H%M%S).sql.gz

# 3. Install dependencies (in case requirements changed)
source venv/bin/activate
pip install -e . --upgrade

# 4. Run migrations
alembic upgrade head

# 5. Restart application
systemctl restart promptvault
# or manually:
# pkill -f "python run_web.py"
# python run_web.py &
```

### Verify Update Success

After update completes, verify:

```bash
# 1. Health endpoint returns 200
curl -i http://localhost:8001/api/health

# 2. Expected response (the timestamp differs)
{
  "status": "healthy",
  "timestamp": "2026-11-24T18:40:10.185871",
  "service": "PromptVault API"
}
# The endpoint does not report the version or the database state. Check the
# version of the running image instead:
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"

# 2b. Check the settings the container actually runs with
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='

# 3. Check logs for errors
docker-compose logs web | grep -i error

# 4. Verify database is accessible
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"

# 5. Test basic functionality in UI
# Visit: http://localhost:8001
# Create/read/update a prompt to ensure everything works

# 6. Check that the documentation portal is up to date
# Visit: http://localhost:7876/release-notes/
# The newest release must be listed first. If it is missing, the docs
# container still runs the old image: run `docker-compose up -d docs`.
```

### Troubleshooting Update Issues

#### Migration Failed Silently

**Problem:** First `alembic upgrade head` showed no output, second one applied migrations

**Cause:** Database wasn't fully initialized when migrations ran

**Solution:**

```bash
# Stop everything
docker-compose down

# Start only database, wait longer
docker-compose up -d db
sleep 30  # Longer wait

# Run migrations
docker-compose exec web alembic upgrade head

# Start web and docs services
docker-compose up -d web docs
```

#### "Column does not exist" Errors

**Problem:** API returns errors like `column categories.updated_at does not exist`

**Cause:** Migrations weren't applied despite appearing to succeed

**Solution:**

```bash
# Check which migrations have been applied
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT version_num FROM alembic_version ORDER BY version_num DESC;"

# If migrations are missing, run again
docker-compose exec web alembic upgrade head

# If still failing, check for migration locks
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT * FROM alembic_version_table WHERE locked = true;"

# Force reset if stuck (use with caution!)
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "UPDATE alembic_version_table SET locked = false WHERE locked = true;"
docker-compose exec web alembic upgrade head
```

#### Rollback to Previous Version

If the update causes critical issues, go back to the image you tagged before the update (`promptvault-web:pre-update`, see the Pre-Deployment Checklist). Do **not** roll back by checking out the old commit and rebuilding with `--no-cache`: the image installs dependencies with `pip install -e .`, which resolves them again and ignores `uv.lock`, so the result can differ from the image you ran before. Some releases cannot be rebuilt at all: any image built from the 1.16.0 source crashes on PostgreSQL with `No module named 'psycopg'` (fixed in 1.17.0).

```bash
# 1. Put the previous web image back and recreate the container without rebuilding
docker tag promptvault-web:pre-update promptvault-web:latest
docker-compose up -d --no-build web

# 2. Verify
docker-compose logs web | tail -20
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

Restore the database only if the update ran database migrations (check the release's section in `CHANGELOG.md`; many releases have none). Restoring replaces **all** data written since the backup:

```bash
docker-compose stop web
docker-compose exec -T db psql -U promptvault postgres -c "DROP DATABASE promptvault;"
docker-compose exec -T db psql -U promptvault postgres -c "CREATE DATABASE promptvault;"
gunzip -c data/backups/promptvault-backup-YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose exec -T db psql -U promptvault -d promptvault
docker-compose up -d --no-build web
```

If you have no tagged image, check out the previous release tag (`git checkout vX.Y.Z`, not a commit hash) and rebuild with `docker-compose build`, then check the result as in step 2. Docker's layer cache may reuse the old dependencies, but nothing guarantees it, so confirm the version and that the app starts before you rely on it.

---

## ⚠️ Permissions & Non-Root Containers (PostgreSQL, Redis, Web)

Recent versions of PromptVault run all services as **non-root users** inside their containers:

- `web` → runs as `appuser` (UID 1000)
- `db` → runs as `postgres` (UID 70)
- `redis` → runs as `redis` (UID 999)

This improves security, but if you are **upgrading from an older deployment** where containers previously ran as `root`, your existing Docker volumes may contain files owned by root.  
This can lead to errors such as:

```text
permission denied
attempt to write a readonly database
could not open file ...: Permission denied
```

### 1. Check your volume names

List existing volumes:

```bash
docker volume ls
```

Typical PromptVault-related volume names:

- `postgres_data` or `promptvault_postgres_data`
- `redis_data` or `promptvault_redis_data`

### 2. Fix PostgreSQL volume permissions (UID 70)

```bash
docker run --rm -it \
  -v postgres_data:/var/lib/postgresql/data \
  --user 0 alpine sh -c 'chown -R 70:70 /var/lib/postgresql/data'
```

If your volume is prefixed (e.g., `promptvault_postgres_data`):

```bash
docker run --rm -it \
  -v promptvault_postgres_data:/var/lib/postgresql/data \
  --user 0 alpine sh -c 'chown -R 70:70 /var/lib/postgresql/data'
```

### 3. Fix Redis volume permissions (UID 999)

```bash
docker run --rm -it \
  -v redis_data:/data \
  --user 0 alpine sh -c 'chown -R 999:999 /data'
```

Or with a prefixed volume:

```bash
docker run --rm -it \
  -v promptvault_redis_data:/data \
  --user 0 alpine sh -c 'chown -R 999:999 /data'
```

### 4. Fix bind-mounted ./data directory for the web container

If you mount a local directory into `/app/data`, it must be writable by the non-root user in the container:

```bash
# Match your local user (Linux or macOS)
chown -R $(id -u):$(id -g) ./data

# Or a more permissive alternative (dev only)
chmod -R 770 ./data
```

### 5. Restart services

After fixing permissions, restart the stack:

```bash
docker-compose down
docker-compose up -d
```

Fresh installations with new volumes do not require this step — everything will be created with correct ownership automatically.

---

## Quick Start with Docker Compose

The fastest way to get PromptVault running with PostgreSQL:

### Important: Generate JWT Keys First

Before starting, you MUST generate JWT keys locally. See [JWT Key Generation](#jwt-key-generation) section for detailed instructions.

```bash
# Quick key generation
mkdir -p secrets/jwt
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem
```

### 1. Clone and Configure

```bash
git clone <repository-url>
cd PromptVault

# Create environment file
cp .env.example .env

# Add a strong database password (.env.example has no POSTGRES_PASSWORD line, and
# Docker Compose silently falls back to "changeme" when it is missing)
echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)" >> .env
nano .env
```

`.env.example` is a **development** template (`ENVIRONMENT=development`). Docker Compose passes some of its values to the containers, so for a production server create a separate `.env.production` instead, see [Production Environment File](#production-environment-file).

### 2. Start Services

```bash
# Start PostgreSQL and PromptVault
docker-compose up -d

# View logs
docker-compose logs -f web

# Check status
docker-compose ps
```

### 3. Run Migrations

```bash
# Run database migrations
docker-compose exec web alembic upgrade head

# (Optional) Migrate from JSON
docker-compose exec web python scripts/migrate_json_to_db.py
```

### 4. Access Application

- **Web UI**: <http://localhost:8001>
- **API**: <http://localhost:8001/api>
- **Health Check**: <http://localhost:8001/api/health>

### 5. Stop Services

```bash
# Stop services
docker-compose down

# Stop and remove data
docker-compose down -v
```

---

## JWT Key Generation

### Security Warning ⚠️

**NEVER commit JWT keys to Git!** Keys must be:

- ✅ Generated locally on each deployment
- ✅ Stored in `secrets/jwt/` (ignored by .gitignore)
- ✅ Backed up in a secure location
- ❌ NEVER committed to version control
- ❌ NEVER shared in email or chat
- ❌ NEVER exposed in logs or error messages

### Generate JWT Keys

Generate ES256 (ECDSA P-256) keys for JWT signing:

```bash
# Generate private key
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem

# Generate public key
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# Verify keys
ls -la secrets/jwt/
```

### Docker Compose Setup

If using Docker Compose, mount the keys as a volume:

```yaml
# docker-compose.yml
services:
  web:
    volumes:
      - ./secrets/jwt:/app/secrets/jwt:ro # Read-only mount
```

### Manual Setup

For manual deployment:

```bash
# 1. Generate keys
mkdir -p secrets/jwt
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# 2. Set permissions (secure)
chmod 600 secrets/jwt/private_key.pem
chmod 644 secrets/jwt/public_key.pem

# 3. Configure environment
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/secrets/jwt/private_key.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/secrets/jwt/public_key.pem" >> .env

# 4. Verify
cat .env | grep JWT
```

### Rotate Keys (Emergency)

If keys are compromised:

```bash
# 1. Generate new keys
rm secrets/jwt/*.pem
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# 2. Restart application
docker-compose restart web
# or
sudo systemctl restart promptvault

# 3. Force logout all users (requires admin token)
curl -X POST http://localhost:8001/api/admin/sessions -H "Authorization: Bearer <admin_token>"

# 4. Backup old keys (safe location)
tar czf /secure/backup/jwt_keys_$(date +%Y%m%d_%H%M%S).tar.gz secrets/jwt/
```

---

## TOTP 2FA Encryption Key

Two-factor authentication (TOTP) secrets are encrypted at rest with AES-256-GCM,
using a key derived from `TOTP_ENCRYPTION_KEY`. This is a server-held secret
(not a user passphrase) — required if any user enables 2FA.

### Security Warning ⚠️

**NEVER commit `TOTP_ENCRYPTION_KEY` to Git!** Treat it like `JWT_PRIVATE_KEY_PATH`:

- ✅ Generated locally on each deployment
- ✅ Stored only in `.env` / your secrets manager
- ✅ Backed up in a secure location
- ❌ NEVER committed to version control
- ❌ NEVER exposed in logs or error messages
- ❌ NEVER rotated without a migration plan — rotating this key invalidates all existing TOTP enrollments (see below)

### Generate the Key

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
echo "TOTP_ENCRYPTION_KEY=<generated-value>" >> .env
```

### Rotate Key (Emergency)

Rotating `TOTP_ENCRYPTION_KEY` makes existing `totp_credentials` rows
undecryptable. There is no in-place re-encryption path in v1 — rotation
requires disabling 2FA for all currently-enrolled users (deleting their
`totp_credentials`/`totp_recovery_codes` rows) before the key changes, then
asking them to re-enroll.

---

## Docker Deployment

### Build Image

```bash
# Build the Docker image
docker build -t promptvault:latest .

# View image
docker images | grep promptvault
```

### Run with SQLite (Development)

```bash
# Run with SQLite database
docker run -d \
  --name promptvault \
  -p 8001:8000 \
  -v $(pwd)/data:/app/data \
  -e DATABASE_URL=sqlite:///./data/promptvault.db \
  promptvault:latest

# View logs
docker logs -f promptvault

# Run migrations
docker exec promptvault alembic upgrade head
```

### Run with PostgreSQL (Production)

```bash
# 1. Start PostgreSQL
docker run -d \
  --name promptvault-db \
  -e POSTGRES_DB=promptvault \
  -e POSTGRES_USER=promptvault \
  -e POSTGRES_PASSWORD=secure_password \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine

# 2. Start PromptVault
docker run -d \
  --name promptvault \
  --link promptvault-db:db \
  -p 8001:8000 \
  -v $(pwd)/data:/app/data \
  -e DATABASE_URL=postgresql://promptvault:secure_password@db:5432/promptvault \
  promptvault:latest

# 3. Run migrations
docker exec promptvault alembic upgrade head
```

---

## Manual Deployment

### Prerequisites

- Python 3.14+
- PostgreSQL 15+ (for production) or SQLite (for development)
- Git

### 1. Install Dependencies

```bash
# Clone repository
git clone <repository-url>
cd PromptVault

# Create virtual environment
python3.14 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

**For PostgreSQL:**

```env
DATABASE_URL=postgresql://username:password@localhost:5432/promptvault
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
ENVIRONMENT=production
LOG_LEVEL=INFO
```

**For SQLite:**

```env
DATABASE_URL=sqlite:///./data/promptvault.db
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 3. Setup Database

**PostgreSQL:**

```bash
# Create database
createdb -U postgres promptvault

# Create user
psql -U postgres -c "CREATE USER promptvault WITH PASSWORD 'secure_password';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE promptvault TO promptvault;"
```

**SQLite:**

```bash
# Create data directory
mkdir -p data
```

### 4. Run Migrations

```bash
# Initialize Alembic (if not already done)
alembic upgrade head

# Verify migration
python -c "from src.db.session import engine; from src.db.base import Base; print(Base.metadata.tables.keys())"
```

### 5. Migrate from JSON (Optional)

If you have existing JSON data:

```bash
# Backup existing data
cp data/prompts.json data/prompts.json.backup

# Run migration script
python scripts/migrate_json_to_db.py

# Verify migration
python scripts/test_db_operations.py
```

### 6. Start Application

```bash
# Development mode (with auto-reload)
uvicorn src.web.app:app --host 0.0.0.0 --port 8003 --reload

# Production mode
uvicorn src.web.app:app --host 0.0.0.0 --port 8003 --workers 4
```

---

## Environment Configuration

### Required Variables

| Variable       | Description                | Default                           |
| -------------- | -------------------------- | --------------------------------- |
| `DATABASE_URL` | Database connection string | `sqlite:///./data/promptvault.db` |

### Optional Variables

| Variable                | Description                                  | Default       |
| ----------------------- | -------------------------------------------- | ------------- |
| `DB_POOL_SIZE`          | Connection pool size (PostgreSQL only)       | `20`          |
| `DB_POOL_TIMEOUT`       | Pool timeout in seconds                      | `30`          |
| `DB_POOL_RECYCLE`       | Connection recycle time in seconds           | `3600`        |
| `DB_ECHO`               | Enable SQL query logging                     | `false`       |
| `ENVIRONMENT`           | Environment (development/testing/production) | `development` |
| `LOG_LEVEL`             | Logging level                                | `INFO`        |
| `AUDIT_LOG_LEVEL`       | Audit log level                              | `INFO`        |
| `DATA_DIR`              | Data directory path                          | `./data`      |
| `DISABLE_RATE_LIMITING` | Disable rate limiting (dev/test only)        | `false`       |

### Skill Package Limits

Skills are imported from `.zip` archives. The archive is read in memory and its entries are never extracted to disk; file contents are stored in the database, so they are part of every backup. These limits protect the server from oversized or malicious archives:

| Variable                      | Description                                               | Default            |
| ----------------------------- | --------------------------------------------------------- | ------------------ |
| `SKILL_MAX_UPLOAD_BYTES`      | Largest accepted `.zip` upload                            | `10485760` (10 MB) |
| `SKILL_MAX_TOTAL_BYTES`       | Largest total unpacked size of one skill                  | `52428800` (50 MB) |
| `SKILL_MAX_FILES`             | Largest number of files in one skill                      | `500`              |
| `SKILL_MAX_DEPTH`             | Deepest folder nesting below the skill root               | `10`               |
| `SKILL_MAX_FILE_BYTES`        | Largest single unpacked file                              | `10485760` (10 MB) |
| `SKILL_MAX_COMPRESSION_RATIO` | Highest compression ratio accepted for an entry over 1 MB | `100`              |
| `SKILL_TEXT_PREVIEW_BYTES`    | Largest text excerpt returned by the file viewer          | `1048576` (1 MB)   |
| `SKILL_MAX_SKILL_MD_BYTES`    | Largest accepted `SKILL.md`                               | `1048576` (1 MB)   |

Raising the limits makes `pg_dump` and restore slower, because file contents are stored as `BYTEA`. If you serve PromptVault behind a reverse proxy, allow request bodies of at least `SKILL_MAX_UPLOAD_BYTES` plus 64 KB on `/api/skills/*`.

### Development-Only Variables

#### `DISABLE_RATE_LIMITING`

Disables rate limiting for development and testing. **Never enable in production.**

**Usage:**

```bash
# Enable (allows unlimited login/register attempts)
DISABLE_RATE_LIMITING=true PORT=8003 python run_web.py

# With Docker Compose
export DISABLE_RATE_LIMITING=true
docker-compose up -d web

# Disable (default - rate limiting active)
DISABLE_RATE_LIMITING=false PORT=8003 python run_web.py
```

**What It Does:**

- All rate limit decorators remain in place but don't restrict requests
- Default limit set to 10,000,000 requests per minute (effectively unlimited)
- Rate limit headers not added to responses
- Warning logged: "⚠️ RATE LIMITING IS DISABLED"

**When to Use:**

- Rapid testing of authentication flows
- UI testing with multiple login attempts
- API testing without throttling delays
- Bug investigation and debugging

**Check production:** Docker Compose passes this variable from `.env` to the container, so a development `.env` that sets it to `true` also disables rate limiting on a server started from the same directory. Confirm it is off:

```bash
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep DISABLE_RATE_LIMITING
# Expected: DISABLE_RATE_LIMITING=false (or no output)
```

### Production Environment File

Docker Compose reads the `.env` next to `docker-compose.yml` and substitutes it into the compose file. That is the same file you use for local development, so development values reach a production stack started from the same directory. Compose only takes these variables from it: `ENVIRONMENT`, `LOG_LEVEL`, `POSTGRES_PASSWORD`, `DISABLE_RATE_LIMITING`, `JWT_ACCESS_TOKEN_EXPIRE_SECONDS`, `JWT_REFRESH_TOKEN_EXPIRE_SECONDS`, `DOCS_APP_URL` and `VITE_DOCS_PORTAL_URL`. The `.env` file itself is not copied into the image (`.dockerignore` excludes it).

Keep a separate file for production and pass it on every command:

```bash
# .env.production must be gitignored before it holds secrets
echo '.env.production' >> .gitignore
cp .env .env.production

sed -i.bak \
  -e 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' \
  -e 's/^LOG_LEVEL=.*/LOG_LEVEL=WARNING/' \
  -e 's/^DISABLE_RATE_LIMITING=.*/DISABLE_RATE_LIMITING=false/' \
  .env.production && rm .env.production.bak
grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)=' .env.production

# Preview what Compose will use, then start
docker-compose --env-file .env.production config | grep -E "ENVIRONMENT|LOG_LEVEL|DISABLE_RATE|POSTGRES_PASSWORD"
docker-compose --env-file .env.production up -d
```

Pass `--env-file .env.production` on **every** later `docker-compose` command (`up`, `build`, `ps`, `exec`), otherwise Compose goes back to `.env`. To avoid repeating it, run `export COMPOSE_ENV_FILES=.env.production` once in each terminal window you use for production (Docker Compose 2.24 or later): every `docker-compose` command in that window then uses the file. `docker-compose config` prints `POSTGRES_PASSWORD` in clear text, so do not paste its output anywhere.

`ENVIRONMENT=production` can enforce stricter behavior than development (for example requirements around HTTPS and cookies). After switching, read `docker-compose logs --tail 30 web` and fix anything it reports.

### Changing the Database Password

If `POSTGRES_PASSWORD` was never set, Docker Compose uses the default `changeme` (`${POSTGRES_PASSWORD:-changeme}`). The database container publishes no host port, so it is only reachable from the Docker network, but you should still replace the default.

Postgres reads `POSTGRES_PASSWORD` only when it first creates the data volume. Changing the variable alone does **not** change the password of an existing database, so change it inside Postgres first:

```bash
# 1. Generate a password without URL-special characters (it ends up in a connection URL)
NEWPW=$(openssl rand -hex 24)

# 2. Change it in the database (the local socket inside the container needs no password)
docker exec promptvault-db psql -U promptvault -d promptvault -c "ALTER USER promptvault PASSWORD '$NEWPW'"

# 3. Store it for Compose and recreate the containers straight away
echo "POSTGRES_PASSWORD=$NEWPW" >> .env.production
docker-compose --env-file .env.production up -d
```

Between steps 2 and 3 the running web container still holds the old password, so new database connections fail for a few seconds. Do it at a quiet moment, and take a fresh backup afterwards.

**Verify from another container.** Do not test from inside the `db` container: the `postgres` image trusts connections from `127.0.0.1` and the local socket, so such a test accepts any password and proves nothing. Connect from the web container, which goes through the network and `scram-sha-256`:

```bash
# The old password must be rejected
docker exec promptvault-web python -c "
import psycopg
try:
    psycopg.connect('postgresql://promptvault:changeme@db:5432/promptvault', connect_timeout=5).close(); print('ACCEPTED (old password still works)')
except Exception as e: print('REJECTED:', str(e).strip().splitlines()[0])"

# The password the web container uses now must work
docker exec promptvault-web python -c "
import os, psycopg
url = os.environ['DATABASE_URL'].replace('postgresql+psycopg2://','postgresql://').replace('postgresql+psycopg://','postgresql://')
with psycopg.connect(url, connect_timeout=5) as c: print('OK, select 1 ->', c.execute('select 1').fetchone()[0], '| password is changeme:', ':changeme@' in url)"
```

Expected: `REJECTED: ... password authentication failed`, then `OK, select 1 -> 1 | password is changeme: False`. Keep `.env.production` somewhere safe (a password manager): it holds the only copy of the password outside the database.

### Database URL Examples

**SQLite:**

```env
DATABASE_URL=sqlite:///./data/promptvault.db
DATABASE_URL=sqlite:////absolute/path/to/database.db
```

**PostgreSQL:**

```env
# Local
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Docker
DATABASE_URL=postgresql://promptvault:password@db:5432/promptvault

# Remote
DATABASE_URL=postgresql://user:password@remote-host:5432/dbname
```

A plain `postgresql://` URL uses the psycopg v3 driver (installed with PromptVault since 1.17.0). The older `postgresql+psycopg2://` form is still accepted and is mapped to psycopg v3, so existing `.env` files need no change. `pg_dump` and `psql` always receive a plain `postgresql://` URI, because they reject the `+driver` suffix.

With Docker Compose you do not set `DATABASE_URL` yourself: the compose file builds it from `POSTGRES_PASSWORD`.

---

## Database Setup

### PostgreSQL Production Setup

#### 1. Install PostgreSQL

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

**macOS:**

```bash
brew install postgresql@15
brew services start postgresql@15
```

#### 2. Create Database and User

```bash
# Connect as postgres user
sudo -u postgres psql

# Run SQL commands
CREATE DATABASE promptvault;
CREATE USER promptvault WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE promptvault TO promptvault;
\q
```

#### 3. Configure PostgreSQL

Edit `/etc/postgresql/15/main/postgresql.conf`:

```ini
# Connection Settings
max_connections = 100
shared_buffers = 256MB

# Logging
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_statement = 'mod'
```

Edit `/etc/postgresql/15/main/pg_hba.conf`:

```
# Allow local connections
local   all             all                                     peer
host    all             all             127.0.0.1/32            md5
host    all             all             ::1/128                 md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### SQLite Setup

SQLite requires no additional setup. The database file will be created automatically when you run migrations.

```bash
# Create data directory
mkdir -p data

# Run migrations
alembic upgrade head
```

---

## Migration from JSON

If you have existing JSON data in `data/prompts.json`, follow these steps:

### 1. Backup Existing Data

```bash
# Backup JSON file
cp data/prompts.json data/prompts.json.backup

# Backup database (if exists)
python scripts/backup_db.py
```

### 2. Run Migration Script

```bash
# Dry run (verify without changes)
python scripts/migrate_json_to_db.py --dry-run

# Actual migration
python scripts/migrate_json_to_db.py

# Verbose output
python scripts/migrate_json_to_db.py --verbose
```

### 3. Verify Migration

```bash
# Test database operations
python scripts/test_db_operations.py

# Check prompt count
python -c "from src.services.prompt_data_service_db import PromptDataService; svc = PromptDataService(); print(f'Total prompts: {len(svc.load_prompts())}')"
```

### 4. Switch Application to Database

Update your application configuration to use the database-backed service:

```python
# Before (JSON)
from src.services.prompt_data_service import PromptDataService

# After (Database)
from src.services.prompt_data_service_db import PromptDataService
```

---

## Health Checks

### Application Health Endpoint

PromptVault includes a health check endpoint at `/api/health`:

```bash
# Check health
curl http://localhost:8003/api/health

# Expected response (the timestamp differs)
{
  "status": "healthy",
  "timestamp": "2026-11-24T18:40:10.185871",
  "service": "PromptVault API"
}
```

The endpoint reports only that the API answers. It does not include the version or the database state; see "Verify Update Success" for how to check those.

### Docker Health Checks

The Dockerfile includes automatic health checks (the container listens on port 8001):

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1
```

Check container health:

```bash
# Docker
docker ps
docker inspect --format='{{.State.Health.Status}}' promptvault

# Docker Compose
docker-compose ps
```

### Database Health Checks

**PostgreSQL:**

```bash
# Docker
docker exec promptvault-db pg_isready -U promptvault

# Manual
psql -U promptvault -d promptvault -c "SELECT 1;"
```

**SQLite:**

```bash
# Check database file exists and is readable
sqlite3 data/promptvault.db "SELECT COUNT(*) FROM prompts;"
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Problem:** `could not connect to server: Connection refused`

**Solutions:**

- Verify PostgreSQL is running: `systemctl status postgresql`
- Check DATABASE_URL is correct
- Verify network connectivity: `pg_isready -h localhost -p 5432`
- Check firewall rules

#### 2. Migration Errors

**Problem:** `alembic.util.exc.CommandError: Can't locate revision identified by 'xxxx'`

**Solutions:**

```bash
# Check current version
alembic current

# Stamp to specific version
alembic stamp head

# Re-run migrations
alembic upgrade head
```

#### 3. Permission Errors

**Problem:** `permission denied for table prompts`

**Solutions:**

```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO promptvault;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO promptvault;
```

#### 4. Port Already in Use

**Problem:** `Error starting userland proxy: listen tcp4 0.0.0.0:8001: bind: address already in use`

**Solutions:**

```bash
# Find process using port
lsof -i :8001
netstat -tuln | grep 8001

# Kill process
kill -9 <PID>

# Or use different port in docker-compose.yml
ports:
  - "8002:8000"
```

#### 5. Docker Volume Permissions

**Problem:** `permission denied` errors in Docker container

**Solutions:**

```bash
# Fix data directory permissions
sudo chown -R 1000:1000 ./data

# Or run with user flag
docker run --user $(id -u):$(id -g) ...
```

### Logs and Debugging

**Docker Compose:**

```bash
# View all logs
docker-compose logs

# Follow specific service
docker-compose logs -f web

# Last 100 lines
docker-compose logs --tail=100
```

**Docker:**

```bash
# View container logs
docker logs promptvault

# Follow logs
docker logs -f promptvault

# With timestamps
docker logs -t promptvault
```

**Application Logs:**

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DB_ECHO=true

# Run application
uvicorn src.web.app:app --reload
```

### Performance Issues

#### Database Performance

**Enable query logging:**

```env
DB_ECHO=true
LOG_LEVEL=DEBUG
```

**Analyze slow queries:**

```sql
-- PostgreSQL
EXPLAIN ANALYZE SELECT * FROM prompts WHERE title LIKE '%search%';

-- Enable slow query log
ALTER DATABASE promptvault SET log_min_duration_statement = 1000;
```

**Optimize connection pool:**

```env
DB_POOL_SIZE=50
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=1800
```

#### Application Performance

**Use production server:**

```bash
# Multiple workers
uvicorn src.web.app:app --workers 4 --host 0.0.0.0 --port 8003

# With Gunicorn
gunicorn src.web.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8003
```

---

## Production Checklist

Before deploying to production:

- [ ] ⚠️ **JWT keys generated locally and stored in `secrets/jwt/`** (NEVER in Git!)
- [ ] Use a separate `.env.production` (gitignored) and pass `--env-file .env.production` on every `docker-compose` command, see [Production Environment File](#production-environment-file)
- [ ] Set a strong `POSTGRES_PASSWORD` (Compose silently uses `changeme` when it is unset), see [Changing the Database Password](#changing-the-database-password)
- [ ] Configure `DATABASE_URL` with production credentials (outside Docker Compose)
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DISABLE_RATE_LIMITING=false` (or leave it unset), and confirm it on the running container
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Enable database backups
- [ ] Configure firewall rules
- [ ] Set up SSL/TLS for database connections
- [ ] Configure reverse proxy (nginx/Caddy)
- [ ] Set up monitoring and alerting
- [ ] Test health check endpoints
- [ ] Review and optimize `DB_POOL_SIZE`
- [ ] Enable audit logging
- [ ] Configure log rotation
- [ ] Test backup and restore procedures
- [ ] Document disaster recovery plan

---

## Next Steps

- [Database Specification](SPECS/SPEC_DATABASE.md) - Database schema and design reference
- [Performance Tuning](phase9_test_infrastructure.md#performance-tests) - Optimize database queries
- [Backup Strategy](phase8_backup_system_integration.md) - Configure automated backups
- [API Documentation](API.md) - Complete API reference
