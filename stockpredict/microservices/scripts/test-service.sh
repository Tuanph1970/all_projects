#!/bin/bash
# =============================================================================
# Test Single Service Script
# =============================================================================
#
# Usage: ./scripts/test-service.sh <service-name>
#
# Examples:
#   ./scripts/test-service.sh auth
#   ./scripts/test-service.sh stock-data
#   ./scripts/test-service.sh portfolio
#
# =============================================================================

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <service-name>"
    echo ""
    echo "Available services:"
    echo "  auth        - Auth service tests"
    echo "  stock-data  - Stock data service tests"
    echo "  portfolio   - Portfolio service tests"
    echo "  prediction  - Prediction service tests"
    echo "  analysis    - Analysis service tests"
    echo "  cross       - Cross-service integration tests"
    exit 1
fi

SERVICE=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Map service name to test file
case $SERVICE in
    auth)
        TEST_FILE="tests/integration/test_auth_flow.py"
        ;;
    stock-data|stock|data)
        TEST_FILE="tests/integration/test_stock_data_flow.py"
        ;;
    portfolio)
        TEST_FILE="tests/integration/test_portfolio_operations.py"
        ;;
    prediction)
        TEST_FILE="tests/integration/test_prediction_pipeline.py"
        ;;
    analysis)
        TEST_FILE="tests/integration/test_analysis_workflow.py"
        ;;
    cross|cross-service)
        TEST_FILE="tests/integration/test_cross_service.py"
        ;;
    *)
        echo "Unknown service: $SERVICE"
        exit 1
        ;;
esac

if [ ! -f "$TEST_FILE" ]; then
    echo "Test file not found: $TEST_FILE"
    exit 1
fi

echo "=============================================="
echo "  Testing: $SERVICE"
echo "  File: $TEST_FILE"
echo "=============================================="
echo ""

pytest "$TEST_FILE" -v --tb=short

echo ""
echo "Done testing $SERVICE"
