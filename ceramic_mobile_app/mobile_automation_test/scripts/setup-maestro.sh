#!/bin/bash

# Maestro setup script for Ceramic Mobile App
# This script installs Maestro CLI and sets up the environment

set -e

echo "=== Maestro Setup Script ==="
echo "Setting up Maestro for mobile automation testing..."

# Check OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE="Linux";;
    Darwin*)    OS_TYPE="macOS";;
    *)          echo "Unsupported OS: ${OS}"; exit 1;;
esac

echo "Detected OS: ${OS_TYPE}"

# Install Maestro CLI
echo "Installing Maestro CLI..."

if [ "${OS_TYPE}" = "macOS" ]; then
    # macOS installation using Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
    fi
    brew tap mobile-dev-inc/maestro
    brew install maestro
elif [ "${OS_TYPE}" = "Linux" ]; then
    # Linux installation using curl
    curl -Ls "https://get.maestro.mobile.dev" | bash
    
    # Add to PATH if not already added
    if ! grep -q "export PATH=\"\$HOME/.maestro/bin:\$PATH\"" ~/.bashrc; then
        echo 'export PATH="$HOME/.maestro/bin:$PATH"' >> ~/.bashrc
        echo "Added Maestro to PATH in ~/.bashrc"
        echo "Please run 'source ~/.bashrc' or restart your terminal"
    fi
    
    # Export for current session
    export PATH="$HOME/.maestro/bin:$PATH"
fi

# Verify installation
if command -v maestro &> /dev/null; then
    echo "Maestro installed successfully!"
    maestro --version
else
    echo "Error: Maestro installation failed"
    exit 1
fi

# Install additional dependencies if needed
echo "Checking for Android SDK..."
if [ -z "$ANDROID_HOME" ]; then
    echo "Warning: ANDROID_HOME is not set. Please set it to your Android SDK path"
    echo "Example: export ANDROID_HOME=~/Android/Sdk"
fi

# Check ADB
if ! command -v adb &> /dev/null; then
    echo "Warning: ADB not found in PATH. Please ensure Android SDK platform-tools is in your PATH"
    echo "Example: export PATH=\$PATH:\$ANDROID_HOME/platform-tools"
fi

echo ""
echo "=== Setup Complete ==="
echo "Next steps:"
echo "1. If on Linux, run: source ~/.bashrc"
echo "2. Ensure ANDROID_HOME is set correctly"
echo "3. Start an Android emulator or connect a device"
echo "4. Run: maestro test maestro/tests"
echo ""