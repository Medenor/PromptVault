# Quickstart Validation: Prompt Sharing & Team Collaboration

**Feature**: 007-prompt-sharing | **Date**: 2026-08-04

Runnable scenarios proving the feature end-to-end. Contracts: [contracts/sharing-api.md](contracts/sharing-api.md). Data model: [data-model.md](data-model.md).

## Prerequisites

```bash
git checkout 007-prompt-sharing
pip install -r requirements.txt && npm install
alembic upgrade head          # applies the prompt_shares migration
npm run build                 # TS must be compiled before manual UI testing
```

## 1. Automated suites (primary gate)

```bash
# Backend — coverage must stay ≥ 85%
python3 -m pytest
# Feature-focused subsets
python3 -m pytest tests/test_sharing_repository.py tests/test_sharing_service.py tests/test_sharing_api.py tests/test_users_api.py
python3 -m pytest tests/test_migration_prompt_shares.py   # up/down; PG cases auto-skip without DATABASE_URL

# Frontend
npm run typecheck && npm run lint
npm run test:unit:coverage    # includes share-modal + badge specs, ≥ 85%
```

**Expected**: all green; authz-matrix test parametrizes 5 actors (owner, grantee-read, grantee-edit, stranger, admin) × 4 actions (view, edit, delete, share-manage) = 20 cases matching the table in data-model.md.

## 2. Migration round-trip (both dialects)

```bash
# SQLite (default dev DB)
alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# PostgreSQL (if available)
DATABASE_URL=postgresql://... alembic upgrade head && \
DATABASE_URL=postgresql://... alembic downgrade -1 && \
DATABASE_URL=postgresql://... alembic upgrade head
```

**Expected**: clean round-trip, no PRAGMA/native-enum errors; `prompt_shares` present with unique constraint + grantee index after upgrade, absent after downgrade.

## 3. Manual two-user walkthrough (US1 + US2 + US3)

Setup: `AUTH_ENABLED=true python run_web.py`, two accounts `alice` and `bob` (create via registration or admin panel).

1. **Grant (US1)**: As `bob`, open a prompt card → Share. Type `al` in the picker → `alice` suggested. Grant `read`. Modal lists alice/read. *Expected*: 201; audit line `prompt.share.granted` in `data/logs/audit.log` with actor=bob, grantee=alice.
2. **Recipient view (US2)**: As `alice`: the prompt appears in the list with a "Shared" badge; "Shared with me" filter shows only it; opening it works; no edit/delete/share controls; direct `PUT /api/prompts/{id}` → 403. Version history opens; revert attempt → 403.
3. **Upgrade to edit (US1 sc.4)**: As `bob`, grant alice `edit`. *Expected*: 200 (update, not duplicate); alice can now edit content/category/tags (creates a version attributed to alice) and revert, but favorite toggle and delete still 403/absent.
4. **Visibility scoping**: Third user `carol` sees neither bob's prompt in her list nor via direct URL (*404*). Admin sees everything.
5. **No enumeration (SC-006)**: As `bob`, grant to `nonexistent-user` and to an email with no account. *Expected*: identical generic 400 bodies.
6. **Revoke (US3)**: As `bob`, open Share modal → revoke alice. *Expected*: grant gone from list; alice's next list load no longer shows the prompt; direct access 404; audit `prompt.share.revoked`.
7. **Cascade (FR-014)**: As `bob`, share a prompt with alice, then delete the prompt. *Expected*: no orphan rows in `prompt_shares` (verify via test or `sqlite3 data/prompts.db 'select count(*) from prompt_shares where prompt_id=...'`).
8. **i18n (FR-015)**: Switch language to fr/es/de — share modal, badge, and filter chip are translated (no raw keys).
9. **Anonymous mode**: Restart with `AUTH_ENABLED=false`. *Expected*: no share controls in UI; `POST /api/prompts/{id}/shares` → 404; listing shows all prompts (legacy behavior).

## 4. Rate limiting spot-check

```bash
# Repeat > limit within a minute as the same user; expect 429 with rate-limit headers
for i in $(seq 1 25); do curl -s -o /dev/null -w "%{http_code} " -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"identifier":"alice","permission":"read"}' \
  http://localhost:8003/api/prompts/1/shares; done
```

## 5. Performance sanity (SC-004, advisory)

`tests/test_sharing_api.py` seeds ~1k prompts + 100 shares and asserts combined listing correctness strictly; timing delta vs. owned-only is logged (target < 10%, non-blocking — research §11).

## Done means

- All of §1 green with coverage gates intact (backend ≥ 85%, frontend ≥ 85%)
- §2 round-trips on SQLite (and Postgres when available)
- §3 walkthrough behaves as written, including audit lines and 4-locale UI
- CHANGELOG entry includes the **visibility behavior change** note (research §1): authenticated users now see only owned + shared prompts
