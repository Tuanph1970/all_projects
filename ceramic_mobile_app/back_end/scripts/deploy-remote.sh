#!/bin/bash
# =============================================================================
# Ceramic Marketplace - Remote Deployment Script
# =============================================================================
# Deploys the application to a remote server
#
# Usage: ./scripts/deploy-remote.sh [options]
#
# Options:
#   -h, --host HOST       Server hostname/IP (default: 112.213.91.103)
#   -u, --user USER       SSH username (default: current user)
#   -p, --path PATH       Remote path (default: /opt/ceramic-marketplace)
#   -k, --key FILE        SSH key file
#   --build-only          Only build, don't deploy
#   --no-build            Skip building, just sync files
#   --help                Show help
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default settings
REMOTE_HOST="112.213.91.103"
REMOTE_USER="$USER"
REMOTE_PATH="/opt/ceramic-marketplace"
SSH_KEY=""
BUILD_ONLY=false
NO_BUILD=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =============================================================================
# Functions
# =============================================================================

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
Ceramic Marketplace - Remote Deployment Script

Usage: $0 [options]

Options:
  -h, --host HOST       Server hostname/IP (default: 112.213.91.103)
  -u, --user USER       SSH username (default: $USER)
  -p, --path PATH       Remote path (default: /opt/ceramic-marketplace)
  -k, --key FILE        SSH key file
  --build-only          Only build locally, don't deploy
  --no-build            Skip local build, just sync files
  --help                Show this help

Examples:
  $0                                    # Deploy to default server
  $0 -h myserver.com -u admin           # Deploy to custom server
  $0 --build-only                       # Build only
  $0 --no-build                         # Quick sync without rebuild
EOF
}

get_ssh_cmd() {
    local cmd="ssh"
    if [ -n "$SSH_KEY" ]; then
        cmd="$cmd -i $SSH_KEY"
    fi
    echo "$cmd"
}

get_scp_cmd() {
    local cmd="scp"
    if [ -n "$SSH_KEY" ]; then
        cmd="$cmd -i $SSH_KEY"
    fi
    echo "$cmd"
}

get_rsync_cmd() {
    local cmd="rsync -avz --progress"
    if [ -n "$SSH_KEY" ]; then
        cmd="$cmd -e 'ssh -i $SSH_KEY'"
    fi
    echo "$cmd"
}

check_remote_connection() {
    log_info "Checking connection to $REMOTE_HOST..."
    local ssh_cmd=$(get_ssh_cmd)

    if $ssh_cmd "$REMOTE_USER@$REMOTE_HOST" "echo 'Connection successful'" 2>/dev/null; then
        log_success "Connected to $REMOTE_HOST"
        return 0
    else
        log_error "Cannot connect to $REMOTE_HOST"
        log_info "Make sure you can SSH to the server:"
        log_info "  ssh $REMOTE_USER@$REMOTE_HOST"
        return 1
    fi
}

build_local() {
    log_info "Building Docker images locally..."
    cd "$PROJECT_DIR"

    # Build all services
    docker-compose -f docker-compose.microservices.yml build

    log_success "Local build complete!"
}

sync_files() {
    log_info "Syncing files to $REMOTE_HOST:$REMOTE_PATH..."

    local ssh_cmd=$(get_ssh_cmd)

    # Create remote directory if not exists
    $ssh_cmd "$REMOTE_USER@$REMOTE_HOST" "sudo mkdir -p $REMOTE_PATH && sudo chown $REMOTE_USER:$REMOTE_USER $REMOTE_PATH"

    # Sync files using rsync
    local exclude_args=(
        --exclude='.git'
        --exclude='__pycache__'
        --exclude='*.pyc'
        --exclude='.env'
        --exclude='uploads/*'
        --exclude='*.log'
        --exclude='.DS_Store'
        --exclude='node_modules'
        --exclude='.pytest_cache'
        --exclude='*.egg-info'
    )

    if [ -n "$SSH_KEY" ]; then
        rsync -avz --progress \
            "${exclude_args[@]}" \
            -e "ssh -i $SSH_KEY" \
            "$PROJECT_DIR/" \
            "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"
    else
        rsync -avz --progress \
            "${exclude_args[@]}" \
            "$PROJECT_DIR/" \
            "$REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/"
    fi

    log_success "Files synced!"
}

