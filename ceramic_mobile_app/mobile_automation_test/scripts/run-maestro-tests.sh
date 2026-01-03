#!/bin/bash

# Maestro test runner script
# This script manages Android emulator and runs Maestro tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
EMULATOR_NAME="${EMULATOR_NAME:-Pixel_4_API_30}"
MAESTRO_PATH="$HOME/.maestro/bin"
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
MAESTRO_DIR="$PROJECT_DIR/maestro"
BACKEND_DIR="$PROJECT_DIR/../backend"
FRONTEND_DIR="$PROJECT_DIR/../front_end"

# Add Maestro to PATH
export PATH="$PATH:$MAESTRO_PATH"

# Functions
print_header() {
    echo -e "\n${GREEN}=== $1 ===${NC}\n"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

check_requirements() {
    print_header "Checking Requirements"
    
    # Check Maestro
    if ! command -v maestro &> /dev/null; then
        print_error "Maestro not found. Please run: ./scripts/setup-maestro.sh"
        exit 1
    fi
    
    # Check Java version
    java_version=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | cut -d'.' -f1)
    if [ "$java_version" -lt 17 ]; then
        print_error "Java 17 or higher required. Current version: $java_version"
        print_warning "Please install Java 17: sudo apt install openjdk-17-jdk"
        exit 1
    fi
    
    # Check ADB
    if ! command -v adb &> /dev/null; then
        print_error "ADB not found. Please install Android SDK and add to PATH"
        exit 1
    fi
    
    # Check emulator
    if ! command -v emulator &> /dev/null; then
        print_warning "Android emulator command not found"
        echo "Make sure ANDROID_HOME is set and emulator is in PATH"
    fi
    
    echo "✓ All requirements met"
}

start_backend() {
    print_header "Starting Backend Server"
    
    if lsof -i:8002 > /dev/null 2>&1; then
        echo "Backend server already running on port 8002"
    else
        echo "Starting backend server..."
        cd "$BACKEND_DIR"
        npm start &
        BACKEND_PID=$!
        echo "Backend PID: $BACKEND_PID"
        
        # Wait for backend to be ready
        echo "Waiting for backend to start..."
        sleep 10
        
        # Check if backend is running
        if ! curl -s http://localhost:8002/health > /dev/null 2>&1; then
            print_warning "Backend may not be fully started"
        fi
    fi
}

start_metro() {
    print_header "Starting Metro Bundler"
    
    if lsof -i:8081 > /dev/null 2>&1; then
        echo "Metro bundler already running on port 8081"
    else
        echo "Starting Metro bundler..."
        cd "$FRONTEND_DIR"
        npx expo start --clear &
        METRO_PID=$!
        echo "Metro PID: $METRO_PID"
        
        # Wait for Metro to be ready
        echo "Waiting for Metro to start..."
        node "$PROJECT_DIR/scripts/wait-for-metro.js"
    fi
}

check_emulator() {
    print_header "Checking Android Emulator"
    
    # Check if any emulator is running
    if adb devices | grep -q "emulator"; then
        echo "✓ Emulator is already running"
        EMULATOR_RUNNING=true
    else
        echo "No emulator running"
        EMULATOR_RUNNING=false
    fi
}

start_emulator() {
    if [ "$EMULATOR_RUNNING" = false ]; then
        print_header "Starting Android Emulator"
        
        # List available AVDs
        echo "Available emulators:"
        emulator -list-avds
        
        # Try to start the configured emulator
        if emulator -list-avds | grep -q "$EMULATOR_NAME"; then
            echo "Starting $EMULATOR_NAME..."
            emulator -avd "$EMULATOR_NAME" -netdelay none -netspeed full &
            EMULATOR_PID=$!
            
            # Wait for emulator to boot
            echo "Waiting for emulator to boot..."
            adb wait-for-device
            
            # Wait for boot animation to finish
            while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
                sleep 2
                echo -n "."
            done
            echo -e "\n✓ Emulator started successfully"
        else
            print_error "Emulator $EMULATOR_NAME not found"
            echo "Please create an AVD or set EMULATOR_NAME to an existing one"
            exit 1
        fi
    fi
}

install_app() {
    print_header "Installing App on Emulator"
    
    APK_PATH="$FRONTEND_DIR/android/app/build/outputs/apk/debug/app-debug.apk"
    
    if [ -f "$APK_PATH" ]; then
        echo "Installing APK..."
        adb install -r "$APK_PATH"
        echo "✓ App installed successfully"
    else
        print_warning "APK not found at $APK_PATH"
        echo "Building app..."
        cd "$FRONTEND_DIR"
        npm run android
    fi
}

run_maestro_tests() {
    print_header "Running Maestro Tests"
    
    cd "$MAESTRO_DIR"
    
    # Parse test arguments
    TEST_TARGET="${1:-tests}"  # Default to all tests
    
    echo "Running tests in: $TEST_TARGET"
    echo "----------------------------------------"
    
    # Run Maestro tests
    if [ "$TEST_TARGET" = "smoke" ]; then
        # Run only smoke tests
        maestro test --tags smoke tests/
    elif [ "$TEST_TARGET" = "auth" ]; then
        # Run only auth tests
        maestro test tests/auth/
    elif [ "$TEST_TARGET" = "all" ]; then
        # Run all tests
        maestro test tests/
    else
        # Run specific test file or directory
        maestro test "$TEST_TARGET"
    fi
}

cleanup() {
    print_header "Cleaning Up"
    
    # Kill processes if we started them
    if [ ! -z "$BACKEND_PID" ]; then
        echo "Stopping backend server..."
        kill $BACKEND_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$METRO_PID" ]; then
        echo "Stopping Metro bundler..."
        kill $METRO_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$EMULATOR_PID" ] && [ "$KEEP_EMULATOR" != "true" ]; then
        echo "Stopping emulator..."
        kill $EMULATOR_PID 2>/dev/null || true
    fi
}

# Trap cleanup on exit
trap cleanup EXIT

# Main execution
main() {
    echo -e "${GREEN}Maestro Test Runner${NC}"
    echo "===================="
    
    # Parse arguments
    case "$1" in
        --help|-h)
            echo "Usage: $0 [test-target]"
            echo ""
            echo "Test targets:"
            echo "  smoke    - Run smoke tests only"
            echo "  auth     - Run auth tests only"
            echo "  all      - Run all tests"
            echo "  <path>   - Run specific test file or directory"
            echo ""
            echo "Environment variables:"
            echo "  EMULATOR_NAME    - Name of AVD to use (default: Pixel_4_API_30)"
            echo "  KEEP_EMULATOR    - Keep emulator running after tests (default: false)"
            echo ""
            exit 0
            ;;
    esac
    
    # Run checks and tests
    check_requirements
    start_backend
    start_metro
    check_emulator
    start_emulator
    install_app
    run_maestro_tests "$1"
    
    echo -e "\n${GREEN}✓ Tests completed!${NC}"
}

# Run main function
main "$@"