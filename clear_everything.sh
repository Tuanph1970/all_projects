#!/bin/bash

# ============================================================================
# Clear Everything Script - Complete Docker & Port Cleanup
# ============================================================================
# This script removes all Docker containers, networks, volumes, and kills
# all processes using ports that might conflict with the deployment.
#
# Usage: ./clear_everything.sh [--force]
#   --force: Skip confirmation prompts
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

# Force mode flag
FORCE_MODE=false
if [[ "$1" == "--force" || "$1" == "-f" ]]; then
    FORCE_MODE=true
fi

# Ports used by the deployment projects
DEPLOYMENT_PORTS=(
    # Mercai
    8002    # API Gateway
    8080    # Traefik Dashboard (Mercai)
    3308    # MySQL
    6379    # Redis

    # Stock Predict
    8004    # API Gateway
    8084    # Traefik Dashboard (Stock)
    3309    # MySQL
    3100    # Grafana
    15672   # RabbitMQ Management
    5672    # RabbitMQ AMQP
    11434   # Ollama LLM

    # Common ports that might conflict
    80      # HTTP
    443     # HTTPS
    3306    # Default MySQL
    5432    # PostgreSQL
    27017   # MongoDB
)

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
    printf "${CYAN}║${NC} %-57s ${CYAN}║${NC}\n" "$1"
    print_color $CYAN "╚═══════════════════════════════════════════════════════════╝"
    echo
}

# Function to ask yes/no question
ask_yes_no() {
    if [ "$FORCE_MODE" = true ]; then
        return 0
    fi

    local question=$1
    local answer
    read -p "$(print_color $YELLOW "$question (y/N): ")" answer
    [[ "$answer" =~ ^[Yy]$ ]]
}

# Function to check if running as root (needed for some port operations)
check_permissions() {
    if [ "$EUID" -ne 0 ] && [ "$FORCE_MODE" = false ]; then
        print_color $YELLOW "Note: Some operations may require sudo privileges."
        print_color $YELLOW "You may be prompted for your password."
        echo
    fi
}

# Function to stop all Docker containers
stop_all_containers() {
    print_header "Stopping All Docker Containers"

    local containers=$(docker ps -q 2>/dev/null)
    if [ -n "$containers" ]; then
        print_color $BLUE "Stopping running containers..."
        docker stop $containers 2>/dev/null || true
        print_color $GREEN "✓ All containers stopped"
    else
        print_color $YELLOW "○ No running containers found"
    fi
}

# Function to remove all Docker containers
remove_all_containers() {
    print_header "Removing All Docker Containers"

    local containers=$(docker ps -aq 2>/dev/null)
    if [ -n "$containers" ]; then
        print_color $BLUE "Removing containers..."
        docker rm -f $containers 2>/dev/null || true
        print_color $GREEN "✓ All containers removed"
    else
        print_color $YELLOW "○ No containers to remove"
    fi
}

# Function to remove project-specific Docker Compose stacks
remove_compose_stacks() {
    print_header "Removing Docker Compose Stacks"

    local projects=("mercai" "stockpredict" "mathematic" "stock_microservices")

    # Also explicitly stop Ollama container if running
    if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q "stock_ollama"; then
        print_color $BLUE "Removing Ollama container (stock_ollama)..."
        docker rm -f stock_ollama 2>/dev/null || true
        print_color $GREEN "✓ Ollama container removed"
    fi

    for project in "${projects[@]}"; do
        local containers=$(docker ps -aq --filter "label=com.docker.compose.project=$project" 2>/dev/null)
        if [ -n "$containers" ]; then
            print_color $BLUE "Removing $project stack..."
            docker rm -f $containers 2>/dev/null || true
            print_color $GREEN "✓ $project stack removed"
        fi
    done

    print_color $GREEN "✓ All compose stacks processed"
}

# Function to remove all Docker networks (except default ones)
remove_docker_networks() {
    print_header "Removing Docker Networks"

    print_color $BLUE "Removing custom networks..."
    docker network prune -f 2>/dev/null || true

    # Remove project-specific networks
    local networks=$(docker network ls --filter "type=custom" -q 2>/dev/null)
    if [ -n "$networks" ]; then
        for network in $networks; do
            docker network rm $network 2>/dev/null || true
        done
    fi

    print_color $GREEN "✓ Custom networks removed"
}

