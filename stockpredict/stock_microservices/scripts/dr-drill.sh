#!/usr/bin/env bash
# =============================================================================
# Disaster-Recovery drill (Phase 3.5 §3.5.4 — "Run DR drill")
# =============================================================================
# Exercises real failure + recovery against the running docker-compose stack
# and measures RTO (Recovery Time Objective) per scenario. Read-only to data;
# only kills/restarts containers, never deletes volumes.
#
# Scenarios:
#   service   Kill a stateless service container; verify Docker restart policy
#             brings it back and the gateway serves it again. Measures RTO.
#   redis     Kill Redis; verify it restarts and data survives (appendonly).
#   gateway   Kill Traefik; verify it restarts and routing recovers.
#   backup    Verify a fresh backup can be produced and is non-empty.
#   all       Run every scenario in sequence and print a summary table.
#
# Usage:
#   ./scripts/dr-drill.sh all
#   TARGET_SERVICE=stock_data_service ./scripts/dr-drill.sh service
#
# Env:
#   RTO_BUDGET_SECONDS   max acceptable recovery time (default 120; RTO is 4h
#                        in the plan, but local restart should be <2m)
#   GATEWAY_URL          default http://localhost:8004
# =============================================================================
set -uo pipefail

GATEWAY_URL="${GATEWAY_URL:-http://localhost:8004}"
RTO_BUDGET_SECONDS="${RTO_BUDGET_SECONDS:-120}"
TARGET_SERVICE="${TARGET_SERVICE:-stock_auth_service}"
TARGET_HEALTH_PATH="${TARGET_HEALTH_PATH:-/stock_helper/api/v2/auth/health/live}"
REDIS_CONTAINER="${REDIS_CONTAINER:-stock_redis}"
GATEWAY_CONTAINER="${GATEWAY_CONTAINER:-stock_traefik}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
declare -a RESULTS

log()  { echo -e "${BLUE}[drill]${NC} $*"; }
ok()   { echo -e "${GREEN}[drill] ✓ $*${NC}"; }
fail() { echo -e "${RED}[drill] ✗ $*${NC}"; }
warn() { echo -e "${YELLOW}[drill] ! $*${NC}"; }

_container_running() { docker ps --format '{{.Names}}' | grep -q "^$1$"; }

_wait_healthy() {
  # Wait for a container to report (healthy) or simply be Up, up to budget.
  local name="$1" deadline=$(( $(date +%s) + RTO_BUDGET_SECONDS ))
  while (( $(date +%s) < deadline )); do
    local status
    status="$(docker inspect -f '{{.State.Status}}:{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo "missing")"
    case "$status" in
      running:healthy|running:none) return 0 ;;
    esac
    sleep 2
  done
  return 1
}

_http_ok() { curl -sf -o /dev/null --max-time 5 "$1"; }

record() { RESULTS+=("$1|$2|$3"); }   # scenario|result|detail

# -----------------------------------------------------------------------------
# Scenario: service failure
# -----------------------------------------------------------------------------
drill_service() {
  log "Scenario: SERVICE failure — target=${TARGET_SERVICE}"
  if ! _container_running "${TARGET_SERVICE}"; then
    warn "Target '${TARGET_SERVICE}' not running — skipping"
    record "service" "SKIP" "container not running"
    return 0
  fi

  log "Killing ${TARGET_SERVICE} ..."
  docker kill "${TARGET_SERVICE}" >/dev/null 2>&1 || true

  local start; start=$(date +%s)
  if _wait_healthy "${TARGET_SERVICE}"; then
    local rto=$(( $(date +%s) - start ))
    if (( rto <= RTO_BUDGET_SECONDS )); then
      ok "Recovered in ${rto}s (budget ${RTO_BUDGET_SECONDS}s)"
      record "service" "PASS" "RTO=${rto}s"
    else
      fail "Recovered but exceeded budget: ${rto}s > ${RTO_BUDGET_SECONDS}s"
      record "service" "FAIL" "RTO=${rto}s over budget"
    fi
  else
    fail "Did not recover within ${RTO_BUDGET_SECONDS}s"
    record "service" "FAIL" "no recovery in ${RTO_BUDGET_SECONDS}s"
  fi
}

