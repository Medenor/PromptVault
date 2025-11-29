---
title: PromptVault Authentication System - Implementation Plan
version: 1.0
date_created: 2025-11-29
spec_ref: docs/SPECS/SPEC_AUTHENTICATION.md
status: READY FOR EXECUTION
estimated_effort: 4-6 weeks
priority: HIGH
---

# Authentication System Implementation Plan

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Database Schema & Models](#phase-1-database-schema--models)
4. [Phase 2: Core Authentication Service](#phase-2-core-authentication-service)
5. [Phase 3: API Endpoints](#phase-3-api-endpoints)
6. [Phase 4: Frontend Implementation](#phase-4-frontend-implementation)
7. [Phase 5: Testing & Security](#phase-5-testing--security)
8. [Phase 6: Migration & Deployment](#phase-6-migration--deployment)
9. [Task Breakdown & Estimates](#task-breakdown--estimates)
10. [Dependencies & Blockers](#dependencies--blockers)
11. [Quality Gates](#quality-gates)
12. [Rollback Plan](#rollback-plan)

---

## Overview

### Objectives

Transform PromptVault from a single-user local application to a secure multi-user web application with:
- JWT-based authentication with token rotation
- Role-based access control (viewer, editor, admin)
- Secure password management with Argon2id hashing
- Session management and token revocation
- Password reset flow
- User profile management
- Admin user management interface

### Success Criteria

1. **Security**: All endpoints protected, zero plaintext passwords
2. **Functionality**: All AC-AUTH-* and AC-SEC-* criteria met (see SPEC_AUTHENTICATION.md §10)
3. **Performance**: Token validation < 10ms, no degradation to existing features
4. **Testing**: ≥ 90% coverage for auth modules, all security tests pass
5. **Migration**: All existing prompts assigned to admin, zero data loss
6. **Documentation**: Complete API docs, migration guide, user guide

### Timeline Overview

| Phase | Duration | Dependencies | Deliverables |
|-------|----------|--------------|--------------|
| Phase 1: Database | 3-4 days | None | Enhanced User model, UserSession, PasswordResetToken tables, Alembic migrations |
| Phase 2: Core Service | 5-7 days | Phase 1 | AuthService, password hashing, JWT generation/validation, token rotation |
| Phase 3: API Endpoints | 5-7 days | Phase 2 | All auth endpoints, RBAC middleware, protected routes |
| Phase 4: Frontend | 7-10 days | Phase 3 | Login/register pages, token management, auth middleware |
| Phase 5: Testing | 5-7 days | Phases 2-4 | 90% test coverage, security tests, performance tests |
| Phase 6: Migration | 3-5 days | Phases 1-5 | Migration scripts, deployment docs, rollback plan |

**Total Estimated Duration**: 28-40 days (4-6 weeks)

---

## Prerequisites

### 1. Development Environment Setup

```bash
# Install dependencies
pip install argon2-cffi==23.1.0
pip install PyJWT==2.8.0
pip install cryptography==41.0.7
pip install python-multipart==0.0.6
pip install slowapi==0.1.9  # Rate limiting
pip install redis==5.0.1  # For rate limiting backend
pip install httpx==0.25.2  # For testing and email
pip install pytest-asyncio==0.21.1

# Generate ECDSA keys for JWT signing
mkdir -p /secure/keys
openssl ecparam -name prime256v1 -genkey -noout -out /secure/keys/es256-private.pem
openssl ec -in /secure/keys/es256-private.pem -pubout -out /secure/keys/es256-public.pem
chmod 600 /secure/keys/es256-private.pem
chmod 644 /secure/keys/es256-public.pem

# Update .env with key paths
echo "JWT_PRIVATE_KEY_PATH=/secure/keys/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=/secure/keys/es256-public.pem" >> .env
```

### 2. Update pyproject.toml

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "argon2-cffi>=23.1.0",
    "PyJWT>=2.8.0",
    "cryptography>=41.0.7",
    "python-multipart>=0.0.6",
    "slowapi>=0.1.9",
    "redis>=5.0.1",
]

[project.optional-dependencies]
test = [
    # ... existing test dependencies ...
    "pytest-asyncio>=0.21.1",
    "freezegun>=1.4.0",  # For testing token expiration
]
```

### 3. Configuration Validation

- [ ] Environment variables defined in `.env.example`
- [ ] JWT keys generated and secured
- [ ] Redis instance available (local or Docker)
- [ ] SMTP server configured (for password reset)
- [ ] Database backup created

---

## Phase 1: Database Schema & Models

**Duration**: 3-4 days
**Owner**: Backend Developer
**Priority**: CRITICAL (blocks all other phases)

### Task 1.1: Enhance User Model

**File**: `src/db/models/user.py`

**Changes**:
```python
# Add authentication fields to existing User model
class User(Base):
    # ... existing fields ...

    # NEW: Authentication fields
    password_hash = Column(String(255), nullable=False)
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    password_changed_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    password_resets = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    # Make email unique and required
    email = Column(String(255), unique=True, nullable=False, index=True)
```

**Acceptance**:
- [ ] Model compiles without errors
- [ ] All new fields have appropriate types and constraints
- [ ] Relationships defined correctly
- [ ] No breaking changes to existing User functionality

### Task 1.2: Create UserSession Model

**File**: `src/db/models/user_session.py` (NEW)

**Implementation**:
```python
"""User session model for JWT token family tracking."""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.db.base import Base


class UserSession(Base):
    """Tracks active user sessions for token rotation and revocation.

    Each session represents a login instance with a unique token family.
    Token rotation creates new tokens within the same family.
    Token reuse detection triggers family-wide revocation.
    """
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_family_id = Column(String(36), nullable=False, unique=True, index=True)
    refresh_token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(String(500))
    is_revoked = Column(Boolean, default=False, index=True)
    revoked_at = Column(DateTime(timezone=True))
    revocation_reason = Column(String(200))  # "logout", "token_reuse", "password_change", etc.

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Composite indices for performance
    __table_args__ = (
        Index('idx_sessions_user_active', 'user_id', 'is_revoked', 'expires_at'),
        Index('idx_sessions_cleanup', 'expires_at', 'is_revoked'),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, family={self.token_family_id})>"
```

**Acceptance**:
- [ ] Model includes all required fields from spec
- [ ] Indices created for query performance
- [ ] Relationship to User model correct
- [ ] CASCADE delete configured

### Task 1.3: Create PasswordResetToken Model

**File**: `src/db/models/password_reset_token.py` (NEW)

**Implementation**: (Similar structure to UserSession, see spec §2.3.3)

### Task 1.4: Create Alembic Migrations

**Files**: `alembic/versions/XXX_add_authentication.py` (3 migrations)

**Migration 1**: Add auth fields to users table
```python
"""Add authentication fields to users table

Revision ID: 001_add_auth_fields
Revises: <previous_migration>
Create Date: 2025-11-29
"""

from alembic import op
import sqlalchemy as sa


def upgrade():
    # Add nullable columns first (existing users have no password yet)
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), server_default='false'))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true'))
    op.add_column('users', sa.Column('last_login', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('failed_login_attempts', sa.Integer(), server_default='0'))
    op.add_column('users', sa.Column('locked_until', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('password_changed_at', sa.DateTime(timezone=True)))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True)))

    # Create indices
    op.create_index('idx_users_is_active', 'users', ['is_active'])

    # Make email unique if not already
    # Note: This requires data migration first if duplicates exist
    # op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index('idx_users_email', 'users', ['email'], unique=True)


def downgrade():
    op.drop_index('idx_users_email', 'users')
    op.drop_index('idx_users_is_active', 'users')
    op.drop_column('users', 'updated_at')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
    op.drop_column('users', 'last_login')
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password_hash')
```

**Migration 2**: Create user_sessions table
**Migration 3**: Create password_reset_tokens table

**Acceptance**:
- [ ] Migrations run successfully on clean database
- [ ] Migrations run successfully on existing database (with data)
- [ ] Downgrades work correctly
- [ ] No data loss during migration
- [ ] All indices created

### Task 1.5: Create UserRepository

**File**: `src/db/repositories/user_repository.py` (NEW)

**Methods**:
```python
class UserRepository(BaseRepository[User]):
    """Repository for user data access."""

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create new user with hashed password."""

    async def update_password(self, user_id: str, password_hash: str) -> None:
        """Update user's password hash."""

    async def increment_failed_login(self, user_id: str) -> int:
        """Increment failed login attempts, return new count."""

    async def reset_failed_login(self, user_id: str) -> None:
        """Reset failed login attempts to 0."""

    async def lock_account(self, user_id: str, until: datetime) -> None:
        """Lock user account until specified time."""

    async def deactivate_user(self, user_id: str) -> None:
        """Deactivate user account."""

    async def get_all_users(
        self,
        page: int = 1,
        limit: int = 50,
        role: Optional[str] = None,
        active: Optional[bool] = None
    ) -> Tuple[List[User], int]:
        """Get paginated user list with filters."""
```

**Acceptance**:
- [ ] All CRUD operations implemented
- [ ] Proper error handling
- [ ] Database transactions managed
- [ ] Unit tests written (≥ 95% coverage)

### Task 1.6: Create SessionRepository

**File**: `src/db/repositories/session_repository.py` (NEW)

**Methods**:
```python
class SessionRepository(BaseRepository[UserSession]):
    """Repository for user session management."""

    async def create_session(self, session_data: Dict[str, Any]) -> UserSession:
        """Create new session."""

    async def get_by_token_family(self, family_id: str) -> Optional[UserSession]:
        """Get session by token family ID."""

    async def update_refresh_token(self, family_id: str, new_token_hash: str) -> None:
        """Update refresh token hash for session."""

    async def revoke_session(self, session_id: str, reason: str) -> None:
        """Revoke specific session."""

    async def revoke_user_sessions(self, user_id: str, except_session_id: Optional[str] = None, reason: str = "manual") -> int:
        """Revoke all sessions for user, optionally except one. Returns count."""

    async def revoke_token_family(self, family_id: str, reason: str = "token_reuse") -> None:
        """Revoke entire token family (for reuse detection)."""

    async def get_active_sessions(self, user_id: str) -> List[UserSession]:
        """Get all active sessions for user."""

    async def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions. Returns count deleted."""

    async def enforce_session_limit(self, user_id: str, max_sessions: int) -> None:
        """Revoke oldest sessions if limit exceeded."""
```

**Acceptance**:
- [ ] All session operations implemented
- [ ] Token family tracking works correctly
- [ ] Session cleanup job ready
- [ ] Unit tests written (≥ 95% coverage)

### Task 1.7: Update Models __init__.py

**File**: `src/db/models/__init__.py`

Add exports for new models:
```python
from .user_session import UserSession
from .password_reset_token import PasswordResetToken

__all__ = [
    # ... existing exports ...
    "UserSession",
    "PasswordResetToken",
]
```

---

## Phase 2: Core Authentication Service

**Duration**: 5-7 days
**Owner**: Backend Developer
**Dependencies**: Phase 1 complete
**Priority**: CRITICAL

### Task 2.1: Create Configuration Class

**File**: `src/config/auth_config.py` (NEW)

**Implementation**: See SPEC_AUTHENTICATION.md §9.2

**Acceptance**:
- [ ] All auth config params loaded from env
- [ ] Validation for required params (JWT keys, etc.)
- [ ] Default values sensible
- [ ] Config accessible via singleton

### Task 2.2: Password Security Module

**File**: `src/services/auth/password_service.py` (NEW)

**Class**: `PasswordService`

**Methods**:
```python
class PasswordService:
    """Handles password hashing, verification, and policy enforcement."""

    def __init__(self):
        """Initialize Argon2 hasher with production settings."""
        from argon2 import PasswordHasher
        self.ph = PasswordHasher(
            time_cost=3,
            memory_cost=65536,  # 64 MiB
            parallelism=4,
            hash_len=32,
            salt_len=16,
            encoding='utf-8',
            type=argon2.Type.ID
        )

    def hash_password(self, password: str) -> str:
        """Hash password using Argon2id.

        Args:
            password: Plaintext password

        Returns:
            Argon2 hash string

        Raises:
            ValueError: If password doesn't meet policy
        """
        self.validate_password_policy(password)
        return self.ph.hash(password)

    def verify_password(self, hash: str, password: str) -> bool:
        """Verify password against hash.

        Args:
            hash: Argon2 hash string
            password: Plaintext password to verify

        Returns:
            True if password matches

        Raises:
            argon2.exceptions.VerifyMismatchError: If password incorrect
        """
        try:
            self.ph.verify(hash, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            raise

    def validate_password_policy(self, password: str) -> None:
        """Validate password meets security policy.

        Policy:
        - Minimum 12 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 digit
        - At least 1 special character

        Args:
            password: Password to validate

        Raises:
            ValueError: If policy not met, with specific message
        """
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")

        if not re.search(r'[A-Z]', password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r'[a-z]', password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r'\d', password):
            raise ValueError("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            raise ValueError("Password must contain at least one special character")

    async def is_password_breached(self, password: str) -> bool:
        """Check if password appears in breach database (optional).

        Uses HaveIBeenPwned API with k-anonymity.
        Only first 5 chars of SHA-1 hash sent to API.

        Args:
            password: Password to check

        Returns:
            True if password found in breach database
        """
        if not auth_config.check_breached_passwords:
            return False

        import hashlib
        import httpx

        sha1 = hashlib.sha1(password.encode()).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.pwnedpasswords.com/range/{prefix}",
                    timeout=2.0
                )
                if response.status_code != 200:
                    return False  # Fail open

                hashes = {line.split(":")[0]: int(line.split(":")[1])
                          for line in response.text.splitlines()}
                return suffix in hashes
        except Exception:
            return False  # Fail open on network error
```

**Unit Tests**: `tests/test_password_service.py`
- [ ] Test password hashing produces unique hashes
- [ ] Test correct password verification
- [ ] Test incorrect password rejection
- [ ] Test all policy validation rules
- [ ] Test breached password detection
- [ ] Target: 100% coverage

### Task 2.3: JWT Token Service

**File**: `src/services/auth/jwt_service.py` (NEW)

**Class**: `JWTService`

**Methods**:
```python
class JWTService:
    """Handles JWT token generation, validation, and key management."""

    def __init__(self):
        """Load ECDSA keys from configured paths."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        # Load private key
        with open(auth_config.jwt_private_key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )

        # Load public key
        with open(auth_config.jwt_public_key_path, 'rb') as f:
            self.public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )

    def generate_access_token(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generate JWT access token.

        Args:
            user: User object
            expires_delta: Optional custom expiration

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=auth_config.access_token_expiry_minutes)

        now = datetime.utcnow()
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "type": "access",
            "iat": now,
            "nbf": now,
            "exp": now + expires_delta,
            "jti": str(uuid.uuid4()),
            "iss": auth_config.jwt_issuer,
            "aud": auth_config.jwt_audience,
        }

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=auth_config.jwt_algorithm
        )
        return token

    def generate_refresh_token(
        self,
        user: User,
        token_family_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generate JWT refresh token with family ID.

        Args:
            user: User object
            token_family_id: UUID for token family tracking
            expires_delta: Optional custom expiration

        Returns:
            JWT refresh token string
        """
        if expires_delta is None:
            expires_delta = timedelta(days=auth_config.refresh_token_expiry_days)

        now = datetime.utcnow()
        payload = {
            "sub": user.id,
            "type": "refresh",
            "family": token_family_id,
            "iat": now,
            "nbf": now,
            "exp": now + expires_delta,
            "jti": str(uuid.uuid4()),
            "iss": auth_config.jwt_issuer,
            "aud": auth_config.jwt_audience,
        }

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=auth_config.jwt_algorithm
        )
        return token

    def decode_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Decode and validate JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded payload dict

        Raises:
            jwt.ExpiredSignatureError: Token expired
            jwt.InvalidTokenError: Invalid token
            ValueError: Wrong token type
        """
        payload = jwt.decode(
            token,
            self.public_key,
            algorithms=[auth_config.jwt_algorithm],
            audience=auth_config.jwt_audience,
            issuer=auth_config.jwt_issuer
        )

        if payload.get("type") != token_type:
            raise ValueError(f"Expected {token_type} token, got {payload.get('type')}")

        return payload

    def extract_user_id(self, token: str) -> str:
        """Extract user ID from token without full validation.

        Use for non-critical operations only.

        Args:
            token: JWT token string

        Returns:
            User ID string
        """
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload.get("sub")
```

**Unit Tests**: `tests/test_jwt_service.py`
- [ ] Test access token generation
- [ ] Test refresh token generation with family
- [ ] Test token decoding
- [ ] Test expired token rejection
- [ ] Test invalid signature rejection
- [ ] Test wrong token type rejection
- [ ] Target: 100% coverage

### Task 2.4: Main Authentication Service

**File**: `src/services/auth/auth_service.py` (NEW)

**Class**: `AuthService`

**Methods**:
```python
class AuthService:
    """Main authentication service orchestrating all auth operations."""

    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        password_service: PasswordService,
        jwt_service: JWTService
    ):
        """Initialize with dependencies."""
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.logger = logging_service.get_logger(__name__)
        self.audit_logger = logging_service.get_audit_logger()

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        role: str = "viewer"
    ) -> User:
        """Register new user.

        Args:
            username: Unique username
            email: Unique email
            password: Plaintext password (will be hashed)
            display_name: Optional display name
            role: User role (default: viewer)

        Returns:
            Created User object

        Raises:
            ValueError: Username/email exists, password policy violation
        """
        # Check username uniqueness
        existing = await self.user_repo.get_by_username(username)
        if existing:
            raise ValueError("Username already exists")

        # Check email uniqueness
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already exists")

        # Validate password policy
        self.password_service.validate_password_policy(password)

        # Check breached passwords (optional)
        if await self.password_service.is_password_breached(password):
            raise ValueError("Password has been compromised in a data breach. Please choose a different password.")

        # Hash password
        password_hash = self.password_service.hash_password(password)

        # Create user
        user = await self.user_repo.create_user({
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "display_name": display_name,
            "role": role,
            "email_verified": False,
            "is_active": True,
            "created_at": datetime.utcnow()
        })

        # Audit log
        await self.audit_logger.log(
            "user_registered",
            user_id=user.id,
            username=username,
            email=email,
            role=role
        )

        return user

    async def login(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate user and create session.

        Args:
            username: Username or email
            password: Plaintext password
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            Dict with access_token, refresh_token, user data

        Raises:
            ValueError: Invalid credentials, account locked, inactive
        """
        # Get user (try username first, then email)
        user = await self.user_repo.get_by_username(username)
        if not user:
            user = await self.user_repo.get_by_email(username)

        if not user:
            # Log failed attempt
            await self.logger.warning(f"Login attempt for non-existent user: {username}")
            raise ValueError("Invalid username or password")

        # Check if account is active
        if not user.is_active:
            raise ValueError("Account is deactivated. Contact administrator.")

        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            minutes_left = int((user.locked_until - datetime.utcnow()).total_seconds() / 60)
            raise ValueError(f"Account is locked. Try again in {minutes_left} minutes.")

        # Verify password
        try:
            self.password_service.verify_password(user.password_hash, password)
        except argon2.exceptions.VerifyMismatchError:
            # Increment failed attempts
            failed_count = await self.user_repo.increment_failed_login(user.id)

            # Lock account if threshold reached
            if failed_count >= auth_config.permanent_lockout_attempts:
                await self.user_repo.deactivate_user(user.id)
                await self.audit_logger.log(
                    "account_locked_permanent",
                    user_id=user.id,
                    reason="too_many_failed_logins",
                    failed_attempts=failed_count
                )
                raise ValueError("Account has been deactivated due to too many failed login attempts. Contact administrator.")

            elif failed_count >= auth_config.max_login_attempts * 2:
                lockout_duration = timedelta(hours=1)
                await self.user_repo.lock_account(user.id, datetime.utcnow() + lockout_duration)
                raise ValueError("Too many failed login attempts. Account locked for 1 hour.")

            elif failed_count >= auth_config.max_login_attempts:
                lockout_duration = timedelta(minutes=auth_config.lockout_duration_minutes)
                await self.user_repo.lock_account(user.id, datetime.utcnow() + lockout_duration)
                raise ValueError(f"Too many failed login attempts. Account locked for {auth_config.lockout_duration_minutes} minutes.")

            raise ValueError("Invalid username or password")

        # Password correct - reset failed attempts
        await self.user_repo.reset_failed_login(user.id)

        # Generate tokens
        token_family_id = str(uuid.uuid4())
        access_token = self.jwt_service.generate_access_token(user)
        refresh_token = self.jwt_service.generate_refresh_token(user, token_family_id)

        # Create session
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        session = await self.session_repo.create_session({
            "user_id": user.id,
            "token_family_id": token_family_id,
            "refresh_token_hash": refresh_token_hash,
            "expires_at": datetime.utcnow() + timedelta(days=auth_config.refresh_token_expiry_days),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow(),
            "last_used_at": datetime.utcnow()
        })

        # Enforce session limit
        await self.session_repo.enforce_session_limit(user.id, auth_config.max_sessions_per_user)

        # Update last login
        user.last_login = datetime.utcnow()
        await self.user_repo.save(user)

        # Audit log
        await self.audit_logger.log(
            "user_login",
            user_id=user.id,
            username=user.username,
            ip_address=ip_address,
            session_id=session.id
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": auth_config.access_token_expiry_minutes * 60,
            "user": self._serialize_user(user)
        }

    async def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, str]:
        """Refresh access token using refresh token (with rotation).

        Args:
            refresh_token: Current refresh token
            ip_address: Client IP

        Returns:
            Dict with new access_token and refresh_token

        Raises:
            ValueError: Invalid token, expired, revoked, reuse detected
        """
        # Decode refresh token
        try:
            payload = self.jwt_service.decode_token(refresh_token, token_type="refresh")
        except jwt.ExpiredSignatureError:
            raise ValueError("Refresh token expired. Please login again.")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")

        user_id = payload["sub"]
        family_id = payload["family"]

        # Get session
        session = await self.session_repo.get_by_token_family(family_id)
        if not session:
            raise ValueError("Session not found")

        # Check if session revoked
        if session.is_revoked:
            raise ValueError("Session has been revoked. Please login again.")

        # Check if session expired
        if session.expires_at < datetime.utcnow():
            raise ValueError("Session expired. Please login again.")

        # Verify refresh token hash (CRITICAL for reuse detection)
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        if session.refresh_token_hash != refresh_token_hash:
            # Token reuse detected! Revoke entire family
            await self.session_repo.revoke_token_family(
                family_id,
                reason="token_reuse_detected"
            )
            await self.audit_logger.log(
                "token_reuse_detected",
                user_id=user_id,
                session_id=session.id,
                token_family_id=family_id,
                ip_address=ip_address,
                severity="critical"
            )
            raise ValueError("Token reuse detected. All sessions revoked for security. Please login again.")

        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        # Generate new tokens (SAME family ID)
        new_access_token = self.jwt_service.generate_access_token(user)
        new_refresh_token = self.jwt_service.generate_refresh_token(user, family_id)

        # Update session with new refresh token hash
        new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        await self.session_repo.update_refresh_token(family_id, new_refresh_token_hash)

        # Update last used
        session.last_used_at = datetime.utcnow()
        await self.session_repo.save(session)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": auth_config.access_token_expiry_minutes * 60
        }

    async def logout(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        revoke_all: bool = False
    ) -> None:
        """Logout user by revoking session(s).

        Args:
            user_id: User ID
            session_id: Specific session to revoke (None = current)
            revoke_all: Revoke all user sessions
        """
        if revoke_all:
            count = await self.session_repo.revoke_user_sessions(user_id, reason="logout_all")
            await self.audit_logger.log(
                "user_logout_all",
                user_id=user_id,
                sessions_revoked=count
            )
        elif session_id:
            await self.session_repo.revoke_session(session_id, reason="logout")
            await self.audit_logger.log(
                "user_logout",
                user_id=user_id,
                session_id=session_id
            )
        else:
            # Revoke all sessions (if no specific session ID)
            count = await self.session_repo.revoke_user_sessions(user_id, reason="logout")
            await self.audit_logger.log(
                "user_logout",
                user_id=user_id,
                sessions_revoked=count
            )

    def _serialize_user(self, user: User) -> Dict[str, Any]:
        """Serialize user for API response (NEVER include password_hash)."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "email_verified": user.email_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
```

**Unit Tests**: `tests/test_auth_service.py`
- [ ] Test user registration success
- [ ] Test duplicate username/email rejection
- [ ] Test password policy enforcement
- [ ] Test login success
- [ ] Test invalid credentials
- [ ] Test account lockout after failures
- [ ] Test token refresh with rotation
- [ ] Test token reuse detection
- [ ] Test logout
- [ ] Target: ≥ 95% coverage

### Task 2.5: Password Reset Service

**File**: `src/services/auth/password_reset_service.py` (NEW)

**Methods**:
- `request_password_reset(email: str) -> None`
- `verify_reset_token(token: str) -> User`
- `reset_password(token: str, new_password: str) -> None`
- Email sending integration (SMTP)

---

## Phase 3: API Endpoints

**Duration**: 5-7 days
**Owner**: Backend Developer
**Dependencies**: Phase 2 complete
**Priority**: HIGH

### Task 3.1: Pydantic Request/Response Models

**File**: `src/web/models/auth_requests.py` (NEW)

**Models**:
```python
from pydantic import BaseModel, Field, field_validator
import re

class RegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=12, max_length=128)
    display_name: Optional[str] = Field(None, max_length=200)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format")
        return v.lower()

class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

class RefreshTokenRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(...)

class LogoutRequest(BaseModel):
    """Logout request."""
    revoke_all_sessions: bool = Field(default=False)

class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(...)
    new_password: str = Field(..., min_length=12, max_length=128)

class PasswordResetRequestModel(BaseModel):
    """Password reset initiation request."""
    email: str = Field(...)

class PasswordResetConfirmModel(BaseModel):
    """Password reset confirmation."""
    token: str = Field(...)
    new_password: str = Field(..., min_length=12, max_length=128)

class UpdateProfileRequest(BaseModel):
    """Update user profile."""
    display_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=255)

