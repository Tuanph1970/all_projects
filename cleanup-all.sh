#!/bin/bash

# ============================================================================
# Multi-Project Cleanup Script
# ============================================================================
# This script removes all containers, volumes, and networks for:
#   - Ceramic Mobile App Backend
#   - Stock Predict Backend
#   - Mathematic Mobile Backend
#
# Usage: ./cleanup-all.sh [--volumes] [--force]
#   Options:
#     --volumes    Also remove data volumes (WARNING: This deletes all data!)
#     --force      Skip confirmation prompts
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Project names
PROJECTS=("ceramic" "stockpredict" "mathematic")

# Options
REMOVE_VOLUMES=false
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--volumes] [--force]"
            exit 1
            ;;
    esac
done

# Function to print colored output
print_color() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Function to print section headers
print_header() {
    echo
    print_color $CYAN "=============================================="
    print_color $CYAN "$1"
    print_color $CYAN "=============================================="
    echo
}

# Function to ask yes/no question
ask_yes_no() {
    if [ "$FORCE" = true ]; then
        return 0
    fi
    
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

# Function to stop and remove containers for a project
cleanup_project_containers() {
    local project=$1
    print_color $BLUE "🧹 Cleaning up $project containers..."
    
    # Get all containers for the project
    local containers=$(docker ps -a --filter "label=com.docker.compose.project=$project" --format "{{.Names}}")
    
    if [ -z "$containers" ]; then
        print_color $YELLOW "  No containers found for $project"
    else
        # Stop containers
        print_color $YELLOW "  Stopping containers..."
        docker stop $containers 2>/dev/null || true
        
        # Remove containers
        print_color $YELLOW "  Removing containers..."
        docker rm $containers 2>/dev/null || true
        
        print_color $GREEN "  ✓ Containers removed"
    fi
}

# Function to remove volumes for a project
cleanup_project_volumes() {
    local project=$1
    print_color $BLUE "🗑️  Removing $project volumes..."
    
    # List of known volume patterns for each project
    case $project in
        ceramic)
            local volumes=(
                "ceramic_mysql_data"
                "ceramic_nginx_logs"
                "ceramic_redis_data"
                "${project}_mysql_data"
                "${project}_nginx_logs"
                "${project}_redis_data"
            )
            ;;
        stockpredict)
            local volumes=(
                "stock_mysql_data"
                "stockpredict_model_data"
                "stockpredict_media_data"
                "stockpredict_logs_data"
                "${project}_model_data"
                "${project}_media_data"
                "${project}_logs_data"
            )
            ;;
        mathematic)
            local volumes=(
                "mysql_data"
                "redis_data"
                "math_mysql_data"
                "math_redis_data"
                "math_uploads"
                "math_models"
                "math_rabbitmq_data"
                "math_prometheus_data"
                "math_grafana_data"
                "${project}_mysql_data"
                "${project}_redis_data"
            )
            ;;
    esac
    
    local removed=false
    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            docker volume rm "$volume" 2>/dev/null && {
                print_color $GREEN "  ✓ Removed volume: $volume"
                removed=true
            } || true
        fi
    done
    
    if [ "$removed" = false ]; then
        print_color $YELLOW "  No volumes found for $project"
    fi
}

# Function to remove networks for a project
cleanup_project_networks() {
    local project=$1
    print_color $BLUE "🔌 Removing $project networks..."
    
    # Known network patterns
    local networks=(
        "${project}_network"
        "${project}_default"
        "ceramic_network"
        "stock_network"
        "math_network"
        "mathematics-solver-network"
        "stockpredict_network"
    )
    
    local removed=false
    for network in "${networks[@]}"; do
        if docker network ls | grep -q "$network"; then
            docker network rm "$network" 2>/dev/null && {
                print_color $GREEN "  ✓ Removed network: $network"
                removed=true
            } || true
        fi
    done
    
    if [ "$removed" = false ]; then
        print_color $YELLOW "  No networks found for $project"
    fi
}

# Function to clean docker-compose override files
cleanup_override_files() {
    print_header "Cleaning Override Files"
    
    local files=(
        # "/home/tuanph/all_projects/ceramic_mobile_app/back_end/docker-compose.override.yml"
        # "/home/tuanph/all_projects/stockpredict/webapi/docker-compose.override.yml"
        # "/home/tuanph/all_projects/mathematic-mobile/backend/docker-compose.override.yml"
        "/home/home/all_projects/ceramic_mobile_app/back_end/docker-compose.override.yml"
        "/home/home/all_projects/stockpredict/webapi/docker-compose.override.yml"
        "/home/home/all_projects/mathematic-mobile/backend/docker-compose.override.yml"
    )
    
    for file in "${files[@]}"; do
        if [ -f "$file" ]; then
            rm "$file"
            print_color $GREEN "✓ Removed: $file"
        fi
    done
}

# Main cleanup function
main() {
    print_header "Multi-Project Cleanup Tool"
    
    print_color $MAGENTA "This tool will clean up Docker resources for all projects."
    
    if [ "$REMOVE_VOLUMES" = true ]; then
        print_color $RED "⚠️  WARNING: --volumes flag is set. This will DELETE ALL DATA!"
    fi
    
    echo
    
    # Show what will be cleaned
    print_color $CYAN "The following will be cleaned:"
    print_color $YELLOW "  • All project containers"
    print_color $YELLOW "  • All project networks"
    print_color $YELLOW "  • Docker-compose override files"
    
    if [ "$REMOVE_VOLUMES" = true ]; then
        print_color $RED "  • ALL PROJECT DATA VOLUMES (PERMANENT DATA LOSS!)"
    fi
    
    echo
    
    if ! ask_yes_no "Do you want to proceed with cleanup?" "n"; then
        print_color $YELLOW "Cleanup cancelled."
        exit 0
    fi
    
    # Stop and remove containers
    print_header "Removing Containers"
    for project in "${PROJECTS[@]}"; do
        cleanup_project_containers "$project"
        echo
    done
    
    # Remove volumes if requested
    if [ "$REMOVE_VOLUMES" = true ]; then
        print_header "Removing Volumes"
        
        print_color $RED "⚠️  FINAL WARNING: This will permanently delete all data!"
        if ask_yes_no "Are you absolutely sure you want to delete all volumes?" "n"; then
            for project in "${PROJECTS[@]}"; do
                cleanup_project_volumes "$project"
                echo
            done
        else
            print_color $YELLOW "Skipping volume removal."
        fi
    fi
    
    # Remove networks
    print_header "Removing Networks"
    for project in "${PROJECTS[@]}"; do
        cleanup_project_networks "$project"
        echo
    done
    
    # Clean override files
    cleanup_override_files
    
    # Docker system cleanup
    print_header "Docker System Cleanup"
    
    if ask_yes_no "Do you want to run Docker system prune? (removes unused images, containers, networks)" "y"; then
        print_color $BLUE "Running Docker system prune..."
        docker system prune -f
        print_color $GREEN "✓ Docker system cleaned"
    fi
    
    # Summary
    print_header "Cleanup Complete!"
    
    print_color $GREEN "All Docker resources have been cleaned."
    echo
    print_color $CYAN "You can now redeploy using:"
    print_color $WHITE "  ./deploy-interactive.sh"
    echo
    print_color $CYAN "Or deploy all projects at once:"
    print_color $WHITE "  ./deploy-projects.sh start all --build"
    echo
    
    if [ "$REMOVE_VOLUMES" = false ]; then
        print_color $YELLOW "Note: Data volumes were preserved. Use --volumes flag to remove them."
    fi
}

# Run main function
main