#!/bin/bash

# Script to hard delete test users
# Permanently removes all users except 'medenor' and 'system_admin'

BASE_URL="http://127.0.0.1:8003"
ADMIN_USERNAME="admin_ui_test"
ADMIN_PASSWORD="SecureAdmin@123456"

echo "[INFO] Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"username_or_email\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" | jq -r '.access_token')

if [ -z "$ADMIN_TOKEN" ] || [ "$ADMIN_TOKEN" = "null" ]; then
  echo "[ERROR] Failed to obtain admin token"
  exit 1
fi

echo "[INFO] Fetching users list..."
USERS=$(curl -s -X GET "$BASE_URL/api/admin/users?limit=1000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json')

echo "[INFO] Filtering users to hard delete (excluding medenor and system_admin)..."
USER_IDS=$(echo "$USERS" | jq -r '.users[] | select(.username != "medenor" and .username != "system_admin") | "\(.id):\(.username)"')

COUNT=0
while IFS=':' read -r user_id username; do
  if [ -n "$user_id" ]; then
    echo "[HARD DELETE] Removing user: $username ($user_id)"
    curl -s -X DELETE "$BASE_URL/api/admin/users/$user_id?hard_delete=true" \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H 'Content-Type: application/json' > /dev/null
    COUNT=$((COUNT + 1))
  fi
done <<< "$USER_IDS"

echo ""
echo "✅ $COUNT users permanently deleted"
echo ""
echo "[INFO] Remaining users:"
curl -s -X GET "$BASE_URL/api/admin/users?limit=1000" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' | jq '.users[] | {username, role, is_active}' -c
