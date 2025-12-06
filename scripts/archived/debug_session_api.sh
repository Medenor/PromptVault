#!/bin/bash

# Diagnostic script to debug session API responses
# Shows detailed response structure for debugging

BASE_URL="http://localhost:8003"
TEST_USER_EMAIL="session_test_$(date +%s)@example.com"
TEST_USER_USERNAME="user_$(date +%s%N | cut -b1-8)"
TEST_USER_PASSWORD="TestPassword123!"

echo "=================================="
echo "Session API Diagnostic Script"
echo "=================================="

# Register user
echo -e "\n1️⃣  Registering user..."
REG_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"username\": \"$TEST_USER_USERNAME\",
        \"email\": \"$TEST_USER_EMAIL\",
        \"password\": \"$TEST_USER_PASSWORD\",
        \"confirm_password\": \"$TEST_USER_PASSWORD\"
    }")

echo "Registration response:"
echo "$REG_RESPONSE" | python -m json.tool

# Extract token
AUTH_TOKEN=$(echo "$REG_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo -e "\n✅ Got token: ${AUTH_TOKEN:0:20}..."

# Get sessions
echo -e "\n2️⃣  Getting sessions..."
SESSIONS=$(curl -s -X GET "$BASE_URL/api/auth/sessions" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: application/json")

echo "Sessions response:"
echo "$SESSIONS" | python -m json.tool

# Check what fields are present
echo -e "\n3️⃣  Field Analysis:"
echo "Checking for required fields in session..."
echo "$SESSIONS" | python -m json.tool | grep -E '"(id|user_id|created_at|last_activity_at|expires_at|user_agent|ip_address|is_current)"'
