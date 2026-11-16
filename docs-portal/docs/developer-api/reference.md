---
title: API reference
sidebar_position: 3
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# API reference

Use this page to find existing route families. Open `/docs` on your **application**, not the documentation host, for the complete live schema. Start with [your first API calls](getting-started.md) for a walkthrough.

## Authentication and access {#authentication-and-access}

Send `Authorization: Bearer <ACCESS_TOKEN>` in scripts. Login and refresh accept JSON. Prompt creation and update accept form fields.

Access tokens expire after 15 minutes by default. Send the latest refresh token to `POST /api/auth/refresh` as `{"refresh_token":"<REFRESH_TOKEN>"}`. Replace **both** tokens after refresh. Reusing an old refresh token can revoke the session; do not refresh concurrently. `POST /api/auth/logout` accepts the current refresh token as JSON to end that session.

With authentication enabled, list/search returns only visible items; a request without credentials or with an invalid/expired token can return an empty page rather than 401. An empty page does not confirm that authentication succeeded. Owners, administrators, share grants, and legacy visibility determine access. Edit grants allow edits and reverts, not deletion or share management. See [sharing](../user-guide/sharing.md). Skills use their own rules; see [skills](../user-guide/skills.md).

## Find an operation {#find-an-operation}

Replace `{id}` with a prompt ID and `{version_id}` with an identifier from its history. This table is an orientation, not an exhaustive inventory of administrative operations.

| Operation                           | Route                                                                                                          |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| List / search                       | `GET /api/prompts` · `GET /api/prompts/search`                                                                 |
| Create / read / update / delete     | `POST /api/prompts` · `GET /api/prompts/{id}` · `PUT /api/prompts/{id}` · `DELETE /api/prompts/{id}`           |
| Read history / one version          | `GET /api/prompts/{id}/versions` · `GET /api/prompts/{id}/versions/{version_id}`                               |
| Revert a version                    | `POST /api/prompts/{id}/versions/{version_id}/revert`                                                          |
| Manage prompt shares                | `POST /api/prompts/{id}/shares` · `GET /api/prompts/{id}/shares` · `DELETE /api/prompts/{id}/shares/{user_id}` |
| Import / inspect / download skills  | `POST /api/skills/import` · `GET /api/skills/{id}` · `GET /api/skills/{id}/download`                           |
| Read categories / tags              | `GET /api/categories` · `GET /api/tags`                                                                        |
| Import / export prompts             | `POST /api/import` · `POST /api/export`                                                                        |
| Manage backups                      | `GET /api/backups` · `POST /api/backups`                                                                       |
| Manage users / sessions / schedules | `/api/admin/users` · `/api/admin/sessions` · `/api/admin/scheduler/...`                                        |

See the live reference for administrative permissions and request formats.

Creation/update form fields are `title`, `prompt`, `category`, `tags`, `commit_message`, and optional `semantic_version`. `title` and `prompt` are required for both. Tags are comma-separated. A revert accepts an optional form field `commit_message` and creates a new history entry. A deletion removes data: use it only on items you intend to delete.

## Read paginated results {#read-paginated-results}

List/search defaults to `page=1` and `limit=50`; the maximum limit is 100. Continue while `has_next` is true. The `prompts` object is keyed by ID. `item_type` accepts `all`, `prompt`, or `skill`; skills omit the `prompt` body. `filter=shared-with-me` narrows results to explicit grants.

Search accepts `search`, `category`, `tag`, `favorites`, `case_sensitive`, and `ranked`. Never render returned search snippets as raw HTML. See the [search guide](../user-guide/search.md) for matching behavior.

## Resolve a failed call {#resolve-a-failed-call}

Inspect the HTTP status and body. Errors can use `detail`, `error`, or a structured message depending on the operation. For example, a missing prompt can return `{"detail":"Prompt with ID 123 not found"}`.

| Status | Cause to check                                        | Action                                                                  |
| ------ | ----------------------------------------------------- | ----------------------------------------------------------------------- |
| 401    | Missing, invalid, or expired credentials              | Sign in or refresh once with the latest refresh token.                  |
| 403    | Insufficient access or incomplete required 2FA setup  | Check permissions and complete setup in the application.                |
| 404    | Wrong path, disabled route, missing or hidden item    | Check the address, ID, and access; do not assume the item exists.       |
| 409    | Operation incompatible with the item type             | Use skill routes for skills and prompt-only routes for prompt features. |
| 422    | Missing fields, incorrect encoding, or invalid values | Read the field errors; use form fields for prompt creation/update.      |
| 429    | Request limit reached                                 | Wait the number of seconds in `Retry-After` before retrying.            |

Limits depend on the operation and server configuration; see [configuration](../configuration/index.md). After a mutation times out, check whether it succeeded before replaying it. For connection and server problems, use [troubleshooting](../troubleshooting/index.md).
