# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#!/bin/bash
# Start the PromptVault server and run manual testing

set -e

WORKSPACE="/Users/raphael/Programmation/PromptVault"
cd "$WORKSPACE"

echo "🚀 Starting PromptVault API server..."
python run_web.py &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to be ready..."
sleep 3

# Check if server is running
if ! kill -0 $SERVER_PID 2>/dev/null; then
    echo "❌ Server failed to start"
    exit 1
fi

echo "✅ Server started (PID: $SERVER_PID)"

# Run tests
echo ""
echo "🧪 Running manual AUTH-SESSION tests..."
python -m pytest tests/manual_testing_session.py -v --tb=short

# Cleanup
echo ""
echo "🛑 Stopping server..."
kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true

echo "✅ Done!"
