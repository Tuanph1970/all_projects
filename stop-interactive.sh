#!/bin/bash

# ============================================================================
# Interactive Multi-Project Stop Script
# ============================================================================
# This script provides an interactive dialog-based interface to stop:
#   - Mercai Backend
#   - Stock Predict Backend
#   - Mathematic Mobile Backend
#
# Usage: ./stop-interactive.sh
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Dynamic BASE_DIR detection - automatically detect the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$SCRIPT_DIR"

# Project directories
MERCAI_DIR="$BASE_DIR/mercai/back_end"
STOCK_DIR="$BASE_DIR/stockpredict/stock_microservices"
MATH_DIR="$BASE_DIR/mathematic-mobile/backend"

# Selected projects
SELECTED_PROJECTS=()

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print section headers
print_header() {
    echo
    print_color $CYAN "╔═══════════════════════════════════════════════════════════╗"
    print_color $CYAN "║                                                           ║"
    printf "${CYAN}║${NC} %-57s ${CYAN}║${NC}\n" "$1"
    print_color $CYAN "║                                                           ║"
    print_color $CYAN "╚═══════════════════════════════════════════════════════════╝"
    echo
}

# Function to print a box
print_box() {
    local title=$1
    local content=$2
    echo
    print_color $RED "┌─────────────────────────────────────────────────────────┐"
    printf "${RED}│${NC} %-55s ${RED}│${NC}\n" "$title"
    print_color $RED "├─────────────────────────────────────────────────────────┤"
    printf "${RED}│${NC} %-55s ${RED}│${NC}\n" "$content"
    print_color $RED "└─────────────────────────────────────────────────────────┘"
    echo
}

# Function to ask yes/no question
ask_yes_no() {
    local question=$1
    local default=$2
    local answer
    
    if [ "$default" = "y" ]; then
        read -p "$(print_color $YELLOW "$question (Y/n): ")" answer
        answer=${answer:-y}
    else
        read -p "$(print_color $YELLOW "$question (y/N): ")" answer
        answer=${answer:-n}
    fi
    
    [[ "$answer" =~ ^[Yy]$ ]]
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_color $RED "Error: Docker is not running!"
        exit 1
    fi
}

# Function to check if project is running
is_project_running() {
    local project_name=$1
    docker ps --filter "label=com.docker.compose.project=$project_name" --format "{{.Names}}" | grep -q .
}

# Function to get running containers
get_project_containers() {
    local project_name=$1
    docker ps --filter "label=com.docker.compose.project=$project_name" --format "{{.Names}}"
}

# Function to stop a project
stop_project() {
    local project=$1
    local project_dir=""
    local compose_file=""
    local project_name=""
    
    case $project in
        mercai)
            project_dir="$MERCAI_DIR"
            compose_file="docker-compose.yml"
            project_name="mercai"
            ;;
        stock)
            project_dir="$STOCK_DIR"
            compose_file="docker-compose.yml"
            project_name="stockpredict"
            ;;
        math)
            project_dir="$MATH_DIR"
            compose_file="docker-compose.yml"
            project_name="mathematic"
            ;;
    esac
    
    print_color $BLUE "🛑 Stopping $project_name..."
    
    cd "$project_dir"
    
    if [ -f "docker-compose.override.yml" ]; then
        docker compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" down
    else
        docker compose -f "$compose_file" -p "$project_name" down
    fi
    
    print_color $GREEN "✓ $project_name stopped successfully!"
}

# Function to show stop summary
show_stop_summary() {
    print_header "Stop Summary"
    
    echo
    print_color $MAGENTA "Projects to be stopped:"
    for project in "${SELECTED_PROJECTS[@]}"; do
        case $project in
            mercai)
                print_color $RED "  ✓ Mercai Backend"
                ;;
            stock)
                print_color $RED "  ✓ Stock Predict Backend"
                ;;
            math)
                print_color $RED "  ✓ Mathematics Mobile Backend"
                ;;
        esac
    done
    
    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ]; then
        print_color $YELLOW "  No projects selected to stop"
    fi
    echo
}

