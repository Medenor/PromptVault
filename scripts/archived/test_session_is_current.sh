#!/bin/bash

#############################################################################
# AUTH-SESSION-008: Current Session Indicator - Isolated Test
# Tests that exactly one session is marked as is_current (current token's session)
# This test creates 3 sessions and verifies is_current field accuracy
#############################################################################

set -e

API_URL="http://localhost:8003/api"
TEST_USER="test_iscurrent_$(date +%s)"
TEST_PASS="TestPass@123"
TEST_EMAIL="test_iscurrent_${TEST_USER}@test.com"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}AUTH-SESSION-008: Current Session Indicator Test${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

# Step 1: Create test user
echo -e "\n${YELLOW}Step 1: Creating test user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"username\": \"$TEST_USER\",
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASS\",
    \"confirm_password\": \"$TEST_PASS\"
  }")

echo "Register response: $REGISTER_RESPONSE" | head -c 100
echo ""

# Step 2: Create Session 1 (initial login)
echo -e "\n${YELLOW}Step 2: Creating Session 1...${NC}"
SESSION1_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username_or_email\": \"$TEST_USER\",
    \"password\": \"$TEST_PASS\"
  }")

SESSION1_TOKEN=$(echo "$SESSION1_RESPONSE" | jq -r '.access_token')
if [ -z "$SESSION1_TOKEN" ] || [ "$SESSION1_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to get token for Session 1${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 1 token: ${SESSION1_TOKEN:0:20}...${NC}"

# Step 3: Create Session 2 (login again, same device)
echo -e "\n${YELLOW}Step 3: Creating Session 2...${NC}"
SESSION2_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username_or_email\": \"$TEST_USER\",
    \"password\": \"$TEST_PASS\"
  }")

SESSION2_TOKEN=$(echo "$SESSION2_RESPONSE" | jq -r '.access_token')
if [ -z "$SESSION2_TOKEN" ] || [ "$SESSION2_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to get token for Session 2${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 2 token: ${SESSION2_TOKEN:0:20}...${NC}"

# Step 4: Create Session 3 (login again)
echo -e "\n${YELLOW}Step 4: Creating Session 3...${NC}"
SESSION3_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"username_or_email\": \"$TEST_USER\",
    \"password\": \"$TEST_PASS\"
  }")

SESSION3_TOKEN=$(echo "$SESSION3_RESPONSE" | jq -r '.access_token')
if [ -z "$SESSION3_TOKEN" ] || [ "$SESSION3_TOKEN" = "null" ]; then
  echo -e "${RED}❌ Failed to get token for Session 3${NC}"
  exit 1
fi
echo -e "${GREEN}✅ Session 3 token: ${SESSION3_TOKEN:0:20}...${NC}"

# Step 5: Get sessions using Session 1 token
echo -e "\n${YELLOW}Step 5: Getting sessions with Session 1 token...${NC}"
SESSIONS_1=$(curl -s -X GET "$API_URL/auth/sessions" \
  -H "Authorization: Bearer $SESSION1_TOKEN")

echo "Sessions (using token 1):"
echo "$SESSIONS_1" | jq '.' | head -30

# Count is_current flags for Session 1 query
CURRENT_COUNT_1=$(echo "$SESSIONS_1" | jq '[.sessions[] | select(.is_current == true)] | length')
echo -e "Current count (from Session 1): $CURRENT_COUNT_1"

if [ "$CURRENT_COUNT_1" -ne 1 ]; then
  echo -e "${RED}❌ FAIL: Expected exactly 1 current session when querying with Session 1 token${NC}"
else
  echo -e "${GREEN}✅ PASS: Exactly 1 session marked as current for Session 1${NC}"
fi

# Verify which session is marked as current
SESSION1_IS_CURRENT=$(echo "$SESSIONS_1" | jq '.sessions[0].is_current')
echo "Session 1 is_current: $SESSION1_IS_CURRENT"

# Step 6: Get sessions using Session 2 token
echo -e "\n${YELLOW}Step 6: Getting sessions with Session 2 token...${NC}"
SESSIONS_2=$(curl -s -X GET "$API_URL/auth/sessions" \
  -H "Authorization: Bearer $SESSION2_TOKEN")

echo "Sessions (using token 2):"
echo "$SESSIONS_2" | jq '.' | head -30

# Count is_current flags for Session 2 query
CURRENT_COUNT_2=$(echo "$SESSIONS_2" | jq '[.sessions[] | select(.is_current == true)] | length')
echo -e "Current count (from Session 2): $CURRENT_COUNT_2"

if [ "$CURRENT_COUNT_2" -ne 1 ]; then
  echo -e "${RED}❌ FAIL: Expected exactly 1 current session when querying with Session 2 token${NC}"
else
  echo -e "${GREEN}✅ PASS: Exactly 1 session marked as current for Session 2${NC}"
fi

# Step 7: Get sessions using Session 3 token
echo -e "\n${YELLOW}Step 7: Getting sessions with Session 3 token...${NC}"
SESSIONS_3=$(curl -s -X GET "$API_URL/auth/sessions" \
  -H "Authorization: Bearer $SESSION3_TOKEN")

echo "Sessions (using token 3):"
echo "$SESSIONS_3" | jq '.' | head -30

# Count is_current flags for Session 3 query
CURRENT_COUNT_3=$(echo "$SESSIONS_3" | jq '[.sessions[] | select(.is_current == true)] | length')
echo -e "Current count (from Session 3): $CURRENT_COUNT_3"

if [ "$CURRENT_COUNT_3" -ne 1 ]; then
  echo -e "${RED}❌ FAIL: Expected exactly 1 current session when querying with Session 3 token${NC}"
else
  echo -e "${GREEN}✅ PASS: Exactly 1 session marked as current for Session 3${NC}"
fi

# Step 8: Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"

PASS_COUNT=0
FAIL_COUNT=0

if [ "$CURRENT_COUNT_1" -eq 1 ]; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

if [ "$CURRENT_COUNT_2" -eq 1 ]; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

if [ "$CURRENT_COUNT_3" -eq 1 ]; then
  PASS_COUNT=$((PASS_COUNT + 1))
else
  FAIL_COUNT=$((FAIL_COUNT + 1))
fi

echo -e "Passed: ${GREEN}$PASS_COUNT/3${NC}"
echo -e "Failed: ${RED}$FAIL_COUNT/3${NC}"

if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "\n${GREEN}✅ AUTH-SESSION-008: PASS${NC}"
  exit 0
else
  echo -e "\n${RED}❌ AUTH-SESSION-008: FAIL${NC}"
  exit 1
fi
