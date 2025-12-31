# Stock Predict WebAPI - Remote Server Deployment Guide

Complete guide for deploying Stock Predict WebAPI on a remote server with MySQL installed on the same machine.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Remote Server                         │
│                  (Static IP: x.x.x.x)                   │
│                                                         │
│  ┌─────────────────────┐    ┌─────────────────────┐    │
│  │   Docker Container  │    │    MySQL Server     │    │
│  │                     │    │                     │    │
│  │  ┌───────────────┐  │    │  ┌───────────────┐  │    │
│  │  │ Django API    │──┼────┼─▶│ stockpredict  │  │    │
│  │  │ Port: 8000    │  │    │  │   database    │  │    │
│  │  └───────────────┘  │    │  └───────────────┘  │    │
│  │                     │    │                     │    │
│  └─────────────────────┘    └─────────────────────┘    │
│            │                                            │
│            ▼                                            │
│       Port 8000 ◀──── Internet ◀──── Your Frontend     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- Ubuntu 20.04/22.04 LTS or Debian 11+ server
- Static IP address
- SSH access with sudo privileges
- At least 4GB RAM, 2 CPU cores, 20GB storage

---

## Option 1: Automated Setup (Recommended)

### Step 1: Connect to Your Server

```bash
ssh user@your-server-ip
```

### Step 2: Clone Repository

```bash
sudo mkdir -p /opt/stockpredict
cd /opt/stockpredict
sudo git clone https://github.com/your-username/stockpredict-webapi.git .
sudo chown -R $USER:$USER /opt/stockpredict
```

### Step 3: Run Setup Script

```bash
sudo bash scripts/setup-server.sh
```

This script will:
- Install Docker & Docker Compose
- Install and configure MySQL Server
- Create database and user
- Generate secure passwords
- Create `.env` file with all configurations

### Step 4: Build and Start

```bash
cd /opt/stockpredict
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Step 5: Verify

```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f stockapi

# Test API
curl http://localhost:8000/stock/api/
```

---

## Option 2: Manual Setup

### Step 1: Install Docker

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install prerequisites
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (optional, avoids using sudo)
sudo usermod -aG docker $USER
```

### Step 2: Install MySQL Server

```bash
# Install MySQL
sudo apt-get install -y mysql-server

# Start MySQL
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation (follow prompts)
sudo mysql_secure_installation
```

### Step 3: Configure MySQL

```bash
# Login to MySQL
sudo mysql -u root -p

# Run these SQL commands:
```

```sql
-- Create database
CREATE DATABASE stockpredict CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user with access from Docker networks
CREATE USER 'stockapi'@'localhost' IDENTIFIED BY 'your_secure_password';
CREATE USER 'stockapi'@'172.17.0.%' IDENTIFIED BY 'your_secure_password';
CREATE USER 'stockapi'@'172.18.0.%' IDENTIFIED BY 'your_secure_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON stockpredict.* TO 'stockapi'@'localhost';
GRANT ALL PRIVILEGES ON stockpredict.* TO 'stockapi'@'172.17.0.%';
GRANT ALL PRIVILEGES ON stockpredict.* TO 'stockapi'@'172.18.0.%';

FLUSH PRIVILEGES;
EXIT;
```

### Step 4: Configure MySQL to Accept Docker Connections

```bash
# Edit MySQL config
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

# Change bind-address to:
bind-address = 0.0.0.0

# Restart MySQL
sudo systemctl restart mysql
```

### Step 5: Clone and Configure Application

```bash
# Create app directory
sudo mkdir -p /opt/stockpredict
cd /opt/stockpredict

# Clone repository
sudo git clone https://github.com/your-username/stockpredict-webapi.git .
sudo chown -R $USER:$USER /opt/stockpredict

# Create environment file
cp .env.production .env
nano .env
```

### Step 6: Edit Environment File

```bash
nano .env
```

Update these values:

