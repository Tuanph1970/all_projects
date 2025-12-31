#!/bin/bash

###############################################
# Ceramic Marketplace API - Server Deployment
# Deploy to remote server via SSH
# Ports: API=8004, MySQL=3308
###############################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Ceramic API - Server Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if SSH is available
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}✗ SSH client is not installed${NC}"
    exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${RED}✗ .env.production file not found${NC}"
    echo ""
    echo -e "${YELLOW}Please create .env.production first:${NC}"
    echo -e "  1. Copy template: ${GREEN}cp .env.server .env.production${NC}"
    echo -e "  2. Edit file: ${GREEN}nano .env.production${NC}"
    echo -e "  3. Update these values:"
    echo -e "     - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo -e "     - DB_PASSWORD"
    echo -e "     - DB_ROOT_PASSWORD"
    echo -e "     - CORS_ORIGINS (add your server IP)"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Found .env.production${NC}"
echo ""

# Get server details
echo -e "${BLUE}Enter your server details:${NC}"
read -p "Server IP address: " SERVER_IP
read -p "SSH username [root]: " SSH_USER
SSH_USER=${SSH_USER:-root}
read -p "SSH port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

# Validate SERVER_IP
if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}✗ Server IP is required${NC}"
    exit 1
fi

# Show configuration
echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo -e "  Server IP: ${GREEN}$SERVER_IP${NC}"
echo -e "  SSH User:  ${GREEN}$SSH_USER${NC}"
echo -e "  SSH Port:  ${GREEN}$SSH_PORT${NC}"
echo -e "  API will be at: ${GREEN}http://$SERVER_IP:8004${NC}"
echo ""
read -p "Continue with deployment? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Deployment cancelled${NC}"
    exit 0
fi

# Test SSH connection
echo ""
echo -e "${GREEN}→${NC} Testing SSH connection..."
if ! ssh -p $SSH_PORT -o ConnectTimeout=10 -o BatchMode=yes $SSH_USER@$SERVER_IP "echo 'Connection successful'" &> /dev/null; then
    echo -e "${YELLOW}⚠ Cannot connect with SSH key, will prompt for password${NC}"
    echo -e "${GREEN}Testing connection with password...${NC}"
    if ! ssh -p $SSH_PORT -o ConnectTimeout=10 $SSH_USER@$SERVER_IP "echo 'Connection successful'"; then
        echo -e "${RED}✗ Cannot connect to server${NC}"
        echo -e "${YELLOW}Please check:${NC}"
        echo -e "  - Server IP address is correct"
        echo -e "  - SSH port is correct"
        echo -e "  - Username is correct"
        echo -e "  - SSH service is running on server"
        exit 1
    fi
fi

echo -e "${GREEN}✓ SSH connection successful${NC}"
echo ""

# Deploy to remote server
echo -e "${GREEN}→${NC} Starting remote deployment..."
echo ""

# Create deployment script
DEPLOY_SCRIPT=$(cat << 'ENDDEPLOY'
#!/bin/bash
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
    usermod -aG docker $USER || true
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}→ Installing Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

echo ""
echo -e "${GREEN}→${NC} Setting up application directory..."
APP_DIR="/opt/ceramic-api"
mkdir -p $APP_DIR
cd $APP_DIR

# Clone or update repository
if [ -d "ceramic_mobile_app" ]; then
    echo -e "${GREEN}→${NC} Updating repository..."
    cd ceramic_mobile_app
    git pull origin main || echo -e "${YELLOW}⚠ Git pull failed (might need credentials)${NC}"
    cd back_end
else
    echo -e "${GREEN}→${NC} Cloning repository..."
    git clone https://github.com/Tuanph1970/ceramic_mobile_app.git || {
        echo -e "${YELLOW}⚠ Could not clone repository${NC}"
        echo -e "${YELLOW}Please clone it manually to $APP_DIR${NC}"
        exit 1
    }
    cd ceramic_mobile_app/back_end
fi

echo -e "${GREEN}✓ Repository ready${NC}"
echo ""

