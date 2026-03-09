#!/bin/bash

# Maestro test runner script for Mathematics Solver Mobile App
# Usage: ./scripts/run-maestro-tests.sh [all|login|register|problem|solution]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MAESTRO_DIR="$PROJECT_DIR/maestro"
FLOWS_DIR="$MAESTRO_DIR/flows"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default test suite
TEST_SUITE="${1:-all}"

echo "========================================"
echo "Mathematics Solver - Maestro Test Runner"
echo "========================================"
echo "Test Suite: $TEST_SUITE"
echo "Flows Directory: $FLOWS_DIR"
echo "========================================"
echo ""

# Check if Maestro is installed
if ! command -v maestro &> /dev/null; then
    echo -e "${RED}Error: Maestro is not installed${NC}"
    echo "Please run: npm run maestro:setup"
    exit 1
fi

# Check if Android device/emulator is available
if ! command -v adb &> /dev/null; then
    echo -e "${YELLOW}Warning: ADB not found. Tests may fail if no device is connected.${NC}"
else
    DEVICE_COUNT=$(adb devices | grep -v "List" | wc -l)
    if [ "$DEVICE_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}Warning: No Android devices/emulators detected.${NC}"
        echo "Please start an emulator or connect a device."
    else
        echo -e "${GREEN}Found $DEVICE_COUNT Android device(s)/emulator(s)${NC}"
    fi
fi

echo ""

# Function to run a single flow
run_flow() {
    local flow_file="$1"
    local flow_name=$(basename "$flow_file" .yaml)
    
    echo -e "${YELLOW}Running: $flow_name${NC}"
    
    if maestro test "$flow_file"; then
        echo -e "${GREEN}✓ $flow_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $flow_name failed${NC}"
        return 1
    fi
}

# Run tests based on suite
FAILED=0

case "$TEST_SUITE" in
    all)
        echo "Running all test flows..."
        for flow in "$FLOWS_DIR"/*.yaml; do
            if [ -f "$flow" ]; then
                run_flow "$flow" || FAILED=$((FAILED + 1))
            fi
        done
        ;;
    
    login)
        echo "Running login tests..."
        run_flow "$FLOWS_DIR/login-flow.yaml" || FAILED=$((FAILED + 1))
        run_flow "$FLOWS_DIR/fast-login-flow.yaml" || FAILED=$((FAILED + 1))
        ;;
    
    register)
        echo "Running registration tests..."
        run_flow "$FLOWS_DIR/register-flow.yaml" || FAILED=$((FAILED + 1))
        ;;
    
    problem)
        echo "Running problem solving tests..."
        run_flow "$FLOWS_DIR/capture-and-solve-flow.yaml" || FAILED=$((FAILED + 1))
        ;;
    
    solution)
        echo "Running solution tests..."
        run_flow "$FLOWS_DIR/capture-and-solve-flow.yaml" || FAILED=$((FAILED + 1))
        ;;
    
    quick)
        echo "Running quick smoke tests..."
        run_flow "$FLOWS_DIR/fast-login-flow.yaml" || FAILED=$((FAILED + 1))
        ;;
    
    regression)
        echo "Running regression tests..."
        for flow in "$FLOWS_DIR"/*.yaml; do
            if [ -f "$flow" ]; then
                run_flow "$flow" || FAILED=$((FAILED + 1))
            fi
        done
        ;;
    
    debug)
        echo "Running in debug mode..."
        export MAESTRO_VERBOSE=true
        for flow in "$FLOWS_DIR"/*.yaml; do
            if [ -f "$flow" ]; then
                maestro test "$flow" --debug
            fi
        done
        ;;
    
    *)
        echo -e "${RED}Unknown test suite: $TEST_SUITE${NC}"
        echo "Available suites: all, login, register, problem, solution, quick, regression, debug"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"

if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED test(s) failed${NC}"
    exit 1
fi
