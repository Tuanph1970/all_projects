#!/bin/bash
# =============================================================================
# Quick Test Script - Run a subset of fast tests for rapid feedback
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Running quick tests (skipping slow tests)..."
echo ""

# Run tests excluding slow-marked tests
pytest tests/integration \
    -v \
    --tb=short \
    -m "not slow" \
    --timeout=10 \
    -x \
    2>&1 | head -100

echo ""
echo "Quick test run complete!"
