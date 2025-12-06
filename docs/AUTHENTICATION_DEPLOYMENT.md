# Authentication System Deployment Guide

This guide covers the deployment and initial setup of PromptVault's authentication system, including prerequisites, configuration, database migrations, and first admin user creation.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [JWT Key Generation](#jwt-key-generation)
4. [Environment Configuration](#environment-configuration)
5. [Database Migration](#database-migration)
6. [First Admin User](#first-admin-user)
7. [Testing the Deployment](#testing-the-deployment)
8. [Security Checklist](#security-checklist)
9. [Production Considerations](#production-considerations)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **PostgreSQL**: 14 or higher (recommended for production)
  - SQLite 3.35+ (acceptable for development/testing)
- **Redis**: 6.2 or higher (required for rate limiting)
- **Operating System**: Linux, macOS, or Windows

### Python Dependencies

All dependencies are specified in `requirements.txt`. Key authentication-related packages:

- `fastapi` - Web framework
- `pyjwt[crypto]` - JWT token handling
- `cryptography` - ES256 key generation and cryptographic operations
- `argon2-cffi` - Argon2id password hashing
- `redis` - Rate limiting storage
- `alembic` - Database migrations
- `sqlalchemy` - ORM

Install dependencies:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### External Services

1. **SMTP Server** (for password reset emails)
   - Any SMTP-compatible email service
   - Examples: Gmail, SendGrid, Amazon SES, Mailgun
   - Required configuration: host, port, credentials

2. **Redis Server** (for rate limiting)
   - Can be local or remote
   - Default: `redis://localhost:6379/0`

---

## Initial Setup

### 1. Clone and Navigate to Project

```bash
git clone <repository-url>
cd PromptVault
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create Required Directories

```bash
# Create secrets directory for JWT keys
mkdir -p secrets/jwt

# Create data directory for SQLite (if using SQLite)
mkdir -p data

# Create logs directory
mkdir -p logs
```

---

## JWT Key Generation

PromptVault uses **ES256** (ECDSA with P-256 curve) for JWT token signing. This provides strong security with smaller key sizes compared to RSA.

### Generate Keys

Run the key generation script:

```bash
python scripts/generate_jwt_keys.py
```

This will:
- Generate a private/public key pair using ECDSA P-256
- Save keys to `secrets/jwt/private_key.pem` and `secrets/jwt/public_key.pem`
- Set appropriate file permissions (600 for private, 644 for public)

### Verify Keys

```bash
# Check that keys were created
ls -la secrets/jwt/

# Output should show:
# -rw-------  1 user  group   227 Dec  4 10:00 private_key.pem
# -rw-r--r--  1 user  group   178 Dec  4 10:00 public_key.pem
```

### Security Warning

**IMPORTANT**:
- **NEVER** commit `private_key.pem` to version control
- The `.gitignore` file already excludes `secrets/` directory
- Keep backups of your private key in a secure location
- If the private key is compromised, regenerate keys and revoke all existing tokens

---

## Environment Configuration

### 1. Copy Environment Template

```bash
cp .env.example .env
```

### 2. Configure Database

#### For Development (SQLite)

```bash
DATABASE_URL=sqlite:///./data/promptvault.db
DB_ECHO=false
```

#### For Production (PostgreSQL)

```bash
# Create PostgreSQL database first
createdb promptvault

# Configure connection
DATABASE_URL=postgresql://username:password@localhost:5432/promptvault
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_ECHO=false
```

### 3. Configure JWT Settings

```bash
# JWT Key Paths (generated in previous step)
JWT_PRIVATE_KEY_PATH=secrets/jwt/private_key.pem
JWT_PUBLIC_KEY_PATH=secrets/jwt/public_key.pem

# Token Expiration (in seconds)
JWT_ACCESS_TOKEN_EXPIRE_SECONDS=900        # 15 minutes
JWT_REFRESH_TOKEN_EXPIRE_SECONDS=604800    # 7 days

# Token Identifiers
JWT_ISSUER=promptvault
JWT_AUDIENCE=promptvault-api
```

### 4. Configure Password Policy

```bash
# Password Requirements
PASSWORD_MIN_LENGTH=12
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGIT=true
PASSWORD_REQUIRE_SPECIAL=true
```

### 5. Configure Account Security

```bash
# Account Lockout
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION_SECONDS=900       # 15 minutes

# Session Management
MAX_SESSIONS_PER_USER=5                    # 0 = unlimited
SESSION_INACTIVE_TIMEOUT_SECONDS=2592000   # 30 days
```

### 6. Configure Rate Limiting

```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Rate Limits
RATE_LIMIT_LOGIN_ATTEMPTS=5
RATE_LIMIT_LOGIN_WINDOW_SECONDS=900        # 15 minutes

RATE_LIMIT_REGISTER_ATTEMPTS=3
RATE_LIMIT_REGISTER_WINDOW_SECONDS=3600    # 1 hour

RATE_LIMIT_PASSWORD_RESET_ATTEMPTS=3
RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS=3600  # 1 hour
```

### 7. Configure Email (SMTP)

```bash
# SMTP Server Settings
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=noreply@example.com
SMTP_PASSWORD=your-smtp-password

# Email Sender Information
EMAIL_FROM_ADDRESS=noreply@example.com
EMAIL_FROM_NAME=PromptVault

# Password Reset Token Validity
PASSWORD_RESET_TOKEN_EXPIRE_SECONDS=3600   # 1 hour

# Application Base URL (for email links)
APP_BASE_URL=https://your-domain.com
```

#### SMTP Provider Examples

**Gmail** (App Password required):
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

**SendGrid**:
```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

**Amazon SES**:
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-smtp-username
SMTP_PASSWORD=your-smtp-password
```

---

## Database Migration

### 1. Verify Alembic Configuration

```bash
# Check alembic.ini points to correct database
cat alembic.ini | grep sqlalchemy.url
```

### 2. Run Migrations

```bash
# Run all pending migrations
alembic upgrade head
```

This will create the following tables:
- `users` - User accounts with authentication fields
- `user_sessions` - JWT refresh token tracking with family IDs
- `password_reset_tokens` - Password reset tokens
- Plus existing tables (prompts, categories, tags, etc.)

### 3. Verify Migration

```bash
# Check current migration version
alembic current

# Check migration history
alembic history

# For PostgreSQL, verify tables
psql -d promptvault -c "\dt"

# For SQLite, verify tables
sqlite3 data/promptvault.db ".tables"
```

### Expected Tables

After migration, you should see:
- `users` - User accounts
- `user_sessions` - Active sessions
- `password_reset_tokens` - Password reset tokens
- `prompts` - Prompt storage
- `prompt_versions` - Version history
- `prompt_branches` - Branch management
- `categories` - Prompt categories
- `tags` - Prompt tags
- `prompt_category` - Association table (only needed for many-to-many relationships)
- `prompt_tag` - Association table
- `alembic_version` - Migration tracking

---

## First Admin User

### Create Admin User Interactively

Run the admin creation script:

```bash
python scripts/create_admin_user.py
```

Follow the interactive prompts:

```
============================================================
PromptVault - Create Admin User
============================================================

This script will create the first admin user for PromptVault.
Please provide the following information:

Username:
  > admin

Email:
  > admin@example.com

Password:

Password Policy Requirements:
  - Minimum length: 12 characters
  - At least one uppercase letter (A-Z)
  - At least one lowercase letter (a-z)
  - At least one digit (0-9)
  - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

Password: [hidden]
Confirm Password: [hidden]

------------------------------------------------------------
Please review the information:
  Username: admin
  Email:    admin@example.com
  Role:     admin
------------------------------------------------------------

Create this admin user? (yes/no): yes

Creating admin user...

✓ Admin user created successfully!
  User ID:  a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Username: admin
  Email:    admin@example.com
  Role:     admin

✓ You can now login with these credentials.
```

### Verify Admin User

```bash
# For PostgreSQL
psql -d promptvault -c "SELECT id, username, email, role, is_active FROM users;"

# For SQLite
sqlite3 data/promptvault.db "SELECT id, username, email, role, is_active FROM users;"
```

---

## Testing the Deployment

### 1. Start Redis (if not already running)

```bash
# macOS (Homebrew)
brew services start redis

# Linux (systemd)
sudo systemctl start redis

# Or run in foreground
redis-server
```

### 2. Start the Application

```bash
# Development mode with auto-reload
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8003

# Production mode
uvicorn src.web.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### 3. Verify API is Running

```bash
# Health check
curl http://localhost:8000/health

# OpenAPI documentation
open http://localhost:8000/docs
```

### 4. Test Authentication Flow

#### Register a New User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecureP@ssw0rd123",
    "confirm_password": "SecureP@ssw0rd123"
  }'
```

#### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "testuser",
    "password": "SecureP@ssw0rd123"
  }'
```

Save the `access_token` from the response.

#### Get Current User

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Test Admin Endpoints

```bash
# Login as admin
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username_or_email": "admin",
    "password": "your-admin-password"
  }'

# List all users (admin only)
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"

# Get system stats (admin only)
curl http://localhost:8000/api/admin/stats \
  -H "Authorization: Bearer ADMIN_ACCESS_TOKEN"
```

---

## Security Checklist

Before deploying to production, verify the following:

### Environment Security

- [ ] `.env` file has restricted permissions (600)
- [ ] `.env` file is in `.gitignore` (never committed)
- [ ] JWT private key has restricted permissions (600)
- [ ] JWT private key is in `.gitignore` (never committed)
- [ ] Secure backup of JWT private key exists
- [ ] All default passwords have been changed

### Application Security

- [ ] HTTPS is enabled (TLS/SSL certificate)
- [ ] `APP_BASE_URL` uses `https://` (not `http://`)
- [ ] Strong password policy is enforced
- [ ] Rate limiting is enabled (Redis is running)
- [ ] Account lockout is configured
- [ ] Session limits are configured
- [ ] SMTP credentials are secure (use app passwords, not main password)

### Database Security

- [ ] Database uses strong password
- [ ] Database allows connections only from application server
- [ ] Database backups are configured
- [ ] Database is not publicly accessible

### Server Security

- [ ] Server firewall is configured (only necessary ports open)
- [ ] SSH uses key-based authentication (not password)
- [ ] System packages are up to date
- [ ] Security monitoring is enabled
- [ ] Log rotation is configured

### Application Monitoring

- [ ] Error logging is configured
- [ ] Audit logging is enabled
- [ ] Performance monitoring is set up
- [ ] Backup strategy is documented and tested

---

## Production Considerations

### Performance

1. **Database Connection Pooling**
   ```bash
   DB_POOL_SIZE=20
   DB_POOL_TIMEOUT=30
   DB_POOL_RECYCLE=3600
   ```

2. **Redis Persistence**
   - Configure Redis persistence (RDB or AOF)
   - Set up Redis backups

3. **Application Scaling**
   ```bash
   # Run multiple workers
   uvicorn src.web.app:app --workers 4 --host 0.0.0.0 --port 8000
   ```

4. **Reverse Proxy**
   - Use Nginx or Caddy for TLS termination
   - Enable HTTP/2 and compression
   - Set appropriate headers (HSTS, CSP, etc.)

### Monitoring

1. **Application Logs**
   ```bash
   # Configure log level
   LOG_LEVEL=WARNING
   AUDIT_LOG_LEVEL=INFO
   ```

2. **Health Checks**
   - Use `/health` endpoint for monitoring
   - Monitor Redis connectivity
   - Monitor database connectivity

3. **Metrics**
   - Track failed login attempts
   - Monitor rate limit hits
   - Track session creation/expiration

### Backup Strategy

1. **Database Backups**
   ```bash
   # PostgreSQL backup
   pg_dump promptvault > backup_$(date +%Y%m%d).sql
   ```

2. **JWT Key Backups**
   - Store private key in secure location
   - Have recovery procedure documented

3. **Configuration Backups**
   - Back up `.env` file securely
   - Document all configuration changes

### High Availability

1. **Database**
   - PostgreSQL replication (streaming or logical)
   - Regular automated backups

2. **Redis**
   - Redis Sentinel for automatic failover
   - Redis Cluster for horizontal scaling

3. **Application**
   - Load balancer for multiple instances
   - Health check-based routing
   - Zero-downtime deployments

---

## Troubleshooting

### Common Issues

#### 1. JWT Key Not Found

**Error**: `JWT private key not found at: secrets/jwt/private_key.pem`

**Solution**:
```bash
python scripts/generate_jwt_keys.py
```

#### 2. Database Connection Failed

**Error**: `FATAL: password authentication failed for user`

**Solution**:
- Verify `DATABASE_URL` in `.env`
- Check PostgreSQL user credentials
- Ensure PostgreSQL is running: `pg_isready`

#### 3. Redis Connection Failed

**Error**: `Error connecting to Redis`

**Solution**:
- Verify `REDIS_URL` in `.env`
- Check Redis is running: `redis-cli ping`
- Start Redis: `redis-server` or `brew services start redis`

#### 4. Migration Failed

**Error**: `Target database is not up to date`

**Solution**:
```bash
# Check current version
alembic current

# Run migrations
alembic upgrade head

# If corrupted, reset and rebuild
alembic downgrade base
alembic upgrade head
```

#### 5. Account Locked

**Error**: `Account is locked. Try again after...`

**Solution**:
```bash
# Manually unlock in database (PostgreSQL)
psql -d promptvault -c "UPDATE users SET failed_login_attempts=0, locked_until=NULL WHERE username='username';"

# Or wait for lockout duration to expire
```

#### 6. SMTP Authentication Failed

**Error**: `SMTP authentication error`

**Solution**:
- For Gmail: Use App Password, not main password
- Verify SMTP credentials in `.env`
- Check SMTP host and port
- Ensure "Less secure apps" is enabled (if applicable)

#### 7. Rate Limit Exceeded

**Error**: `Rate limit exceeded. Try again later.`

**Solution**:
- Wait for rate limit window to expire
- Adjust rate limits in `.env` if needed
- Clear Redis keys (for testing only):
  ```bash
  redis-cli FLUSHDB
  ```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# In .env
LOG_LEVEL=DEBUG
DB_ECHO=true
```

View logs:
```bash
# If using systemd
journalctl -u promptvault -f

# If running directly
tail -f logs/promptvault.log
```

### Getting Help

1. Check logs for detailed error messages
2. Review configuration in `.env`
3. Verify all prerequisites are met
4. Consult API documentation at `/docs`
5. Check GitHub issues for similar problems

---

## Next Steps

After successful deployment:

1. **Configure Email Templates** - Customize password reset emails
2. **Set Up Monitoring** - Configure application and infrastructure monitoring
3. **Review Security** - Complete security audit
4. **User Management** - Create additional admin users if needed
5. **Backup Testing** - Test backup and restore procedures
6. **Documentation** - Document your specific deployment configuration

---

## Additional Resources

- [Authentication API Documentation](./AUTHENTICATION_API.md)
- [Security Documentation](./AUTHENTICATION_SECURITY.md)
- [Testing Guide](./TESTING.md)
- [Main Deployment Guide](./DEPLOYMENT.md)
