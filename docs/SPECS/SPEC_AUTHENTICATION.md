---
title: PromptVault Authentication System Specification
version: 1.0
date_created: 2025-11-29
last_updated: 2025-11-29
owner: medenor
status: DRAFT
tags: [authentication, security, jwt, rbac, phase-2]
dependencies: [SPEC_APP.md, SPEC_DATABASE.md]
priority: HIGH (Phase 2)
---

## 1. Executive Summary

### 1.1 Purpose

This specification defines the complete authentication and authorization system for PromptVault, transforming it from a single-user local application to a secure multi-user web application. The system implements industry-standard JWT-based authentication with role-based access control (RBAC), enabling secure production deployments and collaborative workflows.

### 1.2 Scope

**In Scope:**
- User registration and login with secure password hashing
- JWT access and refresh token generation and validation
- Role-based access control (viewer, editor, admin)
- Session management with token rotation and expiration
- Password reset flow with email-based tokens
- User profile management
- Admin user management endpoints
- Ownership-based prompt access control
- Migration of existing prompts to default admin user
- Frontend authentication UI (login, registration, profile)
- Comprehensive test coverage for auth flows

**Out of Scope (Future Phases):**
- OAuth2/OpenID Connect integration (Google, GitHub)
- Two-factor authentication (2FA)
- Single Sign-On (SSO)
- Advanced audit logging beyond current system
- User invitation system
- Team/organization management

### 1.3 Key Objectives

1. **Security**: Implement defense-in-depth security with modern cryptographic practices
2. **Usability**: Provide seamless authentication UX with automatic token refresh
3. **Scalability**: Design for multi-tenant deployments with clear separation of user data
4. **Compliance**: Follow OWASP recommendations and industry best practices
5. **Maintainability**: Clear separation of concerns with testable components

### 1.4 Success Metrics

- **Security**: Zero plaintext passwords stored, all endpoints protected by authentication
- **Performance**: Token validation adds < 10ms latency to API requests
- **Reliability**: 99.9% authentication service uptime
- **Usability**: < 3 clicks to login, automatic session refresh transparent to users
- **Coverage**: ≥ 90% test coverage for authentication modules

---

## 2. Technical Architecture

### 2.1 Authentication Flow Overview

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │         │  FastAPI     │         │  Database   │
│  (Browser)  │         │  Backend     │         │ (Postgres)  │
└──────┬──────┘         └───────┬──────┘         └──────┬──────┘
       │                        │                       │
       │ POST /api/auth/login   │                       │
       ├───────────────────────>│                       │
       │  {username, password}  │                       │
       │                        │ Query user            │
       │                        ├──────────────────────>│
       │                        │ User record           │
       │                        │<──────────────────────┤
       │                        │                       │
       │                        │ Verify bcrypt hash    │
       │                        │                       │
       │ Access + Refresh Token │                       │
       │<───────────────────────┤                       │
       │                        │                       │
       │ GET /api/prompts       │                       │
       │ Authorization: Bearer  │                       │
       ├───────────────────────>│                       │
       │                        │ Validate JWT          │
       │                        │ Extract user context  │
       │                        │ Query prompts         │
       │                        ├──────────────────────>│
       │ Prompts (filtered)     │                       │
       │<───────────────────────┤                       │
       │                        │                       │
       │ POST /api/auth/refresh │                       │
       ├───────────────────────>│                       │
       │  {refresh_token}       │                       │
       │                        │ Validate refresh      │
       │                        │ Check token family    │
       │ New access token       │                       │
       │<───────────────────────┤                       │
```

### 2.2 Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Password Hashing | **Argon2id** (via `argon2-cffi`) | Winner of Password Hashing Competition, superior to bcrypt for new apps (2025 best practice) |
| JWT Library | **PyJWT 2.8+** | Industry standard, actively maintained, supports all required algorithms |
| Token Algorithm | **ES256** (ECDSA P-256) | Modern, smaller keys than RS256, excellent security, quantum-resistant considerations |
| Session Storage | **Database (PostgreSQL/SQLite)** | Stateful sessions for revocation, token family tracking |
| Token Transport | **HTTP-only Cookies** (primary) + **Authorization header** (API) | XSS protection via HTTP-only, CSRF protection via SameSite |
| FastAPI Security | `fastapi.security.HTTPBearer` + Custom dependencies | Native FastAPI patterns, dependency injection for auth context |

### 2.3 Database Schema Extensions

#### 2.3.1 Enhanced User Model

```python
class User(Base):
    """Enhanced user model with authentication fields."""
    __tablename__ = "users"

    # Existing fields (from src/db/models/user.py)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200))
    email = Column(String(255))
    role = Column(String(50), default='user')
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # NEW: Authentication fields
    password_hash = Column(String(255), nullable=False)  # Argon2 hash
    email = Column(String(255), unique=True, nullable=False, index=True)  # Make required
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    prompts = relationship("Prompt", back_populates="user")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    password_resets = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
```

#### 2.3.2 UserSession Model (Token Family Tracking)

```python
class UserSession(Base):
    """Tracks active user sessions for token rotation and revocation."""
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_family_id = Column(String(36), nullable=False, unique=True, index=True)  # Rotation tracking
    refresh_token_hash = Column(String(255), nullable=False)  # Bcrypt hash of current refresh token
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    is_revoked = Column(Boolean, default=False, index=True)
    revoked_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index('idx_sessions_user_active', 'user_id', 'is_revoked', 'expires_at'),
    )
```

#### 2.3.3 PasswordResetToken Model

```python
class PasswordResetToken(Base):
    """Temporary tokens for password reset flow."""
    __tablename__ = "password_reset_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True)  # Bcrypt hash
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True))
    ip_address = Column(String(45))

    user = relationship("User", back_populates="password_resets")
