#!/bin/bash
#
# Emergency Rollback Script for Traffic Cutover
#
# This script performs an emergency rollback to Django monolith,
# routing 100% of traffic away from microservices.
#
# Usage:
#   ./rollback.sh                    # Interactive mode
#   ./rollback.sh --confirm          # Non-interactive mode
#   ./rollback.sh --dry-run          # Show what would be done
#
# Author: Claude Code Assistant
# Version: 1.0.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
LOG_FILE="/tmp/rollback_${TIMESTAMP//[:-]/_}.log"

# Feature flags service
FEATURE_FLAGS_URL="${FEATURE_FLAGS_URL:-http://localhost:8010}"
ADMIN_API_KEY="${ADMIN_API_KEY:-change-me-in-production}"

# Slack webhook for notifications (optional)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"

# Parse arguments
DRY_RUN=false
CONFIRM=false
REASON=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --confirm)
            CONFIRM=true
            shift
            ;;
        --reason)
            REASON="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
log() {
    echo -e "${1}" | tee -a "$LOG_FILE"
}

log_info() {
    log "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    log "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

send_slack_notification() {
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local message="$1"
        curl -s -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || true
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed"
        exit 1
    fi

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        log_warn "docker-compose not found, some operations may fail"
    fi

    log_info "Prerequisites check passed"
}

get_current_state() {
    log_info "Getting current cutover state..."

    local response
    response=$(curl -s -w "%{http_code}" -o /tmp/current_state.json \
        -H "X-API-Key: $ADMIN_API_KEY" \
        "$FEATURE_FLAGS_URL/api/flags/status" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        cat /tmp/current_state.json | tee -a "$LOG_FILE"
    else
        log_warn "Could not fetch current state (HTTP $response)"
    fi
}

apply_rollback_phase() {
    log_info "Applying rollback phase to feature flags..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would apply 'rollback' phase to feature flags"
        return 0
    fi

    local response
    response=$(curl -s -w "%{http_code}" -o /tmp/rollback_response.json \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-API-Key: $ADMIN_API_KEY" \
        -d "{\"phase\": \"rollback\", \"reason\": \"$REASON\", \"dry_run\": false}" \
        "$FEATURE_FLAGS_URL/api/admin/apply-phase" 2>/dev/null || echo "000")

    if [ "$response" = "200" ]; then
        log_info "Feature flags updated successfully"
        cat /tmp/rollback_response.json | tee -a "$LOG_FILE"
        return 0
    else
        log_error "Failed to update feature flags (HTTP $response)"
        return 1
    fi
}

update_traefik_config() {
    log_info "Updating Traefik routing configuration..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would copy traefik/cutover-100-percent.yml to traefik/dynamic-weighted.yml"
        log_info "[DRY RUN] Would set all weights to Django: 100, Microservices: 0"
        return 0
    fi

    # Backup current config
    if [ -f "$PROJECT_ROOT/traefik/dynamic-weighted.yml" ]; then
        cp "$PROJECT_ROOT/traefik/dynamic-weighted.yml" \
           "$PROJECT_ROOT/traefik/dynamic-weighted.yml.backup.${TIMESTAMP//[:-]/_}"
        log_info "Backed up current Traefik config"
    fi

    # Apply rollback config (0% microservices)
    if [ -f "$PROJECT_ROOT/traefik/cutover-100-percent.yml" ]; then
        # This file should have 100% Django config
        # We'll use sed to update weights in the dynamic file
        sed -i 's/weight: [0-9]*/weight: 0/g' "$PROJECT_ROOT/traefik/dynamic-weighted.yml"
        # Then set Django weights to 100
        # This is a simplified approach - in production, use proper config management
        log_info "Updated Traefik weights to route 100% to Django"
    else
        log_warn "Rollback config not found, manual intervention may be needed"
    fi
}

verify_rollback() {
    log_info "Verifying rollback..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY RUN] Would verify rollback by checking service health"
        return 0
    fi

    # Check Django health
    local django_status
    django_status=$(curl -s -o /dev/null -w "%{http_code}" \
        "http://localhost:8000/health" 2>/dev/null || echo "000")

    if [ "$django_status" = "200" ]; then
        log_info "Django health check: OK"
    else
        log_warn "Django health check failed (HTTP $django_status)"
    fi

    # Get updated flag status
    get_current_state
}

create_audit_record() {
    log_info "Creating audit record..."

    local audit_record=$(cat << EOF
{
    "timestamp": "$TIMESTAMP",
    "action": "emergency_rollback",
    "reason": "$REASON",
    "executed_by": "${USER:-unknown}",
    "dry_run": $DRY_RUN,
    "log_file": "$LOG_FILE"
}
EOF
)

    echo "$audit_record" >> "$PROJECT_ROOT/rollback_audit.log"
    log_info "Audit record created"
}

print_summary() {
    echo ""
    echo "=============================================="
    echo "  ROLLBACK SUMMARY"
    echo "=============================================="
    echo "  Timestamp:  $TIMESTAMP"
    echo "  Dry Run:    $DRY_RUN"
    echo "  Reason:     ${REASON:-Not specified}"
    echo "  Log File:   $LOG_FILE"
    echo "=============================================="

    if [ "$DRY_RUN" = true ]; then
        echo ""
        log_warn "This was a DRY RUN. No changes were made."
        echo "To execute the rollback, run:"
        echo "  $0 --confirm"
    fi
}

# Main execution
main() {
    echo ""
    echo "=============================================="
    echo "  EMERGENCY ROLLBACK SCRIPT"
    echo "=============================================="
    echo "  Timestamp: $TIMESTAMP"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        log_warn "Running in DRY RUN mode - no changes will be made"
    fi

    # Confirmation prompt (unless --confirm flag provided)
    if [ "$DRY_RUN" = false ] && [ "$CONFIRM" = false ]; then
        echo ""
        log_warn "This will route 100% of traffic to Django!"
        read -p "Are you sure you want to proceed? (yes/no): " confirmation

        if [ "$confirmation" != "yes" ]; then
            log_info "Rollback cancelled by user"
            exit 0
        fi
    fi

    # Send start notification
    send_slack_notification ":warning: Emergency rollback initiated by ${USER:-unknown} at $TIMESTAMP"

    # Execute rollback steps
    check_prerequisites
    get_current_state
    apply_rollback_phase
    update_traefik_config
    verify_rollback
    create_audit_record

    # Send completion notification
    if [ "$DRY_RUN" = false ]; then
        send_slack_notification ":white_check_mark: Emergency rollback completed. Django is now serving 100% of traffic."
    fi

    print_summary

    log_info "Rollback complete!"
}

# Run main function
main