class UpdateUserRoleRequest(BaseModel):
    """Admin: Update user role."""
    role: Literal["viewer", "editor", "admin"] = Field(...)

class UpdateUserStatusRequest(BaseModel):
    """Admin: Activate/deactivate user."""
    is_active: bool = Field(...)

class DeleteUserRequest(BaseModel):
    """Admin: Delete user with options."""
    transfer_prompts_to: Optional[str] = Field(None)
    permanent: bool = Field(default=False)
```

### Task 3.2: FastAPI Security Dependencies

**File**: `src/web/dependencies/auth.py` (NEW)

**Dependencies**:
```python
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated, Optional
import jwt

from src.db.models.user import User
from src.services.auth.auth_service import AuthService
from src.services.auth.jwt_service import JWTService
from src.db.repositories.user_repository import UserRepository

security = HTTPBearer()

# Singleton instances (initialized in app startup)
_auth_service: Optional[AuthService] = None
_jwt_service: Optional[JWTService] = None
_user_repo: Optional[UserRepository] = None

def init_auth_dependencies(auth_service, jwt_service, user_repo):
    """Initialize auth dependencies (call from app.py startup)."""
    global _auth_service, _jwt_service, _user_repo
    _auth_service = auth_service
    _jwt_service = jwt_service
    _user_repo = user_repo


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    request: Request
) -> User:
    """Extract and validate JWT token, return authenticated user.

    This dependency can be used on any route to require authentication.

    Usage:
        @app.get("/api/prompts")
        async def get_prompts(user: Annotated[User, Depends(get_current_user)]):
            # user is authenticated User object
            ...

    Args:
        credentials: HTTP Bearer token from Authorization header
        request: FastAPI request object

    Returns:
        Authenticated User object

    Raises:
        HTTPException 401: Invalid or expired token
        HTTPException 403: User inactive or not found
    """
    token = credentials.credentials

    try:
        # Decode and validate token
        payload = _jwt_service.decode_token(token, token_type="access")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )

        # Fetch user from database
        user = await _user_repo.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        # Add user to request state (for logging, audit)
        request.state.user = user

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Get current user and ensure they are active.

    This is essentially same as get_current_user (since we check is_active there),
    but provides semantic clarity.
    """
    return user


def require_role(required_role: str):
    """Dependency factory for role-based access control.

    Creates a dependency that checks if user has required role level.
    Role hierarchy: viewer < editor < admin

    Usage:
        @app.post("/api/backups")
        async def create_backup(user: Annotated[User, Depends(require_role("admin"))]):
            # Only admins can reach this
            ...

    Args:
        required_role: Minimum role required ("viewer", "editor", "admin")

    Returns:
        Dependency function that returns User if authorized

    Raises:
        HTTPException 403: Insufficient permissions
    """
    role_hierarchy = {
        "viewer": 1,
        "editor": 2,
        "admin": 3
    }

    async def role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 99)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )

        return user

    return role_checker


async def get_optional_user(
    request: Request
) -> Optional[User]:
    """Get current user if token provided, otherwise None.

    Use for optional authentication (e.g., public pages with user-specific content).

    Args:
        request: FastAPI request

    Returns:
        User object if authenticated, None otherwise
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    try:
        payload = _jwt_service.decode_token(token, token_type="access")
        user_id = payload.get("sub")
        if user_id:
            user = await _user_repo.get_by_id(user_id)
            if user and user.is_active:
                return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass

    return None
