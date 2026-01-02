#!/bin/bash
# =============================================================================
# Stock Microservices - Deployment Script
# =============================================================================
# Deploys Stock Helper microservices with Traefik routing
# Designed to coexist with Ceramic (port 8002) and Math (port 8003) projects
#
# Usage: ./scripts/deploy.sh [options]
#
# Options:
#   --build          Force rebuild all images
#   --clean          Clean up containers and volumes before deployment
#   --status         Show deployment status
#   --logs [service] Show service logs
#   --stop           Stop all services
#   --health         Check health of all services
#   --test           Test all API endpoints
#   --help           Show this help message
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
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default options
BUILD_FLAG=""
CLEAN_FLAG=false
STATUS_ONLY=false
SHOW_LOGS=false
LOG_SERVICE=""
STOP_ONLY=false
HEALTH_CHECK=false
TEST_ENDPOINTS=false

# Port configuration (unique for stock project)
TRAEFIK_PORT=8004
TRAEFIK_DASHBOARD_PORT=8084
RABBITMQ_PORT=5672
RABBITMQ_MGMT_PORT=15672
PROMETHEUS_PORT=9090
GRAFANA_PORT=3100
JAEGER_PORT=16686

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
        --status)
            STATUS_ONLY=true
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            if [[ -n "$2" && ! "$2" =~ ^-- ]]; then
                LOG_SERVICE="$2"
                shift
            fi
            shift
            ;;
        --stop)
            STOP_ONLY=true
            shift
            ;;
        --health)
            HEALTH_CHECK=true
            shift
            ;;
        --test)
            TEST_ENDPOINTS=true
            shift
            ;;
        --help|-h)
            head -25 "$0" | tail -20
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

cd "$PROJECT_DIR"

# Print banner
echo -e "${CYAN}"
echo "============================================================"
echo "       Stock Microservices Deployment"
echo "============================================================"
echo -e "${NC}"

# =============================================================================
# Status Check
# =============================================================================
if [ "$STATUS_ONLY" = true ]; then
    echo -e "${BLUE}Container Status:${NC}"
    docker ps -a --filter "name=stock_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo -e "${BLUE}Resource Usage:${NC}"
    docker stats --no-stream --filter "name=stock_" --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || true
    exit 0
fi

# =============================================================================
# Stop Services
# =============================================================================
if [ "$STOP_ONLY" = true ]; then
    echo -e "${YELLOW}Stopping Stock microservices...${NC}"
    docker compose -f docker-compose.yml -f docker-compose.local.yml down 2>/dev/null || \
    docker-compose -f docker-compose.yml -f docker-compose.local.yml down 2>/dev/null || true
    echo -e "${GREEN}All Stock services stopped${NC}"
    exit 0
fi

# =============================================================================
# Show Logs
# =============================================================================
if [ "$SHOW_LOGS" = true ]; then
    echo -e "${YELLOW}Showing logs (Ctrl+C to exit)...${NC}"
    if [ -n "$LOG_SERVICE" ]; then
        docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f "$LOG_SERVICE" 2>/dev/null || \
        docker-compose -f docker-compose.yml -f docker-compose.local.yml logs -f "$LOG_SERVICE"
    else
        docker compose -f docker-compose.yml -f docker-compose.local.yml logs -f 2>/dev/null || \
        docker-compose -f docker-compose.yml -f docker-compose.local.yml logs -f
    fi
    exit 0
fi

# =============================================================================
# Health Check Function
# =============================================================================
check_service_health() {
    local service_name=$1
    local port=$2
    local endpoint=${3:-"/health/live"}

    if curl -sf "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        echo -e "${GREEN}  [OK] $service_name (port $port)${NC}"
        return 0
    else
        echo -e "${RED}  [FAIL] $service_name (port $port)${NC}"
        return 1
    fi
}

# =============================================================================
# Health Check Only
# =============================================================================
if [ "$HEALTH_CHECK" = true ]; then
    echo -e "${BLUE}Checking service health...${NC}"
    echo ""

    # Infrastructure
    echo -e "${CYAN}Infrastructure:${NC}"
    check_service_health "Traefik Gateway" $TRAEFIK_PORT "/api/rawdata" || true
    check_service_health "RabbitMQ" $RABBITMQ_MGMT_PORT "/" || true
    check_service_health "Prometheus" $PROMETHEUS_PORT "/-/healthy" || true
    check_service_health "Grafana" $GRAFANA_PORT "/api/health" || true
    check_service_health "Jaeger" $JAEGER_PORT "/" || true

    echo ""
    echo -e "${CYAN}Microservices (via Traefik):${NC}"
    check_service_health "Auth Service" $TRAEFIK_PORT "/stock_helper/api/v2/auth/health" || true
    check_service_health "Stock Data Service" $TRAEFIK_PORT "/stock_helper/api/v2/stocks/health" || true
    check_service_health "Portfolio Service" $TRAEFIK_PORT "/stock_helper/api/v2/portfolio/health" || true
    check_service_health "Prediction Service" $TRAEFIK_PORT "/stock_helper/api/v2/predictions/health" || true
    check_service_health "Analysis Service" $TRAEFIK_PORT "/stock_helper/api/v2/analysis/health" || true
    check_service_health "AI Insights Service" $TRAEFIK_PORT "/stock_helper/api/v2/ai/health" || true
    check_service_health "Chatbot Service" $TRAEFIK_PORT "/stock_helper/api/v2/chat/health" || true

    exit 0
