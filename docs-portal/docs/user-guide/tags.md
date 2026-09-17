---
title: Tags
sidebar_position: 3
---

# Tags

Unlike categories, a prompt can carry many tags at once, making tags better suited to cross-cutting labels — like `client-facing` or `needs-review` — than the single broad grouping a category provides.

## Creating and Assigning Tags

A tag has a name, an optional description, an optional color, and can optionally have a parent tag, letting you build a simple tag hierarchy (a tag cannot be its own parent, and cycles are rejected). Tags are assigned to a prompt when creating or editing it; typing a tag name that doesn't exist yet creates it.

## Filtering by Tag

The main prompt grid can be filtered by tag to narrow the view down to prompts carrying that label.

## Bulk Tag Maintenance

The Manage Tags page offers several bulk operations for keeping your tag list tidy:

- **Merge** — fold one or more source tags into a single target tag, reassigning every prompt that had a source tag.
- **Bulk delete** — remove multiple tags at once; deleting a tag still in use on prompts requires an explicit "force" confirmation.
- **Find and replace** — rename a tag everywhere at once, merging it into the replacement if one already exists by that name.
- **Orphan cleanup** — list tags with zero prompts attached (unused tags) and prompts with zero tags attached (untagged prompts), so you can clean up either side.

Merge, bulk delete, and find-and-replace can all be undone immediately after running them.

## Tag Analytics

A tag analytics view shows your most- and least-used tags and which tag pairs most often appear together on the same prompt, useful for spotting redundant or overly narrow tags.
