#!/bin/bash
#
# Django Archive Script
#
# This script archives the Django monolith codebase, database, and logs
# before decommissioning. Run this AFTER verify_readiness.py passes.
#
# Usage:
#   ./archive_django.sh [--dry-run] [--skip-db] [--skip-logs]
#
# Environment variables:
#   ARCHIVE_BUCKET: S3 bucket for archives (default: stockhelper-archives)
#   DJANGO_DIR: Django project directory
#   DB_HOST: Database host
#   DB_NAME: Database name
#   DB_USER: Database user
#

set -e

# Configuration
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
ARCHIVE_DIR="/tmp/django_archive_${TIMESTAMP}"
ARCHIVE_BUCKET=${ARCHIVE_BUCKET:-"stockhelper-archives"}
ARCHIVE_PREFIX="django-decommission/${TIMESTAMP}"
DJANGO_DIR=${DJANGO_DIR:-"/app/django"}
DB_HOST=${DB_HOST:-"localhost"}
DB_NAME=${DB_NAME:-"defaultdb"}
DB_USER=${DB_USER:-"stockuser"}
RETENTION_DAYS=${RETENTION_DAYS:-90}

# Flags
DRY_RUN=false
SKIP_DB=false
SKIP_LOGS=false
SKIP_CODE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-logs)
            SKIP_LOGS=true
            shift
            ;;
        --skip-code)
            SKIP_CODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--skip-db] [--skip-logs] [--skip-code]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be archived without doing it"
            echo "  --skip-db    Skip database backup"
            echo "  --skip-logs  Skip log archival"
            echo "  --skip-code  Skip code archival"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would execute: $@"
    else
        "$@"
    fi
}

echo ""
echo "=========================================="
echo "  DJANGO ARCHIVE SCRIPT"
echo "=========================================="
echo ""
echo "Timestamp:      ${TIMESTAMP}"
echo "Archive Dir:    ${ARCHIVE_DIR}"
echo "Archive Bucket: ${ARCHIVE_BUCKET}"
echo "Django Dir:     ${DJANGO_DIR}"
echo "Database:       ${DB_NAME}@${DB_HOST}"
echo "Dry Run:        ${DRY_RUN}"
echo ""

# Confirmation
if [ "$DRY_RUN" = false ]; then
    read -p "This will archive and prepare Django for decommissioning. Continue? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        log_warn "Aborted by user"
        exit 0
    fi
fi

# Create archive directory
log_info "Creating archive directory..."
run_cmd mkdir -p "${ARCHIVE_DIR}"

# 1. Archive Django codebase
if [ "$SKIP_CODE" = false ]; then
    log_info "Archiving Django codebase..."

    if [ -d "$DJANGO_DIR" ]; then
        run_cmd tar -czf "${ARCHIVE_DIR}/django_code_${TIMESTAMP}.tar.gz" \
            --exclude="__pycache__" \
            --exclude="*.pyc" \
            --exclude=".git" \
            --exclude="node_modules" \
            --exclude="venv" \
            --exclude="*.log" \
            -C "$(dirname $DJANGO_DIR)" \
            "$(basename $DJANGO_DIR)"

        log_info "Code archive created: django_code_${TIMESTAMP}.tar.gz"
    else
        log_warn "Django directory not found: ${DJANGO_DIR}"
    fi

    # Create git bundle if it's a git repo
    if [ -d "${DJANGO_DIR}/.git" ]; then
        log_info "Creating git bundle..."
        cd "$DJANGO_DIR"
        run_cmd git bundle create "${ARCHIVE_DIR}/django_repo_${TIMESTAMP}.bundle" --all
        cd -
    fi
fi

# 2. Archive database
if [ "$SKIP_DB" = false ]; then
    log_info "Archiving database..."

    # Create database dump
    if [ "$DRY_RUN" = false ]; then
        mysqldump \
            --host="$DB_HOST" \
            --user="$DB_USER" \
            --single-transaction \
            --routines \
            --triggers \
            --events \
            "$DB_NAME" | gzip > "${ARCHIVE_DIR}/django_db_${TIMESTAMP}.sql.gz"

        log_info "Database archive created: django_db_${TIMESTAMP}.sql.gz"

        # Get database size
        DB_SIZE=$(mysql -h "$DB_HOST" -u "$DB_USER" -N -e \
            "SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' \
             FROM information_schema.tables WHERE table_schema = '$DB_NAME';")
        log_info "Database size: ${DB_SIZE} MB"
    else
        echo "[DRY-RUN] Would create database dump: django_db_${TIMESTAMP}.sql.gz"
    fi

    # Export schema only (for documentation)
    if [ "$DRY_RUN" = false ]; then
        mysqldump \
            --host="$DB_HOST" \
            --user="$DB_USER" \
            --no-data \
            "$DB_NAME" > "${ARCHIVE_DIR}/django_schema_${TIMESTAMP}.sql"

        log_info "Schema export created: django_schema_${TIMESTAMP}.sql"
    fi
