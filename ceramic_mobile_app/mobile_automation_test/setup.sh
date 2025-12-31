#!/bin/bash

###############################################################################
# Mobile Automation Test - Automated Setup Script
# This script automates the setup process for E2E mobile testing
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
# Step 1: Check Prerequisites
###############################################################################

check_prerequisites() {
    print_header "Step 1: Checking Prerequisites"

    local all_good=true

    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_success "Node.js found: $NODE_VERSION"
    else
        log_error "Node.js not found. Please install Node.js 18.x or 20.x"
        all_good=false
    fi

    # Check npm
    if command -v npm &> /dev/null; then
        NPM_VERSION=$(npm --version)
        log_success "npm found: $NPM_VERSION"
    else
        log_error "npm not found"
        all_good=false
    fi

    # Check Java
    if command -v java &> /dev/null; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        if echo "$JAVA_VERSION" | grep -q "11\."; then
            log_success "JDK 11 found: $JAVA_VERSION"
        else
            log_warning "JDK version: $JAVA_VERSION (JDK 11 is required)"
            log_info "Install JDK 11: sudo apt install openjdk-11-jdk"
            all_good=false
        fi
    else
        log_error "Java not found. Please install OpenJDK 11"
        all_good=false
    fi

    # Check ANDROID_HOME
    if [ -n "$ANDROID_HOME" ]; then
        log_success "ANDROID_HOME is set: $ANDROID_HOME"
    else
        log_warning "ANDROID_HOME not set. Android SDK may not be installed"
    fi

    # Check Android SDK
    if command -v adb &> /dev/null; then
        ADB_VERSION=$(adb --version | head -n 1)
        log_success "Android SDK found: $ADB_VERSION"
    else
        log_warning "adb not found. Android SDK may not be properly installed"
    fi

    if [ "$all_good" = false ]; then
        log_error "Prerequisites check failed. Please install missing components."
        log_info "See SETUP_GUIDE.md for detailed installation instructions"
        exit 1
    fi

    log_success "All prerequisites met!"
}

###############################################################################
# Step 2: Install Node Dependencies
###############################################################################

install_dependencies() {
    print_header "Step 2: Installing Node Dependencies"

    # Mobile automation test dependencies
    log_info "Installing mobile automation test dependencies..."
    npm install
    log_success "Mobile test dependencies installed"

    # Frontend dependencies
    log_info "Installing frontend dependencies..."
    cd ../front_end
    npm install
    log_success "Frontend dependencies installed"

    # Return to test directory
    cd ../mobile_automation_test
}

###############################################################################
# Step 3: Configure Android SDK
###############################################################################

configure_android_sdk() {
    print_header "Step 3: Configuring Android SDK"

    if [ -z "$ANDROID_HOME" ]; then
        log_warning "ANDROID_HOME not set. Attempting to detect..."

        # Common Android SDK locations
        if [ -d "$HOME/Android/Sdk" ]; then
            export ANDROID_HOME="$HOME/Android/Sdk"
            log_info "Found Android SDK at: $ANDROID_HOME"
        elif [ -d "$HOME/Library/Android/sdk" ]; then
            export ANDROID_HOME="$HOME/Library/Android/sdk"
            log_info "Found Android SDK at: $ANDROID_HOME"
        else
            log_error "Could not find Android SDK"
            log_info "Please install Android SDK and set ANDROID_HOME"
            return 1
        fi
    fi

    # Add Android SDK to PATH
    export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$PATH"
    export PATH="$ANDROID_HOME/platform-tools:$PATH"
    export PATH="$ANDROID_HOME/emulator:$PATH"

    log_success "Android SDK configured"
}

###############################################################################
# Step 4: Check/Create Android Emulator
###############################################################################

setup_emulator() {
    print_header "Step 4: Setting Up Android Emulator"

    EMULATOR_NAME="Pixel_3a_API_36_extension_level_17_x86_64"

    # Check if emulator exists
    if emulator -list-avds | grep -q "$EMULATOR_NAME"; then
        log_success "Emulator '$EMULATOR_NAME' already exists"
    else
        log_info "Emulator not found. Attempting to create..."

        # Check if system image is installed
        if sdkmanager --list_installed | grep -q "system-images;android-33;google_apis;x86_64"; then
            log_info "System image found, creating emulator..."
        else
            log_info "Installing system image..."
            yes | sdkmanager "system-images;android-33;google_apis;x86_64"
        fi

        # Create emulator
        echo "no" | avdmanager create avd \
            -n "$EMULATOR_NAME" \
            -k "system-images;android-33;google_apis;x86_64" \
            -d "pixel_3a" \
            --force

        log_success "Emulator created: $EMULATOR_NAME"
    fi

    # List available emulators
    log_info "Available emulators:"
    emulator -list-avds
}

