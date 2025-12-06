#!/bin/bash

#############################################################################
# AUTH-SESSION Manual Test Suite - Improved with Robust JSON Parsing
# Uses jq for reliable response parsing instead of grep/cut
#############################################################################

BASE_URL="http://localhost:8003"
TEST_USER_EMAIL="session_test_$(date +%s)@example.com"
TEST_USER_USERNAME="user_$(date +%s%N | cut -b1-8)"
TEST_USER_PASSWORD="TestPassword123!"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0
SKIPPED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASSED++))
}

fail_test() {
    echo -e "${RED}❌ $1${NC}"
    if [ -n "$2" ]; then
        echo -e "   ${RED}Error: $2${NC}"
    fi
    ((FAILED++))
}

skip_test() {
    echo -e "${YELLOW}⏭️  $1${NC}"
    if [ -n "$2" ]; then
        echo -e "   ${YELLOW}Reason: $2${NC}"
    fi
    ((SKIPPED++))
}

# Setup test user
setup_test_user() {
    echo -e "\n${BLUE}Setting up test user...${NC}"
    
    # Register
    REG_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$TEST_USER_USERNAME\",
            \"email\": \"$TEST_USER_EMAIL\",
            \"password\": \"$TEST_USER_PASSWORD\",
            \"confirm_password\": \"$TEST_USER_PASSWORD\"
        }")
    
    # Login
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username_or_email\": \"$TEST_USER_USERNAME\",
            \"password\": \"$TEST_USER_PASSWORD\"
        }")
    
    # Extract token using jq (robust)
    AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty' 2>/dev/null)
    
    if [ -z "$AUTH_TOKEN" ] || [ "$AUTH_TOKEN" = "null" ]; then
        echo -e "${RED}Login failed: $LOGIN_RESPONSE${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Test user ready${NC}"
    return 0
}

# AUTH-SESSION-001: View Active Sessions
test_auth_session_001() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-001: View Active Sessions${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Use jq to check if sessions exist and count them
    if SESSIONS_COUNT=$(echo "$RESPONSE" | jq '.sessions | length' 2>/dev/null); then
        if [ "$SESSIONS_COUNT" -gt 0 ]; then
            pass_test "AUTH-SESSION-001: View Active Sessions" "Found $SESSIONS_COUNT sessions"
        else
            fail_test "AUTH-SESSION-001: View Active Sessions" "No sessions found"
        fi
    else
        fail_test "AUTH-SESSION-001: View Active Sessions" "Invalid response: $RESPONSE"
    fi
}

# AUTH-SESSION-002: Session Metadata Accuracy
test_auth_session_002() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-002: Session Metadata Accuracy${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Use jq to check for required fields in first session
    REQUIRED_FIELDS=("id" "family_id" "created_at" "last_used_at" "expires_at" "ip_address" "user_agent")
    ALL_FIELDS_PRESENT=true
    
    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! echo "$RESPONSE" | jq -e ".sessions[0].$field" > /dev/null 2>&1; then
            echo -e "   Missing field: $field"
            ALL_FIELDS_PRESENT=false
        fi
    done
    
    if [ "$ALL_FIELDS_PRESENT" = true ]; then
        pass_test "AUTH-SESSION-002: Session Metadata Accuracy" "All required fields present"
    else
        fail_test "AUTH-SESSION-002: Session Metadata Accuracy" "Missing required fields"
    fi
}

# AUTH-SESSION-003: Revoke Individual Session
test_auth_session_003() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-003: Revoke Individual Session${NC}"
    
    # Get current sessions
    SESSIONS=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Extract first session ID using jq
    SESSION_ID=$(echo "$SESSIONS" | jq -r '.sessions[0].id // empty' 2>/dev/null)
    
    if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
        fail_test "AUTH-SESSION-003: Revoke Individual Session" "Could not get session ID"
        return
    fi
    
    # Revoke the session
    REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/auth/sessions/$SESSION_ID" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Extract HTTP code (last line) and body
    HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -1)
    BODY=$(echo "$REVOKE_RESPONSE" | sed '$d' || echo "$REVOKE_RESPONSE")
    
    if [ "$HTTP_CODE" = "200" ]; then
        pass_test "AUTH-SESSION-003: Revoke Individual Session"
    else
        fail_test "AUTH-SESSION-003: Revoke Individual Session" "HTTP $HTTP_CODE"
    fi
}

# AUTH-SESSION-004: Revoke All Sessions
test_auth_session_004() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-004: Revoke All Sessions${NC}"
    
    # Revoke all sessions
    REVOKE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Extract HTTP code (last line) and body
    HTTP_CODE=$(echo "$REVOKE_RESPONSE" | tail -1)
    BODY=$(echo "$REVOKE_RESPONSE" | sed '$d' || echo "$REVOKE_RESPONSE")
    
    if [ "$HTTP_CODE" = "200" ]; then
        # Extract count using jq
        COUNT=$(echo "$BODY" | jq '.count // 0' 2>/dev/null)
        pass_test "AUTH-SESSION-004: Revoke All Sessions" "Revoked $COUNT sessions"
    else
        fail_test "AUTH-SESSION-004: Revoke All Sessions" "HTTP $HTTP_CODE"
    fi
}

# Main test flow
main() {
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}AUTH-SESSION Manual Test Suite${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    
    # Setup
    if ! setup_test_user; then
        echo -e "${RED}Failed to setup test user${NC}"
        exit 1
    fi
    
    # Run tests
    test_auth_session_001
    test_auth_session_002
    test_auth_session_003
    test_auth_session_004
    
    # Summary
    echo -e "\n${BLUE}════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    echo -e "Passed:  ${GREEN}$PASSED${NC}"
    echo -e "Failed:  ${RED}$FAILED${NC}"
    echo -e "Skipped: ${YELLOW}$SKIPPED${NC}"
    
    TOTAL=$((PASSED + FAILED + SKIPPED))
    if [ "$FAILED" -eq 0 ]; then
        echo -e "\n${GREEN}✅ All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}❌ Some tests failed${NC}"
        exit 1
    fi
}

main "$@"