```

### Task 3.3: Authentication Routes

**File**: `src/web/routers/auth.py` (NEW)

**Endpoints**:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from typing import Annotated

from src.web.models.auth_requests import (
    RegisterRequest, LoginRequest, RefreshTokenRequest,
    LogoutRequest, ChangePasswordRequest,
    PasswordResetRequestModel, PasswordResetConfirmModel
)
from src.web.dependencies.auth import get_current_user, require_role
from src.services.auth.auth_service import AuthService
from src.db.models.user import User

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Dependency injection (initialized in app.py)
def get_auth_service() -> AuthService:
    """Get AuthService instance from app state."""
    # Implementation depends on app structure
    ...


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Register new user account.

    Creates user with default 'viewer' role.
    Password must meet security policy requirements.

    Returns:
        User data (without password hash)
    """
    try:
        user = await auth_service.register_user(
            username=request.username,
            email=request.email,
            password=request.password,
            display_name=request.display_name
        )

        return {
            "user": auth_service._serialize_user(user),
            "message": "Registration successful"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login")
async def login(
    request_data: LoginRequest,
    http_request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Authenticate user and return JWT tokens.

    Sets HTTP-only cookies for tokens.
    Also returns tokens in response body for API clients.

    Returns:
        access_token, refresh_token, user data
    """
    try:
        # Get client IP and user agent
        ip_address = http_request.client.host if http_request.client else None
        user_agent = http_request.headers.get("User-Agent")

        # Authenticate
        result = await auth_service.login(
            username=request_data.username,
            password=request_data.password,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Set HTTP-only cookies
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=True,  # HTTPS only
            samesite="strict",
            max_age=result["expires_in"],
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=auth_config.refresh_token_expiry_days * 24 * 60 * 60,
            path="/api/auth"  # Restrict to auth endpoints
        )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh")
async def refresh_token(
    request_data: Optional[RefreshTokenRequest] = None,
    http_request: Request = None,
    response: Response = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None
):
    """Refresh access token using refresh token.

    Accepts refresh token from:
    1. HTTP-only cookie (preferred)
    2. Request body

    Returns new access and refresh tokens (with rotation).
    """
    # Try cookie first, then request body
    refresh_token = http_request.cookies.get("refresh_token")
    if not refresh_token and request_data:
        refresh_token = request_data.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )

    try:
        ip_address = http_request.client.host if http_request.client else None
        result = await auth_service.refresh_tokens(refresh_token, ip_address)

        # Update cookies
        response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=result["expires_in"],
            path="/"
        )

        response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=True,
            samesite="strict",
            max_age=auth_config.refresh_token_expiry_days * 24 * 60 * 60,
            path="/api/auth"
        )

        return result

    except ValueError as e:
        # Clear cookies on error
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    request_data: LogoutRequest,
    user: Annotated[User, Depends(get_current_user)],
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Logout user by revoking session(s)."""
    await auth_service.logout(
        user_id=user.id,
        revoke_all=request_data.revoke_all_sessions
    )

    # Clear cookies
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/auth")

    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_profile(
    user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Get current authenticated user's profile."""
    # Get additional stats
    prompt_count = await prompt_repository.count_by_user(user.id)
    favorite_count = await prompt_repository.count_favorites_by_user(user.id)

    user_data = auth_service._serialize_user(user)
    user_data["prompt_count"] = prompt_count
    user_data["favorite_count"] = favorite_count

    return user_data


@router.put("/me")
async def update_profile(
    request_data: UpdateProfileRequest,
    user: Annotated[User, Depends(get_current_user)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)]
):
    """Update current user's profile."""
    # Implementation
    ...


@router.post("/me/change-password")
async def change_password(
    request_data: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
    """Change current user's password."""
    # Implementation
    ...


@router.post("/password-reset/request")
async def request_password_reset(
    request_data: PasswordResetRequestModel,
    password_reset_service: Annotated[PasswordResetService, Depends(get_password_reset_service)]
):
    """Request password reset email."""
    # Implementation
    ...


@router.post("/password-reset/confirm")
async def confirm_password_reset(
    request_data: PasswordResetConfirmModel,
    password_reset_service: Annotated[PasswordResetService, Depends(get_password_reset_service)]
):
    """Confirm password reset with token."""
    # Implementation
    ...
```

