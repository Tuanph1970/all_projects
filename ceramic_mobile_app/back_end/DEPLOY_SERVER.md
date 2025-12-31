# Ceramic Marketplace - Server Deployment Guide

Complete deployment guide for Ceramic Marketplace microservices on a remote server (e.g., `112.213.91.103`).

> **Multi-Project Server**: This guide uses `ceramic_` prefix for all resources (directories, containers, databases, networks) to distinguish from other projects on the same server.

---

## Project Naming Convention

| Resource Type | Prefix Pattern | Example |
|---------------|----------------|---------|
| Directory | `/opt/ceramic-marketplace/` | `/opt/ceramic-marketplace/` |
| Database | `ceramic_` | `ceramic_marketplace` |
| DB User | `ceramic_` | `ceramic_user` |
| Containers | `ceramic_` | `ceramic_auth_service` |
| Network | `ceramic_` | `ceramic_network` |
| Volumes | `ceramic_` | `ceramic_redis_data` |
| Nginx upstream | `ceramic_` | `ceramic_api` |

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Connection](#server-connection)
3. [MySQL Configuration (CRITICAL)](#mysql-configuration-critical)
4. [Docker Installation](#docker-installation)
5. [Project Setup](#project-setup)
6. [Environment Configuration](#environment-configuration)
7. [Build and Deploy](#build-and-deploy)
8. [Nginx Configuration](#nginx-configuration)
9. [Health Check and Verification](#health-check-and-verification)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance Commands](#maintenance-commands)

---

## Prerequisites

Before deployment, ensure you have:

- [ ] Server access (SSH/SFTP)
- [ ] Root or sudo privileges
- [ ] Server IP: `112.213.91.103`
- [ ] MySQL installed and running
- [ ] Docker and Docker Compose installed
- [ ] Minimum 2GB RAM, 20GB disk space

---

## Server Connection

### Connect via SSH
```bash
ssh root@112.213.91.103
```

### Connect via SFTP (for file transfer)
```bash
sftp root@112.213.91.103
```

---

## MySQL Configuration (CRITICAL)

> **IMPORTANT**: This is the most common cause of deployment failure. Docker containers connect to MySQL via `host.docker.internal` (the host's IP), NOT `localhost`. You must configure MySQL to accept connections from Docker's network.

### Step 1: Login to MySQL as Root
```bash
sudo mysql
# OR if password is set:
mysql -u root -p
```

### Step 2: Create User for Docker Containers
```sql
-- Create user that can connect from any IP (for Docker)
CREATE USER IF NOT EXISTS 'ceramic_user'@'%' IDENTIFIED BY 'Mysql_2025';

-- Grant privileges on the database
GRANT ALL PRIVILEGES ON ceramic_marketplace.* TO 'ceramic_user'@'%';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- Verify the user was created correctly
SELECT user, host FROM mysql.user WHERE user = 'ceramic_user';
```

Expected output:
```
+--------------+-----------+
| user         | host      |
+--------------+-----------+
| ceramic_user | %         |
| ceramic_user | localhost |
+--------------+-----------+
```

### Step 3: Create Database (if not exists)
```sql
CREATE DATABASE IF NOT EXISTS ceramic_marketplace
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

SHOW DATABASES;
```

### Step 4: Configure MySQL to Accept External Connections
```bash
# Edit MySQL configuration
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Change or add this line:
bind-address = 0.0.0.0

# Save and exit (Ctrl+X, Y, Enter)

# Restart MySQL service
sudo systemctl restart mysql

# Verify MySQL is listening on all interfaces
ss -tlnp | grep 3306
```

Expected output:
```
LISTEN  0  151  *:3306  *:*  users:(("mysqld",pid=xxx,fd=xx))
```

### Step 5: Test MySQL Connection
```bash
# Test local connection
mysql -u ceramic_user -p'Mysql_2025' -e "SELECT 1;"

# Test connection from Docker IP range (172.17.x.x or 172.21.x.x)
mysql -u ceramic_user -p'Mysql_2025' -h 127.0.0.1 -e "SHOW DATABASES;"
```

---

## Docker Installation

### Install Docker (Ubuntu/Debian)
```bash
# Update packages
sudo apt update

# Install prerequisites
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add current user to docker group (optional, avoids sudo)
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker compose version
```

---

## Project Setup

### Step 1: Create Project Directory
```bash
mkdir -p /opt/ceramic-marketplace
cd /opt/ceramic-marketplace
```

### Step 2: Upload Project Files
From your local machine:
```bash
# Using rsync (recommended)
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
    /path/to/back_end/ root@112.213.91.103:/opt/ceramic-marketplace/

# OR using scp
scp -r /path/to/back_end/* root@112.213.91.103:/opt/ceramic-marketplace/
```

### Step 3: Verify Project Structure
```bash
ls -la /opt/ceramic-marketplace/
```

Expected structure:
```
/opt/ceramic-marketplace/
├── docker-compose.microservices.yml
├── .env
├── services/
│   ├── auth/
│   ├── product/
│   ├── order/
│   ├── chat/
│   └── seller/
├── shared/
├── traefik/
│   ├── dynamic/
│   │   └── middlewares.yml
│   └── acme/
└── uploads/
```

---

## Environment Configuration

### Step 1: Create .env File
```bash
cd /opt/ceramic-marketplace

# Copy from template
cp .env.microservices .env

# Edit configuration
nano .env
```

### Step 2: Update .env with Production Values
```ini
# =============================================================================
# CRITICAL SETTINGS - MUST UPDATE
# =============================================================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database - Using host MySQL
DB_HOST=host.docker.internal
DB_PORT=3306
DB_NAME=ceramic_marketplace
DB_USER=ceramic_user
DB_PASSWORD=Mysql_2025

# Security - CHANGE THIS IN PRODUCTION!
SECRET_KEY=your-super-secret-key-at-least-64-characters-long-change-me

# Domain
DOMAIN=112.213.91.103
ALLOWED_ORIGINS=http://112.213.91.103,https://112.213.91.103,http://localhost:3000

# Redis (uses Docker internal network)
REDIS_HOST=redis
REDIS_PORT=6379
```

### Step 3: Create Required Directories
```bash
# Create uploads directory
mkdir -p /opt/ceramic-marketplace/uploads
chmod 755 /opt/ceramic-marketplace/uploads

# Create traefik directories
mkdir -p /opt/ceramic-marketplace/traefik/dynamic
mkdir -p /opt/ceramic-marketplace/traefik/acme
touch /opt/ceramic-marketplace/traefik/acme/acme.json
chmod 600 /opt/ceramic-marketplace/traefik/acme/acme.json
```

---

## Build and Deploy

### Step 1: Build Docker Images
```bash
cd /opt/ceramic-marketplace

# Build all services (this may take 5-10 minutes on first run)
docker compose -f docker-compose.microservices.yml build

# OR build with no cache (for fresh build)
docker compose -f docker-compose.microservices.yml build --no-cache
```

### Step 2: Start Services
```bash
# Start all services in detached mode
docker compose -f docker-compose.microservices.yml up -d

# View startup logs
docker compose -f docker-compose.microservices.yml logs -f

# Press Ctrl+C to stop following logs
```

### Step 3: Check Container Status
```bash
# List running containers
docker compose -f docker-compose.microservices.yml ps

# Expected output:
# NAME                      STATUS          PORTS
# ceramic_auth_service      Up (healthy)    8001/tcp
# ceramic_product_service   Up (healthy)    8002/tcp
# ceramic_order_service     Up (healthy)    8003/tcp
# ceramic_chat_service      Up (healthy)    8004/tcp
# ceramic_seller_service    Up (healthy)    8005/tcp
# ceramic_redis             Up (healthy)    6379/tcp
# ceramic_traefik           Up              0.0.0.0:8002->80/tcp, 8080->8080/tcp
```

---

## Nginx Configuration

> **Important**: Configure Nginx as reverse proxy to expose Ceramic API on standard ports (80/443) while other projects use different ports or domains.

### Step 1: Install Nginx (if not installed)
```bash
sudo apt update
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Step 2: Create Ceramic API Configuration
```bash
sudo nano /etc/nginx/sites-available/ceramic-api
```

Add the following configuration:
```nginx
# =============================================================================
# Ceramic Marketplace API - Nginx Reverse Proxy
# Prefix: ceramic_ (distinguishes from other projects on same server)
# =============================================================================

# Upstream for Ceramic API (Traefik Gateway)
upstream ceramic_api {
    server 127.0.0.1:8002;  # Traefik listens on port 8002
    keepalive 32;
}

# HTTP Server - Redirect to HTTPS (Production)
server {
    listen 80;
    server_name ceramic.yourdomain.com;  # Replace with your domain

    # For Let's Encrypt certificate validation
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all HTTP to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server (Production with SSL)
server {
    listen 443 ssl http2;
    server_name ceramic.yourdomain.com;  # Replace with your domain

    # SSL Certificates (use Let's Encrypt or your certificates)
    ssl_certificate /etc/letsencrypt/live/ceramic.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ceramic.yourdomain.com/privkey.pem;

    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Max upload size (for product images)
    client_max_body_size 50M;

    # Ceramic API Routes
    location /api/v1/ {
        proxy_pass http://ceramic_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # CORS Headers (if needed)
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }

    # WebSocket support for Chat Service
    location /api/v1/chat/ws {
        proxy_pass http://ceramic_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # Static files (uploads)
    location /uploads/ {
        alias /opt/ceramic-marketplace/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

### Step 3: Alternative - IP-based Configuration (No Domain)
If you don't have a domain, use IP-based configuration:
```bash
sudo nano /etc/nginx/sites-available/ceramic-api
```

```nginx
# =============================================================================
# Ceramic Marketplace API - IP-based Configuration
# Prefix: ceramic_ (distinguishes from other projects)
# =============================================================================

upstream ceramic_api {
    server 127.0.0.1:8002;
    keepalive 32;
}

server {
    listen 80;
    server_name 112.213.91.103;  # Your server IP

    client_max_body_size 50M;

    # Ceramic API Routes
    location /api/v1/ {
        proxy_pass http://ceramic_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket for Chat
    location /api/v1/chat/ws {
        proxy_pass http://ceramic_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Static uploads
    location /uploads/ {
        alias /opt/ceramic-marketplace/uploads/;
        expires 30d;
    }
}
```

### Step 4: Enable Configuration
```bash
# Create symbolic link
sudo ln -sf /etc/nginx/sites-available/ceramic-api /etc/nginx/sites-enabled/

# Test configuration syntax
sudo nginx -t

# Expected output:
# nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Reload Nginx
sudo systemctl reload nginx
```

### Step 5: SSL Setup with Let's Encrypt (Optional - Production)
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d ceramic.yourdomain.com

# Auto-renewal is set up automatically
# Verify with:
sudo certbot renew --dry-run
```

### Step 6: Firewall Configuration
```bash
# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Or individually
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Check status
sudo ufw status
```

### Multi-Project Nginx Structure
When running multiple projects on the same server, organize like this:
```
/etc/nginx/sites-available/
├── ceramic-api          # Ceramic Marketplace (this project)
├── other-project-api    # Another project
└── default              # Default Nginx page

/etc/nginx/sites-enabled/
├── ceramic-api -> ../sites-available/ceramic-api
└── other-project-api -> ../sites-available/other-project-api
```

Each project uses different:
- **Upstream names**: `ceramic_api`, `other_project_api`
- **Domains/Ports**: `ceramic.domain.com`, `other.domain.com`
- **API paths**: `/api/v1/` (Ceramic), `/api/v2/` (Other)

---

## Health Check and Verification

### Check Service Health
```bash
# Auth Service
curl -s http://localhost:8002/api/v1/auth/health | jq

# Product Service
curl -s http://localhost:8002/api/v1/products/health | jq

# Order Service
curl -s http://localhost:8002/api/v1/orders/health | jq

# Chat Service
curl -s http://localhost:8002/api/v1/chat/health | jq

# Seller Service
curl -s http://localhost:8002/api/v1/seller/health | jq
```

Expected response:
```json
{
  "status": "healthy",
  "service": "auth-service",
  "timestamp": "2024-xx-xx..."
}
```

### Test External Access
From your local machine:
```bash
# Test API endpoint
curl -s http://112.213.91.103:8002/api/v1/auth/health

# Test Traefik Dashboard
# Open in browser: http://112.213.91.103:8080
```

### Check Traefik Dashboard
```bash
# Access dashboard
http://112.213.91.103:8080/dashboard/

# Or with local port forward
ssh -L 8080:localhost:8080 root@112.213.91.103
# Then open: http://localhost:8080
```

---

## Troubleshooting

### Issue 1: MySQL Connection Error
**Symptom**: Services fail with "Access denied" or "Can't connect to MySQL"

**Solution**:
```bash
# 1. Check MySQL is running
sudo systemctl status mysql

# 2. Verify user exists with correct host
mysql -u root -p -e "SELECT user, host FROM mysql.user WHERE user='ceramic_user';"

# 3. Recreate user if needed
mysql -u root -p
```
```sql
DROP USER IF EXISTS 'ceramic_user'@'%';
CREATE USER 'ceramic_user'@'%' IDENTIFIED BY 'Mysql_2025';
GRANT ALL PRIVILEGES ON ceramic_marketplace.* TO 'ceramic_user'@'%';
FLUSH PRIVILEGES;
```

### Issue 2: Container Keeps Restarting
**Symptom**: Container status shows "Restarting"

**Solution**:
```bash
# Check container logs
docker compose -f docker-compose.microservices.yml logs auth-service

# Common causes:
# - Database connection failed
# - Missing environment variables
# - Port already in use
```

### Issue 3: Port Already in Use
**Symptom**: "address already in use" error

**Solution**:
```bash
# Check what's using the port
sudo lsof -i :8002
# OR
sudo ss -tlnp | grep 8002

# Kill the process or change port in docker-compose
```

### Issue 4: Docker Network Issues
**Symptom**: Services can't communicate with each other

**Solution**:
```bash
# Recreate network
docker compose -f docker-compose.microservices.yml down
docker network prune -f
docker compose -f docker-compose.microservices.yml up -d
```

### Issue 5: host.docker.internal Not Resolving
**Symptom**: "Name or service not known" for host.docker.internal

**Solution**: The `extra_hosts` directive is already in docker-compose.yml:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

If still not working, find host IP manually:
```bash
# Get the host IP for Docker
ip addr show docker0 | grep inet
# Use this IP in DB_HOST instead of host.docker.internal
```

### Issue 6: Check Container Logs
```bash
# View all logs
docker compose -f docker-compose.microservices.yml logs

# Follow specific service logs
docker compose -f docker-compose.microservices.yml logs -f auth-service

# Check last 100 lines
docker compose -f docker-compose.microservices.yml logs --tail=100 auth-service
```

---

## Maintenance Commands

### View Logs
```bash
# All services
docker compose -f docker-compose.microservices.yml logs -f

# Specific service
docker compose -f docker-compose.microservices.yml logs -f auth-service
```

### Restart Services
```bash
# Restart all
docker compose -f docker-compose.microservices.yml restart

# Restart specific service
docker compose -f docker-compose.microservices.yml restart auth-service
```

### Stop Services
```bash
# Stop all
docker compose -f docker-compose.microservices.yml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker-compose.microservices.yml down -v
```

### Update and Rebuild
```bash
# Pull latest code (if using git)
git pull origin main

# Rebuild and restart
docker compose -f docker-compose.microservices.yml down
docker compose -f docker-compose.microservices.yml build --no-cache
docker compose -f docker-compose.microservices.yml up -d
```

### Clean Up
```bash
# Remove unused images
docker image prune -f

# Remove all unused resources
docker system prune -f

# Remove everything including volumes (DANGER)
docker system prune -a --volumes
```

### Monitor Resources
```bash
# Check container resource usage
docker stats

# Check disk usage
docker system df
```

---

## Quick Deployment Checklist

Run these commands in order for a fresh deployment:

```bash
# 1. SSH to server
ssh root@112.213.91.103

# 2. Configure MySQL (FIRST TIME ONLY)
sudo mysql -e "
CREATE DATABASE IF NOT EXISTS ceramic_marketplace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ceramic_user'@'%' IDENTIFIED BY 'Mysql_2025';
GRANT ALL PRIVILEGES ON ceramic_marketplace.* TO 'ceramic_user'@'%';
FLUSH PRIVILEGES;
"

# 3. Navigate to project
cd /opt/ceramic-marketplace

# 4. Build and start
docker compose -f docker-compose.microservices.yml build
docker compose -f docker-compose.microservices.yml up -d

# 5. Verify
docker compose -f docker-compose.microservices.yml ps
curl -s http://localhost:8002/api/v1/auth/health
```

---

## Service Ports Reference

| Service | Internal Port | External Access |
|---------|---------------|-----------------|
| Traefik Gateway | 80 | 8002 |
| Traefik Dashboard | 8080 | 8080 |
| Auth Service | 8001 | via Traefik: /api/v1/auth/* |
| Product Service | 8002 | via Traefik: /api/v1/products/* |
| Order Service | 8003 | via Traefik: /api/v1/orders/* |
| Chat Service | 8004 | via Traefik: /api/v1/chat/* |
| Seller Service | 8005 | via Traefik: /api/v1/seller/* |
| Redis | 6379 | Internal only |
| MySQL | 3306 | Host machine |

---

## API Endpoints

Base URL: `http://112.213.91.103:8002`

- **Auth**: `http://112.213.91.103:8002/api/v1/auth/`
- **Users**: `http://112.213.91.103:8002/api/v1/users/`
- **Products**: `http://112.213.91.103:8002/api/v1/products/`
- **Reviews**: `http://112.213.91.103:8002/api/v1/reviews/`
- **Orders**: `http://112.213.91.103:8002/api/v1/orders/`
- **Cart**: `http://112.213.91.103:8002/api/v1/cart/`
- **Chat**: `http://112.213.91.103:8002/api/v1/chat/`
- **Seller**: `http://112.213.91.103:8002/api/v1/seller/`

---

## Support

If you encounter issues not covered in this guide:

1. Check service logs: `docker compose logs <service-name>`
2. Verify MySQL connectivity: `mysql -u ceramic_user -p'Mysql_2025' -h 127.0.0.1`
3. Ensure firewall allows required ports: `sudo ufw status`
4. Check system resources: `htop` or `docker stats`

---

*Last updated: December 2024*
