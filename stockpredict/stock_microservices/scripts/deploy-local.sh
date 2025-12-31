#!/bin/bash
# =============================================================================
# Stock Microservices - Local Development Deployment Script
# =============================================================================
# Usage: ./scripts/deploy-local.sh [options]
# Options:
#   --build     Force rebuild all images
#   --clean     Clean up volumes and restart fresh
#   --logs      Show logs after deployment
#   --react     Also deploy React client
#   --stop      Stop all services
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
BUILD_FLAG=""
CLEAN_FLAG=false
SHOW_LOGS=false
INCLUDE_REACT=false
STOP_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --clean)
            CLEAN_FLAG=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --react)
            INCLUDE_REACT=true
            shift
            ;;
        --stop)
            STOP_ONLY=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  Stock Microservices - Local Deployment${NC}"
echo -e "${BLUE}=============================================${NC}"

# Check if port 8002 is in use (external service)
echo -e "\n${YELLOW}Checking for port conflicts...${NC}"
if ss -tlnp 2>/dev/null | grep -q ':8002 ' || netstat -tlnp 2>/dev/null | grep -q ':8002 '; then
    echo -e "${GREEN}✓ Port 8002 is in use by existing service (as expected)${NC}"
    echo -e "${GREEN}  Prediction service will be accessed via Traefik gateway only${NC}"
else
    echo -e "${YELLOW}⚠ Port 8002 is free (your external service may not be running)${NC}"
fi

# Stop services if requested
if [ "$STOP_ONLY" = true ]; then
    echo -e "\n${YELLOW}Stopping all services...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.local.yml down
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
fi

# Clean up if requested
if [ "$CLEAN_FLAG" = true ]; then
    echo -e "\n${YELLOW}Cleaning up volumes and containers...${NC}"
    docker-compose -f docker-compose.yml -f docker-compose.local.yml down -v --remove-orphans
    echo -e "${GREEN}✓ Cleanup complete${NC}"
fi

# Copy environment file if not exists
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file from .env.local...${NC}"
    cp .env.local .env
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Build and start services
echo -e "\n${YELLOW}Starting microservices...${NC}"

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"

if [ "$INCLUDE_REACT" = true ]; then
    echo -e "${BLUE}Including React client...${NC}"
fi

docker-compose $COMPOSE_FILES up -d $BUILD_FLAG

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service status
echo -e "\n${BLUE}Service Status:${NC}"
docker-compose $COMPOSE_FILES ps

# Show access URLs
echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "\n${BLUE}Access URLs:${NC}"
echo -e "  ${GREEN}API Gateway (Traefik):${NC}     http://localhost:8088"
echo -e "  ${GREEN}Traefik Dashboard:${NC}        http://localhost:8089"
echo -e "  ${GREEN}RabbitMQ Management:${NC}      http://localhost:15672"
echo -e "  ${GREEN}Grafana:${NC}                  http://localhost:3100"
echo -e "  ${GREEN}Prometheus:${NC}               http://localhost:9090"
echo -e "  ${GREEN}Jaeger Tracing:${NC}           http://localhost:16686"
echo -e ""
echo -e "${BLUE}Microservices (Direct Access):${NC}"
echo -e "  ${GREEN}Auth Service:${NC}             http://localhost:8007/stock_helper/api/v2/auth"
echo -e "  ${GREEN}Stock Data Service:${NC}       http://localhost:8001/stock_helper/api/v2"
echo -e "  ${GREEN}Portfolio Service:${NC}        http://localhost:8003/stock_helper/api/v2/portfolio"
echo -e "  ${GREEN}Analysis Service:${NC}         http://localhost:8004/stock_helper/api/v2/analysis"
echo -e "  ${GREEN}AI Insights Service:${NC}      http://localhost:8005/stock_helper/api/v2/ai"
echo -e "  ${GREEN}Chatbot Service:${NC}          http://localhost:8006/stock_helper/api/v2/chatbot"
echo -e "  ${GREEN}Prediction Service:${NC}       Via Traefik only (port 8002 reserved)"
echo -e ""
if [ "$INCLUDE_REACT" = true ]; then
    echo -e "${BLUE}React Client:${NC}"
    echo -e "  ${GREEN}Web Application:${NC}          http://localhost:3000"
    echo -e ""
fi

echo -e "${YELLOW}Note: Port 8002 is NOT exposed to avoid conflict with your existing service${NC}"
echo -e "${YELLOW}      Access prediction-service via: http://localhost:8088/stock_helper/api/v2/predictions${NC}"

# Show logs if requested
if [ "$SHOW_LOGS" = true ]; then
    echo -e "\n${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose $COMPOSE_FILES logs -f
fi
