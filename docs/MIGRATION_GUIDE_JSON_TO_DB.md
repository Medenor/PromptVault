# PromptVault Migration Guide: JSON to Database

This guide provides step-by-step instructions for migrating PromptVault from JSON file storage to a database backend (SQLite or PostgreSQL).

## Table of Contents

- [Overview](#overview)
- [Before You Begin](#before-you-begin)
- [Migration Paths](#migration-paths)
- [Step-by-Step Migration](#step-by-step-migration)
- [Post-Migration](#post-migration)
- [Rollback Procedures](#rollback-procedures)
- [Troubleshooting](#troubleshooting)

---

## Overview

### What Changes

**Storage:**

- **Before:** JSON file (`data/prompts.json`)
- **After:** Relational database (SQLite or PostgreSQL)

**Data Structure:**

- Prompts stored in normalized tables
- Version history in separate table
- Categories and tags with referential integrity
- Automatic timestamps and metadata

**Benefits:**

- ✅ Faster queries and searches
- ✅ ACID transactions
- ✅ Better data integrity
- ✅ Concurrent access support
- ✅ Advanced querying capabilities
- ✅ Scalability for large datasets

### What Stays the Same

- **API Interface:** All endpoints remain unchanged
- **Data Format:** API responses use same JSON structure
- **Features:** All existing features continue to work
- **Backward Compatibility:** Old code continues to function

---

## Before You Begin

### Prerequisites

1. **Backup Your Data**

   ```bash
   # Create backup directory
   mkdir -p backups

   # Backup JSON file
   cp data/prompts.json backups/prompts_$(date +%Y%m%d_%H%M%S).json

   # Backup entire data directory
   tar -czf backups/data_backup_$(date +%Y%m%d_%H%M%S).tar.gz data/
   ```

2. **Verify Dependencies**

   ```bash
   # Check Python version (3.11+ required)
   python --version

   # Verify dependencies installed
   pip list | grep -E 'sqlalchemy|alembic|psycopg2'
   ```

3. **Test Environment**
   ```bash
   # Test on copy first
   cp -r PromptVault PromptVault_test
   cd PromptVault_test
   ```

### System Requirements

**Minimum:**

- Python 3.11+
- 100MB disk space (SQLite)
- 512MB RAM

**Recommended:**

- Python 3.11+
- 1GB disk space (PostgreSQL)
- 2GB RAM
- PostgreSQL 15+

---

## Migration Paths

### Path 1: SQLite (Recommended for Small to Medium Datasets)

**Best for:**

- Development and testing
- Single-user deployments
- < 10,000 prompts
- Simple setup

**Pros:**

- No additional software required
- Easy to backup (single file)
- Fast for moderate datasets
- Zero configuration

**Cons:**

- Limited concurrent writes
- No network access
- Single file can corrupt

### Path 2: PostgreSQL (Recommended for Production)

**Best for:**

- Production deployments
- Multi-user access
- > 10,000 prompts
- High availability requirements

**Pros:**

- Excellent performance at scale
- Concurrent access
- Advanced features (FTS, JSON queries)
- Robust backup/restore

**Cons:**

- Requires PostgreSQL server
- More complex setup
- Additional maintenance

---

## Step-by-Step Migration

### Migration Path 1: SQLite

#### Step 1: Install Dependencies

```bash
# Ensure all dependencies are installed
pip install -e .
```

#### Step 2: Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env
nano .env
```

Set the following:

```env
DATABASE_URL=sqlite:///./data/promptvault.db
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### Step 3: Initialize Database

```bash
# Create database and run migrations
alembic upgrade head

# Verify tables created
sqlite3 data/promptvault.db ".tables"
```

Expected output:

```
alembic_version  categories       prompt_tags      prompts          tags
backups          prompt_versions  users
```

#### Step 4: Run Migration Script

```bash
# Dry run (verify without changes)
python scripts/migrate_json_to_db.py --source data/prompts_data.json --dry-run

# Actual migration
python scripts/migrate_json_to_db.py --source data/prompts_data.json
```

Expected output:

```
Starting migration from JSON to database...
Loading JSON data from data/prompts.json...
Found 150 prompts to migrate

Migrating prompts...
✓ Prompt 1: "Example Prompt" migrated
✓ Prompt 2: "Another Prompt" migrated
...
✓ 150/150 prompts migrated

Migration Statistics:
- Prompts: 150
- Categories: 12
- Tags: 45
- Versions: 150 (initial versions)

Migration completed successfully!
```

#### Step 5: Verify Migration

```bash
# Test database operations
python scripts/test_db_operations.py

# Check prompt count
python -c "
from src.services.prompt_data_service_db import PromptDataService
svc = PromptDataService()
print(f'Migrated prompts: {len(svc.load_prompts())}')
"

# Compare with JSON
python -c "
import json
with open('data/prompts.json') as f:
    json_data = json.load(f)
print(f'JSON prompts: {len(json_data[\"prompts\"])}')
"
```

#### Step 6: Update Application

No code changes needed! The database-backed service maintains full backward compatibility.

Optionally, update imports to explicitly use database service:

```python
# Before (auto-detects)
from src.services.prompt_data_service import PromptDataService

# After (explicit)
from src.services.prompt_data_service_db import PromptDataService
```

#### Step 7: Test Application

```bash
# Start application
uvicorn src.web.app:app --reload

# Test in another terminal
curl http://localhost:8003/api/prompts
curl http://localhost:8003/api/categories
curl http://localhost:8003/api/tags
```

---

### Migration Path 2: PostgreSQL

#### Step 1: Install PostgreSQL

**Ubuntu/Debian:**

```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**

```bash
brew install postgresql@15
brew services start postgresql@15
```

**Docker:**

```bash
docker run -d \
  --name promptvault-db \
  -e POSTGRES_DB=promptvault \
  -e POSTGRES_USER=promptvault \
  -e POSTGRES_PASSWORD=secure_password \
  -v postgres_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine
```

#### Step 2: Create Database

```bash
# Connect as postgres user
sudo -u postgres psql

# Run SQL commands
CREATE DATABASE promptvault;
CREATE USER promptvault WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE promptvault TO promptvault;
\q
```

#### Step 3: Install Python PostgreSQL Driver

```bash
# Install psycopg2
pip install psycopg2-binary
```

#### Step 4: Configure Environment

```bash
# Create .env file
cp .env.example .env

# Edit .env
nano .env
```

Set the following:

```env
DATABASE_URL=postgresql://promptvault:secure_password@localhost:5432/promptvault
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO=false
ENVIRONMENT=production
LOG_LEVEL=INFO
```

#### Step 5: Initialize Database

```bash
# Run migrations
alembic upgrade head

# Verify tables
psql -U promptvault -d promptvault -c "\dt"
```

#### Step 6: Run Migration Script

```bash
# Dry run
python scripts/migrate_json_to_db.py --dry-run --verbose

# Actual migration
python scripts/migrate_json_to_db.py --verbose
```

#### Step 7: Verify Migration

```bash
# Check record counts
psql -U promptvault -d promptvault << EOF
SELECT 'Prompts' AS table_name, COUNT(*) FROM prompts
UNION ALL
SELECT 'Categories', COUNT(*) FROM categories
UNION ALL
SELECT 'Tags', COUNT(*) FROM tags
UNION ALL
SELECT 'Versions', COUNT(*) FROM prompt_versions;
EOF

# Test database operations
python scripts/test_db_operations.py
```

#### Step 8: Optimize PostgreSQL

```bash
# Connect to database
psql -U promptvault -d promptvault

# Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_prompts_title ON prompts(title);
CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category_id);
CREATE INDEX IF NOT EXISTS idx_prompts_favorite ON prompts(favorite);
CREATE INDEX IF NOT EXISTS idx_versions_prompt ON prompt_versions(prompt_id);

# Analyze tables
ANALYZE prompts;
ANALYZE categories;
ANALYZE tags;
ANALYZE prompt_versions;

# Exit
\q
```

---

## Post-Migration

### 1. Verify Data Integrity

```bash
# Run comprehensive tests
python -m pytest tests/test_db_service_layer.py -v

# Check version history preserved
python -c "
from src.services.prompt_data_service_db import PromptDataService
svc = PromptDataService()
prompts = svc.load_prompts()
for pid in list(prompts.keys())[:5]:
    versions = svc.get_prompt_versions(pid)
    print(f'Prompt {pid}: {len(versions)} versions')
"
```

### 2. Performance Testing

```bash
# Test search performance
python -c "
import time
from src.services.prompt_data_service_db import PromptDataService
svc = PromptDataService()

start = time.time()
prompts = svc.load_prompts()
duration = time.time() - start
print(f'Load all prompts: {duration:.3f}s ({len(prompts)} prompts)')

# Test search
start = time.time()
# Perform search
duration = time.time() - start
print(f'Search performance: {duration:.3f}s')
"
```

### 3. Setup Automated Backups

**SQLite:**

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * cp /path/to/data/promptvault.db /path/to/backups/promptvault_$(date +\%Y\%m\%d).db
```

**PostgreSQL:**

```bash
# Create backup script
cat > backup_postgres.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U promptvault promptvault > "$BACKUP_DIR/promptvault_$DATE.sql"
# Keep only last 30 days
find "$BACKUP_DIR" -name "promptvault_*.sql" -mtime +30 -delete
EOF

chmod +x backup_postgres.sh

# Add to crontab
0 2 * * * /path/to/backup_postgres.sh
```

### 4. Monitor Performance

**Enable query logging:**

```env
DB_ECHO=true
LOG_LEVEL=DEBUG
```

**PostgreSQL slow query log:**

```sql
ALTER DATABASE promptvault SET log_min_duration_statement = 1000;
```

### 5. Cleanup (Optional)

After verifying migration success:

```bash
# Archive old JSON file (don't delete immediately!)
mv data/prompts.json data/prompts.json.archive

# Or move to backups
mv data/prompts.json backups/prompts_pre_migration.json
```

**Important:** Keep the JSON file for at least 30 days as a safety backup!

---

## Rollback Procedures

If you need to rollback to JSON:

### Option 1: Restore from Backup

```bash
# Stop application
pkill -f uvicorn

# Restore JSON backup
cp backups/prompts_YYYYMMDD_HHMMSS.json data/prompts.json

# Revert environment
nano .env
# Remove DATABASE_URL or set to empty

# Restart application with old service
# (Application should auto-detect JSON)
uvicorn src.web.app:app --reload
```

### Option 2: Export from Database

```bash
# Export database to JSON
python scripts/export_db_to_json.py --output data/prompts_exported.json

# Verify export
python -c "
import json
with open('data/prompts_exported.json') as f:
    data = json.load(f)
print(f'Exported {len(data[\"prompts\"])} prompts')
"

# Replace current JSON
mv data/prompts.json data/prompts.json.old
mv data/prompts_exported.json data/prompts.json
```

### Option 3: Database Rollback

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to base
alembic downgrade base

# Remove database
rm data/promptvault.db  # SQLite
# OR
dropdb -U promptvault promptvault  # PostgreSQL
```

---

## Troubleshooting

### Issue 1: Migration Script Fails

**Error:** `FileNotFoundError: data/prompts.json`

**Solution:**

```bash
# Verify JSON file exists
ls -la data/prompts.json

# If missing, restore from backup
cp backups/prompts_*.json data/prompts.json
```

---

**Error:** `IntegrityError: UNIQUE constraint failed`

**Solution:**

```bash
# Clear database and retry
rm data/promptvault.db
alembic upgrade head
python scripts/migrate_json_to_db.py
```

---

**Error:** `KeyError: 'prompts'`

**Solution:** JSON file format is invalid. Check structure:

```bash
# Verify JSON structure
python -c "
import json
with open('data/prompts.json') as f:
    data = json.load(f)
    print('Keys:', list(data.keys()))
    print('Expected: prompts, next_id')
"
```

### Issue 2: Missing Data After Migration

**Problem:** Some prompts missing after migration

**Solution:**

```bash
# Compare counts
echo "JSON count:"
python -c "import json; print(len(json.load(open('data/prompts.json'))['prompts']))"

echo "Database count:"
sqlite3 data/promptvault.db "SELECT COUNT(*) FROM prompts;"

# Check migration logs
python scripts/migrate_json_to_db.py --verbose 2>&1 | tee migration.log
grep -i error migration.log
```

### Issue 3: Performance Degradation

**Problem:** Database queries slower than JSON

**SQLite Solutions:**

```bash
# Analyze and optimize
sqlite3 data/promptvault.db << EOF
ANALYZE;
VACUUM;
PRAGMA optimize;
EOF
```

**PostgreSQL Solutions:**

```sql
-- Add indexes
CREATE INDEX idx_prompts_search ON prompts USING GIN(to_tsvector('english', title || ' ' || prompt));

-- Update statistics
ANALYZE prompts;

-- Check query plans
EXPLAIN ANALYZE SELECT * FROM prompts WHERE title LIKE '%search%';
```

### Issue 4: Database Connection Errors

**Error:** `could not connect to server: Connection refused`

**Solutions:**

```bash
# Check PostgreSQL is running
systemctl status postgresql
# OR
pg_isready

# Verify connection string
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1;"
```

---

**Error:** `password authentication failed`

**Solution:**

```bash
# Reset password
sudo -u postgres psql -c "ALTER USER promptvault WITH PASSWORD 'new_password';"

# Update .env
nano .env
# Update DATABASE_URL with new password
```

### Issue 5: Version History Not Preserved

**Problem:** Version history missing or incorrect

**Solution:**

```bash
# Check version count
sqlite3 data/promptvault.db "SELECT prompt_id, COUNT(*) FROM prompt_versions GROUP BY prompt_id;"

# Verify migration preserved versions
python -c "
from src.services.prompt_data_service_db import PromptDataService
import json

# Load JSON
with open('data/prompts.json') as f:
    json_data = json.load(f)

# Load DB
svc = PromptDataService()

# Compare version counts
for pid in list(json_data['prompts'].keys())[:10]:
    json_versions = len(json_data['prompts'][pid]['versions'])
    db_versions = len(svc.get_prompt_versions(int(pid)))
    print(f'Prompt {pid}: JSON={json_versions}, DB={db_versions}')
"
```

---

## Migration Checklist

Use this checklist to ensure smooth migration:

### Pre-Migration

- [ ] Backup JSON file to multiple locations
- [ ] Backup entire data directory
- [ ] Test migration on copy of data first
- [ ] Verify dependencies installed
- [ ] Stop application during migration
- [ ] Document current prompt count
- [ ] Note any custom modifications

### During Migration

- [ ] Configure DATABASE_URL correctly
- [ ] Run `alembic upgrade head`
- [ ] Verify all tables created
- [ ] Run migration script with `--dry-run` first
- [ ] Run actual migration with `--verbose`
- [ ] Monitor for errors in output
- [ ] Verify migration statistics

### Post-Migration

- [ ] Compare prompt counts (JSON vs DB)
- [ ] Test all API endpoints
- [ ] Verify search functionality
- [ ] Check version history preserved
- [ ] Test category and tag operations
- [ ] Verify backup system works
- [ ] Test restore procedure
- [ ] Monitor performance
- [ ] Setup automated backups
- [ ] Keep JSON backup for 30 days
- [ ] Update documentation
- [ ] Notify users of migration

---

## Additional Resources

- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Database Specification](SPECS/SPEC_DATABASE.md) - Technical database design
- [Phase 7 Documentation](phase7_service_layer_migration.md) - Service layer details
- [Phase 8 Documentation](phase8_backup_system_integration.md) - Backup system
- [Phase 9 Documentation](phase9_test_infrastructure.md) - Testing guide

---

## Support

If you encounter issues not covered in this guide:

1. Check [GitHub Issues](https://github.com/your-repo/PromptVault/issues)
2. Review migration logs: `migration.log`
3. Enable debug logging: `LOG_LEVEL=DEBUG`
4. Run tests: `pytest tests/ -v`
5. Create new issue with:
   - Error message
   - Migration logs
   - System info (`python --version`, `uname -a`)
   - Database type and version
