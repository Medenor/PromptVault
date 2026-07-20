# Phase 0b — Auth Duplication Audit

Read-only comparison of `src/web/dependencies/auth.py` (1043 lines) against
`src/services/auth/auth_service.py` (1017 lines), per Phase 0b of the refactor
plan. No code changed; this is the "short written note" the plan calls for.

## Finding 1: No cryptographic duplication between the DI layer and the service layer

All JWT encode/decode/signature-verification logic lives in exactly one place:
`src/services/auth/jwt_service.py` (`JWTService.validate_access_token`,
`validate_refresh_token`, `decode_token_unsafe`, `generate_access_token`,
`generate_refresh_token`). Both `dependencies/auth.py` and
`services/auth/auth_service.py` call into `JWTService` rather than
reimplementing token verification. This part of Phase 3's premise ("token
validation logic is duplicated across the DI layer and service layer") does
**not** hold — there's a clean division already:

- `auth_service.py` owns the **session lifecycle** (register/login/refresh/
  revoke) and only ever validates **refresh tokens** (`jwt_service.validate_refresh_token`
  at lines 448, 727) plus one `decode_token_unsafe` fallback for logging out
  with an expired token (line 731).
- `dependencies/auth.py` owns **per-request access-token verification** for
  route guards, and only ever validates **access tokens**
  (`jwt_service.validate_access_token`).

These are different token types used for different purposes; there is no
redundant re-implementation of crypto/claims verification.

## Finding 2: Real duplication is intra-file — three copies of the same access-token pipeline in `dependencies/auth.py`

The following steps are hand-copied three separate times within
`dependencies/auth.py`, each time with minor behavioral drift:

1. **`get_current_user_token`** (lines 175–283) — the "canonical" path used by
   `get_current_user`. Extracts Bearer header or `access_token` cookie, calls
   `jwt_service.validate_access_token`, maps `ExpiredSignatureError` /
   `InvalidSignatureError` / `InvalidTokenError` / generic `Exception` each to
   a distinct 401 with a tailored `WWW-Authenticate` header.

2. **`get_optional_user`** (lines 434–550) — re-implements Bearer-header
   parsing (no cookie support here — drift #1), calls
   `jwt_service.validate_access_token` again, re-implements the "look up user,
   check active-session count, check `is_active`" sequence that already lives
   in `get_current_user` (lines 336–363), then collapses all exception types
   into one generic 401 instead of the three specific mappings above (drift
   #2).

3. **`get_current_user_or_none`** (lines 881–933) — a third copy: Bearer
   header or cookie (matches #1, not #2), calls `validate_access_token` again,
   re-implements the same user-lookup/active-session sequence a third time,
   and swallows *all* exceptions into `return None` instead of raising 401
   (correct for its bypass purpose, but yet another distinct error-handling
   shape).

Net effect: the "extract token → validate → look up user → check
active-session count → check is_active" pipeline exists **three times** with
three different edge-case behaviors (cookie support, exception granularity,
inactive-user handling), rather than one canonical implementation with
parameterized behavior.

## Finding 3: The `get_*_or_bypass` family is mechanical, not logically duplicated — but is a 4x copy-paste of the same conditional

`get_user_or_bypass`, `get_admin_or_bypass`, `get_editor_or_admin_or_bypass`
(lines 968–1043), plus `get_current_user_or_default` (936–965), all share the
identical skeleton:

```python
if not auth_settings.auth_enabled:
    return None  # or fall back to default user
if not user:
    raise 401
if <role check>:  # only in admin/editor variants
    raise 403
return user
```

This is a straightforward `require_role`-style factory candidate — the same
shape as `require_role()` (lines 558–635) already used for the non-bypass
case, just with the `AUTH_ENABLED=false` short-circuit prepended. Today there
is no factory; each of the 4 variants is a hand-written async function.

Additionally, `get_admin_user` / `get_editor_or_admin_user` (lines 806–867,
the non-bypass composites) duplicate the same role-list-message-building logic
that already exists inside `require_role`'s inner `check_user_role` (lines
620–631) — `get_admin_user`/`get_editor_or_admin_user` predate `require_role`
and were never migrated to use it (`require_role(["admin"])` would be
equivalent to `get_admin_user`).

## Recommendation for Phase 3 (not executed here — audit only)

1. Consolidate the three token-extraction-and-validation pipelines
   (`get_current_user_token`, the inline block in `get_optional_user`, and
   `get_current_user_or_none`) into one parameterized internal helper, e.g.
   `_resolve_user(token, *, raise_on_invalid: bool, check_active_session: bool)`,
   with the three public dependencies becoming thin wrappers.
2. Replace `get_admin_user` / `get_editor_or_admin_user` with
   `require_role(["admin"])` / `require_role(["admin", "editor"])` calls —
   confirmed equivalent, since `require_role`'s error-message format already
   matches.
3. Replace the `get_*_or_bypass` family with a factory
   `require_role_or_bypass(allowed_roles: Optional[list[str]])` mirroring
   `require_role`, short-circuiting to `None` when `auth_settings.auth_enabled`
   is `False`.
4. No changes needed to `auth_service.py` or `JWTService` — the actual crypto
   layer is already canonical and shared correctly.

This confirms Phase 3's plan is directionally correct (dependencies/auth.py
should "only compose Depends wrappers"), but the consolidation target is
**within `dependencies/auth.py` itself**, not between it and
`auth_service.py` — the two files aren't duplicating validation logic against
each other, `dependencies/auth.py` is duplicating logic against itself.
