---
title: Skills
sidebar_position: 4
---

# Skills

A skill is a folder of instructions and helper files that an AI agent can load for a task. It always contains a `SKILL.md` file, and may also contain scripts, references and other files. PromptVault stores skills next to your prompts so you can organize, search, back up and export both in one place.

## What a skill is {#what-a-skill-is}

A skill is stored as a `.zip` archive. The `SKILL.md` file starts with a short header (the name and a description) followed by the instructions. PromptVault follows the open Agent Skills format.

In the vault list, a skill shows a **Skill** badge and a short description instead of a prompt body. Use the **Type** filter above the list to show only prompts or only skills.

## Importing a skill {#importing-a-skill}

1. Choose **Import skill** in the header.
2. Pick a `.zip` file. The `SKILL.md` can be at the top of the archive or inside one top-level folder.
3. Optionally add a category and tags, then choose **Import**.

The skill is saved in one step: if anything is wrong with the archive, nothing is stored. When the import works, the skill opens right away.

## Format warnings {#format-warnings}

PromptVault accepts skills even when they do not follow the format exactly. You then see a notice that lists each rule that was broken, for example a missing name, a name that is not lowercase with hyphens, a description over 1,024 characters, or a `SKILL.md` placed at the top of the archive instead of inside a folder. The warnings stay on the skill's detail view. They never block an import.

## Limits and rejected archives {#limits-and-rejected-archives}

An archive is rejected, and nothing is stored, when it:

- is not a valid zip file, or is encrypted;
- has no `SKILL.md` at its top or in a single top-level folder;
- contains a path that leaves the skill folder, a symbolic link, a duplicate path, or a file name that is not valid on common systems;
- goes over a limit on upload size (10 MB by default), unpacked size (50 MB), number of files (500), folder depth (10 levels) or the size of a single file (10 MB).

The message tells you which rule was broken and, where it applies, which entry caused it. Administrators can change the limits with the `SKILL_*` settings in the deployment guide.

## Browsing a skill {#browsing-a-skill}

The detail view shows the description, the rendered instructions and the list of files as a tree. Folders come first. You can move through the tree with the arrow keys, open folders with the right arrow and choose a file with Enter.

Text files are shown as read-only text. Binary files show their size and a download link. Nothing in a skill is ever run or shown as a web page, and `${CLAUDE_SKILL_DIR}` or similar markers stay as plain text.

## Downloading a skill {#downloading-a-skill}

**Download skill** gives you `<skill-name>.zip` with one folder inside, in the standard layout. Every file is identical to the one you imported. The archive name uses the skill identifier, so renaming the title does not change it. You can also download a single file from the viewer.

## Editing, replacing and deleting {#editing-replacing-and-deleting}

- **Edit details** changes the title, category, tags, note and favorite. The files are not touched, and no version history is created.
- **Replace files** uploads a new archive. The title, note, tags, category and favorite are kept; the description and identifier come from the new `SKILL.md`. If the new archive is rejected, the skill stays exactly as it was.
- **Delete skill** removes the skill and all of its files for good. This cannot be undone, so you are asked to confirm first.

## Search, backups and what skills do not do {#search-backups-and-what-skills-do-not-do}

Search finds a skill by its title, note and the text of its `SKILL.md`. It does not look inside scripts or other bundled files. Skills are included in full database backups and come back identical after a restore.

Skills are private to the person who imported them. They have no version history, no sharing and no placeholders, and bulk prompt export does not include them: export a skill from its own view instead.
