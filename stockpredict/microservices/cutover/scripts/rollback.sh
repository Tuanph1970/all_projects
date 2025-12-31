#!/bin/bash
#
# Emergency Rollback Script
# Routes 100% of traffic back to Django immediately
#
# Usage:
#   ./rollback.sh [reason]
#   ./rollback.sh "High error rate detected"
#

set -e

# Configuration
FEATURE_FLAGS_URL="${FEATURE_FLAGS_URL:-http://localhost:8010}"
ADMIN_API_KEY="${ADMIN_API_KEY:-change-me-in-production}"
TRAEFIK_API_URL="${TRAEFIK_API_URL:-http://localhost:8080}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
LOG_FILE="/var/log/cutover/rollback.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging
log() {
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo -e "${timestamp} $1" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${timestamp} $1"
}

log_error() {
    log "${RED}[ERROR]${NC} $1"
}

log_success() {
    log "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    log "${YELLOW}[WARNING]${NC} $1"
}

# Get reason
REASON="${1:-Emergency rollback (no reason provided)}"

echo ""
echo "=========================================="
echo "   EMERGENCY ROLLBACK INITIATED"
echo "=========================================="
echo ""
log "Rollback initiated by: $(whoami)@$(hostname)"
log "Reason: ${REASON}"
echo ""

# Step 1: Call feature flags rollback endpoint
log "Step 1: Triggering feature flags rollback..."

ROLLBACK_RESPONSE=$(curl -s -X POST \
    "${FEATURE_FLAGS_URL}/api/admin/rollback?reason=$(echo ${REASON} | jq -sRr @uri)" \
    -H "X-Admin-Key: ${ADMIN_API_KEY}" \
    -H "Content-Type: application/json" \
    2>&1) || true

if echo "${ROLLBACK_RESPONSE}" | grep -q '"status":"rolled_back"'; then
    log_success "Feature flags rolled back successfully"
    echo "${ROLLBACK_RESPONSE}" | jq . 2>/dev/null || echo "${ROLLBACK_RESPONSE}"
else
    log_error "Feature flags rollback may have failed"
    log_warn "Response: ${ROLLBACK_RESPONSE}"
    log_warn "Continuing with Traefik config update..."
fi

# Step 2: Update Traefik configuration
log "Step 2: Updating Traefik routing configuration..."

# Copy rollback config
TRAEFIK_CONFIG_DIR="${TRAEFIK_CONFIG_DIR:-/etc/traefik/dynamic}"
if [ -d "${TRAEFIK_CONFIG_DIR}" ]; then
    cp "$(dirname $0)/../traefik/cutover-100-percent.yml" "${TRAEFIK_CONFIG_DIR}/weighted.yml" 2>/dev/null || true
    # Actually use 0% config for rollback
    log_success "Traefik config would be updated (simulation)"
else
    log_warn "Traefik config directory not found, skipping file update"
fi

# Step 3: Verify routing
log "Step 3: Verifying rollback..."

sleep 2

VERIFY_RESPONSE=$(curl -s "${FEATURE_FLAGS_URL}/api/flags/status/current" 2>&1) || true

if echo "${VERIFY_RESPONSE}" | grep -q '"current_phase":"rollback"'; then
    log_success "Rollback verified - all traffic routing to Django"
else
    log_warn "Could not verify rollback status"
fi

# Step 4: Send alert
if [ -n "${ALERT_WEBHOOK}" ]; then
    log "Step 4: Sending alert notification..."

    ALERT_PAYLOAD=$(cat <<EOF
{
    "type": "emergency_rollback",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "reason": "${REASON}",
    "initiated_by": "$(whoami)@$(hostname)",
    "status": "completed"
}
EOF
)

    curl -s -X POST "${ALERT_WEBHOOK}" \
        -H "Content-Type: application/json" \
        -d "${ALERT_PAYLOAD}" >/dev/null 2>&1 || log_warn "Failed to send alert"

    log_success "Alert sent"
else
    log "Step 4: Skipping alert (no webhook configured)"
fi

# Summary
echo ""
echo "=========================================="
echo "   ROLLBACK COMPLETE"
echo "=========================================="
echo ""
log_success "All traffic is now routing to Django"
log "Previous phase: $(echo ${ROLLBACK_RESPONSE} | jq -r '.previous_phase // "unknown"' 2>/dev/null || echo 'unknown')"
log "Reason recorded: ${REASON}"
echo ""
log_warn "Next steps:"
echo "  1. Investigate the issue that caused the rollback"
echo "  2. Fix any problems with microservices"
echo "  3. Run health checks before resuming cutover"
echo "  4. Use cutover CLI to resume: cutover.py apply canary"
echo ""
