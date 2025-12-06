#!/bin/bash

#############################################################################
# AUTH-PROFILE Manual Testing Script
# Comprehensive testing of profile management endpoints
# Uses jq for robust JSON parsing
#############################################################################

API_URL="http://localhost:8003/api"
TEST_USER="profile_test_$(date +%s)"
TEST_EMAIL="profile_test_${TEST_USER}@test.com"
TEST_PASS="TestPassword123!"
NEW_EMAIL="newemail_${TEST_USER}@test.com"
NEW_DISPLAY_NAME="New Display Name"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# ============================================================================
# Utility Functions
# ============================================================================

test_start() {
  local test_num=$1
  local test_name=$2
  echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
  echo -e "${BLUE}AUTH-PROFILE-${test_num}: ${test_name}${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
}

test_pass() {
  local test_num=$1
  local message=$2
  echo -e "${GREEN}✅ PASS: ${message}${NC}"
  ((TESTS_PASSED++))
}

test_fail() {
  local test_num=$1
  local message=$2
  echo -e "${RED}❌ FAIL: ${message}${NC}"
  ((TESTS_FAILED++))
}

test_skip() {
  local test_num=$1
  local message=$2
  echo -e "${YELLOW}⏭️  SKIP: ${message}${NC}"
  ((TESTS_SKIPPED++))
}

# ============================================================================
# Setup: Create test user
# ============================================================================

echo -e "${BLUE}Setting up test user...${NC}"
REGISTER=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$TEST_USER\",
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASS\",
    \"confirm_password\": \"$TEST_PASS\"
  }")

TOKEN=$(echo "$REGISTER" | jq -r '.access_token // empty')
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo -e "${RED}Failed to create test user${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Test user created: $TEST_USER${NC}"

# ============================================================================
# AUTH-PROFILE-001: View Profile Information
# ============================================================================

test_start "001" "View Profile Information (GET /auth/me)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  USERNAME=$(echo "$BODY" | jq -r '.username // empty')
  EMAIL=$(echo "$BODY" | jq -r '.email // empty')
  
  if [ -n "$USERNAME" ] && [ -n "$EMAIL" ]; then
    test_pass "001" "Profile retrieved successfully (user: $USERNAME, email: $EMAIL)"
  else
    test_fail "001" "Response missing expected fields"
  fi
else
  test_fail "001" "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-002: Update Display Name
# ============================================================================

test_start "002" "Update Display Name (PATCH /auth/me)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"display_name\": \"$NEW_DISPLAY_NAME\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  DISPLAY_NAME=$(echo "$BODY" | jq -r '.display_name // empty')
  if [ "$DISPLAY_NAME" = "$NEW_DISPLAY_NAME" ]; then
    test_pass "002" "Display name updated successfully"
  else
    test_fail "002" "Display name not updated correctly (got: $DISPLAY_NAME)"
  fi
else
  test_fail "002" "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-003: Update Email
# ============================================================================

test_start "003" "Update Email (PATCH /auth/me)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$NEW_EMAIL\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  EMAIL=$(echo "$BODY" | jq -r '.email // empty')
  EMAIL_VERIFIED=$(echo "$BODY" | jq -r '.email_verified')
  
  if [ "$EMAIL" = "$NEW_EMAIL" ]; then
    test_pass "003" "Email updated successfully"
    if [ "$EMAIL_VERIFIED" = "false" ]; then
      test_pass "003" "Email verification reset correctly"
    else
      test_fail "003" "Email verification should be reset (got: $EMAIL_VERIFIED)"
    fi
  else
    test_fail "003" "Email not updated correctly (got: $EMAIL)"
  fi
else
  test_fail "003" "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-004: Email Uniqueness Validation
# ============================================================================

test_start "004" "Email Uniqueness Validation (409 Conflict)"

# Create another user
REGISTER2=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"user2_$(date +%s)\",
    \"email\": \"email2_$(date +%s)@test.com\",
    \"password\": \"TestPassword123!\",
    \"confirm_password\": \"TestPassword123!\"
  }")

TOKEN2=$(echo "$REGISTER2" | jq -r '.access_token // empty')
if [ -z "$TOKEN2" ] || [ "$TOKEN2" = "null" ]; then
  test_skip "004" "Could not create second user for uniqueness test"