setup_remote_env() {
    log_info "Setting up remote environment..."
    local ssh_cmd=$(get_ssh_cmd)

    $ssh_cmd "$REMOTE_USER@$REMOTE_HOST" << 'REMOTE_SCRIPT'
cd /opt/ceramic-marketplace

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.microservices .env
    echo ""
    echo "=========================================="
    echo "IMPORTANT: Update .env with production values!"
    echo "Edit: /opt/ceramic-marketplace/.env"
    echo "=========================================="
fi

# Create required directories
mkdir -p uploads traefik/acme
chmod 600 traefik/acme 2>/dev/null || true

# Make scripts executable
chmod +x scripts/*.sh scripts/*.py 2>/dev/null || true

echo "Remote environment setup complete!"
REMOTE_SCRIPT

    log_success "Remote environment configured!"
}

deploy_remote() {
    log_info "Deploying on remote server..."
    local ssh_cmd=$(get_ssh_cmd)

    $ssh_cmd "$REMOTE_USER@$REMOTE_HOST" << 'REMOTE_SCRIPT'
cd /opt/ceramic-marketplace

echo "Building Docker images..."
docker-compose -f docker-compose.microservices.yml build

echo "Starting services..."
docker-compose -f docker-compose.microservices.yml up -d

echo "Waiting for services to start..."
sleep 10

echo "Checking service status..."
docker-compose -f docker-compose.microservices.yml ps

echo ""
echo "Running health check..."
./scripts/health_check.sh -v || true

echo ""
echo "Deployment complete!"
REMOTE_SCRIPT

    log_success "Remote deployment complete!"
}

print_summary() {
    echo ""
    echo "============================================="
    echo -e "${GREEN}Deployment Summary${NC}"
    echo "============================================="
    echo "Server:     $REMOTE_USER@$REMOTE_HOST"
    echo "Path:       $REMOTE_PATH"
    echo ""
    echo "Access URLs:"
    echo "  API Gateway:    http://$REMOTE_HOST"
    echo "  Traefik:        http://$REMOTE_HOST:8080"
    echo "  Auth API:       http://$REMOTE_HOST/api/v1/auth"
    echo "  Products API:   http://$REMOTE_HOST/api/v1/products"
    echo ""
    echo "Commands:"
    echo "  SSH to server:  ssh $REMOTE_USER@$REMOTE_HOST"
    echo "  View logs:      cd $REMOTE_PATH && docker-compose -f docker-compose.microservices.yml logs -f"
    echo "  Restart:        cd $REMOTE_PATH && ./scripts/deploy.sh restart"
    echo "============================================="
}

# =============================================================================
# Main
# =============================================================================

# Parse options
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            REMOTE_HOST="$2"
            shift 2
            ;;
        -u|--user)
            REMOTE_USER="$2"
            shift 2
            ;;
        -p|--path)
            REMOTE_PATH="$2"
            shift 2
            ;;
        -k|--key)
            SSH_KEY="$2"
            shift 2
            ;;
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --no-build)
            NO_BUILD=true
            shift
            ;;
        --help)
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

# Execute deployment
echo ""
echo "============================================="
echo -e "${BLUE}Ceramic Marketplace - Remote Deployment${NC}"
echo "============================================="
echo "Target: $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH"
echo ""

# Build locally (optional)
if [ "$NO_BUILD" = false ]; then
    build_local
fi

if [ "$BUILD_ONLY" = true ]; then
    log_success "Build complete. Skipping deployment."
    exit 0
fi

# Check connection
if ! check_remote_connection; then
    exit 1
fi

# Sync files
sync_files

# Setup environment
setup_remote_env

# Deploy on remote
deploy_remote

# Print summary
print_summary
