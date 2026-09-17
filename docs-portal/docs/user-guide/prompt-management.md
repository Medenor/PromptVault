---
title: Managing Prompts
sidebar_position: 1
---

# Managing Prompts

The main PromptVault page is a card grid: every prompt you can see is shown as a card, and everyday work — creating, editing, deleting, and favoriting — happens directly from that grid.

## Creating a Prompt

Creating a prompt requires a title and the prompt content itself; category and tags are optional. The first save also creates the prompt's initial version, recorded with a commit message (defaulting to "Initial commit" if you don't provide one) so it shows up in that prompt's [version history](./versioning.md) from the start.

## Editing a Prompt

Editing a prompt's title, content, category, or tags creates a new version rather than silently overwriting the old one — every save is tracked, and you can always look back at (or revert to) an earlier version. You choose the commit message for each edit, the same way you would for the initial creation.

## Deleting a Prompt

Deleting a prompt is a soft delete: the prompt is hidden from the grid, but its data and full version history are preserved rather than destroyed outright, so recovery stays possible. Only the prompt's owner or an admin can delete it.

## Favoriting

Any prompt can be toggled as a favorite from its card, letting you filter the grid down to just the prompts you use most. Only the prompt's owner can toggle its favorite status — favoriting is a personal marker, not a shared one.

## Filtering and Browsing

Beyond favorites, the grid can be filtered by [category](./categories.md), by [tag](./tags.md), or by [search](./search.md) query, and results are paginated — see [Pagination](./pagination.md) for how "Load More" works on large libraries.
