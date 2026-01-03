#!/bin/bash

# Quick Maestro test runner
# Use this when emulator and servers are already running

set -e

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Change to maestro directory
cd "$(dirname "$0")/../maestro"

# Check Maestro is available
if ! command -v maestro &> /dev/null; then
    echo -e "${RED}ERROR: Maestro not found in PATH${NC}"
    exit 1
fi

# Check device is connected
if ! adb devices | grep -q "device$"; then
    echo -e "${RED}ERROR: No Android device/emulator connected${NC}"
    echo "Please start an emulator or connect a device"
    exit 1
fi

# Parse arguments
TEST_TARGET="${1:-tests}"

echo -e "${GREEN}Running Maestro Tests${NC}"
echo "Target: $TEST_TARGET"
echo "------------------------"

# Run tests based on target
case "$TEST_TARGET" in
    smoke)
        maestro test --format junit --output test-results.xml --tags smoke tests/
        ;;
    auth)
        maestro test --format junit --output test-results-auth.xml tests/auth/
        ;;
    product)
        maestro test --format junit --output test-results-product.xml tests/product/
        ;;
    cart)
        maestro test --format junit --output test-results-cart.xml tests/cart/
        ;;
    debug)
        # Run with debug output
        maestro test --debug tests/
        ;;
    single)
        # Run a single test file (pass as second argument)
        if [ -z "$2" ]; then
            echo "Please specify a test file"
            exit 1
        fi
        maestro test "$2"
        ;;
    *)
        # Run all tests or specific path
        maestro test --format junit --output test-results.xml "$TEST_TARGET"
        ;;
esac

echo -e "\n${GREEN}✓ Test run completed${NC}"