---
title: Sharing Prompts
sidebar_position: 3
---

# Sharing Prompts

PromptVault supports sharing individual prompts with specific teammates, with fine-grained read/edit access control.

## Granting Access {#granting-access}

From a prompt's Share modal, you can grant a teammate one of two access levels:

- **Read**: view the prompt and its version history.
- **Edit**: everything Read allows, plus editing the prompt's content, category, and tags, and reverting to a previous version.

Neither level allows deleting the prompt, re-sharing it with others, toggling favorite status, or transferring ownership — those remain owner-only actions. The recipient picker searches active users by username or email prefix, but never displays or exposes email addresses in the results.

## Revoking Access {#revoking-access}

Access can be revoked by the prompt owner at any time from the same Share modal.

## Finding Shared Prompts {#finding-shared-prompts}

A "Shared with me" filter shows prompts other people have shared with you. Shared prompts carry a distinct "Shared" badge so you can tell an explicit share apart from a prompt that's simply visible to you by default.

## Legacy Public Prompts {#legacy-public-prompts}

Prompts created before sharing was introduced are grandfathered as **"Public (legacy)"** — visible to every authenticated user, not just people explicitly granted access — and are badged differently from an explicit share. An owner or admin can make a legacy-public prompt private via a "Make private" action; this is a one-way transition with no way to re-publish it as legacy-public afterward, so treat it as a deliberate decision rather than a display toggle.

Prompts created after sharing was introduced default to **private**: visible only to their owner, admins, and anyone explicitly granted access.

## Export/Import and Sharing {#exportimport-and-sharing}

Sharing grants and the legacy-public flag are **not** included in exported prompts (CSV/Markdown/JSON) — they're access-control state tied to this specific instance's user accounts, not portable prompt content. Re-importing an exported file creates plain private prompts with no grants restored. If you need sharing state preserved, use a full database backup/restore instead of export/import.
