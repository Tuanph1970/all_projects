#!/bin/bash

###############################################
# Ceramic Marketplace API - Local Deployment
# Deploy to your local PC for testing
# Ports: API=8004, MySQL=3308
###############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Ceramic API - Local Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo -e "${YELLOW}Please install Docker Desktop from: https://www.docker.com/products/docker-desktop${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo -e "${YELLOW}Please install Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
echo ""

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop or Docker service${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker daemon is running${NC}"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found, creating from .env.local...${NC}"
    if [ -f ".env.local" ]; then
        cp .env.local .env
        echo -e "${GREEN}✓ Created .env from template${NC}"
    else
        echo -e "${RED}✗ .env.local template not found${NC}"
        exit 1
    fi
fi

# Create required directories
echo -e "${GREEN}→${NC} Creating required directories..."
mkdir -p uploads logs backups
chmod 755 uploads logs backups 2>/dev/null || true
echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Ask user confirmation
echo -e "${BLUE}Deployment Configuration:${NC}"
echo -e "  API will be accessible at: ${GREEN}http://localhost:8002${NC}"
echo -e "  MySQL: ${GREEN}Using native MySQL on localhost:3306${NC}"
echo -e "  Redis: ${GREEN}Using native Redis on localhost:6379${NC}"
echo -e "  API Documentation: ${GREEN}http://localhost:8002/api/docs${NC}"
echo ""
read -p "Start deployment? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Build and start services
echo ""
echo -e "${GREEN}→${NC} Building Docker images (this may take a few minutes)..."
docker-compose -f docker-compose.local.yml build --no-cache

echo ""
echo -e "${GREEN}→${NC} Starting services..."
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be healthy
echo ""
echo -e "${GREEN}→${NC} Waiting for services to be ready..."
sleep 10

# Check service status
echo ""
echo -e "${GREEN}→${NC} Checking service status..."
docker-compose -f docker-compose.local.yml ps

# Test API health
echo ""
echo -e "${GREEN}→${NC} Testing API health..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -f http://localhost:8002/health &> /dev/null; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        break
    fi

    retry_count=$((retry_count + 1))
    if [ $((retry_count % 5)) -eq 0 ]; then
        echo -e "  Waiting for API... ($retry_count/$max_retries)"
    fi
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo -e "${RED}✗ API health check failed after $max_retries attempts${NC}"
    echo ""
    echo -e "${YELLOW}Showing recent logs:${NC}"
    docker-compose -f docker-compose.local.yml logs --tail=50 api
    echo ""
    echo -e "${YELLOW}Check logs with: docker-compose -f docker-compose.local.yml logs${NC}"
    exit 1
fi

# Show success message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Access your API:${NC}"
echo -e "  ${GREEN}→${NC} API: http://localhost:8002"
echo -e "  ${GREEN}→${NC} API Docs (Swagger): http://localhost:8002/api/docs"
echo -e "  ${GREEN}→${NC} API Docs (ReDoc): http://localhost:8002/api/redoc"
echo -e "  ${GREEN}→${NC} Health Check: http://localhost:8002/health"
echo ""
echo -e "${BLUE}Database Access (Native MySQL):${NC}"
echo -e "  ${GREEN}→${NC} Host: localhost"
echo -e "  ${GREEN}→${NC} Port: 3306"
echo -e "  ${GREEN}→${NC} Database: ceramic_marketplace"
echo -e "  ${GREEN}→${NC} User: ceramic_user"
echo ""
echo -e "${BLUE}Management Commands:${NC}"
echo -e "  ${GREEN}→${NC} View logs: docker-compose -f docker-compose.local.yml logs -f"
echo -e "  ${GREEN}→${NC} Stop: docker-compose -f docker-compose.local.yml stop"
echo -e "  ${GREEN}→${NC} Start: docker-compose -f docker-compose.local.yml start"
echo -e "  ${GREEN}→${NC} Restart: docker-compose -f docker-compose.local.yml restart"
echo -e "  ${GREEN}→${NC} Remove: docker-compose -f docker-compose.local.yml down"
echo ""
echo -e "${YELLOW}💡 Tip: Test all features locally before deploying to remote server!${NC}"
echo ""
