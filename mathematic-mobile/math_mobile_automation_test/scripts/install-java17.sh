#!/bin/bash

# Install Java 17 (required for Maestro on Linux)
# Usage: ./scripts/install-java17.sh

set -e

echo "=== Java 17 Installation Script ==="
echo ""

# Check if Java is already installed
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2 | cut -d'.' -f1)
    echo "Current Java version: $JAVA_VERSION"
    
    if [ "$JAVA_VERSION" -ge 17 ]; then
        echo "✓ Java 17 or higher is already installed"
        exit 0
    else
        echo "⚠ Java version is less than 17. Installation required."
    fi
fi

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     
        echo "Installing Java 17 on Linux..."
        
        # Try apt (Debian/Ubuntu)
        if command -v apt &> /dev/null; then
            sudo apt update
            sudo apt install -y openjdk-17-jdk
        # Try yum (RHEL/CentOS)
        elif command -v yum &> /dev/null; then
            sudo yum install -y java-17-openjdk-devel
        else
            echo "Unsupported Linux distribution. Please install Java 17 manually."
            exit 1
        fi
        ;;
    
    Darwin*)    
        echo "Installing Java 17 on macOS..."
        if ! command -v brew &> /dev/null; then
            echo "Homebrew not found. Please install Homebrew first."
            exit 1
        fi
        brew install openjdk@17
        
        # Link Java
        sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
        echo ""
        echo "Add to your shell profile:"
        echo 'export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"'
        ;;
    
    *)          
        echo "Unsupported OS: ${OS}"
        exit 1
        ;;
esac

# Verify installation
if command -v java &> /dev/null; then
    echo ""
    echo "✓ Java installed successfully!"
    java -version
else
    echo ""
    echo "✗ Java installation failed"
    exit 1
fi

echo ""
echo "=== Installation Complete ==="
