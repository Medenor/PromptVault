# API Rate Limiting

PromptVault throttles state-changing and expensive API endpoints — not just
authentication — to protect against abuse, DoS, and data churn in multi-user
deployments. This document covers the **general-API rate-limit taxonomy**. For
the authentication-specific limits (login / register / password-reset), see
[`AUTHENTICATION_SECURITY.md`](AUTHENTICATION_SECURITY.md#rate-limiting).

The middleware itself lives in `src/web/middleware/rate_limit.py` and is wired
into the app in `src/web/middleware_setup.py` (`app.state.limiter` + the
`RateLimitExceeded` exception handler).

## Taxonomy

All budgets are **per authenticated user**, falling back to the client IP for
anonymous requests. Each bucket is `attempts / window` and is independently
overridable via environment variables (defaults shown).

| Bucket        | Default | Env vars                                                                | Applies to                                                                       |
| ------------- | ------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **read**      | 300/min | `RATE_LIMIT_READ_ATTEMPTS` / `RATE_LIMIT_READ_WINDOW_SECONDS`           | GET read endpoints (opt-in helper; most reads remain unthrottled today)          |
| **write**     | 60/min  | `RATE_LIMIT_WRITE_ATTEMPTS` / `RATE_LIMIT_WRITE_WINDOW_SECONDS`         | Prompt create / update / delete, version revert                                  |
| **expensive** | 10/min  | `RATE_LIMIT_EXPENSIVE_ATTEMPTS` / `RATE_LIMIT_EXPENSIVE_WINDOW_SECONDS` | `/api/import`, `/api/export`, backup create / restore / restore-preview / verify |
| **bulk**      | 5/min   | `RATE_LIMIT_BULK_ATTEMPTS` / `RATE_LIMIT_BULK_WINDOW_SECONDS`           | Bulk delete, delete-all backups, compress, retention cleanup                     |

Defaults are defined in `src/config/auth_config.py` (`AuthConfig`) and the limit
strings are built by `read_limit()` / `write_limit()` / `expensive_limit()` /
`bulk_limit()` in `src/web/middleware/rate_limit.py`.

### Endpoints covered

| Endpoint                                              | Bucket    |
| ----------------------------------------------------- | --------- |
| `POST /api/prompts`                                   | write     |
| `PUT /api/prompts/{id}`                               | write     |
| `DELETE /api/prompts/{id}`                            | write     |
| `DELETE /api/prompts/bulk`                            | bulk      |
| `POST /api/prompts/{id}/versions/{version_id}/revert` | write     |
| `POST /api/import`                                    | expensive |
| `POST /api/export`                                    | expensive |
| `POST /api/backups`                                   | expensive |
| `POST /api/backups/{id}/restore`                      | expensive |
| `POST /api/backups/{id}/restore-preview`              | expensive |
| `POST /api/backups/{id}/verify`                       | expensive |
| `DELETE /api/backups`                                 | bulk      |
| `POST /api/backups/compress`                          | bulk      |
| `POST /api/backups/cleanup`                           | bulk      |

## Per-user keying

`get_rate_limit_key()` resolves the caller identity in this order:

1. `request.state.user` (if any middleware populated it),
2. the `X-User-ID` header (test hook only),
3. the JWT `sub` claim, decoded statelessly from the `Authorization: Bearer`
   header or the `access_token` cookie (no DB hit),
4. the client IP (`ip:{addr}`) as the anonymous fallback.

Keying on the JWT subject means one user exhausting a bucket never throttles
another, and a user cannot bypass a limit by rotating IPs.

## Exemptions

Health checks (`/health`, `/api/health`), static asset mounts, the service
worker (`/sw.js`), and HTML page routes are **never** rate-limited. Because
limits are applied per-endpoint via `@limiter.limit(...)` decorators — not global
middleware — any undecorated route is exempt by construction; there is no
allowlist to maintain.

## Response contract

A throttled request receives `429 Too Many Requests` with:

- `Retry-After`: seconds to wait before retrying
- `X-RateLimit-Limit`: the limit that was exceeded
- `X-RateLimit-Remaining`: `0`
- `X-RateLimit-Reset`: Unix timestamp when the window resets

Body:

```json
{
  "error": "Too many requests. Please slow down and try again later.",
  "details": {
    "endpoint": "/api/import",
    "method": "POST",
    "key": "user:42",
    "retry_after_seconds": 60
  }
}
```

## Breach auditing

Every threshold breach emits a `rate_limit.exceeded` audit event to
`data/logs/audit.log` via `logging_service.log_audit_event()`, carrying the
actor key, endpoint, method, and retry-after. **No prompt or note bodies are
logged** — only request metadata.

## Client behavior

`src/web/static/ts/utils/api.ts` handles `429` responses:

- surfaces a warning toast (`showNotification`), i18n keys `messages.rateLimit`
  (with the wait time) and `messages.rateLimitGeneric`,
- auto-retries **idempotent GETs** once, respecting `Retry-After`, within a
  bounded 30s backoff,
- **never** auto-retries writes or form posts — a duplicate could re-run the
  mutation — instead throwing `APIRequestError` (with `.retryAfter`) for the
  caller to handle.

## Enabling / disabling

Rate limiting is implicitly **disabled** in `development` / `testing`
environments (see `is_rate_limiting_disabled()`), and can be forced either way
with `DISABLE_RATE_LIMITING=true|false` (explicit setting wins over the
environment default).

## Storage backend (Redis)

Rate-limit counters are stored in Redis when `REDIS_URL` is configured, giving
persistence and correct behavior across multiple workers. The client connects on
startup using the config in `auth_config.py` and pings to verify.

If Redis is unavailable, the middleware **degrades gracefully** to in-memory
storage: rate limiting still works within a single worker, a warning is logged,
and the app keeps running. In production with multiple workers this is a
critical gap — each worker would keep its own counters — so ensure Redis is
highly available (Sentinel/Cluster) and use `REDIS_URL` with a password.

## Troubleshooting

**Limits not enforced.** Confirm the environment isn't implicitly disabling them
(`ENVIRONMENT=production` or `DISABLE_RATE_LIMITING=false`), that the decorated
handler has a `request: Request` parameter (slowapi requires it), and that Redis
is reachable.

**Redis connection failed.** Look for `Failed to connect to Redis for rate
limiting` in the logs. Verify `redis-cli ping` returns `PONG`, `REDIS_URL` is
correct, network connectivity, and credentials.

**Limits too strict / lenient.** Tune the per-bucket env vars (see the taxonomy
table) — no code change or restart of anything but the app is required.

## Security notes

- Rate limiting is defense-in-depth, not a substitute for authentication/authorization.
- Per-user (JWT `sub`) keying is preferred over IP keying, which an attacker can
  bypass with multiple IPs; anonymous requests still fall back to IP.
- Monitor `rate_limit.exceeded` audit events for patterns indicating distributed
  abuse.

## Configuration reference

All budgets, with defaults, live in `.env.example` under "General API rate-limit
taxonomy". Example override for a busier shared instance:

```bash
RATE_LIMIT_WRITE_ATTEMPTS=120
RATE_LIMIT_EXPENSIVE_ATTEMPTS=20
```
