# Admin Routes - Example Usage

This document provides example usage for all admin API endpoints.

## Authentication

All admin endpoints require admin role authentication. Include the JWT access token in the Authorization header:

```bash
Authorization: Bearer <admin_access_token>
```

## Endpoints Overview

### 1. List Users - `GET /admin/users`

List all users with pagination and filtering support.

**Query Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20, max: 100)
- `role` (string): Filter by role (viewer, editor, admin)
- `is_active` (bool): Filter by active status
- `search` (string): Search by username or email (case-insensitive)

**Example 1: Get first page of users**
```bash
curl -X GET "http://localhost:8000/api/admin/users?page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"
```

**Example 2: Filter by role**
```bash
curl -X GET "http://localhost:8000/api/admin/users?role=editor&page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"
```

**Example 3: Search for users**
```bash
curl -X GET "http://localhost:8000/api/admin/users?search=john&page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"
```

**Example 4: Filter inactive users**
```bash
curl -X GET "http://localhost:8000/api/admin/users?is_active=false&page=1&page_size=20" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "alice",
      "email": "alice@example.com",
      "role": "editor",
      "is_active": true,
      "email_verified": true,
      "created_at": "2025-12-02T10:30:00Z",
      "updated_at": "2025-12-02T10:30:00Z",
      "last_login": "2025-12-03T08:15:00Z",
      "failed_login_attempts": 0,
      "locked_until": null,
      "password_changed_at": "2025-12-02T10:30:00Z",
      "session_count": 2
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```

---

### 2. Get User Details - `GET /admin/users/{user_id}`

Get detailed information about a specific user.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "email": "alice@example.com",
  "role": "editor",
  "is_active": true,
  "email_verified": true,
  "created_at": "2025-12-02T10:30:00Z",
  "updated_at": "2025-12-02T10:30:00Z",
  "last_login": "2025-12-03T08:15:00Z",
  "failed_login_attempts": 0,
  "locked_until": null,
  "password_changed_at": "2025-12-02T10:30:00Z",
  "session_count": 2
}
```

---

### 3. Update User - `PUT /admin/users/{user_id}`

Update user information (role, active status, email verification).

**Request Body:**
```json
{
  "role": "admin",
  "is_active": true,
  "email_verified": true
}
```

**Example 1: Change user role**
```bash
curl -X PUT "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "admin"}'
```

**Example 2: Deactivate user**
```bash
curl -X PUT "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

**Example 3: Verify user email**
```bash
curl -X PUT "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"email_verified": true}'
```

**Example 4: Update multiple fields**
```bash
curl -X PUT "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "editor",
    "is_active": true,
    "email_verified": true
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "email": "alice@example.com",
  "role": "admin",
  "is_active": true,
  "email_verified": true,
  "created_at": "2025-12-02T10:30:00Z",
  "updated_at": "2025-12-03T09:45:00Z",
  "last_login": "2025-12-03T08:15:00Z",
  "failed_login_attempts": 0,
  "locked_until": null,
  "password_changed_at": "2025-12-02T10:30:00Z",
  "session_count": 2
}
```

---

### 4. Delete User - `DELETE /admin/users/{user_id}`

Delete or deactivate a user account.

**Query Parameters:**
- `hard_delete` (bool): If true, permanently delete; if false, soft delete (default: false)

**Example 1: Soft delete (default)**
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "message": "User alice deactivated",
  "detail": "Revoked 2 session(s). User data preserved."
}
```

**Example 2: Hard delete (permanent)**
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000?hard_delete=true" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "message": "User alice permanently deleted",
  "detail": "Revoked 2 session(s)"
}
```

---

### 5. Get User Sessions - `GET /admin/users/{user_id}/sessions`

Get all sessions for a specific user.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000/sessions" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440000",
      "family_id": "750e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-02T10:30:00Z",
      "last_used_at": "2025-12-03T08:15:00Z",
      "expires_at": "2025-12-09T10:30:00Z",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "is_revoked": false
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "family_id": "760e8400-e29b-41d4-a716-446655440001",
      "created_at": "2025-12-01T14:20:00Z",
      "last_used_at": "2025-12-02T16:30:00Z",
      "expires_at": "2025-12-08T14:20:00Z",
      "ip_address": "10.0.0.5",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
      "is_revoked": false
    }
  ],
  "total": 2
}
```

---

### 6. Revoke Single Session - `DELETE /admin/users/{user_id}/sessions/{session_id}`

Revoke a specific session for a user (force logout from one device).

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000/sessions/650e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "message": "Session revoked for user alice",
  "revoked_count": 1
}
```

