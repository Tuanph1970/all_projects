#!/bin/bash
# =============================================================================
# Stock Predict WebAPI - Remote Server Setup Script
# =============================================================================
# This script sets up a fresh Ubuntu/Debian server with:
# - Docker & Docker Compose
# - MySQL Server
# - Stock Predict WebAPI
#
# Usage: sudo bash setup-server.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Stock Predict WebAPI - Server Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo bash setup-server.sh)${NC}"
    exit 1
fi

# =============================================================================
# Step 1: Update System
# =============================================================================
echo -e "\n${YELLOW}[1/6] Updating system packages...${NC}"
apt-get update
apt-get upgrade -y

# =============================================================================
# Step 2: Install Docker
# =============================================================================
echo -e "\n${YELLOW}[2/6] Installing Docker...${NC}"

# Remove old versions
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install prerequisites
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

echo -e "${GREEN}Docker installed successfully!${NC}"
docker --version

# =============================================================================
# Step 3: Install MySQL Server
# =============================================================================
echo -e "\n${YELLOW}[3/6] Installing MySQL Server...${NC}"

# Install MySQL
apt-get install -y mysql-server

# Start and enable MySQL
systemctl start mysql
systemctl enable mysql

echo -e "${GREEN}MySQL installed successfully!${NC}"
mysql --version

# =============================================================================
# Step 4: Configure MySQL for Docker Access
# =============================================================================
echo -e "\n${YELLOW}[4/6] Configuring MySQL...${NC}"

# Generate random password
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 24)
DB_PASSWORD=$(openssl rand -base64 24)
DB_NAME="stockpredict"
DB_USER="stockapi"

# Secure MySQL and create database
mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}';"
mysql -u root -p"${MYSQL_ROOT_PASSWORD}" <<EOF
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'172.17.0.%' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'172.18.0.%' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'172.17.0.%';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'172.18.0.%';
FLUSH PRIVILEGES;
EOF

# Configure MySQL to accept connections from Docker
cat >> /etc/mysql/mysql.conf.d/mysqld.cnf <<EOF

# Allow connections from Docker containers
bind-address = 0.0.0.0
EOF

# Restart MySQL
systemctl restart mysql

echo -e "${GREEN}MySQL configured successfully!${NC}"

# =============================================================================
# Step 5: Setup Application Directory
# =============================================================================
echo -e "\n${YELLOW}[5/6] Setting up application directory...${NC}"

APP_DIR="/opt/stockpredict"
mkdir -p ${APP_DIR}
cd ${APP_DIR}

# If code already exists, skip clone
if [ ! -f "docker-compose.yml" ]; then
    echo "Please clone your repository to ${APP_DIR}"
    echo "Example: git clone https://github.com/your-username/stockpredict-webapi.git ."
fi

# =============================================================================
# Step 6: Create Environment File
# =============================================================================
echo -e "\n${YELLOW}[6/6] Creating environment configuration...${NC}"

# Get server's IP address
SERVER_IP=$(hostname -I | awk '{print $1}')

cat > ${APP_DIR}/.env <<EOF
# =============================================================================
# Stock Predict WebAPI - Production Environment
# Generated on: $(date)
# =============================================================================

# Django Settings
DJANGO_SECRET_KEY=$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9' | head -c 50)
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,${SERVER_IP}

# Database Configuration (MySQL on same server)
DB_ENGINE=django.db.backends.mysql
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=host.docker.internal
DB_PORT=3306
DB_SSL=false

# API Configuration
API_PORT=8000

# CORS (add your frontend domains)
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://${SERVER_IP}:3000

# Logging
LOG_LEVEL=INFO
EOF

chmod 600 ${APP_DIR}/.env

# =============================================================================
# Print Summary
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Server IP: ${YELLOW}${SERVER_IP}${NC}"
echo ""
echo -e "${YELLOW}MySQL Credentials (SAVE THESE!):${NC}"
echo -e "  Root Password: ${RED}${MYSQL_ROOT_PASSWORD}${NC}"
echo -e "  Database: ${DB_NAME}"
echo -e "  Username: ${DB_USER}"
echo -e "  Password: ${RED}${DB_PASSWORD}${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Clone your repository:"
echo "   cd ${APP_DIR}"
echo "   git clone https://github.com/your-username/stockpredict-webapi.git ."
echo ""
echo "2. Build and start the application:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.prod.yml build"
echo "   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d"
echo ""
echo "3. Access the API at:"
echo "   http://${SERVER_IP}:8000/stock/api/"
echo ""
echo -e "${YELLOW}Credentials saved to: ${APP_DIR}/.env${NC}"
echo -e "${RED}IMPORTANT: Save the MySQL passwords above securely!${NC}"

# Save credentials to a file
cat > ${APP_DIR}/credentials.txt <<EOF
# Stock Predict WebAPI - Server Credentials
# Generated: $(date)
# KEEP THIS FILE SECURE!

Server IP: ${SERVER_IP}

MySQL Root Password: ${MYSQL_ROOT_PASSWORD}
Database Name: ${DB_NAME}
Database User: ${DB_USER}
Database Password: ${DB_PASSWORD}

API URL: http://${SERVER_IP}:8000/stock/api/
EOF

chmod 600 ${APP_DIR}/credentials.txt
echo -e "\nCredentials also saved to: ${APP_DIR}/credentials.txt"