```

### 2.4 JWT Token Design

#### 2.4.1 Access Token Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",  // user.id
  "username": "john_doe",
  "role": "editor",
  "type": "access",
  "iat": 1701360000,  // Issued at
  "exp": 1701361800,  // Expires at (30 minutes)
  "jti": "a7b3c4d5-e6f7-8901-2345-6789abcdef00"  // JWT ID for revocation
}
```

**Lifetime**: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRY_MINUTES`)

#### 2.4.2 Refresh Token Payload

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "type": "refresh",
  "family": "f8a9b0c1-d2e3-4567-8901-23456789abcd",  // Token family ID
  "iat": 1701360000,
  "exp": 1702569600,  // Expires at (14 days)
  "jti": "b8c4d5e6-f7a8-9012-3456-789abcdef012"
}
```

**Lifetime**: 14 days (configurable via `REFRESH_TOKEN_EXPIRY_DAYS`)

**Token Rotation**: Each refresh generates new access + refresh token, old refresh token invalidated

---

## 3. API Specification

### 3.1 Authentication Endpoints

#### 3.1.1 User Registration

```
POST /api/auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecureP@ssw0rd123",
  "display_name": "John Doe"  // Optional
}
```

**Validation Rules:**
- `username`: 3-50 chars, alphanumeric + underscore/hyphen, unique
- `email`: Valid email format, unique, max 255 chars
- `password`: Min 12 chars, must contain uppercase, lowercase, digit, special char
- `display_name`: Optional, max 200 chars

**Response (201 Created):**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com",
    "display_name": "John Doe",
    "role": "viewer",
    "created_at": "2025-11-29T10:30:00Z"
  },
  "message": "Registration successful. Please verify your email."
}
```

**Error Responses:**
- `400`: Validation failed (weak password, invalid email)
- `409`: Username or email already exists
- `422`: Pydantic validation error

#### 3.1.2 User Login

```
POST /api/auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "SecureP@ssw0rd123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,  // seconds
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "john_doe",
    "email": "john@example.com",
    "role": "editor",
    "display_name": "John Doe"
  }
}
```

**Set-Cookie Headers (HTTP-only):**
```
Set-Cookie: access_token=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1800; Path=/
Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict; Max-Age=1209600; Path=/api/auth
```

**Error Responses:**
- `401`: Invalid credentials
- `403`: Account locked (too many failed attempts)
- `404`: User not found
- `422`: Validation error

**Rate Limiting**: 5 attempts per 15 minutes per IP

#### 3.1.3 Token Refresh

```
POST /api/auth/refresh
Content-Type: application/json
```

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**OR** via HTTP-only cookie (preferred):
```
Cookie: refresh_token=<token>
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Token Rotation Logic:**
1. Validate refresh token signature and expiration
2. Check token family in database (`UserSession` table)
3. If token reused after rotation → **REVOKE ENTIRE FAMILY** (potential theft)
4. Generate new access + refresh tokens with same family ID
5. Update `UserSession` with new refresh token hash
6. Return new tokens

**Error Responses:**
- `401`: Invalid or expired refresh token
- `403`: Token family revoked (reuse detected)
- `404`: Session not found

#### 3.1.4 Logout

