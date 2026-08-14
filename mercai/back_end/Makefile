.PHONY: help build up down logs shell test clean deploy

# Default target
help:
	@echo "FastAPI Development Commands:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start services"
	@echo "  make up-dev      - Start development services"
	@echo "  make down        - Stop services"
	@echo "  make logs        - View logs"
	@echo "  make shell       - Access app container shell"
	@echo "  make shell-db    - Access database shell"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make deploy      - Deploy to production"
	@echo "  make backup      - Backup database"

# Build Docker images
build:
	docker-compose build

# Start services
up:
	docker-compose up -d

# Start development services
up-dev:
	docker-compose -f docker-compose.dev.yml up

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Access app container
shell:
	docker-compose exec app /bin/bash

# Access database
shell-db:
	docker-compose exec db mysql -u root -p

# Run tests
test:
	docker-compose exec app pytest

# Clean everything
clean:
	docker-compose down -v
	docker system prune -f

# Deploy to production
deploy:
	./deploy.sh

# Backup database
backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	@docker-compose exec db mysqldump -u root -p$$DB_ROOT_PASSWORD $$DB_NAME > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in backups/ directory"

# Development shortcuts
dev: up-dev
prod: up
stop: down

# Install dependencies locally (for IDE support)
install:
	python -m venv venv
	./venv/bin/pip install -r requirements.txt

# Format code
format:
	docker-compose exec app black .
	docker-compose exec app isort .

# Lint code
lint:
	docker-compose exec app flake8 .
	docker-compose exec app mypy .