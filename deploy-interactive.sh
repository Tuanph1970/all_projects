#!/bin/bash

# ============================================================================
# Interactive Multi-Project Deployment Script
# ============================================================================
# This script provides an interactive dialog-based deployment for:
#   - Ceramic Mobile App Backend (Port 8002)
#   - Stock Predict Backend (Port 8004)
#   - Mathematic Mobile Backend (Port 8003)
#
# Usage: ./deploy-interactive.sh
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

# Project directories (relative to BASE_DIR)
CERAMIC_DIR="$BASE_DIR/ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stockpredict/stock_microservices"
MATH_DIR="$BASE_DIR/mathematic-mobile/backend"

# Environment files
ENV_FILE="$BASE_DIR/.deploy-env"

# Deployment settings
BUILD_FLAG=""
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
    print_color $BLUE "┌─────────────────────────────────────────────────────────┐"
    printf "${BLUE}│${NC} %-55s ${BLUE}│${NC}\n" "$title"
    print_color $BLUE "├─────────────────────────────────────────────────────────┤"
    printf "${BLUE}│${NC} %-55s ${BLUE}│${NC}\n" "$content"
    print_color $BLUE "└─────────────────────────────────────────────────────────┘"
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
        print_color $YELLOW "Please start Docker and try again."
        exit 1
    fi
}

# Function to create environment file if not exists
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_header "Initial Setup"
        print_color $YELLOW "Creating default environment configuration..."
        
        cat > "$ENV_FILE" <<EOF
# ============================================================================
# Shared Environment Configuration for Multi-Project Deployment
# ============================================================================

# Database Root Password
MYSQL_ROOT_PASSWORD=Mysql_2025

# Ceramic Project Configuration
CERAMIC_API_PORT=8002
CERAMIC_DB_PORT=3308
CERAMIC_DB_NAME=ceramic_db
CERAMIC_DB_USER=ceramic_user
CERAMIC_DB_PASSWORD=Mysql_2025
CERAMIC_REDIS_PORT=6379

# Stock Predict Project Configuration
STOCK_API_PORT=8080
STOCK_DB_PORT=3309
STOCK_DB_NAME=stockpredict_db
STOCK_DB_USER=stock_user
STOCK_DB_PASSWORD=Mysql_2025

# Mathematic Mobile Project Configuration
MATH_API_PORT=8003
MATH_DB_PORT=3310
MATH_DB_NAME=mathematic_db
MATH_DB_USER=mathematic_user
MATH_DB_PASSWORD=Mysql_2025
MATH_REDIS_PORT=6380

# General Configuration
ENVIRONMENT=production
EOF
        print_color $GREEN "✓ Environment file created at: $ENV_FILE"
    fi
}

# Function to load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    fi
}

# Function to show project info
show_project_info() {
    local project=$1
    case $project in
        ceramic)
            print_box "Ceramic Mobile App Backend" \
                     "API Port: 8002 | DB Port: 3308 | Redis: 6379"
            ;;
        stock)
            print_box "Stock Predict Backend" \
                     "API Port: 8004 | Dashboard: 8084 | Grafana: 3100"
            ;;
        math)
            print_box "Mathematics Mobile Backend" \
                     "API Port: 8003 | DB Port: 3310 | Redis: 6380"
            ;;
    esac
}

# Function to check if project is already running
is_project_running() {
    local project_name=$1
    docker ps --filter "label=com.docker.compose.project=$project_name" --format "{{.Names}}" | grep -q .
}

# Function to get running status
get_project_status() {
    local project_name=$1
    if is_project_running "$project_name"; then
        echo "${GREEN}Running${NC}"
    else
        echo "${RED}Stopped${NC}"
    fi
}

# Function to check if project directory exists
check_project_dir() {
    local project=$1
    local dir=""

    case $project in
        ceramic) dir="$CERAMIC_DIR" ;;
        stock) dir="$STOCK_DIR" ;;
        math) dir="$MATH_DIR" ;;
    esac

    if [ ! -d "$dir" ]; then
        print_color $RED "Error: Project directory not found: $dir"
        return 1
    fi
    return 0
}

# Function to detect docker compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        print_color $RED "Error: Docker Compose is not installed"
        exit 1
    fi
}

COMPOSE_CMD=""