```
POST /api/auth/logout
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "revoke_all_sessions": false  // Optional: logout from all devices
}
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Behavior:**
- Revoke current session in `UserSession` table
- If `revoke_all_sessions=true`: revoke all user sessions
- Clear HTTP-only cookies

#### 3.1.5 Password Reset Request

```
POST /api/auth/password-reset/request
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "john@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "If the email exists, a password reset link has been sent."
}
```

**Behavior:**
- Always return success (prevent user enumeration)
- If email exists: generate reset token, send email with link
- Token valid for 1 hour
- Rate limit: 3 requests per hour per IP

#### 3.1.6 Password Reset Confirmation

```
POST /api/auth/password-reset/confirm
Content-Type: application/json
```

**Request Body:**
```json
{
  "token": "abc123def456...",
  "new_password": "NewSecureP@ssw0rd456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password reset successful. Please login with your new password."
}
```

**Error Responses:**
- `400`: Invalid or expired token
- `422`: Password validation failed

### 3.2 User Management Endpoints

#### 3.2.1 Get Current User Profile

```
GET /api/auth/me
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john_doe",
  "email": "john@example.com",
  "display_name": "John Doe",
  "role": "editor",
  "email_verified": true,
  "created_at": "2025-10-01T08:00:00Z",
  "last_login": "2025-11-29T10:30:00Z",
  "prompt_count": 42,
  "favorite_count": 7
}
```

#### 3.2.2 Update Profile

```
PUT /api/auth/me
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "display_name": "John Smith",
  "email": "john.smith@example.com"  // Triggers re-verification
}
```

**Response (200 OK):**
```json
{
  "user": { ... },
  "message": "Profile updated. Email verification required for new address."
}
```

#### 3.2.3 Change Password

```
POST /api/auth/me/change-password
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "current_password": "SecureP@ssw0rd123",
  "new_password": "NewSecureP@ssw0rd456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password changed successfully. Please login again."
}
```

**Behavior:**
- Revoke all sessions except current
- Update `password_changed_at` timestamp

#### 3.2.4 Delete Account

```
DELETE /api/auth/me
Authorization: Bearer <access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "password": "SecureP@ssw0rd123",
  "confirmation": "DELETE MY ACCOUNT"
}
```

**Response (200 OK):**
```json
{
  "message": "Account deleted successfully."
}
```

**Behavior:**
- Verify password
- Soft delete or transfer prompts to admin (configurable)
- Revoke all sessions
- GDPR compliance: actual deletion vs anonymization

### 3.3 Admin Endpoints

**All admin endpoints require `role=admin` and return 403 for non-admins.**

#### 3.3.1 List All Users

```
GET /api/admin/users?page=1&limit=50&role=editor&active=true
Authorization: Bearer <admin_access_token>
```

**Response (200 OK):**
```json
{
  "users": [
    {
      "id": "...",
      "username": "...",
      "email": "...",
      "role": "editor",
      "is_active": true,
      "created_at": "...",
      "last_login": "...",
      "prompt_count": 15
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 127,
    "pages": 3
  }
}
```

#### 3.3.2 Update User Role

```
PUT /api/admin/users/{user_id}/role
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "role": "admin"  // viewer, editor, admin
}
```

**Response (200 OK):**
```json
{
  "user": { ... },
  "message": "User role updated to admin"
}
```

#### 3.3.3 Deactivate/Reactivate User

```
PUT /api/admin/users/{user_id}/status
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "is_active": false
}
```

**Response (200 OK):**
```json
{
  "user": { ... },
  "message": "User account deactivated"
}
```

**Behavior:**
- If deactivating: revoke all user sessions
- Deactivated users cannot login

#### 3.3.4 Delete User (Admin)

```
DELETE /api/admin/users/{user_id}
Authorization: Bearer <admin_access_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "transfer_prompts_to": "admin-user-id",  // Optional
  "permanent": false  // Soft delete by default
}
```

**Response (200 OK):**
```json
{
  "message": "User deleted. 42 prompts transferred to admin."
}
```

---

## 4. Authorization & Access Control

### 4.1 Role Definitions

| Role | Permissions | Use Case |
|------|-------------|----------|
| **viewer** | - Read own prompts<br>- Export own prompts<br>- Cannot create/edit/delete | External auditors, read-only access |
| **editor** | - All viewer permissions<br>- Create prompts<br>- Edit/delete own prompts<br>- Manage own categories/tags<br>- Version control operations | Standard user, content creators |
| **admin** | - All editor permissions<br>- View/edit/delete ANY prompt<br>- User management<br>- System backups<br>- View audit logs | System administrators |

### 4.2 Permission Matrix

| Operation | Viewer | Editor | Admin | Notes |
|-----------|--------|--------|-------|-------|
| GET /api/prompts | Own | Own | All | Filtered by user_id |
| POST /api/prompts | ❌ | ✅ | ✅ | Auto-set owner |
| PUT /api/prompts/{id} | ❌ | Own | All | Check ownership |
| DELETE /api/prompts/{id} | ❌ | Own | All | Check ownership |
| GET /api/prompts/{id}/versions | Own | Own | All | Check prompt ownership |
| POST /api/prompts/{id}/versions/{vid}/revert | ❌ | Own | All | Check prompt ownership |
| POST /api/backups | ❌ | ❌ | ✅ | Admin only |
| GET /api/admin/users | ❌ | ❌ | ✅ | Admin only |
| PUT /api/admin/users/{id}/role | ❌ | ❌ | ✅ | Admin only |

### 4.3 FastAPI Dependency Injection

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated

security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> User:
    """Extract and validate JWT token, return authenticated user."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, ES256_PUBLIC_KEY, algorithms=["ES256"])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Fetch user from database
        user = await user_repository.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_role(required_role: str):
    """Dependency factory for role-based access control."""
    async def role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        role_hierarchy = {"viewer": 1, "editor": 2, "admin": 3}
        if role_hierarchy.get(user.role, 0) < role_hierarchy.get(required_role, 99):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return role_checker

# Usage in routes
@app.get("/api/prompts")
async def list_prompts(user: Annotated[User, Depends(get_current_user)]):
    # Automatically filter by user_id for non-admins
    prompts = await prompt_repository.get_by_user(user.id)
    return prompts

@app.post("/api/backups")
async def create_backup(user: Annotated[User, Depends(require_role("admin"))]):
    # Only admins can reach this endpoint
    ...
```

### 4.4 Ownership Verification

```python
async def verify_prompt_ownership(prompt_id: int, user: User) -> Prompt:
    """Verify user owns prompt or is admin."""
    prompt = await prompt_repository.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if user.role != "admin" and prompt.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this prompt")

    return prompt
```

---

## 5. Security Requirements

### 5.1 Password Security

**Hashing Algorithm**: Argon2id with parameters:
```python
from argon2 import PasswordHasher
from argon2.profiles import RFC_9106_LOW_MEMORY

# Production settings (balance security vs performance)
ph = PasswordHasher(
    time_cost=3,           # 3 iterations
    memory_cost=65536,     # 64 MiB
    parallelism=4,         # 4 threads
    hash_len=32,           # 32-byte hash
    salt_len=16,           # 16-byte salt
    encoding='utf-8',
    type=argon2.Type.ID    # Argon2id (hybrid)
)

# Hash password
hash = ph.hash("SecureP@ssw0rd123")

# Verify password
try:
    ph.verify(hash, "SecureP@ssw0rd123")
    # Password correct
except argon2.exceptions.VerifyMismatchError:
    # Password incorrect
```

**Password Policy** (enforced in Pydantic validator):
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character from `!@#$%^&*()_+-=[]{}|;:,.<>?`
- Not in common password lists (check against top 10k breached passwords)
- Not same as username/email

**Breach Detection**: Integrate HaveIBeenPwned API (optional, privacy-preserving k-anonymity):
```python
import hashlib
import httpx

async def is_password_breached(password: str) -> bool:
    """Check if password appears in breach database using k-anonymity."""
    sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.pwnedpasswords.com/range/{prefix}")
        hashes = {line.split(":")[0]: int(line.split(":")[1])
                  for line in response.text.splitlines()}
        return suffix in hashes
```

### 5.2 JWT Token Security

