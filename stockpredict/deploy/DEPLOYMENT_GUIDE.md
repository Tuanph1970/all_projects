# Deployment Guide: Ceramic API + Stock Helper

Complete guide for deploying both Ceramic API and Stock Helper microservices on the same computer.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Port Allocation](#port-allocation)
4. [Quick Start](#quick-start)
5. [Local Development Deployment](#local-development-deployment)
6. [Production Deployment](#production-deployment)
7. [Nginx Configuration](#nginx-configuration)
8. [Management Scripts](#management-scripts)
9. [Troubleshooting](#troubleshooting)
10. [Service URLs Reference](#service-urls-reference)

---

## Architecture Overview

```
                                    ┌─────────────────────────────────────────┐
                                    │           System Nginx (Port 80)        │
                                    │  - Routes /api/ceramic/* → Port 8002    │
                                    │  - Routes /stock_helper/* → Port 8088   │
                                    │  - Serves React static files            │
                                    └─────────────────┬───────────────────────┘
                                                      │
                      ┌───────────────────────────────┴───────────────────────────────┐
                      │                                                               │
                      ▼                                                               ▼
    ┌─────────────────────────────────────┐              ┌─────────────────────────────────────┐
    │        Ceramic API (Port 8002)      │              │   Stock Helper Traefik (Port 8088)  │
    │  - FastAPI Application              │              │   - API Gateway                      │
    │  - Uses native MySQL (3306)         │              │   - Load Balancer                    │
    │  - Uses native Redis (6379)         │              │   - Service Discovery                │
    └─────────────────────────────────────┘              └─────────────────┬───────────────────┘
                                                                           │
                           ┌───────────────────────────────────────────────┴───────────────────────┐
                           │                                                                       │
    ┌──────────────────────┴──────────────────────┐      ┌──────────────────────────────────────────┐
    │           Core Microservices                │      │           Infrastructure                 │
    │  - Stock Data Service (8001)                │      │  - Docker Redis (6380)                   │
    │  - Portfolio Service (8003)                 │      │  - RabbitMQ (5672, 15672)                │
    │  - Analysis Service (8004)                  │      │  - Prometheus (9090)                     │
    │  - AI Insights Service (8005)               │      │  - Grafana (3100)                        │
    │  - Chatbot Service (8006)                   │      │  - Jaeger (16686)                        │
    │  - Auth Service (8007)                      │      │                                          │
    │  - Prediction Service (internal 8002)       │      │                                          │
    └─────────────────────────────────────────────┘      └──────────────────────────────────────────┘
```

### Project Structure

```
/home/tuanph/TuanPH/
├── ceramic_mobile_app/
│   └── back_end/
│       ├── docker-compose.local.yml    # Local development
│       ├── docker-compose.prod.yml     # Production
│       ├── .env                        # Environment variables
│       └── Dockerfile
│
└── stockpredict/
    ├── stock_microservices/
    │   ├── docker-compose.yml          # Base configuration
    │   ├── docker-compose.local.yml    # Local overrides
    │   ├── docker-compose.prod.yml     # Production overrides
    │   ├── .env                        # Environment variables
    │   └── services/
    │       ├── stock_data_service/
    │       ├── portfolio_service/
    │       └── ... (other services)
    │
    ├── stock_react_javascript/
    │   └── stock-react-app/
    │       ├── .env.local              # Local development
    │       ├── .env.production         # Production build
    │       └── build/                  # Production build output
    │
    └── deploy/
        ├── scripts/
        │   ├── deploy-all.sh           # Main deployment script
        │   ├── stop-all.sh             # Stop all services
        │   ├── status.sh               # Check service status
        │   └── logs.sh                 # View service logs
        ├── nginx/
        │   └── unified-projects.conf   # System nginx config
        └── DEPLOYMENT_GUIDE.md         # This file
```

---

## Prerequisites

### Required Software

```bash
# Check Docker
docker --version        # Docker version 20.10+
docker-compose --version # Docker Compose 2.0+

# Check Docker daemon is running
docker info

# Check Node.js (for React development)
node --version          # Node 18+ recommended
npm --version

# Check nginx (for production)
nginx -v
```

### Native Services (Already Running)

1. **MySQL** on port 3306
   ```bash
   # Verify MySQL is running
   sudo systemctl status mysql
   mysql -u root -p -e "SHOW DATABASES;"
   ```

2. **Redis** on port 6379
   ```bash
   # Verify Redis is running
   sudo systemctl status redis
   redis-cli ping
   ```

### Database Setup

```sql
-- Create Ceramic database and user
CREATE DATABASE ceramic_marketplace;
CREATE USER 'ceramic_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON ceramic_marketplace.* TO 'ceramic_user'@'%';

-- Create Stock Helper database and user
CREATE DATABASE stock_helper;
CREATE USER 'stock_user'@'%' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON stock_helper.* TO 'stock_user'@'%';

FLUSH PRIVILEGES;
```

---

## Port Allocation

### Port Map (No Conflicts)

| Port | Service | Project | Notes |
|------|---------|---------|-------|
| 80 | System Nginx | Shared | Main entry point |
| 3001 | React Dev Server | Stock Helper | Development only |
| 3100 | Grafana | Stock Helper | Changed from 3000 |
| 3306 | MySQL | Shared (Native) | Native service |
| 5672 | RabbitMQ | Stock Helper | Message queue |
| 6379 | Redis | Ceramic (Native) | Native service |
| 6380 | Redis | Stock Helper | Docker Redis |
| 8001 | Stock Data Service | Stock Helper | |
| 8002 | Ceramic API | Ceramic | **RESERVED** |
| 8003 | Portfolio Service | Stock Helper | |
| 8004 | Analysis Service | Stock Helper | |
| 8005 | AI Insights Service | Stock Helper | |
| 8006 | Chatbot Service | Stock Helper | |
| 8007 | Auth Service | Stock Helper | |
| 8080 | Docker Nginx | Stock Helper | React static files |
| 8088 | Traefik Gateway | Stock Helper | API Gateway |
| 8089 | Traefik Dashboard | Stock Helper | |
| 9090 | Prometheus | Stock Helper | Metrics |
| 15672 | RabbitMQ Management | Stock Helper | Admin UI |
| 16686 | Jaeger UI | Stock Helper | Tracing |

### Important Note

The Stock Helper **prediction-service** runs internally on port 8002 but is **NOT exposed to the host**. It's accessible only through the Traefik gateway at port 8088.

---

## Quick Start

### One-Command Deployment

```bash
cd /home/tuanph/TuanPH/stockpredict/deploy/scripts

# Make scripts executable (first time only)
chmod +x *.sh

# Deploy everything for local development
./deploy-all.sh --local

# Deploy everything for production
./deploy-all.sh --production --nginx

# Deploy with forced rebuild
./deploy-all.sh --local --build
```

### Quick Stop

```bash
# Stop all services
./stop-all.sh --all

# Stop only Stock Helper
./stop-all.sh --stock-only

# Stop only Ceramic
./stop-all.sh --ceramic-only
```

---

## Local Development Deployment

### Step 1: Configure Environment Files

**Ceramic API** (`/home/tuanph/TuanPH/ceramic_mobile_app/back_end/.env`):
```env
ENVIRONMENT=development
DEBUG=true

# Database - Native MySQL
DB_HOST=host.docker.internal
DB_PORT=3306
DB_NAME=ceramic_marketplace
DB_USER=ceramic_user
DB_PASSWORD=your_password

# Redis - Native Redis
REDIS_HOST=host.docker.internal
REDIS_PORT=6379

# Security
SECRET_KEY=your_secret_key_change_in_production
```

**Stock Helper** (`/home/tuanph/TuanPH/stockpredict/stock_microservices/.env`):
```env
ENVIRONMENT=local

# Database via SSH Tunnel
DB_HOST=host.docker.internal
DB_PORT=3307
DB_USER=stock_user
DB_PASSWORD=your_password
DB_NAME=stock_helper

# Redis - Docker Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Service URLs
STOCK_DATA_URL=http://stock-data-service:8001
PORTFOLIO_URL=http://portfolio-service:8003
# ... other service URLs
```

**React Client** (`/home/tuanph/TuanPH/stockpredict/stock_react_javascript/stock-react-app/.env.local`):
```env
REACT_APP_API_URL=http://localhost
REACT_APP_CHAT_SERVICE_URL=http://localhost:8006
REACT_APP_FILE_SERVICE_URL=http://localhost:8006
PORT=3001
BROWSER=none
```

### Step 2: Deploy Services

```bash
# Option A: Use the deployment script
cd /home/tuanph/TuanPH/stockpredict/deploy/scripts
./deploy-all.sh --local

# Option B: Manual deployment

# 1. Deploy Ceramic API
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end
docker-compose -f docker-compose.local.yml up -d

# 2. Deploy Stock Helper
cd /home/tuanph/TuanPH/stockpredict/stock_microservices
docker-compose -f docker-compose.yml -f docker-compose.local.yml up -d

# 3. Start React (separate terminal)
cd /home/tuanph/TuanPH/stockpredict/stock_react_javascript/stock-react-app
npm start
```

### Step 3: Verify Deployment

```bash
# Check status
./status.sh --health

# Test Ceramic API
curl http://localhost:8002/health
curl http://localhost:8002/api/docs

# Test Stock Helper Gateway
curl http://localhost:8088/stock_helper/api/v2/stock-data/health/live

# Test individual services
curl http://localhost:8001/health/live  # Stock Data
curl http://localhost:8006/health/live  # Chatbot
```

---

## Production Deployment

### Step 1: Prepare Production Environment

```bash
# Update production environment files
cp .env.production .env  # For each project

# Generate secure keys
openssl rand -hex 32  # For SECRET_KEY
```

### Step 2: Build and Deploy

```bash
cd /home/tuanph/TuanPH/stockpredict/deploy/scripts

# Deploy with production config and nginx
./deploy-all.sh --production --build --nginx

# Or step by step:

# 1. Deploy Ceramic
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end
docker-compose -f docker-compose.prod.yml up -d --build

# 2. Deploy Stock Helper
cd /home/tuanph/TuanPH/stockpredict/stock_microservices
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 3. Build React for production
cd /home/tuanph/TuanPH/stockpredict/stock_react_javascript/stock-react-app
npm run build

# 4. Configure nginx
sudo cp /home/tuanph/TuanPH/stockpredict/deploy/nginx/unified-projects.conf \
        /etc/nginx/sites-available/unified-projects
sudo ln -sf /etc/nginx/sites-available/unified-projects /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Step 3: Verify Production

```bash
# Test through nginx
curl http://localhost/health
curl http://localhost/api/ceramic/health
curl http://localhost/stock_helper/api/v2/stock-data/health/live

# Check all services
./status.sh --health --ports
```

---

## Nginx Configuration

### System Nginx Setup

The unified nginx configuration routes requests to both projects:

```nginx
# /etc/nginx/sites-available/unified-projects

# Ceramic API routes
location /api/ceramic/ {
    proxy_pass http://127.0.0.1:8002;
}

# Stock Helper API routes
location /stock_helper/api/ {
    proxy_pass http://127.0.0.1:8088;
}

# React App (Stock Helper frontend)
root /path/to/stock-react-app/build;
location / {
    try_files $uri $uri/ /index.html;
}
```

### Install Configuration

```bash
# Copy configuration
sudo cp /home/tuanph/TuanPH/stockpredict/deploy/nginx/unified-projects.conf \
        /etc/nginx/sites-available/unified-projects

# Enable configuration
sudo ln -sf /etc/nginx/sites-available/unified-projects /etc/nginx/sites-enabled/

# Remove default if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## Management Scripts

### deploy-all.sh

Main deployment script with multiple options:

```bash
./deploy-all.sh [options]

Options:
  --local         Deploy for local development (default)
  --production    Deploy for production
  --build         Force rebuild Docker images
  --clean         Clean up volumes before deployment
  --ceramic-only  Deploy only Ceramic API
  --stock-only    Deploy only Stock Helper
  --react         Also build/start React client
  --nginx         Configure system nginx
  --skip-checks   Skip pre-deployment checks
  --help          Show help message

Examples:
  ./deploy-all.sh --local                    # Local development
  ./deploy-all.sh --production --build       # Production with rebuild
  ./deploy-all.sh --stock-only --build       # Only Stock Helper
  ./deploy-all.sh --production --nginx       # Production with nginx
```

### stop-all.sh

Stop services with selective options:

```bash
./stop-all.sh [options]

Options:
  --ceramic-only   Stop only Ceramic API
  --stock-only     Stop only Stock Helper
  --react          Also stop React dev server
  --volumes        Remove volumes (data loss!)
  --all            Stop everything including React

Examples:
  ./stop-all.sh                    # Stop Ceramic and Stock Helper
  ./stop-all.sh --all --volumes    # Stop all and remove data
  ./stop-all.sh --stock-only       # Stop only Stock Helper
```

### status.sh

Check status of all services:

```bash
./status.sh [options]

Options:
  --ceramic     Show only Ceramic status
  --stock       Show only Stock Helper status
  --health      Include health check details
  --ports       Show port usage

Examples:
  ./status.sh                      # Basic status
  ./status.sh --health             # With health checks
  ./status.sh --health --ports     # Full status report
```

### logs.sh

View service logs:

```bash
./logs.sh [service] [options]

Services:
  ceramic, stock-data, portfolio, analysis,
  ai-insights, chatbot, auth, prediction,
  traefik, redis, rabbitmq, grafana, prometheus, jaeger

Options:
  -f, --follow    Follow log output
  -n, --lines N   Number of lines (default: 100)
  --since TIME    Show logs since (e.g., 10m, 1h)

Examples:
  ./logs.sh                        # List available services
  ./logs.sh ceramic -f             # Follow Ceramic logs
  ./logs.sh chatbot -n 50          # Last 50 lines of Chatbot
  ./logs.sh all                    # Brief logs from all services
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use

```bash
# Find what's using a port
sudo lsof -i :8002
sudo ss -tlnp | grep 8002

# Kill process if needed
sudo kill -9 <PID>
```

#### 2. Docker Network Issues

```bash
# Restart Docker
sudo systemctl restart docker

# Clean up networks
docker network prune

# Rebuild containers
./deploy-all.sh --build --clean
```

#### 3. Container Can't Connect to MySQL

Ensure `extra_hosts` is configured in docker-compose:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Test connection from container:
```bash
docker exec -it ceramic_api bash
apt-get update && apt-get install -y mysql-client
mysql -h host.docker.internal -u ceramic_user -p
```

#### 4. Services Not Healthy

```bash
# Check logs
./logs.sh <service> -n 200

# Check container status
docker ps -a
docker inspect <container_name>

# Restart specific service
docker restart <container_name>
```

#### 5. Nginx Configuration Error

```bash
# Test configuration
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log

# Reload after fixing
sudo systemctl reload nginx
```

### Health Check Endpoints

| Service | Health URL |
|---------|------------|
| Ceramic API | http://localhost:8002/health |
| Stock Data | http://localhost:8001/health/live |
| Portfolio | http://localhost:8003/health/live |
| Analysis | http://localhost:8004/health/live |
| AI Insights | http://localhost:8005/health/live |
| Chatbot | http://localhost:8006/health/live |
| Auth | http://localhost:8007/health/live |
| Traefik | http://localhost:8088/ping |

---

## Service URLs Reference

### Development URLs

| Service | URL |
|---------|-----|
| Ceramic API | http://localhost:8002 |
| Ceramic Docs | http://localhost:8002/api/docs |
| Stock Gateway | http://localhost:8088 |
| Stock API | http://localhost:8088/stock_helper/api/v2/ |
| React App | http://localhost:3001 |
| Traefik Dashboard | http://localhost:8089 |
| Grafana | http://localhost:3100 |
| Prometheus | http://localhost:9090 |
| RabbitMQ | http://localhost:15672 |
| Jaeger | http://localhost:16686 |

### Production URLs (via Nginx)

| Service | URL |
|---------|-----|
| React App | http://localhost/ |
| Ceramic API | http://localhost/api/ceramic/ |
| Stock Helper API | http://localhost/stock_helper/api/v2/ |
| Grafana | http://localhost/grafana/ |
| RabbitMQ | http://localhost/rabbitmq/ |
| Jaeger | http://localhost/jaeger/ |

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Grafana | admin | admin (change on first login) |
| RabbitMQ | guest | guest (change in production) |

---

## Maintenance

### Daily Checks

```bash
# Quick health check
./status.sh --health

# Check logs for errors
./logs.sh all | grep -i error
```

### Backup

```bash
# Database backup
mysqldump -u root -p ceramic_marketplace > ceramic_backup.sql
mysqldump -u root -p stock_helper > stock_backup.sql

# Docker volumes backup
docker run --rm -v stock_redis_data:/data -v $(pwd):/backup \
  alpine tar cvf /backup/redis_backup.tar /data
```

### Updates

```bash
# Pull latest images and rebuild
./stop-all.sh
./deploy-all.sh --production --build

# Update React
cd /home/tuanph/TuanPH/stockpredict/stock_react_javascript/stock-react-app
npm update
npm run build
```

---

## Support

For issues or questions:
1. Check logs: `./logs.sh <service> -f`
2. Check status: `./status.sh --health --ports`
3. Review this guide's troubleshooting section
