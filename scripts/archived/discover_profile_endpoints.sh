#!/bin/bash

#############################################################################
# AUTH-PROFILE API Endpoint Discovery
# Check which profile endpoints exist and work
#############################################################################

API_URL="http://localhost:8003/api"
TEST_USER="profile_test_$(date +%s)"
TEST_EMAIL="profile_test_${TEST_USER}@test.com"
TEST_PASS="TestPassword123!"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}AUTH-PROFILE Endpoint Discovery${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"

# Create test user
echo -e "\n${YELLOW}Creating test user...${NC}"
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
echo -e "${GREEN}✅ Test user created${NC}"

# Test endpoints
echo -e "\n${YELLOW}Testing Profile Endpoints:${NC}"

# 1. GET /me (Get Profile)
echo -e "\n${BLUE}1. GET /api/auth/me${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✅ Works${NC}"
  echo "$BODY" | jq 'keys' 2>/dev/null | head -5
else
  echo -e "${RED}❌ Failed${NC}"
fi

# 2. PUT /me (Update Profile)
echo -e "\n${BLUE}2. PUT /api/auth/me${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"New Name"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "422" ]; then
  echo -e "${YELLOW}⚠️  Endpoint exists but may not be fully implemented${NC}"
else
  echo -e "${RED}❌ Not found (404) or error${NC}"
fi

# 3. PATCH /me (Partial Update)
echo -e "\n${BLUE}3. PATCH /api/auth/me${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"New Name"}')
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✅ Works${NC}"
else
  echo -e "${RED}❌ Not found (404)${NC}"
fi

# 4. POST /me/change-password
echo -e "\n${BLUE}4. POST /api/auth/change-password${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/auth/change-password" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"current_password\": \"$TEST_PASS\",
    \"new_password\": \"NewPassword456!\"
  }")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✅ Works${NC}"
else
  echo -e "${YELLOW}⚠️  Endpoint may not exist${NC}"
fi

# 5. GET /me/stats
echo -e "\n${BLUE}5. GET /api/auth/me/stats${NC}"
RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/me/stats" \
  -H "Authorization: Bearer $TOKEN")
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
echo "HTTP $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✅ Works${NC}"
else
  echo -e "${YELLOW}⚠️  Endpoint may not exist${NC}"
fi

echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}Discovery Complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════${NC}"
