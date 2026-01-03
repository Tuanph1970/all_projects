#!/bin/bash

# Test Suite Runner for Maestro
# Runs predefined test suites with proper setup and reporting

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
MAESTRO_DIR="$PROJECT_DIR/maestro"
RESULTS_DIR="$MAESTRO_DIR/results"

# Add Maestro to PATH
export PATH="$PATH:$HOME/.maestro/bin"

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

show_help() {
    echo "Maestro Test Suite Runner"
    echo ""
    echo "Usage: $0 [suite] [options]"
    echo ""
    echo "Test Suites:"
    echo "  smoke      - Critical functionality tests (5-10 min)"
    echo "  auth       - Authentication tests (15-20 min)"
    echo "  seller     - Seller feature tests (20-25 min)"
    echo "  customer   - Customer feature tests (15-20 min)"
    echo "  regression - Full regression suite (45-60 min)"
    echo "  quick      - Quick essential tests (5-10 min)"
    echo ""
    echo "Options:"
    echo "  --device-check    - Check device/emulator before running"
    echo "  --no-setup       - Skip backend/metro setup"
    echo "  --junit          - Generate JUnit XML reports"
    echo "  --video          - Record video for failed tests"
    echo "  --debug          - Run in debug mode"
    echo "  --help, -h       - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 smoke                    # Run smoke tests"
    echo "  $0 auth --junit            # Run auth tests with JUnit output"
    echo "  $0 regression --video      # Run regression with video recording"
    echo ""
}

check_requirements() {
    print_header "Checking Requirements"
    
    if ! command -v maestro &> /dev/null; then
        print_error "Maestro not found. Please install first."
        exit 1
    fi
    
    if ! command -v adb &> /dev/null; then
        print_warning "ADB not found. Make sure Android SDK is installed."
    fi
    
    # Check Java version for Maestro
    if command -v java &> /dev/null; then
        java_version=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)
        if [ "$java_version" -lt 17 ]; then
            print_error "Java 17+ required. Current: $java_version"
            exit 1
        fi
    else
        print_error "Java not found"
        exit 1
    fi
    
    print_success "Requirements check passed"
}

check_device() {
    print_header "Checking Device/Emulator"
    
    # Check if device is connected
    if ! adb devices 2>/dev/null | grep -q "device$"; then
        print_error "No Android device or emulator connected"
        echo "Please start an emulator or connect a device:"
        echo "  emulator -avd <AVD_NAME>"
        echo "  adb devices"
        exit 1
    fi
    
    device_name=$(adb devices | grep "device$" | head -1 | cut -f1)
    print_success "Device connected: $device_name"
    
    # Check if device is ready
    boot_complete=$(adb shell getprop sys.boot_completed 2>/dev/null || echo "0")
    if [ "$boot_complete" != "1" ]; then
        print_warning "Device may not be fully booted"
    fi
}

setup_services() {
    if [ "$SKIP_SETUP" = "true" ]; then
        print_warning "Skipping service setup"
        return
    fi
    
    print_header "Setting up Services"
    
    # Check if backend is running
    if curl -s http://localhost:8002/health > /dev/null 2>&1; then
        print_success "Backend is already running"
    else
        print_warning "Backend may not be running on port 8002"
        print_warning "Make sure your Docker containers are up"
    fi
    
    # Check if Metro is running (if needed)
    if lsof -i:8081 > /dev/null 2>&1; then
        print_success "Metro bundler is running"
    else
        print_warning "Metro bundler may not be running"
    fi
}

setup_results_dir() {
    mkdir -p "$RESULTS_DIR"
    
    # Create timestamp for this run
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    RUN_DIR="$RESULTS_DIR/run_$TIMESTAMP"
    mkdir -p "$RUN_DIR"
    
    echo "$RUN_DIR"
}

run_test_suite() {
    local suite=$1
    local run_dir=$2
    
    print_header "Running $suite Test Suite"
    
    cd "$MAESTRO_DIR"
    
    # Build maestro command
    local cmd="maestro test"
    
    if [ "$JUNIT_OUTPUT" = "true" ]; then
        cmd="$cmd --format junit --output $run_dir/results.xml"
    fi
    
    if [ "$DEBUG_MODE" = "true" ]; then
        cmd="$cmd --debug"
    fi
    
    # Run based on suite type
    case "$suite" in
        smoke)
            $cmd --tags smoke tests/ | tee "$run_dir/smoke.log"
            ;;
        auth)
            $cmd tests/auth/ | tee "$run_dir/auth.log"
            ;;
        seller)
            $cmd tests/seller/ | tee "$run_dir/seller.log"
            ;;
        customer)
            $cmd tests/product/ tests/cart/ | tee "$run_dir/customer.log"
            ;;
        regression)
            $cmd tests/ | tee "$run_dir/regression.log"
            ;;
        quick)
            $cmd tests/auth/login.yaml tests/seller/dashboard.yaml | tee "$run_dir/quick.log"
            ;;
        *)
            print_error "Unknown test suite: $suite"
            exit 1
            ;;
    esac
}

generate_report() {
    local suite=$1
    local run_dir=$2
    local exit_code=$3
    
    print_header "Test Results Summary"
    
    # Count screenshots
    screenshot_count=$(find "$MAESTRO_DIR" -name "*.png" -newer "$run_dir" 2>/dev/null | wc -l)
    
    if [ "$exit_code" -eq 0 ]; then
        print_success "$suite tests completed successfully"
    else
        print_error "$suite tests failed (exit code: $exit_code)"
    fi
    
    echo "Results saved to: $run_dir"
    
    if [ "$screenshot_count" -gt 0 ]; then
        echo "Screenshots captured: $screenshot_count"
        echo "Screenshots location: $MAESTRO_DIR"
    fi
    
    if [ "$JUNIT_OUTPUT" = "true" ] && [ -f "$run_dir/results.xml" ]; then
        echo "JUnit XML report: $run_dir/results.xml"
    fi
}

main() {
    # Parse arguments
    SUITE=""
    DEVICE_CHECK=false
    SKIP_SETUP=false
    JUNIT_OUTPUT=false
    VIDEO_RECORDING=false
    DEBUG_MODE=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            smoke|auth|seller|customer|regression|quick)
                SUITE=$1
                shift
                ;;
            --device-check)
                DEVICE_CHECK=true
                shift
                ;;
            --no-setup)
                SKIP_SETUP=true
                shift
                ;;
            --junit)
                JUNIT_OUTPUT=true
                shift
                ;;
            --video)
                VIDEO_RECORDING=true
                shift
                ;;
            --debug)
                DEBUG_MODE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Validate suite selection
    if [ -z "$SUITE" ]; then
        print_error "Please specify a test suite"
        show_help
        exit 1
    fi
    
    # Main execution
    echo -e "${BLUE}Ceramic Mobile App - Maestro Test Suite Runner${NC}"
    echo "=============================================="
    echo "Suite: $SUITE"
    echo "Time: $(date)"
    echo ""
    
    check_requirements
    
    if [ "$DEVICE_CHECK" = "true" ]; then
        check_device
    fi
    
    setup_services
    
    RUN_DIR=$(setup_results_dir)
    
    # Run tests and capture exit code
    set +e
    run_test_suite "$SUITE" "$RUN_DIR"
    TEST_EXIT_CODE=$?
    set -e
    
    generate_report "$SUITE" "$RUN_DIR" "$TEST_EXIT_CODE"
    
    exit $TEST_EXIT_CODE
}

# Run main function
main "$@"