**Signing Keys**:
- **Algorithm**: ES256 (ECDSA with P-256 curve)
- **Key Generation**:
```bash
# Generate ECDSA P-256 private key
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem

# Extract public key
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

- **Key Storage**: Environment variables (never commit to git)
```bash
# .env
JWT_PRIVATE_KEY_PATH=/secure/path/es256-private.pem
JWT_PUBLIC_KEY_PATH=/secure/path/es256-public.pem
```

- **Key Rotation**: Support multiple public keys with `kid` (key ID) in JWT header
```json
{
  "alg": "ES256",
  "typ": "JWT",
  "kid": "2025-11-29"  // Key version identifier
}
```

**Token Security Checklist**:
- ✅ Short access token lifetime (30 minutes)
- ✅ Refresh token rotation on every use
- ✅ Token family tracking for reuse detection
- ✅ `jti` claim for token revocation
- ✅ Audience (`aud`) claim: `"https://promptvault.app"`
- ✅ Issuer (`iss`) claim: `"https://promptvault.app"`
- ✅ Not Before (`nbf`) claim to prevent premature use
- ✅ HTTP-only cookies for web clients
- ✅ Secure + SameSite=Strict cookie flags

### 5.3 Rate Limiting

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| POST /api/auth/login | 5 | 15 min | IP + Username |
| POST /api/auth/register | 3 | 1 hour | IP |
| POST /api/auth/password-reset/request | 3 | 1 hour | IP |
| POST /api/auth/refresh | 20 | 1 hour | User ID |
| All authenticated endpoints | 1000 | 1 hour | User ID |

**Implementation**: Use `slowapi` library with Redis backend:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/auth/login")
@limiter.limit("5/15minutes")
async def login(request: Request, ...):
    ...
```

### 5.4 Account Lockout

**Failed Login Protection**:
- Track failed attempts in `User.failed_login_attempts`
- After 5 failed attempts: lock account for 15 minutes
- After 10 failed attempts: lock account for 1 hour
- After 15 failed attempts: lock account indefinitely (require admin unlock)

```python
async def handle_failed_login(user: User):
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= 15:
        user.is_active = False  # Permanent lock
        await audit_logger.log("account_locked_permanent", user_id=user.id)
    elif user.failed_login_attempts >= 10:
        user.locked_until = datetime.utcnow() + timedelta(hours=1)
    elif user.failed_login_attempts >= 5:
        user.locked_until = datetime.utcnow() + timedelta(minutes=15)

    await user_repository.save(user)

async def reset_failed_attempts(user: User):
    """Call on successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    await user_repository.save(user)
```

### 5.5 Session Management

**Session Limits**:
- Maximum 5 active sessions per user
- If 6th session created: revoke oldest inactive session
- Admin override: can force revoke all sessions for a user

**Session Metadata**:
```python
@dataclass
class SessionInfo:
    device: str          # Parsed from User-Agent
    browser: str
    os: str
    ip_address: str
    location: str        # Optional: GeoIP lookup
    last_used: datetime
    is_current: bool
```

**User Session Management UI**:
- View all active sessions
- Revoke individual sessions
- "Logout from all devices" button

---

## 6. Migration Strategy

### 6.1 Database Migration (Alembic)

**Migration Steps**:

1. **Migration 001**: Add authentication columns to `users` table
```python
# alembic/versions/001_add_authentication_fields.py
def upgrade():
    # Add new columns
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), default=False))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), default=True))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), default=0))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True)))

    # Make email unique and required (requires data migration first)
    # op.alter_column('users', 'email', nullable=False)
    # op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])

def downgrade():
    # Revert changes
    ...
```

2. **Migration 002**: Create `user_sessions` table
```python
def upgrade():
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_family_id', sa.String(36), nullable=False, unique=True),
        sa.Column('refresh_token_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('is_revoked', sa.Boolean(), default=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
    )
    op.create_index('idx_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('idx_sessions_family_id', 'user_sessions', ['token_family_id'])
    op.create_index('idx_sessions_user_active', 'user_sessions', ['user_id', 'is_revoked', 'expires_at'])
```

3. **Migration 003**: Create `password_reset_tokens` table
```python
def upgrade():
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('ip_address', sa.String(45)),
    )
    op.create_index('idx_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('idx_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'])
```

### 6.2 Data Migration Script

**Objective**: Assign all existing prompts to a default admin user

```python
# scripts/migrate_to_authentication.py
import asyncio
from argon2 import PasswordHasher
from src.db.session import get_session
from src.db.models.user import User
from src.db.models.prompt import Prompt
import uuid
from datetime import datetime
import os

ph = PasswordHasher()

async def create_default_admin():
    """Create default admin user for migration."""
    async with get_session() as session:
        # Check if admin exists
        existing = await session.execute(
            select(User).where(User.username == "admin")
        )
        admin = existing.scalar_one_or_none()

        if admin:
            print(f"Admin user already exists: {admin.id}")
            return admin.id

        # Generate secure random password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + string.punctuation
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(20))

        # Create admin user
        admin = User(
            id=str(uuid.uuid4()),
            username="admin",
            email=os.getenv("ADMIN_EMAIL", "admin@promptvault.local"),
            display_name="System Administrator",
            password_hash=ph.hash(temp_password),
            role="admin",
            is_active=True,
            email_verified=True,
            created_at=datetime.utcnow()
        )
        session.add(admin)
        await session.commit()

        print(f"✅ Created admin user: {admin.id}")
        print(f"   Username: admin")
        print(f"   Email: {admin.email}")
        print(f"   Temporary Password: {temp_password}")
        print(f"   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!")

        return admin.id

async def assign_prompts_to_admin(admin_id: str):
    """Assign all existing prompts to admin user."""
    async with get_session() as session:
        result = await session.execute(
            select(Prompt).where(Prompt.user_id == None)
        )
        prompts = result.scalars().all()

        count = 0
        for prompt in prompts:
            prompt.user_id = admin_id
            count += 1

        await session.commit()
        print(f"✅ Assigned {count} prompts to admin user")

async def main():
    print("🔐 Starting authentication migration...")
    admin_id = await create_default_admin()
    await assign_prompts_to_admin(admin_id)
    print("✅ Migration complete!")
    print("\n⚠️  IMPORTANT: Login as 'admin' and change the password immediately!")

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage**:
```bash
# Set admin email (optional)
export ADMIN_EMAIL="your-email@example.com"

