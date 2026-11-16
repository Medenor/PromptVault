---
title: Update PromptVault
description: Safely update a self-hosted PromptVault installation.
---

# Update PromptVault

These steps apply to the Docker Compose setup described in [Installation](index.md). They update the `web` and `docs` services while keeping the database and its named volume in place.

## Before you start

1. Read the [release notes](../release-notes/index.md) for changes that affect your setup.
2. Make sure the host has enough free disk space for a database backup and new images.
3. Schedule a short maintenance window. Users may be unable to sign in during the restart.
4. Confirm you can access the server's project folder and the database container.

## 1. Back up the database

Create and check a compressed database dump before pulling or starting the update:

```bash
mkdir -p data/backups
docker compose exec -T db pg_dump -U promptvault -d promptvault \
  | gzip > "data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
gzip -t data/backups/promptvault-*.sql.gz
```

Check that the newest file is non-empty and that `gzip -t` exits without an error. Keep the backup somewhere safe. Do not continue if the dump failed.

## 2. Download and rebuild

From the PromptVault project folder, get the version you intend to install. Use the release tag from the release notes if you do not want the latest development version:

```bash
git fetch --tags
git checkout <release-tag>
```

Then rebuild and restart the application and documentation services:

```bash
docker compose build web docs
docker compose up -d db redis
docker compose up -d web docs
```

The database and Redis services should be healthy before the application starts. Compose waits for their health checks as configured in the project file.

## 3. Apply database migrations

Run the migration command using the updated web image:

```bash
docker compose exec -T web alembic upgrade head
docker compose exec -T web alembic current
```

The second command should report the current revision. If the migration command fails, stop here and follow [Troubleshooting](../troubleshooting/index.md).

## 4. Check the update

```bash
curl --fail http://localhost:8001/api/health
```

The health endpoint should return a successful response. Open PromptVault in a browser, sign in, and check that your prompts are present. Open the docs service too if you use it (default: `http://localhost:7876`).

## If something goes wrong

Check the service output first:

```bash
docker compose logs --tail=100 web docs
```

A cache-less rebuild can expose a missing Python dependency if a dependency version is not pinned correctly. For example, the SQLAlchemy version constraint fixed in release notes associated with [issue #94](https://codeberg.org/medenor/promptvault/issues/94) prevents a known `psycopg` installation problem. Use the [Troubleshooting](../troubleshooting/index.md) page for other symptoms.

### Restore the database backup

If the new version cannot be used, switch back to the previous application release and restore the verified dump. Restoring replaces the current database contents, so preserve a copy of the current state first if it contains new data:

```bash
docker compose stop web
# Copy the backup file to the server if needed, then:
docker compose exec -T db psql -U promptvault -d promptvault \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
gzip -dc data/backups/<backup-file>.sql.gz \
  | docker compose exec -T db psql -U promptvault -d promptvault
```

Start the previous release's `web` and `docs` services after the restore. For help with a failed restore, see [Troubleshooting](../troubleshooting/index.md).
