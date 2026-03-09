#!/bin/bash

# Wait for Metro bundler to be ready
# Usage: ./scripts/wait-for-metro.sh [host] [port] [timeout]

HOST="${1:-localhost}"
PORT="${2:-8081}"
TIMEOUT="${3:-60}"

echo "Waiting for Metro bundler at $HOST:$PORT (timeout: ${TIMEOUT}s)..."

SECONDS=0
while [ $SECONDS -lt $TIMEOUT ]; do
    if curl -s "http://$HOST:$PORT/status" > /dev/null 2>&1; then
        echo "✓ Metro bundler is ready!"
        exit 0
    fi
    sleep 2
done

echo "✗ Timeout waiting for Metro bundler"
exit 1
