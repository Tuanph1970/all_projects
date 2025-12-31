#!/bin/bash
# =============================================================================
# Stock Microservices - Production Deployment Script
# =============================================================================
# Usage: ./scripts/deploy-prod.sh [options]
# Options:
#   --build          Force rebuild all images
#   --build-react    Build React production bundle
#   --update         Pull latest images and restart
#   --rollback       Rollback to previous deployment
#   --status         Show deployment status
#   --logs           Show service logs
#   --stop           Stop all services
#   --backup         Backup volumes before deployment
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REACT_DIR="$PROJECT_DIR/../stock_react_javascript/stock-react-app"
BACKUP_DIR="$PROJECT_DIR/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Options
BUILD_FLAG=""
BUILD_REACT=false
UPDATE_ONLY=false
ROLLBACK=false
STATUS_ONLY=false
SHOW_LOGS=false
STOP_ONLY=false
BACKUP_VOLUMES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --build-react)
            BUILD_REACT=true
            shift
            ;;
        --update)
            UPDATE_ONLY=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --status)
            STATUS_ONLY=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --stop)
            STOP_ONLY=true
            shift
            ;;
        --backup)
            BACKUP_VOLUMES=true
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
echo -e "${BLUE}  Stock Microservices - Production Deploy${NC}"
echo -e "${BLUE}=============================================${NC}"

# Check for production environment file
if [ ! -f .env ]; then
    if [ -f .env.production ]; then
        echo -e "${YELLOW}Warning: .env not found, using .env.production${NC}"
        cp .env.production .env
    else
        echo -e "${RED}Error: .env file not found${NC}"
        echo -e "${YELLOW}Please create .env from .env.production template${NC}"
        exit 1
    fi
fi

# Check for default passwords
if grep -q "CHANGE_ME" .env; then
    echo -e "${RED}ERROR: Default passwords detected in .env file!${NC}"
    echo -e "${YELLOW}Please change all passwords before production deployment.${NC}"
    exit 1
fi

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

# Status check
if [ "$STATUS_ONLY" = true ]; then
    echo -e "\n${BLUE}Deployment Status:${NC}"
    docker-compose $COMPOSE_FILES ps
    echo -e "\n${BLUE}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
    exit 0
fi

# Stop services
if [ "$STOP_ONLY" = true ]; then
    echo -e "\n${YELLOW}Stopping production services...${NC}"
    docker-compose $COMPOSE_FILES down
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
fi

# Show logs
if [ "$SHOW_LOGS" = true ]; then
    echo -e "\n${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    docker-compose $COMPOSE_FILES logs -f
    exit 0
fi

# Rollback
if [ "$ROLLBACK" = true ]; then
    echo -e "\n${YELLOW}Rolling back to previous deployment...${NC}"
    if [ -f "$BACKUP_DIR/docker-compose.backup.yml" ]; then
        docker-compose $COMPOSE_FILES down
        docker-compose -f "$BACKUP_DIR/docker-compose.backup.yml" up -d
        echo -e "${GREEN}✓ Rollback complete${NC}"
    else
        echo -e "${RED}No backup found for rollback${NC}"
        exit 1
    fi
    exit 0
fi

# Backup volumes if requested
if [ "$BACKUP_VOLUMES" = true ]; then
    echo -e "\n${YELLOW}Backing up volumes...${NC}"
    mkdir -p "$BACKUP_DIR"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    docker-compose $COMPOSE_FILES config > "$BACKUP_DIR/docker-compose.backup.yml"
    echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"
fi

# Check port 8002 conflict
echo -e "\n${YELLOW}Checking for port conflicts...${NC}"
if ss -tlnp 2>/dev/null | grep -q ':8002 ' || netstat -tlnp 2>/dev/null | grep -q ':8002 '; then
    echo -e "${GREEN}✓ Port 8002 is in use by existing service${NC}"
    echo -e "${GREEN}  Prediction service will be internal only (via Nginx)${NC}"
else
    echo -e "${YELLOW}⚠ Port 8002 is free${NC}"
fi

# Build React if requested
if [ "$BUILD_REACT" = true ]; then
    echo -e "\n${YELLOW}Building React production bundle...${NC}"
    cd "$REACT_DIR"

    # Create production environment
    cat > .env.production.local << EOF
REACT_APP_API_URL=
REACT_APP_CHAT_SERVICE_URL=
REACT_APP_FILE_SERVICE_URL=
EOF

    npm install
    npm run build

    if [ ! -d "build" ]; then
        echo -e "${RED}React build failed!${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ React build complete${NC}"
    cd "$PROJECT_DIR"
fi

# Verify React build exists
if [ ! -d "$REACT_DIR/build" ]; then
    echo -e "${YELLOW}Warning: React build not found at $REACT_DIR/build${NC}"
    echo -e "${YELLOW}Run with --build-react to create production build${NC}"
fi

# Update deployment
if [ "$UPDATE_ONLY" = true ]; then
    echo -e "\n${YELLOW}Pulling latest images...${NC}"
    docker-compose $COMPOSE_FILES pull
fi

# Deploy
echo -e "\n${YELLOW}Deploying production services...${NC}"
docker-compose $COMPOSE_FILES up -d $BUILD_FLAG

# Wait for health checks
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 15

# Verify deployment
echo -e "\n${BLUE}Service Status:${NC}"
docker-compose $COMPOSE_FILES ps

# Check nginx health
if curl -s -f http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "\n${GREEN}✓ Nginx health check passed${NC}"
else
    echo -e "\n${YELLOW}⚠ Nginx health check pending...${NC}"
fi

echo -e "\n${GREEN}=============================================${NC}"
echo -e "${GREEN}  Production Deployment Complete!${NC}"
echo -e "${GREEN}=============================================${NC}"
echo -e "\n${BLUE}Access URLs (Direct - Port 8080):${NC}"
echo -e "  ${GREEN}Web Application:${NC}          http://localhost:8080"
echo -e "  ${GREEN}API Gateway:${NC}              http://localhost:8080/stock_helper/api/v2/"
echo -e "  ${GREEN}Grafana:${NC}                  http://localhost:8080/grafana"
echo -e ""
echo -e "${BLUE}To access via port 80 (through system nginx):${NC}"
echo -e "  See: ${GREEN}DEPLOYMENT.md${NC} section 'Nginx Conflict Resolution'"
echo -e "  Configure system nginx to proxy to port 8080"
echo -e ""
echo -e "${YELLOW}Note: Port 8002 is NOT exposed - prediction service accessed via API gateway${NC}"
echo -e "${YELLOW}Note: Using port 8080 to avoid conflict with system nginx on port 80${NC}"
echo -e ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  ${GREEN}View logs:${NC}    ./scripts/deploy-prod.sh --logs"
echo -e "  ${GREEN}Status:${NC}       ./scripts/deploy-prod.sh --status"
echo -e "  ${GREEN}Stop:${NC}         ./scripts/deploy-prod.sh --stop"
echo -e "  ${GREEN}Rollback:${NC}     ./scripts/deploy-prod.sh --rollback"
