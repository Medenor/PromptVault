# PromptVault Scripts

Helper scripts for PromptVault deployment and management.

## Pre-Deployment Check

**Script**: `pre-deploy-check.sh`

Automated safety checklist before upgrading to a new version.

### Usage

```bash
cd /path/to/PromptVault
./scripts/pre-deploy-check.sh
```

### What it does

1. ✓ Verifies Docker and database connectivity
2. ✓ Counts current data (prompts, tags, etc.)
3. ✓ Creates automatic backup with timestamp
4. ✓ Verifies backup integrity
5. ✓ Checks JWT configuration
6. ✓ Reviews recent changes from CHANGELOG
7. ✓ Provides recovery instructions

### Output Example

```
========================================
PromptVault Pre-Deployment Checklist
========================================

Running checks...

Checking Docker status... ✓ Docker is running
Checking database connectivity... ✓ Database is accessible
Checking data volume... ✓ Found 20 prompts
Checking backup directory... ✓ Backup directory exists
Checking JWT keys... ✓ JWT keys present
Checking environment configuration... ✓ .env file exists

========================================
Creating backup before deployment...
========================================

Creating database backup...
✓ Backup created: data/backups/promptvault-pre-deploy-20251206_164200.sql.gz (125K)
Verifying backup integrity... ✓ Backup verified

========================================
Pre-Deployment Summary
========================================
✓ Checks Passed: 8
✓ All checks passed! Ready for deployment.

Next steps:
1. Review changes in docs/CHANGELOG.md
2. Run: docker-compose pull
3. Run: docker-compose up -d web
4. Monitor: docker-compose logs -f web
5. If issues, restore from: data/backups/promptvault-pre-deploy-20251206_164200.sql.gz
```

### Disaster Recovery

If deployment fails, restore from the backup:

```bash
# Stop application
docker-compose stop web

# Restore database
docker-compose exec -T db psql -U promptvault postgres -c "DROP DATABASE promptvault;"
docker-compose exec -T db psql -U promptvault postgres -c "CREATE DATABASE promptvault;"
gunzip -c data/backups/promptvault-pre-deploy-TIMESTAMP.sql.gz | \
  docker-compose exec -T db psql -U promptvault -d promptvault

# Restart
docker-compose up -d web
```

## Recommended Deployment Flow

```bash
# 1. Run pre-deployment checks
./scripts/pre-deploy-check.sh

# 2. Review changes
cat docs/CHANGELOG.md

# 3. Pull latest images
docker-compose pull

# 4. Deploy with zero-downtime
docker-compose up -d web

# 5. Monitor startup
docker-compose logs -f web

# 6. Verify application is healthy
curl http://localhost:8001/api/health

# 7. Test core functionality
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"admin","password":"your_password"}'
```

## Important Notes

- **Always backup before updating** - The pre-deploy script does this automatically
- **Test on staging first** - Never deploy directly to production without testing
- **Keep multiple backups** - Don't delete old backups immediately
- **Document migration steps** - Check CHANGELOG for breaking changes
- **Monitor logs** - Watch for errors during and after deployment

## Additional Resources

- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Changelog](../docs/CHANGELOG.md)
- [Troubleshooting](../docs/DEPLOYMENT.md#troubleshooting)
