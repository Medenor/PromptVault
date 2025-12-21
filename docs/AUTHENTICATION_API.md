# Authentication API Documentation

Complete API reference for PromptVault's authentication system, including all endpoints, request/response schemas, authentication requirements, and error codes.

## Table of Contents

1. [Base URL](#base-url)
2. [Authentication](#authentication)
3. [Public Endpoints](#public-endpoints)
   - [Register](#post-authregister)
   - [Login](#post-authlogin)
   - [Refresh Token](#post-authrefresh)
   - [Logout](#post-authlogout)
   - [Password Reset Request](#post-authpassword-resetrequest)
   - [Password Reset Confirm](#post-authpassword-resetconfirm)
4. [Protected Endpoints](#protected-endpoints)
   - [Get Current User](#get-authme)
   - [Change Password](#post-authchange-password)
   - [List Sessions](#get-authsessions)
   - [Revoke Session](#delete-authsessionssession_id)
   - [Revoke All Sessions](#delete-authsessions)
5. [Admin Endpoints](#admin-endpoints)
   - [List Users](#get-adminusers)
   - [Get User](#get-adminusersuser_id)
   - [Update User](#put-adminusersuser_id)
   - [Delete User](#delete-adminusersuser_id)
   - [Get User Sessions](#get-adminusersuser_idsessions)
   - [Revoke User Sessions](#delete-adminusersuser_idsessions)
   - [Get System Stats](#get-adminstats)
6. [Error Responses](#error-responses)
7. [Rate Limiting](#rate-limiting)

---

## Base URL

**Development**: `http://localhost:8000`
**Production**: `https://your-domain.com`

All endpoints are prefixed with `/auth` for authentication or `/admin` for admin operations.

---

## Authentication

### Bearer Token Authentication

Most endpoints require authentication using JWT Bearer tokens:

```http
Authorization: Bearer <access_token>
```

### Token Lifecycle

1. **Access Token**: Short-lived (15 minutes), used for API requests
2. **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

### Obtaining Tokens

Tokens are obtained via:

- `/auth/register` - New user registration
- `/auth/login` - User login
- `/auth/refresh` - Refresh token rotation

---

## Public Endpoints

These endpoints do not require authentication.

---

### POST /api/auth/register

Register a new user account.

#### Request

```http
POST /api/auth/register
Content-Type: application/json
```

```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "SecureP@ssw0rd123",
  "confirm_password": "SecureP@ssw0rd123"
}
```

##### Request Schema

| Field              | Type   | Required | Constraints                           | Description           |
| ------------------ | ------ | -------- | ------------------------------------- | --------------------- |
| `username`         | string | Yes      | 3-32 chars, alphanumeric + underscore | Unique username       |
| `email`            | string | Yes      | Valid email format, max 255 chars     | Unique email address  |
| `password`         | string | Yes      | 8-128 chars, must meet policy         | User password         |
| `confirm_password` | string | Yes      | Must match password                   | Password confirmation |

##### Password Policy

- Minimum 12 characters (configurable)
- At least one uppercase letter (A-Z)
- At least one lowercase letter (a-z)
- At least one digit (0-9)
- At least one special character (!@#$%^&\*()\_+-=[]{}|;:,.<>?)
- Not in common password list

#### Response

**Success (201 Created)**:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "alice",
    "email": "alice@example.com",
    "role": "viewer",
    "is_active": true,
    "email_verified": false,
    "created_at": "2025-12-04T10:30:00Z",
    "updated_at": "2025-12-04T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Error           | Description                               |
| ------ | --------------- | ----------------------------------------- |
| 400    | ValidationError | Password doesn't meet policy requirements |
| 409    | Conflict        | Username or email already exists          |
| 429    | TooManyRequests | Rate limit exceeded (3 attempts/hour)     |

---

### POST /api/auth/login

Login with username/email and password.

#### Request

```http
POST /api/auth/login
Content-Type: application/json
```

```json
{
  "username_or_email": "alice",
  "password": "SecureP@ssw0rd123"
}
```

##### Request Schema

| Field               | Type   | Required | Description               |
| ------------------- | ------ | -------- | ------------------------- |
| `username_or_email` | string | Yes      | Username or email address |
| `password`          | string | Yes      | User password             |

#### Response

**Success (200 OK)**:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "alice",
    "email": "alice@example.com",
    "role": "viewer",
    "is_active": true,
    "email_verified": false,
    "created_at": "2025-12-04T10:30:00Z",
    "updated_at": "2025-12-04T10:30:00Z"
  }
}
```

**Error Responses**:

| Status | Error              | Description                                 |
| ------ | ------------------ | ------------------------------------------- |
| 401    | InvalidCredentials | Invalid username/email or password          |
| 403    | AccountLocked      | Account locked due to failed login attempts |
| 403    | AccountInactive    | Account is deactivated                      |
| 429    | TooManyRequests    | Rate limit exceeded (5 attempts/15 minutes) |

---

### POST /api/auth/refresh

Refresh access token using refresh token.

#### Request

```http
POST /api/auth/refresh
Content-Type: application/json
```

```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9..."
}
```

##### Request Schema

| Field           | Type   | Required | Description             |
| --------------- | ------ | -------- | ----------------------- |
| `refresh_token` | string | Yes      | Valid JWT refresh token |

#### Response

**Success (200 OK)**:

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "alice",
    "email": "alice@example.com",
    "role": "viewer",
    "is_active": true,
    "email_verified": false,
    "created_at": "2025-12-04T10:30:00Z",
    "updated_at": "2025-12-04T10:30:00Z"
  }
}
```

**Notes**:

- Token rotation: New refresh token is issued, old one is invalidated
- Token family tracking: Detects and prevents token reuse attacks
- If token reuse is detected, entire token family is revoked

**Error Responses**:

| Status | Error              | Description                           |
| ------ | ------------------ | ------------------------------------- |
| 401    | InvalidToken       | Invalid or malformed token            |
| 401    | TokenExpired       | Refresh token has expired             |
| 401    | TokenReuseDetected | Token reuse detected, session revoked |
| 403    | AccountInactive    | Account is deactivated                |

---

### POST /api/auth/logout

Logout and revoke refresh token.

#### Request

```http
POST /api/auth/logout
Content-Type: application/json
```

```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9..."
}
```

##### Request Schema

| Field           | Type   | Required | Description             |
| --------------- | ------ | -------- | ----------------------- |
| `refresh_token` | string | Yes      | Refresh token to revoke |

#### Response

**Success (200 OK)**:

```json
{
  "message": "Logged out successfully"
}
```

**Error Responses**:

| Status | Error        | Description                      |
| ------ | ------------ | -------------------------------- |
| 401    | InvalidToken | Invalid or already revoked token |

---

### POST /api/auth/password-reset/request

Request password reset email.

#### Request

```http
POST /api/auth/password-reset/request
Content-Type: application/json
```

```json
{
  "email": "alice@example.com"
}
```

##### Request Schema

| Field   | Type   | Required | Description                      |
| ------- | ------ | -------- | -------------------------------- |
| `email` | string | Yes      | Email address for password reset |

#### Response

**Success (200 OK)**:

```json
{
  "message": "If an account with this email exists, a password reset link has been sent",
  "email": "a***@example.com"
}
```

**Notes**:

- Email is partially masked to prevent user enumeration
- Same response is returned whether email exists or not (security)
- Reset token expires in 1 hour (configurable)
- Rate limited to 3 requests per hour per email

**Error Responses**:

| Status | Error           | Description                           |
| ------ | --------------- | ------------------------------------- |
| 429    | TooManyRequests | Rate limit exceeded (3 attempts/hour) |

---

### POST /api/auth/password-reset/confirm

Confirm password reset with token from email.

#### Request

```http
POST /api/auth/password-reset/confirm
Content-Type: application/json
```

```json
{
  "token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "new_password": "NewSecureP@ssw0rd456",
  "confirm_new_password": "NewSecureP@ssw0rd456"
}
```

##### Request Schema

| Field                  | Type   | Required | Description                     |
| ---------------------- | ------ | -------- | ------------------------------- |
| `token`                | string | Yes      | Password reset token from email |
| `new_password`         | string | Yes      | New password (must meet policy) |
| `confirm_new_password` | string | Yes      | Must match new_password         |

#### Response

**Success (200 OK)**:

```json
{
  "message": "Password has been reset successfully. You can now login with your new password."
}
```

**Error Responses**:

| Status | Error            | Description                               |
| ------ | ---------------- | ----------------------------------------- |
| 400    | ValidationError  | Password doesn't meet policy requirements |
| 401    | TokenInvalid     | Invalid or expired reset token            |
| 401    | TokenAlreadyUsed | Reset token has already been used         |

---

## Protected Endpoints

These endpoints require authentication via Bearer token.

---

### GET /api/auth/me

Get current authenticated user information.

#### Request

```http
GET /api/auth/me
Authorization: Bearer <access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "email": "alice@example.com",
  "role": "viewer",
  "is_active": true,
  "email_verified": false,
  "created_at": "2025-12-04T10:30:00Z",
  "updated_at": "2025-12-04T10:30:00Z"
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |

---

### POST /api/auth/change-password

Change user password (requires current password).

#### Request

```http
POST /api/auth/change-password
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "old_password": "OldP@ssw0rd123",
  "new_password": "NewP@ssw0rd456",
  "confirm_new_password": "NewP@ssw0rd456"
}
```

##### Request Schema

| Field                  | Type   | Required | Description                       |
| ---------------------- | ------ | -------- | --------------------------------- |
| `old_password`         | string | Yes      | Current password for verification |
| `new_password`         | string | Yes      | New password (must meet policy)   |
| `confirm_new_password` | string | Yes      | Must match new_password           |

#### Response

**Success (200 OK)**:

```json
{
  "message": "Password changed successfully",
  "detail": "All sessions remain active. Use /auth/sessions to manage your active sessions."
}
```

**Error Responses**:

| Status | Error              | Description                               |
| ------ | ------------------ | ----------------------------------------- |
| 400    | ValidationError    | Password doesn't meet policy requirements |
| 401    | InvalidCredentials | Incorrect current password                |
| 401    | Unauthorized       | Missing or invalid access token           |

---

### GET /api/auth/sessions

List all active sessions for the authenticated user.

#### Request

```http
GET /api/auth/sessions
Authorization: Bearer <access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "sessions": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440000",
      "family_id": "750e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-04T10:30:00Z",
      "last_used_at": "2025-12-04T11:45:00Z",
      "expires_at": "2025-12-11T10:30:00Z",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "is_revoked": false
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "family_id": "760e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-03T14:20:00Z",
      "last_used_at": "2025-12-04T09:15:00Z",
      "expires_at": "2025-12-10T14:20:00Z",
      "ip_address": "10.0.0.5",
      "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
      "is_revoked": false
    }
  ],
  "total": 2
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |

---

### DELETE /api/auth/sessions/{session_id}

Revoke a specific session by ID.

#### Request

```http
DELETE /api/auth/sessions/650e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "message": "Session revoked successfully",
  "revoked_count": 1
}
```

**Error Responses**:

| Status | Error        | Description                                 |
| ------ | ------------ | ------------------------------------------- |
| 401    | Unauthorized | Missing or invalid access token             |
| 404    | NotFound     | Session not found or doesn't belong to user |

---

### DELETE /api/auth/sessions

Revoke all sessions except the current one.

#### Request

```http
DELETE /api/auth/sessions
Authorization: Bearer <access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "message": "All other sessions revoked successfully",
  "revoked_count": 3
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |

---

## Admin Endpoints

These endpoints require admin role authentication.

---

### GET /admin/users

List all users with pagination and filtering.

#### Request

```http
GET /admin/users?page=1&per_page=20&role=viewer&is_active=true&search=alice
Authorization: Bearer <admin_access_token>
```

##### Query Parameters

| Parameter   | Type    | Required | Default | Description                          |
| ----------- | ------- | -------- | ------- | ------------------------------------ |
| `page`      | integer | No       | 1       | Page number (1-indexed)              |
| `per_page`  | integer | No       | 20      | Items per page (1-100)               |
| `role`      | string  | No       | -       | Filter by role (viewer/editor/admin) |
| `is_active` | boolean | No       | -       | Filter by active status              |
| `search`    | string  | No       | -       | Search in username and email         |

#### Response

**Success (200 OK)**:

```json
{
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "alice",
      "email": "alice@example.com",
      "role": "viewer",
      "is_active": true,
      "email_verified": false,
      "created_at": "2025-12-04T10:30:00Z",
      "updated_at": "2025-12-04T10:30:00Z",
      "last_login": "2025-12-04T11:45:00Z",
      "failed_login_attempts": 0,
      "locked_until": null,
      "password_changed_at": "2025-12-04T10:30:00Z",
      "session_count": 2
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20,
  "total_pages": 1
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |
| 403    | Forbidden    | User does not have admin role   |

---

### GET /admin/users/{user_id}

Get detailed information about a specific user.

#### Request

```http
GET /admin/users/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <admin_access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "email": "alice@example.com",
  "role": "viewer",
  "is_active": true,
  "email_verified": false,
  "created_at": "2025-12-04T10:30:00Z",
  "updated_at": "2025-12-04T10:30:00Z",
  "last_login": "2025-12-04T11:45:00Z",
  "failed_login_attempts": 0,
  "locked_until": null,
  "password_changed_at": "2025-12-04T10:30:00Z",
  "session_count": 2
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |
| 403    | Forbidden    | User does not have admin role   |
| 404    | NotFound     | User not found                  |

---

### PUT /admin/users/{user_id}

Update user information (admin only).

#### Request

```http
PUT /admin/users/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

```json
{
  "role": "editor",
  "is_active": true,
  "email_verified": true
}
```

##### Request Schema

| Field            | Type    | Required | Description                     |
| ---------------- | ------- | -------- | ------------------------------- |
| `role`           | string  | No       | User role (viewer/editor/admin) |
| `is_active`      | boolean | No       | Account active status           |
| `email_verified` | boolean | No       | Email verification status       |

#### Response

**Success (200 OK)**:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "alice",
  "email": "alice@example.com",
  "role": "editor",
  "is_active": true,
  "email_verified": true,
  "created_at": "2025-12-04T10:30:00Z",
  "updated_at": "2025-12-04T15:20:00Z",
  "last_login": "2025-12-04T11:45:00Z",
  "failed_login_attempts": 0,
  "locked_until": null,
  "password_changed_at": "2025-12-04T10:30:00Z",
  "session_count": 2
}
```

**Error Responses**:

| Status | Error           | Description                     |
| ------ | --------------- | ------------------------------- |
| 400    | ValidationError | Invalid role or field value     |
| 401    | Unauthorized    | Missing or invalid access token |
| 403    | Forbidden       | User does not have admin role   |
| 404    | NotFound        | User not found                  |

---

### DELETE /admin/users/{user_id}

Delete or deactivate a user account.

#### Request

```http
DELETE /admin/users/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <admin_access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "message": "User account deactivated successfully"
}
```

**Notes**:

- Admins cannot delete themselves (self-harm prevention)
- User is deactivated, not permanently deleted
- All user sessions are revoked

**Error Responses**:

| Status | Error        | Description                                             |
| ------ | ------------ | ------------------------------------------------------- |
| 401    | Unauthorized | Missing or invalid access token                         |
| 403    | Forbidden    | User does not have admin role or attempting self-delete |
| 404    | NotFound     | User not found                                          |

---

### GET /admin/users/{user_id}/sessions

Get all sessions for a specific user.

#### Request

```http
GET /admin/users/550e8400-e29b-41d4-a716-446655440000/sessions
Authorization: Bearer <admin_access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "sessions": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440000",
      "family_id": "750e8400-e29b-41d4-a716-446655440000",
      "created_at": "2025-12-04T10:30:00Z",
      "last_used_at": "2025-12-04T11:45:00Z",
      "expires_at": "2025-12-11T10:30:00Z",
      "ip_address": "192.168.1.1",
      "user_agent": "Mozilla/5.0...",
      "is_revoked": false
    }
  ],
  "total": 1
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |
| 403    | Forbidden    | User does not have admin role   |
| 404    | NotFound     | User not found                  |

---

### DELETE /admin/users/{user_id}/sessions

Revoke all sessions for a specific user.

#### Request

```http
DELETE /admin/users/550e8400-e29b-41d4-a716-446655440000/sessions
Authorization: Bearer <admin_access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "message": "All user sessions revoked successfully",
  "revoked_count": 3
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |
| 403    | Forbidden    | User does not have admin role   |
| 404    | NotFound     | User not found                  |

---

### GET /admin/stats

Get system statistics (user counts, session counts, etc.).

#### Request

```http
GET /admin/stats
Authorization: Bearer <admin_access_token>
```

#### Response

**Success (200 OK)**:

```json
{
  "total_users": 150,
  "active_users": 145,
  "inactive_users": 5,
  "users_by_role": {
    "viewer": 130,
    "editor": 15,
    "admin": 5
  },
  "total_sessions": 287,
  "active_sessions": 275,
  "revoked_sessions": 12,
  "locked_accounts": 2
}
```

**Error Responses**:

| Status | Error        | Description                     |
| ------ | ------------ | ------------------------------- |
| 401    | Unauthorized | Missing or invalid access token |
| 403    | Forbidden    | User does not have admin role   |

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes

| Status Code | Meaning               | Common Causes                                     |
| ----------- | --------------------- | ------------------------------------------------- |
| 400         | Bad Request           | Invalid input, validation errors                  |
| 401         | Unauthorized          | Missing, invalid, or expired token                |
| 403         | Forbidden             | Insufficient permissions, account locked/inactive |
| 404         | Not Found             | Resource doesn't exist                            |
| 409         | Conflict              | Duplicate username/email                          |
| 422         | Unprocessable Entity  | Request validation failed                         |
| 429         | Too Many Requests     | Rate limit exceeded                               |
| 500         | Internal Server Error | Server-side error                                 |

### Authentication-Specific Errors

| Error                     | Status | Description                    | Solution                                  |
| ------------------------- | ------ | ------------------------------ | ----------------------------------------- |
| `Invalid credentials`     | 401    | Wrong username/password        | Check credentials                         |
| `Account locked`          | 403    | Too many failed login attempts | Wait for lockout period to expire         |
| `Account inactive`        | 403    | Account deactivated            | Contact administrator                     |
| `Token expired`           | 401    | Access/refresh token expired   | Use refresh token to get new access token |
| `Token reuse detected`    | 401    | Refresh token reused           | Login again (security measure)            |
| `Invalid token`           | 401    | Malformed or invalid JWT       | Login again                               |
| `Rate limit exceeded`     | 429    | Too many requests              | Wait and retry                            |
| `Username already exists` | 409    | Username taken                 | Choose different username                 |
| `Email already exists`    | 409    | Email already registered       | Use different email or reset password     |

---

## Rate Limiting

Rate limits are enforced per IP address or user:

| Endpoint                       | Limit      | Window     | Notes               |
| ------------------------------ | ---------- | ---------- | ------------------- |
| `/auth/login`                  | 5 attempts | 15 minutes | Per IP address      |
| `/auth/register`               | 3 attempts | 1 hour     | Per IP address      |
| `/auth/password-reset/request` | 3 attempts | 1 hour     | Per email address   |
| All other endpoints            | No limit   | -          | Monitored for abuse |

### Rate Limit Headers

When rate limited, the response includes:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701349200
Retry-After: 900
```

---

## Complete Example Workflow

### 1. Register New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecureP@ssw0rd123",
    "confirm_password": "SecureP@ssw0rd123"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "alice",
    "password": "SecureP@ssw0rd123"
  }'
```

Save the `access_token` and `refresh_token` from response.

### 3. Access Protected Resource

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Refresh Token (when access token expires)

```bash
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### 5. Change Password

```bash
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecureP@ssw0rd123",
    "new_password": "NewP@ssw0rd456",
    "confirm_new_password": "NewP@ssw0rd456"
  }'
```

### 6. List Active Sessions

```bash
curl http://localhost:8000/api/auth/sessions \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 7. Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

These interfaces provide:

- Interactive endpoint testing
- Complete request/response schemas
- Example payloads
- Authentication testing

---

## Security Best Practices

### For API Consumers

1. **Token Storage**:
   - Store tokens securely (HttpOnly cookies or secure storage)
   - Never expose tokens in URLs or logs
   - Clear tokens on logout

2. **Token Refresh**:
   - Refresh access tokens before expiration
   - Handle 401 responses by refreshing token
   - Re-login if refresh fails

3. **Password Security**:
   - Never log or expose passwords
   - Use strong, unique passwords
   - Implement password managers

4. **HTTPS Only**:
   - Always use HTTPS in production
   - Never send tokens over HTTP

5. **Error Handling**:
   - Don't expose sensitive error details to users
   - Log security events for monitoring
   - Implement proper retry logic with backoff

### For Server Administrators

1. **Environment Security**:
   - Use strong JWT keys (generated by script)
   - Rotate keys periodically
   - Secure .env file (permissions 600)

2. **Monitoring**:
   - Monitor failed login attempts
   - Track rate limit violations
   - Alert on suspicious patterns

3. **Database Security**:
   - Regular backups
   - Encrypted connections
   - Minimal permissions

4. **Redis Security**:
   - Enable authentication
   - Use dedicated instance for rate limiting
   - Monitor memory usage

---

## Additional Resources

- [Deployment Guide](./AUTHENTICATION_DEPLOYMENT.md)
- [Security Documentation](./AUTHENTICATION_SECURITY.md)
- [Testing Guide](./TESTING.md)