```env
# Your server's static IP
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,YOUR_SERVER_IP

# MySQL credentials (from Step 3)
DB_NAME=stockpredict
DB_USER=stockapi
DB_PASSWORD=your_secure_password
DB_HOST=host.docker.internal
DB_PORT=3306
DB_SSL=false

# Generate secret key
DJANGO_SECRET_KEY=run-this-command-to-generate-one
```

Generate Django secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

### Step 7: Build and Run

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Firewall Configuration

### Using UFW (Ubuntu)

```bash
# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow API port
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable
```

### Using iptables

```bash
# Allow SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow API
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT

# Allow HTTP/HTTPS
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

---

## Setting Up Nginx Reverse Proxy (Recommended)

### Install Nginx

```bash
sudo apt-get install -y nginx
```

### Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/stockpredict
```

```nginx
server {
    listen 80;
    server_name your-domain.com YOUR_SERVER_IP;

    # Max upload size
    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/stockpredict/static/;
    }

    # Media files
    location /media/ {
        alias /opt/stockpredict/media/;
    }
}
```

### Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/stockpredict /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
sudo systemctl status certbot.timer
```

---

## Management Commands

### Start/Stop Services

```bash
# Start
cd /opt/stockpredict
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop
docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

# Restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml restart

# View logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

### Database Management

```bash
# Backup database
mysqldump -u stockapi -p stockpredict > backup_$(date +%Y%m%d).sql

# Restore database
mysql -u stockapi -p stockpredict < backup_20231215.sql

# Access MySQL shell
mysql -u stockapi -p stockpredict
```

### Django Management

```bash
# Run migrations
docker-compose exec stockapi python manage.py migrate

# Create admin user
docker-compose exec stockapi python manage.py createsuperuser

# Collect static files
docker-compose exec stockapi python manage.py collectstatic --noinput
```

### Update Application

```bash
cd /opt/stockpredict

# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Monitoring

### Check Container Health

```bash
docker-compose ps
docker stats stockpredict-api
```

### Check MySQL Status

```bash
sudo systemctl status mysql
sudo mysqladmin -u root -p status
```

### Check Logs

```bash
# API logs
docker-compose logs -f --tail=100 stockapi

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# MySQL logs
sudo tail -f /var/log/mysql/error.log
```

---

## Troubleshooting

### Container Can't Connect to MySQL

1. Check MySQL is running:
   ```bash
   sudo systemctl status mysql
   ```

2. Check MySQL accepts connections from Docker:
   ```bash
   sudo netstat -tlnp | grep 3306
   ```
   Should show `0.0.0.0:3306`

3. Check MySQL user permissions:
   ```sql
   SELECT user, host FROM mysql.user WHERE user='stockapi';
   ```

4. Test connection from container:
   ```bash
   docker-compose exec stockapi python -c "
   import pymysql
   conn = pymysql.connect(host='host.docker.internal', user='stockapi', password='your_password', database='stockpredict')
   print('Connected!')
   conn.close()
   "
   ```

### API Returns 500 Error

1. Check logs:
   ```bash
   docker-compose logs stockapi
   ```

2. Check Django debug output:
   ```bash
   docker-compose exec stockapi python manage.py check
   ```

### Port 8000 Already in Use

```bash
# Find process
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>

# Or change port in .env
API_PORT=8001
```

---

## Security Best Practices

1. **Use strong passwords** - Generated by the setup script
2. **Enable firewall** - Only open necessary ports
3. **Use SSL/HTTPS** - Set up Let's Encrypt
4. **Regular backups** - Automate database backups
5. **Keep updated** - Regularly update Docker images and system packages
6. **Monitor logs** - Set up log monitoring and alerts

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |
| Stop | `docker-compose -f docker-compose.yml -f docker-compose.prod.yml down` |
| Logs | `docker-compose logs -f stockapi` |
| Restart | `docker-compose restart` |
| Update | `git pull && docker-compose build && docker-compose up -d` |
| Shell | `docker-compose exec stockapi bash` |
| Migrate | `docker-compose exec stockapi python manage.py migrate` |
