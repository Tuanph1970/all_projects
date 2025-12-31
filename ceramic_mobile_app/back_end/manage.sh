#!/bin/bash

#############################################
# Ceramic Marketplace API - Management Script
#############################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.production.yml"

# Help function
show_help() {
    echo -e "${GREEN}Ceramic Marketplace API - Management Script${NC}"
    echo ""
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo -e "  ${GREEN}start${NC}       - Start all services"
    echo -e "  ${GREEN}stop${NC}        - Stop all services"
    echo -e "  ${GREEN}restart${NC}     - Restart all services"
    echo -e "  ${GREEN}status${NC}      - Show service status"
    echo -e "  ${GREEN}logs${NC}        - Show logs (all services)"
    echo -e "  ${GREEN}logs-api${NC}    - Show API logs only"
    echo -e "  ${GREEN}logs-db${NC}     - Show database logs only"
    echo -e "  ${GREEN}logs-nginx${NC}  - Show nginx logs only"
    echo -e "  ${GREEN}shell-api${NC}   - Open shell in API container"
    echo -e "  ${GREEN}shell-db${NC}    - Open MySQL shell"
    echo -e "  ${GREEN}backup${NC}      - Create database backup"
    echo -e "  ${GREEN}restore${NC}     - Restore database from backup"
    echo -e "  ${GREEN}update${NC}      - Pull latest code and rebuild"
    echo -e "  ${GREEN}clean${NC}       - Clean up Docker resources"
    echo -e "  ${GREEN}health${NC}      - Check API health"
    echo -e "  ${GREEN}stats${NC}       - Show container resource usage"
    echo ""
}

# Check if docker-compose is available
check_docker() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
        exit 1
    fi
}

# Start services
start_services() {
    echo -e "${GREEN}→${NC} Starting services..."
    docker-compose -f $COMPOSE_FILE up -d
    echo -e "${GREEN}✓ Services started${NC}"
}

# Stop services
stop_services() {
    echo -e "${YELLOW}→${NC} Stopping services..."
    docker-compose -f $COMPOSE_FILE down
    echo -e "${GREEN}✓ Services stopped${NC}"
}

# Restart services
restart_services() {
    echo -e "${YELLOW}→${NC} Restarting services..."
    docker-compose -f $COMPOSE_FILE restart
    echo -e "${GREEN}✓ Services restarted${NC}"
}

# Show status
show_status() {
    echo -e "${GREEN}Service Status:${NC}"
    docker-compose -f $COMPOSE_FILE ps
}

# Show logs
show_logs() {
    docker-compose -f $COMPOSE_FILE logs -f "$@"
}

# Shell access
shell_api() {
    echo -e "${GREEN}→${NC} Opening shell in API container..."
    docker-compose -f $COMPOSE_FILE exec api bash
}

shell_db() {
    echo -e "${GREEN}→${NC} Opening MySQL shell..."
    docker-compose -f $COMPOSE_FILE exec db mysql -u root -p
}

# Backup database
backup_db() {
    BACKUP_DIR="./backups"
    mkdir -p $BACKUP_DIR

    DATE=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql.gz"

    echo -e "${GREEN}→${NC} Creating database backup..."
    docker-compose -f $COMPOSE_FILE exec -T db mysqldump \
        -u root -p$DB_ROOT_PASSWORD ceramic_marketplace | \
        gzip > $BACKUP_FILE

    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${GREEN}✓ Backup created: $BACKUP_FILE${NC}"

        # Also backup uploads
        UPLOADS_BACKUP="$BACKUP_DIR/uploads_$DATE.tar.gz"
        tar -czf $UPLOADS_BACKUP uploads/ 2>/dev/null || true
        echo -e "${GREEN}✓ Uploads backed up: $UPLOADS_BACKUP${NC}"
    else
        echo -e "${RED}✗ Backup failed${NC}"
    fi
}

# Restore database
restore_db() {
    BACKUP_DIR="./backups"

    echo -e "${YELLOW}Available backups:${NC}"
    ls -lh $BACKUP_DIR/*.sql.gz 2>/dev/null || {
        echo -e "${RED}No backups found${NC}"
        exit 1
    }

    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE

    if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
        echo -e "${RED}✗ Backup file not found${NC}"
        exit 1
    fi

    echo -e "${YELLOW}⚠ This will overwrite the current database!${NC}"
    read -p "Are you sure? (yes/no): " -r

    if [[ $REPLY == "yes" ]]; then
        echo -e "${GREEN}→${NC} Restoring database..."
        gunzip < "$BACKUP_DIR/$BACKUP_FILE" | \
        docker-compose -f $COMPOSE_FILE exec -T db mysql \
            -u root -p$DB_ROOT_PASSWORD ceramic_marketplace

        echo -e "${GREEN}✓ Database restored${NC}"
    else
        echo -e "${YELLOW}Restore cancelled${NC}"
    fi
}

# Update application
update_app() {
    echo -e "${GREEN}→${NC} Pulling latest code..."
    git pull origin $(git branch --show-current) || {
        echo -e "${YELLOW}⚠ Git pull failed${NC}"
    }

    echo -e "${GREEN}→${NC} Rebuilding and restarting..."
    docker-compose -f $COMPOSE_FILE down
    docker-compose -f $COMPOSE_FILE up -d --build

    echo -e "${GREEN}✓ Update complete${NC}"
}

# Clean up Docker resources
clean_docker() {
    echo -e "${YELLOW}⚠ This will remove unused Docker resources${NC}"
    read -p "Continue? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}→${NC} Cleaning up Docker resources..."
        docker system prune -a --volumes -f
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    fi
}

# Health check
check_health() {
    echo -e "${GREEN}→${NC} Checking API health..."

    HEALTH_URL="http://localhost/health"

    if curl -f $HEALTH_URL 2>/dev/null; then
        echo ""
        echo -e "${GREEN}✓ API is healthy${NC}"
    else
        echo -e "${RED}✗ API health check failed${NC}"
        echo -e "${YELLOW}Checking service status...${NC}"
        show_status
    fi
}

# Show resource stats
show_stats() {
    echo -e "${GREEN}Container Resource Usage:${NC}"
    docker stats --no-stream
}

# Main script logic
check_docker

case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    logs-api)
        show_logs api
        ;;
    logs-db)
        show_logs db
        ;;
    logs-nginx)
        show_logs nginx
        ;;
    shell-api)
        shell_api
        ;;
    shell-db)
        shell_db
        ;;
    backup)
        backup_db
        ;;
    restore)
        restore_db
        ;;
    update)
        update_app
        ;;
    clean)
        clean_docker
        ;;
    health)
        check_health
        ;;
    stats)
        show_stats
        ;;
    *)
        show_help
        ;;
esac
