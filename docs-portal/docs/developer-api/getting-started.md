---
title: Make your first API calls
sidebar_position: 2
---

<!-- This Source Code Form is subject to the terms of the Mozilla Public
     License, v. 2.0. If a copy of the MPL was not distributed with this
     file, You can obtain one at https://mozilla.org/MPL/2.0/. -->

# Make your first API calls

Read a page of prompts, then create and find a disposable prompt on your own instance.

## Before you start

Use a test instance, Bash, and `curl` with `--json` support (7.82 or later). With authentication enabled, you need an active account and, if applicable, your authenticator. Replace angle-bracket placeholders locally. Never share passwords, tokens, or login responses. Use HTTPS for remote instances.

## Set the application address

Use your application address, not this documentation site. This example is a local deployment. Keep any deployment prefix and omit the trailing slash.

```bash
BASE_URL='http://localhost:8001'
```

## Sign in

Skip this step only if your isolated instance is already configured with `AUTH_ENABLED=false`; omit the authorization header in later requests. Do not disable authentication to make an integration work. See [configuration](../configuration/index.md).

Send JSON credentials:

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login" \
  --json '{"username_or_email":"<USERNAME>","password":"<PASSWORD>"}'
```

A completed login returns `access_token` and `refresh_token`. If you receive `challenge_token` instead, complete the request below with that challenge and a current authenticator code or unused recovery code. The challenge is not an access token. If enrollment is required, complete setup in the application first; see [two-factor authentication](../user-guide/two-factor-auth.md).

```bash
curl --silent --show-error --fail-with-body \
  "$BASE_URL/api/auth/login/2fa" \
  --json '{"challenge_token":"<CHALLENGE_TOKEN>","code":"<CODE>"}'
```

Copy the resulting `access_token`. Run this command, paste the token, then press Enter. Bash hides the input and keeps the token itself out of command history:

```bash
read -r -s TOKEN
```

## Read a page of prompts

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts?page=1&limit=10&item_type=prompt"
```

Expect HTTP 200 and fields `prompts`, `page`, `limit`, `total_count`, `total_pages`, `has_next`, and `has_previous`. `prompts` is an object keyed by item ID, not an array. An empty page is valid. With authentication enabled, results depend on your identity and access grants.

## Create a disposable prompt

This request creates data. Use a test account and synthetic content. Prompt creation accepts form fields, not JSON:

```bash
curl --silent --show-error --fail-with-body --include \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts" \
  --data-urlencode 'title=API tutorial' \
  --data-urlencode 'prompt=Summarize this sample text.' \
  --data-urlencode 'tags=api-tutorial'
```

Expect HTTP 201 with `{"success":true,"prompt_id":...}`. Copy that `prompt_id` into the next command:

```bash
PROMPT_ID='<PROMPT_ID>'
```

## Search and inspect versions

Search uses `search`, not `q`. Set `item_type=prompt` to exclude skills from list/search results.

```bash
curl --silent --show-error --fail-with-body --get \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/search" \
  --data-urlencode 'search=API tutorial' \
  --data-urlencode 'item_type=prompt'
```

```bash
curl --silent --show-error --fail-with-body \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/prompts/$PROMPT_ID/versions"
```

The history response contains `versions`. For update, revert, and delete routes, see the [reference](reference.md). Delete only the disposable prompt you created. Remove the local token with `unset TOKEN` when finished; that does not revoke the server session. If a request fails, follow [error guidance](reference.md#resolve-a-failed-call) before retrying.
