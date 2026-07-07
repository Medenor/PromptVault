# Deployment Orchestration Script

Complete deployment automation for PromptVault with pre-flight checks, five-phase deployment process, and automatic rollback capabilities.

## Overview

The `deploy.py` script provides a comprehensive, production-ready deployment system that:

- Performs thorough pre-flight checks
- Executes deployment in 5 distinct phases
- Automatically creates backups before deployment
- Handles database migrations
- Provides automatic rollback on failure
- Supports dry-run mode for testing
- Integrates with existing Docker infrastructure

## Quick Start

### Basic Deployment

```bash
# Standard deployment
python scripts/setup/deploy.py

# Non-interactive deployment (CI/CD)
python scripts/setup/deploy.py --non-interactive

# Dry run (see what would happen)
python scripts/setup/deploy.py --dry-run
```

### Advanced Options

```bash
# Skip backup (faster, but not recommended for production)
python scripts/setup/deploy.py --skip-backup

# Skip database migrations
python scripts/setup/deploy.py --skip-migrations

# Force rebuild Docker images
python scripts/setup/deploy.py --rebuild

# Rollback to previous state
python scripts/setup/deploy.py --rollback
```

## Command-Line Options

| Option              | Description                                           |
| ------------------- | ----------------------------------------------------- |
| `--dry-run`         | Show what would happen without executing any changes  |
| `--skip-backup`     | Skip database backup phase (not recommended)          |
| `--skip-migrations` | Skip Alembic migration phase                          |
| `--rollback`        | Rollback to previous deployment state                 |
| `--rebuild`         | Force rebuild of Docker images instead of pulling     |
| `--non-interactive` | Run without prompts (use defaults, perfect for CI/CD) |
| `--help`            | Show help message and available options               |

## Deployment Phases

The deployment process consists of five distinct phases:

### Phase 1: Preparation

- Creates database backup (unless `--skip-backup` is used)
- Saves current container states for rollback
- Pulls or builds Docker images (based on `--rebuild` flag)

### Phase 2: Infrastructure

- Starts PostgreSQL database container
- Waits for database to become healthy (up to 2 minutes)
- Starts Redis cache container
- Waits for Redis to become healthy (up to 1 minute)

### Phase 3: Migrations

- Runs Alembic database migrations (`alembic upgrade head`)
- Can be skipped with `--skip-migrations` flag
- Verifies database connectivity before running migrations

### Phase 4: Application

- Starts PromptVault web service container
- Waits for application to become healthy (up to 3 minutes)
- Monitors health check endpoint

### Phase 5: Verification

- Runs smoke tests:
  - Health endpoint check (`/api/health`)
  - Database connectivity test
  - Redis connectivity test
- Displays deployment summary
- Shows access information and useful commands

## Pre-flight Checks

Before deployment, the script performs comprehensive checks:

1. **Docker Installation**: Verifies Docker is installed and accessible
2. **Docker Daemon**: Confirms Docker daemon is running
3. **Docker Compose**: Ensures Docker Compose is available
4. **Port Availability**: Checks ports 8001, 5432, 6379
5. **Disk Space**: Verifies at least 2GB available (1GB minimum)
6. **JWT Keys**: Validates JWT key files if present
7. **Environment File**: Checks for `.env` file
8. **Docker Compose File**: Confirms `docker-compose.yml` exists

If any critical check fails, deployment is aborted.

## Automatic Rollback

If deployment fails during any phase, the script offers automatic rollback:

1. Stops all running containers
2. Restores database from backup (if available)
3. Restarts services with previous state

You can also manually trigger rollback:

```bash
python scripts/setup/deploy.py --rollback
```

## Backup Management

### Automatic Backups

Backups are automatically created in Phase 1 and stored in:

```
data/backups/promptvault-deploy-YYYYMMDD_HHMMSS.sql.gz
```

Each backup is:

- Timestamped for easy identification
- Compressed with gzip for space efficiency
- Automatically verified after creation

### Manual Restoration

To restore from a specific backup:

```bash
# List available backups
ls -lh data/backups/

# Restore manually
gunzip -c data/backups/promptvault-deploy-20240203_120000.sql.gz | \
  docker-compose exec -T db psql -U promptvault -d promptvault
```

## Dry Run Mode

Test deployment without making changes:

```bash
python scripts/setup/deploy.py --dry-run
```

Dry run mode:

