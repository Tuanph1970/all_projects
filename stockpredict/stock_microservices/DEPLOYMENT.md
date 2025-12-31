# Stock Helper - Deployment Guide

## Overview

This guide covers deploying the Stock Helper microservices and React web application.

**Important:** Port 8002 is reserved for an existing API service and is NOT exposed by this deployment.

## Architecture

```
                                    ┌─────────────────────────┐
                                    │     Existing Service    │
                                    │       Port 8002         │
                                    └─────────────────────────┘
                                              │
┌─────────────────────────────────────────────┴─────────────────────────────────────────────┐
│                                    Your Local PC / Server                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────────────────────────┐   │
│  │   React     │────▶│   Nginx     │────▶│              Traefik Gateway               │   │
│  │   :3000     │     │   :80/:443  │     │                  :8088                      │   │
│  └─────────────┘     └─────────────┘     └──────────────────┬──────────────────────────┘   │
│                                                              │                              │
│  ┌───────────────────────────────────────────────────────────┴────────────────────────┐    │
│  │                              Microservices (Docker Network)                        │    │
│  ├────────────────┬────────────────┬────────────────┬────────────────┬───────────────┤    │
│  │  Auth :8007    │  Stock :8001   │  Portfolio     │  Analysis      │  Prediction   │    │
│  │                │                │  :8003         │  :8004         │  :8002*       │    │
│  ├────────────────┼────────────────┼────────────────┼────────────────┼───────────────┤    │
│  │  AI :8005      │  Chatbot :8006 │  RabbitMQ      │  Redis         │  MySQL        │    │
│  │                │                │  :5672         │  :6379         │  (SSH Tunnel) │    │
│  └────────────────┴────────────────┴────────────────┴────────────────┴───────────────┘    │
│                                                                                             │
│  * Prediction service uses internal port 8002 but is NOT exposed to host                   │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Local Development

```bash
cd stock_microservices

# 1. Create environment file
cp .env.local .env

# 2. Deploy microservices
./scripts/deploy-local.sh

# 3. Deploy React (in another terminal)
./scripts/deploy-react.sh
```

### Production

```bash
cd stock_microservices

# 1. Create and configure environment file
cp .env.production .env
# Edit .env and change ALL passwords!

# 2. Build React production bundle
./scripts/deploy-prod.sh --build-react

# 3. Deploy everything
./scripts/deploy-prod.sh --build
```

## Local Development Deployment

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for native React development)
- Git

### Step 1: Configure Environment

```bash
cd stock_microservices
cp .env.local .env
```

### Step 2: Start Microservices

```bash
# Basic deployment
./scripts/deploy-local.sh

# With rebuild
./scripts/deploy-local.sh --build

# Include React in Docker
./scripts/deploy-local.sh --react

# Clean start (removes volumes)
./scripts/deploy-local.sh --clean --build
```

### Step 3: Start React Client

**Option A: Native (recommended for development)**
```bash
./scripts/deploy-react.sh
# Opens http://localhost:3000
```

**Option B: Docker**
```bash
./scripts/deploy-react.sh --docker
```

### Local Access URLs

| Service | URL |
|---------|-----|
| React App | http://localhost:3000 |
| API Gateway | http://localhost:8088 |
| Traefik Dashboard | http://localhost:8089 |
| RabbitMQ UI | http://localhost:15672 |
| Grafana | http://localhost:3100 |
| Prometheus | http://localhost:9090 |
| Jaeger | http://localhost:16686 |

### Direct Microservice Access

| Service | URL |
|---------|-----|
| Auth | http://localhost:8007/stock_helper/api/v2/auth |
| Stock Data | http://localhost:8001/stock_helper/api/v2 |
| Portfolio | http://localhost:8003/stock_helper/api/v2/portfolio |
| Analysis | http://localhost:8004/stock_helper/api/v2/analysis |
| AI Insights | http://localhost:8005/stock_helper/api/v2/ai |
| Chatbot | http://localhost:8006/stock_helper/api/v2/chatbot |
| Prediction | Via Traefik only (port 8002 reserved) |

## Nginx Conflict Resolution

Your system has **existing nginx** running on port 80. The Stock Helper uses separate ports to avoid conflicts.

### Three Options Available:

#### Option 1: Direct Port Access (Simplest)
Access Stock Helper directly on different ports:
- **HTTP**: `http://your-server:8080`
- **HTTPS**: `https://your-server:8443`

No additional configuration needed.

#### Option 2: Path-Based Routing (Same Domain)
Access both projects on port 80:
- **Existing project**: `http://your-server/`
- **Stock Helper**: `http://your-server/stock/`

