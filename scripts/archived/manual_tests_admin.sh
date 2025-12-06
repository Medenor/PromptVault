#!/bin/bash

# AUTH-ADMIN Manual Tests
# Tests for admin user management endpoints

BASE_URL="http://localhost:8003/api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}✓ PASS${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}✗ FAIL${NC} $1"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

check_field() {
    echo "$1" | jq -e "$2" > /dev/null 2>&1
}

unique_id() {
    echo "test_$(date +%s)_$RANDOM"
}

# Setup admin account
log_info "Setting up admin account..."

# Create new admin user for testing
ADMIN_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_'$(unique_id)'","password":"SecureAdmin@123456","confirm_password":"SecureAdmin@123456","email":"admin_'$(unique_id)'@example.com"}')

ADMIN_ID=$(echo "$ADMIN_USER" | jq -r '.user.id // empty')
ADMIN_USERNAME=$(echo "$ADMIN_USER" | jq -r '.user.username // empty')

if [ -z "$ADMIN_ID" ]; then
    log_fail "Could not create admin user"
    exit 1
fi

# Promote user to admin role (direct DB operation)
cd "$(dirname "$0")/.." && python promote_to_admin.py "$ADMIN_USERNAME" > /dev/null
cd - > /dev/null

# Login with the promoted admin user
ADMIN_LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"'$ADMIN_USERNAME'","password":"SecureAdmin@123456"}')

ADMIN_TOKEN=$(echo "$ADMIN_LOGIN" | jq -r '.access_token // empty')
ADMIN_ID=$(echo "$ADMIN_LOGIN" | jq -r '.user.id // empty')
ADMIN_USERNAME=$(echo "$ADMIN_LOGIN" | jq -r '.user.username // empty')

if [ -z "$ADMIN_TOKEN" ]; then
    log_fail "Could not login as admin"
    exit 1
fi

log_info "Admin setup complete: $ADMIN_USERNAME"

echo ""
echo "================================================================"
echo "AUTH-ADMIN MANUAL TESTS"
echo "================================================================"
echo ""

# Create test users
log_info "Creating test users..."

VIEWER_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"viewer_'$(unique_id)'","password":"SecurePass@123456","confirm_password":"SecurePass@123456","email":"viewer_'$(unique_id)'@example.com"}')
VIEWER_ID=$(echo "$VIEWER_USER" | jq -r '.user.id')

EDITOR_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"editor_'$(unique_id)'","password":"SecurePass@123456","confirm_password":"SecurePass@123456","email":"editor_'$(unique_id)'@example.com"}')
EDITOR_ID=$(echo "$EDITOR_USER" | jq -r '.user.id')

echo ""

# AUTH-ADMIN-001
log_test "AUTH-ADMIN-001: List All Users with Pagination"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/users?page=1&page_size=10" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if check_field "$RESPONSE" '.users[]'; then
    COUNT=$(echo "$RESPONSE" | jq '.users | length')
    TOTAL=$(echo "$RESPONSE" | jq '.total')
    log_pass "Listed $COUNT users (total: $TOTAL)"
else
    log_fail "List users failed"
fi

echo ""

# AUTH-ADMIN-002
log_test "AUTH-ADMIN-002: Filter Users by Role"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/users?role=viewer" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if check_field "$RESPONSE" '.users[0].role' && [ "$(echo "$RESPONSE" | jq -r '.users[0].role')" = "viewer" ]; then
    log_pass "Filter by role succeeded"
else
    log_fail "Filter by role failed"
fi

echo ""

# AUTH-ADMIN-003
log_test "AUTH-ADMIN-003: Filter Users by Active Status"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/users?is_active=true" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if check_field "$RESPONSE" '.users[]'; then
    COUNT=$(echo "$RESPONSE" | jq '.users | length')
    log_pass "Filter by active status returned $COUNT users"
else
    log_fail "Filter by active status failed"
fi

echo ""

