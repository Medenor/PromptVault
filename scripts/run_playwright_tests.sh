#!/bin/bash

# PromptVault AUTH-UI Playwright Test Runner
# Runs AUTH-UI tests with test account initialization

set -e

echo "=================================================="
echo "PromptVault AUTH-UI Playwright Tests"
echo "=================================================="
echo ""

# Configuration
BASE_URL="${BASE_URL:-http://127.0.0.1:8003}"
PYTHON_CMD="${PYTHON_CMD:-python3}"
NPX_CMD="${NPX_CMD:-npx}"

echo "Configuration:"
echo "  Base URL: $BASE_URL"
echo "  Python: $PYTHON_CMD"
echo "  NPX: $NPX_CMD"
echo ""

# Check if server is running
echo "Checking if server is running at $BASE_URL..."
if ! curl -s "$BASE_URL" > /dev/null; then
    echo "⚠️  Server not running at $BASE_URL"
    echo "Starting server in background..."
    PORT=8003 $PYTHON_CMD run_web.py &
    SERVER_PID=$!
    echo "Server started with PID: $SERVER_PID"
    sleep 3
else
    echo "✓ Server is running"
fi

echo ""
echo "Step 1: Initialize test accounts..."
echo "=================================================="

$PYTHON_CMD scripts/init_test_admin.py

echo ""
echo "Step 2: Install Playwright browsers (if needed)..."
echo "=================================================="

$NPX_CMD playwright install

echo ""
echo "Step 3: Run AUTH-UI tests..."
echo "=================================================="

# Run tests with options
PLAYWRIGHT_OPTS=""

# Run in headed mode if requested
if [ "$HEADED" = "1" ]; then
    PLAYWRIGHT_OPTS="--headed"
fi

# Run specific test if provided
if [ -n "$TEST_NAME" ]; then
    PLAYWRIGHT_OPTS="$PLAYWRIGHT_OPTS --grep '$TEST_NAME'"
fi

# Run in debug mode if requested
if [ "$DEBUG" = "1" ]; then
    PLAYWRIGHT_OPTS="$PLAYWRIGHT_OPTS --debug"
fi

# Default: run with UI mode for better visibility
if [ -z "$PLAYWRIGHT_OPTS" ]; then
    echo "Running tests with UI..."
    $NPX_CMD playwright test scripts/playwright_auth_ui_tests.ts --ui
else
    $NPX_CMD playwright test scripts/playwright_auth_ui_tests.ts $PLAYWRIGHT_OPTS
fi

TEST_EXIT_CODE=$?

echo ""
echo "=================================================="
echo "Test Results"
echo "=================================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
    echo ""
    echo "Reports:"
    echo "  HTML Report: open playwright-report/index.html"
else
    echo "✗ Some tests failed"
    echo ""
    echo "Reports:"
    echo "  HTML Report: open playwright-report/index.html"
    echo "  Videos: test-results/"
fi

echo ""

# Cleanup
if [ -n "$SERVER_PID" ]; then
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
fi

exit $TEST_EXIT_CODE
