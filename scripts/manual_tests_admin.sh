#!/bin/bash

# Manual testing script for AUTH-SESSION-007 (Scheduler admin endpoint)
# Tests session management with admin user

BASE_URL="http://localhost:8003"
ADMIN_USERNAME="testuser"
ADMIN_PASSWORD="TestP@ssw0rd123"

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

# Setup admin user
setup_admin_user() {
    echo -e "\n${BLUE}Logging in as admin user...${NC}"
    
    # Login
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{
            \"username_or_email\": \"$ADMIN_USERNAME\",
            \"password\": \"$ADMIN_PASSWORD\"
        }")
    
    AUTH_TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$AUTH_TOKEN" ]; then
        echo -e "${RED}Login response: $LOGIN_RESPONSE${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✅ Admin user authenticated${NC}"
    return 0
}

# AUTH-SESSION-007: Session Cleanup Job (Admin endpoint)
test_auth_session_007() {
    echo -e "\n${BLUE}Testing AUTH-SESSION-007: Session Cleanup Job (Admin Endpoint)${NC}"
    
    RESPONSE=$(curl -s -X GET "$BASE_URL/api/admin/scheduler/status" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        if echo "$BODY" | grep -q '"is_running":true'; then
            pass_test "AUTH-SESSION-007: Session Cleanup Job" "Scheduler is running"
            echo -e "   ${BLUE}Response: $BODY${NC}"
        elif echo "$BODY" | grep -q '"is_running":false'; then
            fail_test "AUTH-SESSION-007: Session Cleanup Job" "Scheduler is not running"
            echo -e "   ${BLUE}Response: $BODY${NC}"
        else
            pass_test "AUTH-SESSION-007: Session Cleanup Job" "Scheduler endpoint responds"
            echo -e "   ${BLUE}Response: $BODY${NC}"
        fi
    elif [ "$HTTP_CODE" = "403" ]; then
        fail_test "AUTH-SESSION-007: Session Cleanup Job" "Admin permissions required (HTTP 403)"
    else
        fail_test "AUTH-SESSION-007: Session Cleanup Job" "HTTP $HTTP_CODE"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    fi
}

# Test scheduler start endpoint
test_scheduler_start() {
    echo -e "\n${BLUE}Testing scheduler start endpoint${NC}"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/admin/scheduler/start" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        pass_test "Scheduler Start Endpoint" "Scheduler start command succeeded"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    else
        fail_test "Scheduler Start Endpoint" "HTTP $HTTP_CODE"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    fi
}

# Test scheduler stop endpoint
test_scheduler_stop() {
    echo -e "\n${BLUE}Testing scheduler stop endpoint${NC}"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/admin/scheduler/stop" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        pass_test "Scheduler Stop Endpoint" "Scheduler stop command succeeded"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    else
        fail_test "Scheduler Stop Endpoint" "HTTP $HTTP_CODE"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    fi
}

# Test scheduler cleanup-now endpoint
test_scheduler_cleanup() {
    echo -e "\n${BLUE}Testing scheduler cleanup-now endpoint${NC}"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/admin/scheduler/cleanup-now" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -w "\n%{http_code}")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | head -n -1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        pass_test "Scheduler Cleanup-Now Endpoint" "Manual cleanup command succeeded"
        echo -e "   ${BLUE}Response: $BODY${NC}"
    else
        fail_test "Scheduler Cleanup-Now Endpoint" "HTTP $HTTP_CODE"
        echo -e "   ${BLUE}Response: $BODY${NC}"
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
    echo -e "${BLUE}AUTH-SESSION-007 & Scheduler Admin Testing Suite${NC}"
    echo -e "${BLUE}============================================================${NC}"
    
    if ! setup_admin_user; then
        echo -e "${RED}Failed to authenticate as admin user${NC}"
        exit 1
    fi
    
    test_auth_session_007
    test_scheduler_start
    test_scheduler_stop
    test_scheduler_cleanup
    
    print_summary
}

main
