#!/bin/bash

###############################################################################
# Mobile Automation Test - Test Runner Script
# Run E2E tests with various options
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

###############################################################################
# Configuration
###############################################################################

# Default values
BUILD_TYPE="release"
TEST_FILE=""
TEST_PATTERN=""
CLEANUP_ARTIFACTS=false
START_BACKEND=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--debug)
            BUILD_TYPE="debug"
            shift
            ;;
        -f|--file)
            TEST_FILE="$2"
            shift 2
            ;;
        -p|--pattern)
            TEST_PATTERN="$2"
            shift 2
            ;;
        -c|--cleanup)
            CLEANUP_ARTIFACTS=true
            shift
            ;;
        -b|--backend)
            START_BACKEND=true
            shift
            ;;
        -h|--help)
            SHOW_HELP=true
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            SHOW_HELP=true
            shift
            ;;
    esac
done

###############################################################################
# Help Menu
###############################################################################

show_help() {
    cat << EOF
Mobile Automation Test Runner

Usage: ./run-tests.sh [OPTIONS]

Options:
    -d, --debug             Run tests with debug build (slower, shows console logs)
    -f, --file <path>       Run specific test file (e.g., e2e/auth/login.test.js)
    -p, --pattern <name>    Run tests matching pattern (e.g., "should login")
    -c, --cleanup           Clean up artifacts before running tests
    -b, --backend           Start backend server before tests
    -h, --help              Show this help message

Examples:
    # Run all tests with release build (fast)
    ./run-tests.sh

    # Run all tests with debug build (slower, shows logs)
    ./run-tests.sh --debug

    # Run only login tests
    ./run-tests.sh --file e2e/auth/login.test.js

    # Run specific test by name
    ./run-tests.sh --pattern "should login successfully"

    # Run with backend server and cleanup
    ./run-tests.sh --backend --cleanup

    # Run login tests in debug mode
    ./run-tests.sh --debug --file e2e/auth/login.test.js

Test Files:
    e2e/auth/login.test.js          - Login flow tests
    e2e/auth/register.test.js       - Registration flow tests

Available Test Patterns:
    "should login successfully"
    "should register"
    "should show error"
    "should navigate"
    "should toggle password"

Configuration:
    Build: $BUILD_TYPE
    Test File: ${TEST_FILE:-"All tests"}
    Pattern: ${TEST_PATTERN:-"All patterns"}

EOF
}

if [ "$SHOW_HELP" = true ]; then
    show_help
    exit 0
fi

###############################################################################
# Pre-flight Checks
###############################################################################

preflight_checks() {
    print_header "Pre-flight Checks"

    local all_good=true

    # Check if we're in the right directory
    if [ ! -f "package.json" ] || [ ! -d "e2e" ]; then
        log_error "Must be run from mobile_automation_test directory"
        exit 1
    fi

    # Check Node.js
    if ! command -v node &> /dev/null; then
        log_error "Node.js not found"
        all_good=false
    else
        log_success "Node.js: $(node --version)"
    fi

    # Check npm packages
    if [ ! -d "node_modules" ]; then
        log_error "Dependencies not installed. Run: npm install"
        all_good=false
    else
        log_success "Dependencies installed"
    fi

    # Check Android SDK
    if [ -z "$ANDROID_HOME" ]; then
        log_warning "ANDROID_HOME not set"
    else
        log_success "ANDROID_HOME: $ANDROID_HOME"
    fi

    # Check emulator
    if ! command -v emulator &> /dev/null; then
        log_warning "Emulator command not found in PATH"
    else
        local emulator_count=$(emulator -list-avds 2>/dev/null | wc -l)
        if [ "$emulator_count" -eq 0 ]; then
            log_warning "No Android emulators found"
        else
            log_success "Android emulators found: $emulator_count"
        fi
    fi

    # Check APK
    local apk_path="../front_end/android/app/build/outputs/apk/$BUILD_TYPE/app-$BUILD_TYPE.apk"
    if [ -f "$apk_path" ]; then
        log_success "APK found: $BUILD_TYPE"
    else
        log_warning "APK not found. Will be built automatically..."
    fi

    if [ "$all_good" = false ]; then
        log_error "Pre-flight checks failed"
        exit 1
    fi

    log_success "Pre-flight checks passed"
}

###############################################################################
# Cleanup Artifacts
###############################################################################

