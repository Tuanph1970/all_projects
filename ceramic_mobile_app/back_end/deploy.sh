#!/bin/bash

# Ceramic Marketplace API - Production Deployment Script
# Server: 112.213.91.103 (Ubuntu 22.04)

set -e  # Exit on any error

echo "========================================"
echo "Ceramic Marketplace API - Deployment"
echo "========================================"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}Error: .env.production file not found!${NC}"
    echo "Please create .env.production with your production settings."
    exit 1
fi

echo -e "${GREEN}✓ Found .env.production${NC}"

# Stop existing containers
echo ""
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

# Remove old images (optional - comment out if you want to keep old images)
# echo "Removing old images..."
# docker rmi ceramic_api_prod 2>/dev/null || true

# Build the application
echo ""
echo "Building Docker image..."
docker-compose -f docker-compose.prod.yml build

# Start the containers
echo ""
echo "Starting containers..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for application to start
echo ""
echo "Waiting for application to start..."
sleep 5

# Check if container is running
if docker ps | grep -q ceramic_api_prod; then
    echo -e "${GREEN}✓ Container is running${NC}"
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "Checking logs..."
    docker-compose -f docker-compose.prod.yml logs --tail 50
    exit 1
fi

# Check application health
echo ""
echo "Checking application health..."
sleep 3

if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Application is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed, but container is running${NC}"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs -f"
fi

# Show container status
echo ""
echo "Container Status:"
docker-compose -f docker-compose.prod.yml ps

# Show recent logs
echo ""
echo "Recent logs:"
docker-compose -f docker-compose.prod.yml logs --tail 20

echo ""
echo -e "${GREEN}========================================"
echo "Deployment Complete!"
echo "========================================${NC}"
echo ""
echo "API is running at: http://112.213.91.103:8000"
echo "API Documentation: http://112.213.91.103:8000/docs"
echo "Health Check: http://112.213.91.103:8000/health"
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop: docker-compose -f docker-compose.prod.yml down"
echo "  Restart: docker-compose -f docker-compose.prod.yml restart"
echo ""