# Run migration
python scripts/migrate_to_authentication.py

# Output:
# 🔐 Starting authentication migration...
# ✅ Created admin user: 550e8400-e29b-41d4-a716-446655440000
#    Username: admin
#    Email: admin@promptvault.local
#    Temporary Password: x7K!mP9@qW2#nL5$vR8&
#    ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!
# ✅ Assigned 127 prompts to admin user
# ✅ Migration complete!
```

---

## 7. Frontend Implementation

### 7.1 Login Page (`src/web/templates/login.html`)

**Features**:
- Username/email + password fields
- "Remember me" checkbox (longer refresh token)
- "Forgot password?" link
- "Register" link
- CSRF protection
- Client-side validation
- Password visibility toggle
- Loading states

**JavaScript** (`src/web/static/js/auth.js`):
```javascript
async function login(username, password, rememberMe) {
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();

        // Store tokens (cookies are set by server, this is backup for localStorage approach)
        if (rememberMe) {
            localStorage.setItem('refresh_token', data.refresh_token);
        } else {
            sessionStorage.setItem('refresh_token', data.refresh_token);
        }

        // Store user info
        localStorage.setItem('user', JSON.stringify(data.user));

        // Redirect to main app
        window.location.href = '/';

    } catch (error) {
        showError(error.message);
        logFailedLogin(username);
    }
}

// Automatic token refresh
let refreshInterval;

function startTokenRefresh() {
    // Refresh 5 minutes before expiration
    refreshInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'include'  // Send HTTP-only cookies
            });

            if (!response.ok) {
                // Refresh failed, redirect to login
                logout();
                return;
            }

            const data = await response.json();
            console.log('Token refreshed successfully');

        } catch (error) {
            console.error('Token refresh failed:', error);
            logout();
        }
    }, 25 * 60 * 1000);  // Every 25 minutes (token expires in 30)
}

function logout() {
    clearInterval(refreshInterval);
    localStorage.removeItem('user');
    sessionStorage.clear();
    localStorage.clear();
    window.location.href = '/login';
}
```

### 7.2 Registration Page

**Fields**:
- Username (with availability check)
- Email (with format validation)
- Password (with strength meter)
- Confirm password
- Display name (optional)
- Terms of service checkbox

**Password Strength Meter**:
```javascript
function calculatePasswordStrength(password) {
    let strength = 0;

    if (password.length >= 12) strength += 25;
    if (/[a-z]/.test(password)) strength += 15;
    if (/[A-Z]/.test(password)) strength += 15;
    if (/[0-9]/.test(password)) strength += 15;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 15;
    if (password.length >= 16) strength += 15;

    return {
        score: strength,
        label: strength < 50 ? 'Weak' : strength < 75 ? 'Medium' : 'Strong',
        color: strength < 50 ? 'red' : strength < 75 ? 'orange' : 'green'
    };
}
```

### 7.3 User Profile Page

**Sections**:
1. **Profile Information**: username, email, display name, role (read-only)
2. **Statistics**: prompts created, favorites, last login
3. **Security**: change password, view active sessions, enable 2FA (future)
4. **Danger Zone**: delete account

### 7.4 Authentication Middleware (Frontend)

```javascript
// Check authentication on page load
window.addEventListener('DOMContentLoaded', async () => {
    const publicPages = ['/login', '/register', '/password-reset'];
    const currentPath = window.location.pathname;

    if (publicPages.includes(currentPath)) {
        return;  // Allow access to public pages
    }

    // Check if user is authenticated
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (!user) {
        window.location.href = '/login';
        return;
    }

    // Verify token is still valid
    try {
        const response = await fetch('/api/auth/me', {
            credentials: 'include'
        });

        if (!response.ok) {
            // Token invalid, redirect to login
            logout();
            return;
        }

        // Update user info
        const userData = await response.json();
        localStorage.setItem('user', JSON.stringify(userData));

        // Start automatic token refresh
        startTokenRefresh();

    } catch (error) {
        console.error('Auth check failed:', error);
        logout();
    }
});

// Add Authorization header to all API requests
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const [url, config = {}] = args;

    // Only add header for API requests
    if (url.startsWith('/api/') && !url.startsWith('/api/auth/')) {
        config.headers = {
            ...config.headers,
            'Authorization': `Bearer ${getAccessToken()}`
        };
        config.credentials = 'include';  // Send cookies
    }

    return originalFetch(url, config)
        .catch(async (error) => {
            // If 401, try to refresh token
            if (error.status === 401) {
                const refreshed = await refreshAccessToken();
                if (refreshed) {
                    // Retry original request
                    return originalFetch(url, config);
                } else {
                    logout();
                }
            }
            throw error;
        });
};
```

---

## 8. Testing Strategy

### 8.1 Test Coverage Requirements

**Minimum Coverage**: 90% for authentication modules

**Critical Test Areas**:
1. Password hashing and verification (100% coverage)
2. JWT token generation and validation (100% coverage)
3. Token rotation logic (100% coverage)
4. Permission checks (100% coverage)
5. Rate limiting (95% coverage)
6. Account lockout (95% coverage)

### 8.2 Unit Tests

```python
# tests/test_auth_service.py
import pytest
from src.services.auth_service import AuthService
from argon2.exceptions import VerifyMismatchError

@pytest.fixture
def auth_service():
    return AuthService()

