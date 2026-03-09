#!/bin/bash

# Test suite runner for Mathematics Solver Mobile App
# Usage: ./scripts/run-test-suite.sh [smoke|auth|problem|solution|customer|regression]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
FLOWS_DIR="$PROJECT_DIR/maestro/flows"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SUITE="$1"

if [ -z "$SUITE" ]; then
    echo -e "${RED}Error: No test suite specified${NC}"
    echo "Usage: $0 [smoke|auth|problem|solution|customer|regression]"
    exit 1
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Mathematics Solver Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Suite: ${YELLOW}$SUITE${NC}"
echo ""

# Check Maestro
if ! command -v maestro &> /dev/null; then
    echo -e "${RED}Maestro not found. Run: npm run maestro:setup${NC}"
    exit 1
fi

# Define test flows for each suite
declare -A SUITES
SUITES=(
    ["smoke"]="fast-login-flow.yaml"
    ["auth"]="login-flow.yaml register-flow.yaml"
    ["problem"]="capture-and-solve-flow.yaml"
    ["solution"]="capture-and-solve-flow.yaml"
    ["customer"]="login-flow.yaml capture-and-solve-flow.yaml"
    ["regression"]="login-flow.yaml fast-login-flow.yaml register-flow.yaml capture-and-solve-flow.yaml"
)

# Get flows for suite
FLOWS="${SUITES[$SUITE]}"

if [ -z "$FLOWS" ]; then
    echo -e "${RED}Unknown suite: $SUITE${NC}"
    echo "Available: smoke, auth, problem, solution, customer, regression"
    exit 1
fi

# Run tests
FAILED=0
PASSED=0

for FLOW in $FLOWS; do
    FLOW_PATH="$FLOWS_DIR/$FLOW"
    
    if [ ! -f "$FLOW_PATH" ]; then
        echo -e "${YELLOW}Skip: $FLOW (not found)${NC}"
        continue
    fi
    
    echo -e "${YELLOW}Running: $FLOW${NC}"
    
    if maestro test "$FLOW_PATH"; then
        echo -e "${GREEN}✓ Passed: $FLOW${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ Failed: $FLOW${NC}"
        FAILED=$((FAILED + 1))
    fi
    
    echo ""
done

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