fi

# =============================================================================
# Test API Endpoints
# =============================================================================
if [ "$TEST_ENDPOINTS" = true ]; then
    echo -e "${BLUE}Testing API endpoints...${NC}"
    echo ""

    BASE_URL="http://localhost:$TRAEFIK_PORT"

    echo -e "${CYAN}Testing Stock Data Service:${NC}"
    echo -n "  GET /stock_helper/api/v2/companies: "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/stock_helper/api/v2/companies" 2>/dev/null)
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}$RESPONSE OK${NC}"
    else
        echo -e "${YELLOW}$RESPONSE${NC}"
    fi

    echo -n "  GET /stock_helper/api/v2/market: "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/stock_helper/api/v2/market" 2>/dev/null)
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}$RESPONSE OK${NC}"
    else
        echo -e "${YELLOW}$RESPONSE${NC}"
    fi

    echo ""
    echo -e "${CYAN}Testing Auth Service:${NC}"
    echo -n "  GET /stock_helper/api/v2/auth: "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/stock_helper/api/v2/auth" 2>/dev/null)
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
        echo -e "${GREEN}$RESPONSE (service responding)${NC}"
    else
        echo -e "${YELLOW}$RESPONSE${NC}"
    fi

    echo ""
    echo -e "${CYAN}Testing Analysis Service:${NC}"
    echo -n "  GET /stock_helper/api/v2/analysis: "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/stock_helper/api/v2/analysis" 2>/dev/null)
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
        echo -e "${GREEN}$RESPONSE (service responding)${NC}"
    else
        echo -e "${YELLOW}$RESPONSE${NC}"
    fi

    echo ""
    echo -e "${CYAN}Testing Chatbot Service:${NC}"
    echo -n "  GET /stock_helper/api/v2/chat: "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/stock_helper/api/v2/chat" 2>/dev/null)
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
        echo -e "${GREEN}$RESPONSE (service responding)${NC}"
    else
        echo -e "${YELLOW}$RESPONSE${NC}"
    fi

    exit 0
fi

# =============================================================================
# Pre-deployment Checks
# =============================================================================
echo -e "${BLUE}Running pre-deployment checks...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker installed${NC}"

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo -e "${RED}Docker daemon is not running${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker daemon running${NC}"