class TestPasswordHashing:
    def test_hash_password(self, auth_service):
        """Test password hashing produces unique hashes."""
        password = "SecureP@ssw0rd123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        assert hash1 != hash2  # Unique salts
        assert len(hash1) > 0
        assert hash1.startswith("$argon2id$")

    def test_verify_password_correct(self, auth_service):
        """Test correct password verification."""
        password = "SecureP@ssw0rd123"
        hash = auth_service.hash_password(password)

        assert auth_service.verify_password(hash, password) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test incorrect password rejection."""
        hash = auth_service.hash_password("SecureP@ssw0rd123")

        with pytest.raises(VerifyMismatchError):
            auth_service.verify_password(hash, "WrongPassword")

    def test_password_policy_enforcement(self, auth_service):
        """Test password policy validation."""
        # Too short
        with pytest.raises(ValueError, match="at least 12 characters"):
            auth_service.validate_password_policy("Short1!")

        # No uppercase
        with pytest.raises(ValueError, match="uppercase"):
            auth_service.validate_password_policy("nocapitals123!")

        # No digit
        with pytest.raises(ValueError, match="digit"):
            auth_service.validate_password_policy("NoDigitsHere!")

        # Valid password
        auth_service.validate_password_policy("SecureP@ssw0rd123")  # No exception

class TestJWTTokens:
    def test_generate_access_token(self, auth_service, test_user):
        """Test access token generation."""
        token = auth_service.generate_access_token(test_user)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify payload
        payload = auth_service.decode_token(token)
        assert payload["sub"] == test_user.id
        assert payload["username"] == test_user.username
        assert payload["role"] == test_user.role
        assert payload["type"] == "access"

    def test_token_expiration(self, auth_service, test_user):
        """Test expired token rejection."""
        # Generate token with 0 second expiry
        token = auth_service.generate_access_token(test_user, expires_delta=timedelta(seconds=0))

        time.sleep(1)

        with pytest.raises(jwt.ExpiredSignatureError):
            auth_service.decode_token(token)

    def test_invalid_signature(self, auth_service):
        """Test token with invalid signature is rejected."""
        fake_token = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.invalid"

        with pytest.raises(jwt.InvalidTokenError):
            auth_service.decode_token(fake_token)

class TestTokenRotation:
    async def test_refresh_token_rotation(self, auth_service, test_user):
        """Test refresh token rotation creates new tokens."""
        # Create initial session
        refresh_token = auth_service.generate_refresh_token(test_user)
        session = await auth_service.create_session(test_user, refresh_token)

        # Refresh token
        new_tokens = await auth_service.refresh_tokens(refresh_token)

        assert new_tokens["access_token"] != ""
        assert new_tokens["refresh_token"] != refresh_token

        # Old refresh token should be invalid
        with pytest.raises(ValueError, match="already used"):
            await auth_service.refresh_tokens(refresh_token)

    async def test_token_reuse_detection(self, auth_service, test_user):
        """Test token reuse revokes entire family."""
        refresh_token = auth_service.generate_refresh_token(test_user)
        session = await auth_service.create_session(test_user, refresh_token)

        # Rotate once
        new_tokens = await auth_service.refresh_tokens(refresh_token)

        # Try to reuse old token (simulating theft)
        with pytest.raises(ValueError, match="Token family revoked"):
            await auth_service.refresh_tokens(refresh_token)

        # New token should also be revoked
        with pytest.raises(ValueError, match="Token family revoked"):
            await auth_service.refresh_tokens(new_tokens["refresh_token"])
```

### 8.3 Integration Tests

```python
# tests/test_auth_api.py
import pytest
from httpx import AsyncClient

class TestAuthenticationAPI:
    async def test_register_user_success(self, api_client: AsyncClient):
        """Test successful user registration."""
        response = await api_client.post("/api/auth/register", json={
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecureP@ssw0rd123",
            "display_name": "New User"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == "newuser"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["role"] == "viewer"  # Default role
        assert "password" not in data["user"]

    async def test_register_duplicate_username(self, api_client, test_user):
        """Test registration with duplicate username fails."""
        response = await api_client.post("/api/auth/register", json={
            "username": test_user.username,
            "email": "different@example.com",
            "password": "SecureP@ssw0rd123"
        })

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"].lower()

    async def test_login_success(self, api_client, test_user):
        """Test successful login returns tokens."""
        response = await api_client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": "TestPassword123!"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["username"] == test_user.username

        # Verify HTTP-only cookies set
        assert "access_token" in response.cookies
        assert response.cookies["access_token"]["httponly"] is True

    async def test_login_invalid_credentials(self, api_client, test_user):
        """Test login with wrong password fails."""
        response = await api_client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": "WrongPassword"
        })

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_access_protected_endpoint(self, api_client, authenticated_user):
        """Test accessing protected endpoint with valid token."""
        token = authenticated_user["access_token"]

        response = await api_client.get(
            "/api/prompts",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    async def test_access_protected_endpoint_no_token(self, api_client):
        """Test accessing protected endpoint without token fails."""
        response = await api_client.get("/api/prompts")

        assert response.status_code == 401

    async def test_refresh_token_rotation(self, api_client, authenticated_user):
        """Test token refresh rotates refresh token."""
        refresh_token = authenticated_user["refresh_token"]

        response = await api_client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != refresh_token  # Rotated

class TestRoleBasedAccess:
    async def test_viewer_cannot_create_prompt(self, api_client, viewer_user):
        """Test viewer role cannot create prompts."""
        response = await api_client.post(
            "/api/prompts",
            headers={"Authorization": f"Bearer {viewer_user['token']}"},
            json={"title": "Test", "prompt": "Content"}
        )

        assert response.status_code == 403

    async def test_editor_can_create_prompt(self, api_client, editor_user):
        """Test editor role can create prompts."""
        response = await api_client.post(
            "/api/prompts",
            headers={"Authorization": f"Bearer {editor_user['token']}"},
            json={"title": "Test", "prompt": "Content"}
        )

        assert response.status_code == 201

    async def test_admin_can_access_admin_endpoints(self, api_client, admin_user):
        """Test admin role can access admin endpoints."""
        response = await api_client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {admin_user['token']}"}
        )

        assert response.status_code == 200

    async def test_editor_cannot_access_admin_endpoints(self, api_client, editor_user):
        """Test editor role cannot access admin endpoints."""
        response = await api_client.get(
            "/api/admin/users",
            headers={"Authorization": f"Bearer {editor_user['token']}"}
        )

        assert response.status_code == 403

class TestPromptOwnership:
    async def test_user_can_edit_own_prompt(self, api_client, editor_user, user_prompt):
        """Test user can edit their own prompts."""
        response = await api_client.put(
            f"/api/prompts/{user_prompt.id}",
            headers={"Authorization": f"Bearer {editor_user['token']}"},
            json={"title": "Updated", "prompt": "New content", "commit_message": "Update"}
        )

        assert response.status_code == 200

    async def test_user_cannot_edit_others_prompt(self, api_client, editor_user, other_user_prompt):
        """Test user cannot edit another user's prompts."""
        response = await api_client.put(
            f"/api/prompts/{other_user_prompt.id}",
            headers={"Authorization": f"Bearer {editor_user['token']}"},
            json={"title": "Hacked", "prompt": "Should fail", "commit_message": "Hack"}
        )

        assert response.status_code == 403

    async def test_admin_can_edit_any_prompt(self, api_client, admin_user, other_user_prompt):
        """Test admin can edit any user's prompts."""
        response = await api_client.put(
            f"/api/prompts/{other_user_prompt.id}",
            headers={"Authorization": f"Bearer {admin_user['token']}"},
            json={"title": "Admin edit", "prompt": "Content", "commit_message": "Admin update"}
        )

        assert response.status_code == 200
