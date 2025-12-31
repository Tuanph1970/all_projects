# Ceramic Marketplace - Microservices Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development Deployment](#local-development-deployment)
3. [Production Server Deployment](#production-server-deployment)
4. [Configuration](#configuration)
5. [Monitoring](#monitoring)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- Docker Engine 24.0+
- Docker Compose 2.20+
- Git

### Check Docker Installation
```bash
docker --version
docker-compose --version
```

### Install Docker (if needed)
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## Local Development Deployment

### Step 1: Clone and Navigate
```bash
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end
```

### Step 2: Configure Environment
```bash
# Copy microservices environment file
cp .env.microservices .env

# Edit configuration (update passwords, secrets)
nano .env
```

**Important settings to update:**
```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Update in .env:
SECRET_KEY=<your-generated-secret>
DB_PASSWORD=<your-mysql-password>
DB_ROOT_PASSWORD=<your-mysql-root-password>
```

### Step 3: Build Services
```bash
# Build all microservices
docker-compose -f docker-compose.microservices.yml build

# Or build specific service
docker-compose -f docker-compose.microservices.yml build auth-service
```

### Step 4: Start Infrastructure First
```bash
# Start database and cache
docker-compose -f docker-compose.microservices.yml up -d db redis

# Wait for MySQL to be ready (about 30-60 seconds)
docker-compose -f docker-compose.microservices.yml logs -f db

# Look for: "ready for connections"
# Press Ctrl+C to exit logs
```

### Step 5: Start All Services
```bash
# Start remaining services
docker-compose -f docker-compose.microservices.yml up -d

# Check status
docker-compose -f docker-compose.microservices.yml ps
```

### Step 6: Verify Deployment
```bash
# Run health check
./scripts/health_check.sh -v

# Or check individual services
curl http://localhost/api/v1/auth/health
curl http://localhost/api/v1/products/health
curl http://localhost/api/v1/orders/health
curl http://localhost/api/v1/chat/health
curl http://localhost/api/v1/seller/health
```

### Step 7: View Logs
```bash
# All services
docker-compose -f docker-compose.microservices.yml logs -f

# Specific service
docker-compose -f docker-compose.microservices.yml logs -f auth-service
docker-compose -f docker-compose.microservices.yml logs -f product-service
```

### Local Endpoints
| Service | URL |
|---------|-----|
| API Gateway | http://localhost |
| Traefik Dashboard | http://localhost:8080 |
| Auth API | http://localhost/api/v1/auth |
| Products API | http://localhost/api/v1/products |
| Orders API | http://localhost/api/v1/orders |
| Cart API | http://localhost/api/v1/cart |
| Chat API | http://localhost/api/v1/chat |
| Seller API | http://localhost/api/v1/seller |

### Stop Services
```bash
# Stop all services
docker-compose -f docker-compose.microservices.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker-compose.microservices.yml down -v
```

---

## Production Server Deployment

### Server Information
- **IP Address**: 112.213.91.103
- **MySQL & Services**: Same machine

### Step 1: Connect to Server
```bash
ssh user@112.213.91.103
```

### Step 2: Install Docker on Server
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Logout and login again for group changes
exit
ssh user@112.213.91.103
```

### Step 3: Create Application Directory
```bash
sudo mkdir -p /opt/ceramic-marketplace
sudo chown $USER:$USER /opt/ceramic-marketplace
cd /opt/ceramic-marketplace
```

### Step 4: Transfer Files from Local Machine
Run this from your **local PC**:
```bash
# From your local machine
cd /home/tuanph/TuanPH/ceramic_mobile_app/back_end

# Transfer all files to server
rsync -avz --progress \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.env' \
  --exclude 'uploads/*' \
  . user@112.213.91.103:/opt/ceramic-marketplace/
```

Or use SCP:
```bash
scp -r . user@112.213.91.103:/opt/ceramic-marketplace/
```

### Step 5: Configure Production Environment
On the **server**:
```bash
cd /opt/ceramic-marketplace

# Create production .env
cp .env.microservices .env

# Edit with production values
nano .env
```

**Production .env settings:**
```bash
# =============================================================================
# PRODUCTION CONFIGURATION
# =============================================================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database - Same machine, use 'db' for Docker network
DB_HOST=db
DB_PORT=3306
DB_NAME=ceramic_marketplace
DB_USER=ceramic_user
DB_PASSWORD=<STRONG_PASSWORD_HERE>
DB_ROOT_PASSWORD=<STRONG_ROOT_PASSWORD_HERE>

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Security - Generate new secret!
SECRET_KEY=<GENERATE_NEW_64_CHAR_SECRET>
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Server IP for CORS
ALLOWED_ORIGINS=http://112.213.91.103,http://localhost:3000,https://your-domain.com

# Domain (update when you have domain)
DOMAIN=112.213.91.103

# Email (update with your SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Step 6: Create Required Directories
```bash
mkdir -p uploads traefik/acme
chmod 600 traefik/acme
```

### Step 7: Build and Deploy
```bash
# Build all services
docker-compose -f docker-compose.microservices.yml build

# Start infrastructure
docker-compose -f docker-compose.microservices.yml up -d db redis
sleep 60  # Wait for MySQL initialization

# Start all services
docker-compose -f docker-compose.microservices.yml up -d

# Check status
docker-compose -f docker-compose.microservices.yml ps
```

### Step 8: Configure Firewall
```bash
# Allow required ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8080/tcp    # Traefik Dashboard (optional, remove in production)
sudo ufw enable
sudo ufw status
```

### Step 9: Verify Deployment
```bash
# Health check
./scripts/health_check.sh -v

# Test from outside (run from your local PC)
curl http://112.213.91.103/api/v1/auth/health
curl http://112.213.91.103/api/v1/products/health
```

### Production Endpoints
| Service | URL |
|---------|-----|
| API Gateway | http://112.213.91.103 |
| Traefik Dashboard | http://112.213.91.103:8080 |
| Auth API | http://112.213.91.103/api/v1/auth |
| Products API | http://112.213.91.103/api/v1/products |
| Orders API | http://112.213.91.103/api/v1/orders |
| Chat API | http://112.213.91.103/api/v1/chat |
| Seller API | http://112.213.91.103/api/v1/seller |

---

## Configuration

### Update Traefik for Production Domain
When you have a domain, update `traefik/dynamic/middlewares.yml`:
```yaml
http:
  middlewares:
    ratelimit:
      rateLimit:
        average: 100
        burst: 50
```

### Enable HTTPS (with domain)
Update `docker-compose.microservices.yml` Traefik configuration:
```yaml
traefik:
  command:
    # Add these for HTTPS
    - "--certificatesresolvers.letsencrypt.acme.email=your@email.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/etc/traefik/acme/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
```

---

## Monitoring

### Enable Monitoring Stack
```bash
# Start monitoring services
docker-compose -f docker-compose.microservices.yml \
               -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://112.213.91.103:3000 (admin/admin)
# Prometheus: http://112.213.91.103:9090
```

### Quick Status Check
```bash
# Service status dashboard
./scripts/service_status.sh

# Watch mode (auto-refresh)
./scripts/service_status.sh -w
```

---

## Troubleshooting

### View Logs
```bash
# All services
docker-compose -f docker-compose.microservices.yml logs -f

# Specific service
docker-compose -f docker-compose.microservices.yml logs -f auth-service

# Last 100 lines
docker-compose -f docker-compose.microservices.yml logs --tail=100 product-service
```

### Common Issues

#### 1. MySQL Connection Refused
```bash
# Check MySQL status
docker-compose -f docker-compose.microservices.yml logs db

# Restart MySQL
docker-compose -f docker-compose.microservices.yml restart db

# Wait and restart services
sleep 30
docker-compose -f docker-compose.microservices.yml restart
```

#### 2. Service Health Check Failing
```bash
# Check specific service logs
docker-compose -f docker-compose.microservices.yml logs auth-service

# Restart specific service
docker-compose -f docker-compose.microservices.yml restart auth-service
```

#### 3. Port Already in Use
```bash
# Check what's using port 80
sudo lsof -i :80
sudo netstat -tlnp | grep :80

# Stop conflicting service
sudo systemctl stop nginx  # if nginx is running
sudo systemctl stop apache2  # if apache is running
```

#### 4. Docker Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 5. Out of Disk Space
```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a -f
docker volume prune -f
```

### Restart All Services
```bash
docker-compose -f docker-compose.microservices.yml down
docker-compose -f docker-compose.microservices.yml up -d
```

### Full Reset (WARNING: Deletes all data)
```bash
docker-compose -f docker-compose.microservices.yml down -v
docker system prune -a -f
docker-compose -f docker-compose.microservices.yml build --no-cache
docker-compose -f docker-compose.microservices.yml up -d
```

---

## Quick Reference Commands

```bash
# Start all
docker-compose -f docker-compose.microservices.yml up -d

# Stop all
docker-compose -f docker-compose.microservices.yml down

# View status
docker-compose -f docker-compose.microservices.yml ps

# View logs
docker-compose -f docker-compose.microservices.yml logs -f

# Restart service
docker-compose -f docker-compose.microservices.yml restart <service-name>

# Rebuild and restart
docker-compose -f docker-compose.microservices.yml up -d --build <service-name>

# Health check
./scripts/health_check.sh -v

# Service status
./scripts/service_status.sh
```

---

## Support

For issues, check:
1. Service logs: `docker-compose logs -f <service>`
2. Health check: `./scripts/health_check.sh -v`
3. Docker status: `docker ps -a`
