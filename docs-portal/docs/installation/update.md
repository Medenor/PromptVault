---
title: Update PromptVault
description: Safely update a self-hosted PromptVault installation.
---

# Update PromptVault

Use these steps to update the Docker Compose installation described in [Installation](index.md). The database keeps its stored data while you rebuild the `web` and `docs` services.

## Before you start

1. Read the [release notes](../release-notes/index.md) and `CHANGELOG.md` for breaking changes and migration notes.
2. Check that the server has enough free disk space for a database backup and new images.
3. Test the update on a staging installation first, if one is available.
4. Schedule a short maintenance window. Users may be unable to sign in while the app restarts.
5. Make sure you can access the PromptVault project folder and database container.

## 1. Back up the database

Create and verify a compressed database backup before you download or start the update. Run these commands from the PromptVault project folder:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

The last command must finish without an error. Check that the backup file is not empty. Keep it in `data/backups` for a possible restore, and copy a second copy to a safe location outside the server. Do not continue if the backup failed.

## 2. Download and rebuild

From the PromptVault project folder, update to the latest code on `main`. If you want a specific stable release, use its tag instead.

```bash
git checkout main
git pull origin main
```

To install a specific published release instead, fetch and check out its tag:

```bash
git fetch --tags
git checkout <RELEASE_TAG>
```

Build the services without using cached layers, then replace the web container. Keep the database and Redis running while you do this:

```bash
docker-compose build --no-cache
docker-compose stop web
docker-compose rm web
docker-compose up -d db redis
sleep 15
docker-compose up -d web docs
```

Wait 15 seconds after starting the database and Redis so the database can finish initializing. The project also waits for database and Redis health checks before starting `web`.

## 3. Apply database updates

A database migration updates the database structure for the new PromptVault version. Run the migration, then check which migration version is active:

```bash
docker-compose exec -T web alembic upgrade head
docker-compose exec -T web alembic current
```

Run this migration only after `web` has started. The second command should show the current migration version. If the migration command fails, stop here and follow [Troubleshooting](../troubleshooting/index.md).

## 4. Check the update

```bash
docker-compose logs web | head -50
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

The health check should return a successful response. Open PromptVault in a browser, sign in, and check that your prompts are present. If you use the docs service, open it too (default address: `http://localhost:7876`).

## If something goes wrong

Check the service logs for an error message:

```bash
docker-compose logs --tail=100 web docs
```

If rebuilding without cache fails with `No module named 'psycopg'`, use PromptVault 1.13.1 or later; that release fixed the dependency issue described in [issue #94](https://codeberg.org/medenor/promptvault/issues/94). For other errors, follow [Troubleshooting](../troubleshooting/index.md).

### Return to the previous version

These steps restore the database backup you made before the update and return the app and docs to the previous release. Restoring replaces the current database with the earlier backup. Any prompts or other changes made since that backup will be lost unless you save the current database first.

Stop the app before continuing:

```bash
docker-compose stop web
```

If you created or changed prompts after updating, save the current database before restoring:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Restore the verified pre-update backup. Replace `<BACKUP_FILE>` with the backup filename from step 1, without the `data/backups/` folder prefix. These commands delete and recreate the database before loading the backup:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<BACKUP_FILE>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

Then select the previous release and rebuild its images without using cached layers:

```bash
git fetch --tags
git checkout <PREVIOUS_RELEASE_TAG>
docker-compose build --no-cache
```

Start the previous release and check the logs and health endpoint:

```bash
docker-compose up -d web docs
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Sign in and check that your prompts are present. If restoration or startup fails, stop and follow [Troubleshooting](../troubleshooting/index.md).