# Function to remove all Docker volumes
remove_docker_volumes() {
    print_header "Removing Docker Volumes"

    if ask_yes_no "This will DELETE ALL DATA in Docker volumes. Continue?"; then
        print_color $BLUE "Removing volumes..."
        docker volume prune -f 2>/dev/null || true

        # Remove any remaining volumes
        local volumes=$(docker volume ls -q 2>/dev/null)
        if [ -n "$volumes" ]; then
            docker volume rm $volumes 2>/dev/null || true
        fi

        print_color $GREEN "✓ All volumes removed"
    else
        print_color $YELLOW "○ Skipping volume removal"
    fi
}

# Function to remove dangling images
remove_dangling_images() {
    print_header "Removing Dangling Docker Images"

    print_color $BLUE "Removing dangling images..."
    docker image prune -f 2>/dev/null || true
    print_color $GREEN "✓ Dangling images removed"
}

# Function to remove all Docker images (optional)
remove_all_images() {
    print_header "Removing All Docker Images"

    if ask_yes_no "Remove ALL Docker images? (This will require rebuilding)"; then
        print_color $BLUE "Removing all images..."
        local images=$(docker images -q 2>/dev/null)
        if [ -n "$images" ]; then
            docker rmi -f $images 2>/dev/null || true
        fi
        print_color $GREEN "✓ All images removed"
    else
        print_color $YELLOW "○ Skipping image removal"
    fi
}

# Function to kill process on a specific port
kill_port() {
    local port=$1
    local pids=""

    # Try different methods to find processes using the port
    if command -v lsof &> /dev/null; then
        pids=$(lsof -ti:$port 2>/dev/null || true)
    elif command -v ss &> /dev/null; then
        pids=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP '(?<=pid=)\d+' | sort -u || true)
    elif command -v netstat &> /dev/null; then
        pids=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | sort -u || true)
    elif command -v fuser &> /dev/null; then
        pids=$(fuser $port/tcp 2>/dev/null || true)
    fi

    if [ -n "$pids" ]; then
        for pid in $pids; do
            if [ -n "$pid" ] && [ "$pid" != "-" ]; then
                print_color $BLUE "  Killing process $pid on port $port..."
                kill -9 $pid 2>/dev/null || sudo kill -9 $pid 2>/dev/null || true
            fi
        done
        return 0
    fi
    return 1
}

# Function to kill all processes on deployment ports
kill_all_ports() {
    print_header "Killing Processes on Deployment Ports"

    local killed_count=0

    for port in "${DEPLOYMENT_PORTS[@]}"; do
        if kill_port $port; then
            print_color $GREEN "  ✓ Port $port cleared"
            ((killed_count++))
        fi
    done

    if [ $killed_count -eq 0 ]; then
        print_color $YELLOW "○ No processes found on deployment ports"
    else
        print_color $GREEN "✓ Cleared $killed_count port(s)"
    fi
}