```

### 8.4 Security Tests

```python
# tests/test_auth_security.py
class TestSecurityMeasures:
    async def test_rate_limiting_login(self, api_client):
        """Test login rate limiting after 5 failed attempts."""
        for i in range(5):
            await api_client.post("/api/auth/login", json={
                "username": "test",
                "password": "wrong"
            })

        # 6th attempt should be rate limited
        response = await api_client.post("/api/auth/login", json={
            "username": "test",
            "password": "wrong"
        })

        assert response.status_code == 429  # Too Many Requests

    async def test_account_lockout_after_failures(self, api_client, test_user):
        """Test account locks after 5 failed login attempts."""
        for i in range(5):
            await api_client.post("/api/auth/login", json={
                "username": test_user.username,
                "password": "WrongPassword"
            })

        # Account should be locked
        response = await api_client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": test_user.correct_password
        })

        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()

    async def test_password_not_returned_in_responses(self, api_client, test_user):
        """Test password_hash never appears in API responses."""
        # Login
        response = await api_client.post("/api/auth/login", json={
            "username": test_user.username,
            "password": "TestPassword123!"
        })
        assert "password" not in response.text.lower()
        assert "password_hash" not in response.text.lower()

        # Get profile
        token = response.json()["access_token"]
        response = await api_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert "password" not in response.text.lower()

    async def test_sql_injection_prevention(self, api_client):
        """Test SQL injection attempts are prevented."""
        # Try SQL injection in login
        response = await api_client.post("/api/auth/login", json={
            "username": "admin' OR '1'='1",
            "password": "anything"
        })

        assert response.status_code in [401, 404]  # Not successful

    async def test_xss_prevention_in_user_data(self, api_client):
        """Test XSS scripts in user input are sanitized."""
        response = await api_client.post("/api/auth/register", json={
            "username": "xss_test",
            "email": "xss@test.com",
            "password": "SecureP@ssw0rd123",
            "display_name": "<script>alert('XSS')</script>"
        })

        if response.status_code == 201:
            data = response.json()
            # Should be escaped or stripped
            assert "<script>" not in data["user"]["display_name"]
```

---

## 9. Configuration

### 9.1 Environment Variables

Add to `.env.example`:

```bash
# =============================================================================
# Authentication Configuration
# =============================================================================

# JWT Token Settings
JWT_PRIVATE_KEY_PATH=/secure/path/es256-private.pem
JWT_PUBLIC_KEY_PATH=/secure/path/es256-public.pem
JWT_ALGORITHM=ES256
ACCESS_TOKEN_EXPIRY_MINUTES=30
REFRESH_TOKEN_EXPIRY_DAYS=14

# Token issuer and audience (your domain)
JWT_ISSUER=https://promptvault.app
JWT_AUDIENCE=https://promptvault.app

# Password Security
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
CHECK_BREACHED_PASSWORDS=false  # Optional: HaveIBeenPwned integration

# Account Lockout
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
PERMANENT_LOCKOUT_ATTEMPTS=15

# Session Management
MAX_SESSIONS_PER_USER=5
SESSION_CLEANUP_INTERVAL_HOURS=24

# Rate Limiting (requires Redis)
RATE_LIMIT_ENABLED=true
REDIS_URL=redis://localhost:6379/0

# Email Configuration (for password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@promptvault.app
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=noreply@promptvault.app
SMTP_TLS=true

# Password Reset
PASSWORD_RESET_TOKEN_EXPIRY_HOURS=1
PASSWORD_RESET_RATE_LIMIT=3  # per hour per IP

# Registration
REGISTRATION_ENABLED=true
REQUIRE_EMAIL_VERIFICATION=false  # Future: email verification flow
DEFAULT_USER_ROLE=viewer  # viewer, editor, or admin

# Admin Account (for migration)
ADMIN_EMAIL=admin@promptvault.local
```

### 9.2 Configuration Class

```python
# src/config/auth_config.py
from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path

class AuthConfig(BaseSettings):
    """Authentication configuration from environment variables."""

    # JWT Settings
    jwt_private_key_path: Path
    jwt_public_key_path: Path
    jwt_algorithm: str = "ES256"
    access_token_expiry_minutes: int = 30
    refresh_token_expiry_days: int = 14
    jwt_issuer: str = "https://promptvault.app"
    jwt_audience: str = "https://promptvault.app"

    # Password Security
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True
    check_breached_passwords: bool = False

    # Account Lockout
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    permanent_lockout_attempts: int = 15

    # Session Management
    max_sessions_per_user: int = 5
    session_cleanup_interval_hours: int = 24

    # Rate Limiting
    rate_limit_enabled: bool = True
    redis_url: Optional[str] = None

    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_tls: bool = True

    # Password Reset
    password_reset_token_expiry_hours: int = 1
    password_reset_rate_limit: int = 3

    # Registration
    registration_enabled: bool = True
    require_email_verification: bool = False
    default_user_role: str = "viewer"

    # Admin
    admin_email: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False

