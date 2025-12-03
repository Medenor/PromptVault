# Authentication & Authorization Dependencies

This document provides comprehensive usage examples for FastAPI authentication and authorization dependencies in PromptVault.

## Table of Contents

- [Overview](#overview)
- [Configuration Dependencies](#configuration-dependencies)
- [Authentication Dependencies](#authentication-dependencies)
- [Authorization Dependencies (RBAC)](#authorization-dependencies-rbac)
- [Request Metadata Dependencies](#request-metadata-dependencies)
- [Composite Dependencies](#composite-dependencies)
- [Complete Examples](#complete-examples)

## Overview

The authentication dependencies are located in `src/web/dependencies/auth.py` and provide:

- **JWT token validation** with ES256 signatures
- **User authentication** from database
- **Role-based access control** (RBAC)
- **Email verification** enforcement
- **IP address and User-Agent extraction**

All dependencies follow FastAPI's dependency injection pattern and can be composed together.

## Configuration Dependencies

### get_auth_config()

Returns the global authentication configuration singleton.

```python
from fastapi import APIRouter, Depends
from src.web.dependencies.auth import get_auth_config
from src.config.auth_config import AuthConfig

router = APIRouter()

@router.get("/config/password-policy")
def get_password_policy(config: AuthConfig = Depends(get_auth_config)):
    """Return password policy requirements."""
    return {
        "min_length": config.password_min_length,
        "require_uppercase": config.password_require_uppercase,
        "require_lowercase": config.password_require_lowercase,
        "require_digit": config.password_require_digit,
        "require_special": config.password_require_special,
        "description": config.password_policy_description,
    }
```

### get_jwt_service()

Returns a JWTService instance for token operations.

```python
from src.web.dependencies.auth import get_jwt_service
from src.services.auth.jwt_service import JWTService

@router.post("/debug/token-info")
def get_token_info(
    token: str,
    jwt_service: JWTService = Depends(get_jwt_service)
):
    """Decode and display token information (debug only)."""
    try:
        claims = jwt_service.decode_token_unsafe(token)
        expiry = jwt_service.get_token_expiry(token)
        is_expired = jwt_service.is_token_expired(token)

        return {
            "user_id": claims.get("sub"),
            "username": claims.get("username"),
            "role": claims.get("role"),
            "expires_at": expiry.isoformat(),
            "is_expired": is_expired,
        }
    except Exception as e:
        return {"error": str(e)}
```

## Authentication Dependencies

### get_current_user_token()

Extracts and validates JWT access token from Authorization header.

```python
from src.web.dependencies.auth import get_current_user_token

@router.get("/token-info")
def get_my_token_info(token_data: dict = Depends(get_current_user_token)):
    """Get information about the current access token."""
    return {
        "user_id": token_data["sub"],
        "username": token_data["username"],
        "email": token_data["email"],
        "role": token_data["role"],
        "issued_at": token_data["iat"],
        "expires_at": token_data["exp"],
        "jti": token_data["jti"],
    }
```

**Request Format:**
```http
GET /token-info HTTP/1.1
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Error Responses:**
- `401 Unauthorized` - Token missing, invalid, or expired
- Includes `WWW-Authenticate` header per RFC 6750

### get_current_user()

Gets the authenticated user from the database.

```python
from src.web.dependencies.auth import get_current_user
from src.db.models.user import User

@router.get("/me")
def get_my_profile(user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "email_verified": user.email_verified,
        "created_at": user.created_at,
    }
```

**Note:** This does NOT check if the user is active or locked. Use `get_current_active_user` for that.

### get_current_active_user()

Gets the authenticated user and verifies account is active and not locked.

```python
from src.web.dependencies.auth import get_current_active_user

@router.post("/prompts")
def create_prompt(
    prompt_data: dict,
    user: User = Depends(get_current_active_user)
):
    """Create a new prompt (requires active account)."""
    # Only active, unlocked users can create prompts
    return {
        "prompt_id": "...",
        "user_id": user.id,
        "created": True,
    }
```

**Validation:**
- ✅ User exists in database
- ✅ `is_active == True`
- ✅ `locked_until` is None or expired

**Error Responses:**
- `401 Unauthorized` - Account inactive or locked

### get_optional_user()

Gets the user if authenticated, None otherwise (for optional authentication).

```python
from typing import Optional
from src.web.dependencies.auth import get_optional_user

@router.get("/prompts")
def list_prompts(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """List prompts (personalized if authenticated)."""
    if user:
        # Return user's prompts + public prompts
        prompts = get_user_and_public_prompts(user.id, db)
    else:
        # Return only public prompts
        prompts = get_public_prompts(db)

    return {"prompts": prompts}
```

**Behavior:**
- No token → Returns `None` (not an error)
- Invalid token → Raises `401` error
- Valid token → Returns `User`

## Authorization Dependencies (RBAC)

### require_role()

Factory function that creates a role-based access control dependency.

```python
from src.web.dependencies.auth import require_role

# Create reusable role requirements
require_admin = require_role(["admin"])
require_editor_or_admin = require_role(["admin", "editor"])

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin)
):
    """Delete a user (admin only)."""
    # Only admins can access this endpoint
    return {"deleted": user_id}

@router.post("/prompts")
def create_prompt(
    prompt_data: dict,
    user: User = Depends(require_editor_or_admin)
):
    """Create a prompt (admin or editor only)."""
    # Admins and editors can create prompts
    return {"created": True, "user_id": user.id}
```

**Available Roles:**
- `viewer` - Can view content
- `editor` - Can create and edit content
- `admin` - Full administrative access

**Error Response:**
- `403 Forbidden` - User lacks required role

### require_verified_email()

Requires email verification for the authenticated user.

```python
from src.web.dependencies.auth import require_verified_email

@router.post("/prompts/publish")
def publish_prompt(
    prompt_id: str,
    user: User = Depends(require_verified_email)
):
    """Publish a prompt (verified users only)."""
    # Only verified users can publish prompts
    return {"published": prompt_id, "user_id": user.id}

@router.post("/api-keys")
def create_api_key(user: User = Depends(require_verified_email)):
    """Create an API key (verified users only)."""
    # Only verified users can create API keys
    return {"api_key": "...", "user_id": user.id}
```

**Error Response:**
- `403 Forbidden` - Email not verified

## Request Metadata Dependencies

### get_client_ip()

Extracts client IP address with proxy support.

```python
from src.web.dependencies.auth import get_client_ip

@router.post("/auth/login")
def login(
    credentials: LoginRequest,
    ip_address: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """Login endpoint with IP tracking."""
    # Log login attempt with IP address
    logger.info(f"Login attempt for {credentials.username} from {ip_address}")

    # Authenticate user
    user = authenticate_user(credentials, db)

    # Create session with IP address
    session = create_session(user.id, ip_address=ip_address)

    return {"access_token": "...", "user": user}
```

**Priority Order:**
1. `X-Forwarded-For` header (first IP)
2. `X-Real-IP` header
3. `request.client.host`
4. `"unknown"` (fallback)

**Security Note:** Only trust `X-Forwarded-For` if behind a reverse proxy.

### get_user_agent()

Extracts User-Agent header (truncated to 255 characters).

```python
from src.web.dependencies.auth import get_user_agent

@router.post("/auth/login")
def login(
    credentials: LoginRequest,
    user_agent: str = Depends(get_user_agent),
    db: Session = Depends(get_db)
):
    """Login endpoint with device tracking."""
    # Authenticate user
    user = authenticate_user(credentials, db)

    # Create session with user agent
    session = create_session(
        user.id,
        user_agent=user_agent
    )

    return {"access_token": "...", "user": user}

@router.get("/sessions")
def list_sessions(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user sessions with device information."""
    sessions = get_user_sessions(user.id, db)

    # Each session includes user_agent for device identification
    return {
        "sessions": [
            {
                "id": s.id,
                "created_at": s.created_at,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "device": parse_user_agent(s.user_agent),
            }
            for s in sessions
        ]
    }
```

## Composite Dependencies

Convenience dependencies that combine common patterns.

### get_admin_user()

```python
from src.web.dependencies.auth import get_admin_user

@router.get("/admin/users")
def list_all_users(admin: User = Depends(get_admin_user)):
    """List all users (admin only)."""
    # Equivalent to: Depends(require_role(["admin"]))
    return {"users": [...]}
```

### get_editor_or_admin_user()

```python
from src.web.dependencies.auth import get_editor_or_admin_user

@router.post("/prompts")
def create_prompt(
    prompt_data: dict,
    user: User = Depends(get_editor_or_admin_user)
):
    """Create a prompt (editor or admin)."""
    # Equivalent to: Depends(require_role(["admin", "editor"]))
    return {"created": True}
```

## Complete Examples

### Protected Endpoint (Active Users Only)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.web.dependencies.auth import get_current_active_user
from src.db.session import get_db
from src.db.models.user import User

router = APIRouter(prefix="/api/v1", tags=["prompts"])

@router.post("/prompts")
def create_prompt(
    prompt_data: dict,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new prompt."""
    prompt = Prompt(
        user_id=user.id,
        title=prompt_data["title"],
        content=prompt_data["content"],
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)

    return {"prompt": prompt, "user_id": user.id}
```

### Role-Based Endpoint (Admin Only)

```python
from src.web.dependencies.auth import require_role

@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    user_repo.delete(user_id)
    db.commit()

    return {"deleted": user_id, "deleted_by": admin.id}
```

### Multiple Role Requirement

```python
@router.post("/prompts/{prompt_id}/publish")
def publish_prompt(
    prompt_id: str,
    user: User = Depends(require_role(["admin", "editor"])),
    db: Session = Depends(get_db)
):
    """Publish a prompt (admin or editor only)."""
    prompt = get_prompt(prompt_id, db)

    # Check ownership (editors can only publish their own prompts)
    if user.role == "editor" and prompt.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Editors can only publish their own prompts"
        )

    prompt.published = True
    db.commit()

    return {"published": prompt_id, "published_by": user.id}
```

### Email Verification Requirement

```python
from src.web.dependencies.auth import require_verified_email

@router.post("/api-keys")
def create_api_key(
    user: User = Depends(require_verified_email),
    db: Session = Depends(get_db)
):
    """Create an API key (verified users only)."""
    import secrets

    api_key = secrets.token_urlsafe(32)

    # Store hashed API key
    db_api_key = APIKey(
        user_id=user.id,
        key_hash=hash_api_key(api_key),
    )
    db.add(db_api_key)
    db.commit()

    # Return plaintext key once (never stored)
    return {
        "api_key": api_key,
        "user_id": user.id,
        "created_at": db_api_key.created_at,
    }
```

### Optional Authentication

```python
from typing import Optional
from src.web.dependencies.auth import get_optional_user

@router.get("/prompts")
def list_prompts(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
    limit: int = 20,
):
    """List prompts (personalized if authenticated)."""
    if user:
        # Authenticated: show user's prompts + public prompts
        prompts = (
            db.query(Prompt)
            .filter(
                (Prompt.user_id == user.id) | (Prompt.is_public == True)
            )
            .limit(limit)
            .all()
        )
    else:
        # Anonymous: show only public prompts
        prompts = (
            db.query(Prompt)
            .filter(Prompt.is_public == True)
            .limit(limit)
            .all()
        )

    return {"prompts": prompts, "authenticated": user is not None}
```

### Login with IP and User-Agent Tracking

```python
from src.web.dependencies.auth import get_client_ip, get_user_agent

@router.post("/auth/login")
def login(
    credentials: LoginRequest,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    db: Session = Depends(get_db)
):
    """Login with session tracking."""
    # Authenticate user
    auth_service = AuthService(db)
    result = auth_service.login(
        credentials.username,
        credentials.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "token_type": "Bearer",
        "expires_in": 900,
        "user": result["user"],
    }
```

### Combining Multiple Dependencies

```python
@router.post("/admin/prompts/{prompt_id}/verify")
def verify_prompt(
    prompt_id: str,
    admin: User = Depends(require_role(["admin"])),
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    db: Session = Depends(get_db)
):
    """Verify a prompt (admin only) with audit logging."""
    prompt = get_prompt(prompt_id, db)

    # Update prompt
    prompt.verified = True
    prompt.verified_by = admin.id
    prompt.verified_at = datetime.now(timezone.utc)

    # Audit log
    audit_log = AuditLog(
        user_id=admin.id,
        action="verify_prompt",
        resource_type="prompt",
        resource_id=prompt_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)

    db.commit()

    return {
        "verified": prompt_id,
        "verified_by": admin.id,
        "verified_at": prompt.verified_at,
    }
```

## Error Handling

All dependencies follow FastAPI's exception handling:

```python
from fastapi import HTTPException, status

# 401 Unauthorized - Authentication failed
# - Missing token
# - Invalid token
# - Expired token
# - User not found
# - Account inactive/locked

# 403 Forbidden - Authorization failed
# - Wrong role
# - Email not verified

# Example error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
        headers=exc.headers,
    )
```

## Testing

Mock dependencies in tests:

```python
import pytest
from fastapi.testclient import TestClient
from src.db.models.user import User

def test_protected_endpoint():
    """Test endpoint with authentication."""
    # Create test user
    test_user = User(
        id="test123",
        username="testuser",
        email="test@example.com",
        role="viewer",
        is_active=True,
    )

    # Override dependency
    app.dependency_overrides[get_current_active_user] = lambda: test_user

    client = TestClient(app)
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
```

## Security Best Practices

1. **Always use HTTPS in production** - JWT tokens are bearer tokens
2. **Validate tokens on every request** - Never trust client claims
3. **Check account status** - Use `get_current_active_user` for protected routes
4. **Implement rate limiting** - Protect authentication endpoints
5. **Log security events** - Track failed authentication attempts
6. **Rotate JWT keys** - Implement key versioning
7. **Set short token expiry** - 15 minutes for access tokens
8. **Use refresh tokens** - Avoid long-lived access tokens
9. **Implement CORS properly** - Restrict origins in production
10. **Monitor for suspicious activity** - Track IP changes, unusual user agents

## References

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OAuth 2.0 Bearer Token RFC 6750](https://tools.ietf.org/html/rfc6750)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