# AUTH-ADMIN-004
log_test "AUTH-ADMIN-004: View User Details"
RESPONSE=$(curl -s -X GET "$BASE_URL/admin/users/$VIEWER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if check_field "$RESPONSE" '.id'; then
    USERNAME=$(echo "$RESPONSE" | jq -r '.username')
    log_pass "User details retrieved: $USERNAME"
else
    log_fail "Get user details failed"
fi

echo ""

# AUTH-ADMIN-005
log_test "AUTH-ADMIN-005: Update User Role (Viewer to Editor)"
RESPONSE=$(curl -s -X PUT "$BASE_URL/admin/users/$VIEWER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"editor"}')

if check_field "$RESPONSE" '.role' && [ "$(echo "$RESPONSE" | jq -r '.role')" = "editor" ]; then
    log_pass "User role updated to editor"
else
    log_fail "Update user role failed"
fi

echo ""

# AUTH-ADMIN-006
log_test "AUTH-ADMIN-006: Update User Role (Editor to Admin)"
RESPONSE=$(curl -s -X PUT "$BASE_URL/admin/users/$EDITOR_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}')

if check_field "$RESPONSE" '.role' && [ "$(echo "$RESPONSE" | jq -r '.role')" = "admin" ]; then
    log_pass "User role updated to admin"
else
    log_fail "Update user role to admin failed"
fi

echo ""

# AUTH-ADMIN-007
log_test "AUTH-ADMIN-007: Deactivate User Account"

DEACTIVATE_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"deactivate_'$(unique_id)'","password":"SecurePass@123456","confirm_password":"SecurePass@123456","email":"deactivate_'$(unique_id)'@example.com"}')
DEACTIVATE_ID=$(echo "$DEACTIVATE_USER" | jq -r '.user.id')

RESPONSE=$(curl -s -X PUT "$BASE_URL/admin/users/$DEACTIVATE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}')

if echo "$RESPONSE" | jq -e '.is_active != null' > /dev/null 2>&1 && [ "$(echo "$RESPONSE" | jq -r '.is_active')" = "false" ]; then
    log_pass "User account deactivated"
else
    log_fail "Deactivate user failed"
fi

echo ""

# AUTH-ADMIN-008
log_test "AUTH-ADMIN-008: Reactivate User Account"
RESPONSE=$(curl -s -X PUT "$BASE_URL/admin/users/$DEACTIVATE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active":true}')

if echo "$RESPONSE" | jq -e '.is_active != null' > /dev/null 2>&1 && [ "$(echo "$RESPONSE" | jq -r '.is_active')" = "true" ]; then
    log_pass "User account reactivated"
else
    log_fail "Reactivate user failed"
fi

echo ""

# AUTH-ADMIN-009
log_test "AUTH-ADMIN-009: Deactivation Revokes Sessions"

SESSION_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"session_'$(unique_id)'","password":"SecurePass@123456","confirm_password":"SecurePass@123456","email":"session_'$(unique_id)'@example.com"}')
SESSION_ID=$(echo "$SESSION_USER" | jq -r '.user.id')
SESSION_USERNAME=$(echo "$SESSION_USER" | jq -r '.user.username')

SESSION_LOGIN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username_or_email":"'$SESSION_USERNAME'","password":"SecurePass@123456"}')
SESSION_TOKEN=$(echo "$SESSION_LOGIN" | jq -r '.access_token')

TEST_BEFORE=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $SESSION_TOKEN")

curl -s -X PUT "$BASE_URL/admin/users/$SESSION_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active":false}' > /dev/null

TEST_AFTER=$(curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $SESSION_TOKEN")

if check_field "$TEST_BEFORE" '.id' && (check_field "$TEST_AFTER" '.detail' || check_field "$TEST_AFTER" '.message'); then
    log_pass "Deactivation revoked user sessions"
else
    log_fail "Session not properly revoked"
fi

echo ""

# AUTH-ADMIN-010
log_test "AUTH-ADMIN-010: Delete User Account"

DELETE_USER=$(curl -s -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username":"delete_'$(unique_id)'","password":"SecurePass@123456","confirm_password":"SecurePass@123456","email":"delete_'$(unique_id)'@example.com"}')
DELETE_ID=$(echo "$DELETE_USER" | jq -r '.user.id')

RESPONSE=$(curl -s -X DELETE "$BASE_URL/admin/users/$DELETE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

if check_field "$RESPONSE" '.message'; then
    log_pass "User account deleted"
else
    log_fail "Delete user failed"
fi

echo ""

# AUTH-ADMIN-011
log_test "AUTH-ADMIN-011: Transfer User Prompts on Deletion"
log_info "Skipped (requires prompt creation)"

echo ""

# AUTH-ADMIN-012
log_test "AUTH-ADMIN-012: Admin Cannot Delete Self"
RESPONSE=$(curl -s -X DELETE "$BASE_URL/admin/users/$ADMIN_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

ERROR=$(echo "$RESPONSE" | jq -r '.message // .detail // empty')
if [[ "$ERROR" == *"cannot"* ]] || [[ "$ERROR" == *"self"* ]]; then
    log_pass "Admin cannot delete themselves"
else
    log_fail "Self-delete prevention failed"
fi

echo ""
echo "================================================================"
echo "SUMMARY"
echo "================================================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
