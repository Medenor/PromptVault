# Authentication Dependencies Quick Reference

## Import

```python
from src.web.dependencies.auth import (
    get_current_active_user,
    require_role,
    require_verified_email,
    get_optional_user,
    get_client_ip,
    get_user_agent,
)
```

## Common Patterns

### Basic Authentication

```python
@router.get("/me")
def get_profile(user: User = Depends(get_current_active_user)):
    return {"username": user.username}
```

### Admin Only

```python
@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin: User = Depends(require_role(["admin"]))):
    return {"deleted": user_id}
```

### Editor or Admin

```python
@router.post("/prompts")
def create_prompt(data: dict, user: User = Depends(require_role(["admin", "editor"]))):
    return {"created": True}
```

### Email Verification Required

```python
@router.post("/api-keys")
def create_api_key(user: User = Depends(require_verified_email)):
    return {"api_key": "..."}
```

### Optional Authentication

```python
@router.get("/prompts")
def list_prompts(user: Optional[User] = Depends(get_optional_user)):
    if user:
        # Personalized results
        pass
    # Public results
    return {"prompts": [...]}
```

### With IP and User-Agent Tracking

```python
@router.post("/auth/login")
def login(
    credentials: dict,
    ip: str = Depends(get_client_ip),
    ua: str = Depends(get_user_agent)
):
    # Log and track session
    return {"token": "..."}
```

## Dependency Cheat Sheet

| Dependency | Purpose | Returns | Raises |
|------------|---------|---------|--------|
| `get_current_user` | Get authenticated user | `User` | 401 if not authenticated |
| `get_current_active_user` | Get active user | `User` | 401 if inactive/locked |
| `get_optional_user` | Optional auth | `Optional[User]` | 401 if token invalid |
| `require_role(["admin"])` | Require admin role | `User` | 403 if wrong role |
| `require_role(["admin", "editor"])` | Require admin/editor | `User` | 403 if wrong role |
| `require_verified_email` | Require verified email | `User` | 403 if not verified |
| `get_client_ip` | Get client IP | `str` | Never |
| `get_user_agent` | Get User-Agent | `str` | Never |

## HTTP Status Codes

- **401 Unauthorized** - Authentication failed (missing/invalid token, inactive account)
- **403 Forbidden** - Authorization failed (wrong role, email not verified)

## Available Roles

- `viewer` - Read-only access
- `editor` - Can create/edit content
- `admin` - Full administrative access

## Example Router Setup

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.web.dependencies.auth import (
    get_current_active_user,
    require_role,
)
from src.db.session import get_db
from src.db.models.user import User

router = APIRouter(prefix="/api/v1", tags=["prompts"])

# Public endpoint
@router.get("/prompts/public")
def list_public_prompts(db: Session = Depends(get_db)):
    return {"prompts": [...]}

# Authenticated endpoint
@router.get("/prompts/my")
def list_my_prompts(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return {"prompts": [...]}

# Role-restricted endpoint
@router.delete("/prompts/{id}")
def delete_prompt(
    id: str,
    user: User = Depends(require_role(["admin", "editor"])),
    db: Session = Depends(get_db)
):
    return {"deleted": id}
```

## Testing

```python
from fastapi.testclient import TestClient

# Create test user
test_user = User(id="1", username="test", role="admin", is_active=True)

# Override dependency
app.dependency_overrides[get_current_active_user] = lambda: test_user

# Test with client
client = TestClient(app)
response = client.get("/api/v1/me")
assert response.status_code == 200
```

## Security Notes

1. Always use HTTPS in production
2. Use `get_current_active_user` for protected routes
3. Short token expiry (15 minutes for access tokens)
4. Implement rate limiting on auth endpoints
5. Log security events (failed logins, role violations)
6. Only trust X-Forwarded-For if behind reverse proxy

## Full Documentation

See [AUTH_DEPENDENCIES.md](./AUTH_DEPENDENCIES.md) for complete documentation with detailed examples.
