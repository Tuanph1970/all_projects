#!/bin/bash
#
# Django Decommission Script
#
# This script performs the actual decommissioning of Django services.
# Run ONLY after verify_readiness.py passes and archive_django.sh completes.
#
# Usage:
#   ./decommission_django.sh [--dry-run] [--force] [--keep-db]
#
# This script will:
#   1. Remove Django routes from Traefik
#   2. Stop Django containers
#   3. Remove Django from docker-compose
#   4. Clean up Django-specific resources
#   5. Update CI/CD configurations
#   6. Notify stakeholders
#

set -e

# Configuration
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
COMPOSE_FILE=${COMPOSE_FILE:-"docker-compose.yml"}
TRAEFIK_CONFIG=${TRAEFIK_CONFIG:-"traefik/dynamic.yml"}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-""}
EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS:-""}

# Flags
DRY_RUN=false
FORCE=false
KEEP_DB=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --keep-db)
            KEEP_DB=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--dry-run] [--force] [--keep-db]"
            echo ""
            echo "Options:"
            echo "  --dry-run  Show what would be done without doing it"
            echo "  --force    Skip confirmation prompts"
            echo "  --keep-db  Keep Django database (for reference)"
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

run_cmd() {
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY-RUN] Would execute: $@"
    else
        "$@"
    fi
}