### Task 3.4: Admin Routes

**File**: `src/web/routers/admin.py` (NEW)

**Endpoints**: All require `Depends(require_role("admin"))`
- `GET /api/admin/users` - List all users (paginated)
- `GET /api/admin/users/{user_id}` - Get user details
- `PUT /api/admin/users/{user_id}/role` - Update user role
- `PUT /api/admin/users/{user_id}/status` - Activate/deactivate user
- `DELETE /api/admin/users/{user_id}` - Delete user

### Task 3.5: Protect Existing Routes

**File**: `src/web/app.py`

**Changes**:
```python
from src.web.dependencies.auth import get_current_user, require_role
from src.db.models.user import User
from typing import Annotated

# Protect all prompt endpoints
@app.get("/api/prompts")
async def list_prompts(
    user: Annotated[User, Depends(get_current_user)],  # ADD THIS
    # ... existing params ...
):
    # Filter prompts by user_id for non-admins
    if user.role != "admin":
        prompts = await prompt_service.get_prompts_by_user(user.id)
    else:
        prompts = await prompt_service.get_all_prompts()
    # ...

@app.post("/api/prompts")
async def create_prompt(
    user: Annotated[User, Depends(require_role("editor"))],  # Editors and admins only
    request_data: PromptCreateRequest,
    # ...
):
    # Auto-set owner
    prompt_id = await prompt_service.create_prompt(
        user_id=user.id,  # ADD THIS
        **request_data.dict()
    )
    # ...

@app.put("/api/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    user: Annotated[User, Depends(require_role("editor"))],
    request_data: PromptUpdateRequest,
    # ...
):
    # Verify ownership
    prompt = await verify_prompt_ownership(prompt_id, user)
    # ... proceed with update

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    user: Annotated[User, Depends(require_role("editor"))],
    # ...
):
    # Verify ownership
    prompt = await verify_prompt_ownership(prompt_id, user)
    # ... proceed with delete

# Admin-only endpoints
@app.post("/api/backups")
async def create_backup(
    user: Annotated[User, Depends(require_role("admin"))],
    # ...
):
    # Only admins can create backups
    ...

# Add helper function
async def verify_prompt_ownership(prompt_id: int, user: User) -> Prompt:
    """Verify user owns prompt or is admin."""
    prompt = await prompt_repository.get_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if user.role != "admin" and prompt.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to access this prompt"
        )

    return prompt
```

