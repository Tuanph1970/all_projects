# Ceramic Marketplace - Production Deployment Guide

**Server IP:** `112.213.91.103`
**App Path:** `/ceramic-app`
**Architecture:** Microservices with Traefik API Gateway + Nginx Reverse Proxy

---

## API Base URL

```
http://112.213.91.103/ceramic-app/api/v1/
```

### Quick Examples:
- Products: `http://112.213.91.103/ceramic-app/api/v1/products/`
- Auth: `http://112.213.91.103/ceramic-app/api/v1/auth/login`
- WebSocket: `ws://112.213.91.103/ceramic-app/api/v1/chat/ws/{user_id}`

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Server Setup](#server-setup)
4. [Database Setup](#database-setup)
5. [Deploy Microservices](#deploy-microservices)
6. [Configure Nginx](#configure-nginx)
7. [Verify Deployment](#verify-deployment)
8. [Frontend Configuration](#frontend-configuration)
9. [SSL/HTTPS Setup (Optional)](#sslhttps-setup-optional)
10. [Monitoring & Maintenance](#monitoring--maintenance)
11. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Internet                                      │
│                           │                                          │
│                           ▼                                          │
│                  ┌────────────────┐                                  │
│                  │  Nginx (:80)   │  ← Reverse Proxy, Rate Limiting  │
│                  └───────┬────────┘                                  │
│                          │                                           │
│                          ▼                                           │
│              ┌───────────────────────┐                               │
│              │  Traefik (:8002)      │  ← API Gateway, Load Balancer │
│              │  Dashboard (:8080)    │                               │
│              └───────────┬───────────┘                               │
│                          │                                           │
│         ┌────────────────┼────────────────┐                          │
│         │                │                │                          │
│         ▼                ▼                ▼                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│  │ Auth Service│  │Product Svc  │  │ Order Svc   │                   │
│  │   (:8001)   │  │  (:8002)    │  │  (:8003)    │                   │
│  └─────────────┘  └─────────────┘  └─────────────┘                   │
│         │                │                │                          │
│         ▼                ▼                ▼                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                   │
│  │ Chat Service│  │Seller Svc   │  │   Redis     │                   │
│  │   (:8004)   │  │  (:8005)    │  │  (Cache)    │                   │
│  └─────────────┘  └─────────────┘  └─────────────┘                   │
│                          │                                           │
│                          ▼                                           │
│                  ┌─────────────┐                                     │
│                  │   MySQL     │  ← Host Machine Database            │
│                  │  (:3306)    │                                     │
│                  └─────────────┘                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Services & Ports

| Service | Internal Port | External Port | Route |
|---------|---------------|---------------|-------|
| Nginx | 80, 443 | 80, 443 | Public entry point |
| Traefik | 80 | 8002 | API Gateway |
| Traefik Dashboard | 8080 | 8080 | Monitoring |
| Auth Service | 8001 | - | `/api/v1/auth/*`, `/api/v1/users/*` |
| Product Service | 8002 | - | `/api/v1/products/*`, `/api/v1/reviews/*` |
| Order Service | 8003 | - | `/api/v1/orders/*`, `/api/v1/cart/*` |
| Chat Service | 8004 | - | `/api/v1/chat/*` |
| Seller Service | 8005 | - | `/api/v1/seller/*` |
| Redis | 6379 | - | Internal cache |
| MySQL | 3306 | 3306 | Database (host) |

---

## Prerequisites

### Required Software

```bash
# Check versions
docker --version      # >= 20.10
docker-compose --version  # >= 2.0
mysql --version       # >= 8.0
nginx -v              # >= 1.18
```

### Install Docker (if not installed)

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Install Nginx (if not installed)

```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable nginx
```

### Install MySQL (if not installed)

```bash
sudo apt install -y mysql-server
sudo systemctl enable mysql
sudo mysql_secure_installation
```

---

## Server Setup

### 1. Clone Repository

```bash
# SSH into your server
ssh user@112.213.91.103

# Create project directory
mkdir -p /home/tuanph/TuanPH/ceramic_mobile_app
cd /home/tuanph/TuanPH/ceramic_mobile_app

# Clone or copy your project
# Option 1: Git clone
git clone <your-repo-url> .

# Option 2: SCP from local machine
# Run on local machine:
# scp -r /home/tuanph/TuanPH/ceramic_mobile_app/* user@112.213.91.103:/home/tuanph/TuanPH/ceramic_mobile_app/
```

### 2. Configure Environment

```bash
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end

# Verify .env file exists and is configured
cat .env | grep -E "^(DB_|REDIS_|SECRET_|DOMAIN)"

# Expected output:
# DB_HOST=host.docker.internal
# DB_PORT=3306
# DB_NAME=ceramic_marketplace
# DB_USER=ceramic_user
# DB_PASSWORD=Mysql_2025
# REDIS_HOST=redis
# SECRET_KEY=your-super-secret-key-change-this-in-production-use-64-chars-min
# DOMAIN=112.213.91.103
```

### 3. Generate Secure Secret Key

```bash
# Generate a new secret key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Update .env with the generated key
# Edit the SECRET_KEY line in .env file
```

---

## Database Setup

### 1. Create Database and User

```bash
# Login to MySQL as root
sudo mysql -u root -p

# Run these SQL commands:
```

```sql
-- Create database
CREATE DATABASE IF NOT EXISTS ceramic_marketplace
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

-- Create user
CREATE USER IF NOT EXISTS 'ceramic_user'@'%'
IDENTIFIED BY 'Mysql_2025';

-- Grant privileges
GRANT ALL PRIVILEGES ON ceramic_marketplace.* TO 'ceramic_user'@'%';
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
SELECT user, host FROM mysql.user WHERE user = 'ceramic_user';

-- Exit MySQL
EXIT;
```

### 2. Configure MySQL for Docker Access

```bash
# Edit MySQL config
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Change bind-address to allow Docker connections:
# bind-address = 0.0.0.0

# Restart MySQL
sudo systemctl restart mysql

# Verify MySQL is listening on all interfaces
sudo netstat -tlnp | grep 3306
```

### 3. Open Firewall for MySQL (internal only)

```bash
# Allow MySQL from Docker network only
sudo ufw allow from 172.21.0.0/16 to any port 3306
```

---

## Deploy Microservices

### 1. Navigate to Backend Directory

```bash
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end
```

### 2. Create Required Directories

```bash
mkdir -p traefik/dynamic traefik/acme uploads
chmod 600 traefik/acme
```

### 3. Build and Start Services

```bash
# Pull base images first (if network is slow)
docker pull python:3.11-slim
docker pull redis:7-alpine
docker pull traefik:v3.0

# Build all services
docker-compose -f docker-compose.microservices.yml build

# Start services in detached mode
docker-compose -f docker-compose.microservices.yml up -d

# Check status
docker-compose -f docker-compose.microservices.yml ps
```

### 4. Verify All Services are Healthy

```bash
# Check container status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Expected output:
# ceramic_auth_service      Up X minutes (healthy)
# ceramic_product_service   Up X minutes (healthy)
# ceramic_order_service     Up X minutes (healthy)
# ceramic_chat_service      Up X minutes (healthy)
# ceramic_seller_service    Up X minutes (healthy)
# ceramic_redis             Up X minutes (healthy)
# ceramic_traefik           Up X minutes

# Check logs if any service is failing
docker logs ceramic_auth_service --tail 50
docker logs ceramic_product_service --tail 50
```

### 5. Test API Through Traefik

```bash
# Test root endpoint
curl http://localhost:8002/

# Test products endpoint
curl http://localhost:8002/api/v1/products/

# Test auth endpoint (should return Method Not Allowed for GET)
curl http://localhost:8002/api/v1/auth/login

# Test health endpoints
curl http://localhost:8002/api/v1/auth/health 2>/dev/null || echo "Auth health check"
```

---

## Configure Nginx

### 1. Backup Current Configuration

```bash
sudo cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.backup.$(date +%Y%m%d)
```

### 2. Deploy New Configuration

```bash
# For MULTI-PROJECT setup (recommended - uses /ceramic-app path)
sudo cp /home/tuanph/TuanPH/ceramic_mobile_app/back_end/nginx/nginx-multi-project.conf /etc/nginx/nginx.conf

# OR for SINGLE-PROJECT setup (ceramic only, uses root path)
# sudo cp /home/tuanph/TuanPH/ceramic_mobile_app/back_end/nginx/ceramic-host.conf /etc/nginx/nginx.conf
```

### 3. Test Configuration

```bash
sudo nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 4. Reload Nginx

```bash
sudo systemctl reload nginx

# Verify nginx is running
sudo systemctl status nginx
```

### 5. Test Through Nginx

```bash
# Test from server (with /ceramic-app prefix)
curl http://localhost/ceramic-app/api/v1/products/
curl http://localhost/ceramic-app/health

# Test from external (run from your local machine)
curl http://112.213.91.103/ceramic-app/api/v1/products/
curl http://112.213.91.103/ceramic-app/health

# Test root endpoint (shows available APIs)
curl http://112.213.91.103/
```

---

## Verify Deployment

### Complete Verification Checklist

```bash
# 1. Check all Docker containers are running
docker ps --format "table {{.Names}}\t{{.Status}}"

# 2. Check Traefik is routing correctly
curl -s http://localhost:8002/api/v1/products/ | head -5

# 3. Check Nginx is proxying correctly
curl -s http://localhost/api/v1/products/ | head -5

# 4. Test from external IP
curl -s http://112.213.91.103/api/v1/products/

# 5. Check database connectivity
docker exec ceramic_auth_service python -c "from shared.database import engine; print('DB OK')" 2>/dev/null || echo "Check DB connection"

# 6. Check Redis connectivity
docker exec ceramic_redis redis-cli ping

# 7. View Traefik dashboard (access in browser)
echo "Traefik Dashboard: http://112.213.91.103:8080"
```

### Expected API Responses

| Endpoint | Expected Response |
|----------|-------------------|
| `/ceramic-app/` | `{"service": "Ceramic Marketplace API", ...}` |
| `/ceramic-app/api/v1/products/` | `[]` (empty array) |
| `/ceramic-app/api/v1/auth/login` (GET) | `{"detail":"Method Not Allowed"}` |
| `/ceramic-app/api/v1/orders/` | `{"detail":"Not authenticated"}` |
| `/ceramic-app/health` | JSON with status |
| `/` | `{"server": "112.213.91.103", "apis": {...}}` |

---

## Frontend Configuration

The frontend has been configured for production with `/ceramic-app` path prefix.

### File: `front_end/src/constants/config.js`

```javascript
// Environment set to production
const ENVIRONMENT = 'production';

// Production URLs with /ceramic-app prefix
const ENV_CONFIG = {
  production: {
    BASE_URL: 'http://112.213.91.103/ceramic-app',
    WS_URL: 'ws://112.213.91.103/ceramic-app',
  },
};
```

### API Endpoints (auto-appended to BASE_URL):
- Login: `{BASE_URL}/api/v1/auth/login` → `http://112.213.91.103/ceramic-app/api/v1/auth/login`
- Products: `{BASE_URL}/api/v1/products` → `http://112.213.91.103/ceramic-app/api/v1/products`
- WebSocket: `{WS_URL}/api/v1/chat/ws/{userId}` → `ws://112.213.91.103/ceramic-app/api/v1/chat/ws/{userId}`

### Build Frontend for Production

```bash
cd /home/tuanph/TuanPH/ceramic_mobile_app/front_end

# Install dependencies
npm install

# Build for production (React Native)
# For Android:
npx react-native run-android --variant=release

# For iOS:
npx react-native run-ios --configuration Release

# For Expo:
eas build --platform android --profile production
eas build --platform ios --profile production
```

---

## SSL/HTTPS Setup (Optional)

### Option 1: Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

### Option 2: Manual SSL Certificate

```bash
# Create SSL directory
sudo mkdir -p /etc/nginx/ssl

# Copy your certificates
sudo cp fullchain.pem /etc/nginx/ssl/
sudo cp privkey.pem /etc/nginx/ssl/

# Update nginx config to enable HTTPS
# Uncomment the HTTPS server block in /etc/nginx/nginx.conf
```

### Update Frontend for HTTPS

```javascript
// front_end/src/constants/config.js
const ENV_CONFIG = {
  production: {
    BASE_URL: 'https://112.213.91.103',  // Change to https
    WS_URL: 'wss://112.213.91.103',      // Change to wss
  },
};
```

---

## Monitoring & Maintenance

### View Logs

```bash
# All services
docker-compose -f docker-compose.microservices.yml logs -f

# Specific service
docker logs -f ceramic_auth_service
docker logs -f ceramic_product_service

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Service Management

```bash
# Stop all services
docker-compose -f docker-compose.microservices.yml down

# Restart specific service
docker-compose -f docker-compose.microservices.yml restart auth-service

# Rebuild and restart a service
docker-compose -f docker-compose.microservices.yml up -d --build auth-service

# Scale a service (if needed)
docker-compose -f docker-compose.microservices.yml up -d --scale product-service=2
```

### Database Backup

```bash
# Create backup
mysqldump -u ceramic_user -p ceramic_marketplace > backup_$(date +%Y%m%d).sql

# Restore from backup
mysql -u ceramic_user -p ceramic_marketplace < backup_20251219.sql
```

### Health Monitoring Script

```bash
#!/bin/bash
# Save as /home/tuanph/scripts/health_check.sh

SERVICES=("auth" "product" "order" "chat" "seller")
BASE_URL="http://localhost:8002/api/v1"

for service in "${SERVICES[@]}"; do
    response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/$service/health" 2>/dev/null)
    if [ "$response" -eq 200 ]; then
        echo "✅ $service service: OK"
    else
        echo "❌ $service service: FAILED (HTTP $response)"
    fi
done
```

---

## Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs
docker logs ceramic_auth_service --tail 100

# Common fixes:
# - Database not accessible: Check MySQL is running and accepting connections
# - Port conflict: Check if port is already in use
# - Missing environment variables: Verify .env file
```

#### 2. Database Connection Failed

```bash
# Test MySQL connection from host
mysql -u ceramic_user -p -h 127.0.0.1 ceramic_marketplace

# Test from Docker container
docker exec -it ceramic_auth_service python -c "
from shared.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connection OK')
"

# Check MySQL is listening
sudo netstat -tlnp | grep 3306
```

#### 3. Redis Connection Failed

```bash
# Test Redis
docker exec ceramic_redis redis-cli ping

# Check Redis logs
docker logs ceramic_redis
```

#### 4. Nginx 502 Bad Gateway

```bash
# Check if Traefik is running
curl http://localhost:8002/

# Check nginx error log
sudo tail -f /var/log/nginx/error.log

# Verify upstream is accessible
curl http://127.0.0.1:8002/api/v1/products/
```

#### 5. CORS Errors

```bash
# Verify CORS headers in response
curl -I http://112.213.91.103/api/v1/products/

# Check ALLOWED_ORIGINS in .env includes your frontend URL
grep ALLOWED_ORIGINS .env
```

### Reset Everything

```bash
# Nuclear option - reset all containers and volumes
docker-compose -f docker-compose.microservices.yml down -v
docker system prune -af

# Rebuild from scratch
docker-compose -f docker-compose.microservices.yml build --no-cache
docker-compose -f docker-compose.microservices.yml up -d
```

---

## Quick Reference Commands

```bash
# Start services
docker-compose -f docker-compose.microservices.yml up -d

# Stop services
docker-compose -f docker-compose.microservices.yml down

# View status
docker-compose -f docker-compose.microservices.yml ps

# View logs
docker-compose -f docker-compose.microservices.yml logs -f

# Rebuild service
docker-compose -f docker-compose.microservices.yml up -d --build <service-name>

# Restart nginx
sudo systemctl reload nginx

# Test API (with /ceramic-app prefix)
curl http://112.213.91.103/ceramic-app/api/v1/products/
curl http://112.213.91.103/ceramic-app/health
curl http://112.213.91.103/  # Shows all available APIs
```

---

## Support

For issues or questions:
1. Check container logs: `docker logs <container_name>`
2. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify all services are healthy: `docker ps`

---

**Last Updated:** December 19, 2025
**Version:** 1.0.0
