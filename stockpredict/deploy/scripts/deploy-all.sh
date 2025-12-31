#!/bin/bash
# =============================================================================
# Unified Deployment Script - Ceramic + Stock Helper
# =============================================================================
# Deploys both Ceramic API and Stock Helper microservices
#
# Usage:
#   ./deploy-all.sh [options]
#
# Options:
#   --local         Deploy for local development (default)
#   --production    Deploy for production
#   --build         Force rebuild all Docker images
#   --clean         Clean up volumes before deployment
#   --ceramic-only  Deploy only Ceramic API
#   --stock-only    Deploy only Stock Helper
#   --react         Also build/start React client
#   --nginx         Configure system nginx
#   --skip-checks   Skip pre-deployment checks
#   --help          Show this help message
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(dirname "$SCRIPT_DIR")"
BASE_DIR="$(dirname "$DEPLOY_DIR")"
CERAMIC_DIR="$BASE_DIR/../ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stock_microservices"
REACT_DIR="$BASE_DIR/stock_react_javascript/stock-react-app"

# Default options
ENV_TYPE="local"
BUILD_FLAG=""
CLEAN_FLAG=false
DEPLOY_CERAMIC=true
DEPLOY_STOCK=true
DEPLOY_REACT=false
CONFIGURE_NGINX=false
SKIP_CHECKS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            ENV_TYPE="local"
            shift
            ;;
        --production|--prod)
            ENV_TYPE="production"
            shift
            ;;
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --clean)
            CLEAN_FLAG=true
            shift
            ;;
        --ceramic-only)
            DEPLOY_CERAMIC=true
            DEPLOY_STOCK=false
            shift
            ;;
        --stock-only)
            DEPLOY_CERAMIC=false
            DEPLOY_STOCK=true
            shift
            ;;
        --react)
            DEPLOY_REACT=true
            shift
            ;;
        --nginx)
            CONFIGURE_NGINX=true
            shift
            ;;
        --skip-checks)
            SKIP_CHECKS=true
            shift
            ;;
        --help|-h)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Print banner
echo -e "${CYAN}"
echo "============================================================"
echo "       UNIFIED DEPLOYMENT - Ceramic + Stock Helper"
echo "============================================================"
echo -e "${NC}"
echo -e "Environment: ${GREEN}$ENV_TYPE${NC}"
echo -e "Ceramic API: ${DEPLOY_CERAMIC:+${GREEN}Yes${NC}}${DEPLOY_CERAMIC:-${YELLOW}No${NC}}"
echo -e "Stock Helper: ${DEPLOY_STOCK:+${GREEN}Yes${NC}}${DEPLOY_STOCK:-${YELLOW}No${NC}}"
echo -e "React Client: ${DEPLOY_REACT:+${GREEN}Yes${NC}}${DEPLOY_REACT:-${YELLOW}No${NC}}"
echo ""

# =============================================================================
# Pre-deployment Checks
# =============================================================================
if [ "$SKIP_CHECKS" = false ]; then
    echo -e "${BLUE}Running pre-deployment checks...${NC}"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker installed${NC}"

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        echo -e "${RED}✗ Docker daemon is not running${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker daemon running${NC}"

    # Check docker-compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose installed${NC}"

    # Check port conflicts
    echo -e "\n${BLUE}Checking port availability...${NC}"

    check_port() {
        local port=$1
        local service=$2
        if ss -tlnp 2>/dev/null | grep -q ":$port " || netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            echo -e "${YELLOW}⚠ Port $port ($service) is in use${NC}"
            return 1
        fi
        echo -e "${GREEN}✓ Port $port ($service) is available${NC}"
        return 0
    }

    # Check critical ports
    PORTS_OK=true
    if [ "$DEPLOY_CERAMIC" = true ]; then
        check_port 8002 "Ceramic API" || PORTS_OK=false
    fi

    if [ "$DEPLOY_STOCK" = true ]; then
        check_port 8088 "Stock Traefik" || true  # May be restarting
        check_port 8001 "Stock Data Service" || true
    fi

    echo ""
fi

# =============================================================================
# Deploy Ceramic API
# =============================================================================
if [ "$DEPLOY_CERAMIC" = true ]; then
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  Deploying Ceramic API${NC}"
    echo -e "${CYAN}============================================${NC}"

    cd "$CERAMIC_DIR"

    # Select compose file
    if [ "$ENV_TYPE" = "production" ]; then
        COMPOSE_FILE="docker-compose.prod.yml"
        ENV_FILE=".env.production"
    else
        COMPOSE_FILE="docker-compose.local.yml"
        ENV_FILE=".env"
    fi

    # Check env file
    if [ ! -f "$ENV_FILE" ] && [ -f ".env.production" ]; then
        echo -e "${YELLOW}Creating $ENV_FILE from template...${NC}"
        cp .env.production "$ENV_FILE"
    fi

    # Clean if requested
    if [ "$CLEAN_FLAG" = true ]; then
        echo -e "${YELLOW}Cleaning up Ceramic containers...${NC}"
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
    fi

    # Create directories
    mkdir -p uploads logs

    # Deploy
    echo -e "${GREEN}Starting Ceramic API...${NC}"
    docker-compose -f "$COMPOSE_FILE" up -d $BUILD_FLAG

    # Wait for health
    echo -e "${YELLOW}Waiting for Ceramic API to be healthy...${NC}"
    for i in {1..30}; do
        if curl -sf http://localhost:8002/health > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Ceramic API is healthy${NC}"
            break
        fi
        sleep 2
        echo -n "."
    done
    echo ""
fi

