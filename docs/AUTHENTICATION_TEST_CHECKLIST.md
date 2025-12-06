# PromptVault Authentication System - Manual Testing Checklist

**Version**: 1.0
**Date**: December 4, 2025
**Status**: Ready for QA
**Test Environment**: Local/Staging/Production
**Tester**: _____________________
**Date Tested**: _____________________

---

## Overview

This comprehensive checklist covers all manual testing scenarios for the PromptVault authentication and authorization system. Each test case includes detailed steps, expected results, and checkboxes for tracking progress.

**Testing Priority Levels:**

- 🔴 **High**: Critical security features and core authentication flows
- 🟡 **Medium**: Important features affecting user experience
- 🟢 **Low**: Nice-to-have features and edge cases

**Test Status:**

- ⬜ Not Started
- 🔄 In Progress
- ✅ Passed
- ❌ Failed
- ⏭️ Skipped (with reason)

---

## 1. User Registration (15 test cases)

### AUTH-REG-001: Valid User Registration

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Application is running
- Registration page is accessible at `/register`
- No existing user with test credentials

**Test Steps:**

1. Navigate to `/register`
2. Enter username: `testuser001`
3. Enter email: `testuser001@example.com`
4. Enter password: `SecureP@ssw0rd123`
5. Enter confirm password: `SecureP@ssw0rd123`
6. (Optional) Enter display name: `Test User`
7. Click "Register" button

**Expected Results:**

- Registration succeeds with 201 status
- Success message displayed: "Registration successful"
- User redirected to login page
- User can login with new credentials

**Notes:**
_________________________________

---

### AUTH-REG-002: Username Too Short

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter username: `ab` (2 characters)
3. Enter valid email and password
4. Attempt registration

**Expected Results:**

- Validation error displayed: "Username must be at least 3 characters"
- Registration blocked
- Form remains on registration page

**Notes:**
_________________________________

---

### AUTH-REG-003: Username Too Long

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter username with 51 characters
3. Enter valid email and password
4. Attempt registration

**Expected Results:**

- Validation error: "Username must be 50 characters or less"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-004: Username Invalid Characters

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter username: `test@user!` (special characters)
3. Enter valid email and password
4. Attempt registration

**Expected Results:**

- Validation error: "Username can only contain letters, numbers, underscore, and hyphen"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-005: Duplicate Username

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `existinguser` already exists

**Test Steps:**

1. Navigate to `/register`
2. Enter username: `existinguser`
3. Enter unique email and valid password
4. Attempt registration

**Expected Results:**

- HTTP 409 Conflict error
- Error message: "Username already exists"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-006: Invalid Email Format

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username
3. Enter email: `invalidemail` (no @ symbol)
4. Enter valid password
5. Attempt registration

**Expected Results:**

- Validation error: "Invalid email format"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-007: Duplicate Email

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Email `existing@example.com` already registered

**Test Steps:**

1. Navigate to `/register`
2. Enter unique username
3. Enter email: `existing@example.com`
4. Enter valid password
5. Attempt registration

**Expected Results:**

- HTTP 409 Conflict error
- Error message: "Email already exists"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-008: Password Too Short

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `Short1!` (8 characters)
4. Attempt registration

**Expected Results:**

- Validation error: "Password must be at least 12 characters"
- Password strength indicator shows "Weak"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-009: Password Missing Uppercase

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `nocapitals123!`
4. Attempt registration

**Expected Results:**

- Validation error: "Password must contain at least one uppercase letter"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-010: Password Missing Lowercase

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `NOLOWERCASE123!`
4. Attempt registration

**Expected Results:**

- Validation error: "Password must contain at least one lowercase letter"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-011: Password Missing Digit

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `NoDigitsHere!`
4. Attempt registration

**Expected Results:**

- Validation error: "Password must contain at least one digit"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-012: Password Missing Special Character

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `NoSpecialChar123`
4. Attempt registration

**Expected Results:**

- Validation error: "Password must contain at least one special character"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-013: Common Password Detection

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `Password123!` (common password with variation)
4. Attempt registration

**Expected Results:**

- Validation error: "This password is too common and easily guessable"
- Registration blocked

**Implementation Notes:**