fi

# 3. Archive logs
if [ "$SKIP_LOGS" = false ]; then
    log_info "Archiving logs..."

    LOG_DIRS=(
        "/var/log/django"
        "${DJANGO_DIR}/logs"
        "/var/log/gunicorn"
        "/var/log/nginx"
    )

    for log_dir in "${LOG_DIRS[@]}"; do
        if [ -d "$log_dir" ]; then
            dir_name=$(basename "$log_dir")
            run_cmd tar -czf "${ARCHIVE_DIR}/logs_${dir_name}_${TIMESTAMP}.tar.gz" \
                -C "$(dirname $log_dir)" \
                "$dir_name"
            log_info "Archived logs from: $log_dir"
        fi
    done
fi

# 4. Archive configuration
log_info "Archiving configuration..."

CONFIG_FILES=(
    "${DJANGO_DIR}/settings.py"
    "${DJANGO_DIR}/config/settings.py"
    "/etc/nginx/sites-available/django"
    "/etc/supervisor/conf.d/django.conf"
    "/etc/systemd/system/django.service"
)

run_cmd mkdir -p "${ARCHIVE_DIR}/config"

for config in "${CONFIG_FILES[@]}"; do
    if [ -f "$config" ]; then
        run_cmd cp "$config" "${ARCHIVE_DIR}/config/"
        log_info "Archived config: $config"
    fi
done

# 5. Create archive manifest
log_info "Creating archive manifest..."

if [ "$DRY_RUN" = false ]; then
    cat > "${ARCHIVE_DIR}/MANIFEST.json" << EOF
{
    "archive_type": "django_decommission",
    "timestamp": "${TIMESTAMP}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "retention_days": ${RETENTION_DAYS},
    "delete_after": "$(date -u -d "+${RETENTION_DAYS} days" +%Y-%m-%dT%H:%M:%SZ)",
    "contents": {
        "code": $([ "$SKIP_CODE" = false ] && echo "true" || echo "false"),
        "database": $([ "$SKIP_DB" = false ] && echo "true" || echo "false"),
        "logs": $([ "$SKIP_LOGS" = false ] && echo "true" || echo "false"),
        "configuration": true
    },
    "source": {
        "django_dir": "${DJANGO_DIR}",
        "db_host": "${DB_HOST}",
        "db_name": "${DB_NAME}"
    },
    "notes": "Django monolith archived during migration to microservices"
}
EOF
fi

# 6. Upload to S3
log_info "Uploading archive to S3..."

if [ "$DRY_RUN" = false ]; then
    # Create final archive
    tar -czf "/tmp/django_complete_archive_${TIMESTAMP}.tar.gz" -C "${ARCHIVE_DIR}" .

    # Upload to S3
    aws s3 cp "/tmp/django_complete_archive_${TIMESTAMP}.tar.gz" \
        "s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/django_complete_archive.tar.gz" \
        --storage-class STANDARD_IA

    # Also upload manifest separately for easy access
    aws s3 cp "${ARCHIVE_DIR}/MANIFEST.json" \
        "s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/MANIFEST.json"

    log_info "Archive uploaded to: s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/"

    # Set lifecycle policy for retention
    aws s3api put-object-tagging \
        --bucket "${ARCHIVE_BUCKET}" \
        --key "${ARCHIVE_PREFIX}/django_complete_archive.tar.gz" \
        --tagging "TagSet=[{Key=RetentionDays,Value=${RETENTION_DAYS}},{Key=ArchiveType,Value=django-decommission}]"
else
    echo "[DRY-RUN] Would upload to: s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/"
fi

# 7. Cleanup local archive
log_info "Cleaning up local files..."
run_cmd rm -rf "${ARCHIVE_DIR}"
run_cmd rm -f "/tmp/django_complete_archive_${TIMESTAMP}.tar.gz"

# 8. Generate archive report
echo ""
echo "=========================================="
echo "  ARCHIVE COMPLETE"
echo "=========================================="
echo ""
echo "Archive Location: s3://${ARCHIVE_BUCKET}/${ARCHIVE_PREFIX}/"
echo "Retention: ${RETENTION_DAYS} days"
echo ""
echo "Contents archived:"
[ "$SKIP_CODE" = false ] && echo "  ✅ Django codebase"
[ "$SKIP_DB" = false ] && echo "  ✅ Database dump"
[ "$SKIP_LOGS" = false ] && echo "  ✅ Application logs"
echo "  ✅ Configuration files"
echo "  ✅ Archive manifest"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "NOTE: This was a dry run. No files were actually archived."
fi

echo ""
echo "Next steps:"
echo "  1. Verify archive integrity"
echo "  2. Run decommission_django.sh to shut down Django"
echo "  3. Update DNS/routing configuration"
echo "  4. Remove Django from infrastructure"
echo ""

log_info "Archive script completed successfully!"
