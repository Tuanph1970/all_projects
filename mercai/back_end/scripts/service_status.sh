#!/bin/bash
# =============================================================================
# Mercai - Service Status Monitor
# =============================================================================
# Usage: ./scripts/service_status.sh [options]
# Options:
#   -w, --watch      Continuous monitoring mode
#   -i, --interval   Refresh interval in seconds (default: 5)
#   -h, --help       Show help message
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Configuration
WATCH_MODE=false
INTERVAL=5
COMPOSE_FILE="docker-compose.microservices.yml"

# Service list
SERVICES=("traefik" "db" "redis" "auth-service" "product-service" "order-service" "chat-service" "seller-service")
CONTAINER_PREFIX="mercai"

show_help() {
    echo "Mercai - Service Status Monitor"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -w, --watch      Continuous monitoring mode"
    echo "  -i, --interval   Refresh interval in seconds (default: 5)"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Show current status"
    echo "  $0 -w                 # Watch mode with 5s refresh"
    echo "  $0 -w -i 10           # Watch mode with 10s refresh"
}

get_container_name() {
    local service=$1
    case $service in
        "db") echo "${CONTAINER_PREFIX}_mysql" ;;
        "redis") echo "${CONTAINER_PREFIX}_redis" ;;
        "traefik") echo "${CONTAINER_PREFIX}_traefik" ;;
        *) echo "${CONTAINER_PREFIX}_${service//-/_}" ;;
    esac
}

get_container_status() {
    local container=$1
    docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "not_found"
}

get_container_health() {
    local container=$1
    docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$container" 2>/dev/null || echo "unknown"
}

get_container_uptime() {
    local container=$1
    local started=$(docker inspect --format='{{.State.StartedAt}}' "$container" 2>/dev/null)
    if [ -n "$started" ] && [ "$started" != "" ]; then
        local start_ts=$(date -d "$started" +%s 2>/dev/null || echo "0")
        local now_ts=$(date +%s)
        local diff=$((now_ts - start_ts))

        if [ $diff -lt 60 ]; then
            echo "${diff}s"
        elif [ $diff -lt 3600 ]; then
            echo "$((diff / 60))m"
        elif [ $diff -lt 86400 ]; then
            echo "$((diff / 3600))h $((diff % 3600 / 60))m"
        else
            echo "$((diff / 86400))d $((diff % 86400 / 3600))h"
        fi
    else
        echo "N/A"
    fi
}

get_container_memory() {
    local container=$1
    docker stats --no-stream --format "{{.MemUsage}}" "$container" 2>/dev/null | cut -d'/' -f1 || echo "N/A"
}

get_container_cpu() {
    local container=$1
    docker stats --no-stream --format "{{.CPUPerc}}" "$container" 2>/dev/null || echo "N/A"
}

get_container_ports() {
    local container=$1
    docker port "$container" 2>/dev/null | head -1 | awk '{print $3}' || echo "N/A"
}

get_restart_count() {
    local container=$1
    docker inspect --format='{{.RestartCount}}' "$container" 2>/dev/null || echo "0"
}

format_status() {
    local status=$1
    case $status in
        "running") echo -e "${GREEN}●${NC} Running" ;;
        "exited") echo -e "${RED}○${NC} Exited" ;;
        "restarting") echo -e "${YELLOW}↻${NC} Restarting" ;;
        "paused") echo -e "${YELLOW}❚❚${NC} Paused" ;;
        "not_found") echo -e "${RED}✗${NC} Not Found" ;;
        *) echo -e "${YELLOW}?${NC} $status" ;;
    esac
}

format_health() {
    local health=$1
    case $health in
        "healthy") echo -e "${GREEN}✓${NC}" ;;
        "unhealthy") echo -e "${RED}✗${NC}" ;;
        "starting") echo -e "${YELLOW}...${NC}" ;;
        "no_healthcheck") echo -e "${CYAN}-${NC}" ;;
        *) echo -e "${YELLOW}?${NC}" ;;
    esac
}

print_header() {
    clear
    echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${BLUE}║${NC}           ${BOLD}MERCAI - MICROSERVICES STATUS${NC}                           ${BOLD}${BLUE}║${NC}"
    echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Last updated: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    if [ "$WATCH_MODE" = true ]; then
        echo -e "${CYAN}Refresh interval: ${INTERVAL}s (Press Ctrl+C to exit)${NC}"
    fi
    echo ""
}

