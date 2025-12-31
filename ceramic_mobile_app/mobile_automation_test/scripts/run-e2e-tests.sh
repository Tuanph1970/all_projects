#!/bin/bash

#===============================================================================
# E2E Test Runner Script
# Run this after initial setup is complete
#===============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
FRONTEND_DIR="$PROJECT_ROOT/front_end"
TEST_DIR="$PROJECT_ROOT/mobile_automation_test"
EMULATOR_NAME="${EMULATOR_NAME:-Pixel_4_API_35}"
API_PORT="${API_PORT:-8002}"
METRO_PORT="${METRO_PORT:-8081}"

# Test file to run (optional argument)
TEST_FILE="${1:-}"

print_step() {
    echo -e "\n${BLUE}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

#===============================================================================
# Check Prerequisites
#===============================================================================
check_prerequisites() {
    print_step "Checking prerequisites..."

    # Check if APKs exist
    DEBUG_APK="$FRONTEND_DIR/android/app/build/outputs/apk/debug/app-debug.apk"
    TEST_APK="$FRONTEND_DIR/android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk"

    if [ ! -f "$DEBUG_APK" ] || [ ! -f "$TEST_APK" ]; then
        print_warning "APKs not found. Building..."
        build_apks
    else
        print_success "APKs found"
    fi

    # Check node_modules
    if [ ! -d "$TEST_DIR/node_modules" ]; then
        print_warning "Test dependencies not installed. Installing..."
        cd "$TEST_DIR" && npm install
    fi

    if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
        print_warning "Frontend dependencies not installed. Installing..."
        cd "$FRONTEND_DIR" && npm install
    fi
}

#===============================================================================
# Build APKs
#===============================================================================
build_apks() {
    print_step "Building APKs..."

    cd "$FRONTEND_DIR"

    export JAVA_HOME="${JAVA_HOME:-/usr/lib/jvm/java-17-openjdk-amd64}"

    ./android/gradlew -p android assembleDebug assembleAndroidTest -DtestBuildType=debug

    print_success "APKs built successfully"
}

#===============================================================================
# Start Emulator
#===============================================================================
start_emulator() {
    print_step "Starting emulator..."

    # Check if emulator is already running
    if adb devices 2>/dev/null | grep -q "emulator"; then
        print_success "Emulator already running"
        return 0
    fi

    # Check if emulator exists
    if ! emulator -list-avds 2>/dev/null | grep -q "$EMULATOR_NAME"; then
        print_error "Emulator '$EMULATOR_NAME' not found!"
        echo "Available emulators:"
        emulator -list-avds
        exit 1
    fi

    # Start emulator in background
    echo "Starting $EMULATOR_NAME..."
    emulator -avd "$EMULATOR_NAME" -no-snapshot-load -gpu swiftshader_indirect &>/dev/null &
    EMULATOR_PID=$!

    # Wait for emulator to boot
    echo "Waiting for emulator to boot (this may take a few minutes)..."

    local max_wait=120
    local waited=0

    while [ $waited -lt $max_wait ]; do
        if adb shell getprop sys.boot_completed 2>/dev/null | grep -q "1"; then
            print_success "Emulator booted successfully"
            return 0
        fi
        sleep 5
        waited=$((waited + 5))
        echo "  Still waiting... ($waited/$max_wait seconds)"
    done

    print_error "Emulator failed to boot within $max_wait seconds"
    exit 1
}

#===============================================================================
# Setup ADB Port Forwarding
#===============================================================================
setup_port_forwarding() {
    print_step "Setting up port forwarding..."

    # Wait for device to be ready
    adb wait-for-device

    # Set up reverse port forwarding
    adb reverse tcp:$METRO_PORT tcp:$METRO_PORT 2>/dev/null || true
    adb reverse tcp:$API_PORT tcp:$API_PORT 2>/dev/null || true

    print_success "Port forwarding configured"
}

#===============================================================================
# Start Metro Bundler
#===============================================================================
start_metro() {
    print_step "Starting Metro bundler..."

    # Check if Metro is already running
    if lsof -i:$METRO_PORT >/dev/null 2>&1; then
        print_success "Metro bundler already running on port $METRO_PORT"
        return 0
    fi

    cd "$FRONTEND_DIR"

    # Start Metro in background
    npx react-native start --port $METRO_PORT &>/dev/null &
    METRO_PID=$!

    # Wait for Metro to start
    echo "Waiting for Metro to start..."
    sleep 10

    if lsof -i:$METRO_PORT >/dev/null 2>&1; then
        print_success "Metro bundler started"
    else
        print_warning "Metro bundler may not have started properly"
    fi
}

#===============================================================================
# Run Tests
#===============================================================================
run_tests() {
    print_step "Running E2E tests..."

    cd "$TEST_DIR"

    if [ -n "$TEST_FILE" ]; then
        echo "Running specific test: $TEST_FILE"
        npx detox test --configuration android.emu.debug "$TEST_FILE"
    else
        echo "Running all tests..."
        npx detox test --configuration android.emu.debug
    fi
}

#===============================================================================
# Cleanup
#===============================================================================
cleanup() {
    print_step "Cleaning up..."

    # Kill Metro if we started it
    if [ -n "${METRO_PID:-}" ]; then
        kill $METRO_PID 2>/dev/null || true
    fi
}

trap cleanup EXIT

#===============================================================================
# Main
#===============================================================================
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║           Ceramic Mobile App - E2E Test Runner                ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    check_prerequisites
    start_emulator
    setup_port_forwarding
    start_metro
    run_tests

    echo -e "\n${GREEN}Tests completed!${NC}"
}

# Show usage
usage() {
    echo "Usage: $0 [test-file]"
    echo ""
    echo "Examples:"
    echo "  $0                              # Run all tests"
    echo "  $0 e2e/auth/login.test.js      # Run specific test file"
    echo ""
    echo "Environment variables:"
    echo "  EMULATOR_NAME    Emulator AVD name (default: Pixel_4_API_35)"
    echo "  API_PORT         API server port (default: 8002)"
    echo "  METRO_PORT       Metro bundler port (default: 8081)"
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    usage
    exit 0
fi

main "$@"
