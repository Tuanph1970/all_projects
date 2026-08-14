#!/bin/bash
# =============================================================================
# Unified Local Deployment Script for All Projects
# =============================================================================
# This script deploys all projects using LOCAL MySQL database
#
# Usage:
#   ./deploy-local.sh              # Deploy all projects
#   ./deploy-local.sh mercai      # Deploy only Mercai app
#   ./deploy-local.sh stock        # Deploy only Stock projects
#   ./deploy-local.sh math         # Deploy only Mathematic project
#   ./deploy-local.sh --setup-db   # Setup MySQL databases first
#   ./deploy-local.sh --stop       # Stop all projects
#   ./deploy-local.sh --status     # Show status of all projects
#
# Prerequisites:
#   - Docker and docker-compose installed
#   - MySQL running locally (for database)
#   - Run with --setup-db first time to create databases
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERCAI_DIR="$BASE_DIR/mercai/back_end"
STOCK_MICRO_DIR="$BASE_DIR/stockpredict/stock_microservices"
MATH_DIR="$BASE_DIR/mathematic-mobile/backend"

# Docker compose command (will be set in check_prerequisites)
DOCKER_COMPOSE=""

# Print header
print_header() {
    echo -e "${BLUE}=============================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}=============================================${NC}"
}

# Print section
print_section() {
    echo ""
    echo -e "${CYAN}>>> $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_section "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker installed${NC}"

    # Check docker-compose (support both old and new syntax)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
        echo -e "${GREEN}✓ Docker Compose (v2) installed${NC}"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
        echo -e "${GREEN}✓ docker-compose installed${NC}"
    else
        echo -e "${RED}✗ docker-compose is not installed${NC}"
        exit 1
    fi

    # Check MySQL
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet mysql 2>/dev/null || systemctl is-active --quiet mariadb 2>/dev/null; then
            echo -e "${GREEN}✓ MySQL service is running${NC}"
        else
            echo -e "${YELLOW}⚠ MySQL service might not be running${NC}"
            echo -e "${YELLOW}  Run: sudo systemctl start mysql${NC}"
        fi
    fi
}

# Setup environment files
setup_env_files() {
    print_section "Setting up environment files..."

    # Mercai
    if [ -f "$MERCAI_DIR/.env.local" ] && [ ! -f "$MERCAI_DIR/.env" ]; then
        cp "$MERCAI_DIR/.env.local" "$MERCAI_DIR/.env"
        echo -e "${GREEN}✓ Created $MERCAI_DIR/.env${NC}"
    elif [ -f "$MERCAI_DIR/.env" ]; then
        echo -e "${YELLOW}⚡ $MERCAI_DIR/.env already exists${NC}"
    fi

    # Stock Microservices
    if [ -f "$STOCK_MICRO_DIR/.env.local" ] && [ ! -f "$STOCK_MICRO_DIR/.env" ]; then
        cp "$STOCK_MICRO_DIR/.env.local" "$STOCK_MICRO_DIR/.env"
        echo -e "${GREEN}✓ Created $STOCK_MICRO_DIR/.env${NC}"
    elif [ -f "$STOCK_MICRO_DIR/.env" ]; then
        echo -e "${YELLOW}⚡ $STOCK_MICRO_DIR/.env already exists${NC}"
    fi

    # Math
    if [ -f "$MATH_DIR/.env.local" ] && [ ! -f "$MATH_DIR/.env" ]; then
        cp "$MATH_DIR/.env.local" "$MATH_DIR/.env"
        echo -e "${GREEN}✓ Created $MATH_DIR/.env${NC}"
    elif [ -f "$MATH_DIR/.env" ]; then
        echo -e "${YELLOW}⚡ $MATH_DIR/.env already exists${NC}"
    fi
}

# Deploy Mercai
deploy_mercai() {
    print_section "Deploying Mercai..."
    cd "$MERCAI_DIR"

    if [ -f "docker-compose.local.yml" ]; then
        $DOCKER_COMPOSE -f docker-compose.local.yml up -d --build
    else
        $DOCKER_COMPOSE up -d --build
    fi

    echo -e "${GREEN}✓ Mercai deployed on port 8002${NC}"
}

# Deploy Stock Microservices
deploy_stock_microservices() {
    print_section "Deploying Stock Microservices..."
    cd "$STOCK_MICRO_DIR"

    # Use standalone local config (no merge needed)
    if [ -f "docker-compose.local.yml" ]; then
        $DOCKER_COMPOSE -f docker-compose.local.yml up -d --build
    else
        $DOCKER_COMPOSE up -d --build
    fi

    echo -e "${GREEN}✓ Stock Microservices deployed${NC}"
    echo -e "  - Traefik Gateway: http://localhost:8088"
    echo -e "  - Traefik Dashboard: http://localhost:8089"
    echo -e "  - Auth Service: http://localhost:8007"
    echo -e "  - Stock Data Service: http://localhost:8001"
}

