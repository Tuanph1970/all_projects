#!/bin/bash
# =============================================================================
# Ceramic Marketplace - Microservices Deployment Script
# =============================================================================
# Usage: ./deploy-microservices.sh [command] [options]
#
# Commands:
#   start       Start all microservices
#   stop        Stop all microservices
#   restart     Restart all microservices
#   build       Build all microservices
#   status      Show service status
#   logs        View service logs
#   health      Run health check
#   update      Pull latest and redeploy
#   clean       Clean unused Docker resources
#
# Options:
#   -s, --service NAME    Target specific service
#   -m, --monitoring      Include monitoring stack
#   -f, --force           Force rebuild (no cache)
#   -h, --help            Show help
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
COMPOSE_FILE="docker-compose.yml"
MONITORING_FILE="docker-compose.monitoring.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default options
SERVICE=""
WITH_MONITORING=false
FORCE_BUILD=false
DOCKER_COMPOSE=""  # Set by check_docker()

# =============================================================================
# Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
Ceramic Marketplace - Microservices Deployment Script

Usage: $0 [command] [options]

Commands:
  start       Start all microservices
  stop        Stop all microservices
  restart     Restart all microservices
  build       Build all microservices
  status      Show service status
  logs        View service logs
  health      Run health check
  update      Pull latest and redeploy
  clean       Clean unused Docker resources

Options:
  -s, --service NAME    Target specific service (auth-service, product-service, order-service, chat-service, seller-service)
  -m, --monitoring      Include monitoring stack (Prometheus, Grafana, etc.)
  -f, --force           Force rebuild (no cache)
  -h, --help            Show help

Services:
  - traefik         API Gateway (port 8002)
  - auth-service    Authentication & User Management
  - product-service Product Catalog & Search
  - order-service   Cart & Orders
  - chat-service    Real-time Messaging
  - seller-service  Seller Dashboard & Analytics
  - db              MySQL Database
  - redis           Redis Cache

Examples:
  $0 start                    # Start all microservices
  $0 start -m                 # Start with monitoring stack
  $0 restart -s auth-service  # Restart auth service only
  $0 logs -s product-service  # View product service logs
  $0 build -f                 # Force rebuild all services
EOF
}

get_compose_files() {
    local files="-f $COMPOSE_FILE"
    if [ "$WITH_MONITORING" = true ]; then
        files="$files -f $MONITORING_FILE"
    fi
    echo "$files"
}

check_env() {
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        log_warning ".env file not found!"
        if [ -f "$PROJECT_DIR/.env.microservices" ]; then
            log_info "Creating from .env.microservices..."
            cp "$PROJECT_DIR/.env.microservices" "$PROJECT_DIR/.env"
        elif [ -f "$PROJECT_DIR/.env.example" ]; then
            log_info "Creating from .env.example..."
            cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        fi
        log_warning "Please update .env with your settings before deploying!"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check for Docker Compose (v2 plugin or legacy standalone)
    if docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    elif command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi
}

do_start() {
    log_info "Starting microservices..."
    cd "$PROJECT_DIR"
    check_env
    check_docker

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        $DOCKER_COMPOSE $compose_files up -d "$SERVICE"
        log_success "Started $SERVICE"
    else
        # Start infrastructure first
        log_info "Starting infrastructure (db, redis)..."
        $DOCKER_COMPOSE $compose_files up -d db redis

        log_info "Waiting for database to be ready..."
        sleep 10

        # Check if db is healthy
        local max_attempts=30
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if $DOCKER_COMPOSE $compose_files exec -T db mysqladmin ping -h localhost --silent 2>/dev/null; then
                log_success "Database is ready!"
                break
            fi
            attempt=$((attempt + 1))
            log_info "Waiting for database... ($attempt/$max_attempts)"
            sleep 2
        done

        if [ $attempt -eq $max_attempts ]; then
            log_warning "Database may not be ready, continuing anyway..."
        fi

        # Start all services
        log_info "Starting all microservices..."
        $DOCKER_COMPOSE $compose_files up -d

        log_success "All microservices started!"
    fi

    # Show status
    echo ""
    $DOCKER_COMPOSE $compose_files ps

    # Show access URLs
    echo ""
    log_info "Access URLs:"
    echo "  API Gateway:    http://localhost:8002"
    echo "  Traefik Dashboard: http://localhost:8080"
    echo "  Auth API:       http://localhost:8002/api/v1/auth"
    echo "  Products API:   http://localhost:8002/api/v1/products"
    echo "  Orders API:     http://localhost:8002/api/v1/orders"
    echo "  Chat API:       http://localhost:8002/api/v1/chat"
    echo "  Seller API:     http://localhost:8002/api/v1/seller"
}