**Notes:**
- Session must belong to the specified user
- Returns 404 if session doesn't exist or doesn't belong to user
- User is immediately logged out from that specific device
- Access tokens for that session become invalid immediately

---

### 7. Revoke All User Sessions - `DELETE /admin/users/{user_id}/sessions`

Revoke all sessions for a specific user (force logout from all devices).

**Example:**
```bash
curl -X DELETE "http://localhost:8000/api/admin/users/550e8400-e29b-41d4-a716-446655440000/sessions" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "message": "All sessions revoked for user alice",
  "revoked_count": 2
}
```

**Notes:**
- Revokes ALL active sessions for the user
- User is logged out from all devices
- All access tokens become invalid immediately
- Returns `revoked_count: 0` if user has no active sessions

---

### 8. Get System Statistics - `GET /admin/stats`

Get comprehensive system statistics.

**Example:**
```bash
curl -X GET "http://localhost:8000/api/admin/stats" \
  -H "Authorization: Bearer <admin_token>"
```

**Response:**
```json
{
  "total_users": 100,
  "active_users": 85,
  "inactive_users": 15,
  "total_sessions": 150,
  "active_sessions": 120,
  "users_by_role": {
    "viewer": 60,
    "editor": 30,
    "admin": 10
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "You cannot deactivate your own account"
}
```

### 403 Forbidden
```json
{
  "detail": "Access denied. This operation requires 'admin' role. Your role: 'editor'"
}
```

### 404 Not Found
```json
{
  "detail": "User with ID 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

---

## Security Notes

1. **Admin-Only Access**: All endpoints require admin role
2. **Self-Harm Prevention**: Admins cannot delete or deactivate themselves
3. **Audit Logging**: All admin actions are logged with details
4. **Password Security**: Password hashes are NEVER returned in responses
5. **Session Management**: Deleting a user automatically revokes all their sessions

---

## Common Use Cases

### Use Case 1: User Account Management
```bash
# 1. Search for user
curl -X GET "http://localhost:8000/api/admin/users?search=problematic_user" \
  -H "Authorization: Bearer <admin_token>"

# 2. View user details
curl -X GET "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer <admin_token>"

# 3. Deactivate user
curl -X PUT "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# 4. Revoke all sessions
curl -X DELETE "http://localhost:8000/api/admin/users/{user_id}/sessions" \
  -H "Authorization: Bearer <admin_token>"
```

### Use Case 2: Security Incident Response
```bash
# 1. View user's sessions
curl -X GET "http://localhost:8000/api/admin/users/{user_id}/sessions" \
  -H "Authorization: Bearer <admin_token>"

# 2. Force logout (revoke all sessions)
curl -X DELETE "http://localhost:8000/api/admin/users/{user_id}/sessions" \
  -H "Authorization: Bearer <admin_token>"

# 3. Lock account (deactivate)
curl -X PUT "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

### Use Case 3: User Role Promotion
```bash
# 1. Find user
curl -X GET "http://localhost:8000/api/admin/users?search=alice" \
  -H "Authorization: Bearer <admin_token>"

# 2. Promote to editor
curl -X PUT "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"role": "editor"}'

# 3. Verify email if not already verified
curl -X PUT "http://localhost:8000/api/admin/users/{user_id}" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"email_verified": true}'
```

### Use Case 4: System Monitoring
```bash
# Get system statistics
curl -X GET "http://localhost:8000/api/admin/stats" \
  -H "Authorization: Bearer <admin_token>"

# List inactive users
curl -X GET "http://localhost:8000/api/admin/users?is_active=false&page=1&page_size=50" \
  -H "Authorization: Bearer <admin_token>"

# List all admins
curl -X GET "http://localhost:8000/api/admin/users?role=admin&page=1&page_size=50" \
  -H "Authorization: Bearer <admin_token>"
```

---

## Integration with FastAPI App

To integrate the admin router into your FastAPI app:

```python
from fastapi import FastAPI
from src.web.routers.admin import router as admin_router

app = FastAPI()

# Include admin router
app.include_router(admin_router, prefix="/api")
```

The admin endpoints will then be available at:
- `http://localhost:8000/api/admin/users`
- `http://localhost:8000/api/admin/users/{user_id}`
- `http://localhost:8000/api/admin/stats`
- etc.

---

## OpenAPI Documentation

All endpoints are fully documented in OpenAPI/Swagger. Access the interactive documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Filter by the "Admin" tag to see all admin endpoints.
