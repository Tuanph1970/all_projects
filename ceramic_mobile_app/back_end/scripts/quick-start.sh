#!/bin/bash
# =============================================================================
# Ceramic Marketplace - Quick Start Script
# =============================================================================
# One-command local deployment for testing
#
# Usage: ./scripts/quick-start.sh
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}     ${BLUE}CERAMIC MARKETPLACE - MICROSERVICES QUICK START${NC}       ${CYAN}║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_DIR"

# Step 1: Check Docker
echo -e "${BLUE}[1/6]${NC} Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed!${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Docker daemon is not running!${NC}"
    echo "Please start Docker and try again."
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker is running"

# Step 2: Setup environment
echo -e "${BLUE}[2/6]${NC} Setting up environment..."
if [ ! -f .env ]; then
    cp .env.microservices .env
    echo -e "${YELLOW}!${NC} Created .env from template"
    echo -e "${YELLOW}!${NC} Using default configuration for testing"
else
    echo -e "${GREEN}✓${NC} Environment file exists"
fi

# Step 3: Create required directories
echo -e "${BLUE}[3/6]${NC} Creating directories..."
mkdir -p uploads traefik/acme
echo -e "${GREEN}✓${NC} Directories ready"

# Step 4: Build services
echo -e "${BLUE}[4/6]${NC} Building services (this may take a few minutes)..."
docker-compose -f docker-compose.microservices.yml build --quiet
echo -e "${GREEN}✓${NC} Build complete"

# Step 5: Start services
echo -e "${BLUE}[5/6]${NC} Starting services..."

# Start infrastructure first
echo "    Starting database and cache..."
docker-compose -f docker-compose.microservices.yml up -d db redis

# Wait for database
echo "    Waiting for database to initialize..."
sleep 15

# Check database health
max_wait=60
waited=0
while [ $waited -lt $max_wait ]; do
    if docker-compose -f docker-compose.microservices.yml exec -T db mysqladmin ping -h localhost --silent 2>/dev/null; then
        break
    fi
    sleep 2
    waited=$((waited + 2))
    echo -n "."
done
echo ""

# Start all services
echo "    Starting all microservices..."
docker-compose -f docker-compose.microservices.yml up -d

echo -e "${GREEN}✓${NC} All services started"

# Step 6: Health check
echo -e "${BLUE}[6/6]${NC} Verifying deployment..."
sleep 5

echo ""
echo "Service Status:"
docker-compose -f docker-compose.microservices.yml ps --format "table {{.Name}}\t{{.Status}}"

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo "  API Gateway:       http://localhost"
echo "  Traefik Dashboard: http://localhost:8080"
echo ""
echo -e "${BLUE}API Endpoints:${NC}"
echo "  Auth:     http://localhost/api/v1/auth"
echo "  Products: http://localhost/api/v1/products"
echo "  Orders:   http://localhost/api/v1/orders"
echo "  Cart:     http://localhost/api/v1/cart"
echo "  Chat:     http://localhost/api/v1/chat"
echo "  Seller:   http://localhost/api/v1/seller"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs:     docker-compose -f docker-compose.microservices.yml logs -f"
echo "  Stop services: docker-compose -f docker-compose.microservices.yml down"
echo "  Health check:  ./scripts/health_check.sh -v"
echo "  Full status:   ./scripts/service_status.sh"
echo ""
echo -e "${YELLOW}Testing the API:${NC}"
echo "  curl http://localhost/api/v1/products"
echo ""
