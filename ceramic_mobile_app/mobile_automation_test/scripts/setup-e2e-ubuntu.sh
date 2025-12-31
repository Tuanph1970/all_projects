#!/bin/bash

#===============================================================================
# E2E Test Environment Setup Script for Ubuntu 22.04
# Ceramic Mobile App - Detox E2E Testing
#===============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
NODE_VERSION="20"
JAVA_VERSION="17"
ANDROID_SDK_VERSION="35"
ANDROID_BUILD_TOOLS_VERSION="35.0.0"
EMULATOR_NAME="Pixel_4_API_35"
EMULATOR_DEVICE="pixel_4"
EMULATOR_API="35"

print_step() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
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
# Step 1: System Update and Basic Dependencies
#===============================================================================
install_system_dependencies() {
    print_step "Step 1: Installing System Dependencies"

    sudo apt-get update
    sudo apt-get install -y \
        curl \
        wget \
        git \
        unzip \
        openjdk-${JAVA_VERSION}-jdk \
        qemu-kvm \
        libvirt-daemon-system \
        libvirt-clients \
        bridge-utils \
        cpu-checker

    # Add user to kvm group for emulator acceleration
    sudo adduser $USER kvm 2>/dev/null || true

    print_success "System dependencies installed"
}

#===============================================================================
# Step 2: Install Node.js
#===============================================================================
install_nodejs() {
    print_step "Step 2: Installing Node.js ${NODE_VERSION}"

    if command -v node &> /dev/null; then
        CURRENT_NODE=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
        if [ "$CURRENT_NODE" -ge "$NODE_VERSION" ]; then
            print_warning "Node.js $(node -v) already installed, skipping..."
            return
        fi
    fi

    # Install Node.js via NodeSource
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
    sudo apt-get install -y nodejs

    print_success "Node.js $(node -v) installed"
    print_success "npm $(npm -v) installed"
}

