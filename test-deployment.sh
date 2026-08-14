#!/bin/bash

# ============================================================================
# Deployment Test Script
# ============================================================================
# This script tests the deployment and provides a summary of services
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
    print_color $CYAN "======================================"
    print_color $CYAN "$1"
    print_color $CYAN "======================================"
    echo
}

# Function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    printf "%-30s" "$name:"
    
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        print_color $GREEN " ✓ OK (HTTP $expected_code)"
        return 0
    else
        local actual_code=$(curl -s -o /dev/null -w "%{http_code}" "$url")
        print_color $RED " ✗ FAILED (HTTP $actual_code)"
        return 1
    fi
}

# Function to check port
check_port() {
    local name=$1
    local port=$2
    
    printf "%-30s" "$name (Port $port):"
    
    if nc -z localhost "$port" 2>/dev/null; then
        print_color $GREEN " ✓ OPEN"
        return 0
    else
        print_color $RED " ✗ CLOSED"
        return 1
    fi
}

# Main test
main() {
    print_header "Multi-Project Deployment Test"
    
    print_color $BLUE "Testing service availability..."
    echo
    
    # Test API endpoints
    print_color $YELLOW "API Services:"
    test_endpoint "Mercai API" "http://localhost:8002/health" || true
    test_endpoint "Mercai Docs" "http://localhost:8002/docs" || true
    test_endpoint "Stock API" "http://localhost:8080/stock/api/" || true
    test_endpoint "Math API" "http://localhost:8003/health" || true
    
    echo
    
    # Test database ports
    print_color $YELLOW "Database Services:"
    check_port "Mercai MySQL" 3308 || true
    check_port "Stock MySQL" 3309 || true
    check_port "Math MySQL" 3310 || true
    
    echo
    
    # Test Redis ports
    print_color $YELLOW "Cache Services:"
    check_port "Mercai Redis" 6379 || true
    check_port "Math Redis" 6380 || true
    
    echo
    
    # Docker container status
    print_header "Docker Container Status"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(mercai|stock|math)" || print_color $YELLOW "No project containers running"
    
    echo
    
    # Summary
    print_header "Deployment Summary"
    
    print_color $CYAN "To deploy services, use one of these methods:"
    echo
    print_color $YELLOW "1. Interactive deployment (recommended):"
    print_color $WHITE "   ./deploy-interactive.sh"
    echo
    print_color $YELLOW "2. Command line deployment:"
    print_color $WHITE "   ./deploy-projects.sh start all"
    echo
    print_color $YELLOW "3. Deploy specific projects:"
    print_color $WHITE "   ./deploy-projects.sh start mercai stock"
    echo
    
    print_color $CYAN "Environment configuration file:"
    print_color $WHITE "   .deploy-env"
    echo
}

main