#!/bin/bash

# Manual testing script for AUTH-SESSION tests (003-008)
# Tests session management endpoints with real API

BASE_URL="http://localhost:8003"
TEST_USER_EMAIL="session_test_$(date +%s)@example.com"
TEST_USER_PASSWORD="TestPassword123!"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
SKIPPED=0

# Functions
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
            \"email\": \"$TEST_USER_EMAIL\",
            \"password\": \"$TEST_USER_PASSWORD\",
            \"password_confirm\": \"$TEST_USER_PASSWORD\"
        }")
    
    # Login
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"email\": \"$TEST_USER_EMAIL\",
            \"password\": \"$TEST_USER_PASSWORD\"
        }")
    
    AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo -e "${RED}Failed to get auth token${NC}"
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
    
    if echo "$RESPONSE" | grep -q '"sessions"'; then
        SESSIONS_COUNT=$(echo "$RESPONSE" | grep -o '"id":"[^"]*' | wc -l)
        pass_test "AUTH-SESSION-001: View Active Sessions" "Found $SESSIONS_COUNT sessions"
    else
        fail_test "AUTH-SESSION-001: View Active Sessions" "$RESPONSE"
    fi
}

# AUTH-SESSION-002: Session Metadata Accuracy
test_auth_session_002() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-002: Session Metadata Accuracy${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Check for required fields
    REQUIRED_FIELDS=("id" "user_id" "created_at" "last_activity_at" "expires_at" "user_agent" "ip_address" "is_current")
    
    MISSING_FIELDS=()
    for field in "${REQUIRED_FIELDS[@]}"; do
        if ! echo "$RESPONSE" | grep -q "\"$field\""; then
            MISSING_FIELDS+=("$field")
        fi
    done
    
    if [ ${#MISSING_FIELDS[@]} -eq 0 ]; then
        pass_test "AUTH-SESSION-002: Session Metadata Accuracy"
    else
        fail_test "AUTH-SESSION-002: Session Metadata Accuracy" "Missing fields: ${MISSING_FIELDS[*]}"
    fi
}

# AUTH-SESSION-003: Revoke Individual Session
test_auth_session_003() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-003: Revoke Individual Session${NC}"
    
    # Get sessions
    SESSIONS_BEFORE=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    SESSION_ID=$(echo "$SESSIONS_BEFORE" | grep -o '"id":"[^"]*' | head -1 | cut -d'"' -f4)
    
    if [ -z "$SESSION_ID" ]; then
        fail_test "AUTH-SESSION-003: Revoke Individual Session" "No session to revoke"
        return
    fi
    
    # Revoke session
    REVOKE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/auth/sessions/$SESSION_ID" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    if echo "$REVOKE_RESPONSE" | grep -q '"message"' || [ -z "$REVOKE_RESPONSE" ]; then
        sleep 1
        
        # Check if revoked
        SESSIONS_AFTER=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json")
        
        if ! echo "$SESSIONS_AFTER" | grep -q "\"$SESSION_ID\""; then
            pass_test "AUTH-SESSION-003: Revoke Individual Session"
        else
            fail_test "AUTH-SESSION-003: Revoke Individual Session" "Session still present after revocation"
        fi
    else
        fail_test "AUTH-SESSION-003: Revoke Individual Session" "$REVOKE_RESPONSE"
    fi
}

# AUTH-SESSION-004: Revoke All Sessions
test_auth_session_004() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-004: Revoke All Sessions${NC}"
    
    # Revoke all sessions
    REVOKE_RESPONSE=$(curl -s -X DELETE "$BASE_URL/api/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    if echo "$REVOKE_RESPONSE" | grep -q '"message"' || [ -z "$REVOKE_RESPONSE" ]; then
        sleep 1
        
        # Try to access with old token
        TEST_RESPONSE=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -w "\n%{http_code}")
        
        HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -1)
        
        if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
            pass_test "AUTH-SESSION-004: Revoke All Sessions" "User logged out (HTTP $HTTP_CODE)"
        else
            fail_test "AUTH-SESSION-004: Revoke All Sessions" "User still authenticated (HTTP $HTTP_CODE)"
        fi
    else
        fail_test "AUTH-SESSION-004: Revoke All Sessions" "$REVOKE_RESPONSE"
    fi
}

# AUTH-SESSION-005: Maximum Session Limit
test_auth_session_005() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-005: Maximum Session Limit${NC}"
    skip_test "AUTH-SESSION-005: Maximum Session Limit" "Requires configuration of max_sessions_per_user. Check config."
}

# AUTH-SESSION-006: Session Expiration
test_auth_session_006() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-006: Session Expiration${NC}"
    skip_test "AUTH-SESSION-006: Session Expiration" "Requires waiting for token expiration. Manual verification needed."
}

# AUTH-SESSION-007: Session Cleanup Job
test_auth_session_007() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-007: Session Cleanup Job${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/admin/scheduler/status" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        if echo "$BODY" | grep -q '"is_running":true'; then
            pass_test "AUTH-SESSION-007: Session Cleanup Job" "Scheduler is running"
        else
            skip_test "AUTH-SESSION-007: Session Cleanup Job" "Scheduler exists but not running"
        fi
    elif [ "$HTTP_CODE" = "403" ]; then
        fail_test "AUTH-SESSION-007: Session Cleanup Job" "Admin permissions required"
    else
        fail_test "AUTH-SESSION-007: Session Cleanup Job" "HTTP $HTTP_CODE"
    fi
}

# AUTH-SESSION-008: Current Session Indicator
test_auth_session_008() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-008: Current Session Indicator${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    # Setup test user again for this test since previous revoked all
    if ! setup_test_user; then
        fail_test "AUTH-SESSION-008: Current Session Indicator" "Could not setup test user"
        return
    fi
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/auth/sessions" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json")
    
    CURRENT_COUNT=$(echo "$RESPONSE" | grep -o '"is_current":true' | wc -l)
    
    if [ "$CURRENT_COUNT" = "1" ]; then
        pass_test "AUTH-SESSION-008: Current Session Indicator" "Exactly 1 current session marked"
    else
        fail_test "AUTH-SESSION-008: Current Session Indicator" "Expected 1 current session, found $CURRENT_COUNT"
    fi
}

# Summary
print_summary() {
    TOTAL=$((PASSED + FAILED + SKIPPED))
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}Test Summary:${NC}"
    echo -e "  ${GREEN}Passed: $PASSED${NC}"
    echo -e "  ${RED}Failed: $FAILED${NC}"
    echo -e "  ${YELLOW}Skipped: $SKIPPED${NC}"
    echo -e "  Total: $TOTAL"
    echo -e "${BLUE}============================================================${NC}"
}

# Main
main() {
    echo -e "\n${BLUE}============================================================${NC}"
    echo -e "${BLUE}AUTH-SESSION Manual Testing Suite${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    if ! setup_test_user; then
        echo -e "${RED}Failed to setup test user${NC}"
        exit 1
    fi
    
    test_auth_session_001
    test_auth_session_002
    test_auth_session_003
    test_auth_session_004
    test_auth_session_005
    test_auth_session_006
    test_auth_session_007
    test_auth_session_008
    
    print_summary
}

main
