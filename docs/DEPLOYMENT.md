# PromptVault Deployment Guide

This guide covers deploying PromptVault with database support using Docker, Docker Compose, or manual deployment.

## Table of Contents

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

## ⚠️ Pre-Deployment Checklist

**BEFORE upgrading PromptVault to a new version, ALWAYS:**

### 1. **Backup Your Database** (CRITICAL)

```bash
# PostgreSQL backup
docker-compose exec db pg_dump -U promptvault -d promptvault --verbose | gzip > \
  data/backups/promptvault-backup-$(date +%Y%m%d_%H%M%S).sql.gz

# SQLite backup (if applicable)
cp data/promptvault.db data/backups/promptvault-backup-$(date +%Y%m%d_%H%M%S).db
```

### 2. **Verify Backup Integrity**

```bash
# Test PostgreSQL backup restoration (on test database)
gunzip -c data/backups/promptvault-backup-*.sql.gz | psql -U promptvault -d test_promptvault

# Verify file size (should be reasonable, not empty)
ls -lh data/backups/promptvault-backup-*.sql.gz | tail -1
```

### 3. **Document Current State**

```bash
# Save version and configuration
docker-compose images > backup_images_$(date +%Y%m%d).txt
docker-compose config > backup_compose_$(date +%Y%m%d).yml
```

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

# Edit .env and set POSTGRES_PASSWORD
nano .env
```

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

- Python 3.11+
- PostgreSQL 15+ (for production) or SQLite (for development)
- Git

### 1. Install Dependencies

```bash
# Clone repository
git clone <repository-url>
cd PromptVault

# Create virtual environment
python3.11 -m venv venv
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

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### Docker Health Checks

The Dockerfile includes automatic health checks:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8003/api/health || exit 1
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
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `DATABASE_URL` with production credentials
- [ ] Set `ENVIRONMENT=production`
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

- [Migration Guide](MIGRATION_GUIDE.md) - Detailed migration from JSON to database
- [Performance Tuning](phase9_test_infrastructure.md#performance-tests) - Optimize database queries
- [Backup Strategy](phase8_backup_system_integration.md) - Configure automated backups
- [API Documentation](API.md) - Complete API reference
