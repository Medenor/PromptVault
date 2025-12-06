# Rate Limiting Middleware Integration Guide

This guide explains how to integrate the rate limiting middleware into your FastAPI application.

## Quick Start

### 1. Add to FastAPI Application

In your `src/web/app.py`, add the rate limiting middleware:

```python
from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from src.web.middleware import limiter, rate_limit_exceeded_handler

app = FastAPI(title="PromptVault")

# Add limiter to app state (required by slowapi)
app.state.limiter = limiter

# Register exception handler for rate limit violations
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
```

### 2. Apply Rate Limits to Routes

#### Authentication Endpoints

```python
from fastapi import APIRouter, Request
from src.web.middleware import limiter, auth_login_limit, auth_register_limit, password_reset_limit

router = APIRouter()

@router.post("/auth/login")
@limiter.limit(auth_login_limit)
async def login(request: Request):
    """Login endpoint with rate limiting (5 attempts per 15 minutes)."""
    # Your login logic here
    return {"status": "ok"}

@router.post("/auth/register")
@limiter.limit(auth_register_limit)
async def register(request: Request):
    """Registration endpoint with rate limiting (3 attempts per hour)."""
    # Your registration logic here
    return {"status": "ok"}

@router.post("/auth/password-reset")
@limiter.limit(password_reset_limit)
async def reset_password(request: Request):
    """Password reset endpoint with rate limiting (3 attempts per hour)."""
    # Your password reset logic here
    return {"status": "ok"}
```

#### General API Endpoints

```python
from src.web.middleware import limiter, api_limit

@router.get("/api/prompts")
@limiter.limit(api_limit)
async def get_prompts(request: Request):
    """Get prompts with rate limiting (100 requests per minute)."""
    # Your logic here
    return {"prompts": []}
```

#### Admin Endpoints

```python
from src.web.middleware import limiter, admin_limit

@router.get("/api/admin/users")
@limiter.limit(admin_limit)
async def get_users(request: Request):
    """Admin endpoint with higher rate limit (200 requests per minute)."""
    # Your logic here
    return {"users": []}
```

### 3. Custom Rate Limits

You can also apply custom rate limits to specific endpoints:

```python
@router.post("/api/custom-endpoint")
@limiter.limit("10/minute")  # 10 requests per minute
async def custom_endpoint(request: Request):
    return {"status": "ok"}

@router.post("/api/expensive-operation")
@limiter.limit("5/hour")  # 5 requests per hour
async def expensive_operation(request: Request):
    return {"status": "ok"}
```

## Rate Limit Configuration

Rate limits are configured in `src/config/auth_config.py` and can be overridden with environment variables:

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Login Rate Limiting
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=900  # 15 minutes

# Registration Rate Limiting
RATE_LIMIT_REGISTER_ATTEMPTS=3
RATE_LIMIT_REGISTER_WINDOW_SECONDS=3600  # 1 hour

# Password Reset Rate Limiting
RATE_LIMIT_PASSWORD_RESET_ATTEMPTS=3
RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS=3600  # 1 hour
```

## Rate Limit Headers

All rate-limited responses include the following headers:

- `X-RateLimit-Limit`: Maximum number of requests allowed in the window
- `X-RateLimit-Remaining`: Number of requests remaining in the current window
- `X-RateLimit-Reset`: Unix timestamp when the rate limit resets

When rate limit is exceeded, a 429 response includes:

- `Retry-After`: Number of seconds to wait before retrying

## Rate Limit Keys

The middleware uses smart rate limit keys:

1. **Authenticated users**: `user:{user_id}` (more accurate, prevents bypassing via IP change)
2. **Unauthenticated users**: `ip:{ip_address}` (fallback for public endpoints)

This means authenticated users are tracked per user ID, while unauthenticated requests are tracked per IP address.

## Error Response Format

When rate limit is exceeded, the API returns:

```json
{
  "error": "Too many requests. Please slow down and try again later.",
  "details": {
    "endpoint": "/api/auth/login",
    "method": "POST",
    "key": "ip:192.168.1.100",
    "retry_after_seconds": 900
  }
}
```

HTTP Status: `429 Too Many Requests`

## Redis Backend

The middleware uses Redis for persistent rate limit storage. If Redis is unavailable, the middleware falls back to in-memory storage (not recommended for production with multiple workers).

### Redis Connection

The middleware automatically connects to Redis using the configuration from `auth_config.py`. Connection is tested on startup, and failures are logged as warnings.

### Graceful Degradation

If Redis is unavailable:
- Rate limiting still works using in-memory storage
- Warning is logged
- Application continues to function normally
- In production with multiple workers, consider this a critical issue and ensure Redis is available

## Testing Rate Limits

### Manual Testing

```bash
# Test login rate limit (should allow 5 requests, then block)
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"test"}' \
    -w "\nStatus: %{http_code}\n\n"
  sleep 1