# Function to show port status
show_port_status() {
    print_header "Checking Port Status"

    local ports_in_use=()

    for port in "${DEPLOYMENT_PORTS[@]}"; do
        local in_use=false

        if command -v lsof &> /dev/null; then
            if lsof -i:$port -sTCP:LISTEN &>/dev/null; then
                in_use=true
            fi
        elif command -v ss &> /dev/null; then
            if ss -tln "sport = :$port" 2>/dev/null | grep -q LISTEN; then
                in_use=true
            fi
        elif command -v netstat &> /dev/null; then
            if netstat -tln 2>/dev/null | grep -q ":$port "; then
                in_use=true
            fi
        fi

        if [ "$in_use" = true ]; then
            ports_in_use+=($port)
        fi
    done

    if [ ${#ports_in_use[@]} -eq 0 ]; then
        print_color $GREEN "✓ All deployment ports are free!"
    else
        print_color $RED "⚠ The following ports are still in use:"
        for port in "${ports_in_use[@]}"; do
            print_color $YELLOW "  - Port $port"
        done
    fi
}

# Function to remove Ollama data (volume and images)
remove_ollama_data() {
    print_header "Removing Ollama LLM Data"

    # Remove Ollama volume (contains downloaded models like llama3.1)
    local ollama_volume=$(docker volume ls -q 2>/dev/null | grep -i ollama || true)
    if [ -n "$ollama_volume" ]; then
        if ask_yes_no "Remove Ollama volume ($ollama_volume)? This deletes all downloaded models"; then
            print_color $BLUE "Removing Ollama volume..."
            docker volume rm $ollama_volume 2>/dev/null || true
            print_color $GREEN "✓ Ollama volume removed (models deleted)"
        else
            print_color $YELLOW "○ Keeping Ollama volume (models preserved)"
        fi
    else
        print_color $YELLOW "○ No Ollama volume found"
    fi

    # Remove Ollama Docker image
    local ollama_images=$(docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' 2>/dev/null | grep -i ollama || true)
    if [ -n "$ollama_images" ]; then
        if ask_yes_no "Remove Ollama Docker image(s)?"; then
            print_color $BLUE "Removing Ollama images..."
            docker images --format '{{.ID}}' 2>/dev/null | while read -r img_id; do
                docker inspect "$img_id" 2>/dev/null | grep -qi ollama && docker rmi -f "$img_id" 2>/dev/null || true
            done
            # Direct approach
            docker rmi -f $(docker images 'ollama/ollama' -q 2>/dev/null) 2>/dev/null || true
            print_color $GREEN "✓ Ollama images removed"
        else
            print_color $YELLOW "○ Keeping Ollama images"
        fi
    else
        print_color $YELLOW "○ No Ollama images found"
    fi
}

# Function to remove Docker build cache
remove_build_cache() {
    print_header "Removing Docker Build Cache"

    print_color $BLUE "Removing build cache..."
    docker builder prune -af 2>/dev/null || true
    print_color $GREEN "✓ Build cache removed"
}

# Function to run Docker system prune
docker_system_prune() {
    print_header "Docker System Cleanup"

    print_color $BLUE "Running Docker system prune..."
    docker system prune -af 2>/dev/null || true
    print_color $GREEN "✓ Docker system cleaned"
}

# Function to show final status
show_final_status() {
    print_header "Cleanup Complete - Final Status"

    echo
    print_color $MAGENTA "Docker Status:"
    echo

    # Container count
    local container_count=$(docker ps -aq 2>/dev/null | wc -l)
    if [ "$container_count" -eq 0 ]; then
        print_color $GREEN "  ✓ Containers: 0"
    else
        print_color $YELLOW "  ○ Containers: $container_count remaining"
    fi

    # Network count (excluding defaults)
    local network_count=$(docker network ls --filter "type=custom" -q 2>/dev/null | wc -l)
    if [ "$network_count" -eq 0 ]; then
        print_color $GREEN "  ✓ Custom Networks: 0"
    else
        print_color $YELLOW "  ○ Custom Networks: $network_count remaining"
    fi

    # Volume count
    local volume_count=$(docker volume ls -q 2>/dev/null | wc -l)
    if [ "$volume_count" -eq 0 ]; then
        print_color $GREEN "  ✓ Volumes: 0"
    else
        print_color $YELLOW "  ○ Volumes: $volume_count remaining"
    fi

    echo
    show_port_status

    echo
    print_color $CYAN "You can now run ./deploy-interactive.sh safely!"
    echo
}

# Main function
main() {
    clear
    print_header "Complete Docker & Port Cleanup"

    print_color $MAGENTA "This script will:"
    print_color $WHITE "  1. Stop and remove all Docker containers"
    print_color $WHITE "  2. Remove Docker Compose stacks (mercai, stock, ollama)"
    print_color $WHITE "  3. Remove Docker networks"
    print_color $WHITE "  4. Optionally remove Docker volumes (DATA LOSS!)"
    print_color $WHITE "  5. Remove dangling Docker images"
    print_color $WHITE "  6. Optionally remove Ollama data (models & images)"
    print_color $WHITE "  7. Optionally remove all Docker images"
    print_color $WHITE "  8. Remove Docker build cache"
    print_color $WHITE "  9. Kill processes on deployment ports"
    print_color $WHITE "  10. Run Docker system prune"
    echo

    if [ "$FORCE_MODE" = true ]; then
        print_color $YELLOW "Running in FORCE mode - skipping confirmations"
        echo
    fi

    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        print_color $RED "Error: Docker is not running!"
        print_color $YELLOW "Please start Docker first."
        exit 1
    fi

    check_permissions

    if ! ask_yes_no "Proceed with cleanup?"; then
        print_color $YELLOW "Cleanup cancelled."
        exit 0
    fi

    # Execute cleanup steps
    stop_all_containers
    remove_compose_stacks
    remove_all_containers
    remove_docker_networks
    remove_docker_volumes
    remove_dangling_images
    remove_ollama_data
    remove_all_images
    remove_build_cache
    kill_all_ports
    docker_system_prune

    # Show final status
    show_final_status
}

# Run main function
main "$@"