**Checklist**:
- [ ] All `/api/prompts/*` routes protected
- [ ] All `/api/prompts/{id}/versions/*` routes protected
- [ ] All `/api/backups/*` routes admin-only
- [ ] All `/api/import` and `/api/export` routes protected
- [ ] Ownership checks on edit/delete operations

### Task 3.6: Rate Limiting Middleware

**File**: `src/web/middleware/rate_limit.py` (NEW)

**Implementation using slowapi**:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, FastAPI
import redis.asyncio as redis

# Initialize Redis connection
redis_client = redis.from_url(auth_config.redis_url or "redis://localhost:6379/0")

# Create limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=auth_config.redis_url or "redis://localhost:6379/0"
)

def setup_rate_limiting(app: FastAPI):
    """Configure rate limiting for app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to specific routes in routers/auth.py
@router.post("/login")
@limiter.limit("5/15minutes")  # 5 attempts per 15 minutes per IP
async def login(...):
    ...

@router.post("/register")
@limiter.limit("3/hour")  # 3 registrations per hour per IP
async def register(...):
    ...
```

---

## Phase 4: Frontend Implementation

**Duration**: 7-10 days
**Owner**: Frontend Developer
**Dependencies**: Phase 3 complete
**Priority**: HIGH

### Task 4.1: Login Page

**Files**:
- `src/web/templates/login.html` (NEW)
- `src/web/static/js/auth.js` (NEW)
- `src/web/static/css/auth.css` (NEW)

**Features**:
- Username/email input
- Password input with visibility toggle
- "Remember me" checkbox
- "Forgot password?" link
- "Register" link
- CSRF protection
- Client-side validation
- Error messaging
- Loading states

**HTML Structure** (simplified):
```html
<!DOCTYPE html>
<html>
<head>
    <title>Login - PromptVault</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <link rel="stylesheet" href="/static/css/auth.css">
</head>
<body>
    <div class="auth-container">
        <div class="auth-card">
            <h1>Welcome to PromptVault</h1>
            <form id="login-form">
                <div class="form-group">
                    <label for="username">Username or Email</label>
                    <input
                        type="text"
                        id="username"
                        name="username"
                        required
                        autocomplete="username"
                    >
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <div class="password-input">
                        <input
                            type="password"
                            id="password"
                            name="password"
                            required
                            autocomplete="current-password"
                        >
                        <button type="button" class="toggle-password">
                            <i class="icon-eye"></i>
                        </button>
                    </div>
                </div>

                <div class="form-group checkbox">
                    <input type="checkbox" id="remember" name="remember">
                    <label for="remember">Remember me</label>
                </div>

                <button type="submit" class="btn-primary" id="login-btn">
                    Login
                </button>

                <div class="form-links">
                    <a href="/password-reset">Forgot password?</a>
                    <span>•</span>
                    <a href="/register">Create account</a>
                </div>
            </form>

            <div id="error-message" class="error" style="display:none;"></div>
        </div>
    </div>

    <script src="/static/js/auth.js"></script>
</body>
</html>
```

**JavaScript** (`auth.js`):
```javascript
// Login form handler
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const remember = document.getElementById('remember').checked;

    const loginBtn = document.getElementById('login-btn');
    loginBtn.disabled = true;
    loginBtn.textContent = 'Logging in...';

    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',  // Important for cookies
            body: JSON.stringify({ username, password })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();

        // Store user info (but not tokens - they're in HTTP-only cookies)
        localStorage.setItem('user', JSON.stringify(data.user));

        // Optionally store refresh token in localStorage for "remember me"
        if (remember) {
            localStorage.setItem('refresh_token', data.refresh_token);
        }

        // Redirect to main app
        window.location.href = '/';

    } catch (error) {
        showError(error.message);
        loginBtn.disabled = false;
        loginBtn.textContent = 'Login';
    }
});

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

// Password visibility toggle
document.querySelector('.toggle-password').addEventListener('click', () => {
    const passwordInput = document.getElementById('password');
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;
});
```

**Acceptance**:
- [ ] Login form functional
- [ ] Error messages displayed
- [ ] Loading states work
- [ ] Redirects to main app on success
- [ ] "Remember me" works
- [ ] Mobile responsive

### Task 4.2: Registration Page

**File**: `src/web/templates/register.html` (NEW)

**Features**:
- Username input with availability check
- Email input with format validation
- Password input with strength meter
- Confirm password input
- Display name (optional)
- Terms of service checkbox
- Client-side validation
- Real-time feedback

**Password Strength Meter**:
```javascript
function calculatePasswordStrength(password) {
    let strength = 0;
    const checks = {
        length: password.length >= 12,
        length16: password.length >= 16,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        digit: /\d/.test(password),
        special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)
    };

    if (checks.length) strength += 20;
    if (checks.length16) strength += 10;
    if (checks.uppercase) strength += 15;
    if (checks.lowercase) strength += 15;
    if (checks.digit) strength += 15;
    if (checks.special) strength += 15;
    if (checks.uppercase && checks.lowercase && checks.digit && checks.special) strength += 10;

    return {
        score: strength,
        label: strength < 50 ? 'Weak' : strength < 75 ? 'Medium' : 'Strong',
        color: strength < 50 ? 'red' : strength < 75 ? 'orange' : 'green',
        checks
    };
}

// Update strength meter on input
document.getElementById('password').addEventListener('input', (e) => {
    const strength = calculatePasswordStrength(e.target.value);
    updateStrengthMeter(strength);
});
```

**Username Availability Check**:
```javascript
let usernameCheckTimeout;

document.getElementById('username').addEventListener('input', (e) => {
    clearTimeout(usernameCheckTimeout);
    const username = e.target.value;

    if (username.length < 3) return;

    usernameCheckTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/api/auth/check-username?username=${encodeURIComponent(username)}`);
            const data = await response.json();

            if (data.available) {
                showSuccess('username-feedback', '✓ Username available');
            } else {
                showError('username-feedback', '✗ Username already taken');
            }
        } catch (error) {
            console.error('Username check failed:', error);
        }
    }, 500);  // Debounce 500ms
});
```

### Task 4.3: Authentication Middleware (Frontend)

**File**: `src/web/static/js/auth-middleware.js` (NEW)

**Features**:
- Check authentication on page load
- Auto-redirect to login if not authenticated
- Automatic token refresh
- Add Authorization header to all API requests
- Handle 401 responses

**Implementation**:
```javascript
// Check auth on page load
window.addEventListener('DOMContentLoaded', async () => {
    const publicPages = ['/login', '/register', '/password-reset'];
    const currentPath = window.location.pathname;

    // Skip auth check for public pages
    if (publicPages.includes(currentPath)) {
        return;
    }

    // Check if user data exists
    const user = JSON.parse(localStorage.getItem('user') || 'null');
    if (!user) {
        redirectToLogin();
        return;
    }

    // Verify token is still valid
    try {
        const response = await fetch('/api/auth/me', {
            credentials: 'include'  // Send cookies
        });

        if (!response.ok) {
            // Token invalid, redirect to login
            redirectToLogin();
            return;
        }

        // Update user info
        const userData = await response.json();
        localStorage.setItem('user', JSON.stringify(userData));

        // Display user info in UI
        updateUserUI(userData);

        // Start automatic token refresh
        startTokenRefresh();

    } catch (error) {
        console.error('Auth check failed:', error);
        redirectToLogin();
    }
});

function redirectToLogin() {
    localStorage.clear();
    sessionStorage.clear();
    window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
}

// Automatic token refresh (25 minutes, before 30 min expiration)
let refreshInterval;

function startTokenRefresh() {
    refreshInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                credentials: 'include'
            });

            if (!response.ok) {
                console.error('Token refresh failed');
                redirectToLogin();
                return;
            }

            console.log('Token refreshed successfully');

        } catch (error) {
            console.error('Token refresh error:', error);
            redirectToLogin();
        }
    }, 25 * 60 * 1000);  // 25 minutes
}

// Intercept fetch to add Authorization header
const originalFetch = window.fetch;
window.fetch = function(...args) {
    const [url, config = {}] = args;

    // Only for API requests (except auth endpoints which use cookies)
    if (url.startsWith('/api/') && !url.startsWith('/api/auth/')) {
        // Token is in HTTP-only cookie, so browser sends automatically
        config.credentials = 'include';
    }

    return originalFetch(url, config)
        .then(async (response) => {
            // Handle 401 Unauthorized
            if (response.status === 401) {
                // Try to refresh token
                const refreshed = await tryRefreshToken();
                if (refreshed) {
                    // Retry original request
                    return originalFetch(url, config);
                } else {
                    // Refresh failed, redirect to login
                    redirectToLogin();
                    throw new Error('Authentication required');
                }
            }
            return response;
        });
};

async function tryRefreshToken() {
    try {
        const response = await originalFetch('/api/auth/refresh', {
            method: 'POST',
            credentials: 'include'
        });
        return response.ok;
    } catch (error) {
        return false;
    }
}

// Logout function
window.logout = async function() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        clearInterval(refreshInterval);
        localStorage.clear();
        sessionStorage.clear();
        window.location.href = '/login';
    }
};
```

### Task 4.4: User Profile Page

**File**: `src/web/templates/profile.html` (NEW)

**Sections**:
1. Profile information (username, email, display name, role)
2. Statistics (prompts created, favorites, last login)
3. Change password form
4. Active sessions list
5. Danger zone (delete account)

### Task 4.5: Password Reset Flow

**Files**:
- `src/web/templates/password-reset-request.html` (NEW)
- `src/web/templates/password-reset-confirm.html` (NEW)

### Task 4.6: Update Main App UI

**Changes to** `src/web/templates/index.html`:
- Add user menu in header (username, role badge)
- Add "Profile" link
- Add "Logout" button
- Display username in prompt cards ("Created by: username")
- Show role-specific features (e.g., hide "Create" button for viewers)

**JavaScript Changes** (`src/web/static/js/app.js`):
```javascript
// Display current user in header
function updateUserUI(user) {
    const userMenu = document.getElementById('user-menu');
    if (userMenu) {
        userMenu.innerHTML = `
            <span class="username">${user.display_name || user.username}</span>
            <span class="role-badge ${user.role}">${user.role}</span>
            <div class="dropdown">
                <a href="/profile">Profile</a>
                <a href="#" onclick="logout()">Logout</a>
            </div>
        `;
    }

    // Show/hide features based on role
    if (user.role === 'viewer') {
        document.querySelectorAll('.editor-only').forEach(el => el.style.display = 'none');
    }
    if (user.role !== 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
    }
}
```

### Task 4.7: Internationalization (i18n)

**Update** `src/web/static/locales/en.json`:
```json
{
  "auth": {
    "login": "Login",
    "logout": "Logout",
    "register": "Register",
    "username": "Username",
    "email": "Email",
    "password": "Password",
    "confirmPassword": "Confirm Password",
    "forgotPassword": "Forgot password?",
    "rememberMe": "Remember me",
    "loginButton": "Sign In",
    "registerButton": "Create Account",
    "loginError": "Invalid username or password",
    "accountLocked": "Account locked due to failed login attempts",
    "passwordStrength": {
      "weak": "Weak password",
      "medium": "Medium strength",
      "strong": "Strong password"
    },
    "profile": "Profile",
    "changePassword": "Change Password",
    "activeSessions": "Active Sessions",
    "revokeSession": "Revoke Session",
    "deleteAccount": "Delete Account"
  }
}
```

**Repeat for** `fr.json`, `es.json`, `de.json`

---

## Phase 5: Testing & Security

**Duration**: 5-7 days
**Owner**: QA Engineer + Backend Developer
**Dependencies**: Phases 2-4 complete
**Priority**: CRITICAL

### Task 5.1: Unit Tests - Password Service

**File**: `tests/test_password_service.py`

**Coverage Target**: 100%

**Tests**:
```python
class TestPasswordHashing:
    def test_hash_password_creates_unique_hashes(self, password_service):
        """Verify same password produces different hashes (unique salts)."""

    def test_verify_password_correct(self, password_service):
        """Verify correct password returns True."""

    def test_verify_password_incorrect_raises_exception(self, password_service):
        """Verify incorrect password raises VerifyMismatchError."""

    def test_password_policy_min_length(self, password_service):
        """Verify password must be at least 12 chars."""

    def test_password_policy_uppercase(self, password_service):
        """Verify password requires uppercase letter."""

    def test_password_policy_lowercase(self, password_service):
        """Verify password requires lowercase letter."""

    def test_password_policy_digit(self, password_service):
        """Verify password requires digit."""

    def test_password_policy_special_char(self, password_service):
        """Verify password requires special character."""

    def test_password_policy_valid_password(self, password_service):
        """Verify valid password passes all checks."""

    @pytest.mark.asyncio
    async def test_breached_password_detection(self, password_service):
        """Test breached password detection with HaveIBeenPwned API."""
        # Use known breached password
        is_breached = await password_service.is_password_breached("password123")
        assert is_breached is True

        # Use strong unique password (very unlikely to be breached)
        is_breached = await password_service.is_password_breached("X9k#mP2@qW7$nL5!")
        assert is_breached is False
```

### Task 5.2: Unit Tests - JWT Service

**File**: `tests/test_jwt_service.py`

**Coverage Target**: 100%

**Tests**: (See spec §8.2 for details)

### Task 5.3: Unit Tests - Auth Service

**File**: `tests/test_auth_service.py`

**Coverage Target**: ≥ 95%

**Tests**: (See spec §8.2)

### Task 5.4: Integration Tests - Auth API

**File**: `tests/test_auth_api.py`

**Coverage Target**: ≥ 90%

**Tests**: (See spec §8.3)

### Task 5.5: Security Tests

**File**: `tests/test_auth_security.py`

**Tests**:
- Rate limiting on login endpoint
- Account lockout after failed attempts
- Password not returned in API responses
- SQL injection prevention
- XSS prevention in user data
- CSRF protection
- Token reuse detection
- Session revocation

### Task 5.6: Performance Tests

**File**: `tests/performance/test_auth_performance.py`

**Requirements**:
- Token validation < 10ms (99th percentile)
- Login endpoint < 500ms (including password verification)
- Concurrent token validation (100 req/s)

**Tool**: `locust` or `pytest-benchmark`

### Task 5.7: End-to-End Tests

**Tool**: Playwright (via tester agent)

**Scenarios**:
1. User registration flow
2. Login → Browse prompts → Logout
3. Password reset flow
4. Change password flow
5. Admin user management
6. Role-based access (viewer cannot create)
7. Session expiration and refresh

---

## Phase 6: Migration & Deployment

**Duration**: 3-5 days
**Owner**: DevOps + Backend Developer
**Dependencies**: Phase 5 complete (all tests pass)
**Priority**: CRITICAL

### Task 6.1: Data Migration Script

**File**: `scripts/migrate_to_authentication.py`

**See SPEC_AUTHENTICATION.md §6.2 for full implementation**

**Steps**:
1. Create default admin user with random password
2. Assign all existing prompts to admin
3. Print admin credentials (must be changed immediately)
4. Create audit log entry

**Usage**:
```bash
export ADMIN_EMAIL="admin@example.com"
python scripts/migrate_to_authentication.py
```

**Output**:
```
🔐 Starting authentication migration...
✅ Created admin user: 550e8400-e29b-41d4-a716-446655440000
   Username: admin
   Email: admin@example.com
   Temporary Password: x7K!mP9@qW2#nL5$vR8&
   ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!
✅ Assigned 127 prompts to admin user
✅ Migration complete!
```

**Acceptance**:
- [ ] Script creates admin user successfully
- [ ] All existing prompts assigned to admin
- [ ] Temporary password generated securely
- [ ] Script idempotent (can run multiple times)
- [ ] Rollback capability (backup created first)

### Task 6.2: Deployment Documentation

**File**: `docs/AUTHENTICATION_DEPLOYMENT.md` (NEW)

**Sections**:
1. Prerequisites (Redis, SMTP, JWT keys)
2. Environment configuration
3. Database migration steps
4. Data migration steps
5. First login instructions
6. Security checklist
7. Troubleshooting

### Task 6.3: Update README.md

**Add section**: "Authentication & User Management"

**Content**:
- Overview of auth system
- Default admin credentials (CHANGE IMMEDIATELY)
- User roles and permissions
- How to create new users
- How to reset passwords

### Task 6.4: Update Docker Compose

**File**: `docker-compose.yml`

**Changes**:
```yaml
services:
  web:
    # ... existing config ...
    environment:
      # ... existing env vars ...
      JWT_PRIVATE_KEY_PATH: /app/keys/es256-private.pem
      JWT_PUBLIC_KEY_PATH: /app/keys/es256-public.pem
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./data:/app/data:rw
      - ./keys:/app/keys:ro  # NEW: Mount JWT keys
    depends_on:
      - db
      - redis  # NEW

  redis:  # NEW SERVICE
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:  # NEW
```

**Key Generation in Dockerfile**:
```dockerfile
# Add to Dockerfile
RUN mkdir -p /app/keys && \
    openssl ecparam -name prime256v1 -genkey -noout -out /app/keys/es256-private.pem && \
    openssl ec -in /app/keys/es256-private.pem -pubout -out /app/keys/es256-public.pem && \
    chmod 600 /app/keys/es256-private.pem && \
    chmod 644 /app/keys/es256-public.pem
```

### Task 6.5: Session Cleanup Cron Job

**File**: `scripts/cleanup_sessions.py` (NEW)

**Function**: Delete expired sessions every 24 hours

**Implementation**:
```python
import asyncio
from src.db.session import get_session
from src.db.repositories.session_repository import SessionRepository

async def cleanup_expired_sessions():
    """Delete expired user sessions."""
    async with get_session() as session:
        repo = SessionRepository(session)
        count = await repo.cleanup_expired_sessions()
        print(f"Deleted {count} expired sessions")

if __name__ == "__main__":
    asyncio.run(cleanup_expired_sessions())
```

**Crontab Entry**:
```cron
0 2 * * * cd /app && python scripts/cleanup_sessions.py
```

**Or Docker Compose Service**:
```yaml
services:
  session-cleanup:
    image: promptvault:latest
    command: python -m scripts.cleanup_sessions
    environment:
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      - db
    restart: unless-stopped
    deploy:
      replicas: 0  # Run via cron or scheduler
```

### Task 6.6: Rollback Plan

**Document**: `docs/AUTHENTICATION_ROLLBACK.md` (NEW)

**Steps**:
1. Restore database backup (before migration)
2. Revert code to previous version
3. Remove authentication tables (run down migrations)
4. Restart services

**Commands**:
```bash
# 1. Restore database backup
docker-compose exec db psql -U promptvault < backup_pre_auth.sql

# 2. Revert code
git checkout <previous-commit>

# 3. Rollback migrations
alembic downgrade -3  # Revert 3 migrations

# 4. Restart
docker-compose down
docker-compose up -d
```

---

## Task Breakdown & Estimates

### Detailed Task List with Estimates

| Task ID | Description | Estimate | Dependencies | Owner |
|---------|-------------|----------|--------------|-------|
| **Phase 1: Database** |
| 1.1 | Enhance User model | 4h | None | Backend |
| 1.2 | Create UserSession model | 3h | None | Backend |
| 1.3 | Create PasswordResetToken model | 2h | None | Backend |
| 1.4 | Create Alembic migrations (3x) | 6h | 1.1-1.3 | Backend |
| 1.5 | Create UserRepository | 8h | 1.1, 1.4 | Backend |
| 1.6 | Create SessionRepository | 8h | 1.2, 1.4 | Backend |
| 1.7 | Update models __init__.py | 0.5h | 1.1-1.3 | Backend |
| **Phase 1 Subtotal** | | **31.5h** (~4 days) |
| **Phase 2: Core Service** |
| 2.1 | Create auth config class | 3h | None | Backend |
| 2.2 | Password service (hashing, validation) | 10h | None | Backend |
| 2.3 | JWT service (generation, validation) | 10h | 2.1 | Backend |
| 2.4 | Main auth service (register, login, refresh) | 16h | 2.2, 2.3, 1.5, 1.6 | Backend |
| 2.5 | Password reset service | 6h | 2.1-2.4 | Backend |
| **Phase 2 Subtotal** | | **45h** (~6 days) |
| **Phase 3: API Endpoints** |
| 3.1 | Pydantic request/response models | 4h | None | Backend |
| 3.2 | FastAPI security dependencies | 6h | 2.3, 2.4 | Backend |
| 3.3 | Authentication routes (8 endpoints) | 12h | 3.1, 3.2 | Backend |
| 3.4 | Admin routes (5 endpoints) | 8h | 3.2, 3.3 | Backend |
| 3.5 | Protect existing routes (10 endpoints) | 10h | 3.2 | Backend |
| 3.6 | Rate limiting middleware | 4h | None | Backend |
| **Phase 3 Subtotal** | | **44h** (~5.5 days) |
| **Phase 4: Frontend** |
| 4.1 | Login page (HTML + JS + CSS) | 8h | 3.3 | Frontend |
| 4.2 | Registration page | 12h | 3.3 | Frontend |
| 4.3 | Auth middleware (token refresh, intercept) | 10h | 3.3 | Frontend |
| 4.4 | User profile page | 10h | 3.3 | Frontend |
| 4.5 | Password reset flow (2 pages) | 8h | 3.3 | Frontend |
| 4.6 | Update main app UI (header, user menu) | 6h | 4.1, 4.3 | Frontend |
| 4.7 | i18n translations (4 languages) | 6h | 4.1-4.6 | Frontend |
| **Phase 4 Subtotal** | | **60h** (~7.5 days) |
| **Phase 5: Testing** |
| 5.1 | Unit tests - Password service | 6h | 2.2 | Backend/QA |
| 5.2 | Unit tests - JWT service | 6h | 2.3 | Backend/QA |
| 5.3 | Unit tests - Auth service | 10h | 2.4 | Backend/QA |
| 5.4 | Integration tests - Auth API | 12h | 3.3, 3.4 | Backend/QA |
| 5.5 | Security tests | 8h | 3.5 | Backend/QA |
| 5.6 | Performance tests | 6h | 2.3, 2.4 | Backend/QA |
| 5.7 | E2E tests (Playwright) | 10h | 4.1-4.6 | QA |
| **Phase 5 Subtotal** | | **58h** (~7 days) |
| **Phase 6: Migration & Deployment** |
| 6.1 | Data migration script | 6h | 1.5, 2.4 | Backend |
| 6.2 | Deployment documentation | 4h | All | DevOps |
| 6.3 | Update README.md | 2h | All | DevOps |
| 6.4 | Update Docker Compose | 4h | 2.1 | DevOps |
| 6.5 | Session cleanup cron job | 3h | 1.6 | Backend |
| 6.6 | Rollback plan documentation | 3h | All | DevOps |
| **Phase 6 Subtotal** | | **22h** (~3 days) |
| **TOTAL** | | **260.5h** (~33 days) |

### Critical Path

1. Phase 1 → Phase 2 → Phase 3 → Phase 4 (sequential)
2. Phase 5 can partially overlap with Phase 4 (frontend tests)
3. Phase 6 depends on all previous phases

### Parallelization Opportunities

- **Week 1-2**: Backend work (Phases 1-2)
- **Week 3**: Backend (Phase 3) + Frontend starts (Phase 4.1-4.2)
- **Week 4**: Frontend (Phase 4.3-4.7) + Testing starts (Phase 5.1-5.3)
- **Week 5**: Testing (Phase 5.4-5.7) + Deployment prep (Phase 6)

---

## Dependencies & Blockers

### External Dependencies

1. **Redis**: Required for rate limiting
   - **Mitigation**: Use in-memory store if Redis unavailable (degraded mode)
2. **SMTP Server**: Required for password reset emails
   - **Mitigation**: Skip password reset feature initially, add later
3. **JWT Keys**: Must be generated securely
   - **Mitigation**: Auto-generate on first deployment

### Internal Dependencies

1. **Database Migration**: Must complete before auth can work
   - **Risk**: Migration failure on production database
   - **Mitigation**: Test migrations on copy of production data
2. **Existing User Model**: Already has relationships to Prompt
   - **Risk**: Breaking existing functionality
   - **Mitigation**: Additive changes only (nullable columns first)
3. **Testing Infrastructure**: Need 90% coverage
   - **Risk**: Tests take too long to write
   - **Mitigation**: Start testing early (TDD approach)

### Potential Blockers

| Blocker | Impact | Probability | Mitigation |
|---------|--------|-------------|------------|
| Redis not available | Medium | Low | Use in-memory rate limiter (slowapi memory backend) |
| SMTP not configured | Low | Medium | Skip password reset initially, manual admin reset |
| JWT key generation fails | High | Low | Provide pre-generated keys for testing |
| Argon2 too slow on old hardware | Medium | Low | Reduce time_cost to 2, or fall back to bcrypt |
| Database migration conflicts | High | Low | Careful testing, backup, rollback plan |
| Frontend token handling issues | Medium | Medium | Thorough testing with browser dev tools |

---

## Quality Gates

### Phase 1 Exit Criteria

- [ ] All database models compile without errors
- [ ] Alembic migrations run successfully (up and down)
- [ ] UserRepository and SessionRepository unit tests ≥ 95% coverage
- [ ] No breaking changes to existing User/Prompt functionality

### Phase 2 Exit Criteria

- [ ] All auth service unit tests pass
- [ ] Password hashing: 100% test coverage
- [ ] JWT service: 100% test coverage
- [ ] Auth service: ≥ 95% test coverage
- [ ] Token rotation logic verified manually
- [ ] Breached password detection works (optional)

### Phase 3 Exit Criteria

- [ ] All auth API endpoints functional
- [ ] Integration tests ≥ 90% coverage
- [ ] All existing endpoints protected with auth
- [ ] Rate limiting working
- [ ] OpenAPI docs updated

### Phase 4 Exit Criteria

- [ ] Login and registration pages functional
- [ ] Token refresh working automatically
- [ ] User menu and logout working
- [ ] Mobile responsive design
- [ ] i18n complete for 4 languages

### Phase 5 Exit Criteria

- [ ] Overall auth module test coverage ≥ 90%
- [ ] All security tests pass
- [ ] Performance tests meet <10ms requirement
- [ ] E2E tests cover critical user journeys
- [ ] No high-severity security issues

### Phase 6 Exit Criteria

- [ ] Migration script tested on production-like data
- [ ] Default admin user created successfully
- [ ] All prompts assigned to admin
- [ ] Documentation complete
- [ ] Rollback plan tested

### Final Release Criteria

- [ ] All phase exit criteria met
- [ ] Security review complete
- [ ] Performance benchmarks met
- [ ] Documentation reviewed
- [ ] User acceptance testing (UAT) passed
- [ ] Rollback plan validated

---

## Rollback Plan

### Pre-Migration Checklist

- [ ] Full database backup created
- [ ] Backup verified (restore test successful)
- [ ] Current code version tagged in git
- [ ] Downtime window scheduled (if needed)
- [ ] Rollback plan reviewed by team

### Rollback Triggers

**Rollback immediately if**:
1. Migration fails and cannot be fixed within 30 minutes
2. Critical bug discovered that prevents login
3. Data integrity issues detected
4. Performance degradation > 50%
5. Security vulnerability discovered

### Rollback Steps

```bash
# 1. Stop services
docker-compose down

# 2. Restore database backup
docker-compose up -d db
docker-compose exec db psql -U promptvault < backup_pre_auth_migration.sql

# 3. Revert code to previous version
git checkout <tag-before-auth>

# 4. Rollback Alembic migrations
docker-compose run web alembic downgrade -3

# 5. Restart services with old code
docker-compose up -d

# 6. Verify functionality
curl http://localhost:8001/api/prompts  # Should work without auth

# 7. Notify users of rollback
```

### Post-Rollback Actions

1. Analyze failure cause
2. Fix issues in development
3. Re-test thoroughly
4. Schedule new deployment

---

## Success Metrics

### Security Metrics

- **Password Security**: 100% of passwords hashed with Argon2id
- **Token Security**: 0 plaintext tokens in database
- **Rate Limiting**: ≤ 5 login attempts per 15 minutes
- **Session Security**: 100% of sessions tracked and revocable

### Performance Metrics

- **Token Validation**: < 10ms (p99)
- **Login Latency**: < 500ms (p99)
- **Page Load**: No regression vs baseline (< 5% increase)
- **Concurrent Users**: Support 100 concurrent authenticated users

### Functionality Metrics

- **Test Coverage**: ≥ 90% for auth modules
- **API Completeness**: 100% of AC-AUTH-* criteria met
- **Bug Density**: < 1 high-severity bug per 1000 LOC

### User Metrics

- **Migration Success**: 100% of prompts assigned to users
- **First Login**: < 3 clicks to login
- **Password Reset**: < 5 minutes end-to-end
- **Session Duration**: 14 days with auto-refresh

---

## Conclusion

This implementation plan provides a comprehensive roadmap for adding authentication to PromptVault over 4-6 weeks. The phased approach allows for incremental testing and validation, while the quality gates ensure security and functionality at each stage.

**Key Success Factors**:
1. **Security First**: Argon2id hashing, ES256 JWT, HTTP-only cookies
2. **Robust Testing**: 90% coverage, security tests, performance tests
3. **Safe Migration**: Data backup, rollback plan, gradual rollout
4. **User Experience**: Auto token refresh, responsive design, clear error messages

**Next Steps**:
1. Review and approve this plan
2. Allocate resources (backend dev, frontend dev, QA, DevOps)
3. Set up development environment (Redis, SMTP, JWT keys)
4. Begin Phase 1: Database Schema & Models

---

**Document Status**: READY FOR EXECUTION
**Approval Required From**: Tech Lead, Security Team, Product Owner
**Questions/Clarifications**: [GitHub Issue #XX]