print_table_header() {
    printf "${BOLD}%-20s %-15s %-8s %-12s %-12s %-10s %-10s${NC}\n" \
        "SERVICE" "STATUS" "HEALTH" "UPTIME" "MEMORY" "CPU" "RESTARTS"
    echo "────────────────────────────────────────────────────────────────────────────────"
}

print_service_row() {
    local service=$1
    local container=$(get_container_name "$service")

    local status=$(get_container_status "$container")
    local health=$(get_container_health "$container")
    local uptime=$(get_container_uptime "$container")
    local memory=$(get_container_memory "$container")
    local cpu=$(get_container_cpu "$container")
    local restarts=$(get_restart_count "$container")

    local status_fmt=$(format_status "$status")
    local health_fmt=$(format_health "$health")

    printf "%-20s %-15b %-8b %-12s %-12s %-10s %-10s\n" \
        "$service" "$status_fmt" "$health_fmt" "$uptime" "$memory" "$cpu" "$restarts"
}

print_network_info() {
    echo ""
    echo -e "${BOLD}${MAGENTA}Network Information:${NC}"
    echo "────────────────────────────────────────────────────────────────────────────────"

    # Get network info
    local network_name="back_end_mercai_network"
    if docker network inspect "$network_name" &>/dev/null; then
        local subnet=$(docker network inspect "$network_name" --format='{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null)
        echo -e "Network: ${CYAN}$network_name${NC}"
        echo -e "Subnet:  ${CYAN}$subnet${NC}"
    else
        echo -e "${YELLOW}Network not found${NC}"
    fi
}

print_endpoints() {
    echo ""
    echo -e "${BOLD}${MAGENTA}Service Endpoints:${NC}"
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo -e "API Gateway:       ${CYAN}http://localhost:80${NC}"
    echo -e "Traefik Dashboard: ${CYAN}http://localhost:8080${NC}"
    echo ""
    echo -e "Auth Service:      ${CYAN}/api/v1/auth${NC}, ${CYAN}/api/v1/users${NC}"
    echo -e "Product Service:   ${CYAN}/api/v1/products${NC}, ${CYAN}/api/v1/reviews${NC}"
    echo -e "Order Service:     ${CYAN}/api/v1/orders${NC}, ${CYAN}/api/v1/cart${NC}"
    echo -e "Chat Service:      ${CYAN}/api/v1/chat${NC}"
    echo -e "Seller Service:    ${CYAN}/api/v1/seller${NC}"
}

print_quick_commands() {
    echo ""
    echo -e "${BOLD}${MAGENTA}Quick Commands:${NC}"
    echo "────────────────────────────────────────────────────────────────────────────────"
    echo -e "Start all:    ${CYAN}docker-compose -f $COMPOSE_FILE up -d${NC}"
    echo -e "Stop all:     ${CYAN}docker-compose -f $COMPOSE_FILE down${NC}"
    echo -e "View logs:    ${CYAN}docker-compose -f $COMPOSE_FILE logs -f [service]${NC}"
    echo -e "Restart:      ${CYAN}docker-compose -f $COMPOSE_FILE restart [service]${NC}"
    echo -e "Health check: ${CYAN}./scripts/health_check.sh -v${NC}"
}

show_status() {
    print_header
    print_table_header

    # Infrastructure services
    echo -e "${BOLD}Infrastructure:${NC}"
    for service in "traefik" "db" "redis"; do
        print_service_row "$service"
    done

    echo ""
    echo -e "${BOLD}Microservices:${NC}"
    for service in "auth-service" "product-service" "order-service" "chat-service" "seller-service"; do
        print_service_row "$service"
    done

    print_network_info
    print_endpoints
    print_quick_commands
}

# =============================================================================
# Main
# =============================================================================

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -w|--watch)
            WATCH_MODE=true
            shift
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "Error: docker is required but not installed"
    exit 1
fi

# Run
if [ "$WATCH_MODE" = true ]; then
    while true; do
        show_status
        sleep "$INTERVAL"
    done
else
    show_status
fi
