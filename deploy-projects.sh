#!/bin/bash

# ============================================================================
# Multi-Project Deployment Script
# ============================================================================
# This script manages the deployment of multiple backend projects:
#   - Ceramic Mobile App Backend
#   - Stock Predict Backend
#   - Mathematic Mobile Backend
#
# Usage: ./deploy-projects.sh [command] [project1] [project2] ... [options]
#   Commands: start, stop, restart, status, logs
#   Projects: ceramic, stock, math, all
#   Options: --local, --production, --build, --no-cache
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
BASE_DIR="/home/tuanph/all_projects"
CERAMIC_DIR="$BASE_DIR/ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stockpredict/webapi"
MATH_DIR="$BASE_DIR/mathematic-mobile/backend"

# Environment files
ENV_FILE="$BASE_DIR/.deploy-env"

# Default values
COMMAND=""
PROJECTS=()
ENVIRONMENT="local"
BUILD_FLAG=""
CACHE_FLAG=""

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

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_color $RED "Error: Docker is not running!"
        exit 1
    fi
}

# Function to create environment file if not exists
create_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_header "Creating default environment file"
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
        print_color $GREEN "Environment file created at: $ENV_FILE"
        print_color $YELLOW "Please review and update the configuration as needed."
    fi
}

# Function to load environment variables
load_env() {
    if [ -f "$ENV_FILE" ]; then
        export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    fi
}

# Function to start a project
start_project() {
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
        *)
            print_color $RED "Unknown project: $project"
            return 1
            ;;
    esac
    
    print_color $BLUE "Starting $project_name..."
    
    cd "$project_dir"
    
    # Create custom docker-compose override
    create_compose_override "$project"
    
    # Build if requested
    if [ -n "$BUILD_FLAG" ]; then
        docker-compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" build $CACHE_FLAG
    fi
    
    # Start services
    docker-compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" up -d
    
    print_color $GREEN "$project_name started successfully!"
}

# Function to stop a project
stop_project() {
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
        *)
            print_color $RED "Unknown project: $project"
            return 1
            ;;
    esac
    
    print_color $BLUE "Stopping $project_name..."
    
    cd "$project_dir"
    
    if [ -f "docker-compose.override.yml" ]; then
        docker-compose -f "$compose_file" -f docker-compose.override.yml -p "$project_name" down
    else
        docker-compose -f "$compose_file" -p "$project_name" down
    fi
    
    print_color $GREEN "$project_name stopped successfully!"
}

# Function to show project status
show_project_status() {
    local project=$1
    local project_name=""
    
    case $project in
        ceramic)
            project_name="ceramic"
            ;;
        stock)
            project_name="stockpredict"
            ;;
        math)
            project_name="mathematic"
            ;;
        *)
            print_color $RED "Unknown project: $project"
            return 1
            ;;
    esac
    
    print_color $BLUE "Status for $project_name:"
    docker ps -a --filter "label=com.docker.compose.project=$project_name" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# Function to show project logs
show_project_logs() {
    local project=$1
    local project_name=""
    
    case $project in
        ceramic)
            project_name="ceramic"
            ;;
        stock)
            project_name="stockpredict"
            ;;
        math)
            project_name="mathematic"
            ;;
        *)
            print_color $RED "Unknown project: $project"
            return 1
            ;;
    esac
    
    print_color $BLUE "Logs for $project_name (last 100 lines):"
    docker-compose -p "$project_name" logs --tail 100 -f
}

# Function to create docker-compose override file
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

# Function to parse command line arguments
parse_args() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi
    
    COMMAND=$1
    shift
    
    while [ $# -gt 0 ]; do
        case $1 in
            --local)
                ENVIRONMENT="local"
                ;;
            --production|--prod)
                ENVIRONMENT="production"
                ;;
            --build)
                BUILD_FLAG="--build"
                ;;
            --no-cache)
                CACHE_FLAG="--no-cache"
                ;;
            all)
                PROJECTS=("ceramic" "stock" "math")
                ;;
            ceramic|stock|math)
                PROJECTS+=("$1")
                ;;
            *)
                print_color $RED "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
        shift
    done
    
    # Default to all projects if none specified
    if [ ${#PROJECTS[@]} -eq 0 ]; then
        PROJECTS=("ceramic" "stock" "math")
    fi
}

# Function to show usage
show_usage() {
    cat <<EOF
Multi-Project Deployment Script

Usage: $0 [command] [project1] [project2] ... [options]

Commands:
  start     Start the specified projects
  stop      Stop the specified projects
  restart   Restart the specified projects
  status    Show status of the specified projects
  logs      Show logs for the specified projects

Projects:
  ceramic   Ceramic Mobile App Backend
  stock     Stock Predict Backend
  math      Mathematic Mobile Backend
  all       All projects

Options:
  --local        Use local environment settings
  --production   Use production environment settings
  --build        Build images before starting
  --no-cache     Build without cache

Examples:
  $0 start all              # Start all projects
  $0 start ceramic stock    # Start ceramic and stock projects
  $0 stop math             # Stop math project
  $0 restart all --build   # Rebuild and restart all projects
  $0 status                # Show status of all projects
  $0 logs ceramic          # Show logs for ceramic project
EOF
}

# Main execution
main() {
    print_header "Multi-Project Deployment Manager"
    
    # Parse arguments
    parse_args "$@"
    
    # Check Docker
    check_docker
    
    # Create and load environment
    create_env_file
    load_env
    
    # Execute command
    case $COMMAND in
        start)
            print_header "Starting Projects"
            for project in "${PROJECTS[@]}"; do
                start_project "$project"
                echo
            done
            ;;
        stop)
            print_header "Stopping Projects"
            for project in "${PROJECTS[@]}"; do
                stop_project "$project"
                echo
            done
            ;;
        restart)
            print_header "Restarting Projects"
            for project in "${PROJECTS[@]}"; do
                stop_project "$project"
                echo
                start_project "$project"
                echo
            done
            ;;
        status)
            print_header "Project Status"
            for project in "${PROJECTS[@]}"; do
                show_project_status "$project"
                echo
            done
            ;;
        logs)
            if [ ${#PROJECTS[@]} -ne 1 ]; then
                print_color $RED "Please specify exactly one project for logs"
                exit 1
            fi
            show_project_logs "${PROJECTS[0]}"
            ;;
        *)
            print_color $RED "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
    
    print_color $GREEN "Operation completed successfully!"
}

# Run main function
main "$@"