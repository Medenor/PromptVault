#!/bin/bash

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# PromptVault Accessibility Test Runner
# Comprehensive test suite for WCAG 2.1 AA compliance verification

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "=================================================="
echo "PromptVault Full Accessibility Test Suite"
echo "WCAG 2.1 AA Compliance Verification"
echo "=================================================="
echo ""

# Configuration
BASE_URL="${ACCESSIBILITY_BASE_URL:-http://127.0.0.1:8003}"
PYTHON_CMD="${PYTHON_CMD:-python3}"
NPX_CMD="${NPX_CMD:-npx}"

echo "Configuration:"
echo "  Base URL: $BASE_URL"
echo "  Python: $PYTHON_CMD"
echo "  NPX: $NPX_CMD"
echo "  Project Root: $PROJECT_ROOT"
echo ""

# Step 1: Check/start server
echo "Step 1: Checking server..."
echo "=================================================="

if ! curl -s "$BASE_URL" > /dev/null 2>&1; then
    echo "Server not running at $BASE_URL, starting..."
    PORT=8003 UVICORN_RELOAD=false $PYTHON_CMD run_web.py > /tmp/server.log 2>&1 &
    SERVER_PID=$!
    echo "Server started with PID: $SERVER_PID"
    sleep 5
else
    echo "✓ Server is running at $BASE_URL"
    SERVER_PID=""
fi

echo ""

# Step 2: Initialize test accounts
echo "Step 2: Initializing test accounts..."
echo "=================================================="

if [ -f "scripts/init_test_admin.py" ]; then
    $PYTHON_CMD scripts/init_test_admin.py || echo "Note: Test account initialization failed (may already exist)"
else
    echo "Test account initialization script not found, skipping..."
fi

echo ""

# Step 3: Install Playwright browsers
echo "Step 3: Installing Playwright browsers..."
echo "=================================================="

$NPX_CMD playwright install

echo ""

# Step 4: Run accessibility tests
echo "Step 4: Running comprehensive accessibility tests..."
echo "=================================================="

# Create test results directory
mkdir -p test-results

# Run tests with all projects
export ACCESSIBILITY_BASE_URL="$BASE_URL"

# Run Playwright tests
echo "Running Playwright test suite (all 5 browsers)..."
$NPX_CMD playwright test \
  --reporter=html,json,junit,list \
  --output=test-results \
  2>&1 | tee /tmp/test_output.log

TEST_EXIT_CODE=$?

echo ""

# Step 5: Analyze results
echo "Step 5: Analyzing test results..."
echo "=================================================="

if [ -f "scripts/test_analysis.mjs" ]; then
    node scripts/test_analysis.mjs || true
fi

echo ""

# Step 6: Generate final report
echo "Step 6: Generating final compliance report..."
echo "=================================================="

if [ -f "test-results/results.json" ]; then
    echo "Test results captured to: test-results/results.json"
fi

echo ""
echo "=================================================="
echo "Test Execution Complete"
echo "=================================================="
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✓ All tests passed!"
else
    echo "⚠ Some tests failed (see details above)"
fi

echo ""
echo "Reports available:"
echo "  HTML: open playwright-report/index.html"
echo "  JSON: test-results/results.json"
echo "  JUnit: test-results/junit.xml"
echo ""

# Cleanup
if [ -n "$SERVER_PID" ]; then
    echo "Stopping server..."
    kill $SERVER_PID 2>/dev/null || true
    wait $SERVER_PID 2>/dev/null || true
fi

exit $TEST_EXIT_CODE
