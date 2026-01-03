#!/bin/bash

# Script to install Java 17 for Maestro requirements

set -e

echo "=== Installing Java 17 for Maestro ==="

# Update package list
echo "Updating package list..."
sudo apt update

# Install OpenJDK 17
echo "Installing OpenJDK 17..."
sudo apt install -y openjdk-17-jdk

# Set Java 17 as the default
echo "Configuring Java 17 as default..."
sudo update-alternatives --config java << EOF
2
EOF

# Verify installation
echo ""
echo "Java version after installation:"
java -version

echo ""
echo "=== Java 17 Installation Complete ==="
echo "You may need to set JAVA_HOME:"
echo "export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64"
echo ""