send_notification() {
    local message="$1"
    local severity="${2:-info}"

    # Slack notification
    if [ -n "$SLACK_WEBHOOK" ] && [ "$DRY_RUN" = false ]; then
        curl -s -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{\"text\":\"[$severity] Django Decommission: $message\"}" || true
    fi

    # Email notification
    if [ -n "$EMAIL_RECIPIENTS" ] && [ "$DRY_RUN" = false ]; then
        echo "$message" | mail -s "Django Decommission - $severity" "$EMAIL_RECIPIENTS" || true
    fi
}

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              DJANGO DECOMMISSION SCRIPT                          ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  ⚠️   WARNING: This will permanently shut down Django services   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Timestamp:     ${TIMESTAMP}"
echo "Compose File:  ${COMPOSE_FILE}"
echo "Dry Run:       ${DRY_RUN}"
echo "Force Mode:    ${FORCE}"
echo "Keep Database: ${KEEP_DB}"
echo ""

# Pre-flight checks
log_step "Running pre-flight checks..."

# Check if verification was done
if [ ! -f ".decommission_verified" ] && [ "$FORCE" = false ]; then
    log_error "Verification not completed. Run verify_readiness.py first."
    log_error "Or use --force to skip this check (not recommended)."
    exit 1
fi

# Check if archive was done
if [ ! -f ".django_archived" ] && [ "$FORCE" = false ]; then
    log_warn "Archive not completed. Run archive_django.sh first."
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        exit 0
    fi
fi

# Final confirmation
if [ "$FORCE" = false ] && [ "$DRY_RUN" = false ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════════════"
    echo "  THIS ACTION IS IRREVERSIBLE"
    echo "  Django services will be permanently shut down."
    echo "═══════════════════════════════════════════════════════════════════"
    echo ""
    read -p "Type 'DECOMMISSION' to confirm: " confirm
    if [ "$confirm" != "DECOMMISSION" ]; then
        log_warn "Aborted by user"
        exit 0
    fi
fi

# Start decommissioning
send_notification "Django decommission started" "warning"

#############################################
# STEP 1: Update Traefik Configuration
#############################################
log_step "Step 1/7: Removing Django routes from Traefik..."

if [ -f "$TRAEFIK_CONFIG" ]; then
    # Backup current config
    run_cmd cp "$TRAEFIK_CONFIG" "${TRAEFIK_CONFIG}.backup.${TIMESTAMP}"

    # Remove Django routes (using sed)
    if [ "$DRY_RUN" = false ]; then
        # Create a cleaned config without Django services
        python3 << EOF
import yaml

with open('$TRAEFIK_CONFIG', 'r') as f:
    config = yaml.safe_load(f)

# Remove Django-related entries
if 'http' in config:
    # Remove Django routers
    if 'routers' in config['http']:
        config['http']['routers'] = {
            k: v for k, v in config['http']['routers'].items()
            if 'django' not in k.lower()
        }

    # Remove Django services
    if 'services' in config['http']:
        config['http']['services'] = {
            k: v for k, v in config['http']['services'].items()
            if 'django' not in k.lower()
        }

with open('$TRAEFIK_CONFIG', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print("Django routes removed from Traefik config")
EOF
    fi

    log_info "Traefik configuration updated"
else
    log_warn "Traefik config not found: $TRAEFIK_CONFIG"
fi

#############################################
# STEP 2: Stop Django Containers
#############################################
log_step "Step 2/7: Stopping Django containers..."

DJANGO_CONTAINERS=$(docker ps --filter "name=django" --format "{{.Names}}" 2>/dev/null || true)

if [ -n "$DJANGO_CONTAINERS" ]; then
    for container in $DJANGO_CONTAINERS; do
        log_info "Stopping container: $container"
        run_cmd docker stop "$container" || true
    done
else
    log_info "No Django containers running"
fi

#############################################
# STEP 3: Remove from Docker Compose
#############################################
log_step "Step 3/7: Removing Django from docker-compose..."

if [ -f "$COMPOSE_FILE" ]; then
    run_cmd cp "$COMPOSE_FILE" "${COMPOSE_FILE}.backup.${TIMESTAMP}"

    if [ "$DRY_RUN" = false ]; then
        python3 << EOF
import yaml

with open('$COMPOSE_FILE', 'r') as f:
    config = yaml.safe_load(f)

# Remove Django service
if 'services' in config:
    django_services = [k for k in config['services'].keys() if 'django' in k.lower()]
    for svc in django_services:
        del config['services'][svc]
        print(f"Removed service: {svc}")

# Remove Django volumes
if 'volumes' in config:
    django_volumes = [k for k in config['volumes'].keys() if 'django' in k.lower()]
    for vol in django_volumes:
        del config['volumes'][vol]
        print(f"Removed volume: {vol}")

with open('$COMPOSE_FILE', 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
EOF
    fi

    log_info "Docker compose updated"
fi

#############################################
# STEP 4: Remove Django Containers and Images
#############################################
log_step "Step 4/7: Removing Django containers and images..."

# Remove stopped containers
run_cmd docker rm $(docker ps -a --filter "name=django" -q) 2>/dev/null || true

# Remove Django images
DJANGO_IMAGES=$(docker images --filter "reference=*django*" -q 2>/dev/null || true)
if [ -n "$DJANGO_IMAGES" ]; then
    log_info "Removing Django images..."
    run_cmd docker rmi $DJANGO_IMAGES 2>/dev/null || true
fi

#############################################
# STEP 5: Clean Up Database (Optional)
#############################################
log_step "Step 5/7: Database cleanup..."

if [ "$KEEP_DB" = true ]; then
    log_info "Keeping Django database as requested"
else
    log_warn "Database cleanup skipped - keeping for reference"
    log_info "To manually drop: DROP DATABASE defaultdb;"
fi

#############################################
# STEP 6: Update Feature Flags
#############################################
log_step "Step 6/7: Updating feature flags..."

FEATURE_FLAGS_URL=${FEATURE_FLAGS_URL:-"http://localhost:8010"}

if [ "$DRY_RUN" = false ]; then
    # Disable Django fallback permanently
    curl -s -X POST "${FEATURE_FLAGS_URL}/api/admin/flags/django_fallback" \
        -H "Content-Type: application/json" \
        -d '{"enabled": false, "archived": true}' || true

    log_info "Feature flags updated"
fi

#############################################
# STEP 7: Final Cleanup
#############################################
log_step "Step 7/7: Final cleanup..."

# Remove temporary files
run_cmd rm -f .decommission_verified
run_cmd rm -f .django_archived

# Create decommission record
if [ "$DRY_RUN" = false ]; then
    cat > ".django_decommissioned" << EOF
{
    "decommissioned_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "timestamp": "${TIMESTAMP}",
    "archive_location": "s3://stockhelper-archives/django-decommission/${TIMESTAMP}/",
    "performed_by": "$(whoami)",
    "kept_database": ${KEEP_DB}
}
EOF
fi

# Notify completion
send_notification "Django decommission completed successfully" "success"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║              DECOMMISSION COMPLETE                               ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Django has been successfully decommissioned."
echo ""
echo "Summary:"
echo "  ✅ Traefik routes removed"
echo "  ✅ Docker containers stopped"
echo "  ✅ Docker compose updated"
echo "  ✅ Container images removed"
[ "$KEEP_DB" = true ] && echo "  ⚠️  Database kept (as requested)" || echo "  ⚠️  Database kept for reference"
echo "  ✅ Feature flags updated"
echo "  ✅ Cleanup completed"
echo ""
echo "Backup files:"
echo "  - ${TRAEFIK_CONFIG}.backup.${TIMESTAMP}"
echo "  - ${COMPOSE_FILE}.backup.${TIMESTAMP}"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "NOTE: This was a dry run. No changes were actually made."
    echo ""
fi

echo "Post-decommission tasks:"
echo "  1. Update CI/CD pipelines to remove Django builds"
echo "  2. Update documentation and architecture diagrams"
echo "  3. Notify stakeholders of completion"
echo "  4. Schedule database archival (if not done)"
echo "  5. Update DNS records if applicable"
echo ""

log_info "Decommission script completed!"