# Check for .env.production
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}⚠ .env.production will be uploaded from local machine${NC}"
fi

# Create directories
echo -e "${GREEN}→${NC} Creating directories..."
mkdir -p uploads logs backups
chmod 755 uploads logs backups

echo -e "${GREEN}✓ Setup complete${NC}"
ENDDEPLOY
)

# Execute remote setup
echo "$DEPLOY_SCRIPT" | ssh -p $SSH_PORT $SSH_USER@$SERVER_IP "bash -s"

# Copy files to server
echo ""
echo -e "${GREEN}→${NC} Uploading configuration and project files..."

# Upload .env.production
scp -P $SSH_PORT .env.production $SSH_USER@$SERVER_IP:/opt/ceramic-api/ceramic_mobile_app/back_end/.env.production

# Upload docker-compose file
scp -P $SSH_PORT docker-compose.server.yml $SSH_USER@$SERVER_IP:/opt/ceramic-api/ceramic_mobile_app/back_end/docker-compose.server.yml

# Upload Dockerfile
scp -P $SSH_PORT Dockerfile $SSH_USER@$SERVER_IP:/opt/ceramic-api/ceramic_mobile_app/back_end/Dockerfile

# Upload docker-entrypoint.sh
scp -P $SSH_PORT docker-entrypoint.sh $SSH_USER@$SERVER_IP:/opt/ceramic-api/ceramic_mobile_app/back_end/docker-entrypoint.sh

echo -e "${GREEN}✓ Files uploaded${NC}"
echo ""

# Deploy application
echo -e "${GREEN}→${NC} Deploying application on server..."

ssh -p $SSH_PORT $SSH_USER@$SERVER_IP << 'ENDSSH'
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /opt/ceramic-api/ceramic_mobile_app/back_end

# Load environment variables
export $(cat .env.production | grep -v '^#' | xargs) 2>/dev/null || true

# Stop existing services
echo -e "${GREEN}→${NC} Stopping existing services..."
docker-compose -f docker-compose.server.yml down 2>/dev/null || true

# Build and start
echo -e "${GREEN}→${NC} Building and starting services..."
docker-compose -f docker-compose.server.yml up -d --build

# Wait for services
echo -e "${GREEN}→${NC} Waiting for services..."
sleep 15

# Check health
echo -e "${GREEN}→${NC} Checking health..."
if curl -f http://localhost:8004/health &> /dev/null; then
    echo -e "${GREEN}✓ API is healthy!${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed, showing logs...${NC}"
    docker-compose -f docker-compose.server.yml logs --tail=30 api
fi

# Show status
echo ""
echo -e "${GREEN}→${NC} Service status:"
docker-compose -f docker-compose.server.yml ps

ENDSSH

# Final message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}Your API is now running:${NC}"
echo -e "  ${GREEN}→${NC} API: http://$SERVER_IP:8004"
echo -e "  ${GREEN}→${NC} API Docs: http://$SERVER_IP:8004/api/docs"
echo -e "  ${GREEN}→${NC} Health: http://$SERVER_IP:8004/health"
echo ""
echo -e "${BLUE}To manage your deployment:${NC}"
echo -e "  ${GREEN}→${NC} SSH: ssh -p $SSH_PORT $SSH_USER@$SERVER_IP"
echo -e "  ${GREEN}→${NC} View logs: docker-compose -f docker-compose.server.yml logs -f"
echo -e "  ${GREEN}→${NC} Restart: docker-compose -f docker-compose.server.yml restart"
echo ""
echo -e "${YELLOW}⚠ Important Next Steps:${NC}"
echo -e "  1. Configure firewall: sudo ufw allow 8004/tcp"
echo -e "  2. After first deployment, set SEED_DATA=false in .env.production"
echo -e "  3. Setup automated backups (see DEPLOYMENT_GUIDE.md)"
echo -e "  4. Consider setting up SSL/HTTPS"
echo ""
echo -e "${BLUE}Test your API:${NC}"
echo -e "  curl http://$SERVER_IP:8004/health"
echo ""