# Deploy Mathematic Mobile
deploy_math() {
    print_section "Deploying Mathematic Mobile..."
    cd "$MATH_DIR"

    # Use standalone local config (no merge needed)
    if [ -f "docker-compose.local.yml" ]; then
        $DOCKER_COMPOSE -f docker-compose.local.yml up -d --build
    else
        $DOCKER_COMPOSE up -d --build
    fi

    echo -e "${GREEN}✓ Mathematic Mobile deployed on port 8003${NC}"
}

# Stop all projects
stop_all() {
    print_header "Stopping All Projects"

    # Detect docker compose command
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi

    print_section "Stopping Mercai..."
    cd "$MERCAI_DIR" && $DOCKER_COMPOSE down 2>/dev/null || true

    print_section "Stopping Stock Microservices..."
    cd "$STOCK_MICRO_DIR" && $DOCKER_COMPOSE down 2>/dev/null || true

    print_section "Stopping Mathematic Mobile..."
    cd "$MATH_DIR" && $DOCKER_COMPOSE down 2>/dev/null || true

    echo -e "${GREEN}✓ All projects stopped${NC}"
}

# Show status
show_status() {
    print_header "Project Status"

    # Detect docker compose command
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi

    echo ""
    echo -e "${YELLOW}Mercai:${NC}"
    cd "$MERCAI_DIR" && $DOCKER_COMPOSE ps 2>/dev/null || echo "  Not running"

    echo ""
    echo -e "${YELLOW}Stock Microservices:${NC}"
    cd "$STOCK_MICRO_DIR" && $DOCKER_COMPOSE ps 2>/dev/null || echo "  Not running"

    echo ""
    echo -e "${YELLOW}Mathematic Mobile:${NC}"
    cd "$MATH_DIR" && $DOCKER_COMPOSE ps 2>/dev/null || echo "  Not running"
}

# Print usage
print_usage() {
    echo "Usage: $0 [OPTIONS] [PROJECT]"
    echo ""
    echo "Projects:"
    echo "  mercai     Deploy only Mercai"
    echo "  stock       Deploy only Stock Microservices"
    echo "  math        Deploy only Mathematic Mobile"
    echo "  all         Deploy all projects (default)"
    echo ""
    echo "Options:"
    echo "  --setup-db  Setup MySQL databases before deploying"
    echo "  --stop      Stop all projects"
    echo "  --status    Show status of all projects"
    echo "  --help      Show this help message"
}

# Print summary
print_summary() {
    echo ""
    print_header "Deployment Summary"
    echo ""
    echo -e "${YELLOW}Services Deployed:${NC}"
    echo ""
    echo -e "${CYAN}Mercai:${NC}"
    echo "  - API: http://localhost:8002"
    echo ""
    echo -e "${CYAN}Stock Microservices:${NC}"
    echo "  - API Gateway: http://localhost:8088"
    echo "  - Traefik Dashboard: http://localhost:8089"
    echo "  - RabbitMQ Management: http://localhost:15672"
    echo "  - Grafana: http://localhost:3100"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Jaeger: http://localhost:16686"
    echo ""
    echo -e "${CYAN}Mathematic Mobile:${NC}"
    echo "  - API: http://localhost:8003"
    echo ""
    echo -e "${YELLOW}Database:${NC}"
    echo "  - MySQL: localhost:3306 (local)"
    echo ""
    echo -e "${GREEN}All projects are using LOCAL MySQL database!${NC}"
}

# Main execution
main() {
    print_header "Local Deployment Script"
    echo ""

    # Parse arguments
    SETUP_DB=false
    PROJECT="all"

    for arg in "$@"; do
        case $arg in
            --setup-db)
                SETUP_DB=true
                ;;
            --stop)
                stop_all
                exit 0
                ;;
            --status)
                show_status
                exit 0
                ;;
            --help)
                print_usage
                exit 0
                ;;
            mercai)
                PROJECT="mercai"
                ;;
            stock)
                PROJECT="stock"
                ;;
            math)
                PROJECT="math"
                ;;
            all)
                PROJECT="all"
                ;;
        esac
    done

    # Check prerequisites
    check_prerequisites

    # Setup database if requested
    if [ "$SETUP_DB" = true ]; then
        print_section "Setting up MySQL databases..."
        if [ -f "$BASE_DIR/setup-local-mysql.sh" ]; then
            bash "$BASE_DIR/setup-local-mysql.sh"
        else
            echo -e "${RED}✗ setup-local-mysql.sh not found${NC}"
            exit 1
        fi
    fi

    # Setup environment files
    setup_env_files

    # Deploy projects
    case $PROJECT in
        mercai)
            deploy_mercai
            ;;
        stock)
            deploy_stock_microservices
            ;;
        math)
            deploy_math
            ;;
        all)
            deploy_mercai
            deploy_stock_microservices
            deploy_math
            ;;
    esac

    # Print summary
    print_summary
}

# Run main
main "$@"
