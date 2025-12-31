#!/bin/bash
# =============================================================================
# React Client - Local Development Deployment Script
# =============================================================================
# Usage: ./scripts/deploy-react.sh [options]
# Options:
#   --docker    Run in Docker container
#   --native    Run with npm (native, default)
#   --build     Build production version
#   --stop      Stop React server
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REACT_DIR="$PROJECT_DIR/../stock_react_javascript/stock-react-app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default options
USE_DOCKER=false
BUILD_PROD=false
STOP_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --native)
            USE_DOCKER=false
            shift
            ;;
        --build)
            BUILD_PROD=true
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

cd "$REACT_DIR"

echo -e "${BLUE}=============================================${NC}"
echo -e "${BLUE}  React Client - Local Deployment${NC}"
echo -e "${BLUE}=============================================${NC}"

# Stop if requested
if [ "$STOP_ONLY" = true ]; then
    echo -e "\n${YELLOW}Stopping React development server...${NC}"
    pkill -f "react-scripts start" 2>/dev/null || true
    echo -e "${GREEN}✓ React server stopped${NC}"
    exit 0
fi

# Create .env.local for React if not exists
if [ ! -f .env.local ]; then
    echo -e "\n${YELLOW}Creating .env.local for React...${NC}"
    cat > .env.local << 'EOF'
# React App - Local Development Configuration
# API Gateway URL (Traefik)
REACT_APP_API_URL=http://localhost

# External services
REACT_APP_CHAT_SERVICE_URL=http://localhost:8006
REACT_APP_FILE_SERVICE_URL=http://localhost:8006

# Development settings
BROWSER=none
PORT=3000
EOF
    echo -e "${GREEN}✓ .env.local created${NC}"
fi

if [ "$BUILD_PROD" = true ]; then
    echo -e "\n${YELLOW}Building production version...${NC}"
    npm run build
    echo -e "${GREEN}✓ Production build complete${NC}"
    echo -e "${BLUE}Build output: ${REACT_DIR}/build${NC}"
    exit 0
fi

if [ "$USE_DOCKER" = true ]; then
    echo -e "\n${YELLOW}Starting React in Docker...${NC}"
    cd "$PROJECT_DIR"
    docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d react-client
    echo -e "${GREEN}✓ React client started in Docker${NC}"
else
    echo -e "\n${YELLOW}Installing dependencies...${NC}"
    npm install

    echo -e "\n${YELLOW}Starting React development server...${NC}"
    echo -e "${GREEN}React will be available at: http://localhost:3000${NC}"
    npm start
fi