- Shows exactly what would happen
- Performs all checks except actual execution
- Perfect for testing deployment in CI/CD pipelines
- Validates configuration and prerequisites

## CI/CD Integration

For automated deployments in CI/CD pipelines:

```bash
# Non-interactive deployment with error handling
python scripts/setup/deploy.py --non-interactive || exit 1
```

Example Forgejo Actions workflow:

```yaml
- name: Deploy PromptVault
  run: |
    python scripts/setup/deploy.py \
      --non-interactive \
      --rebuild
```

Example GitLab CI:

```yaml
deploy:
  script:
    - python scripts/setup/deploy.py --non-interactive
  only:
    - main
```

## Troubleshooting

### Deployment Fails

1. Check the logs from the failed phase
2. Review error messages in the console output
3. Use `--dry-run` to validate configuration
4. Check Docker logs: `docker-compose logs -f`

### Pre-flight Checks Fail

**Docker not running:**

```bash
# macOS/Windows
# Start Docker Desktop

# Linux
sudo systemctl start docker
```

**Port already in use:**

```bash
# Check what's using the port
lsof -i :8001

# Stop conflicting service or change port in docker-compose.yml
```

**Insufficient disk space:**

```bash
# Clean up Docker resources
docker system prune -a

# Remove old backups
rm data/backups/promptvault-deploy-*.sql.gz
```

### Migrations Fail

1. Check database connectivity:

   ```bash
   docker-compose exec db psql -U promptvault -d promptvault -c "SELECT 1"
   ```

2. Review Alembic migration files:

   ```bash
   ls -la alembic/versions/
   ```

3. Check current migration version:

   ```bash
   alembic current
   ```

4. Manually run migrations with verbose output:
   ```bash
   alembic upgrade head -v
   ```

### Application Won't Start

1. View application logs:

   ```bash
   docker-compose logs -f web
   ```

2. Check health endpoint:

   ```bash
   curl http://localhost:8001/api/health
   ```

3. Verify environment variables:
   ```bash
   docker-compose config
   ```

## Integration with Existing Scripts

The deployment script integrates with existing PromptVault tools:

### Pre-Deploy Check Script

For additional validation, you can run the legacy pre-deploy check:

```bash
bash scripts/pre-deploy-check.sh
```

### Docker Utils

The script uses `scripts/setup/utils/docker_utils.py` for all Docker operations, ensuring consistency across all setup scripts.

### Console Utilities

Rich-formatted console output is provided by `scripts/setup/utils/console.py` for a consistent user experience.

## Best Practices

1. **Always run pre-flight checks**: Let the script validate your environment
2. **Use backups**: Don't skip the backup phase in production
3. **Test with dry-run**: Validate changes before applying them
4. **Monitor logs**: Watch application logs during deployment
5. **Keep backups**: Retain several recent backups for safety
6. **Use non-interactive mode in CI/CD**: Ensures consistent automation
7. **Review migrations**: Check Alembic migrations before deploying

## Exit Codes

| Code | Meaning                                                            |
| ---- | ------------------------------------------------------------------ |
| 0    | Deployment completed successfully                                  |
| 1    | Deployment failed (rollback may have been performed)               |
| 2    | Deployment and rollback both failed (manual intervention required) |

## Examples

### Production Deployment

```bash
# Full production deployment with all safety checks
python scripts/setup/deploy.py
```

### Development Deployment

```bash
# Quick deployment for development (skip backup, rebuild images)
python scripts/setup/deploy.py \
  --skip-backup \
  --rebuild \
  --non-interactive
```

### Testing New Migrations

```bash
# Test migrations without full deployment
python scripts/setup/deploy.py \
  --dry-run \
  --skip-backup
```

### Emergency Rollback

```bash
# Immediately rollback to previous state
python scripts/setup/deploy.py --rollback
```

## File Locations

- **Script**: `scripts/setup/deploy.py`
- **Tests**: `scripts/setup/tests/test_deploy.py`
- **Utilities**: `scripts/setup/utils/`
- **Backups**: `data/backups/`
- **Docker Compose**: `docker-compose.yml`
- **Environment**: `.env`
- **JWT Keys**: `secrets/jwt/`

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Docker logs: `docker-compose logs`
3. Run with `--dry-run` to diagnose issues
4. Check Codeberg issues or create a new one

## License

This script is part of PromptVault and is subject to the same Mozilla Public License v2.0.