cleanup_artifacts() {
    if [ "$CLEANUP_ARTIFACTS" = true ]; then
        print_header "Cleaning Up Artifacts"

        if [ -d "artifacts" ]; then
            log_info "Removing old test artifacts..."
            rm -rf artifacts/*
            log_success "Artifacts cleaned"
        else
            log_info "No artifacts to clean"
        fi
    fi
}

###############################################################################
# Start Backend Server
###############################################################################

start_backend_server() {
    if [ "$START_BACKEND" = true ]; then
        print_header "Starting Backend Server"

        # Check if backend is already running
        if curl -s http://localhost:8002/api/v1/health > /dev/null 2>&1; then
            log_success "Backend server is already running"
        else
            log_info "Starting backend server..."

            # Check if gunicorn is available
            if ! command -v gunicorn &> /dev/null; then
                log_error "gunicorn not found. Install with: pip install gunicorn"
                exit 1
            fi

            # Start backend in background
            cd ../back_end
            gunicorn app.main:app --workers 4 --bind 0.0.0.0:8002 > /tmp/backend.log 2>&1 &
            BACKEND_PID=$!
            cd ../mobile_automation_test

            # Wait for backend to start
            log_info "Waiting for backend to start..."
            for i in {1..30}; do
                if curl -s http://localhost:8002/api/v1/health > /dev/null 2>&1; then
                    log_success "Backend server started (PID: $BACKEND_PID)"
                    echo $BACKEND_PID > /tmp/backend.pid
                    break
                fi
                sleep 1
            done

            if ! curl -s http://localhost:8002/api/v1/health > /dev/null 2>&1; then
                log_error "Backend server failed to start"
                log_info "Check logs: tail -f /tmp/backend.log"
                exit 1
            fi
        fi
    fi
}

###############################################################################
# Build Application
###############################################################################

build_application() {
    print_header "Building Application ($BUILD_TYPE)"

    local apk_path="../front_end/android/app/build/outputs/apk/$BUILD_TYPE/app-$BUILD_TYPE.apk"

    # Check if APK already exists and is recent (less than 1 hour old)
    if [ -f "$apk_path" ]; then
        local apk_age=$(($(date +%s) - $(stat -c %Y "$apk_path" 2>/dev/null || stat -f %m "$apk_path" 2>/dev/null)))
        if [ "$apk_age" -lt 3600 ]; then
            log_info "Recent APK found ($(($apk_age / 60)) minutes old)"
            read -p "Skip rebuild? (Y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                log_success "Using existing APK"
                return
            fi
        fi
    fi

    log_info "Building $BUILD_TYPE APK..."
    log_info "This may take a few minutes..."

    cd ../front_end/android

    if [ "$BUILD_TYPE" = "debug" ]; then
        ./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug
    else
        ./gradlew assembleRelease assembleAndroidTest -DtestBuildType=release
    fi

    cd ../../mobile_automation_test

    if [ -f "$apk_path" ]; then
        log_success "Build completed successfully"
    else
        log_error "Build failed - APK not found"
        exit 1
    fi
}

###############################################################################
# Run Tests
###############################################################################

run_tests() {
    print_header "Running Tests"

    local config="android.emu.$BUILD_TYPE"
    local test_cmd="npx detox test --configuration $config"

    # Add test file if specified
    if [ -n "$TEST_FILE" ]; then
        test_cmd="$test_cmd $TEST_FILE"
        log_info "Test file: $TEST_FILE"
    else
        log_info "Running all tests"
    fi

    # Add test pattern if specified
    if [ -n "$TEST_PATTERN" ]; then
        test_cmd="$test_cmd --testNamePattern=\"$TEST_PATTERN\""
        log_info "Test pattern: $TEST_PATTERN"
    fi

    log_info "Build type: $BUILD_TYPE"
    log_info "Configuration: $config"
    echo ""
    log_info "Command: $test_cmd"
    echo ""

    # Run tests
    eval $test_cmd

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "All tests passed!"
    else
        log_error "Tests failed with exit code: $exit_code"
    fi

    return $exit_code
}

###############################################################################
# Cleanup on Exit
###############################################################################

cleanup_on_exit() {
    echo ""
    log_info "Cleaning up..."

    # Stop backend if we started it
    if [ -f /tmp/backend.pid ]; then
        local pid=$(cat /tmp/backend.pid)
        if ps -p $pid > /dev/null 2>&1; then
            log_info "Stopping backend server (PID: $pid)..."
            kill $pid 2>/dev/null || true
            rm -f /tmp/backend.pid
        fi
    fi
}

trap cleanup_on_exit EXIT

###############################################################################
# Generate Test Report
###############################################################################

generate_report() {
    print_header "Test Summary"

    # Check if artifacts directory exists
    if [ -d "artifacts" ]; then
        local screenshot_count=$(find artifacts -name "*.png" 2>/dev/null | wc -l)
        local log_count=$(find artifacts -name "*.log" 2>/dev/null | wc -l)

        log_info "Artifacts generated:"
        echo "  - Screenshots: $screenshot_count"
        echo "  - Logs: $log_count"
        echo "  - Location: artifacts/"
        echo ""

        # Show recent screenshots
        if [ $screenshot_count -gt 0 ]; then
            log_info "Recent screenshots:"
            find artifacts -name "*.png" -type f -printf "%T@ %p\n" 2>/dev/null | sort -rn | head -5 | cut -d' ' -f2- | sed 's/^/  - /'
        fi
    fi

    echo ""
    log_info "Test execution completed"
    echo ""
}

###############################################################################
# Main Execution
###############################################################################

main() {
    print_header "Mobile Automation Test Runner"

    log_info "Configuration:"
    echo "  - Build Type: $BUILD_TYPE"
    echo "  - Test File: ${TEST_FILE:-All tests}"
    echo "  - Pattern: ${TEST_PATTERN:-All patterns}"
    echo "  - Cleanup: $CLEANUP_ARTIFACTS"
    echo "  - Start Backend: $START_BACKEND"
    echo ""

    # Run setup steps
    preflight_checks
    cleanup_artifacts
    start_backend_server
    build_application

    # Run tests
    local test_result=0
    run_tests || test_result=$?

    # Generate report
    generate_report

    # Exit with test result
    if [ $test_result -eq 0 ]; then
        print_header "✅ SUCCESS"
        log_success "All tests passed!"
    else
        print_header "❌ FAILURE"
        log_error "Some tests failed"
        log_info "Check artifacts/ directory for screenshots and logs"
    fi

    exit $test_result
}

# Run main function
main "$@"
