# Complete Deployment Guide - All Projects

Deploy all projects (Mercai, Stock, Mathematic) on a fresh Ubuntu machine using Docker only.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install Docker](#install-docker)
3. [Clone Repository](#clone-repository)
4. [Project Overview](#project-overview)
5. [Environment Setup](#environment-setup)
6. [Deploy All Projects](#deploy-all-projects)
7. [Verify Deployment](#verify-deployment)
8. [Port Reference](#port-reference)
9. [Management Commands](#management-commands)
10. [Troubleshooting](#troubleshooting)
11. [Maintenance](#maintenance)

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04 LTS or later
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk**: Minimum 20GB free space
- **Network**: Internet connection for pulling Docker images

### Required Software

The only requirement is Docker. All other dependencies run inside containers.

---

## Install Docker

### Step 1: Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### Step 2: Install Docker

```bash
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

# Add current user to docker group (avoids using sudo)
sudo usermod -aG docker $USER

# Apply group changes (or logout/login)
newgrp docker
```

### Step 3: Verify Installation

```bash
docker --version
docker compose version
docker run hello-world
```

Expected output:
```
Docker version 24.x.x or higher
Docker Compose version v2.x.x or higher
Hello from Docker! (success message)
```

---

## Clone Repository

### Step 1: Install Git (if not installed)

```bash
sudo apt install -y git
```

### Step 2: Clone the Repository

```bash
# Navigate to your preferred directory
cd ~

# Clone the repository
git clone https://github.com/Tuanph1970/all_projects.git

# Enter project directory
cd all_projects
```

---

## Project Overview

This repository contains three backend API projects:

| Project | Description | API Port | Database Port | Technologies |
|---------|-------------|----------|---------------|--------------|
| **Mercai** | Marketplace API | 8002 | 3308 (MySQL) | Python/FastAPI, MySQL, Redis |
| **Stock Predict** | Stock analysis API | 8080 | 3309 (MySQL) | Python/Django, MySQL |
| **Mathematic Mobile** | Math solver API | 8003 | 3310 (MySQL) | C#/.NET, MySQL, Redis |

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Ubuntu Server                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │  Mercai API    │  │   Stock API     │  │   Math API      │         │
│  │     :8002       │  │     :8080       │  │     :8003       │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│  ┌────────┴────────┐  ┌────────┴────────┐  ┌────────┴────────┐         │
│  │  MySQL :3308    │  │  MySQL :3309    │  │  MySQL :3310    │         │
│  │  Redis :6379    │  │                 │  │  Redis :6380    │         │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘         │
│                                                                         │
│  Additional Services:                                                   │
│  • RabbitMQ :5673 (management :15673) - Mathematic                     │
│  • Traefik Dashboard :8083 - Mathematic                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Environment Setup

### Step 1: Create Shared Environment File

```bash
cd ~/all_projects

# Copy the example file
cp .deploy-env.example .deploy-env

# Edit if needed (default values work for most cases)
nano .deploy-env
```

Default `.deploy-env` contents:
```bash
# MySQL Configuration
MYSQL_ROOT_PASSWORD=Mysql_2025

# Mercai Project
MERCAI_API_PORT=8002
MERCAI_DB_PORT=3308
MERCAI_DB_NAME=mercai_db
MERCAI_DB_USER=mercai_user
MERCAI_DB_PASSWORD=Mysql_2025

# Stock Project
STOCK_API_PORT=8080
STOCK_DB_PORT=3309
STOCK_DB_NAME=stockpredict_db
STOCK_DB_USER=stock_user
STOCK_DB_PASSWORD=Mysql_2025

# Mathematic Project
MATH_API_PORT=8003
MATH_DB_PORT=3310
MATH_DB_NAME=mathematic_db
MATH_DB_USER=mathematic_user
MATH_DB_PASSWORD=Mysql_2025
```

### Step 2: Setup Project-Specific Environment Files

#### Mercai Project

```bash
cd ~/all_projects/mercai/back_end
cp .env.example .env
```

#### Stock Project

```bash
cd ~/all_projects/stockpredict/stock_microservices
cp .env.example .env
```

#### Mathematic Project

```bash
cd ~/all_projects/mathematic-mobile/backend
cp .env.example .env
```

### Step 3: AI / LLM (DeepSeek) API Key — Stock Project

The Stock Predict AI-insights and company-news features need an LLM key. For the
**full-stack deploy** (`deploy-interactive.sh`), the relevant file is
`stockpredict/.env` — **not** `stockpredict/stock_microservices/.env`. This file is
auto-generated on first run of `deploy-interactive.sh`, so the normal order is:

```bash
cd ~/all_projects
./deploy-interactive.sh          # generates stockpredict/.env (with an empty OPENAI_API_KEY)
nano stockpredict/.env           # paste your DeepSeek key, then re-deploy
```

In `stockpredict/.env` you will find this block (the key is intentionally **empty** —
you must fill it in):

```bash
LLM_PROVIDER=auto
OPENAI_API_KEY=            # <-- paste your DeepSeek key here (sent as the bearer token)
ANTHROPIC_API_KEY=
LLM_MODEL=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com/v1
```

Notes:
- The model is **`deepseek-chat`** (DeepSeek is OpenAI-compatible — there is no
  "DeepSeek 4.0"). Put the DeepSeek key into `OPENAI_API_KEY`, not a DeepSeek-named var.
- **Empty `OPENAI_API_KEY` = template mode**: canned neutral sentiment, so company
  good/bad-news notifications will not fire. Fill the key to enable real analysis.
- To use OpenAI instead of DeepSeek: `LLM_MODEL=gpt-4o-mini` and
  `LLM_BASE_URL=https://api.openai.com/v1`.
- If you upgraded from an older clone and the block is missing, just re-run
  `./deploy-interactive.sh` — it now backfills the AI/LLM block into an existing
  `stockpredict/.env`. After editing the key, re-deploy so ai-insights picks it up:
  ```bash
  cd ~/all_projects/stockpredict
  docker compose -f docker-compose.full-stack.yml up -d ai-insights-service news-service
  ```

---

## Deploy All Projects

### Method 1: Interactive Deployment (Recommended)

```bash
cd ~/all_projects

# Make scripts executable (first time only)
chmod +x deploy-interactive.sh stop-interactive.sh deploy-projects.sh

# Run interactive deployment
./deploy-interactive.sh
```

The interactive script will:
- Ask which projects to deploy (Yes/No for each)
- Ask if you want to build images
- Show current status of all services
- Deploy only selected projects

### Method 2: Command Line Deployment

```bash
cd ~/all_projects

# Deploy all projects
./deploy-projects.sh start all

# Deploy with fresh build
./deploy-projects.sh start all --build

# Deploy specific projects
./deploy-projects.sh start mercai stock
./deploy-projects.sh start math
```

### Method 3: Manual Deployment (Per Project)

#### Deploy Mercai Project

```bash
cd ~/all_projects/mercai/back_end
docker compose --env-file .env up -d --build
```

#### Deploy Stock Project

```bash
cd ~/all_projects/stockpredict/stock_microservices
docker compose --env-file .env up -d --build
```

#### Deploy Mathematic Project

```bash
cd ~/all_projects/mathematic-mobile/backend
docker compose --env-file .env up -d --build
```

---

## Verify Deployment

### Check All Containers

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected output shows all containers with "Up" status.

### Test API Endpoints

```bash
# Mercai API
curl http://localhost:8002/health
curl http://localhost:8002/docs    # Swagger UI

# Stock API
curl http://localhost:8080/health
curl http://localhost:8080/stock/api/    # API docs

# Mathematic API
curl http://localhost:8003/swagger    # Swagger UI
curl http://localhost:8003/health
```

### Check Database Connections

```bash
# Mercai MySQL
docker exec -it mercai_mysql mysql -u root -pMysql_2025 -e "SHOW DATABASES;"

# Stock MySQL
docker exec -it stock_mysql mysql -u root -pMysql_2025 -e "SHOW DATABASES;"

# Mathematic MySQL
docker exec -it math_mysql mysql -u root -pMysql_2025 -e "SHOW DATABASES;"
```

### Check Redis

```bash
# Mercai Redis
docker exec -it mercai_redis redis-cli ping
# Expected: PONG

# Mathematic Redis
docker exec -it math_redis redis-cli ping
# Expected: PONG
```

---

## Port Reference

### API Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Mercai API | 8002 | http://localhost:8002 | Marketplace API |
| Stock API | 8080 | http://localhost:8080 | Stock prediction API |
| Math API | 8003 | http://localhost:8003 | Math solver API |

### API Documentation

| Service | URL |
|---------|-----|
| Mercai Swagger | http://localhost:8002/docs |
| Stock API | http://localhost:8080/stock/api/ |
| Math Swagger | http://localhost:8003/swagger |

### Database Services

| Service | Port | Credentials |
|---------|------|-------------|
| Mercai MySQL | 3308 | mercai_user / Mysql_2025 |
| Stock MySQL | 3309 | stock_user / Mysql_2025 |
| Math MySQL | 3310 | mathematic_user / Mysql_2025 |

### Cache Services

| Service | Port |
|---------|------|
| Mercai Redis | 6379 |
| Math Redis | 6380 |

### Additional Services (Mathematic)

| Service | Port | Notes |
|---------|------|-------|
| RabbitMQ | 5673 | Message queue |
| RabbitMQ Management | 15673 | Admin UI (admin/admin123) |
| Traefik Dashboard | 8083 | For microservices routing |

---

## Management Commands

### View Status

```bash
# Using deployment script
./deploy-projects.sh status

# Using Docker directly
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### View Logs

```bash
# All logs for a project
./deploy-projects.sh logs mercai
./deploy-projects.sh logs stock
./deploy-projects.sh logs math

# Specific container logs
docker logs mercai_api --tail 100 -f
docker logs stock_api --tail 100 -f
docker logs math_api --tail 100 -f
```

### Stop Services

```bash
# Interactive stop
./stop-interactive.sh

# Command line stop
./deploy-projects.sh stop all

# Stop specific project
./deploy-projects.sh stop mercai
```

### Restart Services

```bash
./deploy-projects.sh restart all
./deploy-projects.sh restart mercai
```

### Rebuild and Restart

```bash
./deploy-projects.sh restart all --build
```

---

## Troubleshooting

### Issue 1: Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :PORT_NUMBER

# Example: Check port 8002
sudo lsof -i :8002

# Kill the process or change port in .deploy-env
```

### Issue 2: Container Not Starting

```bash
# Check container logs
docker logs CONTAINER_NAME

# Examples
docker logs mercai_api
docker logs mercai_mysql

# Common causes:
# - Database not ready yet (wait and retry)
# - Missing environment variables
# - Port conflict
```

### Issue 3: Database Connection Failed

```bash
# Verify MySQL container is healthy
docker ps | grep mysql

# Check MySQL logs
docker logs mercai_mysql
docker logs stock_mysql
docker logs math_mysql

# Test connection from container
docker exec -it mercai_api python -c "from shared.database import engine; print('Connected!')"
```

### Issue 4: Redis Connection Failed

```bash
# Test Redis
docker exec -it mercai_redis redis-cli ping

# Check Redis logs
docker logs mercai_redis
```

### Issue 5: Docker Network Issues

```bash
# List networks
docker network ls

# Remove and recreate (stops containers first)
docker compose down
docker network prune -f
docker compose up -d
```

### Issue 6: Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply changes
newgrp docker

# Or logout and login again
```

### Issue 7: Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker resources
docker system prune -a --volumes

# This removes:
# - All stopped containers
# - All unused networks
# - All unused images
# - All unused volumes (WARNING: data loss)
```

### Reset Everything (Nuclear Option)

```bash
# Stop all containers
./deploy-projects.sh stop all

# Clean all Docker resources including volumes
./cleanup-all.sh --volumes --force

# Rebuild from scratch
./deploy-projects.sh start all --build
```

---

## Maintenance

### Database Backup

```bash
# Backup all databases
docker exec mercai_mysql mysqldump -u root -pMysql_2025 mercai_db > mercai_backup_$(date +%Y%m%d).sql
docker exec stock_mysql mysqldump -u root -pMysql_2025 stockpredict_db > stock_backup_$(date +%Y%m%d).sql
docker exec math_mysql mysqldump -u root -pMysql_2025 mathematic_db > math_backup_$(date +%Y%m%d).sql
```

### Database Restore

```bash
# Restore database
cat mercai_backup_20250101.sql | docker exec -i mercai_mysql mysql -u root -pMysql_2025 mercai_db
```

### Update Code and Redeploy

```bash
# Pull latest changes
cd ~/all_projects
git pull

# Rebuild and restart
./deploy-projects.sh restart all --build
```

### Monitor Resource Usage

```bash
# Real-time container stats
docker stats

# Check disk usage by Docker
docker system df
```

### Clean Up Unused Resources

```bash
# Remove unused images
docker image prune -f

# Remove unused containers
docker container prune -f

# Remove unused volumes (WARNING: data loss)
docker volume prune -f

# Remove everything unused
docker system prune -a
```

---

## Production Deployment Notes

For production deployment, consider:

### 1. Change Default Passwords

Edit `.deploy-env` and all project `.env` files:
```bash
# Use strong passwords
MYSQL_ROOT_PASSWORD=YourStrongPassword123!
MERCAI_DB_PASSWORD=AnotherStrongPassword!
# etc.
```

### 2. Configure Firewall

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8002/tcp    # Mercai API
sudo ufw allow 8080/tcp    # Stock API
sudo ufw allow 8003/tcp    # Math API
sudo ufw enable
```

### 3. Setup Nginx Reverse Proxy (Optional)

```bash
# Install Nginx
sudo apt install -y nginx

# Copy configuration
sudo cp nginx-unified-projects.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/nginx-unified-projects.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

This exposes all services under a single domain:
- `/mercai/*` → Mercai API
- `/stock/*` → Stock API
- `/math/*` → Math API

### 4. Setup SSL (HTTPS)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Quick Reference

### Essential Commands

```bash
# Deploy all
./deploy-projects.sh start all

# Stop all
./deploy-projects.sh stop all

# Check status
./deploy-projects.sh status

# View logs
./deploy-projects.sh logs [mercai|stock|math]

# Restart with rebuild
./deploy-projects.sh restart all --build
```

### Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| All MySQL (root) | root | Mysql_2025 |
| Mercai DB | mercai_user | Mysql_2025 |
| Stock DB | stock_user | Mysql_2025 |
| Mathematic DB | mathematic_user | Mysql_2025 |
| RabbitMQ | admin | admin123 |

### Health Check URLs

| Service | Health URL |
|---------|------------|
| Mercai | http://localhost:8002/health |
| Stock | http://localhost:8080/health |
| Mathematic | http://localhost:8003/health |

---

## Support

For issues:
1. Check container logs: `docker logs CONTAINER_NAME`
2. Check this troubleshooting section
3. Verify environment configuration
4. Check container health: `docker ps`

---

**Last Updated**: January 2026
**Repository**: https://github.com/Tuanph1970/all_projects.git
