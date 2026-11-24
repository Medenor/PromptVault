---
title: Update PromptVault
description: Safely update a self-hosted PromptVault installation.
---

# Update PromptVault

Use these steps to update the Docker Compose installation described in [Installation](index.md). The database keeps its stored data while you rebuild the `web` and `docs` services.

If your production settings are in a separate `.env.production` file (recommended, see [Set up a production environment](production-setup.md)), tell Docker Compose to use it once before you start. Every `docker-compose` command in the same terminal window then uses it:

```bash
export COMPOSE_ENV_FILES=.env.production
```

Run the commands on this page in that terminal window. Without this setting, Docker Compose reads `.env` and your development values replace the production ones. This needs Docker Compose 2.24 or later; with an older version, see [Set up a production environment](production-setup.md#use-a-separate-environment-file).

## Before you start {#before-you-start}

1. Read the [release notes](../release-notes/index.md) and `CHANGELOG.md` for breaking changes and migration notes.
2. Check that the server has enough free disk space for a database backup and new images.
3. Test the update on a staging installation first, if one is available.
4. Schedule a short maintenance window. Users may be unable to sign in while the app restarts.
5. Make sure you can access the PromptVault project folder and database container.

## 1. Back up the database {#1-back-up-the-database}

Create a compressed database backup and check that the archive is intact before you download or start the update. Run these commands from the PromptVault project folder:

```bash
set -euo pipefail
mkdir -p data/backups
BACKUP_FILE="data/backups/promptvault-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$BACKUP_FILE"
gzip -t "$BACKUP_FILE"
```

The last command must finish without an error. Check that the backup file is not empty. Keep it in `data/backups` for a possible restore, and copy a second copy to a safe location outside the server. Do not continue if the backup failed. The `gzip -t` check shows that the file is not damaged. It does not test a restore.

Next, tag the image your production container runs now, so you can return to it without rebuilding. The *image* is the packaged copy of PromptVault that the container runs. Use the container's image ID, not `:latest`: the `:latest` tag on your machine may already point at a newer build.

```bash
docker tag "$(docker inspect promptvault-web --format '{{.Image}}')" promptvault-web:pre-update
docker run --rm --entrypoint python promptvault-web:pre-update -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

The second command must print the version you are running now. If it prints a different version, do not continue: check the container name with `docker-compose ps`, then run the first command again.

## 2. Download and rebuild {#2-download-and-rebuild}

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

## 3. Apply database updates {#3-apply-database-updates}

A database migration updates the database structure for the new PromptVault version. Run the migration, then check which migration version is active:

```bash
docker-compose exec -T web alembic upgrade head
docker-compose exec -T web alembic current
```

Run this migration only after `web` has started. The second command should show the current migration version. If the migration command fails, stop here and follow [Troubleshooting](../troubleshooting/index.md).

## 4. Check the update {#4-check-the-update}

```bash
# Recent log lines: look for errors
docker-compose logs web | head -50
# Health check: must succeed
curl --fail http://localhost:8001/api/health
# Number of prompts: must match what you expect
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
# Version now running: must be the new version
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
# Settings in use: production needs ENVIRONMENT=production and DISABLE_RATE_LIMITING=false
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

The health response does not include the version, so use the version command to confirm the update. Open PromptVault in a browser, sign in, and check that your prompts are present. If you use the docs service, open it too (default address: `http://localhost:7876`).

## If something goes wrong {#if-something-goes-wrong}

Check the service logs for an error message:

```bash
docker-compose logs --tail=100 web docs
```

If the `web` container keeps restarting with `No module named 'psycopg'` on PostgreSQL, see [Troubleshooting](../troubleshooting/index.md#psycopg-missing). For other errors, follow [Troubleshooting](../troubleshooting/index.md).

### Return to the previous version {#return-to-the-previous-version}

Go back to the image you tagged in step 1 (`promptvault-web:pre-update`). Follow these steps in order.

**1. Start the previous image.**

```bash
docker tag promptvault-web:pre-update promptvault-web:latest
docker-compose up -d --no-build web
docker-compose logs web --tail=20
docker exec promptvault-web python -c "import importlib.metadata as m; print(m.version('promptvault'))"
```

The last command must print the previous version. Check the health endpoint (`curl --fail http://localhost:8001/api/health`), sign in, and check that your prompts are present. If everything works and the update ran no database migrations, you are done. The "Upgrade" line in the [release notes](../release-notes/index.md) for the version you installed says whether it ran migrations; many releases ran none. If it did, continue with step 2.

**2. Stop the app.** Do this only if you restore the database.

```bash
docker-compose stop web
```

**3. Save the current database (optional).**

If you created or changed prompts after updating, save the current database before restoring:

```bash
set -euo pipefail
CURRENT_BACKUP="data/backups/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz"
docker-compose exec -T db pg_dump -U promptvault -d promptvault --verbose | gzip > "$CURRENT_BACKUP"
gzip -t "$CURRENT_BACKUP"
```

**4. Restore the backup.** The restore replaces the current database, so prompts and other changes made since the backup are lost unless you saved them in step 3.

Restore the verified pre-update backup. Replace `<BACKUP_FILE>` with the backup filename from step 1, without the `data/backups/` folder prefix. These commands delete and recreate the database before loading the backup:

```bash
set -euo pipefail
docker-compose exec -T db psql -U promptvault postgres -c 'DROP DATABASE promptvault;'
docker-compose exec -T db psql -U promptvault postgres -c 'CREATE DATABASE promptvault;'
gzip -dc "data/backups/<BACKUP_FILE>" \
  | docker-compose exec -T db psql -U promptvault -d promptvault
```

**5. Start the previous image again and check it.**

```bash
docker-compose up -d --no-build web
docker-compose logs web --tail=20
curl --fail http://localhost:8001/api/health
docker-compose exec -T db psql -U promptvault -d promptvault -c "SELECT COUNT(*) FROM prompts;"
```

Sign in and check that your prompts are present. If restoration or startup fails, stop and follow [Troubleshooting](../troubleshooting/index.md).

**If you did not tag an image in step 1,** check out the previous release tag (`git fetch --tags`, then `git checkout <PREVIOUS_RELEASE_TAG>`) and run `docker-compose build` without `--no-cache`. Docker may reuse cached dependency layers, but nothing guarantees it, so confirm the version and that the app starts before you rely on it.

Do not return by checking out the old release and rebuilding with `--no-cache`. A build installs its dependencies again, so the result can differ from the image you ran before, and some releases cannot be rebuilt at all: an image built from the 1.16.0 source, for example, crashes on PostgreSQL.