# Main interactive flow
main() {
    clear
    print_header "Interactive Multi-Project Stop Tool"
    
    print_color $MAGENTA "This tool will help you stop running backend services."
    echo
    
    # Check Docker
    print_color $BLUE "🔍 Checking Docker..."
    check_docker
    print_color $GREEN "✓ Docker is running"
    
    echo
    print_header "Running Services Overview"
    
    # Check each project status
    local has_running=false
    
    print_color $CYAN "Currently running services:"
    echo
    
    # Mercai
    if is_project_running "mercai"; then
        has_running=true
        print_color $GREEN "  • Mercai Backend (Port 8002)"
        print_color $YELLOW "    Containers: $(get_project_containers mercai | tr '\n' ', ' | sed 's/,$//')"
    else
        print_color $RED "  ○ Mercai Backend - Not Running"
    fi
    
    # Stock
    if is_project_running "stockpredict"; then
        has_running=true
        print_color $GREEN "  • Stock Predict Backend (Port 8080)"
        print_color $YELLOW "    Containers: $(get_project_containers stockpredict | tr '\n' ', ' | sed 's/,$//')"
    else
        print_color $RED "  ○ Stock Predict Backend - Not Running"
    fi
    
    # Mathematics
    if is_project_running "mathematic"; then
        has_running=true
        print_color $GREEN "  • Mathematics Mobile Backend (Port 8003)"
        print_color $YELLOW "    Containers: $(get_project_containers mathematic | tr '\n' ', ' | sed 's/,$//')"
    else
        print_color $RED "  ○ Mathematics Mobile Backend - Not Running"
    fi
    
    echo
    
    if [ "$has_running" = false ]; then
        print_color $YELLOW "No services are currently running."
        exit 0
    fi
    
    print_header "Select Services to Stop"
    
    # Ask about each running project
    # Mercai
    if is_project_running "mercai"; then
        print_box "Mercai Backend" \
                 "Running on port 8002"
        if ask_yes_no "Do you want to stop Mercai Backend?" "y"; then
            SELECTED_PROJECTS+=("mercai")
            print_color $RED "✓ Mercai Backend will be stopped"
        else
            print_color $YELLOW "○ Keeping Mercai Backend running"
        fi
        echo
    fi
    
    # Stock
    if is_project_running "stockpredict"; then
        print_box "Stock Predict Backend" \
                 "Running on port 8080"
        if ask_yes_no "Do you want to stop Stock Predict Backend?" "y"; then
            SELECTED_PROJECTS+=("stock")
            print_color $RED "✓ Stock Predict Backend will be stopped"
        else
            print_color $YELLOW "○ Keeping Stock Predict Backend running"
        fi
        echo
    fi
    
    # Mathematics
    if is_project_running "mathematic"; then
        print_box "Mathematics Mobile Backend" \
                 "Running on port 8003"
        if ask_yes_no "Do you want to stop Mathematics Mobile Backend?" "y"; then
            SELECTED_PROJECTS+=("math")
            print_color $RED "✓ Mathematics Mobile Backend will be stopped"
        else
            print_color $YELLOW "○ Keeping Mathematics Mobile Backend running"
        fi
        echo
    fi
    
    # Show summary and confirm
    show_stop_summary
    
    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ]; then
        print_color $YELLOW "No projects selected. Exiting."
        exit 0
    fi
    
    print_color $RED "⚠️  WARNING: This will stop the selected services and their databases!"
    if ask_yes_no "Are you sure you want to proceed?" "n"; then
        print_header "Stopping Projects"
        
        for project in "${SELECTED_PROJECTS[@]}"; do
            echo
            stop_project "$project"
        done
        
        echo
        print_header "Stop Complete!"
        
        print_color $GREEN "All selected projects have been stopped successfully!"
        echo
        print_color $CYAN "To start services again, run:"
        print_color $WHITE "  ./deploy-interactive.sh"
        echo
        print_color $CYAN "To check the status of all services, run:"
        print_color $WHITE "  ./deploy-projects.sh status"
        echo
    else
        print_color $YELLOW "Stop operation cancelled."
    fi
}

# Run main function
main