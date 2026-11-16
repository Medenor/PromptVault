---
title: Use the existing API
sidebar_position: 1
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Use the existing API

Use the application programming interface (API) to connect scripts and tools to PromptVault. This space is for integrators who use HTTP requests and a terminal. For everyday tasks, use the [user guide](../user-guide/prompt-management.md). For deployment and server settings, use [installation](../installation/index.md) and [configuration](../configuration/index.md).

## Choose your starting point {#choose-your-starting-point}

- [Make your first API calls](getting-started.md): read, create, and search a test prompt.
- [API reference](reference.md): find operations, formats, access rules, and help with errors.

## Open the reference on your instance {#open-the-reference-on-your-instance}

The documentation site and your PromptVault application can have different addresses. On the **application** address, open:

| Path            | Purpose                          |
| --------------- | -------------------------------- |
| `/docs`         | Interactive API reference        |
| `/redoc`        | Alternative reference view       |
| `/openapi.json` | Machine-readable API description |

For an application at `http://localhost:8001`, open `http://localhost:8001/docs`. Keep any deployment URL prefix supplied by your operator.

You can read these guides without a running instance. To execute a request, use a running application and the credentials it requires. **Try it out** in the live reference sends real requests. Use disposable prompts when modifying or deleting data.

## Know the current boundaries {#know-the-current-boundaries}

Current routes use `/api/...`, without `/v1`. Authenticate script requests with the session access token described in the tutorial.

The live reference lists the routes enabled on your instance. Authentication and administration routes are absent when authentication is disabled. Some descriptions retain older visibility wording: use the access notes in the [reference](reference.md). Check your installed application version in its footer and consult the [release notes](../release-notes/index.md) when comparing releases.