done
```

### With User Authentication

```bash
# Test as authenticated user (tracked by user ID instead of IP)
curl -X GET http://localhost:8000/api/prompts \
  -H "X-User-ID: 123" \
  -w "\nStatus: %{http_code}\n\n"
```

## Integration Checklist

- [ ] Add `limiter` to `app.state.limiter`
- [ ] Register `rate_limit_exceeded_handler` exception handler
- [ ] Apply rate limits to authentication endpoints (login, register, password reset)
- [ ] Apply rate limits to sensitive API endpoints
- [ ] Configure Redis connection in `.env`
- [ ] Test rate limits with manual requests
- [ ] Verify rate limit headers in responses
- [ ] Test graceful degradation when Redis is unavailable
- [ ] Monitor rate limit violations in logs

## Complete Example

Here's a complete example of integrating rate limiting into a FastAPI app:

```python
# src/web/app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.web.middleware import (
    limiter,
    rate_limit_exceeded_handler,
    auth_login_limit,
    auth_register_limit,
    api_limit,
)
from src.web.routers import auth_router, prompts_router

# Create FastAPI app
app = FastAPI(title="PromptVault")

# Add limiter to app state (required by slowapi)
app.state.limiter = limiter

# Register rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Include routers with rate limiting
app.include_router(auth_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint (no rate limiting)."""
    return {"status": "healthy"}
```

```python
# src/web/routers/auth.py
from fastapi import APIRouter, Request, Depends
from src.web.middleware import limiter, auth_login_limit, auth_register_limit

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login")
@limiter.limit(auth_login_limit)
async def login(request: Request, credentials: LoginRequest):
    """Login with rate limiting."""
    # Your login logic here
    return {"token": "..."}

@router.post("/register")
@limiter.limit(auth_register_limit)
async def register(request: Request, user_data: RegisterRequest):
    """Register with rate limiting."""
    # Your registration logic here
    return {"user_id": "..."}
```

## Troubleshooting

### Rate Limiting Not Working

1. Check that `limiter` is added to `app.state.limiter`
2. Verify Redis is running and accessible
3. Check logs for Redis connection errors
4. Ensure decorators are applied correctly (must include `request: Request` parameter)

### Redis Connection Failed

Check the logs for:
```
WARNING - Failed to connect to Redis for rate limiting: [error details]
```

Verify:
- Redis is running: `redis-cli ping` (should return PONG)
- Redis URL is correct in `.env` or `auth_config.py`
- Network connectivity to Redis server
- Redis authentication credentials if required

### Rate Limits Too Strict/Lenient

Adjust the configuration in `.env`:
```bash
# Make login rate limit more lenient
RATE_LIMIT_LOGIN_ATTEMPTS=10
RATE_LIMIT_LOGIN_WINDOW_SECONDS=300  # 5 minutes
```

## Best Practices

1. **Apply rate limits to all authentication endpoints** to prevent brute force attacks
2. **Use user-based rate limiting** for authenticated endpoints (more accurate)
3. **Use IP-based rate limiting** for public endpoints (unauthenticated)
4. **Monitor rate limit violations** in logs to detect potential attacks
5. **Set generous limits for admin endpoints** to avoid blocking legitimate admin operations
6. **Test rate limits** in staging environment before deploying to production
7. **Ensure Redis is highly available** in production (use Redis Sentinel or Cluster)
8. **Consider whitelisting** internal services or health check endpoints

## Security Considerations

- Rate limiting is a defense-in-depth measure, not a replacement for proper authentication
- Attackers can bypass IP-based rate limiting using multiple IPs (use user-based when possible)
- Monitor rate limit violations for patterns indicating distributed attacks
- Consider implementing CAPTCHA after multiple rate limit violations
- Use Redis password authentication in production
- Ensure Redis is not exposed to the public internet
