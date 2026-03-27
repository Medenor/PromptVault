# PromptVault Troubleshooting Guide

This guide provides solutions to common issues encountered during PromptVault setup, deployment, and operation.

## Table of Contents

- [Common Setup Issues](#common-setup-issues)
- [Docker Issues](#docker-issues)
- [Port Conflicts](#port-conflicts)
- [Database Issues](#database-issues)
- [JWT Key Issues](#jwt-key-issues)
- [Configuration Issues](#configuration-issues)
- [Container Issues](#container-issues)
- [Migration Issues](#migration-issues)
- [Permission Errors](#permission-errors)
- [Error Code Reference](#error-code-reference)
- [Debug Commands](#debug-commands)
- [Log Locations](#log-locations)
- [Getting Help](#getting-help)

---

## Common Setup Issues

### Setup Script Not Found

**Symptom:** `python: can't open file 'scripts/setup/setup.py': [Errno 2] No such file or directory`

**Causes:**
- Running script from wrong directory
- Script file missing or deleted

**Solutions:**

```bash
# Verify you're in the PromptVault root directory
pwd
# Should output: /path/to/PromptVault

# Check if setup script exists
ls -la scripts/setup/setup.py

# If missing, re-clone the repository
git pull origin main

# Run setup from correct directory
cd /path/to/PromptVault
python scripts/setup/setup.py
```

### Python Not Found

**Symptom:** `command not found: python` or `python: command not found`

**Causes:**
- Python not installed
- Python not in PATH
- Wrong Python version

**Solutions:**

```bash
# Check Python installation
python3 --version
python --version

# Install Python (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3.14 python3-pip

# Install Python (macOS with Homebrew)
brew install python@3.14

# Create alias if needed
alias python=python3

# Or use python3 explicitly
python3 scripts/setup/setup.py
```

### Module Not Found Errors

**Symptom:** `ModuleNotFoundError: No module named 'rich'` or `No module named 'click'`

**Causes:**
- Required dependencies not installed
- Wrong Python environment
- Virtual environment not activated

**Solutions:**

```bash
# Install required dependencies
pip install rich click PyYAML

# Or install all project dependencies
pip install -e .

# If using virtual environment, activate it first
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Then install dependencies
pip install -e .
```

### Permission Denied Errors

**Symptom:** `PermissionError: [Errno 13] Permission denied`

**Causes:**
- Insufficient permissions to create directories
- File ownership issues
- Protected system directories

**Solutions:**

```bash
# Check file permissions
ls -la /path/to/file

# Fix directory permissions
chmod 755 /path/to/directory

# Fix file permissions
chmod 644 /path/to/file

# Change ownership if needed
chown -R $USER:$USER /path/to/directory

# Run setup script with appropriate permissions
# (avoid sudo if possible, run as your user)
python scripts/setup/setup.py
```

---

## Docker Issues

### Docker Not Installed

**Symptom:** `Docker is not installed or not in PATH` or `E001` error code

**Causes:**
- Docker not installed on system
- Docker not in system PATH

**Solutions:**

```bash
# Check if Docker is installed
docker --version

# Install Docker (Ubuntu/Debian)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect

# Install Docker (macOS)
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Install Docker (Windows)
# Download and install Docker Desktop from:
# https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker run hello-world
```

### Docker Daemon Not Running

**Symptom:** `Cannot connect to the Docker daemon` or `E002` error code

**Causes:**
- Docker service stopped
- Docker Desktop not started
- Permission issues with Docker socket

**Solutions:**

```bash
# Check Docker daemon status (Linux)
sudo systemctl status docker

# Start Docker daemon (Linux)
sudo systemctl start docker
sudo systemctl enable docker  # Enable auto-start

# Check Docker daemon (macOS/Windows)
# Open Docker Desktop application

# Verify Docker is running
docker info

# Check Docker socket permissions (Linux)
ls -la /var/run/docker.sock
sudo chmod 666 /var/run/docker.sock  # Temporary fix
# Better: add user to docker group
sudo usermod -aG docker $USER
```

### Docker Compose Not Found

**Symptom:** `Docker Compose is not installed` or command not recognized

**Causes:**
- Docker Compose plugin not installed
- Standalone docker-compose not installed
- Wrong command syntax

**Solutions:**

```bash
# Try Docker Compose V2 (plugin)
docker compose version

# Try Docker Compose V1 (standalone)
docker-compose --version

# Install Docker Compose plugin (Linux)
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Install standalone docker-compose (Linux)
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker compose version
# or
docker-compose --version
```

### Permission Denied for Docker Socket

**Symptom:** `permission denied while trying to connect to the Docker daemon socket`

**Causes:**
- User not in docker group
- Docker socket has wrong permissions

**Solutions:**

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in for changes to take effect
# Or use newgrp to activate group immediately
newgrp docker

# Verify group membership
groups
# Should include 'docker'

# Fix socket permissions (temporary)
sudo chmod 666 /var/run/docker.sock

# Permanent fix: ensure docker group owns socket
sudo chown root:docker /var/run/docker.sock
```

### Out of Disk Space

**Symptom:** `no space left on device` or `E010` error code

**Causes:**
- Docker images consuming disk space
- Container logs filling disk
- Old volumes not cleaned up

**Solutions:**

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Remove unused images
docker image prune -a

# Remove unused containers
docker container prune

# Remove unused volumes
docker volume prune

# Remove everything unused (CAUTION: destructive)
docker system prune -a --volumes

# View largest Docker resources
docker images --format "{{.Size}}\t{{.Repository}}:{{.Tag}}" | sort -hr | head -10
docker ps -a --format "{{.Size}}\t{{.Names}}" | sort -hr | head -10
```

---

## Port Conflicts

### Port 8001 Already in Use (Web)

**Symptom:** `bind: address already in use` or `E003` error code for port 8001

**Causes:**
- Another PromptVault instance running
- Another web application using port 8001
- Previous container not stopped properly

**Solutions:**

```bash
# Find process using port 8001
sudo lsof -i :8001
# or
sudo netstat -tulpn | grep 8001
# or (macOS)
sudo lsof -i tcp:8001

# Kill the process
sudo kill -9 <PID>

# Or stop existing PromptVault containers
docker-compose down

# Change port in docker-compose.yml
# Edit the ports section:
ports:
  - "8002:8001"  # Use 8002 on host instead

# Or use environment variable
PORT=8002 docker-compose up -d
```

### Port 5432 Already in Use (PostgreSQL)

**Symptom:** `bind: address already in use` for port 5432

**Causes:**
- System PostgreSQL already running
- Another PostgreSQL container running
- Port conflict with other service

**Solutions:**

```bash
# Find process using port 5432
sudo lsof -i :5432
sudo netstat -tulpn | grep 5432

# Stop system PostgreSQL (if not needed)
sudo systemctl stop postgresql
sudo systemctl disable postgresql  # Prevent auto-start

# Or expose PostgreSQL on different port
# Edit docker-compose.yml:
db:
  ports:
    - "5433:5432"  # Use 5433 on host

# Note: Internal connections use port 5432, only host access changes
```

### Port 6379 Already in Use (Redis)

**Symptom:** `bind: address already in use` for port 6379

**Causes:**
- System Redis already running
- Another Redis container running

**Solutions:**

```bash
# Find process using port 6379
sudo lsof -i :6379
sudo netstat -tulpn | grep 6379

# Stop system Redis
sudo systemctl stop redis
sudo systemctl disable redis

# Redis port is not exposed by default in docker-compose.yml
# If you exposed it manually and have conflicts, change it:
redis:
  ports:
    - "6380:6379"  # Use 6380 on host
```

### Check Multiple Ports

```bash
# Check all PromptVault ports at once
for port in 8001 5432 6379; do
  echo "Checking port $port..."
  sudo lsof -i :$port || echo "Port $port is free"
done

# Quick port availability test
nc -zv localhost 8001
nc -zv localhost 5432
nc -zv localhost 6379
```

---

## Database Issues

### PostgreSQL Connection Failed

**Symptom:** `could not connect to server: Connection refused` or `E004` error code

**Causes:**
- PostgreSQL container not running
- Wrong DATABASE_URL
- Network connectivity issues
- Database not fully initialized

**Solutions:**

```bash
# Check PostgreSQL container status
docker-compose ps db

# Check PostgreSQL logs
docker-compose logs db

# Verify DATABASE_URL in .env
cat .env | grep DATABASE_URL
# Should be: postgresql://promptvault:password@db:5432/promptvault

# Test database connectivity from web container
docker-compose exec web pg_isready -h db -p 5432 -U promptvault

# Restart PostgreSQL container
docker-compose restart db

# Wait for database to be ready
docker-compose up -d db
sleep 15  # Give it time to initialize

# Check health status
docker inspect promptvault-db --format='{{.State.Health.Status}}'
```

### Database Does Not Exist

**Symptom:** `database "promptvault" does not exist`

**Causes:**
- Database not created during initialization
- Wrong database name in DATABASE_URL
- PostgreSQL initialization failed

**Solutions:**

```bash
# Check PostgreSQL logs for initialization errors
docker-compose logs db | grep -i error

# Recreate database manually
docker-compose exec db psql -U promptvault postgres -c "CREATE DATABASE promptvault;"

# Or recreate containers to reinitialize
docker-compose down -v  # WARNING: Destroys data!
docker-compose up -d

# Verify database exists
docker-compose exec db psql -U promptvault postgres -c "\l"
```

### Authentication Failed for User

**Symptom:** `password authentication failed for user "promptvault"`

**Causes:**
- Wrong POSTGRES_PASSWORD in .env
- Password mismatch between .env and DATABASE_URL
- PostgreSQL authentication configuration issue

**Solutions:**

```bash
# Check .env file
cat .env | grep POSTGRES_PASSWORD

# Ensure DATABASE_URL uses same password
cat .env | grep DATABASE_URL
# Should match: postgresql://promptvault:${POSTGRES_PASSWORD}@db:5432/promptvault

# Update password in both places
nano .env
# Set: POSTGRES_PASSWORD=your_secure_password
# And: DATABASE_URL=postgresql://promptvault:your_secure_password@db:5432/promptvault

# Recreate database container with new password
docker-compose down
docker volume rm promptvault_postgres_data  # WARNING: Destroys data!
docker-compose up -d db

# Or change password in running database
docker-compose exec db psql -U postgres -c "ALTER USER promptvault WITH PASSWORD 'new_password';"
```

### Migration Failures

**Symptom:** `alembic.util.exc.CommandError` or `E005` error code during migrations

**Causes:**
- Database schema out of sync
- Migration revision not found
- Concurrent migration attempts
- Database connection issues during migration

**Solutions:**

```bash
# Check current migration version
docker-compose exec web alembic current

# Check migration history
docker-compose exec web alembic history

# View pending migrations
docker-compose exec web alembic upgrade head --sql

# Reset migration state (use with caution)
docker-compose exec web alembic stamp head

# Downgrade and re-upgrade
docker-compose exec web alembic downgrade -1
docker-compose exec web alembic upgrade head

# If completely stuck, recreate database
docker-compose down
docker volume rm promptvault_postgres_data
docker-compose up -d db
sleep 15
docker-compose exec web alembic upgrade head
```

### SQLite File Permissions

**Symptom:** `attempt to write a readonly database` (SQLite)

**Causes:**
- Database file has wrong permissions
- Database directory not writable
- File owned by different user

**Solutions:**

```bash
# Check file permissions
ls -la data/promptvault.db

# Fix file permissions
chmod 644 data/promptvault.db
chmod 755 data/

# Fix ownership
chown $USER:$USER data/promptvault.db
chown $USER:$USER data/

# Ensure directory is writable
test -w data && echo "Writable" || echo "Not writable"
```

### Database Locked Errors

**Symptom:** `database is locked` (SQLite)

**Causes:**
- Multiple processes accessing SQLite database
- Long-running transaction
- File system issues

**Solutions:**

```bash
# Identify processes using database
lsof data/promptvault.db

# Stop all PromptVault processes
docker-compose down
pkill -f "python run_web.py"

# Remove lock files if present
rm -f data/promptvault.db-shm
rm -f data/promptvault.db-wal

# Use PostgreSQL for production (SQLite not recommended)
# SQLite is single-writer, not suitable for concurrent access
```

---

## JWT Key Issues

### Keys Missing or Not Found

**Symptom:** `JWT key file does not exist` or `E006` error code

**Causes:**
- JWT keys not generated
- Keys deleted or moved
- Wrong path in configuration
- Volume mount issue in Docker

**Solutions:**

```bash
# Check if keys exist
ls -la secrets/jwt/

# Generate missing keys
mkdir -p secrets/jwt
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# Verify keys are valid
openssl ec -in secrets/jwt/private_key.pem -text -noout
openssl ec -pubin -in secrets/jwt/public_key.pem -text -noout

# Check Docker volume mount
docker-compose config | grep jwt
# Should show: - ./secrets/jwt:/app/secrets/jwt:ro

# Check keys inside container
docker-compose exec web ls -la /app/secrets/jwt/

# Restart containers after generating keys
docker-compose restart web
```

### Invalid Key Format

**Symptom:** `Invalid private key format` or `Invalid public key format`

**Causes:**
- Corrupted key file
- Wrong key algorithm (not EC P-256)
- File encoding issues
- Wrong PEM format

**Solutions:**

```bash
# Verify key format
head -1 secrets/jwt/private_key.pem
# Should be: -----BEGIN EC PRIVATE KEY-----

head -1 secrets/jwt/public_key.pem
# Should be: -----BEGIN PUBLIC KEY-----

# Regenerate keys with correct format
rm secrets/jwt/*.pem
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# Validate key structure
openssl ec -in secrets/jwt/private_key.pem -text -noout | grep "ASN1 OID: prime256v1"
# Should confirm P-256 curve

# Check file encoding
file secrets/jwt/private_key.pem
# Should be: PEM EC private key
```

### Permission Denied Reading Keys

**Symptom:** `Key file is not readable` or `PermissionError` when accessing keys

**Causes:**
- Wrong file permissions
- Keys owned by wrong user
- SELinux or AppArmor blocking access

**Solutions:**

```bash
# Check current permissions
ls -la secrets/jwt/

# Set correct permissions
chmod 600 secrets/jwt/private_key.pem  # Private: read-write for owner only
chmod 644 secrets/jwt/public_key.pem   # Public: readable by all

# Fix ownership
chown $USER:$USER secrets/jwt/*.pem

# For Docker, ensure directory is readable
chmod 755 secrets/jwt/

# Check SELinux context (if applicable)
ls -Z secrets/jwt/
# Fix if needed:
sudo chcon -R -t container_file_t secrets/jwt/
```

### Keys Not Validated Correctly

**Symptom:** JWT tokens not working, `Invalid signature` errors

**Causes:**
- Public/private key mismatch
- Keys regenerated but old tokens still in use
- Wrong key loaded by application

**Solutions:**

```bash
# Verify public key matches private key
# Extract public key from private key and compare
openssl ec -in secrets/jwt/private_key.pem -pubout | diff - secrets/jwt/public_key.pem
# Should show no differences

# Regenerate both keys together
rm secrets/jwt/*.pem
openssl ecparam -name prime256v1 -genkey -noout -out secrets/jwt/private_key.pem
openssl ec -in secrets/jwt/private_key.pem -pubout -out secrets/jwt/public_key.pem

# Restart application to load new keys
docker-compose restart web

# Clear any cached tokens (logout all users)
# Users will need to login again
```

---

## Configuration Issues

### .env File Missing

**Symptom:** `File does not exist: .env` or environment variables not loaded

**Causes:**
- .env file not created
- Running from wrong directory
- File named incorrectly

**Solutions:**

```bash
# Check if .env exists
ls -la .env

# Create from example
cp .env.example .env

# Or create minimal .env
cat > .env << 'EOF'
POSTGRES_PASSWORD=change_this_password
DATABASE_URL=postgresql://promptvault:change_this_password@db:5432/promptvault
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF

# Set secure password
nano .env  # Edit POSTGRES_PASSWORD

# Verify .env is valid
cat .env
```

### Invalid DATABASE_URL Format

**Symptom:** `Invalid URL format` or `E007` configuration error

**Causes:**
- Wrong URL scheme
- Missing components (host, port, database name)
- Special characters not escaped
- Typos in URL

**Solutions:**

```bash
# Valid PostgreSQL URL format:
# postgresql://username:password@host:port/database

# Valid SQLite URL format:
# sqlite:///./data/promptvault.db

# Check current DATABASE_URL
cat .env | grep DATABASE_URL

# Common mistakes to avoid:
# ❌ postgres://... (should be postgresql://)
# ❌ postgresql://host:5432 (missing username, password, database)
# ❌ postgresql://user@host:5432/db (missing password)

# Correct format:
DATABASE_URL=postgresql://promptvault:mypassword@db:5432/promptvault

# Escape special characters in password
# If password is: p@ssw0rd!
# Escape as: p%40ssw0rd%21
```

### Missing Required Environment Variables

**Symptom:** Application fails to start, environment validation errors

**Causes:**
- Required variables not set in .env
- Typos in variable names
- Wrong variable format

**Solutions:**

```bash
# Check required variables
cat .env | grep -E "DATABASE_URL|POSTGRES_PASSWORD"

# Minimal required .env:
cat > .env << 'EOF'
# Database
POSTGRES_PASSWORD=your_secure_password_here
DATABASE_URL=postgresql://promptvault:your_secure_password_here@db:5432/promptvault

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8001

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_PRIVATE_KEY_PATH=/app/secrets/jwt/private_key.pem
JWT_PUBLIC_KEY_PATH=/app/secrets/jwt/public_key.pem
EOF

# Validate .env file
python scripts/setup/utils/validators.py .env  # If validator script exists
```

### Configuration Validation Errors

**Symptom:** `Configuration validation failed` or `E007` error code

**Causes:**
- Invalid configuration values
- Type mismatch (string instead of number)
- Out of range values

**Solutions:**

```bash
# Common validation issues:

# Port must be 1-65535
PORT=8001  # ✓ Valid
PORT=70000  # ✗ Invalid (too high)

# Password must meet complexity requirements (16+ chars)
POSTGRES_PASSWORD=Ab1!defghijklmno  # ✓ Valid (16 chars, mixed case, number, special)
POSTGRES_PASSWORD=password  # ✗ Invalid (too short, no complexity)

# Environment must be specific values
ENVIRONMENT=production  # ✓ Valid
ENVIRONMENT=prod  # ✗ Invalid (use 'production')

# Log level must be valid
LOG_LEVEL=INFO  # ✓ Valid
LOG_LEVEL=VERBOSE  # ✗ Invalid (use DEBUG, INFO, WARNING, ERROR)

# Check all values in .env
cat .env
```

---

## Container Issues

### Container Fails to Start

**Symptom:** Container exits immediately, `docker-compose ps` shows exited status

**Causes:**
- Configuration errors
- Missing dependencies
- Port conflicts
- Resource limits
- Healthcheck failures

**Solutions:**

```bash
# Check container status
docker-compose ps

# View container logs
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Check for errors in logs
docker-compose logs web | grep -i error
docker-compose logs web | grep -i exception

# Try starting with verbose output
docker-compose up web  # Without -d to see output

# Check container configuration
docker-compose config

# Rebuild container
docker-compose build --no-cache web
docker-compose up -d web

# Check resource usage
docker stats
```

### Health Check Timeouts

**Symptom:** Service marked as unhealthy, `E008` error code

**Causes:**
- Service taking too long to start
- Healthcheck endpoint not responding
- Network issues
- Resource constraints

**Solutions:**

```bash
# Check health status
docker inspect promptvault-web --format='{{.State.Health.Status}}'
docker inspect promptvault-db --format='{{.State.Health.Status}}'

# View health check logs
docker inspect promptvault-web --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Manually test health endpoint
docker-compose exec web curl -f http://localhost:8001/api/health

# Increase timeout in docker-compose.yml
# Edit healthcheck section:
healthcheck:
  start_period: 60s  # Increase from 40s
  timeout: 15s       # Increase from 10s
  interval: 30s
  retries: 5

# Restart with new settings
docker-compose down
docker-compose up -d
```

### Services Not Becoming Healthy

**Symptom:** Containers start but never reach healthy status

**Causes:**
- Application errors preventing startup
- Database migrations not running
- Missing environment variables
- Dependency issues

**Solutions:**

```bash
# Check all service health
docker-compose ps

# Check if dependencies are ready
docker-compose exec db pg_isready -U promptvault
docker-compose exec redis redis-cli ping

# Run migrations manually
docker-compose exec web alembic upgrade head

# Check application logs for startup errors
docker-compose logs web --tail=100

# Verify environment variables are set
docker-compose exec web env | grep -E "DATABASE_URL|REDIS_URL|JWT"

# Test health endpoint directly
curl -v http://localhost:8001/api/health

# Restart in correct order
docker-compose down
docker-compose up -d db redis
sleep 15
docker-compose up -d web
```

### Container Constantly Restarting

**Symptom:** Container in restart loop, `Restarting (1)` status

**Causes:**
- Application crashes on startup
- Healthcheck failures
- Configuration errors
- Resource exhaustion

**Solutions:**

```bash
# Check restart count
docker-compose ps

# View crash logs
docker-compose logs web --tail=200

# Disable auto-restart temporarily
docker-compose stop web
docker-compose run --rm web  # Run once without restart policy

# Check for specific errors
docker-compose logs web | grep -i "error\|exception\|fatal\|critical"

# Increase resource limits (if needed)
# Edit docker-compose.yml:
web:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 512M

# Restart with more verbose logging
docker-compose down
LOG_LEVEL=DEBUG docker-compose up web
```

---

## Migration Issues

### Alembic Revision Not Found

**Symptom:** `Can't locate revision identified by 'xxxx'`

**Causes:**
- Migration files missing
- Database alembic_version table out of sync
- Git conflicts in migration files

**Solutions:**

```bash
# Check current migration version
docker-compose exec web alembic current

# View migration history
docker-compose exec web alembic history

# Check migration files exist
ls -la alembic/versions/

# Reset migration state to head
docker-compose exec web alembic stamp head

# Or stamp to specific revision
docker-compose exec web alembic stamp <revision_id>

# Re-run migrations
docker-compose exec web alembic upgrade head

# If migrations are completely broken, recreate database
docker-compose down
docker volume rm promptvault_postgres_data
docker-compose up -d db
sleep 15
docker-compose exec web alembic upgrade head
```

### Column Does Not Exist Errors

**Symptom:** `column "categories.updated_at" does not exist`

**Causes:**
- Migrations not applied
- Migrations failed silently
- Database schema mismatch

**Solutions:**

```bash
# Check which migrations have been applied
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 5;"

# Check if specific column exists
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT column_name FROM information_schema.columns WHERE table_name='categories';"

# Run migrations again
docker-compose exec web alembic upgrade head

# If migrations appear to run but don't apply:
# Stop everything, ensure database is ready, then migrate
docker-compose down
docker-compose up -d db redis
sleep 30  # Longer wait for database
docker-compose exec web alembic upgrade head
docker-compose up -d web

# Check logs for migration output
docker-compose logs web | grep alembic
```

### Database Schema Mismatch

**Symptom:** Application errors due to schema differences

**Causes:**
- Partial migration application
- Manual database changes
- Migration rollback issues

**Solutions:**

```bash
# Check current schema
docker-compose exec -T db psql -U promptvault -d promptvault -c "\dt"

# Compare with expected schema
docker-compose exec web alembic current
docker-compose exec web alembic history

# Generate SQL to see what would be applied
docker-compose exec web alembic upgrade head --sql

# Reset to known good state
docker-compose exec web alembic downgrade base
docker-compose exec web alembic upgrade head

# Or recreate from scratch (WARNING: data loss!)
docker-compose down
docker volume rm promptvault_postgres_data
docker-compose up -d db
sleep 15
docker-compose exec web alembic upgrade head
```

### Migration Timeout

**Symptom:** Migration hangs or times out during execution

**Causes:**
- Large dataset migration
- Database locks
- Network issues
- Resource constraints

**Solutions:**

```bash
# Check for database locks
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Kill blocking queries
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND pid <> pg_backend_pid();"

# Run migration with increased timeout
docker-compose exec web bash -c "export PGCONNECT_TIMEOUT=300 && alembic upgrade head"

# Run migration directly with SQL
docker-compose exec web alembic upgrade head --sql > migration.sql
docker-compose exec -T db psql -U promptvault -d promptvault < migration.sql

# Monitor migration progress
docker-compose logs -f web
```

---

## Permission Errors

### Volume Permission Issues (Upgrading from Root Containers)

**Symptom:** `permission denied` after upgrading, `attempt to write a readonly database`

**Causes:**
- Upgrading from containers that ran as root
- Volume files owned by wrong user
- Non-root container can't access root-owned files

**Solutions:**

```bash
# Check volume ownership
docker volume ls
docker run --rm -v promptvault_postgres_data:/data alpine ls -la /data

# Fix PostgreSQL volume permissions (UID 70)
docker run --rm -it \
  -v promptvault_postgres_data:/var/lib/postgresql/data \
  --user 0 alpine sh -c 'chown -R 70:70 /var/lib/postgresql/data'

# If your volume has a prefix:
docker run --rm -it \
  -v postgres_data:/var/lib/postgresql/data \
  --user 0 alpine sh -c 'chown -R 70:70 /var/lib/postgresql/data'

# Fix Redis volume permissions (UID 999)
docker run --rm -it \
  -v promptvault_redis_data:/data \
  --user 0 alpine sh -c 'chown -R 999:999 /data'

# Fix bind-mounted data directory
chown -R $(id -u):$(id -g) ./data
chmod -R 770 ./data

# Restart services after fixing permissions
docker-compose down
docker-compose up -d
```

### File Permission Errors

**Symptom:** `Permission denied` when accessing specific files

**Causes:**
- Wrong file ownership
- Incorrect file permissions
- SELinux/AppArmor restrictions

**Solutions:**

```bash
# Check file ownership and permissions
ls -la /path/to/file

# Fix ownership
chown $USER:$USER /path/to/file

# Fix permissions
chmod 644 /path/to/file  # Files (read-write owner, read others)
chmod 755 /path/to/dir   # Directories (read-write-execute owner, read-execute others)

# Recursive fix for directory
chown -R $USER:$USER /path/to/directory
chmod -R u+rw,go+r /path/to/directory
find /path/to/directory -type d -exec chmod 755 {} \;

# Check SELinux context (if applicable)
ls -Z /path/to/file
# Fix if needed:
sudo chcon -t container_file_t /path/to/file
```

### Directory Creation Failures

**Symptom:** `Cannot create directory` or `mkdir: Permission denied`

**Causes:**
- Parent directory not writable
- Insufficient permissions
- Disk full

**Solutions:**

```bash
# Check parent directory permissions
ls -la /path/to/parent

# Make parent directory writable
chmod 755 /path/to/parent

# Check available disk space
df -h

# Check if directory already exists with wrong permissions
ls -la /path/to/directory
chmod 755 /path/to/directory

# Create directory with correct permissions
mkdir -p /path/to/directory
chmod 755 /path/to/directory
chown $USER:$USER /path/to/directory
```

---

## Error Code Reference

Comprehensive error codes used by PromptVault setup and deployment tools:

| Code | Description | Common Causes | Resolution |
|------|-------------|---------------|------------|
| **E001** | Docker not installed | Docker not in PATH, not installed | Install Docker from docker.com, verify with `docker --version` |
| **E002** | Docker daemon not running | Service stopped, Docker Desktop closed | Start Docker daemon: `sudo systemctl start docker` or open Docker Desktop |
| **E003** | Port already in use | Another service using port 8001/5432/6379 | Check with `lsof -i :PORT`, stop conflicting service or change port |
| **E004** | Database connection failed | PostgreSQL not ready, wrong credentials, network issue | Verify DATABASE_URL, check PostgreSQL logs, wait for initialization |
| **E005** | Migration failed | Database not initialized, migration conflict, schema mismatch | Check Alembic logs, run `alembic stamp head` then `alembic upgrade head` |
| **E006** | JWT key generation failed | No write permissions, disk full, OpenSSL missing | Check `secrets/jwt/` permissions, verify disk space, install OpenSSL |
| **E007** | Invalid configuration | Wrong .env values, invalid DATABASE_URL, missing variables | Validate .env file format, check DATABASE_URL syntax, verify all required vars set |
| **E008** | Health check timeout | Service slow to start, healthcheck endpoint down | Increase healthcheck timeout, check application logs, verify endpoint responds |
| **E009** | Insufficient permissions | User not in docker group, file permissions wrong | Add user to docker group: `sudo usermod -aG docker $USER`, fix file permissions |
| **E010** | Disk space insufficient | Docker images/volumes consuming space | Run `docker system prune -a`, free up disk space, check with `df -h` |

### Error Code Details

#### E001: Docker Not Installed

**Full Description:** Docker is not installed on the system or not accessible in the system PATH.

**How to Diagnose:**
```bash
docker --version
# If returns: command not found
```

**Resolution Steps:**
1. Download Docker from https://docker.com
2. Install for your platform (Linux/macOS/Windows)
3. Verify installation: `docker --version`
4. Add to PATH if needed
5. Re-run setup script

#### E002: Docker Daemon Not Running

**Full Description:** Docker is installed but the daemon is not running or not accessible.

**How to Diagnose:**
```bash
docker info
# If returns: Cannot connect to the Docker daemon
```

**Resolution Steps:**
1. Linux: `sudo systemctl start docker`
2. macOS/Windows: Start Docker Desktop application
3. Verify: `docker info`
4. Enable auto-start: `sudo systemctl enable docker` (Linux)
5. Re-run setup script

#### E003: Port Already in Use

**Full Description:** Required port (8001, 5432, or 6379) is already bound by another process.

**How to Diagnose:**
```bash
sudo lsof -i :8001
sudo lsof -i :5432
sudo lsof -i :6379
```

**Resolution Steps:**
1. Identify process using port
2. Stop the conflicting process
3. Or change PromptVault port in docker-compose.yml
4. Re-run setup script

#### E004: Database Connection Failed

**Full Description:** Unable to establish connection to PostgreSQL database.

**How to Diagnose:**
```bash
docker-compose logs db
docker-compose exec web pg_isready -h db -p 5432
```

**Resolution Steps:**
1. Ensure database container is running
2. Wait 15+ seconds for initialization
3. Verify DATABASE_URL in .env
4. Check PostgreSQL logs for errors
5. Restart database: `docker-compose restart db`

#### E005: Migration Failed

**Full Description:** Alembic database migration failed to complete successfully.

**How to Diagnose:**
```bash
docker-compose exec web alembic current
docker-compose exec web alembic history
docker-compose logs web | grep alembic
```

**Resolution Steps:**
1. Ensure database is fully initialized (wait 15s)
2. Check Alembic version: `alembic current`
3. Reset state: `alembic stamp head`
4. Re-run: `alembic upgrade head`
5. Check logs for specific errors

#### E006: JWT Key Generation Failed

**Full Description:** Unable to generate or validate JWT cryptographic keys.

**How to Diagnose:**
```bash
ls -la secrets/jwt/
openssl version
```

**Resolution Steps:**
1. Verify OpenSSL installed: `openssl version`
2. Check directory permissions: `ls -la secrets/`
3. Generate manually: See JWT Key Issues section
4. Verify disk space: `df -h`
5. Check file permissions after generation

#### E007: Invalid Configuration

**Full Description:** Configuration validation failed due to invalid or missing values.

**How to Diagnose:**
```bash
cat .env | grep -E "DATABASE_URL|POSTGRES_PASSWORD|PORT"
```

**Resolution Steps:**
1. Validate .env file exists and is readable
2. Check DATABASE_URL format
3. Verify POSTGRES_PASSWORD meets requirements (16+ chars)
4. Ensure PORT is valid (1-65535)
5. Check for typos in variable names

#### E008: Health Check Timeout

**Full Description:** Service container failed to become healthy within timeout period.

**How to Diagnose:**
```bash
docker inspect promptvault-web --format='{{.State.Health.Status}}'
docker-compose logs web --tail=100
```

**Resolution Steps:**
1. Check application logs for errors
2. Verify healthcheck endpoint: `curl http://localhost:8001/api/health`
3. Increase timeout in docker-compose.yml
4. Ensure dependencies (db, redis) are healthy
5. Restart services in correct order

#### E009: Insufficient Permissions

**Full Description:** User lacks necessary permissions to perform operation.

**How to Diagnose:**
```bash
groups  # Check if 'docker' is listed
ls -la /var/run/docker.sock
```

**Resolution Steps:**
1. Add user to docker group: `sudo usermod -aG docker $USER`
2. Log out and back in
3. Verify: `groups` should include 'docker'
4. Check file permissions: `ls -la`
5. Fix as needed: `chmod` or `chown`

#### E010: Disk Space Insufficient

**Full Description:** Not enough disk space to complete operation.

**How to Diagnose:**
```bash
df -h
docker system df
```

**Resolution Steps:**
1. Check disk usage: `df -h`
2. Check Docker usage: `docker system df`
3. Remove unused images: `docker image prune -a`
4. Remove unused volumes: `docker volume prune`
5. Free up system disk space

---

## Debug Commands

### Check Docker Status

```bash
# Verify Docker installation
docker --version
docker compose version

# Check Docker daemon
docker info
systemctl status docker  # Linux

# List running containers
docker ps

# List all containers
docker ps -a

# Check Docker disk usage
docker system df

# View Docker events (real-time)
docker events
```

### View Container Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Follow logs (real-time)
docker-compose logs -f web

# Last N lines
docker-compose logs --tail=100 web

# With timestamps
docker-compose logs -t web

# Since specific time
docker-compose logs --since 2024-01-01T00:00:00 web

# Multiple services
docker-compose logs web db
```

### Inspect Database Connectivity

```bash
# Test PostgreSQL connection from host
docker-compose exec db psql -U promptvault -d promptvault -c "SELECT 1;"

# Test from web container
docker-compose exec web pg_isready -h db -p 5432 -U promptvault

# Check database exists
docker-compose exec -T db psql -U promptvault postgres -c "\l"

# List tables
docker-compose exec -T db psql -U promptvault -d promptvault -c "\dt"

# Count records
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"

# Check PostgreSQL version
docker-compose exec db psql -U promptvault -d promptvault -c "SELECT version();"

# View active connections
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT * FROM pg_stat_activity WHERE state = 'active';"
```

### Verify Configuration

```bash
# View environment variables
cat .env

# Check Docker Compose configuration
docker-compose config

# View environment in running container
docker-compose exec web env

# Check specific variables
docker-compose exec web env | grep DATABASE_URL
docker-compose exec web env | grep JWT

# Verify file mounts
docker-compose exec web ls -la /app/secrets/jwt/
docker-compose exec web ls -la /app/data/

# Test configuration validity
docker-compose config --quiet && echo "Valid" || echo "Invalid"
```

### Test JWT Keys

```bash
# Check keys exist
ls -la secrets/jwt/

# Verify private key format
openssl ec -in secrets/jwt/private_key.pem -text -noout

# Verify public key format
openssl ec -pubin -in secrets/jwt/public_key.pem -text -noout

# Extract public key from private key and compare
openssl ec -in secrets/jwt/private_key.pem -pubout | diff - secrets/jwt/public_key.pem

# Check keys in container
docker-compose exec web cat /app/secrets/jwt/private_key.pem | head -1
docker-compose exec web cat /app/secrets/jwt/public_key.pem | head -1

# Verify key permissions
ls -la secrets/jwt/
# Private key should be 600 or 400
# Public key should be 644 or 444
```

### Network Debugging

```bash
# Check network connectivity
docker-compose exec web ping -c 3 db
docker-compose exec web ping -c 3 redis

# Test HTTP endpoint
docker-compose exec web curl -v http://localhost:8001/api/health
curl -v http://localhost:8001/api/health

# Check DNS resolution
docker-compose exec web nslookup db
docker-compose exec web nslookup redis

# List Docker networks
docker network ls

# Inspect PromptVault network
docker network inspect promptvault_default

# Check port bindings
docker port promptvault-web
docker port promptvault-db
```

### Container Health Checks

```bash
# Check health status
docker inspect promptvault-web --format='{{.State.Health.Status}}'
docker inspect promptvault-db --format='{{.State.Health.Status}}'
docker inspect promptvault-redis --format='{{.State.Health.Status}}'

# View health check logs
docker inspect promptvault-web --format='{{range .State.Health.Log}}{{.Output}}{{end}}'

# Manual health check
docker-compose exec web curl -f http://localhost:8001/api/health
docker-compose exec db pg_isready -U promptvault
docker-compose exec redis redis-cli ping

# Wait for service to be healthy
timeout 120 bash -c 'until docker inspect promptvault-db --format="{{.State.Health.Status}}" | grep -q healthy; do sleep 2; done'
```

### Performance Monitoring

```bash
# Container resource usage
docker stats

# Specific container stats
docker stats promptvault-web

# Container processes
docker-compose top web

# Database performance
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"

# Slow queries
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT query, calls, total_time, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

---

## Log Locations

### Application Logs

**Docker Compose:**
```bash
# Real-time logs
docker-compose logs -f web

# Saved to file
docker-compose logs web > promptvault-app.log

# Location inside container
docker-compose exec web ls -la /app/logs/  # If configured
```

**Manual Deployment:**
```bash
# Standard output (if running in foreground)
python run_web.py

# Or systemd journal (if running as service)
journalctl -u promptvault -f

# Custom log file (if configured)
tail -f /var/log/promptvault/app.log
```

### Docker Logs

**Container logs:**
```bash
# Docker Compose
docker-compose logs web
docker-compose logs db
docker-compose logs redis

# Direct Docker
docker logs promptvault-web
docker logs promptvault-db
docker logs promptvault-redis

# Log files on host
sudo ls -la /var/lib/docker/containers/*/
```

**Docker daemon logs:**
```bash
# Linux (systemd)
journalctl -u docker -f

# Linux (traditional)
tail -f /var/log/docker.log

# macOS
tail -f ~/Library/Containers/com.docker.docker/Data/log/vm/dockerd.log
```

### Database Logs

**PostgreSQL logs (Docker):**
```bash
# Via docker-compose
docker-compose logs db

# PostgreSQL internal logs
docker-compose exec db tail -f /var/lib/postgresql/data/log/postgresql-*.log

# Query logs (if enabled)
docker-compose exec -T db psql -U promptvault -d promptvault -c "SHOW log_destination;"
```

**PostgreSQL logs (Manual):**
```bash
# Default location (Ubuntu/Debian)
tail -f /var/log/postgresql/postgresql-15-main.log

# Alternative locations
tail -f /var/lib/postgresql/15/main/log/postgresql-*.log
tail -f /usr/local/var/log/postgres.log  # macOS Homebrew
```

### Audit Logs

**Application audit logs:**
```bash
# Location defined in configuration
docker-compose exec web ls -la /app/data/audit/

# View recent audit events
docker-compose exec web tail -f /app/data/audit/audit.log

# Search audit logs
docker-compose exec web grep "login" /app/data/audit/audit.log
docker-compose exec web grep "failed" /app/data/audit/audit.log
```

**Database audit logs:**
```bash
# User activity
docker-compose exec -T db psql -U promptvault -d promptvault -c \
  "SELECT * FROM pg_stat_activity ORDER BY state_change DESC;"

# Connection logs
docker-compose exec db grep "connection" /var/lib/postgresql/data/log/postgresql-*.log
```

### Access Logs

**Web server access logs:**
```bash
# If using nginx reverse proxy
tail -f /var/log/nginx/promptvault-access.log

# If using Apache reverse proxy
tail -f /var/log/apache2/promptvault-access.log

# Uvicorn access logs (application server)
docker-compose logs web | grep "GET\|POST\|PUT\|DELETE"
```

### Log Rotation

**Configure log rotation:**
```bash
# Create logrotate configuration
sudo nano /etc/logrotate.d/promptvault

# Add configuration:
/var/log/promptvault/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 promptvault promptvault
}

# Test log rotation
sudo logrotate -d /etc/logrotate.d/promptvault
```

**Docker log rotation:**
```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

---

## Getting Help

### Codeberg Issues

**Before creating an issue:**

1. Search existing issues: https://codeberg.org/medenor/promptvault/issues
2. Check if your version is up to date
3. Review this troubleshooting guide
4. Collect relevant information (see below)

**Creating a new issue:**

1. Go to: https://codeberg.org/medenor/promptvault/issues/new
2. Choose appropriate template (Bug Report, Feature Request, etc.)
3. Fill in all required information
4. Include debug information (see next section)

### Providing Debug Information

**Essential information to include:**

```bash
# System information
uname -a
cat /etc/os-release  # Linux
sw_vers  # macOS

# Docker versions
docker --version
docker compose version

# PromptVault version
git describe --tags
git log -1 --oneline

# Container status
docker-compose ps

# Configuration (sanitized - remove passwords!)
docker-compose config | sed 's/password=.*/password=REDACTED/g'

# Recent logs
docker-compose logs --tail=100 web
docker-compose logs --tail=100 db

# Error messages (specific error you're seeing)
docker-compose logs web | grep -i "error\|exception" | tail -20
```

**Save debug information to file:**

```bash
# Create debug report
cat > debug-report.txt << EOF
=== System Information ===
$(uname -a)
$(cat /etc/os-release)

=== Docker Versions ===
$(docker --version)
$(docker compose version)

=== Container Status ===
$(docker-compose ps)

=== Recent Logs ===
$(docker-compose logs --tail=50 web)

=== Configuration ===
$(docker-compose config | sed 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=REDACTED/')
EOF

# Review before sharing (ensure no secrets!)
less debug-report.txt
```

### What to Include in Bug Reports

**Required:**
- Clear description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages (full text)

**Helpful:**
- PromptVault version
- Docker version
- Operating system
- Configuration (sanitized)
- Logs (relevant portions)
- Screenshots (if UI issue)

**Security:**
- NEVER include passwords
- NEVER include JWT keys
- NEVER include personal data
- NEVER include sensitive database content

**Example bug report:**

```markdown
## Description
Database migration fails when upgrading from v1.4.0 to v1.5.0

## Steps to Reproduce
1. Running PromptVault v1.4.0 with PostgreSQL
2. Pull latest code: `git pull origin main`
3. Rebuild containers: `docker-compose build --no-cache`
4. Run migrations: `docker-compose exec web alembic upgrade head`

## Expected Behavior
Migrations should apply cleanly and upgrade database schema to v1.5.0

## Actual Behavior
Migration fails with error:
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

## Environment
- PromptVault version: v1.5.0 (commit: def456)
- Docker version: 24.0.6
- OS: Ubuntu 22.04
- Database: PostgreSQL 15

## Logs
```
[logs here]
```

## Configuration
```
DATABASE_URL=postgresql://promptvault:REDACTED@db:5432/promptvault
```
```

### Community Support

**Resources:**
- Documentation: https://codeberg.org/medenor/promptvault/src/branch/main/docs

**Before asking:**
1. Search existing discussions
2. Read relevant documentation
3. Try basic troubleshooting steps
4. Prepare clear question with context

**When asking for help:**
1. Be specific about the problem
2. Show what you've tried
3. Include relevant details
4. Be patient and respectful
5. Update thread with resolution

---

## Additional Resources

- [Turnkey Deployment Guide](DEPLOYMENT.md) - Automated deployment with rollback capabilities
- [Deployment Guide](DEPLOYMENT.md) - Detailed deployment instructions
- [Migration Guide](MIGRATION_GUIDE_JSON_TO_DB.md) - Migrating from JSON to database
- [Authentication Documentation](AUTHENTICATION_DEPLOYMENT.md) - JWT and security setup
- [Testing Guide](TESTING.md) - Running tests and validation

---

**Last Updated:** 2024-02-03

**Contributing:** If you encounter an issue not covered in this guide, please submit a pull request with the solution!
