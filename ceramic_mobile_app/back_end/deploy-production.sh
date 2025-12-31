#!/bin/bash

#############################################
# Ceramic Marketplace API - Production Deploy
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
ENV_FILE=".env.production"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Ceramic Marketplace API Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running with sudo
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}✗ Please do not run this script as root/sudo${NC}"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠ Warning: $ENV_FILE not found!${NC}"
    echo -e "${YELLOW}Creating from .env.example...${NC}"

    if [ -f ".env.example" ]; then
        cp .env.example $ENV_FILE
        echo -e "${YELLOW}⚠ Please edit $ENV_FILE with your production values before continuing${NC}"
        echo -e "${YELLOW}Run: nano $ENV_FILE${NC}"
        exit 1
    else
        echo -e "${RED}✗ .env.example not found. Cannot create environment file.${NC}"
        exit 1
    fi
fi

# Create required directories
echo -e "${GREEN}→${NC} Creating required directories..."
mkdir -p uploads logs backups nginx/ssl
chmod 755 uploads logs backups

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

# Pull latest code (if in git repo)
if [ -d ".git" ]; then
    echo -e "${GREEN}→${NC} Pulling latest code from git..."
    git pull origin $(git branch --show-current) || echo -e "${YELLOW}⚠ Git pull failed or no remote configured${NC}"
fi

# Build and start services
echo -e "${GREEN}→${NC} Building Docker images..."
docker-compose -f $COMPOSE_FILE build --no-cache

echo -e "${GREEN}→${NC} Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for services to be healthy
echo -e "${GREEN}→${NC} Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo -e "${GREEN}→${NC} Checking service status..."
docker-compose -f $COMPOSE_FILE ps

# Test API health
echo ""
echo -e "${GREEN}→${NC} Testing API health..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if curl -f http://localhost/health &> /dev/null; then
        echo -e "${GREEN}✓ API is healthy!${NC}"
        break
    fi

    retry_count=$((retry_count + 1))
    echo -e "Waiting for API to be ready... ($retry_count/$max_retries)"
    sleep 2
done

if [ $retry_count -eq $max_retries ]; then
    echo -e "${RED}✗ API health check failed after $max_retries attempts${NC}"
    echo -e "${YELLOW}Check logs with: docker-compose -f $COMPOSE_FILE logs${NC}"
    exit 1
fi

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || echo "YOUR_SERVER_IP")

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "API is running at:"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/api/docs (API Documentation)"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/health (Health Check)"
echo ""
echo -e "Management commands:"
echo -e "  ${GREEN}→${NC} View logs:    docker-compose -f $COMPOSE_FILE logs -f"
echo -e "  ${GREEN}→${NC} Stop:         docker-compose -f $COMPOSE_FILE down"
echo -e "  ${GREEN}→${NC} Restart:      docker-compose -f $COMPOSE_FILE restart"
echo -e "  ${GREEN}→${NC} Status:       docker-compose -f $COMPOSE_FILE ps"
echo ""
echo -e "${YELLOW}⚠ Next steps:${NC}"
echo -e "  1. Configure SSL/HTTPS if needed (see DOCKER_DEPLOY.md)"
echo -e "  2. Setup automated backups (see DOCKER_DEPLOY.md)"
echo -e "  3. Configure firewall (UFW)"
echo -e "  4. Update CORS settings in $ENV_FILE"
echo ""
