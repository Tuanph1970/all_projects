#!/bin/bash
# =============================================================================
# Service Status - Ceramic + Stock Helper
# =============================================================================
# Usage:
#   ./status.sh [options]
#
# Options:
#   --ceramic     Show only Ceramic status
#   --stock       Show only Stock Helper status
#   --health      Include health check details
#   --ports       Show port usage
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
SHOW_CERAMIC=true
SHOW_STOCK=true
SHOW_HEALTH=false
SHOW_PORTS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ceramic)
            SHOW_CERAMIC=true
            SHOW_STOCK=false
            shift
            ;;
        --stock)
            SHOW_CERAMIC=false
            SHOW_STOCK=true
            shift
            ;;
        --health)
            SHOW_HEALTH=true
            shift
            ;;
        --ports)
            SHOW_PORTS=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${CYAN}"
echo "============================================"
echo "       Service Status Dashboard"
echo "============================================"
echo -e "${NC}"

# Function to check service health
check_health() {
    local url=$1
    local name=$2
    local timeout=${3:-5}

    if curl -sf --max-time $timeout "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name${NC}"
        return 0
    else
        echo -e "${RED}✗ $name${NC}"
        return 1
    fi
}

# Function to check container status
check_container() {
    local name=$1
    local status=$(docker ps --filter "name=$name" --format "{{.Status}}" 2>/dev/null)

    if [ -n "$status" ]; then
        if [[ "$status" == *"Up"* ]]; then
            echo -e "${GREEN}✓ $name: $status${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ $name: $status${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ $name: Not running${NC}"
        return 1
    fi
}

# =============================================================================
# Ceramic API Status
# =============================================================================
if [ "$SHOW_CERAMIC" = true ]; then
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        CERAMIC API STATUS                ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${YELLOW}Container:${NC}"
    check_container "ceramic_api"

    if [ "$SHOW_HEALTH" = true ]; then
        echo ""
        echo -e "${YELLOW}Health Checks:${NC}"
        check_health "http://localhost:8002/health" "API Health"
        check_health "http://localhost:8002/api/docs" "API Docs"
    fi

    echo ""
fi

# =============================================================================
# Stock Helper Status
# =============================================================================
if [ "$SHOW_STOCK" = true ]; then
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     STOCK HELPER MICROSERVICES           ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${YELLOW}Core Services:${NC}"
    check_container "stock_data_service"
    check_container "portfolio_service"
    check_container "analysis_service"
    check_container "ai_insights_service"
    check_container "chatbot_service"
    check_container "auth_service"
    check_container "prediction_service"

    echo ""
    echo -e "${YELLOW}Infrastructure:${NC}"
    check_container "stock_traefik"
    check_container "stock_redis"
    check_container "stock_rabbitmq"

    echo ""
    echo -e "${YELLOW}Monitoring:${NC}"
    check_container "stock_grafana"
    check_container "stock_prometheus"
    check_container "stock_jaeger"

    if [ "$SHOW_HEALTH" = true ]; then
        echo ""
        echo -e "${YELLOW}Service Health Checks:${NC}"

        SERVICES=(
            "8001:Stock Data"
            "8003:Portfolio"
            "8004:Analysis"
            "8005:AI Insights"
            "8006:Chatbot"
            "8007:Auth"
        )

        for svc in "${SERVICES[@]}"; do
            PORT="${svc%%:*}"
            NAME="${svc##*:}"
            check_health "http://localhost:$PORT/health/live" "$NAME Service"
        done

        echo ""
        echo -e "${YELLOW}Gateway Health:${NC}"
        check_health "http://localhost:8088/stock_helper/api/v2/stock-data/health/live" "Traefik Gateway"
    fi

    echo ""
fi

# =============================================================================
# Port Usage
# =============================================================================
if [ "$SHOW_PORTS" = true ]; then
    echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           PORT USAGE                     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
    echo ""

    echo -e "${YELLOW}Project Ports:${NC}"

    PORTS=(
        "80:System Nginx"
        "3001:React Dev Server"
        "3100:Grafana"
        "3306:MySQL"
        "6379:Native Redis"
        "6380:Stock Redis"
        "8001:Stock Data Service"
        "8002:Ceramic API"
        "8003:Portfolio Service"
        "8004:Analysis Service"
        "8005:AI Insights Service"
        "8006:Chatbot Service"
        "8007:Auth Service"
        "8088:Stock Traefik"
        "8089:Traefik Dashboard"
        "9090:Prometheus"
        "15672:RabbitMQ Management"
        "16686:Jaeger UI"
    )

    for item in "${PORTS[@]}"; do
        PORT="${item%%:*}"
        NAME="${item##*:}"

        if ss -tlnp 2>/dev/null | grep -q ":$PORT " || netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
            echo -e "  ${GREEN}●${NC} Port $PORT: $NAME"
        else
            echo -e "  ${RED}○${NC} Port $PORT: $NAME (not in use)"
        fi
    done

    echo ""
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              SUMMARY                     ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# Count running containers
CERAMIC_COUNT=$(docker ps --filter "name=ceramic" --format "{{.Names}}" 2>/dev/null | wc -l)
STOCK_COUNT=$(docker ps --filter "name=stock" --format "{{.Names}}" 2>/dev/null | wc -l)

echo -e "  Ceramic containers running: ${GREEN}$CERAMIC_COUNT${NC}"
echo -e "  Stock Helper containers running: ${GREEN}$STOCK_COUNT${NC}"
echo ""

# Quick URLs
echo -e "${YELLOW}Quick Access URLs:${NC}"
echo -e "  Ceramic API:      http://localhost:8002"
echo -e "  Stock Gateway:    http://localhost:8088"
echo -e "  React App:        http://localhost:3001"
echo -e "  Grafana:          http://localhost:3100"
echo -e "  Traefik:          http://localhost:8089"
echo ""
