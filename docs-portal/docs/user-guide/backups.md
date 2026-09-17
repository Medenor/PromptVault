---
title: Backups
sidebar_position: 2
---

# Backups

PromptVault includes a backup and restore system covering scheduling, integrity verification, encryption, and optional cloud storage.

## Scheduled Backups

Administrators can configure automatic backups with a daily, weekly, or monthly cadence at a chosen time. The schedule can be enabled or disabled at any point. If a scheduled backup would start while another backup is still running, the new trigger is skipped rather than run concurrently, and the skip is logged.

The first backup for an installation (or the first after a prior backup becomes unusable) is always a full backup; subsequent scheduled backups are incremental, storing only what changed since the last full backup to keep storage usage down.

## Integrity Verification

Every backup's contents are validated after creation, and the result is recorded. A checksum is stored alongside each backup's metadata so its integrity can be re-checked later. You can also manually trigger an integrity test on any existing backup at any time from the backup management page — useful before you actually need to rely on a restore.

## Encryption

Backups can be encrypted with a key you provide before they're written to storage; PromptVault never stores encryption keys in plain text. Key rotation is supported — backups already encrypted under a previous key remain accessible during the transition to a new one.

## Cloud Storage

You can configure an S3-compatible provider, Google Drive, or Dropbox as a backup destination from the admin UI. A local copy is always retained even when cloud upload is configured, and you can restore directly from cloud storage, not just from local backups.

Cloud provider credentials (access key / secret key) are encrypted at rest using `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` — see [Configuration](../configuration/index.md#backups). This variable is required before you can add a cloud provider.

## Restore Preview and Selective Restore

Before a restore is applied, PromptVault shows a preview diff of exactly what will change — prompts to be added, updated, or deleted — rather than restoring blind. From that preview you can also select a subset of prompts to restore instead of restoring the entire backup.

## Retention

A configurable retention period (in days) determines when older backups become eligible for cleanup, so backup storage doesn't grow unbounded.

## Practical Notes

- Keep `PROMPTVAULT_DATA_DIR` distinct per environment (dev/staging/prod) — sharing a data directory across environments can make scheduled backups and restores collide with each other, since backups are stored relative to that directory.
- Test a restore occasionally, not just a backup — the integrity check confirms the backup file is readable, but a full restore-preview run confirms the data inside it is actually what you expect.