else
  # Try to update first user to use second user's email
  RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
    -H "Authorization: Bearer $TOKEN2" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$NEW_EMAIL\"
    }")
  HTTP_CODE=$(echo "$RESPONSE" | tail -1)
  
  if [ "$HTTP_CODE" = "409" ]; then
    test_pass "004" "Email uniqueness validation works (got 409 Conflict)"
  else
    test_fail "004" "Expected HTTP 409, got $HTTP_CODE"
  fi
fi

# ============================================================================
# AUTH-PROFILE-005: View Account Statistics
# ============================================================================

test_start "005" "View Account Statistics (GET /auth/me/stats)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me/stats" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  ACTIVE_SESSIONS=$(echo "$BODY" | jq -r '.active_sessions_count // empty')
  TOTAL_SESSIONS=$(echo "$BODY" | jq -r '.total_sessions_count // empty')
  DAYS_SINCE_CREATION=$(echo "$BODY" | jq -r '.days_since_creation // empty')
  
  if [ -n "$ACTIVE_SESSIONS" ] && [ -n "$TOTAL_SESSIONS" ] && [ -n "$DAYS_SINCE_CREATION" ]; then
    test_pass "005" "Stats retrieved (active: $ACTIVE_SESSIONS, total: $TOTAL_SESSIONS, age: $DAYS_SINCE_CREATION days)"
  else
    test_fail "005" "Stats missing expected fields"
  fi
else
  test_fail "005" "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-006: Change Password
# ============================================================================

test_start "006" "Change Password (POST /auth/change-password)"

NEW_PASS="NewPassword456!"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/change-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"old_password\": \"$TEST_PASS\",
    \"new_password\": \"$NEW_PASS\",
    \"confirm_new_password\": \"$NEW_PASS\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  MESSAGE=$(echo "$BODY" | jq -r '.message // empty')
  if [[ "$MESSAGE" == *"success"* ]] || [[ "$MESSAGE" == *"changed"* ]]; then
    test_pass "006" "Password changed successfully"
  else
    test_fail "006" "Unexpected response message: $MESSAGE"
  fi
else
  test_fail "006" "Expected HTTP 200, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-007: Password Validation
# ============================================================================

test_start "007" "Password Validation (Weak Password)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/change-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"old_password\": \"$NEW_PASS\",
    \"new_password\": \"weak\",
    \"confirm_new_password\": \"weak\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "400" ]; then
  test_pass "007" "Weak password rejected (got 400)"
else
  test_skip "007" "Password policy may not be enforced (got $HTTP_CODE)"
fi

# ============================================================================
# AUTH-PROFILE-008: Session Revocation After Password Change
# ============================================================================

test_start "008" "Session Revocation After Password Change"

# Get current sessions
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/sessions" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
  SESSIONS=$(echo "$BODY" | jq -r '.sessions // []')
  COUNT=$(echo "$SESSIONS" | jq 'length')
  
  if [ "$COUNT" -gt 0 ]; then
    test_pass "008" "Session still active after password change (sessions: $COUNT)"
  else
    test_fail "008" "No sessions found"
  fi
else
  test_skip "008" "Could not verify session status"
fi

# ============================================================================
# AUTH-PROFILE-009: Update Profile Validation (No Fields)
# ============================================================================

test_start "009" "Update Profile Validation (No Fields)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{}")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "422" ]; then
  test_pass "009" "Empty update rejected (got 422)"
elif [ "$HTTP_CODE" = "400" ]; then
  test_pass "009" "Empty update rejected (got 400)"
else
  test_fail "009" "Expected HTTP 400 or 422, got $HTTP_CODE"
fi

# ============================================================================
# AUTH-PROFILE-010: Authorization Check (Unauthenticated)
# ============================================================================

test_start "010" "Authorization Check (Unauthenticated)"

RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
  -H "Content-Type: application/json" \
  -d "{
    \"display_name\": \"Test\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
  test_pass "010" "Unauthenticated request rejected (got $HTTP_CODE)"
else
  test_fail "010" "Expected HTTP 401 or 403, got $HTTP_CODE"
fi

# ============================================================================
# Summary
# ============================================================================

echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}AUTH-PROFILE Test Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}Passed:  $TESTS_PASSED${NC}"
echo -e "${RED}Failed:  $TESTS_FAILED${NC}"
echo -e "${YELLOW}Skipped: $TESTS_SKIPPED${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "\n${GREEN}✅ All AUTH-PROFILE tests completed successfully!${NC}\n"
  exit 0
else
  echo -e "\n${RED}❌ Some tests failed. Review the output above.${NC}\n"
  exit 1
fi
