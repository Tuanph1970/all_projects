#!/bin/bash

# ============================================================================
# Interactive Multi-Project Deployment Script
# ============================================================================
# This script provides an interactive dialog-based deployment for:
#   - Ceramic Mobile App Backend
#   - Stock Predict Backend
#   - Mathematic Mobile Backend
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
NC='\033[0m' # No Color

# Project directories
# BASE_DIR="/home/tuanph/all_projects"
BASE_DIR="/home/home/all_projects"
CERAMIC_DIR="$BASE_DIR/ceramic_mobile_app/back_end"
# STOCK_DIR="$BASE_DIR/stockpredict/webapi"
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
                     "API Port: 8080 | DB Port: 3309"
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

# Function to create docker compose override file
create_compose_override() {
    local project=$1
    
    case $project in
        ceramic)
            cat > "$CERAMIC_DIR/docker-compose.override.yml" <<EOF
version: '3.8'

services:
  api:
    ports:
      - "\${CERAMIC_API_PORT:-8002}:8002"
    environment:
      - DB_NAME=\${CERAMIC_DB_NAME}
      - DB_USER=\${CERAMIC_DB_USER}
      - DB_PASSWORD=\${CERAMIC_DB_PASSWORD}
      - DB_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}
  
  db:
    ports:
      - "\${CERAMIC_DB_PORT:-3308}:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=\${CERAMIC_DB_NAME}
      - MYSQL_USER=\${CERAMIC_DB_USER}
      - MYSQL_PASSWORD=\${CERAMIC_DB_PASSWORD}
  
  redis:
    ports:
      - "\${CERAMIC_REDIS_PORT:-6379}:6379"
  
  nginx:
    ports:
      - "8082:80"
EOF
            ;;
            
        stock)
            cat > "$STOCK_DIR/docker-compose.override.yml" <<EOF
version: '3.8'

services:
  stockapi:
    ports:
      - "\${STOCK_API_PORT:-8080}:8000"
    environment:
      - DATABASE_URL=mysql://\${STOCK_DB_USER}:\${STOCK_DB_PASSWORD}@stock_mysql:\${STOCK_DB_PORT}/\${STOCK_DB_NAME}
    depends_on:
      - stock_mysql

  stock_mysql:
    image: mysql:8.0
    container_name: stock_mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=\${STOCK_DB_NAME}
      - MYSQL_USER=\${STOCK_DB_USER}
      - MYSQL_PASSWORD=\${STOCK_DB_PASSWORD}
    ports:
      - "\${STOCK_DB_PORT:-3309}:3306"
    volumes:
      - stock_mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p\${MYSQL_ROOT_PASSWORD}"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  stock_mysql_data:
EOF
            ;;
            
        math)
            cat > "$MATH_DIR/docker-compose.override.yml" <<EOF
version: '3.8'

services:
  mathematics-solver-api:
    ports:
      - "\${MATH_API_PORT:-8003}:8001"
    environment:
      - ConnectionStrings__DefaultConnection=Server=mysql;Database=\${MATH_DB_NAME};User=\${MATH_DB_USER};Password=\${MATH_DB_PASSWORD};
  
  mysql:
    ports:
      - "\${MATH_DB_PORT:-3310}:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=\${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=\${MATH_DB_NAME}
      - MYSQL_USER=\${MATH_DB_USER}
      - MYSQL_PASSWORD=\${MATH_DB_PASSWORD}
    volumes:
      - ./scripts/init-multi-user.sql:/docker-entrypoint-initdb.d/00-init-multi-user.sql:ro
  
  redis:
    ports:
      - "\${MATH_REDIS_PORT:-6380}:6379"
EOF
            ;;
    esac
}

# Function to deploy a project
deploy_project() {
    local project=$1
    local project_dir=""
    local compose_file=""
    local project_name=""
    
    case $project in
        ceramic)
            project_dir="$CERAMIC_DIR"
            compose_file="docker-compose.yml"
            project_name="ceramic"
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
    
    print_color $BLUE "📦 Deploying $project_name..."
    
    cd "$project_dir"
    
    # Create custom docker compose override
    create_compose_override "$project"
    
    # Build if requested
    if [ -n "$BUILD_FLAG" ]; then
        print_color $YELLOW "🔨 Building images..."
        docker compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" build
    fi
    
    # Start services
    print_color $YELLOW "🚀 Starting services..."
    docker compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" up -d
    
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
    
    # Check Docker
    print_color $BLUE "🔍 Checking Docker..."
    check_docker
    print_color $GREEN "✓ Docker is running"
    
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
            print_color $YELLOW "  • Ceramic API: http://localhost:8002"
            print_color $YELLOW "    Documentation: http://localhost:8002/docs"
        fi
        
        if [[ " ${SELECTED_PROJECTS[@]} " =~ " stock " ]]; then
            print_color $YELLOW "  • Stock API: http://localhost:8080"
            print_color $YELLOW "    API Endpoint: http://localhost:8080/stock/api/"
        fi
        
        if [[ " ${SELECTED_PROJECTS[@]} " =~ " math " ]]; then
            print_color $YELLOW "  • Mathematics API: http://localhost:8003"
            print_color $YELLOW "    Swagger: http://localhost:8003/swagger"
        fi
        
        echo
        print_color $CYAN "To check the status of your services, run:"
        print_color $WHITE "  ./deploy-projects.sh status"
        echo
        print_color $CYAN "To view logs, run:"
        print_color $WHITE "  ./deploy-projects.sh logs [project_name]"
        echo
    else
        print_color $YELLOW "Deployment cancelled."
    fi
}

# Run main function
main