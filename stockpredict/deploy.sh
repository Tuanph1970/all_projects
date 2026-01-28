#!/bin/bash

# =============================================================================
# Stock Predict Full-Stack Deployment Script
# =============================================================================
# Deploys Backend API, Frontend React, MySQL and all supporting services
#
# Usage:
#   ./deploy.sh              # Deploy all services
#   ./deploy.sh --build      # Build images before deploying
#   ./deploy.sh --stop       # Stop all services
#   ./deploy.sh --status     # Show service status
#   ./deploy.sh --logs       # Show logs
#   ./deploy.sh --clean      # Stop and remove all data
#
# Port Allocation:
#   - Frontend:    3004
#   - API Gateway: 8004
#   - MySQL:       3309
#   - Redis:       6382
#   - RabbitMQ:    5674/15674
#   - Grafana:     3100
#   - Prometheus:  9094
#   - Jaeger:      16686
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

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="stockpredict"
COMPOSE_FILE="docker-compose.full-stack.yml"

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

# Detect docker compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        print_error "Docker Compose is not installed"
        exit 1
    fi
}

COMPOSE_CMD=$(get_compose_cmd)

# Check Docker
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running!"
        print_warning "Please start Docker and try again."
        exit 1
    fi
    print_success "Docker is running"
}

# Create .env file if not exists
create_env_file() {
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            print_success "Created .env file from .env.example"
            print_warning "Please review and update .env with your settings"
        fi
    fi
}

# Deploy services
deploy() {
    local build_flag=""
    if [ "$1" == "--build" ]; then
        build_flag="--build"
        print_info "Building images before deployment..."
    fi

    print_header "Deploying Stock Predict Full-Stack"

    check_docker
    create_env_file

    cd "$SCRIPT_DIR"

    print_info "Starting services..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d $build_flag

    print_success "Deployment complete!"
    show_endpoints
}

# Stop services
stop() {
    print_header "Stopping Stock Predict Services"
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    print_success "All services stopped"
}

# Show status
status() {
    print_header "Stock Predict Service Status"
    cd "$SCRIPT_DIR"
    $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
}

# Show logs
logs() {
    local service=$1
    cd "$SCRIPT_DIR"
    if [ -n "$service" ]; then
        $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f "$service"
    else
        $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
    fi
}

# Clean up everything
clean() {
    print_header "Cleaning Stock Predict Deployment"
    print_warning "This will remove all containers and volumes!"
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        cd "$SCRIPT_DIR"
        $COMPOSE_CMD -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down -v --remove-orphans
        print_success "Cleanup complete"
    else
        print_info "Cleanup cancelled"
    fi
}

# Show endpoints
show_endpoints() {
    echo
    echo -e "${WHITE}┌─────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${WHITE}│                    Stock Predict Services                    │${NC}"
    echo -e "${WHITE}├─────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${YELLOW}│ Frontend App:       http://localhost:3004                   │${NC}"
    echo -e "${YELLOW}│ API Gateway:        http://localhost:8004                   │${NC}"
    echo -e "${YELLOW}│ Traefik Dashboard:  http://localhost:8084                   │${NC}"
    echo -e "${WHITE}├─────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│ API Endpoints:                                              │${NC}"
    echo -e "${CYAN}│   Auth:      http://localhost:8004/stock_helper/api/v2/auth │${NC}"
    echo -e "${CYAN}│   Stocks:    http://localhost:8004/stock_helper/api/v2/stocks│${NC}"
    echo -e "${CYAN}│   Portfolio: http://localhost:8004/stock_helper/api/v2/portfolio│${NC}"
    echo -e "${CYAN}│   Analysis:  http://localhost:8004/stock_helper/api/v2/analysis│${NC}"
    echo -e "${WHITE}├─────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${GREEN}│ Monitoring:                                                 │${NC}"
    echo -e "${GREEN}│   Grafana:     http://localhost:3100     (admin/admin)      │${NC}"
    echo -e "${GREEN}│   Prometheus:  http://localhost:9094                        │${NC}"
    echo -e "${GREEN}│   Jaeger:      http://localhost:16686                       │${NC}"
    echo -e "${GREEN}│   RabbitMQ:    http://localhost:15674    (stockuser/stockpass)│${NC}"
    echo -e "${WHITE}├─────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${BLUE}│ Database:                                                   │${NC}"
    echo -e "${BLUE}│   MySQL:       localhost:3309                               │${NC}"
    echo -e "${BLUE}│   Redis:       localhost:6382                               │${NC}"
    echo -e "${WHITE}└─────────────────────────────────────────────────────────────┘${NC}"
    echo
}

# Help
show_help() {
    echo "Stock Predict Full-Stack Deployment Script"
    echo
    echo "Usage: $0 [command]"
    echo
    echo "Commands:"
    echo "  (none)       Deploy all services"
    echo "  --build      Build images before deploying"
    echo "  --stop       Stop all services"
    echo "  --status     Show service status"
    echo "  --logs [svc] Show logs (optionally for specific service)"
    echo "  --clean      Stop and remove all data"
    echo "  --help       Show this help"
    echo
    echo "Examples:"
    echo "  $0                  # Deploy all services"
    echo "  $0 --build          # Build and deploy"
    echo "  $0 --logs frontend  # Show frontend logs"
    echo
}

# Main
case "$1" in
    --build)
        deploy --build
        ;;
    --stop)
        stop
        ;;
    --status)
        status
        ;;
    --logs)
        logs "$2"
        ;;
    --clean)
        clean
        ;;
    --help|-h)
        show_help
        ;;
    "")
        deploy
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
