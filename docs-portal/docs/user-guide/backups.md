---
title: Backups
sidebar_position: 2
---

# Backups

PromptVault includes backup and restore features for scheduled copies, integrity verification, encryption, and optional cloud storage. A backup helps you recover data; an export is not a substitute when you need to preserve sharing permissions.

## Scheduled Backups

Administrators configure automatic backups from the backup management page. Choose a daily, weekly, or monthly schedule and a time, then enable the schedule. If a scheduled backup would start while another backup is still running, PromptVault skips the new run and records that decision.

The first backup for an installation (or the first after a prior backup becomes unusable) is always a full backup; subsequent scheduled backups are incremental, storing only what changed since the last full backup to keep storage usage down.

## Integrity Verification

Every backup's contents are validated after creation, and the result is recorded. A checksum is stored alongside each backup's metadata so its integrity can be re-checked later. You can also manually trigger an integrity test on any existing backup at any time from the backup management page — useful before you actually need to rely on a restore.

## Encryption

Backups can be encrypted with a key you provide before they're written to storage; PromptVault never stores encryption keys in plain text. Key rotation is supported — backups already encrypted under a previous key remain accessible during the transition to a new one.

## Cloud Storage

From the backup management page, configure an S3-compatible provider, Google Drive, or Dropbox as a destination. PromptVault retains a local copy even when cloud upload is configured, and you can restore directly from cloud storage.

Cloud provider credentials (access key / secret key) are encrypted at rest using `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` — see [Configuration](../configuration/index.md#backups). This variable is required before you can add a cloud provider.

## Restore Preview and Selective Restore

Before applying a restore, review the preview: it lists prompts that will be added, updated, or deleted. Select only the prompts you intend to restore, or restore the complete backup. Do not apply the restore until you understand the listed changes.

## Retention

A configurable retention period (in days) determines when older backups become eligible for cleanup, so backup storage doesn't grow unbounded.

## Practical Notes

- Keep `PROMPTVAULT_DATA_DIR` distinct per environment (dev/staging/prod) — sharing a data directory across environments can make scheduled backups and restores collide with each other, since backups are stored relative to that directory.
- Test a restore occasionally, not only a backup. The integrity check confirms that the backup file is readable; a restore preview confirms that it contains the data you expect.