#===============================================================================
# Step 3: Install Android SDK
#===============================================================================
install_android_sdk() {
    print_step "Step 3: Installing Android SDK"

    export ANDROID_HOME="$HOME/Android/Sdk"
    export ANDROID_SDK_ROOT="$ANDROID_HOME"

    if [ -d "$ANDROID_HOME" ] && [ -f "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
        print_warning "Android SDK already installed at $ANDROID_HOME, skipping..."
        return
    fi

    # Create Android SDK directory
    mkdir -p "$ANDROID_HOME/cmdline-tools"

    # Download command-line tools
    CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
    wget -q --show-progress -O /tmp/cmdline-tools.zip "$CMDLINE_TOOLS_URL"

    # Extract and organize
    unzip -q /tmp/cmdline-tools.zip -d /tmp/
    mv /tmp/cmdline-tools "$ANDROID_HOME/cmdline-tools/latest"
    rm /tmp/cmdline-tools.zip

    # Accept licenses and install components
    export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

    yes | sdkmanager --licenses > /dev/null 2>&1 || true

    sdkmanager \
        "platform-tools" \
        "platforms;android-${ANDROID_SDK_VERSION}" \
        "build-tools;${ANDROID_BUILD_TOOLS_VERSION}" \
        "emulator" \
        "system-images;android-${EMULATOR_API};google_apis;x86_64"

    print_success "Android SDK installed at $ANDROID_HOME"
}

#===============================================================================
# Step 4: Create Android Emulator
#===============================================================================
create_emulator() {
    print_step "Step 4: Creating Android Emulator"

    export ANDROID_HOME="$HOME/Android/Sdk"
    export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

    # Check if emulator already exists
    if avdmanager list avd 2>/dev/null | grep -q "$EMULATOR_NAME"; then
        print_warning "Emulator '$EMULATOR_NAME' already exists, skipping..."
        return
    fi

    # Create emulator
    echo "no" | avdmanager create avd \
        --name "$EMULATOR_NAME" \
        --device "$EMULATOR_DEVICE" \
        --package "system-images;android-${EMULATOR_API};google_apis;x86_64" \
        --force

    # Configure emulator for better performance
    EMULATOR_CONFIG="$HOME/.android/avd/${EMULATOR_NAME}.avd/config.ini"
    if [ -f "$EMULATOR_CONFIG" ]; then
        echo "hw.ramSize=4096" >> "$EMULATOR_CONFIG"
        echo "hw.gpu.enabled=yes" >> "$EMULATOR_CONFIG"
        echo "hw.gpu.mode=auto" >> "$EMULATOR_CONFIG"
        echo "disk.dataPartition.size=4G" >> "$EMULATOR_CONFIG"
    fi

    print_success "Emulator '$EMULATOR_NAME' created"
}

#===============================================================================
# Step 5: Setup Environment Variables
#===============================================================================
setup_environment() {
    print_step "Step 5: Setting Up Environment Variables"

    ENV_FILE="$HOME/.bashrc"

    # Check if already configured
    if grep -q "ANDROID_HOME" "$ENV_FILE"; then
        print_warning "Environment variables already configured in $ENV_FILE"
    else
        cat >> "$ENV_FILE" << 'EOF'

# Android SDK Environment Variables (added by E2E setup script)
export ANDROID_HOME="$HOME/Android/Sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

# Java Environment Variables
export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
export PATH="$JAVA_HOME/bin:$PATH"
EOF
        print_success "Environment variables added to $ENV_FILE"
    fi

    # Export for current session
    export ANDROID_HOME="$HOME/Android/Sdk"
    export ANDROID_SDK_ROOT="$ANDROID_HOME"
    export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"
    export JAVA_HOME="/usr/lib/jvm/java-17-openjdk-amd64"
    export PATH="$JAVA_HOME/bin:$PATH"
}

#===============================================================================
# Step 6: Install Detox CLI
#===============================================================================
install_detox_cli() {
    print_step "Step 6: Installing Detox CLI"

    if command -v detox &> /dev/null; then
        print_warning "Detox CLI already installed: $(detox --version)"
    else
        sudo npm install -g detox-cli
        print_success "Detox CLI installed"
    fi
}

#===============================================================================
# Step 7: Clone and Setup Project (if needed)
#===============================================================================
setup_project() {
    print_step "Step 7: Project Setup Instructions"

    echo -e "${YELLOW}After this script completes, run the following commands:${NC}"
    echo ""
    echo "1. Clone the repository (if not already done):"
    echo "   git clone <repository-url>"
    echo "   cd ceramic_mobile_app"
    echo ""
    echo "2. Install frontend dependencies:"
    echo "   cd front_end"
    echo "   npm install"
    echo ""
    echo "3. Build the debug APK for testing:"
    echo "   cd android"
    echo "   ./gradlew assembleDebug assembleAndroidTest -DtestBuildType=debug"
    echo "   cd ../.."
    echo ""
    echo "4. Install test dependencies:"
    echo "   cd mobile_automation_test"
    echo "   npm install"
    echo ""
    echo "5. Start the emulator:"
    echo "   emulator -avd ${EMULATOR_NAME} &"
    echo ""
    echo "6. Wait for emulator to boot, then run tests:"
    echo "   npx detox test --configuration android.emu.debug"
    echo ""
}

#===============================================================================
# Step 8: Verification
#===============================================================================
verify_installation() {
    print_step "Step 8: Verifying Installation"

    echo "Checking installed components..."
    echo ""

    # Node.js
    if command -v node &> /dev/null; then
        print_success "Node.js: $(node -v)"
    else
        print_error "Node.js: NOT INSTALLED"
    fi

    # npm
    if command -v npm &> /dev/null; then
        print_success "npm: $(npm -v)"
    else
        print_error "npm: NOT INSTALLED"
    fi

    # Java
    if command -v java &> /dev/null; then
        JAVA_VER=$(java -version 2>&1 | head -n 1)
        print_success "Java: $JAVA_VER"
    else
        print_error "Java: NOT INSTALLED"
    fi

    # Android SDK
    if [ -d "$HOME/Android/Sdk" ]; then
        print_success "Android SDK: $HOME/Android/Sdk"
    else
        print_error "Android SDK: NOT INSTALLED"
    fi

    # ADB
    if command -v adb &> /dev/null || [ -f "$HOME/Android/Sdk/platform-tools/adb" ]; then
        print_success "ADB: Available"
    else
        print_error "ADB: NOT AVAILABLE"
    fi

    # Emulator
    if [ -d "$HOME/.android/avd/${EMULATOR_NAME}.avd" ]; then
        print_success "Emulator: $EMULATOR_NAME"
    else
        print_error "Emulator: NOT CREATED"
    fi

    # KVM
    if [ -e /dev/kvm ]; then
        print_success "KVM: Available (hardware acceleration enabled)"
    else
        print_warning "KVM: Not available (emulator will be slow)"
    fi

    # Detox CLI
    if command -v detox &> /dev/null; then
        print_success "Detox CLI: $(detox --version)"
    else
        print_error "Detox CLI: NOT INSTALLED"
    fi

    echo ""
}

#===============================================================================
# Main Execution
#===============================================================================
main() {
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║     Ceramic Mobile App - E2E Test Environment Setup          ║"
    echo "║                    Ubuntu 22.04                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo "This script will install:"
    echo "  - Node.js ${NODE_VERSION}"
    echo "  - Java ${JAVA_VERSION}"
    echo "  - Android SDK (API ${ANDROID_SDK_VERSION})"
    echo "  - Android Emulator (${EMULATOR_NAME})"
    echo "  - Detox CLI"
    echo ""

    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi

    install_system_dependencies
    install_nodejs
    install_android_sdk
    create_emulator
    setup_environment
    install_detox_cli
    verify_installation
    setup_project

    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                    Setup Complete!                            ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Please restart your terminal or run:${NC}"
    echo "  source ~/.bashrc"
    echo ""
    echo "Then follow the project setup instructions above."
}

# Run main function
main "$@"
