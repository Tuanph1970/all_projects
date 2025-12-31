#!/bin/bash
# Distributed load test runner for Stock Helper microservices
# Uses Locust in master/worker mode for high-scale testing

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
HOST="${HOST:-http://localhost}"
WORKERS="${WORKERS:-4}"
MASTER_PORT="${MASTER_PORT:-5557}"
LOCUST_FILE="${LOCUST_FILE:-locustfile.py}"
USERS="${USERS:-100}"
SPAWN_RATE="${SPAWN_RATE:-10}"
RUN_TIME="${RUN_TIME:-5m}"
REPORT_DIR="${REPORT_DIR:-./reports}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         Stock Helper Distributed Load Testing               ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start distributed test (master + workers)"
    echo "  master      Start master node only"
    echo "  worker      Start worker node only"
    echo "  stop        Stop all running nodes"
    echo "  status      Check status of nodes"
    echo ""
    echo "Options:"
    echo "  --host URL         Target host"
    echo "  --workers N        Number of worker processes (default: 4)"
    echo "  --users N          Number of users"
    echo "  --spawn-rate N     Users per second"
    echo "  --run-time T       Test duration"
    echo "  --master-host H    Master hostname (for workers)"
    echo "  --master-port P    Master port (default: 5557)"
    echo ""
    echo "Examples:"
    echo "  $0 start --workers 8 --users 500"
    echo "  $0 master --host http://api.example.com"
    echo "  $0 worker --master-host 192.168.1.100"
}

cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    pkill -f "locust.*--master" 2>/dev/null || true
    pkill -f "locust.*--worker" 2>/dev/null || true
}

start_master() {
    cd "$SCRIPT_DIR"

    mkdir -p "$REPORT_DIR"
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    REPORT_PREFIX="${REPORT_DIR}/distributed_${TIMESTAMP}"

    echo -e "${GREEN}Starting master node...${NC}"

    locust -f "$LOCUST_FILE" \
        --master \
        --master-bind-port="$MASTER_PORT" \
        --host="$HOST" \
        --headless \
        --users "$USERS" \
        --spawn-rate "$SPAWN_RATE" \
        --run-time "$RUN_TIME" \
        --expect-workers "$WORKERS" \
        --html "${REPORT_PREFIX}.html" \
        --csv "${REPORT_PREFIX}" &

    MASTER_PID=$!
    echo "Master started with PID: $MASTER_PID"
    echo "$MASTER_PID" > /tmp/locust_master.pid
}

start_workers() {
    cd "$SCRIPT_DIR"

    local master_host="${MASTER_HOST:-localhost}"

    echo -e "${GREEN}Starting $WORKERS worker(s)...${NC}"

    for i in $(seq 1 $WORKERS); do
        locust -f "$LOCUST_FILE" \
            --worker \
            --master-host="$master_host" \
            --master-port="$MASTER_PORT" &

        echo "Worker $i started with PID: $!"
    done
}

start_distributed() {
    echo -e "${BLUE}Starting distributed load test${NC}"
    echo "  Workers:    $WORKERS"
    echo "  Users:      $USERS"
    echo "  Spawn Rate: $SPAWN_RATE"
    echo "  Duration:   $RUN_TIME"
    echo ""

    # Trap to clean up on exit
    trap cleanup EXIT

    start_master
    sleep 2  # Wait for master to start

    start_workers

    echo ""
    echo -e "${GREEN}Distributed test running...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""

    # Wait for master to complete
    wait $MASTER_PID
}

stop_all() {
    echo -e "${YELLOW}Stopping all Locust processes...${NC}"

    if [ -f /tmp/locust_master.pid ]; then
        kill $(cat /tmp/locust_master.pid) 2>/dev/null || true
        rm /tmp/locust_master.pid
    fi

    pkill -f "locust" 2>/dev/null || true

    echo -e "${GREEN}All processes stopped${NC}"
}

check_status() {
    echo -e "${BLUE}Locust Process Status${NC}"
    echo ""

    if pgrep -f "locust.*--master" > /dev/null; then
        echo -e "  Master: ${GREEN}Running${NC}"
        pgrep -af "locust.*--master" | head -1
    else
        echo -e "  Master: ${RED}Not running${NC}"
    fi

    echo ""

    worker_count=$(pgrep -cf "locust.*--worker" 2>/dev/null || echo 0)
    if [ "$worker_count" -gt 0 ]; then
        echo -e "  Workers: ${GREEN}$worker_count running${NC}"
    else
        echo -e "  Workers: ${RED}None running${NC}"
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --host)
                HOST="$2"
                shift 2
                ;;
            --workers)
                WORKERS="$2"
                shift 2
                ;;
            --users)
                USERS="$2"
                shift 2
                ;;
            --spawn-rate)
                SPAWN_RATE="$2"
                shift 2
                ;;
            --run-time)
                RUN_TIME="$2"
                shift 2
                ;;
            --master-host)
                MASTER_HOST="$2"
                shift 2
                ;;
            --master-port)
                MASTER_PORT="$2"
                shift 2
                ;;
            --file)
                LOCUST_FILE="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
}

main() {
    print_banner

    if [ $# -eq 0 ]; then
        print_usage
        exit 0
    fi

    COMMAND="$1"
    shift
    parse_args "$@"

    case $COMMAND in
        start)
            start_distributed
            ;;
        master)
            start_master
            wait
            ;;
        worker)
            start_workers
            wait
            ;;
        stop)
            stop_all
            ;;
        status)
            check_status
            ;;
        --help|-h)
            print_usage
            ;;
        *)
            echo -e "${RED}Unknown command: $COMMAND${NC}"
            print_usage
            exit 1
            ;;
    esac
}

main "$@"