# Check docker compose
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}Docker Compose is not installed${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker Compose available${NC}"

# Check port conflicts
echo -e "\n${BLUE}Checking port availability...${NC}"

check_port() {
    local port=$1
    local service=$2
    if ss -tlnp 2>/dev/null | grep -q ":$port " || netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        # Check if it's our own container
        if docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null | grep -q "stock_.*:$port->"; then
            echo -e "${GREEN}  Port $port ($service) - in use by stock container${NC}"
            return 0
        fi
        echo -e "${YELLOW}  Port $port ($service) is in use by another process${NC}"
        return 1
    fi
    echo -e "${GREEN}  Port $port ($service) is available${NC}"
    return 0
}

PORTS_OK=true
check_port $TRAEFIK_PORT "Traefik Gateway" || PORTS_OK=false
check_port $TRAEFIK_DASHBOARD_PORT "Traefik Dashboard" || PORTS_OK=false
check_port $RABBITMQ_MGMT_PORT "RabbitMQ Management" || true
check_port $PROMETHEUS_PORT "Prometheus" || true
check_port $GRAFANA_PORT "Grafana" || true

# Show existing projects' ports
echo -e "\n${BLUE}Existing project ports:${NC}"
echo -e "  ${CYAN}Ceramic:${NC} 8002 (Traefik), 8080 (Dashboard), 3308 (MySQL)"
echo -e "  ${CYAN}Math:${NC} 8003 (Traefik), 8083 (Dashboard), 3310 (MySQL)"
echo -e "  ${CYAN}Stock:${NC} $TRAEFIK_PORT (Traefik), $TRAEFIK_DASHBOARD_PORT (Dashboard)"

# =============================================================================
# Clean Up
# =============================================================================
if [ "$CLEAN_FLAG" = true ]; then
    echo -e "\n${YELLOW}Cleaning up existing containers and volumes...${NC}"
    $COMPOSE_CMD -f docker-compose.yml -f docker-compose.local.yml down -v --remove-orphans 2>/dev/null || true
    docker volume rm stock-rabbitmq-data stock-redis-data stock-prometheus-data stock-grafana-data stock-prediction-models 2>/dev/null || true
    echo -e "${GREEN}Cleanup complete${NC}"
fi

# =============================================================================
# Check Environment File
# =============================================================================
if [ ! -f .env ]; then
    if [ -f .env.local ]; then
        echo -e "${YELLOW}Creating .env from .env.local...${NC}"
        cp .env.local .env
    else
        echo -e "${RED}Error: .env file not found${NC}"
        exit 1
    fi
fi

# =============================================================================
# Deploy Services
# =============================================================================
echo -e "\n${CYAN}============================================${NC}"
echo -e "${CYAN}  Starting Stock Microservices${NC}"
echo -e "${CYAN}============================================${NC}"

# Use local compose file for development
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"

echo -e "\n${YELLOW}Building and starting services...${NC}"
$COMPOSE_CMD $COMPOSE_FILES up -d $BUILD_FLAG

# =============================================================================
# Wait for Services
# =============================================================================
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"

# Wait for infrastructure first
echo -e "${CYAN}Waiting for infrastructure...${NC}"
TIMEOUT=120
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    # Check if SSH tunnel is healthy
    if docker ps --filter "name=stock_ssh_tunnel" --filter "health=healthy" --format '{{.Names}}' | grep -q "stock_ssh_tunnel"; then
        echo -e "${GREEN}  SSH tunnel is healthy${NC}"
        break
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done
echo ""

# Wait a bit more for all services
sleep 10

# =============================================================================
# Verify Services
# =============================================================================
echo -e "\n${BLUE}Verifying services...${NC}"

SERVICES=(
    "stock_traefik:Traefik Gateway"
    "stock_redis:Redis Cache"
    "stock_rabbitmq:RabbitMQ"
    "stock_prometheus:Prometheus"
    "stock_grafana:Grafana"
    "stock_auth_service:Auth Service"
    "stock_data_service:Stock Data Service"
    "stock_portfolio_service:Portfolio Service"
    "stock_prediction_service:Prediction Service"
    "stock_analysis_service:Analysis Service"
    "stock_ai_insights_service:AI Insights Service"
    "stock_chatbot_service:Chatbot Service"
)

for svc in "${SERVICES[@]}"; do
    CONTAINER="${svc%%:*}"
    NAME="${svc##*:}"

    STATUS=$(docker ps --filter "name=$CONTAINER" --format '{{.Status}}' 2>/dev/null | head -1)
    if [ -n "$STATUS" ]; then
        if echo "$STATUS" | grep -q "healthy"; then
            echo -e "${GREEN}  [OK] $NAME - $STATUS${NC}"
        elif echo "$STATUS" | grep -q "Up"; then
            echo -e "${YELLOW}  [UP] $NAME - $STATUS${NC}"
        else
            echo -e "${RED}  [!] $NAME - $STATUS${NC}"
        fi
    else
        echo -e "${RED}  [!] $NAME - Not running${NC}"
    fi
done

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}  Deployment Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${BLUE}Service URLs:${NC}"
echo -e "  ${GREEN}API Gateway:${NC}           http://localhost:$TRAEFIK_PORT"
echo -e "  ${GREEN}API Base:${NC}              http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/"
echo -e "  ${GREEN}Traefik Dashboard:${NC}     http://localhost:$TRAEFIK_DASHBOARD_PORT"
echo -e "  ${GREEN}RabbitMQ Management:${NC}   http://localhost:$RABBITMQ_MGMT_PORT"
echo -e "  ${GREEN}Prometheus:${NC}            http://localhost:$PROMETHEUS_PORT"
echo -e "  ${GREEN}Grafana:${NC}               http://localhost:$GRAFANA_PORT"
echo -e "  ${GREEN}Jaeger:${NC}                http://localhost:$JAEGER_PORT"
echo ""
echo -e "${BLUE}API Endpoints:${NC}"
echo -e "  ${GREEN}Auth:${NC}        http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/auth"
echo -e "  ${GREEN}Stocks:${NC}      http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/stocks"
echo -e "  ${GREEN}Companies:${NC}   http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/companies"
echo -e "  ${GREEN}Market:${NC}      http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/market"
echo -e "  ${GREEN}Portfolio:${NC}   http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/portfolio"
echo -e "  ${GREEN}Predictions:${NC} http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/predictions"
echo -e "  ${GREEN}Analysis:${NC}    http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/analysis"
echo -e "  ${GREEN}AI:${NC}          http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/ai"
echo -e "  ${GREEN}Chat:${NC}        http://localhost:$TRAEFIK_PORT/stock_helper/api/v2/chat"
echo ""
echo -e "${BLUE}Management Commands:${NC}"
echo -e "  ${GREEN}Status:${NC}    $SCRIPT_DIR/deploy.sh --status"
echo -e "  ${GREEN}Health:${NC}    $SCRIPT_DIR/deploy.sh --health"
echo -e "  ${GREEN}Test:${NC}      $SCRIPT_DIR/deploy.sh --test"
echo -e "  ${GREEN}Logs:${NC}      $SCRIPT_DIR/deploy.sh --logs [service]"
echo -e "  ${GREEN}Stop:${NC}      $SCRIPT_DIR/deploy.sh --stop"
echo ""
echo -e "${CYAN}Port Allocation Summary:${NC}"
echo -e "  ${GREEN}Ceramic:${NC} 8002 | ${GREEN}Math:${NC} 8003 | ${GREEN}Stock:${NC} $TRAEFIK_PORT"
echo ""
