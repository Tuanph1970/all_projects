#!/bin/bash
# =============================================================================
# Ceramic Marketplace - Deployment Script
# =============================================================================
# Usage: ./scripts/deploy.sh [command] [options]
#
# Commands:
#   start       Start all services
#   stop        Stop all services
#   restart     Restart all services
#   build       Build all services
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
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="docker-compose.microservices.yml"
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

# =============================================================================
# Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
Ceramic Marketplace - Deployment Script

Usage: $0 [command] [options]

Commands:
  start       Start all services
  stop        Stop all services
  restart     Restart all services
  build       Build all services
  status      Show service status
  logs        View service logs
  health      Run health check
  update      Pull latest and redeploy
  clean       Clean unused Docker resources

Options:
  -s, --service NAME    Target specific service
  -m, --monitoring      Include monitoring stack
  -f, --force           Force rebuild (no cache)
  -h, --help            Show help

Examples:
  $0 start                    # Start all services
  $0 start -m                 # Start with monitoring
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
        log_info "Creating from .env.microservices..."
        cp "$PROJECT_DIR/.env.microservices" "$PROJECT_DIR/.env"
        log_warning "Please update .env with your settings before deploying!"
        exit 1
    fi
}

do_start() {
    log_info "Starting services..."
    cd "$PROJECT_DIR"
    check_env

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        docker-compose $compose_files up -d "$SERVICE"
        log_success "Started $SERVICE"
    else
        # Start infrastructure first
        log_info "Starting infrastructure (db, redis)..."
        docker-compose $compose_files up -d db redis

        log_info "Waiting for database to be ready..."
        sleep 10

        # Check if db is healthy
        local max_attempts=30
        local attempt=0
        while [ $attempt -lt $max_attempts ]; do
            if docker-compose $compose_files exec -T db mysqladmin ping -h localhost --silent 2>/dev/null; then
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
        log_info "Starting all services..."
        docker-compose $compose_files up -d

        log_success "All services started!"
    fi

    # Show status
    docker-compose $compose_files ps
}

do_stop() {
    log_info "Stopping services..."
    cd "$PROJECT_DIR"

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        docker-compose $compose_files stop "$SERVICE"
        log_success "Stopped $SERVICE"
    else
        docker-compose $compose_files down
        log_success "All services stopped!"
    fi
}

do_restart() {
    log_info "Restarting services..."
    cd "$PROJECT_DIR"

    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        docker-compose $compose_files restart "$SERVICE"
        log_success "Restarted $SERVICE"
    else
        docker-compose $compose_files restart
        log_success "All services restarted!"
    fi
}

do_build() {
    log_info "Building services..."
    cd "$PROJECT_DIR"
    check_env

    local compose_files=$(get_compose_files)
    local build_args=""

    if [ "$FORCE_BUILD" = true ]; then
        build_args="--no-cache"
        log_info "Force rebuilding (no cache)..."
    fi

    if [ -n "$SERVICE" ]; then
        docker-compose $compose_files build $build_args "$SERVICE"
        log_success "Built $SERVICE"
    else
        docker-compose $compose_files build $build_args
        log_success "All services built!"
    fi
}

do_status() {
    cd "$PROJECT_DIR"
    local compose_files=$(get_compose_files)

    echo ""
    log_info "Service Status:"
    echo "============================================="
    docker-compose $compose_files ps
    echo ""

    # Run detailed status script if available
    if [ -x "$SCRIPT_DIR/service_status.sh" ]; then
        "$SCRIPT_DIR/service_status.sh"
    fi
}

do_logs() {
    cd "$PROJECT_DIR"
    local compose_files=$(get_compose_files)

    if [ -n "$SERVICE" ]; then
        docker-compose $compose_files logs -f --tail=100 "$SERVICE"
    else
        docker-compose $compose_files logs -f --tail=100
    fi
}

do_health() {
    log_info "Running health check..."

    if [ -x "$SCRIPT_DIR/health_check.sh" ]; then
        "$SCRIPT_DIR/health_check.sh" -v
    else
        log_error "Health check script not found!"
        exit 1
    fi
}

do_update() {
    log_info "Updating deployment..."
    cd "$PROJECT_DIR"

    local compose_files=$(get_compose_files)

    # Pull latest code (if using git)
    if [ -d ".git" ]; then
        log_info "Pulling latest code..."
        git pull
    fi

    # Rebuild and restart
    log_info "Rebuilding services..."
    docker-compose $compose_files build

    log_info "Restarting services..."
    docker-compose $compose_files up -d

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