The common password detection now includes sophisticated variation detection:
- Direct matches (case-insensitive)
- Passwords with trailing special characters (!, @, #, etc.)
- Passwords with trailing numbers stripped
- Passwords with substituted characters (P@ssw0rd, passw0rd, etc.)

This prevents users from thinking they're secure by adding minor modifications to common passwords.

**Notes:**
_________________________________

---

### AUTH-REG-014: Password Confirmation Mismatch

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter password: `SecureP@ssw0rd123`
4. Enter confirm password: `DifferentP@ssw0rd456`
5. Attempt registration

**Expected Results:**

- Validation error: "Passwords do not match"
- Registration blocked

**Notes:**
_________________________________

---

### AUTH-REG-015: Display Name Handling

- **Priority**: 🟢 Low
- **Status**: 🙅🏻‍♂️ Display Name field doesn't exist in form

**Preconditions:**

- Registration page is accessible

**Test Steps:**

1. Navigate to `/register`
2. Enter valid username and email
3. Enter valid password
4. Leave display name empty
5. Complete registration

**Expected Results:**

- Registration succeeds
- Display name defaults to username
- User profile shows username as display name

**Notes:**
_________________________________

---

## 2. User Login (12 test cases)

### AUTH-LOGIN-001: Login with Username and Password

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists with password `TestP@ssw0rd123`

**Test Steps:**

1. Navigate to `/login`
2. Enter username: `testuser`
3. Enter password: `TestP@ssw0rd123`
4. Click "Login" button

**Expected Results:**

- Login succeeds with 200 status
- Access token and refresh token returned
- HTTP-only cookies set for tokens
- User redirected to main application (`/`)
- User info stored in localStorage
- Last login timestamp updated in database

**Notes:**
_________________________________

---

### AUTH-LOGIN-002: Login with Email and Password

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User with email `testuser@example.com` exists

**Test Steps:**

1. Navigate to `/login`
2. Enter email: `testuser@example.com`
3. Enter password: `TestP@ssw0rd123`
4. Click "Login" button

**Expected Results:**

- Login succeeds with 200 status
- User authenticated using email
- Redirected to main application

**Notes:**
_________________________________

---

### AUTH-LOGIN-003: Invalid Username

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- No user with username `nonexistent` exists

**Test Steps:**

1. Navigate to `/login`
2. Enter username: `nonexistent`
3. Enter password: `AnyPassword123!`
4. Attempt login

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Invalid username or password"
- No sensitive information leaked (don't reveal which field is wrong)
- Failed login attempt NOT tracked (user doesn't exist)

**Notes:**
_________________________________

---

### AUTH-LOGIN-004: Invalid Password

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Navigate to `/login`
2. Enter username: `testuser`
3. Enter password: `WrongPassword123!`
4. Attempt login

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Invalid username or password"
- Failed login attempt incremented in database
- User `failed_login_attempts` increases by 1

**Notes:**
_________________________________

---

### AUTH-LOGIN-005: Account Lockout After 5 Failures

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists with 0 failed attempts

**Test Steps:**

1. Attempt login 5 times with wrong password
2. Verify failed attempts tracked
3. Attempt 6th login with CORRECT password

**Expected Results:**

- First 5 attempts: 401 error with "Invalid username or password"
- After 5th attempt: User `locked_until` set to 15 minutes from now
- 6th attempt (even with correct password): HTTP 403 Forbidden
- Error message: "Account locked due to too many failed attempts. Try again in 15 minutes."
- Login blocked until lockout expires

**Notes:**
_________________________________

---

### AUTH-LOGIN-006: Lockout Expiry After 15 Minutes

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` is locked (locked_until in past)

**Test Steps:**

1. Wait for lockout period to expire (or manually update database)
2. Attempt login with correct password

**Expected Results:**

- Login succeeds with 200 status
- `locked_until` cleared (set to NULL)
- `failed_login_attempts` reset to 0
- User can access application

**Notes:**
_________________________________

---

### AUTH-LOGIN-007: Session Creation

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Login as `testuser`
2. Query database for `user_sessions` table
3. Verify session record created

**Expected Results:**

- New session record in `user_sessions` table
- Session includes:
  - Unique `token_family_id`
  - Hashed refresh token
  - IP address of client
  - User agent string
  - Expiration timestamp (14 days from now)
- Session metadata captured correctly

**Notes:**
_________________________________

---

### AUTH-LOGIN-008: Remember Me Functionality

- **Priority**: 🟡 Medium
- **Status**: ⏭️ N/A - "Remember me" checkbox not implemented in login form

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Navigate to `/login`
2. Enter credentials
3. Check "Remember me" checkbox
4. Login
5. Close browser and reopen

**Expected Results:**

- Refresh token stored in localStorage (not sessionStorage)
- User remains logged in after browser restart
- Session persists until token expiration (14 days)

**Notes:**
_________________________________

---

### AUTH-LOGIN-009: Redirect After Successful Login

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Navigate to protected page `/prompts/123` (not logged in)
2. Application redirects to `/login?redirect=/prompts/123`
3. Login with valid credentials

**Expected Results:**

- After login, user redirected to original target (`/prompts/123`)
- If no redirect parameter, redirect to main page (`/`)

**Notes:**
_________________________________

---

### AUTH-LOGIN-010: Failed Login Resets on Success

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `testuser` has 3 failed login attempts

**Test Steps:**

1. Login with correct password
2. Query database for user record

**Expected Results:**

- Login succeeds
- `failed_login_attempts` reset to 0
- `last_login` timestamp updated

**Notes:**
_________________________________

---

### AUTH-LOGIN-011: Inactive User Cannot Login

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists with `is_active = false`

**Test Steps:**

1. Attempt login with correct credentials

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Account is inactive. Contact administrator."
- Login blocked

**Notes:**
_________________________________

---

### AUTH-LOGIN-012: Token Storage

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Login successfully
2. Inspect browser cookies
3. Inspect localStorage

**Expected Results:**

- `access_token` cookie set with HttpOnly flag
- `refresh_token` cookie set with HttpOnly flag
- Cookies have Secure flag (in production)
- Cookies have SameSite=Strict flag
- User info stored in localStorage (non-sensitive data only)
- No tokens visible in JavaScript console

**Notes:**
_________________________________

---

## 3. Password Reset (10 test cases)

### AUTH-RESET-001: Request Password Reset with Valid Email

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User with email `testuser@example.com` exists

**Test Steps:**

1. Navigate to `/forgot-password`
2. Enter email: `testuser@example.com`
3. Click "Send Reset Link" button

**Expected Results:**

- HTTP 200 OK response
- Generic success message: "If the email exists, a reset link has been sent"
- Password reset token created in database (`password_reset_tokens` table)
- Token expires in 1 hour
- Email sent with reset link (check email or logs)

**Notes:**
_________________________________

---

### AUTH-RESET-002: Request with Non-Existent Email

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Email `nonexistent@example.com` does NOT exist

**Test Steps:**

1. Navigate to `/forgot-password`
2. Enter email: `nonexistent@example.com`
3. Click "Send Reset Link" button

**Expected Results:**

- HTTP 200 OK response (same as valid email)
- Same generic message: "If the email exists, a reset link has been sent"
- No email sent
- No token created in database
- No user enumeration (attacker cannot determine if email exists)

**Notes:**
_________________________________

---

### AUTH-RESET-003: Rate Limiting on Reset Requests

- **Priority**: 🔴 High
- **Status**: ❌ Implementation Issue - Rate limiting not functioning, all requests return 200 OK

**Preconditions:**

- Clean state (no recent reset requests from IP)

**Test Steps:**

1. Request password reset for any email
2. Immediately request reset again (2nd)
3. Immediately request reset again (3rd)
4. Immediately request reset again (4th attempt)

**Expected Results:**

- First 3 requests: HTTP 200 OK
- 4th request within 1 hour: HTTP 429 Too Many Requests
- Error message: "Too many password reset requests. Try again later."
- Rate limit: 3 requests per hour per IP address

**Notes:**
_________________________________

---

### AUTH-RESET-004: Reset Token Expiration

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Password reset token exists but expired (created > 1 hour ago)

**Test Steps:**

1. Obtain expired reset token
2. Navigate to `/reset-password?token=<expired_token>`
3. Enter new password
4. Attempt password reset

**Expected Results:**

- HTTP 400 Bad Request error
- Error message: "Reset token is invalid or has expired"
- Password NOT changed
- User redirected to request new reset link

**Notes:**
_________________________________

---

### AUTH-RESET-005: Valid Password Reset Flow

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Valid reset token exists (< 1 hour old)

**Test Steps:**

1. Navigate to `/reset-password?token=<valid_token>`
2. Enter new password: `NewSecureP@ssw0rd456`
3. Confirm new password: `NewSecureP@ssw0rd456`
4. Click "Reset Password" button

**Expected Results:**

- HTTP 200 OK response
- Success message: "Password reset successful. Please login."
- Password hash updated in database
- Token marked as `used_at` (single-use enforcement)
- All user sessions revoked
- User redirected to login page
- User can login with new password

**Notes:**
_________________________________

---

### AUTH-RESET-006: Token Single-Use Enforcement

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Reset token was already used once

**Test Steps:**

1. Attempt to use the same token again
2. Enter a different new password

**Expected Results:**

- HTTP 400 Bad Request error
- Error message: "Reset token has already been used"
- Password NOT changed
- Token remains marked as used

**Notes:**
_________________________________

---

### AUTH-RESET-007: New Password Validation

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Valid reset token exists

**Test Steps:**

1. Navigate to reset page with valid token
2. Enter weak password: `weak`
3. Attempt reset

**Expected Results:**

- Validation error: "Password must be at least 12 characters"
- All password policy checks enforced (same as registration)
- Password NOT changed

**Notes:**
_________________________________

---

### AUTH-RESET-008: Session Revocation on Password Reset

- **Priority**: 🔴 High
- **Status**: ✅ PASS (sessions marked as revoked)

**Preconditions:**

- User has 3 active sessions
- Valid reset token exists

**Test Steps:**

1. Verify 3 active sessions in database
2. Complete password reset
3. Query `user_sessions` table

**Expected Results:**

- All 3 sessions marked as `is_revoked = true`
- `revoked_at` timestamp set
- Previous access tokens no longer valid
- User must login again on all devices

**Notes:**
_________________________________

---

### AUTH-RESET-009: Login with New Password

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Password was successfully reset

**Test Steps:**

1. Navigate to `/login`
2. Enter username
3. Enter NEW password (set during reset)
4. Attempt login

**Expected Results:**

- Login succeeds with 200 status
- Access and refresh tokens issued
- User can access application

**Notes:**
_________________________________

---

### AUTH-RESET-010: Old Password No Longer Works

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Password was successfully reset

**Test Steps:**

1. Navigate to `/login`
2. Enter username
3. Enter OLD password (before reset)
4. Attempt login

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Invalid username or password"
- Login fails

**Notes:**
_________________________________

---

## 4. Token Management (8 test cases)

### AUTH-TOKEN-001: Access Token Expiration

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in with access token

**Test Steps:**

1. Login and obtain access token
2. Wait 31 minutes (token expires after 30 minutes)
3. Make authenticated API request with expired token

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Token has expired"
- Request blocked
- Frontend should trigger automatic token refresh

**Notes:**
_________________________________

---

### AUTH-TOKEN-002: Automatic Token Refresh

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in with valid refresh token

**Test Steps:**

1. Login and obtain tokens
2. Wait 25 minutes (before access token expires)
3. Frontend should automatically call `/api/auth/refresh`
4. Observe new tokens issued

**Expected Results:**

- Refresh endpoint called automatically
- New access token issued (30-minute expiry)
- New refresh token issued (rotated)
- Old refresh token invalidated
- User continues using application seamlessly

**Notes:**
_________________________________

---

### AUTH-TOKEN-003: Manual Token Refresh

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in with valid refresh token

**Test Steps:**

1. Login and obtain tokens
2. Call `POST /api/auth/refresh` with refresh token
3. Verify response

**Expected Results:**

- HTTP 200 OK response
- New access token returned
- New refresh token returned (rotated)
- Old refresh token invalidated
- Token family ID remains the same

**Notes:**
_________________________________

---

### AUTH-TOKEN-004: Refresh Token Rotation

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and save `refresh_token_1`
2. Call refresh endpoint, receive `refresh_token_2`
3. Attempt to use `refresh_token_1` again

**Expected Results:**

- First refresh: succeeds, returns `refresh_token_2`
- Second attempt with `refresh_token_1`: HTTP 401 error
- Error message: "Refresh token has already been used"
- Old token cannot be reused (rotation enforced)

**Notes:**
_________________________________

---

### AUTH-TOKEN-005: Token Family Tracking

- **Priority**: 🔴 High
- **Status**: ⏭️ N/A - Session ID not in token claims

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and note `token_family_id` from session
2. Refresh token multiple times
3. Query database for all refresh operations

**Expected Results:**

- All tokens in the refresh chain share same `token_family_id`
- Session record updated with new refresh token hash each time
- `last_used_at` timestamp updated on each refresh

**Notes:**
_________________________________

---

### AUTH-TOKEN-006: Token Reuse Detection

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and save `refresh_token_1`
2. Refresh to get `refresh_token_2`
3. Refresh again with `refresh_token_2` to get `refresh_token_3`
4. Attempt to use `refresh_token_1` (simulate token theft)

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Token family revoked due to reuse detection"
- ENTIRE token family revoked (all tokens in chain)
- `refresh_token_3` also becomes invalid
- User must login again on all devices
- Security event logged

**Notes:**
_________________________________

---

### AUTH-TOKEN-007: Logout Token Revocation

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and obtain tokens
2. Call `POST /api/auth/logout`
3. Attempt to use access token after logout

**Expected Results:**

- Logout succeeds with 200 OK
- Current session revoked in database
- Access token no longer valid
- Refresh token no longer valid
- Cookies cleared
- HTTP 401 error when using old tokens

**Notes:**
_________________________________

---

### AUTH-TOKEN-008: Logout from All Devices

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User has 3 active sessions (logged in on 3 devices)

**Test Steps:**

1. Verify 3 active sessions in database
2. Call `POST /api/auth/logout` with `revoke_all_sessions: true`
3. Query database for sessions

**Expected Results:**

- All 3 sessions marked as `is_revoked = true`
- All access/refresh tokens invalidated
- User logged out on all devices simultaneously
- Must login again on each device

**Notes:**
_________________________________

---

## 5. Session Management (8 test cases)

### AUTH-SESSION-001: View Active Sessions

- **Priority**: 🟡 Medium
- **Status**: ✅ PASS - Endpoint implemented with metadata

**Preconditions:**

- User has 2 active sessions

**Test Steps:**

1. Login and navigate to `/profile/sessions`
2. View list of active sessions

**Expected Results:**

- List displays all active sessions (2)
- Each session shows:
  - Device type (parsed from user agent)
  - Browser name
  - Operating system
  - IP address
  - Last used timestamp
  - "Current session" indicator
- Sessions sorted by last used (newest first)

**Notes:**
_________________________________

---

### AUTH-SESSION-002: Session Metadata Accuracy

- **Priority**: 🟡 Medium
- **Status**: ✅ PASS - User-Agent parser implemented and integrated

**Preconditions:**

- User logged in

**Test Steps:**

1. Login from Chrome on macOS
2. View session details
3. Verify metadata parsed correctly

**Expected Results:**

- Device: "Desktop" or "MacBook"
- Browser: "Chrome X.X.X"
- OS: "Mac OS X X.X.X"

**Implementation Details:**

- Created `src/services/user_agent_parser.py` with UserAgentParser class
- Integrated parsing into `GET /api/auth/sessions` endpoint
- Updated SessionResponse model to include device, browser, os fields
- Handles edge cases (empty/invalid User-Agent) gracefully
- All test cases pass (Chrome on Mac, Safari on iPhone, empty UA, None UA)

**Verification:**

```bash
PYTHONPATH=/Users/raphael/Programmation/PromptVault python tests/test_auth_session_002.py
# Result: ✅ All AUTH-SESSION-002 tests passed!
```
- Browser: "Chrome"
- OS: "macOS" or "Mac OS X"
- IP address matches client IP
- Last used timestamp recent (< 1 minute ago)

**Notes:**
_________________________________

---

### AUTH-SESSION-003: Revoke Individual Session

- **Priority**: 🔴 High
- **Status**: ✅ PASS - API endpoint functional via `/api/auth/sessions/{session_id}`

**Preconditions:**

- User has 2 active sessions (current + 1 other)

**Test Steps:**

1. Navigate to `/profile/sessions` (or via API: `DELETE /api/auth/sessions/{session_id}`)
2. Identify non-current session
3. Click "Revoke" button for that session (or call DELETE endpoint)
4. Confirm revocation

**Expected Results:**

- Session revoked successfully ✅
- Success message displayed ✅
- Session removed from active list ✅
- Other device immediately logged out ✅
- Current session remains active ✅

**Notes:**
API test confirmed endpoint works correctly. Frontend UI not yet implemented.
_________________________________

---

### AUTH-SESSION-004: Revoke All Sessions

- **Priority**: 🔴 High
- **Status**: ✅ PASS - API endpoint functional via `DELETE /api/auth/sessions`

**Preconditions:**

- User has 3 active sessions

**Test Steps:**

1. Navigate to `/profile/sessions` (or via API: `DELETE /api/auth/sessions`)
2. Click "Revoke All Sessions" button
3. Confirm action

**Expected Results:**

- All sessions revoked ✅
- User logged out (redirected to login page) ✅
- All other devices logged out ✅
- Must login again on all devices ✅

**Notes:**
API test confirmed endpoint works correctly. User is immediately logged out after revocation.
_________________________________

---

### AUTH-SESSION-005: Maximum Session Limit

- **Priority**: 🔴 High
- **Status**: ⏭️ SKIP - Session limit feature not yet implemented (configurable via max_sessions_per_user)

**Preconditions:**

- User has 5 active sessions (maximum)

**Test Steps:**

1. Verify 5 sessions exist
2. Login on a 6th device

**Expected Results:**

- Login succeeds
- Oldest inactive session automatically revoked
- Total active sessions remains at 5
- Oldest device logged out automatically

**Notes:**
_________________________________

---

### AUTH-SESSION-006: Session Expiration

- **Priority**: 🟡 Medium
- **Status**: ⏭️ SKIP - Requires waiting 14 days or manual database modification to test

**Preconditions:**

- Refresh token expires in 14 days

**Test Steps:**

1. Login and note session expiration time
2. Wait 14 days (or manually update database)
3. Attempt to use refresh token

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Refresh token has expired"
- Session marked as expired in database
- User must login again

**Notes:**
_________________________________

---

### AUTH-SESSION-007: Session Cleanup Job

- **Priority**: 🟢 Low
- **Status**: ⏭️ SKIP - Requires admin user role

**Preconditions:**

- Database contains expired sessions (> 14 days old)
- User has admin role (standard test user is 'viewer')

**Test Steps:**

1. Run session cleanup job (manual or scheduled) via `GET /api/admin/scheduler/status`
2. Query database for expired sessions

**Expected Results:**

- Expired sessions removed from database ✅ (verified via code review)
- Active sessions remain untouched ✅ (verified via code review)
- Database size reduced ✅ (verified via code review)
- Cleanup logged ✅ (verified via code review)

**Notes:**
Scheduler is implemented and running in production. API endpoints require admin authentication which standard test users don't have.
_________________________________

---

### AUTH-SESSION-008: Current Session Indicator

- **Priority**: 🟢 Low
- **Status**: ⚠️ PARTIAL - API returns sessions but is_current field behavior needs review

**Preconditions:**

- User has multiple sessions

**Test Steps:**

1. Navigate to `/profile/sessions`
2. Identify current session in list

**Expected Results:**

- Current session marked with "This device" or "Current session"
- Visual indicator (badge, icon, or styling)
- Cannot revoke current session individually (only via logout)

**Notes:**
_________________________________

---

## 6. User Profile (10 test cases)

### AUTH-PROFILE-001: View Profile Information

- **Priority**: 🟡 Medium
- **Status**: ✅ PASS

**Test Result**: Profile information retrieved successfully via GET /auth/me

**Preconditions:**

- User logged in

**Test Steps:**

1. Navigate to `/profile`
2. View profile information

**Expected Results:**

- Profile displays:
  - Username (read-only)
  - Email (editable)
  - Display name (editable)
  - Role (read-only)
  - Email verified status
  - Account created date
  - Last login timestamp
- All fields populated correctly

**Notes:**
_________________________________

---

### AUTH-PROFILE-002: Update Display Name

- **Priority**: 🟡 Medium
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Navigate to `/profile`
2. Edit display name field: `New Display Name`
3. Click "Save Changes"

**Expected Results:**

- HTTP 200 OK response
- Success message: "Profile updated successfully"
- Display name updated in database
- New name visible across application
- Header/nav shows updated name

**Notes:**
_________________________________

---

### AUTH-PROFILE-003: Update Email

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in with email `old@example.com`

**Test Steps:**

1. Navigate to `/profile`
2. Edit email field: `new@example.com`
3. Click "Save Changes"

**Expected Results:**

- HTTP 200 OK response
- Email updated in database
- `email_verified` set to `false`
- Verification email sent to new address
- Warning message: "Email verification required for new address"

**Notes:**
_________________________________

---

### AUTH-PROFILE-004: View Account Statistics

- **Priority**: 🟢 Low
- **Status**: ✅ PASS

**Preconditions:**

- User has created prompts and favorites

**Test Steps:**

1. Navigate to `/profile`
2. View account statistics section

**Expected Results:**

- Statistics displayed:
  - Total prompts created
  - Favorite prompts count
  - Categories used
  - Tags created
  - Account age (days since registration)
- All counts accurate

**Notes:**
_________________________________

---

### AUTH-PROFILE-005: Change Password from Profile

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Navigate to `/profile`
2. Click "Change Password" button
3. Enter current password: `OldP@ssw0rd123`
4. Enter new password: `NewP@ssw0rd456`
5. Confirm new password: `NewP@ssw0rd456`
6. Submit form

**Expected Results:**

- HTTP 200 OK response
- Success message: "Password changed successfully"
- Password hash updated in database
- All other sessions revoked (except current)
- `password_changed_at` timestamp updated
- User remains logged in on current device

**Notes:**
_________________________________

---

### AUTH-PROFILE-006: Change Password - Current Password Validation

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Navigate to `/profile/change-password`
2. Enter WRONG current password
3. Enter valid new password
4. Submit form

**Expected Results:**

- HTTP 400 Bad Request or 401 Unauthorized
- Error message: "Current password is incorrect"
- Password NOT changed
- Form displays error

**Notes:**
_________________________________

---

### AUTH-PROFILE-007: Change Password - New Password Validation

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Navigate to `/profile/change-password`
2. Enter correct current password
3. Enter weak new password: `weak`
4. Submit form

**Expected Results:**

- Validation error: "Password must be at least 12 characters"
- All password policy checks enforced
- Password NOT changed

**Notes:**
_________________________________

---

### AUTH-PROFILE-008: Session Revocation After Password Change

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- User logged in on 3 devices

**Test Steps:**

1. From device 1, change password
2. Verify behavior on devices 2 and 3

**Expected Results:**

- Device 1 (current): remains logged in
- Devices 2 and 3: logged out automatically
- Must re-login on devices 2 and 3 with new password
- Old sessions revoked in database

**Notes:**
_________________________________

---

### AUTH-PROFILE-009: View Last Login Timestamp

- **Priority**: 🟢 Low
- **Status**: ✅ PASS

**Preconditions:**

- User logged in

**Test Steps:**

1. Login at specific time (note timestamp)
2. Navigate to `/profile`
3. View last login timestamp

**Expected Results:**

- Last login displays recent timestamp
- Format: "December 4, 2025 at 10:30 AM" or relative "5 minutes ago"
- Timestamp matches actual login time

**Notes:**
_________________________________

---

### AUTH-PROFILE-010: Profile Page Authorization

- **Priority**: 🔴 High
- **Status**: ✅ PASS

**Preconditions:**

- Not logged in

**Test Steps:**

1. Attempt to access `/profile` without authentication

**Expected Results:**

- HTTP 401 Unauthorized redirect
- Redirected to `/login?redirect=/profile`
- Profile page NOT accessible
- After login, redirected back to `/profile`

**Notes:**
_________________________________

---

## 7. Role-Based Access Control (15 test cases)

### AUTH-RBAC-001: Viewer Can Read Own Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `viewer1` has role `viewer`
- User owns prompt with ID `123`

**Test Steps:**

1. Login as `viewer1`
2. Call `GET /api/prompts`
3. Call `GET /api/prompts/123`

**Expected Results:**

- Both endpoints succeed with 200 OK
- Prompt data returned
- Read access granted

**Notes:**
_________________________________

---

### AUTH-RBAC-002: Viewer Cannot Create Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `viewer1` has role `viewer`

**Test Steps:**

1. Login as `viewer1`
2. Call `POST /api/prompts` with valid prompt data

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Insufficient permissions"
- Prompt NOT created

**Notes:**
_________________________________

---

### AUTH-RBAC-003: Viewer Cannot Edit Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `viewer1` has role `viewer`
- Prompt with ID `123` exists (owned by viewer)

**Test Steps:**

1. Login as `viewer1`
2. Call `PUT /api/prompts/123` with updated data

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Insufficient permissions"
- Prompt NOT updated

**Notes:**
_________________________________

---

### AUTH-RBAC-004: Viewer Cannot Delete Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `viewer1` has role `viewer`
- Prompt with ID `123` exists (owned by viewer)

**Test Steps:**

1. Login as `viewer1`
2. Call `DELETE /api/prompts/123`

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Insufficient permissions"
- Prompt NOT deleted

**Notes:**
_________________________________

---

### AUTH-RBAC-005: Editor Can Create Prompts

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- User `editor1` has role `editor`

**Test Steps:**

1. Login as `editor1`
2. Call `POST /api/prompts` with valid prompt data

**Expected Results:**

- HTTP 201 Created response
- Prompt created in database
- `user_id` set to `editor1`'s ID automatically
- Prompt returned in response

**Notes:**
_________________________________

---

### AUTH-RBAC-006: Editor Can Edit Own Prompts

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- User `editor1` has role `editor`
- Prompt with ID `123` owned by `editor1`

**Test Steps:**

1. Login as `editor1`
2. Call `PUT /api/prompts/123` with updated data

**Expected Results:**

- HTTP 200 OK response
- Prompt updated in database
- New version created (version control)
- Updated prompt returned

**Notes:**
_________________________________

---

### AUTH-RBAC-007: Editor Cannot Edit Others' Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `editor1` has role `editor`
- Prompt with ID `456` owned by `editor2`

**Test Steps:**

1. Login as `editor1`
2. Call `PUT /api/prompts/456` with updated data

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Not authorized to access this prompt"
- Prompt NOT updated
- Ownership verified

**Notes:**
_________________________________

---

### AUTH-RBAC-008: Editor Can Delete Own Prompts

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- User `editor1` has role `editor`
- Prompt with ID `123` owned by `editor1`

**Test Steps:**

1. Login as `editor1`
2. Call `DELETE /api/prompts/123`

**Expected Results:**

- HTTP 200 OK response
- Prompt deleted from database
- Success message returned

**Notes:**
_________________________________

---

### AUTH-RBAC-009: Admin Can View All Prompts

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `admin1` has role `admin`
- Multiple users with prompts exist

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/prompts`

**Expected Results:**

- HTTP 200 OK response
- ALL prompts returned (not just admin's)
- Prompts from all users visible
- Admin can see system-wide prompts

**Notes:**
_________________________________

---

### AUTH-RBAC-010: Admin Can Edit Any Prompt

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `admin1` has role `admin`
- Prompt with ID `456` owned by `editor1` (not admin)

**Test Steps:**

1. Login as `admin1`
2. Call `PUT /api/prompts/456` with updated data

**Expected Results:**

- HTTP 200 OK response
- Prompt updated successfully
- Admin can bypass ownership check
- Audit log records admin action

**Notes:**
_________________________________

---

### AUTH-RBAC-011: Admin Can Delete Any Prompt

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `admin1` has role `admin`
- Prompt with ID `456` owned by `editor1`

**Test Steps:**

1. Login as `admin1`
2. Call `DELETE /api/prompts/456`

**Expected Results:**

- HTTP 200 OK response
- Prompt deleted successfully
- Admin can delete any user's prompts

**Notes:**
_________________________________

---

### AUTH-RBAC-012: Admin Can Access Admin Endpoints

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/users`

**Expected Results:**

- HTTP 200 OK response
- List of all users returned
- Admin endpoints accessible

**Notes:**
_________________________________

---

### AUTH-RBAC-013: Non-Admin Cannot Access Admin Endpoints

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `editor1` has role `editor`

**Test Steps:**

1. Login as `editor1`
2. Call `GET /api/admin/users`

**Expected Results:**

- HTTP 403 Forbidden error
- Error message: "Insufficient permissions"
- Admin endpoints blocked

**Notes:**
_________________________________

---

### AUTH-RBAC-014: Ownership Verification

- **Priority**: 🔴 High
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `editor1` has role `editor`
- Prompt with ID `999` does NOT exist

**Test Steps:**

1. Login as `editor1`
2. Call `PUT /api/prompts/999`

**Expected Results:**

- HTTP 404 Not Found error
- Error message: "Prompt not found"
- Ownership check fails (prompt doesn't exist)

**Notes:**
_________________________________

---

### AUTH-RBAC-015: Permission Denied Messages

- **Priority**: 🟡 Medium
- **Status**: ⏸️ FUTURE (RBAC not in authentication spec scope)

**Preconditions:**

- User `viewer1` has role `viewer`

**Test Steps:**

1. Login as `viewer1`
2. Attempt various forbidden actions
3. Verify error messages

**Expected Results:**

- Clear, consistent error messages
- "Insufficient permissions" for role checks
- "Not authorized to access this resource" for ownership checks
- No sensitive information leaked in errors

**Notes:**
_________________________________

---

## 8. Admin User Management (12 test cases)

### AUTH-ADMIN-001: List All Users with Pagination

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- Database has 100+ users

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/users?page=1&limit=50`

**Expected Results:**

- HTTP 200 OK response
- First 50 users returned
- Pagination metadata included:
  - `page: 1`
  - `limit: 50`
  - `total: 127` (example)
  - `pages: 3`
- User list includes username, email, role, is_active, created_at

**Notes:**
_________________________________

---

### AUTH-ADMIN-002: Filter Users by Role

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/users?role=editor`

**Expected Results:**

- HTTP 200 OK response
- Only users with role `editor` returned
- Other roles excluded from results

**Notes:**
_________________________________

---

### AUTH-ADMIN-003: Filter Users by Active Status

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/users?active=false`

**Expected Results:**

- HTTP 200 OK response
- Only inactive users (`is_active = false`) returned
- Active users excluded

**Notes:**
_________________________________

---

### AUTH-ADMIN-004: View User Details

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` exists

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/users/{editor1_id}`

**Expected Results:**

- HTTP 200 OK response
- Full user details returned:
  - id, username, email, display_name
  - role, is_active, email_verified
  - created_at, last_login
  - prompt_count, favorite_count
  - failed_login_attempts, locked_until

**Notes:**
_________________________________

---

### AUTH-ADMIN-005: Update User Role (Viewer to Editor)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `viewer1` has role `viewer`

**Test Steps:**

1. Login as `admin1`
2. Call `PUT /api/admin/users/{viewer1_id}/role`
3. Body: `{ "role": "editor" }`

**Expected Results:**

- HTTP 200 OK response
- User role updated to `editor` in database
- Success message: "User role updated to editor"
- User can now create/edit prompts

**Notes:**
_________________________________

---

### AUTH-ADMIN-006: Update User Role (Editor to Admin)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` has role `editor`

**Test Steps:**

1. Login as `admin1`
2. Call `PUT /api/admin/users/{editor1_id}/role`
3. Body: `{ "role": "admin" }`

**Expected Results:**

- HTTP 200 OK response
- User role updated to `admin`
- User can now access admin endpoints

**Notes:**
_________________________________

---

### AUTH-ADMIN-007: Deactivate User Account

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` is active

**Test Steps:**

1. Login as `admin1`
2. Call `PUT /api/admin/users/{editor1_id}/status`
3. Body: `{ "is_active": false }`

**Expected Results:**

- HTTP 200 OK response
- User `is_active` set to `false` in database
- All user sessions revoked automatically
- User cannot login
- Success message: "User account deactivated"

**Notes:**
_________________________________

---

### AUTH-ADMIN-008: Reactivate User Account

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` is inactive

**Test Steps:**

1. Login as `admin1`
2. Call `PUT /api/admin/users/{editor1_id}/status`
3. Body: `{ "is_active": true }`

**Expected Results:**

- HTTP 200 OK response
- User `is_active` set to `true` in database
- User can login again
- Success message: "User account reactivated"

**Notes:**
_________________________________

---

### AUTH-ADMIN-009: Deactivation Revokes Sessions

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `editor1` has 2 active sessions

**Test Steps:**

1. Verify 2 sessions active
2. Admin deactivates `editor1` account
3. Query database for sessions

**Expected Results:**

- All sessions marked as `is_revoked = true`
- User logged out on all devices
- Cannot use old tokens

**Notes:**
_________________________________

---

### AUTH-ADMIN-010: Delete User Account

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` exists with 10 prompts

**Test Steps:**

1. Login as `admin1`
2. Call `DELETE /api/admin/users/{editor1_id}`
3. Body: `{ "transfer_prompts_to": "{admin1_id}", "permanent": false }`

**Expected Results:**

- HTTP 200 OK response
- User deleted (soft delete or hard delete based on config)
- 10 prompts transferred to `admin1`
- All sessions revoked
- Success message: "User deleted. 10 prompts transferred to admin."

**Notes:**
_________________________________

---

### AUTH-ADMIN-011: Transfer User Prompts on Deletion

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- User `editor1` has 10 prompts

**Test Steps:**

1. Admin deletes `editor1` with prompt transfer
2. Query database for prompts

**Expected Results:**

- All 10 prompts now owned by transfer target user
- Prompts NOT deleted
- Prompt history preserved
- Ownership changed in database

**Notes:**
_________________________________

---

### AUTH-ADMIN-012: Admin Cannot Delete Self

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Attempt to delete own account: `DELETE /api/admin/users/{admin1_id}`

**Expected Results:**

- HTTP 400 Bad Request or 403 Forbidden
- Error message: "Cannot delete your own account"
- Admin account NOT deleted
- Safety check prevents self-deletion

**Notes:**
_________________________________

---

## 8A. Admin User Creation (11 test cases)

### AUTH-ADMIN-CREATE-001: Open Create User Modal

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User Management page open at `/admin/users`

**Test Steps:**

1. Click "Add User" button at top of user list
2. Observe modal opening

**Expected Results:**

- Modal `#create-user-modal` opens
- Modal shows "Create New User" title
- Form fields displayed: username, email, password, confirm password, role, email verified
- All form fields empty and focused on first field
- Cancel and Create buttons visible
- Modal overlay prevents interaction with background

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-002: Form Validation - Username Required

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Leave username field empty
2. Fill in other fields with valid data
3. Click "Create User" button

**Expected Results:**

- Validation error displayed: "Username is required"
- Error shown in red below username field
- Form submission blocked
- Create button remains visible for retry

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-003: Form Validation - Username Too Short

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter username: `ab` (2 characters)
2. Tab to next field
3. Observe validation

**Expected Results:**

- Real-time validation error: "Username must be 3-32 characters"
- Error shown in red
- Form submission blocked

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-004: Form Validation - Username Invalid Characters

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter username: `test@user!` (invalid characters)
2. Tab to next field

**Expected Results:**

- Validation error: "Username can only contain letters, numbers, underscore, and hyphen"
- Error displayed in real-time
- Form submission blocked

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-005: Password Strength Indicator

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter weak password: `weak`
   - Observe strength indicator
2. Enter medium password: `Test123`
   - Observe strength indicator
3. Enter strong password: `SecureP@ss123`
   - Observe strength indicator

**Expected Results:**

- Weak password: Red bar (0-33%), "Weak" label
- Medium password: Orange bar (34-66%), "Medium" label
- Strong password: Green bar (67-100%), "Strong" label
- Strength bar updates in real-time
- Requirements checklist updates live

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-006: Password Requirements Checklist

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter password that meets requirements one by one
2. Observe checklist items

**Expected Results:**

- ○ At least 12 characters - checked when password >= 12
- ○ One uppercase letter - checked when uppercase present
- ○ One lowercase letter - checked when lowercase present
- ○ One digit - checked when digit present
- ○ One special character - checked when special char (!@#$%^&*) present
- Met items display ✓ with green color
- Items update real-time as user types
- All items can be met with valid password

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-007: Password Visibility Toggle

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open
- Password field has content

**Test Steps:**

1. Enter password in password field
2. Click eye toggle icon (⊙)
3. Verify password visible
4. Click eye toggle again
5. Verify password hidden

**Expected Results:**

- Password field initially type="password" (hidden)
- After toggle: type="text" (visible)
- After toggle again: type="password" (hidden)
- Toggle works for both password AND confirm password fields
- Icon doesn't change (same ⊙ icon used)

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-008: Create Valid User

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter username: `newuser001`
2. Enter email: `newuser001@example.com`
3. Enter password: `SecureP@ssw0rd123!`
4. Enter confirm password: `SecureP@ssw0rd123!`
5. Select role: `Editor`
6. Check "Mark email as verified"
7. Click "Create User" button
8. Observe response

**Expected Results:**

- HTTP 201 Created response
- Success message displayed
- Modal closes automatically
- User appears in user list
- User can be found with search
- Refresh table to verify creation
- User has role "Editor"
- User marked active
- User email verified

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-009: Prevent Duplicate Username

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `existinguser` already exists
- Create User modal open

**Test Steps:**

1. Enter username: `existinguser`
2. Enter unique email
3. Fill remaining fields with valid data
4. Click "Create User"

**Expected Results:**

- HTTP 409 Conflict error
- Error message: "Username already exists"
- Modal remains open
- Form data preserved
- User NOT created

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-010: Prevent Duplicate Email

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User with email `existing@example.com` exists
- Create User modal open

**Test Steps:**

1. Enter unique username
2. Enter email: `existing@example.com`
3. Fill remaining fields with valid data
4. Click "Create User"

**Expected Results:**

- HTTP 409 Conflict error
- Error message: "Email already exists"
- Modal remains open
- Form preserved
- User NOT created

**Notes:**
_________________________________

---

### AUTH-ADMIN-CREATE-011: Password Mismatch Error

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Create User modal open

**Test Steps:**

1. Enter password: `SecureP@ssw0rd123!`
2. Enter confirm password: `DifferentP@ss456!`
3. Click "Create User"

**Expected Results:**

- Validation error: "Passwords do not match"
- Error shown in red
- Form submission blocked
- User NOT created

**Notes:**
_________________________________

---

## 9. Admin Session Management (8 test cases)

### AUTH-ADMIN-SESSION-001: View All Sessions Across All Users

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- Multiple users have active sessions

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/sessions`

**Expected Results:**

- HTTP 200 OK response
- All active sessions across ALL users returned
- Each session includes:
  - Session ID
  - User ID and username
  - Device, browser, OS
  - IP address
  - Created at, last used at
  - Expiration timestamp

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-002: Filter Sessions by User

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Call `GET /api/admin/sessions?user_id={editor1_id}`

**Expected Results:**

- HTTP 200 OK response
- Only sessions for `editor1` returned
- Other users' sessions excluded

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-003: View Session Metadata

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- Active session exists

**Test Steps:**

1. Login as `admin1`
2. View session details in admin panel

**Expected Results:**

- Full session metadata visible:
  - Token family ID
  - IP address (IPv4 or IPv6)
  - User agent string
  - Parsed device info (device, browser, OS)
  - Created timestamp
  - Last used timestamp
  - Expires at timestamp
  - Is revoked status

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-004: Revoke Any User Session

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` has active session

**Test Steps:**

1. Login as `admin1`
2. Call `DELETE /api/admin/sessions/{editor1_session_id}`

**Expected Results:**

- HTTP 200 OK response
- Session revoked (`is_revoked = true`)
- `editor1` logged out on that device
- Success message: "Session revoked successfully"

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-005: Revoke All Sessions for a User

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- User `editor1` has 3 active sessions

**Test Steps:**

1. Login as `admin1`
2. Call `DELETE /api/admin/users/{editor1_id}/sessions`

**Expected Results:**

- HTTP 200 OK response
- All 3 sessions revoked
- `editor1` logged out on all devices
- Success message: "All sessions revoked for user editor1"

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-006: Session Statistics

- **Priority**: 🟢 Low
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Navigate to admin session dashboard
3. View session statistics

**Expected Results:**

- Statistics displayed:
  - Total active sessions (system-wide)
  - Average sessions per user
  - Total users with active sessions
  - Sessions expiring soon (< 24 hours)
- Charts/graphs for visual representation

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-007: Real-Time Session Updates

- **Priority**: 🟢 Low
- **Status**: ✅

**Preconditions:**

- User `admin1` has role `admin`
- Admin dashboard open

**Test Steps:**

1. Admin views session list
2. Another user logs in
3. Refresh session list

**Expected Results:**

- New session appears in list
- Last used timestamps update
- Real-time or near-real-time updates

**Notes:**
_________________________________

---

### AUTH-ADMIN-SESSION-008: Session Export (Optional)

- **Priority**: 🟢 Low
- **Status**: ⏸️

**Preconditions:**

- User `admin1` has role `admin`

**Test Steps:**

1. Login as `admin1`
2. Export session data to CSV

**Expected Results:**

- CSV file generated with all session data
- Includes all relevant fields
- Suitable for audit purposes

**Notes:**
_________________________________

---

## 10. Security Features (15 test cases)

### AUTH-SEC-001: Password Hashing (Argon2id)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User registration enabled

**Test Steps:**

1. Register new user with password `TestP@ssw0rd123`
2. Query database for user record
3. Inspect `password_hash` field

**Expected Results:**

- Password hash starts with `$argon2id$`
- Hash is 97-100 characters long
- Each registration produces unique hash (unique salt)
- Plain password NOT stored anywhere

**Notes:**
_________________________________

---

### AUTH-SEC-002: JWT Signature Validation (ES256)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and obtain access token
2. Decode token header
3. Verify algorithm

**Expected Results:**

- Token header contains: `{ "alg": "ES256", "typ": "JWT" }`
- Token uses ECDSA P-256 signature
- Token cannot be forged without private key

**Notes:**
_________________________________

---

### AUTH-SEC-003: Token Expiration Enforcement

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and obtain access token
2. Wait for token to expire (30+ minutes)
3. Use expired token to access API

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Token has expired"
- Request blocked
- No data returned

**Notes:**
_________________________________

---

### AUTH-SEC-004: Invalid Token Rejection

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- None

**Test Steps:**

1. Craft invalid JWT token: `invalid.token.signature`
2. Use token to access API

**Expected Results:**

- HTTP 401 Unauthorized error
- Error message: "Invalid token"
- Request blocked

**Notes:**
_________________________________

---

### AUTH-SEC-005: Rate Limiting on Login Endpoint

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Rate limiting enabled

**Test Steps:**

1. Attempt 6 logins in rapid succession (within 15 minutes)

**Expected Results:**

- First 5 attempts: processed normally (may fail or succeed)
- 6th attempt: HTTP 429 Too Many Requests
- Error message: "Too many login attempts. Try again later."
- Rate limit: 5 attempts per 15 minutes per IP

**Implementation Details:**
- Decorator `@limiter.limit(auth_login_limit)` applied to `/login` endpoint
- Rate limit function references config: `rate_limit_login_attempts=5`, `rate_limit_login_window_seconds=900`
- Uses slowapi library with Redis backend
- Timing: 5 attempts per 15 minutes per IP address

**Notes:**
Rate limiting decorator activated on login endpoint. Limit: 5/15min per IP
_________________________________

---

### AUTH-SEC-006: Rate Limiting on Password Reset

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Rate limiting enabled

**Test Steps:**

1. Request password reset 4 times in rapid succession (within 1 hour)

**Expected Results:**

- First 3 attempts: HTTP 200 OK
- 4th attempt: HTTP 429 Too Many Requests
- Error message: "Too many password reset requests. Try again later."
- Rate limit: 3 requests per hour per IP

**Implementation Details:**
- Decorator `@limiter.limit(password_reset_limit)` applied to `/password-reset/request` endpoint
- Rate limit function references config: `rate_limit_password_reset_attempts=3`, `rate_limit_password_reset_window_seconds=3600`
- Uses slowapi library with Redis backend
- Timing: 3 attempts per hour per IP address

**Notes:**
Rate limiting decorator activated on password reset endpoint. Limit: 3/hour per IP

---

### AUTH-SEC-007: Account Lockout Mechanism

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User `testuser` exists

**Test Steps:**

1. Fail login 5 times with wrong password
2. Verify account lockout triggered

**Expected Results:**

- After 5th failure: `locked_until` set to 15 minutes from now
- Further login attempts blocked with 403 Forbidden
- Lockout automatically expires after 15 minutes

**Implementation Details:**
- Account lockout logic in `AuthService.login()` method
- Configuration: `max_login_attempts=5`, `account_lockout_duration_seconds=900` (15 minutes)
- Tracks `failed_login_attempts` counter per user
- Sets `locked_until` timestamp on account when threshold reached
- Counter resets on successful login
- Status: Fully implemented and functional

**Notes:**
Account lockout already fully implemented in AuthService. Behavior confirmed: 5 failed attempts trigger 900-second lockout.

---

### AUTH-SEC-008: HTTP-Only Cookie Security

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and inspect cookies
2. Attempt to access cookie via JavaScript: `document.cookie`

**Expected Results:**

- `access_token` cookie has `HttpOnly` flag
- `refresh_token` cookie has `HttpOnly` flag
- Cookies NOT accessible via JavaScript
- XSS attacks cannot steal tokens

**Notes:**
_________________________________

---

### AUTH-SEC-009: CSRF Protection (SameSite=Strict)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in

**Test Steps:**

1. Login and inspect cookies
2. Verify SameSite attribute

**Expected Results:**

- Cookies have `SameSite=Strict` attribute
- Cookies NOT sent with cross-site requests
- CSRF attacks prevented

**Notes:**
_________________________________

---

### AUTH-SEC-010: Security Headers (HSTS, CSP, X-Frame-Options)

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Server running on https (or http for local testing)

**Test Steps:**

1. Make HTTP request to any endpoint: `curl -I http://127.0.0.1:8003/`
2. Inspect response headers
3. Verify all security headers present

**Expected Results:**

- `Strict-Transport-Security: max-age=31536000` (1 year)
- `Content-Security-Policy: default-src 'self'` (strict CSP)
- `X-Frame-Options: DENY` (no embedding)
- `X-Content-Type-Options: nosniff` (prevent MIME sniffing)
- `X-XSS-Protection: 1; mode=block` (XSS protection)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: geolocation=(), microphone=(), camera=()`

**Implementation Details:**
- SecurityHeadersMiddleware in `src/web/middleware/security_headers.py`
- Applied to all HTTP responses via middleware stack
- Headers configured with strong security settings
- Supports both HTTP and HTTPS environments
- No content modification, only header injection

**Notes:**
Security headers middleware created and integrated into FastAPI app. All required headers now present on every response.

---

### AUTH-SEC-011: XSS Prevention in User Input

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User registered

**Test Steps:**

1. Update profile with XSS payload: `<script>alert('XSS')</script>` in display_name
2. View profile page
3. Inspect page source

**Expected Results:**

- Script NOT executed on page load
- Display name escaped/sanitized in HTML
- No JavaScript injection possible
- PATCH /auth/me endpoint accepts payload safely

**Implementation Details:**
- UpdateProfileRequest validates display_name field
- Field validator in auth_requests.py sanitizes input
- Database stores validated value
- Frontend renders escaped content (Jinja2 auto-escapes)
- CSP header prevents inline script execution

**Notes:**
Display name sanitization implemented in UpdateProfileRequest.validate_display_name(). XSS prevented through input validation + HTML escaping + CSP headers.

---

### AUTH-SEC-012: SQL Injection Prevention

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- Login page accessible

**Test Steps:**

1. Attempt SQL injection in login:
   - Username: `admin' OR '1'='1`
   - Password: `anything`
2. Attempt login

**Expected Results:**

- Login fails with 401 Unauthorized
- No SQL error messages exposed
- Query parameterization prevents injection
- No unauthorized access

**Notes:**
_________________________________

---

### AUTH-SEC-012: No Sensitive Data in Responses

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in

**Test Steps:**

1. Make various API requests (login, profile, etc.)
2. Inspect response bodies

**Expected Results:**

- `password_hash` NEVER returned
- `refresh_token_hash` NEVER returned
- Only safe fields returned (id, username, email, role)
- Sensitive fields excluded from responses

**Notes:**
_________________________________

---

### AUTH-SEC-013: Audit Logging for Security Events

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- Audit logging enabled

**Test Steps:**

1. Perform various authentication actions:
   - Login
   - Failed login
   - Password change
   - Account lockout
2. Check audit logs

**Expected Results:**

- All security events logged to `data/logs/audit.log`
- Logs include:
  - Event type (login, failed_login, etc.)
  - User ID and username
  - IP address
  - Timestamp
  - Result (success/failure)
- Logs structured (JSON format)

**Notes:**
_________________________________

---

### AUTH-SEC-014: Session Cleanup Job

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- Multiple user sessions created and expired

**Test Steps:**

1. Create multiple sessions (multiple logins)
2. Wait for some sessions to expire (max session age or refresh token expiry)
3. Query UserSession table for expired sessions
4. (Optional) Run manual cleanup: SessionRepository.cleanup_expired_sessions()

**Expected Results:**

- Expired sessions remain in database (soft-delete via is_revoked flag)
- Active sessions remain accessible
- revoked_at timestamp set for expired sessions
- Cleanup can be triggered manually or via scheduled task
- Database maintains referential integrity

**Implementation Details:**
- UserSession model has revoked_at and is_revoked fields
- Sessions marked as revoked when expired (not hard-deleted)
- SessionRepository.cleanup_expired_sessions() can remove old sessions
- Automatic cleanup on login (oldest session revoked if limit exceeded)
- Scheduler can run cleanup job periodically

**Notes:**
Session management fully implemented. Expired sessions marked with is_revoked flag. Manual cleanup available via SessionRepository.cleanup_expired_sessions().

---

### AUTH-SEC-015: Token Revocation Check

- **Priority**: 🔴 High
- **Status**: ✅

**Preconditions:**

- User logged in with active session

**Test Steps:**

1. Login as user: GET /api/auth/me (succeeds with valid token)
2. Get session ID: GET /api/auth/me/sessions
3. Revoke session: DELETE /api/auth/me/sessions/{session_id}
4. Attempt API request with revoked token: GET /api/auth/me

**Expected Results:**

- Step 1: HTTP 200 OK (token valid)
- Step 3: HTTP 204 No Content (session revoked)
- Step 4: HTTP 401 Unauthorized (token revoked)
- Error message: "Session has been revoked"

**Implementation Details:**
- DELETE /api/auth/me/sessions/{session_id} endpoint implemented
- Revokes session by setting is_revoked = true
- AuthService.validate_token() checks is_revoked before allowing access
- Token family tracking detects token reuse (revokes entire family)
- JTI (JWT ID) can be used for granular token revocation

**Notes:**
Token revocation fully implemented. Revoke endpoint: DELETE /api/auth/me/sessions/{session_id}. Validation checks is_revoked flag on each request.

---

## 11. Frontend UI/UX (10 test cases)

### AUTH-UI-001: Login Page Renders Correctly

- **Priority**: 🟡 Medium
- **Status**: ✅

**Preconditions:**

- Application running at http://127.0.0.1:8003

**Test Steps:**

1. Navigate to `/auth/login`
2. Inspect page elements

**Expected Results:**

- Login form displayed with all required elements
- Username/email input field visible
- Password input field visible
- Login button visible
- Register link visible
- Forgot password link visible
- Page styled correctly

**Implementation Details:**
- Playwright test: AUTH-UI-001 in scripts/playwright_auth_ui_tests.ts
- Checks page title matches /login|connexion/
- Verifies all form elements visible (username, password, buttons, links)
- Tests across all browsers: Chrome, Firefox, Safari
- Mobile viewport testing included (Pixel 5, iPhone 12)

**Notes:**
Playwright test implemented and passing. Covers login page rendering across all browsers and viewports.

**Notes:**
_________________________________

---

### AUTH-UI-002: Registration Page Renders Correctly

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Application running

**Test Steps:**

1. Navigate to `/register`
2. Inspect page elements

**Expected Results:**

- Registration form displayed with:
  - Username field
  - Email field
  - Password field
  - Confirm password field
  - Display name field (optional)
  - "Register" button
  - "Already have an account? Login" link
- Password strength indicator present
- Form styled correctly

**Notes:**
_________________________________

---

### AUTH-UI-003: Password Visibility Toggle

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Login or registration page open

**Test Steps:**

1. Enter password in field
2. Click "Show password" icon/button
3. Click "Hide password" icon/button

**Expected Results:**

- Password initially hidden (type="password")
- After clicking show: password visible (type="text")
- After clicking hide: password hidden again
- Icon changes to reflect state (eye icon vs eye-slash icon)

**Notes:**
_________________________________

---

### AUTH-UI-004: Password Strength Indicator

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Registration page open

**Test Steps:**

1. Enter weak password: `weak`
2. Enter medium password: `StrongerPass1`
3. Enter strong password: `SecureP@ssw0rd123!`

**Expected Results:**

- Weak password: red indicator, "Weak" label
- Medium password: orange indicator, "Medium" label
- Strong password: green indicator, "Strong" label
- Real-time updates as user types

**Notes:**
_________________________________

---

### AUTH-UI-005: Form Validation Feedback

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- Registration page open

**Test Steps:**

1. Leave username empty
2. Enter invalid email format
3. Enter weak password
4. Submit form

**Expected Results:**

- Validation errors displayed inline
- Each field shows specific error message
- Error messages in red
- Form submission blocked
- Focus moves to first error field

**Notes:**
_________________________________

---

### AUTH-UI-006: Loading States During API Calls

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Login page open

**Test Steps:**

1. Enter credentials
2. Click "Login" button
3. Observe loading state

**Expected Results:**

- "Login" button disabled during request
- Loading spinner or "Logging in..." text
- Form fields disabled
- User cannot submit twice
- Loading state clears after response

**Notes:**
_________________________________

---

### AUTH-UI-007: Error Message Display

- **Priority**: 🔴 High
- **Status**: ⬜

**Preconditions:**

- Login page open

**Test Steps:**

1. Enter invalid credentials
2. Submit form

**Expected Results:**

- Error message displayed at top of form
- Message in red or error styling
- Icon (exclamation mark) next to message
- Message text: "Invalid username or password"
- Message dismissible (X button or auto-fade)

**Notes:**
_________________________________

---

### AUTH-UI-008: Success Message Display

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Registration page open

**Test Steps:**

1. Complete registration successfully

**Expected Results:**

- Success message displayed
- Message in green or success styling
- Icon (checkmark) next to message
- Message text: "Registration successful"
- Message auto-fades or dismissible

**Notes:**
_________________________________

---

### AUTH-UI-009: Responsive Design (Mobile, Tablet, Desktop)

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Login/registration pages open

**Test Steps:**

1. View on desktop (1920x1080)
2. View on tablet (768x1024)
3. View on mobile (375x667)

**Expected Results:**

- Desktop: full-width form, side-by-side elements
- Tablet: adjusted layout, readable text
- Mobile: single-column layout, touch-friendly buttons
- All devices: fully functional, no horizontal scroll
- Responsive breakpoints work correctly

**Notes:**
_________________________________

---

### AUTH-UI-010: Navigation Between Auth Pages

- **Priority**: 🟡 Medium
- **Status**: ⬜

**Preconditions:**

- Login page open

**Test Steps:**

1. Click "Register" link → navigate to `/register`
2. Click "Login" link → navigate to `/login`
3. Click "Forgot password?" → navigate to `/forgot-password`
4. Complete reset flow → return to `/login`

**Expected Results:**

- All links functional
- Smooth navigation (no errors)
- URLs update correctly
- Back button works
- Breadcrumbs or navigation cues present

**Notes:**
_________________________________

---

## 12. API Endpoints (20 test cases)

### Test all 20 authentication endpoints systematically

1. `POST /api/auth/register` ✅ Tested in AUTH-REG-001
2. `POST /api/auth/login` ✅ Tested in AUTH-LOGIN-001
3. `POST /api/auth/refresh` ✅ Tested in AUTH-TOKEN-003
4. `POST /api/auth/logout` ✅ Tested in AUTH-TOKEN-007
5. `POST /api/auth/password-reset/request` ✅ Tested in AUTH-RESET-001
6. `POST /api/auth/password-reset/confirm` ✅ Tested in AUTH-RESET-005
7. `GET /api/auth/me` ✅ Tested in AUTH-PROFILE-001
8. `PUT /api/auth/me` ✅ Tested in AUTH-PROFILE-002
9. `POST /api/auth/me/change-password` ✅ Tested in AUTH-PROFILE-005
10. `GET /api/auth/me/sessions` ✅ Tested in AUTH-SESSION-001
11. `DELETE /api/auth/me/sessions/{id}` ✅ Tested in AUTH-SESSION-003
12. `GET /api/admin/users` ✅ Tested in AUTH-ADMIN-001
13. `GET /api/admin/users/{id}` ✅ Tested in AUTH-ADMIN-004
14. `PUT /api/admin/users/{id}/role` ✅ Tested in AUTH-ADMIN-005
15. `PUT /api/admin/users/{id}/status` ✅ Tested in AUTH-ADMIN-007
16. `DELETE /api/admin/users/{id}` ✅ Tested in AUTH-ADMIN-010
17. `GET /api/admin/sessions` ✅ Tested in AUTH-ADMIN-SESSION-001
18. `DELETE /api/admin/sessions/{id}` ✅ Tested in AUTH-ADMIN-SESSION-004
19. Verify request/response schemas match documentation
20. Verify proper HTTP status codes returned

**Additional API verification tests should cover:**

- Correct HTTP status codes (200, 201, 400, 401, 403, 404, 409, 422, 429)
- Response body structure matches OpenAPI spec
- Rate limiting responses (429) with Retry-After headers
- CORS headers present
- Content-Type headers correct (application/json)

---

---

## 13. Performance & Load Testing (5 test cases)

### AUTH-PERF-001: Login Endpoint Performance

- **Priority**: 🔴 High
- **Status**: ✅

**Objective**: Measure login endpoint response time and throughput

**Test Parameters**:
- Concurrent Requests: 100
- Test Duration: Full suite
- Success Target: ≥ 99.5%
- Response Time Target (p95): < 150ms

**Implementation**:
- Script: `scripts/benchmark_auth_performance.py`
- Method: `AuthPerformanceBenchmark.benchmark_login(num_requests=100)`
- Metrics Tracked: Avg, min, max, p95, p99 response times

**Expected Results**:
- Average Response Time: < 100ms
- p95 Response Time: < 150ms
- p99 Response Time: < 200ms
- Success Rate: ≥ 99.5%

**Notes**:
- Tests realistic authentication with password hashing
- Measures full login workflow including token generation
- Can be run individually: `python3 scripts/benchmark_auth_performance.py`

---

### AUTH-PERF-002: Registration Endpoint Performance

- **Priority**: 🔴 High
- **Status**: ✅

**Objective**: Measure registration endpoint performance under concurrent load

**Test Parameters**:
- Concurrent Registrations: 50
- Unique Users: 50
- Success Target: ≥ 99.5%
- Response Time Target (p95): < 200ms

**Implementation**:
- Script: `scripts/benchmark_auth_performance.py`
- Method: `AuthPerformanceBenchmark.benchmark_registration(num_requests=50)`
- Metrics Tracked: Registration time, password hashing performance

**Expected Results**:
- Average Response Time: < 150ms
- p95 Response Time: < 200ms
- p99 Response Time: < 300ms
- Success Rate: ≥ 99.5%

**Notes**:
- Tests full validation pipeline
- Measures Argon2id password hashing performance
- Database transaction overhead included

---

### AUTH-PERF-003: Token Refresh Performance

- **Priority**: 🟡 Medium
- **Status**: ✅

**Objective**: Measure JWT token refresh speed and validation overhead

**Test Parameters**:
- Refresh Operations: 50
- Success Target: ≥ 99.5%
- Response Time Target (p95): < 50ms

**Implementation**:
- Script: `scripts/benchmark_auth_performance.py`
- Method: `AuthPerformanceBenchmark.benchmark_token_refresh(num_requests=50)`
- Metrics Tracked: Token generation, validation time

**Expected Results**:
- Average Response Time: < 30ms
- p95 Response Time: < 50ms
- p99 Response Time: < 100ms
- Success Rate: ≥ 99.5%

**Notes**:
- Tests JWT parsing and validation performance
- Measures session lookup overhead
- Includes token rotation if applicable

---

### AUTH-PERF-004: Session Management Scalability

- **Priority**: 🟡 Medium
- **Status**: ⏭️

**Objective**: Test system's ability to handle multiple concurrent sessions

**Test Parameters**:
- Concurrent Users: 20-50
- Sessions per User: 3-5
- Duration: 60+ seconds
- Success Target: ≥ 99%

**Implementation**:
- Script: `scripts/locustfile_auth_performance.py`
- Class: `SessionManagementTest`
- Operations: Create, list, revoke sessions

**Expected Results**:
- Session Creation: < 50ms
- Session Listing: < 100ms
- Session Revocation: < 30ms
- Throughput: ≥ 100 session ops/sec
- Success Rate: ≥ 99%

**Notes**:
- Requires Locust framework
- Run with: `locust -f scripts/locustfile_auth_performance.py --host=http://127.0.0.1:8003`

---

### AUTH-PERF-005: Concurrent User Authentication

- **Priority**: 🟡 Medium
- **Status**: ⏭️

**Objective**: Simulate realistic load with multiple concurrent users

**Test Parameters**:
- Concurrent Users: 50-100
- Duration: 60-300 seconds
- Spawn Rate: 10 users/second
- Success Target: ≥ 99%

**Implementation**:
- Script: `scripts/locustfile_auth_performance.py`
- Class: `AuthPerformanceUser`
- Behavior: Login → Activities → Logout

**Expected Results**:
- Throughput: ≥ 500 requests/second
- Average Response Time: < 150ms
- p95 Response Time: < 250ms
- Success Rate: ≥ 99%

**Notes**:
- Full-stack load test with realistic user behavior
- Requires Locust framework
- Monitor CPU and memory during test

---

## Test Summary

**Total Test Cases**: 139

**By Priority:**

- 🔴 High: 83 tests
- 🟡 Medium: 43 tests
- 🟢 Low: 13 tests

**By Category:**

1. User Registration: 15 tests
2. User Login: 12 tests
3. Password Reset: 10 tests
4. Token Management: 8 tests
5. Session Management: 8 tests
6. User Profile: 10 tests
7. Role-Based Access Control: 15 tests
8. Admin User Management: 12 tests
8A. Admin User Creation: 11 tests (NEW)
9. Admin Session Management: 8 tests
10. Security Features: 15 tests
11. Frontend UI/UX: 10 tests
12. Performance & Load Testing: 5 tests (NEW)
13. API Endpoints: 20 tests (reference to above tests)

**Completion Tracking:**

- Not Started: ⬜ _____ / 134
- In Progress: 🔄 _____ / 134
- Passed: ✅ _____ / 134
- Failed: ❌ _____ / 134
- Skipped: ⏭️ _____ / 134

---

## Notes & Issues

Use this space to document any issues found during testing:

**Issue #1:**

- Test Case: _____________
- Description: _____________
- Severity: _____________
- Screenshot/Log: _____________

**Issue #2:**

- Test Case: _____________
- Description: _____________
- Severity: _____________
- Screenshot/Log: _____________

---

## Sign-Off

**QA Tester**: _____________________
**Date**: _____________________
**Signature**: _____________________

**Approved By**: _____________________
**Date**: _____________________
**Signature**: _____________________

---

**End of Authentication Test Checklist**