auth_config = AuthConfig()
```

---

## 10. Acceptance Criteria

### 10.1 Functional Requirements

- ✅ **AC-AUTH-001**: User can register with username, email, password
- ✅ **AC-AUTH-002**: User can login and receive JWT access + refresh tokens
- ✅ **AC-AUTH-003**: Access token expires after 30 minutes
- ✅ **AC-AUTH-004**: Refresh token rotates on every use
- ✅ **AC-AUTH-005**: Token reuse detection revokes entire token family
- ✅ **AC-AUTH-006**: All existing API endpoints require authentication
- ✅ **AC-AUTH-007**: Users can only access their own prompts (unless admin)
- ✅ **AC-AUTH-008**: Admin can access all prompts and user management
- ✅ **AC-AUTH-009**: Password reset flow generates email with secure token
- ✅ **AC-AUTH-010**: Failed login attempts lock account after 5 attempts
- ✅ **AC-AUTH-011**: User can view and revoke active sessions
- ✅ **AC-AUTH-012**: Migration assigns all existing prompts to default admin

### 10.2 Security Requirements

- ✅ **AC-SEC-001**: Passwords hashed with Argon2id, never stored plaintext
- ✅ **AC-SEC-002**: Password policy enforces 12+ chars with complexity
- ✅ **AC-SEC-003**: JWT tokens signed with ES256 algorithm
- ✅ **AC-SEC-004**: HTTP-only cookies prevent XSS attacks on tokens
- ✅ **AC-SEC-005**: Rate limiting on login endpoint (5 attempts / 15 min)
- ✅ **AC-SEC-006**: CSRF protection via SameSite=Strict cookies
- ✅ **AC-SEC-007**: Token validation adds < 10ms latency
- ✅ **AC-SEC-008**: No sensitive data in JWT payload
- ✅ **AC-SEC-009**: Session cleanup job runs every 24 hours

### 10.3 Testing Requirements

- ✅ **AC-TEST-001**: ≥ 90% test coverage for authentication modules
- ✅ **AC-TEST-002**: 100% coverage for password hashing functions
- ✅ **AC-TEST-003**: 100% coverage for JWT generation/validation
- ✅ **AC-TEST-004**: Integration tests for all auth endpoints
- ✅ **AC-TEST-005**: Security tests for SQL injection, XSS, CSRF
- ✅ **AC-TEST-006**: Load tests for token validation performance

### 10.4 Documentation Requirements

- ✅ **AC-DOC-001**: API documentation updated with authentication
- ✅ **AC-DOC-002**: README.md includes authentication setup guide
- ✅ **AC-DOC-003**: Migration guide for existing deployments
- ✅ **AC-DOC-004**: Security best practices documented
- ✅ **AC-DOC-005**: i18n files include auth-related messages

---

## 11. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Key Compromise** | High | Low | Key rotation support, monitor for unusual activity |
| **Token Theft** | High | Medium | HTTP-only cookies, short expiry, rotation detection |
| **Brute Force Attacks** | Medium | High | Rate limiting, account lockout, CAPTCHA (future) |
| **Session Fixation** | Medium | Low | Regenerate session on login, token family tracking |
| **Password Reset Abuse** | Medium | Medium | Rate limiting, email verification, token expiry |
| **Privilege Escalation** | High | Low | Strict role checks, audit logging, principle of least privilege |
| **Database Breach** | High | Low | Argon2 hashing makes passwords infeasible to crack |
| **Migration Data Loss** | High | Low | Backup before migration, dry-run script, rollback plan |

---

## 12. Future Enhancements (Out of Scope)

1. **OAuth2/OpenID Connect**: Google, GitHub, Microsoft login
2. **Two-Factor Authentication (2FA)**: TOTP, SMS, backup codes
3. **Single Sign-On (SSO)**: SAML, LDAP integration
4. **Magic Link Login**: Passwordless email-based authentication
5. **WebAuthn/FIDO2**: Hardware security key support
6. **API Keys**: Service account tokens for programmatic access
7. **Audit Logging Dashboard**: Visual audit trail with filtering
8. **IP Whitelisting**: Restrict access by IP ranges
9. **Device Fingerprinting**: Enhanced session security
10. **Anomaly Detection**: ML-based suspicious activity detection

---

## 13. References & Resources

### Official Documentation
- [FastAPI Security Guide](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI OAuth2 with JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Argon2 Specification RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)

### Best Practices (2025)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT Security Best Practices 2025](https://jwt.app/blog/jwt-best-practices/)
- [Refresh Token Rotation Guide](https://www.serverion.com/uncategorized/refresh-token-rotation-best-practices-for-developers/)
- [FastAPI RBAC Implementation](https://www.permit.io/blog/fastapi-rbac-full-implementation-tutorial)

### Research Articles
- [Securing FastAPI with JWT (TestDriven.io)](https://testdriven.io/blog/fastapi-jwt-auth/)
- [FastAPI Security Best Practices 2025](https://blog.greeden.me/en/2025/07/29/fastapi-security-best-practices-from-authentication-authorization-to-cors/)
- [Auth0 Refresh Tokens Guide](https://auth0.com/blog/refresh-tokens-what-are-they-and-when-to-use-them/)

---

**Document Status**: DRAFT - Ready for Review
**Next Steps**: Review → Approval → Implementation Planning
**Estimated Implementation Effort**: 4-6 weeks
**Priority**: HIGH (Phase 2: Security & Architecture)
