#!/bin/bash
# =============================================================================
# Service Logs Viewer - Ceramic + Stock Helper
# =============================================================================
# Usage:
#   ./logs.sh [service] [options]
#
# Services:
#   ceramic         Ceramic API logs
#   stock-data      Stock Data Service logs
#   portfolio       Portfolio Service logs
#   analysis        Analysis Service logs
#   ai-insights     AI Insights Service logs
#   chatbot         Chatbot Service logs
#   auth            Auth Service logs
#   prediction      Prediction Service logs
#   traefik         Traefik Gateway logs
#   redis           Redis logs
#   rabbitmq        RabbitMQ logs
#   grafana         Grafana logs
#   prometheus      Prometheus logs
#   jaeger          Jaeger logs
#   all             All services (brief)
#
# Options:
#   -f, --follow    Follow log output
#   -n, --lines N   Number of lines to show (default: 100)
#   --since TIME    Show logs since timestamp (e.g., 10m, 1h, 2023-01-01)
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
BASE_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CERAMIC_DIR="$BASE_DIR/../ceramic_mobile_app/back_end"
STOCK_DIR="$BASE_DIR/stock_microservices"

# Default options
SERVICE=""
FOLLOW=""
LINES="100"
SINCE=""

# Service to container mapping
declare -A SERVICE_MAP=(
    ["ceramic"]="ceramic_api"
    ["stock-data"]="stock_data_service"
    ["portfolio"]="portfolio_service"
    ["analysis"]="analysis_service"
    ["ai-insights"]="ai_insights_service"
    ["chatbot"]="chatbot_service"
    ["auth"]="auth_service"
    ["prediction"]="prediction_service"
    ["traefik"]="stock_traefik"
    ["redis"]="stock_redis"
    ["rabbitmq"]="stock_rabbitmq"
    ["grafana"]="stock_grafana"
    ["prometheus"]="stock_prometheus"
    ["jaeger"]="stock_jaeger"
)

# Print usage
print_usage() {
    head -35 "$0" | tail -30
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        --since)
            SINCE="--since $2"
            shift 2
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            if [ -z "$SERVICE" ]; then
                SERVICE="$1"
            else
                echo -e "${RED}Unknown option: $1${NC}"
                exit 1
            fi
            shift
            ;;
    esac
done

# If no service specified, show list
if [ -z "$SERVICE" ]; then
    echo -e "${CYAN}"
    echo "============================================"
    echo "       Available Services"
    echo "============================================"
    echo -e "${NC}"

    echo -e "${YELLOW}Ceramic:${NC}"
    echo "  ceramic         - Ceramic API"
    echo ""

    echo -e "${YELLOW}Stock Helper Services:${NC}"
    echo "  stock-data      - Stock Data Service"
    echo "  portfolio       - Portfolio Service"
    echo "  analysis        - Analysis Service"
    echo "  ai-insights     - AI Insights Service"
    echo "  chatbot         - Chatbot Service"
    echo "  auth            - Auth Service"
    echo "  prediction      - Prediction Service"
    echo ""

    echo -e "${YELLOW}Infrastructure:${NC}"
    echo "  traefik         - API Gateway"
    echo "  redis           - Redis Cache"
    echo "  rabbitmq        - Message Queue"
    echo ""

    echo -e "${YELLOW}Monitoring:${NC}"
    echo "  grafana         - Grafana Dashboard"
    echo "  prometheus      - Metrics Server"
    echo "  jaeger          - Tracing"
    echo ""

    echo -e "${YELLOW}Special:${NC}"
    echo "  all             - Brief logs from all services"
    echo ""

    echo -e "${BLUE}Usage: ./logs.sh <service> [-f] [-n lines] [--since time]${NC}"
    exit 0
fi

# Handle 'all' service
if [ "$SERVICE" = "all" ]; then
    echo -e "${CYAN}"
    echo "============================================"
    echo "       All Services Logs (Brief)"
    echo "============================================"
    echo -e "${NC}"

    for svc_name in "${!SERVICE_MAP[@]}"; do
        container="${SERVICE_MAP[$svc_name]}"
        echo -e "${YELLOW}=== $svc_name ($container) ===${NC}"

        if docker ps --filter "name=$container" --format "{{.Names}}" 2>/dev/null | grep -q "$container"; then
            docker logs --tail 10 "$container" 2>&1 | head -10 || true
        else
            echo -e "${RED}Not running${NC}"
        fi
        echo ""
    done
    exit 0
fi

# Get container name
CONTAINER="${SERVICE_MAP[$SERVICE]}"

if [ -z "$CONTAINER" ]; then
    echo -e "${RED}Unknown service: $SERVICE${NC}"
    echo ""
    echo "Available services:"
    for svc in "${!SERVICE_MAP[@]}"; do
        echo "  - $svc"
    done
    exit 1
fi

# Check if container is running
if ! docker ps --filter "name=$CONTAINER" --format "{{.Names}}" 2>/dev/null | grep -q "$CONTAINER"; then
    echo -e "${RED}Container '$CONTAINER' is not running${NC}"
    echo ""
    echo "Start the service first with:"
    echo "  ./deploy-all.sh --stock-only  (for Stock Helper services)"
    echo "  ./deploy-all.sh --ceramic-only (for Ceramic API)"
    exit 1
fi

# Show logs
echo -e "${CYAN}"
echo "============================================"
echo "       Logs: $SERVICE ($CONTAINER)"
echo "============================================"
echo -e "${NC}"

if [ -n "$FOLLOW" ]; then
    echo -e "${YELLOW}Following logs... (Ctrl+C to exit)${NC}"
    echo ""
fi

# Build docker logs command
CMD="docker logs --tail $LINES $SINCE $FOLLOW $CONTAINER"

eval $CMD
