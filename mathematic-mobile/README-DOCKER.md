# Docker Setup Guide

## Prerequisites
- Docker and Docker Compose installed
- Ports available: 3306 (MySQL), 6379 (Redis), 8001 (Backend), 8002 (ML Service), 8081, 19000-19002, 19006 (Expo)

## Quick Start

### Development Mode (Default)
```bash
# Build and start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or run in detached mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# View logs
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Stop all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### Production Mode
```bash
# Build and start services
docker-compose up --build

# Run in detached mode
docker-compose up -d --build
```

## Service Access

| Service | Port | URL |
|---------|------|-----|
| Backend API | 8001 | http://localhost:8001/api |
| ML/OCR Service | 8002 | http://localhost:8002 |
| Expo Dev Server | 19000 | http://localhost:19000 |
| Metro Bundler | 8081 | http://localhost:8081 |
| MySQL | 3306 | mysql://localhost:3306 |
| Redis | 6379 | redis://localhost:6379 |
| Nginx (optional) | 80 | http://localhost |

## Optional Services

### Enable Nginx Reverse Proxy
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile nginx up
```

### Enable Monitoring (Prometheus + Grafana)
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml --profile monitoring up
```

## Common Issues & Solutions

### Issue: SQL scripts not found
**Solution**: Fixed - now uses `init-db.sql` from `backend/scripts/`

### Issue: Nginx config missing
**Solution**: Created nginx configuration files in `nginx/` directory

### Issue: Port conflicts
**Solution**: Check if ports are already in use and stop conflicting services

### Issue: Build failures
**Solution**: Clean build with no cache
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build --no-cache
```

## Database Initialization

The MySQL container automatically runs `backend/scripts/init-db.sql` on first startup to create tables and initial data.

## Development Workflow

1. **Start services**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
   ```

2. **Backend changes**: Auto-reloads with `dotnet watch`

3. **ML service changes**: Auto-reloads with `uvicorn --reload`

4. **Frontend changes**: Hot reload via Expo Metro bundler

5. **View logs**:
   ```bash
   # All services
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

   # Specific service
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend-api
   ```

## Cleanup

### Remove containers and volumes
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### Clean up Docker system
```bash
docker system prune -a --volumes
```

## Health Checks

- **MySQL**: `docker exec math-solver-mysql mysqladmin ping -h localhost`
- **Redis**: `docker exec math-solver-redis redis-cli ping`
- **Backend**: `curl http://localhost:8001/health`
- **ML Service**: `curl http://localhost:8002/health`

## Environment Variables

Copy `.env.example` to `.env` and customize values:
```bash
cp .env.example .env
```

## Troubleshooting

### Check container status
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
```

### Restart specific service
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend-api
```

### Access container shell
```bash
docker exec -it math-solver-backend bash
docker exec -it math-solver-llm bash
docker exec -it math-solver-expo-dev sh
```

### Check service logs
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs --tail=100 backend-api
```