# Function to deploy a project
deploy_project() {
    local project=$1
    local project_dir=""
    local project_name=""
    local build_args=""

    # Check if project directory exists
    if ! check_project_dir "$project"; then
        print_color $RED "Skipping $project - directory not found"
        return 1
    fi

    case $project in
        ceramic)
            project_dir="$CERAMIC_DIR"
            project_name="ceramic"
            ;;
        stock)
            project_dir="$STOCK_DIR"
            project_name="stockpredict"
            ;;
        math)
            project_dir="$MATH_DIR"
            project_name="mathematic"
            ;;
    esac

    print_color $BLUE "📦 Deploying $project_name..."

    cd "$project_dir"

    # Build args based on BUILD_FLAG
    if [ -n "$BUILD_FLAG" ]; then
        build_args="--build"
        print_color $YELLOW "🔨 Building images..."
    fi

    # Deploy based on project type
    case $project in
        ceramic)
            # Ceramic uses its own deploy script or docker-compose
            if [ -f "docker-compose.yml" ]; then
                print_color $YELLOW "🚀 Starting Ceramic services..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose.yml not found in $project_dir"
                return 1
            fi
            ;;
        stock)
            # Stock has its own deploy script with local compose files
            if [ -f "docker-compose.yml" ] && [ -f "docker-compose.local.yml" ]; then
                print_color $YELLOW "🚀 Starting Stock services..."
                $COMPOSE_CMD -f docker-compose.yml -f docker-compose.local.yml -p "$project_name" up -d $build_args
            elif [ -f "docker-compose.yml" ]; then
                print_color $YELLOW "🚀 Starting Stock services (base only)..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose.yml not found in $project_dir"
                return 1
            fi
            ;;
        math)
            # Math uses docker-compose.yml
            if [ -f "docker-compose.yml" ]; then
                print_color $YELLOW "🚀 Starting Math services..."
                $COMPOSE_CMD -f docker-compose.yml -p "$project_name" up -d $build_args
            else
                print_color $RED "docker-compose.yml not found in $project_dir"
                return 1
            fi
            ;;
    esac

    print_color $GREEN "✓ $project_name deployed successfully!"
}

# Function to show deployment summary
show_deployment_summary() {
    print_header "Deployment Summary"
    
    echo
    print_color $MAGENTA "Selected Projects:"
    for project in "${SELECTED_PROJECTS[@]}"; do
        case $project in
            ceramic)
                print_color $GREEN "  ✓ Ceramic Mobile App Backend"
                ;;
            stock)
                print_color $GREEN "  ✓ Stock Predict Backend"
                ;;
            math)
                print_color $GREEN "  ✓ Mathematics Mobile Backend"
                ;;
        esac
    done
    
    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ]; then
        print_color $YELLOW "  No projects selected for deployment"
    fi
    
    echo
    print_color $MAGENTA "Build Option:"
    if [ -n "$BUILD_FLAG" ]; then
        print_color $GREEN "  ✓ Build images before deployment"
    else
        print_color $YELLOW "  ○ Use existing images"
    fi
    echo
}