# =============================================================================
# Deploy Stock Helper
# =============================================================================
if [ "$DEPLOY_STOCK" = true ]; then
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  Deploying Stock Helper Microservices${NC}"
    echo -e "${CYAN}============================================${NC}"

    cd "$STOCK_DIR"

    # Select compose files
    if [ "$ENV_TYPE" = "production" ]; then
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
        ENV_FILE=".env.production"
    else
        COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"
        ENV_FILE=".env.local"
    fi

    # Check env file
    if [ ! -f ".env" ]; then
        if [ -f "$ENV_FILE" ]; then
            echo -e "${YELLOW}Creating .env from $ENV_FILE...${NC}"
            cp "$ENV_FILE" .env
        fi
    fi

    # Clean if requested
    if [ "$CLEAN_FLAG" = true ]; then
        echo -e "${YELLOW}Cleaning up Stock Helper containers...${NC}"
        docker-compose $COMPOSE_FILES down -v --remove-orphans 2>/dev/null || true
    fi

    # Deploy
    echo -e "${GREEN}Starting Stock Helper microservices...${NC}"
    docker-compose $COMPOSE_FILES up -d $BUILD_FLAG

    # Wait for services
    echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
    sleep 15

    # Check services
    SERVICES=("8001:Stock Data" "8003:Portfolio" "8004:Analysis" "8005:AI Insights" "8006:Chatbot" "8007:Auth")
    for svc in "${SERVICES[@]}"; do
        PORT="${svc%%:*}"
        NAME="${svc##*:}"
        if curl -sf "http://localhost:$PORT/health/live" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $NAME Service is healthy${NC}"
        else
            echo -e "${YELLOW}⚠ $NAME Service may still be starting...${NC}"
        fi
    done
fi

# =============================================================================
# Deploy React Client
# =============================================================================
if [ "$DEPLOY_REACT" = true ]; then
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  Deploying React Client${NC}"
    echo -e "${CYAN}============================================${NC}"

    cd "$REACT_DIR"

    if [ "$ENV_TYPE" = "production" ]; then
        # Build production bundle
        echo -e "${YELLOW}Building React production bundle...${NC}"

        # Create production env
        cat > .env.production.local << EOF
REACT_APP_API_URL=
REACT_APP_CHAT_SERVICE_URL=
REACT_APP_FILE_SERVICE_URL=
EOF

        npm install
        npm run build

        echo -e "${GREEN}✓ React build complete: $REACT_DIR/build${NC}"
    else
        # Development mode
        echo -e "${YELLOW}Starting React development server...${NC}"

        # Create local env
        cat > .env.local << EOF
REACT_APP_API_URL=http://localhost
REACT_APP_CHAT_SERVICE_URL=http://localhost:8006
REACT_APP_FILE_SERVICE_URL=http://localhost:8006
PORT=3001
BROWSER=none
EOF

        # Start in background
        nohup npm start > /tmp/react-app.log 2>&1 &
        echo -e "${GREEN}✓ React dev server starting on port 3001${NC}"
    fi
fi

# =============================================================================
# Configure System Nginx
# =============================================================================
if [ "$CONFIGURE_NGINX" = true ]; then
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  Configuring System Nginx${NC}"
    echo -e "${CYAN}============================================${NC}"

    NGINX_CONF="$DEPLOY_DIR/nginx/unified-projects.conf"

    if [ -f "$NGINX_CONF" ]; then
        echo -e "${YELLOW}Installing nginx configuration...${NC}"
        sudo cp "$NGINX_CONF" /etc/nginx/sites-available/unified-projects
        sudo ln -sf /etc/nginx/sites-available/unified-projects /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

        if sudo nginx -t; then
            sudo systemctl reload nginx
            echo -e "${GREEN}✓ Nginx configured and reloaded${NC}"
        else
            echo -e "${RED}✗ Nginx configuration test failed${NC}"
        fi
    else
        echo -e "${RED}✗ Nginx config not found: $NGINX_CONF${NC}"
    fi
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"

if [ "$DEPLOY_CERAMIC" = true ]; then
    echo -e "  ${GREEN}Ceramic API:${NC}          http://localhost:8002"
    echo -e "  ${GREEN}Ceramic Docs:${NC}         http://localhost:8002/api/docs"
fi

if [ "$DEPLOY_STOCK" = true ]; then
    echo -e "  ${GREEN}Stock Gateway:${NC}        http://localhost:8088"
    echo -e "  ${GREEN}Stock API:${NC}            http://localhost:8088/stock_helper/api/v2/"
    echo -e "  ${GREEN}Traefik Dashboard:${NC}    http://localhost:8089"
    echo -e "  ${GREEN}Grafana:${NC}              http://localhost:3100"
    echo -e "  ${GREEN}RabbitMQ:${NC}             http://localhost:15672"
    echo -e "  ${GREEN}Jaeger:${NC}               http://localhost:16686"
fi

if [ "$DEPLOY_REACT" = true ]; then
    if [ "$ENV_TYPE" = "production" ]; then
        echo -e "  ${GREEN}React App:${NC}            http://localhost (via nginx)"
    else
        echo -e "  ${GREEN}React App:${NC}            http://localhost:3001"
    fi
fi

echo ""
echo -e "${BLUE}Management:${NC}"
echo -e "  ${GREEN}Status:${NC}    $SCRIPT_DIR/status.sh"
echo -e "  ${GREEN}Stop:${NC}      $SCRIPT_DIR/stop-all.sh"
echo -e "  ${GREEN}Logs:${NC}      $SCRIPT_DIR/logs.sh [service]"
echo ""