###############################################################################
# Step 5: Configure Environment
###############################################################################

configure_environment() {
    print_header "Step 5: Configuring Environment"

    # Create local.properties for Android
    log_info "Creating local.properties..."
    if [ -n "$ANDROID_HOME" ]; then
        echo "sdk.dir=$ANDROID_HOME" > ../front_end/android/local.properties
        log_success "local.properties created"
    fi

    # Check if .env exists
    if [ -f .env ]; then
        log_success ".env file already exists"
    else
        log_info "Creating .env file..."
        cat > .env << 'EOF'
# Backend API Configuration
API_BASE_URL=http://10.0.2.2:8002
API_TIMEOUT=30000

# Test Configuration
TEST_TIMEOUT=120000
EOF
        log_success ".env file created"
    fi
}

###############################################################################
# Step 6: Build Android App
###############################################################################

build_android_app() {
    print_header "Step 6: Building Android Application"

    log_info "This may take several minutes on first build..."

    cd ../front_end/android

    # Clean build
    log_info "Cleaning previous builds..."
    ./gradlew clean

    # Build release and test APKs
    log_info "Building release APK..."
    ./gradlew assembleRelease assembleAndroidTest -DtestBuildType=release

    cd ../../mobile_automation_test

    log_success "Android app built successfully"
}

###############################################################################
# Step 7: Setup Test Database
###############################################################################

setup_database() {
    print_header "Step 7: Setting Up Test Database"

    log_info "Checking database connection..."

    # Check if MySQL is accessible
    if command -v mysql &> /dev/null; then
        log_info "Attempting to create test users..."

        # Try to run SQL script
        if mysql -h 127.0.0.1 -P 3308 -u ceramic_user -p'Mysql_2025' ceramic_marketplace < ../back_end/insert_test_users.sql 2>/dev/null; then
            log_success "Test users created successfully"

            # Verify users
            log_info "Verifying test users:"
            mysql -h 127.0.0.1 -P 3308 -u ceramic_user -p'Mysql_2025' ceramic_marketplace \
                -e "SELECT id, username, email, role FROM users WHERE id IN (500, 501, 502);" 2>/dev/null || true
        else
            log_warning "Could not connect to database"
            log_info "Make sure MySQL is running and credentials are correct"
            log_info "You can run this manually later:"
            log_info "  mysql -h 127.0.0.1 -P 3308 -u ceramic_user -p'Mysql_2025' ceramic_marketplace < ../back_end/insert_test_users.sql"
        fi
    else
        log_warning "MySQL client not found"
        log_info "Install with: sudo apt install mysql-client"
    fi
}

###############################################################################
# Step 8: Verify Installation
###############################################################################

verify_installation() {
    print_header "Step 8: Verifying Installation"

    local all_good=true

    # Check node_modules
    if [ -d "node_modules" ]; then
        log_success "Test dependencies installed"
    else
        log_error "Test dependencies missing"
        all_good=false
    fi

    # Check frontend node_modules
    if [ -d "../front_end/node_modules" ]; then
        log_success "Frontend dependencies installed"
    else
        log_error "Frontend dependencies missing"
        all_good=false
    fi

    # Check APK
    if [ -f "../front_end/android/app/build/outputs/apk/release/app-release.apk" ]; then
        log_success "Release APK built"
    else
        log_warning "Release APK not found"
    fi

    # Check emulator
    if emulator -list-avds | grep -q "Pixel_3a"; then
        log_success "Android emulator configured"
    else
        log_warning "Android emulator not found"
    fi

    if [ "$all_good" = true ]; then
        log_success "Installation verified successfully!"
    else
        log_warning "Some components may be missing. Check the logs above."
    fi
}

###############################################################################
# Main Setup Flow
###############################################################################

main() {
    print_header "Mobile Automation Test - Automated Setup"

    log_info "Starting automated setup process..."
    log_info "This will install dependencies and configure the test environment"
    echo ""

    # Run setup steps
    check_prerequisites
    install_dependencies
    configure_android_sdk
    setup_emulator
    configure_environment
    build_android_app
    setup_database
    verify_installation

    # Final instructions
    print_header "Setup Complete!"

    echo ""
    log_success "Mobile automation test environment is ready!"
    echo ""
    log_info "Next steps:"
    echo "  1. Start the backend server:"
    echo "     cd ../back_end"
    echo "     gunicorn app.main:app --workers 4 --bind 0.0.0.0:8002"
    echo ""
    echo "  2. Run tests:"
    echo "     ./run-tests.sh"
    echo ""
    echo "  Or run specific tests:"
    echo "     npx detox test --configuration android.emu.release e2e/auth/login.test.js"
    echo ""
    log_info "See SETUP_GUIDE.md for more information"
    echo ""
}

# Run main function
main "$@"
