#!/bin/bash

#############################################
# Ceramic Marketplace API - Remote Deployment
# Deploy to a remote server with static IP
#############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Remote Server Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}✗ SSH client is not installed${NC}"
    exit 1
fi

# Get remote server details
read -p "Enter remote server IP address: " SERVER_IP
read -p "Enter SSH username (default: root): " SSH_USER
SSH_USER=${SSH_USER:-root}
read -p "Enter SSH port (default: 22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

# Confirm details
echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo -e "  Server IP: ${GREEN}$SERVER_IP${NC}"
echo -e "  SSH User:  ${GREEN}$SSH_USER${NC}"
echo -e "  SSH Port:  ${GREEN}$SSH_PORT${NC}"
echo ""
read -p "Continue with deployment? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Test SSH connection
echo -e "${GREEN}→${NC} Testing SSH connection..."
if ! ssh -p $SSH_PORT -o ConnectTimeout=10 $SSH_USER@$SERVER_IP "echo 'SSH connection successful'" &> /dev/null; then
    echo -e "${RED}✗ Cannot connect to server. Please check:${NC}"
    echo -e "  - Server IP address is correct"
    echo -e "  - SSH port is correct"
    echo -e "  - SSH key is configured or password is correct"
    echo -e "  - Server is accessible from your network"
    exit 1
fi
echo -e "${GREEN}✓ SSH connection successful${NC}"

# Remote deployment commands
echo ""
echo -e "${GREEN}→${NC} Starting remote deployment..."
echo ""

ssh -p $SSH_PORT $SSH_USER@$SERVER_IP bash << 'ENDSSH'
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Remote Server Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}→ Installing Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker is already installed${NC}"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}→ Installing Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose is already installed${NC}"
fi

# Create application directory
APP_DIR="/opt/ceramic-marketplace"
echo -e "${GREEN}→${NC} Setting up application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or update repository
if [ -d "back_end" ]; then
    echo -e "${GREEN}→${NC} Updating existing repository..."
    cd back_end
    git pull origin main || echo -e "${YELLOW}⚠ Git pull failed${NC}"
else
    echo -e "${GREEN}→${NC} Cloning repository..."
    if [ -d ".git" ]; then
        cd back_end
    else
        # Ask for repository URL
        echo -e "${YELLOW}Please clone your repository to $APP_DIR${NC}"
        echo -e "Run: git clone YOUR_REPO_URL ."
        echo -e "Then run the local deploy-production.sh script"
        exit 1
    fi
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}⚠ Creating .env.production from example...${NC}"
    cp .env.example .env.production
    echo -e "${RED}IMPORTANT: Edit .env.production with your production values!${NC}"
    echo -e "Run: nano .env.production"
    echo ""
    echo -e "Required changes:"
    echo -e "  - SECRET_KEY=\$(openssl rand -hex 32)"
    echo -e "  - DB_PASSWORD=your-strong-password"
    echo -e "  - DB_ROOT_PASSWORD=your-root-password"
    echo -e "  - CORS_ORIGINS with your domains/IPs"
    echo ""
    read -p "Press Enter after you've configured .env.production..."
fi

# Create directories
echo -e "${GREEN}→${NC} Creating required directories..."
mkdir -p uploads logs backups nginx/ssl
chmod 755 uploads logs backups

# Deploy with Docker Compose
echo -e "${GREEN}→${NC} Deploying application..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true
docker-compose -f docker-compose.production.yml up -d --build

# Wait for services
echo -e "${GREEN}→${NC} Waiting for services to start..."
sleep 15

# Check health
echo -e "${GREEN}→${NC} Checking application health..."
if curl -f http://localhost/health &> /dev/null; then
    echo -e "${GREEN}✓ Application is healthy!${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed, checking logs...${NC}"
    docker-compose -f docker-compose.production.yml logs --tail=50
fi

# Show status
echo ""
echo -e "${GREEN}→${NC} Service status:"
docker-compose -f docker-compose.production.yml ps

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Remote Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

ENDSSH

# Get server IP
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Successful!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Your API is now running at:"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/api/docs"
echo -e "  ${GREEN}→${NC} http://$SERVER_IP/health"
echo ""
echo -e "To manage the application:"
echo -e "  ${GREEN}→${NC} SSH: ssh -p $SSH_PORT $SSH_USER@$SERVER_IP"
echo -e "  ${GREEN}→${NC} Logs: docker-compose -f docker-compose.production.yml logs -f"
echo -e "  ${GREEN}→${NC} Stop: docker-compose -f docker-compose.production.yml down"
echo ""
echo -e "${YELLOW}⚠ Next steps:${NC}"
echo -e "  1. Configure firewall (UFW) to allow ports 80, 443, 22"
echo -e "  2. Setup SSL/HTTPS with Let's Encrypt"
echo -e "  3. Configure automated backups"
echo -e "  4. Update CORS settings in .env.production"
echo ""
echo -e "See ${GREEN}DOCKER_DEPLOY.md${NC} for detailed instructions."
echo ""