# Main interactive flow
main() {
    clear
    print_header "Interactive Multi-Project Deployment"

    print_color $MAGENTA "Welcome to the Multi-Project Deployment Tool!"
    print_color $MAGENTA "This tool will help you deploy your backend services."
    echo

    # Show detected base directory
    print_color $CYAN "📂 Base directory: $BASE_DIR"
    echo

    # Check Docker
    print_color $BLUE "🔍 Checking Docker..."
    check_docker
    print_color $GREEN "✓ Docker is running"

    # Initialize compose command
    COMPOSE_CMD=$(get_compose_cmd)
    print_color $GREEN "✓ Docker Compose detected: $COMPOSE_CMD"
    
    # Create and load environment
    create_env_file
    load_env
    
    echo
    print_header "Project Status Overview"
    
    # Show current status
    print_color $CYAN "Current project status:"
    echo
    printf "  %-30s %s\n" "Ceramic Mobile App:" "$(get_project_status ceramic)"
    printf "  %-30s %s\n" "Stock Predict:" "$(get_project_status stockpredict)"
    printf "  %-30s %s\n" "Mathematics Mobile:" "$(get_project_status mathematic)"
    echo
    
    # Ask about deployment mode
    print_header "Deployment Configuration"
    
    # Ask about building
    if ask_yes_no "Do you want to build images before deployment?" "n"; then
        BUILD_FLAG="--build"
        print_color $GREEN "✓ Images will be built before deployment"
    else
        print_color $YELLOW "○ Using existing images"
    fi
    
    echo
    print_header "Project Selection"
    
    # Ask about each project
    # Ceramic
    show_project_info "ceramic"
    if ask_yes_no "Do you want to deploy Ceramic Mobile App Backend?" "y"; then
        SELECTED_PROJECTS+=("ceramic")
        print_color $GREEN "✓ Ceramic Mobile App Backend selected"
    else
        print_color $YELLOW "○ Skipping Ceramic Mobile App Backend"
    fi
    
    echo
    
    # Stock
    show_project_info "stock"
    if ask_yes_no "Do you want to deploy Stock Predict Backend?" "y"; then
        SELECTED_PROJECTS+=("stock")
        print_color $GREEN "✓ Stock Predict Backend selected"
    else
        print_color $YELLOW "○ Skipping Stock Predict Backend"
    fi
    
    echo
    
    # Mathematics
    show_project_info "math"
    if ask_yes_no "Do you want to deploy Mathematics Mobile Backend?" "y"; then
        SELECTED_PROJECTS+=("math")
        print_color $GREEN "✓ Mathematics Mobile Backend selected"
    else
        print_color $YELLOW "○ Skipping Mathematics Mobile Backend"
    fi
    
    # Show summary and confirm
    show_deployment_summary
    
    if [ ${#SELECTED_PROJECTS[@]} -eq 0 ]; then
        print_color $YELLOW "No projects selected. Exiting."
        exit 0
    fi
    
    if ask_yes_no "Proceed with deployment?" "y"; then
        print_header "Deploying Projects"
        
        for project in "${SELECTED_PROJECTS[@]}"; do
            echo
            deploy_project "$project"
        done
        
        echo
        print_header "Deployment Complete!"
        
        print_color $GREEN "All selected projects have been deployed successfully!"
        echo
        print_color $CYAN "Access your services at:"

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " ceramic " ]]; then
            echo
            print_color $WHITE "  ┌─ Ceramic Mobile App ─────────────────────────────────┐"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8002"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8080"
            print_color $YELLOW "  │ Auth API:           http://localhost:8002/api/v1/auth"
            print_color $YELLOW "  │ Products API:       http://localhost:8002/api/v1/products"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " stock " ]]; then
            echo
            print_color $WHITE "  ┌─ Stock Predict ──────────────────────────────────────┐"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8004"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8084"
            print_color $YELLOW "  │ Stock API:          http://localhost:8004/stock_helper/api/v2/"
            print_color $YELLOW "  │ Grafana:            http://localhost:3100"
            print_color $YELLOW "  │ RabbitMQ:           http://localhost:15672"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        if [[ " ${SELECTED_PROJECTS[@]} " =~ " math " ]]; then
            echo
            print_color $WHITE "  ┌─ Mathematics Mobile ─────────────────────────────────┐"
            print_color $YELLOW "  │ API Gateway:        http://localhost:8003"
            print_color $YELLOW "  │ Traefik Dashboard:  http://localhost:8083"
            print_color $YELLOW "  │ Auth API:           http://localhost:8003/api/v1/auth"
            print_color $YELLOW "  │ Problems API:       http://localhost:8003/api/v1/problems"
            print_color $YELLOW "  │ Solutions API:      http://localhost:8003/api/v1/solutions"
            print_color $WHITE "  └─────────────────────────────────────────────────────┘"
        fi

        echo
        print_color $CYAN "Port Allocation Summary:"
        print_color $WHITE "  Ceramic: 8002 | Math: 8003 | Stock: 8004"
        echo
        print_color $CYAN "To check the status of your services, run:"
        print_color $WHITE "  $SCRIPT_DIR/deploy-projects.sh status"
        echo
        print_color $CYAN "To view logs, run:"
        print_color $WHITE "  $SCRIPT_DIR/deploy-projects.sh logs [project_name]"
        echo
    else
        print_color $YELLOW "Deployment cancelled."
    fi
}

# Run main function
main