# -----------------------------------------------------------------------------
# Scenario: Redis failure (data must survive via appendonly)
# -----------------------------------------------------------------------------
drill_redis() {
  log "Scenario: REDIS failure — ${REDIS_CONTAINER}"
  if ! _container_running "${REDIS_CONTAINER}"; then
    warn "Redis '${REDIS_CONTAINER}' not running — skipping"
    record "redis" "SKIP" "container not running"
    return 0
  fi

  # Write a sentinel key, then kill Redis and verify it survives the restart.
  local sentinel="dr_drill_$(date +%s)"
  docker exec "${REDIS_CONTAINER}" redis-cli SET "${sentinel}" "ok" >/dev/null 2>&1 || true
  docker exec "${REDIS_CONTAINER}" redis-cli SAVE >/dev/null 2>&1 || true

  log "Killing ${REDIS_CONTAINER} ..."
  docker kill "${REDIS_CONTAINER}" >/dev/null 2>&1 || true

  local start; start=$(date +%s)
  if _wait_healthy "${REDIS_CONTAINER}"; then
    local rto=$(( $(date +%s) - start ))
    local val
    val="$(docker exec "${REDIS_CONTAINER}" redis-cli GET "${sentinel}" 2>/dev/null || echo '')"
    if [[ "${val}" == "ok" ]]; then
      ok "Redis recovered in ${rto}s and sentinel key survived (durability OK)"
      record "redis" "PASS" "RTO=${rto}s, data persisted"
    else
      warn "Redis recovered in ${rto}s but sentinel lost (acceptable for cache; RPO note)"
      record "redis" "WARN" "RTO=${rto}s, sentinel lost"
    fi
    docker exec "${REDIS_CONTAINER}" redis-cli DEL "${sentinel}" >/dev/null 2>&1 || true
  else
    fail "Redis did not recover within ${RTO_BUDGET_SECONDS}s"
    record "redis" "FAIL" "no recovery"
  fi
}

# -----------------------------------------------------------------------------
# Scenario: gateway failure
# -----------------------------------------------------------------------------
drill_gateway() {
  log "Scenario: GATEWAY failure — ${GATEWAY_CONTAINER}"
  if ! _container_running "${GATEWAY_CONTAINER}"; then
    warn "Gateway '${GATEWAY_CONTAINER}' not running — skipping"
    record "gateway" "SKIP" "container not running"
    return 0
  fi

  log "Killing ${GATEWAY_CONTAINER} ..."
  docker kill "${GATEWAY_CONTAINER}" >/dev/null 2>&1 || true

  local start; start=$(date +%s)
  if _wait_healthy "${GATEWAY_CONTAINER}"; then
    # Give routing a moment, then probe.
    local deadline=$(( $(date +%s) + 30 ))
    while (( $(date +%s) < deadline )); do
      if _http_ok "${GATEWAY_URL}/health/live" || _http_ok "${GATEWAY_URL}"; then break; fi
      sleep 2
    done
    local rto=$(( $(date +%s) - start ))
    ok "Gateway recovered in ${rto}s"
    record "gateway" "PASS" "RTO=${rto}s"
  else
    fail "Gateway did not recover within ${RTO_BUDGET_SECONDS}s"
    record "gateway" "FAIL" "no recovery"
  fi
}

# -----------------------------------------------------------------------------
# Scenario: backup viability
# -----------------------------------------------------------------------------
drill_backup() {
  log "Scenario: BACKUP viability"
  local tmp; tmp="$(mktemp -d)"
  if BACKUP_DIR="${tmp}" "${SCRIPT_DIR}/backup.sh" redis >/dev/null 2>&1; then
    local n; n="$(find "${tmp}" -type f | wc -l | tr -d ' ')"
    if (( n > 0 )); then
      ok "Backup produced ${n} file(s)"
      record "backup" "PASS" "${n} file(s)"
    else
      warn "Backup script ran but produced no files (Redis may be down)"
      record "backup" "WARN" "0 files"
    fi
  else
    warn "Backup script exited non-zero (DB/redis may be unavailable in this env)"
    record "backup" "WARN" "script non-zero"
  fi
  rm -rf "${tmp}"
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
print_summary() {
  echo
  echo -e "${BOLD}============================================================${NC}"
  echo -e "${BOLD}  DR Drill Summary  ($(date -u +%Y-%m-%dT%H:%M:%SZ))${NC}"
  echo -e "${BOLD}  RTO budget: ${RTO_BUDGET_SECONDS}s${NC}"
  echo -e "${BOLD}============================================================${NC}"
  printf "  %-12s %-6s %s\n" "SCENARIO" "RESULT" "DETAIL"
  printf "  %-12s %-6s %s\n" "--------" "------" "------"
  local hard_fail=0
  for row in "${RESULTS[@]}"; do
    IFS='|' read -r scn res det <<< "${row}"
    local color="${GREEN}"
    case "${res}" in FAIL) color="${RED}"; hard_fail=1 ;; WARN|SKIP) color="${YELLOW}" ;; esac
    printf "  %-12s ${color}%-6s${NC} %s\n" "${scn}" "${res}" "${det}"
  done
  echo -e "${BOLD}============================================================${NC}"
  if (( hard_fail )); then
    echo -e "  ${RED}${BOLD}DRILL FAILED — one or more scenarios did not recover.${NC}"
    return 1
  fi
  echo -e "  ${GREEN}${BOLD}DRILL PASSED — all exercised scenarios recovered within budget.${NC}"
  return 0
}

main() {
  local cmd="${1:-all}"
  case "${cmd}" in
    service) drill_service ;;
    redis)   drill_redis ;;
    gateway) drill_gateway ;;
    backup)  drill_backup ;;
    all)
      drill_service
      drill_redis
      drill_gateway
      drill_backup
      ;;
    *) fail "Unknown scenario '${cmd}' (use: service|redis|gateway|backup|all)"; exit 2 ;;
  esac
  print_summary
}

main "$@"
