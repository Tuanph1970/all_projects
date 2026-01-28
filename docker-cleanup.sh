#!/bin/bash

# =============================================================================
# Docker Complete Cleanup Script
# =============================================================================
# This script removes ALL Docker resources:
#   - Containers (running and stopped)
#   - Images
#   - Volumes
#   - Networks
#   - Build cache
#
# Usage:
#   ./docker-cleanup.sh           # Interactive mode (asks for confirmation)
#   ./docker-cleanup.sh --force   # Force mode (no confirmation)
#   ./docker-cleanup.sh --help    # Show help
#
# WARNING: This will DELETE ALL Docker data!
# =============================================================================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Print functions
print_header() {
    echo
    echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${WHITE}$1${NC}"
    echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo
}

print_info() {
    echo -e "${BLUE}ℹ${NC}  $1"
}

print_success() {
    echo -e "${GREEN}✓${NC}  $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_error() {
    echo -e "${RED}✗${NC}  $1"
}

# Show current Docker usage
show_current_usage() {
    print_header "Current Docker Usage"

    echo -e "${WHITE}Containers:${NC}"
    local containers=$(docker ps -a -q 2>/dev/null | wc -l)
    echo "  Total: $containers"
    docker ps -a --format "  - {{.Names}} ({{.Status}})" 2>/dev/null | head -20
    if [ "$containers" -gt 20 ]; then
        echo "  ... and $((containers - 20)) more"
    fi
    echo

    echo -e "${WHITE}Images:${NC}"
    local images=$(docker images -q 2>/dev/null | wc -l)
    echo "  Total: $images"
    docker images --format "  - {{.Repository}}:{{.Tag}} ({{.Size}})" 2>/dev/null | head -10
    if [ "$images" -gt 10 ]; then
        echo "  ... and $((images - 10)) more"
    fi
    echo

    echo -e "${WHITE}Volumes:${NC}"
    local volumes=$(docker volume ls -q 2>/dev/null | wc -l)
    echo "  Total: $volumes"
    docker volume ls --format "  - {{.Name}}" 2>/dev/null | head -10
    if [ "$volumes" -gt 10 ]; then
        echo "  ... and $((volumes - 10)) more"
    fi
    echo

    echo -e "${WHITE}Networks:${NC}"
    local networks=$(docker network ls -q 2>/dev/null | wc -l)
    echo "  Total: $networks (including default networks)"
    docker network ls --format "  - {{.Name}} ({{.Driver}})" 2>/dev/null
    echo

    echo -e "${WHITE}Disk Usage:${NC}"
    docker system df 2>/dev/null || echo "  Unable to get disk usage"
    echo
}

# Stop all running containers
stop_containers() {
    print_info "Stopping all running containers..."
    local running=$(docker ps -q 2>/dev/null)
    if [ -n "$running" ]; then
        docker stop $running 2>/dev/null || true
        print_success "All containers stopped"
    else
        print_info "No running containers"
    fi
}

# Remove all containers
remove_containers() {
    print_info "Removing all containers..."
    local containers=$(docker ps -a -q 2>/dev/null)
    if [ -n "$containers" ]; then
        docker rm -f $containers 2>/dev/null || true
        print_success "All containers removed"
    else
        print_info "No containers to remove"
    fi
}

# Remove all images
remove_images() {
    print_info "Removing all images..."
    local images=$(docker images -q 2>/dev/null)
    if [ -n "$images" ]; then
        docker rmi -f $images 2>/dev/null || true
        print_success "All images removed"
    else
        print_info "No images to remove"
    fi
}

# Remove all volumes
remove_volumes() {
    print_info "Removing all volumes..."
    local volumes=$(docker volume ls -q 2>/dev/null)
    if [ -n "$volumes" ]; then
        docker volume rm -f $volumes 2>/dev/null || true
        print_success "All volumes removed"
    else
        print_info "No volumes to remove"
    fi
}

# Remove all custom networks
remove_networks() {
    print_info "Removing all custom networks..."
    # Get all networks except default ones (bridge, host, none)
    local networks=$(docker network ls --format "{{.Name}}" 2>/dev/null | grep -v -E "^(bridge|host|none)$")
    if [ -n "$networks" ]; then
        echo "$networks" | xargs -r docker network rm 2>/dev/null || true
        print_success "All custom networks removed"
    else
        print_info "No custom networks to remove"
    fi
}

# Clean build cache
clean_build_cache() {
    print_info "Cleaning build cache..."
    docker builder prune -af 2>/dev/null || true
    print_success "Build cache cleaned"
}

# System prune
system_prune() {
    print_info "Running system prune..."
    docker system prune -af --volumes 2>/dev/null || true
    print_success "System pruned"
}

# Full cleanup
full_cleanup() {
    print_header "Starting Full Docker Cleanup"

    stop_containers
    remove_containers
    remove_volumes
    remove_networks
    remove_images
    clean_build_cache
    system_prune

    print_header "Cleanup Complete"

    echo -e "${WHITE}Final Docker Status:${NC}"
    echo "  Containers: $(docker ps -a -q 2>/dev/null | wc -l)"
    echo "  Images: $(docker images -q 2>/dev/null | wc -l)"
    echo "  Volumes: $(docker volume ls -q 2>/dev/null | wc -l)"
    echo "  Networks: $(docker network ls -q 2>/dev/null | wc -l)"
    echo

    docker system df 2>/dev/null || true
}

# Show help
show_help() {
    echo "Docker Complete Cleanup Script"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  (none)      Interactive mode - shows current usage and asks for confirmation"
    echo "  --force     Force mode - cleans everything without confirmation"
    echo "  --show      Show current Docker usage only (no cleanup)"
    echo "  --help      Show this help message"
    echo
    echo "What gets removed:"
    echo "  - All containers (running and stopped)"
    echo "  - All images"
    echo "  - All volumes (INCLUDING DATA!)"
    echo "  - All custom networks"
    echo "  - Build cache"
    echo
    echo -e "${RED}WARNING: This will DELETE ALL Docker data including databases!${NC}"
    echo
}

# Main
main() {
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running!"
        exit 1
    fi

    case "$1" in
        --force|-f)
            print_warning "Force mode - cleaning everything without confirmation!"
            full_cleanup
            ;;
        --show|-s)
            show_current_usage
            ;;
        --help|-h)
            show_help
            ;;
        "")
            show_current_usage

            echo -e "${RED}╔═══════════════════════════════════════════════════════════╗${NC}"
            echo -e "${RED}║  WARNING: This will DELETE ALL Docker data!               ║${NC}"
            echo -e "${RED}║  Including all databases, volumes, and images!            ║${NC}"
            echo -e "${RED}╚═══════════════════════════════════════════════════════════╝${NC}"
            echo

            read -p "Are you sure you want to clean EVERYTHING? (yes/no): " confirm
            if [ "$confirm" == "yes" ]; then
                full_cleanup
            else
                print_info "Cleanup cancelled"
                exit 0
            fi
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