do_stop() {
    log_info "Stopping microservices..."
    cd "$PROJECT_DIR"
    check_docker

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        $DOCKER_COMPOSE $compose_files stop "$SERVICE"
        log_success "Stopped $SERVICE"
    else
        $DOCKER_COMPOSE $compose_files down
        log_success "All microservices stopped!"
    fi
}

do_restart() {
    log_info "Restarting microservices..."
    cd "$PROJECT_DIR"
    check_docker

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        $DOCKER_COMPOSE $compose_files restart "$SERVICE"
        log_success "Restarted $SERVICE"
    else
        $DOCKER_COMPOSE $compose_files restart
        log_success "All microservices restarted!"
    fi
}

do_build() {
    log_info "Building microservices..."
    cd "$PROJECT_DIR"
    check_env
    check_docker

    local compose_files=$(get_compose_files)
    local build_args=""

    if [ "$FORCE_BUILD" = true ]; then
        build_args="--no-cache"
        log_info "Force rebuilding (no cache)..."
    fi

    if [ -n "$SERVICE" ]; then
        $DOCKER_COMPOSE $compose_files build $build_args "$SERVICE"
        log_success "Built $SERVICE"
    else
        $DOCKER_COMPOSE $compose_files build $build_args
        log_success "All microservices built!"
    fi
}

do_status() {
    cd "$PROJECT_DIR"
    check_docker
    local compose_files=$(get_compose_files)

    echo ""
    log_info "Microservice Status:"
    echo "============================================="
    $DOCKER_COMPOSE $compose_files ps
    echo ""

    # Run health check script if available
    if [ -x "$PROJECT_DIR/scripts/health_check.sh" ]; then
        "$PROJECT_DIR/scripts/health_check.sh"
    fi
}

do_logs() {
    cd "$PROJECT_DIR"
    check_docker
    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        $DOCKER_COMPOSE $compose_files logs -f --tail=100 "$SERVICE"
    else
        $DOCKER_COMPOSE $compose_files logs -f --tail=100
    fi
}

do_health() {
    log_info "Running health check..."

    if [ -x "$PROJECT_DIR/scripts/health_check.sh" ]; then
        "$PROJECT_DIR/scripts/health_check.sh" -v
    else
        # Basic health check
        echo ""
        log_info "Checking service health..."

        services=("auth-service:8001" "product-service:8002" "order-service:8003" "chat-service:8004" "seller-service:8005")

        for service_port in "${services[@]}"; do
            service="${service_port%%:*}"
            port="${service_port##*:}"

            container_name="ceramic_${service//-/_}"
            if docker exec "$container_name" curl -sf "http://localhost:$port/health" > /dev/null 2>&1; then
                echo -e "  ${GREEN}✓${NC} $service is healthy"
            else
                echo -e "  ${RED}✗${NC} $service is not responding"
            fi
        done
    fi
}

do_update() {
    log_info "Updating deployment..."
    cd "$PROJECT_DIR"
    check_docker

    local compose_files=$(get_compose_files)

    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        log_info "Pulling latest code..."
        git pull
    fi

    # Rebuild and restart
    log_info "Rebuilding microservices..."
    $DOCKER_COMPOSE $compose_files build

    log_info "Restarting microservices..."
    $DOCKER_COMPOSE $compose_files up -d

    log_success "Update complete!"
    do_health
}

do_clean() {
    log_warning "This will remove unused Docker resources."
    read -p "Continue? (y/N) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cleaning Docker resources..."
        docker system prune -f
        docker volume prune -f
        log_success "Cleanup complete!"
    else
        log_info "Cleanup cancelled."
    fi
}

# =============================================================================
# Main
# =============================================================================

# Parse command
COMMAND="${1:-}"
shift || true

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -m|--monitoring)
            WITH_MONITORING=true
            shift
            ;;
        -f|--force)
            FORCE_BUILD=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    build)
        do_build
        ;;
    status)
        do_status
        ;;
    logs)
        do_logs
        ;;
    health)
        do_health
        ;;
    update)
        do_update
        ;;
    clean)
        do_clean
        ;;
    ""|help)
        show_help
        ;;
    *)
        log_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
