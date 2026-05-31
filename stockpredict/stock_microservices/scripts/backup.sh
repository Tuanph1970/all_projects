#!/usr/bin/env bash
# =============================================================================
# Automated backup — MySQL + Redis (Phase 3.5 §3.5.4)
# =============================================================================
# Supports the DR plan's RPO of 1 hour:
#   - MySQL : full logical dump (mysqldump) — run hourly via cron
#   - Redis : RDB snapshot copy             — run every 5 minutes via cron
#
# Backups are written to $BACKUP_DIR with a UTC timestamp and pruned past
# $RETENTION_DAYS. Set BACKUP_S3_BUCKET to also push to object storage.
#
# Usage:
#   ./scripts/backup.sh mysql           # one MySQL dump
#   ./scripts/backup.sh redis           # one Redis snapshot
#   ./scripts/backup.sh all             # both
#   ./scripts/backup.sh prune           # apply retention only
#
# Cron example (RPO 1h for DB, 5m for cache):
#   0   * * * *  /path/scripts/backup.sh mysql >> /var/log/backup.log 2>&1
#   */5 * * * *  /path/scripts/backup.sh redis >> /var/log/backup.log 2>&1
# =============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TS="$(date -u +%Y%m%d_%H%M%S)"

# MySQL connection (defaults mirror docker-compose env)
MYSQL_HOST="${DATABASE_HOST:-host.docker.internal}"
MYSQL_PORT="${DATABASE_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-Mysql_2025}"
MYSQL_DB="${DATABASE_NAME:-defaultdb}"

REDIS_CONTAINER="${REDIS_CONTAINER:-stock_redis}"
BACKUP_S3_BUCKET="${BACKUP_S3_BUCKET:-}"   # e.g. s3://backups/mysql/

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
log()  { echo -e "${GREEN}[backup ${TS}]${NC} $*"; }
warn() { echo -e "${YELLOW}[backup ${TS}]${NC} $*"; }
err()  { echo -e "${RED}[backup ${TS}]${NC} $*" >&2; }

mkdir -p "${BACKUP_DIR}/mysql" "${BACKUP_DIR}/redis"

backup_mysql() {
  local out="${BACKUP_DIR}/mysql/${MYSQL_DB}_${TS}.sql.gz"
  log "MySQL dump → ${out}"
  if ! command -v mysqldump >/dev/null 2>&1; then
    err "mysqldump not found on PATH — install mysql-client or run inside a container"
    return 1
  fi
  mysqldump \
    --host="${MYSQL_HOST}" --port="${MYSQL_PORT}" \
    --user="${MYSQL_USER}" --password="${MYSQL_PASSWORD}" \
    --single-transaction --quick --routines --triggers --events \
    "${MYSQL_DB}" | gzip > "${out}"
  local size; size="$(du -h "${out}" | cut -f1)"
  log "MySQL backup complete (${size})"
  _maybe_upload "${out}" "mysql"
}

backup_redis() {
  local out="${BACKUP_DIR}/redis/dump_${TS}.rdb"
  log "Redis snapshot → ${out}"
  if ! docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER}$"; then
    warn "Redis container '${REDIS_CONTAINER}' not running — skipping"
    return 0
  fi
  # Trigger a synchronous save, then copy the RDB out of the container.
  docker exec "${REDIS_CONTAINER}" redis-cli SAVE >/dev/null
  docker cp "${REDIS_CONTAINER}:/data/dump.rdb" "${out}"
  local size; size="$(du -h "${out}" | cut -f1)"
  log "Redis backup complete (${size})"
  _maybe_upload "${out}" "redis"
}

_maybe_upload() {
  local file="$1" kind="$2"
  if [[ -n "${BACKUP_S3_BUCKET}" ]] && command -v aws >/dev/null 2>&1; then
    log "Uploading ${file} → ${BACKUP_S3_BUCKET%/}/${kind}/"
    aws s3 cp "${file}" "${BACKUP_S3_BUCKET%/}/${kind}/" || warn "S3 upload failed (kept local copy)"
  fi
}

prune() {
  log "Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}"
  find "${BACKUP_DIR}/mysql" -name '*.sql.gz' -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
  find "${BACKUP_DIR}/redis" -name '*.rdb'    -type f -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
}

main() {
  case "${1:-all}" in
    mysql) backup_mysql; prune ;;
    redis) backup_redis; prune ;;
    all)   backup_mysql; backup_redis; prune ;;
    prune) prune ;;
    *) err "Unknown command '$1' (use: mysql|redis|all|prune)"; exit 2 ;;
  esac
  log "Done."
}

main "$@"
