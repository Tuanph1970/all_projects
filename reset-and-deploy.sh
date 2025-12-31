#!/bin/bash

# ============================================================================
# Reset and Deploy Script
# ============================================================================
# This script provides a quick way to reset everything and redeploy
# ============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo
    print_color $CYAN "=============================================="
    print_color $CYAN "$1"
    print_color $CYAN "=============================================="
    echo
}

# Main execution
main() {
    print_header "Reset and Redeploy"
    
    print_color $YELLOW "This will:"
    print_color $YELLOW "1. Stop all running containers"
    print_color $YELLOW "2. Clean up Docker resources"
    print_color $YELLOW "3. Preserve your data volumes"
    print_color $YELLOW "4. Launch interactive deployment"
    echo
    
    read -p "$(print_color $CYAN "Continue? (y/N): ")" answer
    answer=${answer:-n}
    
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
        print_color $YELLOW "Operation cancelled."
        exit 0
    fi
    
    # Step 1: Cleanup
    print_header "Step 1: Cleaning Up"
    print_color $BLUE "Running cleanup..."
    ./cleanup-all.sh --force
    
    # Step 2: Wait a moment
    print_color $BLUE "Waiting for cleanup to complete..."
    sleep 2
    
    # Step 3: Interactive deployment
    print_header "Step 2: Redeploying"
    print_color $BLUE "Launching interactive deployment..."
    ./deploy-interactive.sh
}

# Check if required scripts exist
if [ ! -f "./cleanup-all.sh" ]; then
    print_color $RED "Error: cleanup-all.sh not found!"
    exit 1
fi

if [ ! -f "./deploy-interactive.sh" ]; then
    print_color $RED "Error: deploy-interactive.sh not found!"
    exit 1
fi

# Run main
main