Add to `/etc/nginx/sites-available/default`:
```nginx
location /stock/ {
    proxy_pass http://127.0.0.1:8080/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /stock_helper/api/ {
    proxy_pass http://127.0.0.1:8080/stock_helper/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then reload nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

#### Option 3: Subdomain Routing (Separate Domain)
Access Stock Helper on a subdomain:
- **Existing project**: `http://your-domain.com`
- **Stock Helper**: `http://stock.your-domain.com`

```bash
sudo cp production/nginx/stock-helper.system-nginx.conf /etc/nginx/sites-available/stock-helper
sudo ln -s /etc/nginx/sites-available/stock-helper /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Architecture with System Nginx

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              System Nginx (:80)                             │
│  /etc/nginx/sites-enabled/default                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                    │                                        │
│         /  (existing)              │        /stock/ or stock.domain         │
│              │                     │                  │                     │
│              ▼                     │                  ▼                     │
│    ┌─────────────────┐            │         ┌─────────────────┐            │
│    │ Existing Project│            │         │  Stock Helper   │            │
│    │  /var/www/html  │            │         │  Docker :8080   │            │
│    └─────────────────┘            │         └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Production Deployment

### Prerequisites

- Docker & Docker Compose
- SSL certificates (for HTTPS, optional)
- Domain configured (optional)

### Step 1: Configure Environment

```bash
cp .env.production .env

# Edit and change ALL default passwords
vim .env
```

**Required changes in `.env`:**
- `SSH_PASSWORD` - SSH tunnel password
- `MYSQL_PASSWORD` - Database password
- `RABBITMQ_PASSWORD` - Message broker password
- `REDIS_PASSWORD` - Cache password
- `JWT_SECRET_KEY` - Generate with `openssl rand -hex 32`
- `GRAFANA_PASSWORD` - Monitoring password
- `DOMAIN` - Your domain name

### Step 2: Build React

```bash
./scripts/deploy-prod.sh --build-react
```

### Step 3: Configure SSL (Optional but recommended)

Place SSL certificates in `production/ssl/`:
- `fullchain.pem`
- `privkey.pem`

Uncomment HTTPS section in `production/nginx/conf.d/default.conf`

### Step 4: Deploy

```bash
# First deployment
./scripts/deploy-prod.sh --build

# Update deployment
./scripts/deploy-prod.sh --update

# View status
./scripts/deploy-prod.sh --status
```

### Production Management

```bash
# View logs
./scripts/deploy-prod.sh --logs

# Stop all services
./scripts/deploy-prod.sh --stop

# Backup before update
./scripts/deploy-prod.sh --backup

# Rollback if needed
./scripts/deploy-prod.sh --rollback
```

## Port Conflict Resolution

Your existing service on port 8002 is protected:

1. **Local Development**: Prediction service uses internal port 8002 but is NOT published to host
2. **Production**: All services are internal, accessed only through Nginx → Traefik

Access prediction service via API gateway:
- Local: `http://localhost:8088/stock_helper/api/v2/predictions`
- Production: `https://your-domain/stock_helper/api/v2/predictions`

## Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose -f docker-compose.yml -f docker-compose.local.yml logs -f

# Restart specific service
docker-compose -f docker-compose.yml -f docker-compose.local.yml restart auth-service
```

### SSH Tunnel issues

```bash
# Check SSH tunnel status
docker logs stock-ssh-tunnel

# Verify database connectivity
docker exec -it stock-auth-service python -c "from app.db import engine; print('Connected!')"
```

### React build issues

```bash
cd ../stock_react_javascript/stock-react-app
rm -rf node_modules
npm install
npm run build
```

## File Structure

```
stock_microservices/
├── docker-compose.yml          # Base configuration
├── docker-compose.local.yml    # Local development overrides
├── docker-compose.prod.yml     # Production overrides
├── .env.local                  # Local environment template
├── .env.production             # Production environment template
├── scripts/
│   ├── deploy-local.sh         # Local deployment script
│   ├── deploy-react.sh         # React deployment script
│   └── deploy-prod.sh          # Production deployment script
├── production/
│   ├── nginx/
│   │   ├── nginx.conf          # Nginx main config
│   │   └── conf.d/default.conf # Server configuration
│   └── ssl/                    # SSL certificates (production)
└── traefik/
    └── dynamic.yml             # Traefik routing rules

stock_react_javascript/stock-react-app/
├── Dockerfile                  # Production build
├── Dockerfile.dev              # Development with hot-reload
├── nginx.conf                  # Standalone nginx config
└── build/                      # Production build output
```
