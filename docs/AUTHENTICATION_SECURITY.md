# Authentication Security Documentation

Comprehensive documentation of PromptVault's authentication security features, best practices, OWASP compliance, and common vulnerabilities prevented.

## Table of Contents

1. [Security Overview](#security-overview)
2. [Password Security](#password-security)
3. [Token Security](#token-security)
4. [Session Management](#session-management)
5. [Account Protection](#account-protection)
6. [Rate Limiting](#rate-limiting)
7. [OWASP Compliance](#owasp-compliance)
8. [Vulnerabilities Prevented](#vulnerabilities-prevented)
9. [Security Best Practices](#security-best-practices)
10. [Security Audit Checklist](#security-audit-checklist)

---

## Security Overview

PromptVault's authentication system is designed with security as the top priority, implementing industry best practices and OWASP recommendations throughout.

### Core Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Users have minimal permissions by default
3. **Secure by Default**: Security features enabled out of the box
4. **Fail Securely**: Errors don't expose sensitive information
5. **Zero Trust**: All requests are validated and authenticated

### Key Security Features

- **ES256 JWT Tokens**: ECDSA-based asymmetric encryption
- **Argon2id Password Hashing**: OWASP-recommended algorithm
- **Token Family Tracking**: Detects and prevents token replay attacks
- **Account Lockout**: Protection against brute force attacks
- **Rate Limiting**: Prevents abuse and DoS attacks
- **Secure Password Reset**: Time-limited, single-use tokens
- **Session Management**: IP and User-Agent tracking
- **Audit Logging**: Comprehensive security event logging

---

## Password Security

### Password Hashing

**Algorithm**: Argon2id (Hybrid mode)

Argon2id combines:

- **Argon2d**: Data-dependent memory access (GPU-resistant)
- **Argon2i**: Data-independent memory access (side-channel resistant)

**Parameters** (OWASP-recommended):

```python
time_cost = 2        # Number of iterations
memory_cost = 102400 # Memory usage in KiB (100 MB)
parallelism = 8      # Number of parallel threads
hash_len = 32        # Output hash length in bytes
salt_len = 16        # Salt length in bytes
```

**Why Argon2id?**

- Winner of Password Hashing Competition (2015)
- Resistant to GPU cracking attacks
- Resistant to side-channel attacks
- Tunable memory-hardness
- OWASP recommended since 2020

**Security Properties**:

- Unique random salt per password
- Constant-time verification (prevents timing attacks)
- Configurable cost factors for future-proofing
- Cannot be reverse-engineered

### Password Policy

**Default Requirements**:

- Minimum length: **12 characters** (configurable)
- At least one **uppercase letter** (A-Z)
- At least one **lowercase letter** (a-z)
- At least one **digit** (0-9)
- At least one **special character** (!@#$%^&\*()\_+-=[]{}|;:,.<>?)
- Not in **common password list** (top 100 most common passwords)

**Why These Requirements?**:

- 12+ characters: ~72 bits of entropy with mixed character sets
- Complexity rules: Increase search space for attackers
- Common password check: Prevents weak but policy-compliant passwords

**Password Strength Analysis**:

The system calculates password entropy and provides feedback:

| Entropy (bits) | Strength    | Crack Time (offline)   |
| -------------- | ----------- | ---------------------- |
| < 40           | Weak        | Seconds to minutes     |
| 40-59          | Medium      | Hours to days          |
| 60-79          | Strong      | Years to decades       |
| 80+            | Very Strong | Centuries to millennia |

**Example Strength Ratings**:

- `password123`: Weak (rejected by common password check)
- `P@ssw0rd`: Weak (too short, common pattern)
- `MyP@ssw0rd123`: Medium (acceptable but not ideal)
- `Tr0ub4dor&3`: Strong (good length and complexity)
- `correct-horse-battery-staple-2025`: Very Strong (long passphrase)

### Password Storage

**What is stored**:

- Argon2id hash (97 characters)
- Salt (embedded in hash string)
- Algorithm identifier and parameters

**What is NOT stored**:

- Plain text password
- Reversible encryption of password
- Password hints or recovery questions

**Database column**:

```python
password_hash = Column(String(255), nullable=False)
```

**Example hash format**:

```
$argon2id$v=19$m=102400,t=2,p=8$
<base64-encoded-salt>$<base64-encoded-hash>
```

---

## Token Security

### JWT Algorithm: ES256

**Algorithm**: ECDSA with SHA-256 and P-256 curve

**Why ES256 over HS256?**

| Feature              | ES256 (Used)                      | HS256 (Avoided)               |
| -------------------- | --------------------------------- | ----------------------------- |
| Encryption Type      | Asymmetric                        | Symmetric                     |
| Key Confusion Attack | Immune                            | Vulnerable                    |
| Key Distribution     | Public key can be shared          | Secret must be protected      |
| Key Size             | 256-bit (smaller)                 | 512-bit minimum (larger)      |
| Performance          | Slower signing, fast verification | Fast signing and verification |
| Security             | Higher                            | Lower                         |

**Key Confusion Attack** (why we avoid HS256):

HS256 is vulnerable to algorithm substitution attacks where an attacker can:

1. Obtain the public key (often exposed in JWKS endpoints)
2. Create a token signed with HS256 using the public key as the secret
3. The server verifies the token successfully (security breach!)

ES256 prevents this because:

- Public key cannot be used to sign tokens
- Private key is never exposed
- Algorithm validation is enforced

### Token Structure

**Access Token** (Short-lived: 15 minutes):

```json
{
  "header": {
    "typ": "JWT",
    "alg": "ES256"
  },
  "payload": {
    "sub": "user-uuid",
    "username": "alice",
    "email": "alice@example.com",
    "role": "viewer",
    "type": "access",
    "iat": 1701344700,
    "exp": 1701345600,
    "iss": "promptvault",
    "aud": "promptvault-api"
  },
  "signature": "<ES256-signature>"
}
```

**Refresh Token** (Long-lived: 7 days):

```json
{
  "header": {
    "typ": "JWT",
    "alg": "ES256"
  },
  "payload": {
    "sub": "user-uuid",
    "type": "refresh",
    "family_id": "family-uuid",
    "jti": "token-uuid",
    "iat": 1701344700,
    "exp": 1701949500,
    "iss": "promptvault",
    "aud": "promptvault-api"
  },
  "signature": "<ES256-signature>"
}
```

### Token Validation

**Validation Steps**:

1. **Format Validation**: Three parts separated by dots
2. **Signature Verification**: ES256 signature with public key
3. **Algorithm Check**: Must be ES256 (prevents algorithm confusion)
4. **Expiration Check**: Token not expired (`exp` claim)
5. **Issued At Check**: Token not used before issued (`iat` claim)
6. **Issuer Check**: Matches expected issuer (`iss` claim)
7. **Audience Check**: Matches expected audience (`aud` claim)
8. **Type Check**: Correct token type (access vs refresh)
9. **User Existence**: User still exists in database
10. **Account Status**: User account is active

**Security Properties**:

- Stateless validation (no database lookup required for access tokens)
- Cryptographically secure (cannot be forged without private key)
- Tamper-evident (any modification breaks signature)
- Time-limited (automatic expiration)

### Token Family Tracking

**Purpose**: Detect and prevent token replay/reuse attacks

**How it works**:

1. **Family Creation**: Each login creates a new token family

   ```
   Login → Family ID: abc-123
   ```

2. **Token Rotation**: Each refresh generates new tokens in same family

   ```
   Refresh 1 → JTI: token-1 (Family: abc-123)
   Refresh 2 → JTI: token-2 (Family: abc-123)
   Refresh 3 → JTI: token-3 (Family: abc-123)
   ```

3. **Reuse Detection**: If an old token is reused
   ```
   ❌ Reuse token-1 (already used)
   → SECURITY BREACH DETECTED
   → Revoke entire family abc-123
   → User must login again
   ```

**Why This Matters**:

Scenario: Token theft

1. Attacker steals refresh token-2
2. Legitimate user refreshes token → gets token-3
3. Attacker tries to use token-2
4. System detects token-2 was already used
5. All tokens in family are revoked
6. Both legitimate user and attacker must re-authenticate
7. Security team is alerted

**Database Tracking**:

```python
class UserSession:
    family_id: str        # Token family identifier
    refresh_token_jti: str # Current refresh token ID (JWT ID)
    is_revoked: bool      # Revocation status
```

---

## Session Management

### Session Tracking

Each session tracks:

- **User ID**: Owner of the session
- **Family ID**: Token family for rotation tracking
- **Refresh Token JTI**: Current refresh token ID
- **IP Address**: Client IP (IPv4 or IPv6)
- **User Agent**: Browser/client information
- **Created At**: Session start time
- **Last Used At**: Last token refresh time
- **Expires At**: Session expiration time
- **Is Revoked**: Revocation status

### Session Limits

**Default**: 5 concurrent sessions per user (configurable)

**Why Limit Sessions?**:

- Prevents credential sharing
- Limits blast radius of token theft
- Detects unusual activity (many simultaneous logins)
- Forces device cleanup

**Enforcement**:

- When limit reached, oldest session is revoked
- User can manually revoke sessions via `/auth/sessions/{session_id}`
- Admin can revoke individual sessions via `/admin/users/{user_id}/sessions/{session_id}`
- Admin can revoke all user sessions via `/admin/users/{user_id}/sessions`

### Session Revocation Enforcement

**Critical Security Feature**: Session revocation is immediately enforced at the API level.

**How It Works**:

1. **Database Check**: Every authenticated request checks if the user has at least one active (non-revoked) session
2. **Immediate Invalidation**: If all sessions are revoked, access tokens are immediately rejected
3. **Frontend Protection**: Main app UI blocks content rendering until session is verified
4. **Privacy Protection**: Loading overlay prevents content flash before redirect

**Implementation**:

```python
# In get_current_user() dependency (src/web/dependencies/auth.py)
active_session_count = session_repo.count_user_sessions(user_id, active_only=True)

if active_session_count == 0:
    raise HTTPException(
        status_code=401,
        detail="All sessions have been revoked. Please log in again."
    )
```

**Access Token Behavior**:

- **Access tokens** (15 min lifetime) remain cryptographically valid after session revocation
- However, every API request checks session status in the database
- If no active sessions exist, the access token is rejected despite being valid JWT
- This provides **immediate revocation** without complex token blacklisting

**Frontend Security Flow**:

1. Page loads with full-screen "Verifying session..." overlay
2. Authentication check runs: `GET /api/auth/me`
3. If 401 (revoked): Immediate redirect to login (content never shown)
4. If 200 (valid): Hide overlay, show content
5. No content flash - prevents privacy leaks

**Why This Matters**:

- Prevents unauthorized access even with valid JWT tokens
- Admin session revocation takes effect immediately (not after token expiry)
- User cannot access app after session revocation
- Protects against token theft scenarios

**Performance Impact**:

- Minimal: Single database query per request to count active sessions
- Query is fast (indexed on user_id and is_revoked)
- Acceptable overhead for security benefit

### Session Timeout

**Inactivity Timeout**: 30 days (configurable)

**Why Timeout?**:

- Automatic cleanup of abandoned sessions
- Reduces attack surface
- Encourages periodic re-authentication

**Implementation**:

- Based on `last_used_at` timestamp
- Updated on each token refresh
- Expired sessions cannot be used

---

## Account Protection

### Account Lockout

**Purpose**: Prevent brute force password guessing attacks

**Configuration**:

- **Max Attempts**: 5 failed login attempts
- **Lockout Duration**: 15 minutes
- **Tracking**: Per user account (not per IP)

**How It Works**:

1. **Failed Login**: Increment `failed_login_attempts` counter
2. **Threshold Reached**: Set `locked_until` timestamp
3. **Login Blocked**: Return 403 error during lockout period
4. **Auto-Unlock**: After lockout period expires
5. **Manual Unlock**: Admin can reset counter

**Lockout Response**:

```json
{
  "detail": "Account is locked due to too many failed login attempts. Try again after 2025-12-04T12:45:00Z"
}
```

**Counter Reset**:

- Successful login resets counter to 0
- Lockout expiration resets counter to 0
- Admin can manually reset counter

### Failed Login Tracking

**What is tracked**:

- Number of failed attempts
- Timestamp of last failed attempt
- Lockout expiration time

**Database fields**:

```python
failed_login_attempts: int
locked_until: datetime | None
```

**Security Notes**:

- Tracking per account prevents distributed attacks
- Time-based lockout prevents persistent lockout
- Admin override allows legitimate user recovery

---

## Rate Limiting

### Implementation

**Technology**: Redis-based rate limiting

**Why Redis?**:

- In-memory storage (fast)
- TTL support (automatic expiration)
- Atomic operations (thread-safe)
- Distributed support (multi-instance deployments)

### Rate Limit Rules

| Endpoint                       | Limit      | Window | Scope     |
| ------------------------------ | ---------- | ------ | --------- |
| `/auth/login`                  | 5 attempts | 15 min | Per IP    |
| `/auth/register`               | 3 attempts | 1 hour | Per IP    |
| `/auth/password-reset/request` | 3 attempts | 1 hour | Per email |

### Rate Limit Algorithm

**Fixed Window Counter**:

1. Create key: `rate_limit:{endpoint}:{identifier}`
2. Increment counter in Redis
3. Set expiration if first request
4. Check if counter exceeds limit
5. Return 429 if limit exceeded

**Example**:

```python
key = "rate_limit:login:192.168.1.1"
count = redis.incr(key)
if count == 1:
    redis.expire(key, window_seconds)
if count > limit:
    raise RateLimitExceededError()
```

### Rate Limit Response

**Headers**:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1701349200
Retry-After: 900
```

**Body**:

```json
{
  "detail": "Rate limit exceeded for login. Try again in 15 minutes."
}
```

---

## OWASP Compliance

PromptVault's authentication system follows OWASP (Open Web Application Security Project) guidelines and recommendations.

### OWASP Top 10 2021 Coverage

| OWASP Risk                                          | Mitigation                       | Implementation                                        |
| --------------------------------------------------- | -------------------------------- | ----------------------------------------------------- |
| **A01: Broken Access Control**                      | Role-based access control (RBAC) | User roles (viewer/editor/admin), permission checks   |
| **A02: Cryptographic Failures**                     | Strong encryption                | Argon2id passwords, ES256 JWT, TLS/HTTPS              |
| **A03: Injection**                                  | Input validation                 | Pydantic validation, SQLAlchemy parameterized queries |
| **A04: Insecure Design**                            | Security by design               | Token families, account lockout, rate limiting        |
| **A05: Security Misconfiguration**                  | Secure defaults                  | Password policy enforced, JWT keys required           |
| **A07: Identification and Authentication Failures** | Robust authentication            | Multi-factor protection mechanisms                    |
| **A08: Software and Data Integrity Failures**       | JWT signature verification       | ES256 signatures, algorithm validation                |
| **A09: Security Logging and Monitoring Failures**   | Comprehensive logging            | Audit logs, failed login tracking                     |
| **A10: Server-Side Request Forgery (SSRF)**         | Input validation                 | URL validation in email configuration                 |

### OWASP Password Storage Cheat Sheet

✅ **Compliant**:

- [x] Use Argon2id as first choice
- [x] Minimum iteration count (time_cost=2)
- [x] Minimum memory cost (102400 KiB)
- [x] Unique salt per password
- [x] Store only hashes, never plain text
- [x] Use constant-time comparison

### OWASP Authentication Cheat Sheet

✅ **Compliant**:

- [x] Password complexity requirements
- [x] Account lockout mechanism
- [x] Secure password reset flow
- [x] Token-based authentication
- [x] Secure session management
- [x] Multi-factor authentication foundation (extensible)
- [x] Proper error messages (no user enumeration)

### OWASP Forgot Password Cheat Sheet

✅ **Compliant**:

- [x] Time-limited reset tokens (1 hour)
- [x] Single-use tokens
- [x] Secure token generation (cryptographically random)
- [x] Token hashing before storage
- [x] Rate limiting (3 requests/hour)
- [x] No user enumeration (same response for all emails)
- [x] Email masking (u\*\*\*@example.com)

---

## Vulnerabilities Prevented

### 1. Brute Force Attacks

**Vulnerability**: Attacker tries many passwords to guess credentials

**Mitigations**:

- ✅ Account lockout after 5 failed attempts
- ✅ Rate limiting on login endpoint (5 attempts/15 minutes)
- ✅ Strong password policy (increases search space)
- ✅ Argon2id hashing (slow verification)

### 2. Credential Stuffing

**Vulnerability**: Attacker uses leaked credentials from other breaches

**Mitigations**:

- ✅ Account lockout triggers on failed attempts
- ✅ Rate limiting prevents automated attacks
- ✅ Password policy prevents common passwords
- ✅ Monitoring and logging of failed login patterns

### 3. Token Theft/Replay Attacks

**Vulnerability**: Attacker steals and reuses authentication tokens

**Mitigations**:

- ✅ Token family tracking detects reuse
- ✅ Entire family revoked on reuse detection
- ✅ Short access token lifetime (15 minutes)
- ✅ IP address and User-Agent tracking
- ✅ Session limits per user

### 4. JWT Algorithm Confusion

**Vulnerability**: Attacker substitutes HS256 for RS256/ES256

**Mitigations**:

- ✅ ES256 exclusively (asymmetric encryption)
- ✅ Algorithm validation enforced
- ✅ Public key cannot sign tokens
- ✅ No support for HS256

### 5. Password Timing Attacks

**Vulnerability**: Attacker measures response time to guess passwords

**Mitigations**:

- ✅ Constant-time password verification
- ✅ Argon2id built-in timing resistance
- ✅ Same response time for valid/invalid users

### 6. User Enumeration

**Vulnerability**: Attacker determines which usernames/emails exist

**Mitigations**:

- ✅ Same error message for invalid user/password
- ✅ Email masking in password reset responses
- ✅ Timing-safe user lookups
- ✅ Rate limiting prevents enumeration testing

### 7. Session Fixation

**Vulnerability**: Attacker forces user to use known session ID

**Mitigations**:

- ✅ New session on each login
- ✅ JWT tokens (stateless, unfixable)
- ✅ Token family rotation
- ✅ Session revocation on logout

### 8. Cross-Site Request Forgery (CSRF)

**Vulnerability**: Attacker tricks user into making unintended requests

**Mitigations**:

- ✅ JWT tokens in Authorization header (not cookies)
- ✅ CORS configuration
- ✅ SameSite cookie attribute (if using cookies)

### 9. SQL Injection

**Vulnerability**: Attacker injects SQL code into queries

**Mitigations**:

- ✅ SQLAlchemy ORM (parameterized queries)
- ✅ Input validation with Pydantic
- ✅ No raw SQL with user input

### 10. Mass Assignment

**Vulnerability**: Attacker sets unauthorized fields via API

**Mitigations**:

- ✅ Pydantic models with explicit field definitions
- ✅ Admin-only fields protected
- ✅ Role-based access control
- ✅ No direct database updates from user input

---

## Security Best Practices

### For Developers

#### 1. Never Log Sensitive Data

**DON'T**:

```python
logger.info(f"User login: {username} with password: {password}")  # ❌
logger.debug(f"JWT token: {access_token}")  # ❌
```

**DO**:

```python
logger.info(f"User login: {username}")  # ✅
logger.debug(f"JWT token generated for user: {user_id}")  # ✅
```

#### 2. Use Prepared Statements

**DON'T**:

```python
query = f"SELECT * FROM users WHERE username = '{username}'"  # ❌ SQL Injection
```

**DO**:

```python
user = db.query(User).filter(User.username == username).first()  # ✅ Parameterized
```

#### 3. Validate All Input

**DON'T**:

```python
user.role = request_data.role  # ❌ Unchecked assignment
```

**DO**:

```python
if request_data.role not in ['viewer', 'editor', 'admin']:  # ✅ Validated
    raise ValueError("Invalid role")
user.role = request_data.role
```

#### 4. Handle Errors Securely

**DON'T**:

```python
except Exception as e:
    return {"error": str(e)}  # ❌ Exposes internal details
```

**DO**:

```python
except Exception as e:
    logger.error(f"Error: {e}")  # ✅ Log internally
    return {"error": "An error occurred"}  # ✅ Generic message
```

### For Administrators

#### 1. Secure Environment Variables

```bash
# Set restrictive permissions on .env file
chmod 600 .env

# Never commit .env to version control
echo ".env" >> .gitignore

# Use strong, random values
JWT_PRIVATE_KEY_PATH=secrets/jwt/private_key.pem  # Generated by script
DATABASE_URL=postgresql://user:strong_random_password@localhost/db
```

#### 2. Enable HTTPS

```nginx
# Nginx configuration
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';

    # HSTS header
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

#### 3. Monitor Security Events

```python
# Alert on suspicious patterns
if failed_attempts > 10:
    alert_security_team(user_id, ip_address)

if session_count > max_sessions * 2:
    alert_security_team(user_id, "Unusual session count")

if token_reuse_detected:
    alert_security_team(user_id, "Token reuse attack")
```

#### 4. Regular Security Audits

```bash
# Check for vulnerable dependencies
pip-audit

# Run security scanners
bandit -r src/

# Review audit logs
grep "failed login" logs/audit.log | tail -100
```

### For Users

#### 1. Use Strong Passwords

- ✅ At least 12 characters
- ✅ Mix of uppercase, lowercase, numbers, symbols
- ✅ Unique to this service (not reused)
- ✅ Use a password manager

#### 2. Enable Two-Factor Authentication

(When implemented)

- ✅ Use authenticator app (not SMS)
- ✅ Save backup codes securely
- ✅ Don't share 2FA codes

#### 3. Review Active Sessions

```bash
# Regularly check active sessions
GET /auth/sessions

# Revoke unknown sessions
DELETE /auth/sessions/{session_id}
```

#### 4. Secure Your Devices

- ✅ Use antivirus/anti-malware
- ✅ Keep OS and browser updated
- ✅ Don't save passwords in browser (use password manager)
- ✅ Logout from shared devices

---

## Security Audit Checklist

### Pre-Deployment

- [ ] JWT keys generated (ES256, not HS256)
- [ ] Private key secured (600 permissions)
- [ ] Strong database password
- [ ] Redis authentication enabled
- [ ] SMTP credentials secured
- [ ] `.env` file not in version control
- [ ] Strong password policy enforced
- [ ] Rate limiting configured
- [ ] Account lockout enabled
- [ ] Session limits configured

### Deployment

- [ ] HTTPS enabled (TLS 1.2+)
- [ ] HSTS header configured
- [ ] CORS properly configured
- [ ] Security headers set
- [ ] Database encrypted connections
- [ ] Redis encrypted connections (if remote)
- [ ] Firewall rules configured
- [ ] Intrusion detection enabled
- [ ] Log aggregation configured
- [ ] Monitoring and alerting set up

### Post-Deployment

- [ ] Security scanning (OWASP ZAP, Burp Suite)
- [ ] Penetration testing
- [ ] Dependency audit (`pip-audit`)
- [ ] Code security scan (`bandit`)
- [ ] Log review (failed logins, errors)
- [ ] Session monitoring
- [ ] Performance testing
- [ ] Backup and recovery testing

### Ongoing

- [ ] Monthly dependency updates
- [ ] Quarterly security reviews
- [ ] Regular log reviews
- [ ] Incident response plan tested
- [ ] Security training for team
- [ ] Third-party security assessments

---

## Additional Resources

### OWASP Resources

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

### Security Standards

- [NIST Digital Identity Guidelines](https://pages.nist.gov/800-63-3/)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/)
- [ISO 27001 Information Security](https://www.iso.org/isoiec-27001-information-security.html)

### Tools and Libraries

- [Argon2 Password Hashing](https://github.com/P-H-C/phc-winner-argon2)
- [PyJWT Library](https://pyjwt.readthedocs.io/)
- [Bandit Security Linter](https://github.com/PyCQA/bandit)
- [pip-audit Dependency Scanner](https://github.com/pypa/pip-audit)

---

## Reporting Security Issues

If you discover a security vulnerability in PromptVault, please report it responsibly:

1. **DO NOT** create a public Codeberg issue
2. Email security@yourdomain.com with details
3. Include steps to reproduce
4. Allow time for fix before disclosure

We take security seriously and will respond promptly to legitimate reports.

---

## Additional Documentation

- [Deployment Guide](./AUTHENTICATION_DEPLOYMENT.md)
- [API Documentation](./AUTHENTICATION_API.md)
- [Testing Guide](./TESTING.md)
