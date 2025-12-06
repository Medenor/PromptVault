#!/bin/bash

# Test rate limiting on authentication endpoints

echo "=========================================="
echo "Testing Rate Limiting on Auth Endpoints"
echo "=========================================="
echo ""

# Test 1: Login rate limiting (5/15min = 5 attempts per 15 minutes)
echo "Test 1: Login Rate Limiting (limit: 5/15min)"
echo "Testing with invalid credentials..."
for i in {1..7}; do
    echo -n "Attempt $i: "
    response=$(curl -s -X POST http://127.0.0.1:8003/api/auth/login \
        -H "Content-Type: application/json" \
        -d '{"username_or_email":"testuser","password":"wrongpassword"}' \
        -w "\nSTATUS:%{http_code}")
    
    status=$(echo "$response" | grep "STATUS:" | cut -d: -f2)
    if [ "$status" == "429" ]; then
        echo "Rate limited (429)"
    elif [ "$status" == "401" ]; then
        echo "Invalid credentials (401)"
    else
        echo "Status: $status"
    fi
done

echo ""
echo "Test 2: Register Rate Limiting (limit: 3/1hour)"
echo "Testing with invalid data..."
for i in {1..5}; do
    echo -n "Attempt $i: "
    response=$(curl -s -X POST http://127.0.0.1:8003/api/auth/register \
        -H "Content-Type: application/json" \
        -d '{
            "username":"testuser'$i'",
            "email":"test'$i'@example.com",
            "password":"Password123!@#"
        }' \
        -w "\nSTATUS:%{http_code}")
    
    status=$(echo "$response" | grep "STATUS:" | cut -d: -f2)
    if [ "$status" == "429" ]; then
        echo "Rate limited (429)"
    elif [ "$status" == "400" ]; then
        echo "Bad request (400)"
    elif [ "$status" == "409" ]; then
        echo "Conflict (409)"
    elif [ "$status" == "201" ]; then
        echo "Created (201)"
    else
        echo "Status: $status"
    fi
done

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
