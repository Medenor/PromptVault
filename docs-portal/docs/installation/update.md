---
title: Update PromptVault
description: Safely update a self-hosted PromptVault installation.
---

# Update PromptVault

Use these steps to update the Docker Compose installation described in [Installation](index.md). The database keeps its stored data while you rebuild the `web` and `docs` services.

## Before you start

1. Read the [release notes](../release-notes/index.md) for changes that affect your setup.
2. Check that the server has enough free disk space for a database backup and new images.
3. Schedule a short maintenance window. Users may be unable to sign in while the app restarts.
4. Make sure you can access the PromptVault project folder and database container.

## 1. Back up the database

Create and verify a compressed database backup before you download or start the update. Run these commands from the PromptVault project folder:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

The last command must finish without an error. Check that the backup file is not empty, then copy it to a safe location outside the server. Do not continue if the backup failed.

## 2. Download and rebuild

From the PromptVault project folder, choose the release you want to install. A release tag is the label for a published version. Use one listed in the release notes:

```bash
git fetch --tags
git checkout <RELEASE_TAG>
```

Rebuild and start the application and documentation services:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

The project is configured to start `web` only after the database and Redis report that they are ready.

## 3. Apply database updates

A database migration updates the database structure for the new PromptVault version. Run the migration, then check which migration version is active:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

The second command should show the current migration version. If the migration command fails, stop here and follow [Troubleshooting](../troubleshooting/index.md).

## 4. Check the update

```bash
curl --fail http://localhost:8001/api/health
```

The health check should return a successful response. Open PromptVault in a browser, sign in, and check that your prompts are present. If you use the docs service, open it too (default address: `http://localhost:7876`).

## If something goes wrong

Check the service logs for an error message:

```bash
docker compose logs --tail=100 web docs
```

If rebuilding without cache fails with `No module named 'psycopg'`, use PromptVault 1.13.1 or later; that release fixed the dependency issue described in [issue #94](https://codeberg.org/medenor/promptvault/issues/94). For other errors, follow [Troubleshooting](../troubleshooting/index.md).

### Return to the previous version

These steps restore the database backup you made before the update and return the app and docs to the previous release. Restoring replaces the current database with the earlier backup. Any prompts or other changes made since that backup will be lost unless you save the current database first.

If you created or changed prompts after updating, save the current database before restoring:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker compose exec -T db pg_dump -U promptvault -d promptvault | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

Then stop the app, select the previous release tag from your release notes, and rebuild its images:

```bash
docker compose stop web
git fetch --tags
git checkout <PREVIOUS_RELEASE_TAG>
docker compose build web docs
```

Restore the verified pre-update backup. Replace `<BACKUP_FILE>` with the backup filename you created in step 1. The first command deletes the current database contents before loading the backup:

```bash
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
set -euo pipefail
gzip -dc "data/backups/<BACKUP_FILE>" \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Start the previous release and verify that PromptVault works:

```bash
docker compose up -d web docs
curl --fail http://localhost:8001/api/health
```

Sign in and check that your prompts are present. If restoration or startup fails, stop and follow [Troubleshooting](../troubleshooting/index.md).
