# Ceramic Marketplace API - Deployment & Testing Guide

Complete guide for deploying and testing the Ceramic Marketplace backend API.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Production Deployment](#production-deployment)
4. [API Testing](#api-testing)
5. [Database Management](#database-management)
6. [Troubleshooting](#troubleshooting)
7. [Management Commands](#management-commands)

---

## Prerequisites

### Required Software

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher (or Docker with Compose plugin)
- **Git**: For version control
- **curl**: For API testing

### System Requirements

- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: At least 5GB free space
- **OS**: Linux, macOS, or Windows with WSL2

### Verify Installation

```bash
# Check Docker
docker --version

# Check Docker Compose
docker compose version

# Check if Docker is running
docker info
```

---

## Local Deployment

### Step 1: Clone and Navigate

```bash
cd /path/to/ceramic_mobile_app/back_end
```

### Step 2: Environment Configuration

The `.env` file contains all configuration. Key settings:

```env
ENVIRONMENT=production
DEBUG=false
DB_HOST=db
DB_PORT=3306
DB_NAME=ceramic_marketplace
DB_USER=ceramic_user
DB_PASSWORD=Mysql_2025
API_PORT=8002
```

### Step 3: Deploy Services

```bash
# Build and start all services
docker compose up -d

# View logs during startup
docker compose logs -f
```

### Step 4: Verify Deployment

```bash
# Check container status
docker compose ps

# All containers should show "healthy" status
# Expected output:
# ceramic_api     Up X seconds (healthy)
# ceramic_mysql   Up X seconds (healthy)
# ceramic_nginx   Up X seconds (healthy)
```

### Step 5: Test API Endpoints

```bash
# Test health endpoint
curl http://localhost:8002/health

# Expected: {"status":"healthy","environment":"production"}

# Test API v1 root
curl http://localhost:8002/api/v1

# Expected: {"message":"Ceramic Marketplace API v1","version":"1.0.0","docs":"/api/docs"}
```

### Access Points

- **API Direct Access**: http://localhost:8002
- **API Documentation (Swagger)**: http://localhost:8002/api/docs
- **API Documentation (ReDoc)**: http://localhost:8002/api/redoc
- **Through Nginx**: http://localhost
- **Database**: localhost:3308

---

## Production Deployment

### Prerequisites

- SSH access to production server
- Server IP: `112.213.91.103`
- Docker and Docker Compose installed on server

### Deployment Steps

#### Option 1: Using Git (Recommended)

```bash
# 1. SSH into production server
ssh user@112.213.91.103

# 2. Navigate to backend directory
cd /path/to/ceramic_mobile_app/back_end

# 3. Pull latest changes
git pull origin main

# 4. Rebuild and restart services
docker compose down
docker compose build --no-cache
docker compose up -d

# 5. Verify deployment
curl http://localhost:8002/health
```

#### Option 2: Manual File Transfer

```bash
# 1. From local machine, copy files
scp -r ./* user@112.213.91.103:/path/to/ceramic_mobile_app/back_end/

# 2. SSH into server
ssh user@112.213.91.103

# 3. Navigate and restart
cd /path/to/ceramic_mobile_app/back_end
docker compose down
docker compose up -d --build
```

### Post-Deployment Verification

```bash
# Test from production server
curl http://localhost:8002/api/v1/health

# Test from external network
curl http://112.213.91.103:8002/api/v1/health

# Check logs
docker compose logs -f api
```

---

## API Testing

### Interactive API Documentation

Access Swagger UI for interactive testing:

```
http://localhost:8002/api/docs
```

### Manual Testing with curl

#### Health Check

```bash
curl -X GET http://localhost:8002/health
```

#### API v1 Endpoints

```bash
# API Root
curl -X GET http://localhost:8002/api/v1

# Health Check
curl -X GET http://localhost:8002/api/v1/health
```

#### Authentication

```bash
# User Registration
curl -X POST http://localhost:8002/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User",
    "role": "customer"
  }'

# User Login
curl -X POST http://localhost:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'

# Response includes access_token - use for authenticated requests
```

#### Authenticated Requests

```bash
# Get current user profile
curl -X GET http://localhost:8002/api/v1/users/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Testing with Python

```python
import requests

# Base URL
BASE_URL = "http://localhost:8002/api/v1"

# Test health endpoint
response = requests.get(f"{BASE_URL}/health")
print(response.json())

# Register user
register_data = {
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User",
    "role": "customer"
}
response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
print(response.json())

# Login
login_data = {
    "email": "test@example.com",
    "password": "SecurePass123"
}
response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
token = response.json()["access_token"]

# Get user profile
headers = {"Authorization": f"Bearer {token}"}
response = requests.get(f"{BASE_URL}/users/me", headers=headers)
print(response.json())
```

### Automated Testing

```bash
# Run Python tests (if available)
python test_api.py

# Run specific test categories
python test_api.py --categories "Authentication,Products"
```

---

## Database Management

### Access MySQL Database

```bash
# Access database container
docker compose exec db mysql -u ceramic_user -p
# Password: Mysql_2025

# Or connect from host
mysql -h localhost -P 3308 -u ceramic_user -p ceramic_marketplace
```

### Common Database Operations

```sql
-- Show all tables
SHOW TABLES;

-- Check users table
SELECT * FROM users LIMIT 10;

-- Check products table
SELECT * FROM products LIMIT 10;

-- Count records
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM products;
```

### Database Backup

```bash
# Create backup
docker compose exec db mysqldump -u ceramic_user -p ceramic_marketplace > backup_$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T db mysql -u ceramic_user -p ceramic_marketplace < backup_20231113.sql
```

### Reset Database

```bash
# Stop services
docker compose down

# Remove database volume
docker volume rm back_end_mysql_data

# Start services (database will be recreated)
docker compose up -d
```

---

## Troubleshooting

### Container Not Starting

```bash
# Check container status
docker compose ps

# View logs
docker compose logs api
docker compose logs db
docker compose logs nginx

# Check specific container logs
docker compose logs -f api --tail=100
```

### Common Issues

#### Issue 1: Port Already in Use

```bash
# Find process using port 8002
sudo lsof -i :8002

# Kill the process
sudo kill -9 <PID>

# Or change port in docker-compose.yml
```

#### Issue 2: Database Connection Failed

```bash
# Check if database is healthy
docker compose ps db

# Wait for database initialization
docker compose logs db | grep "ready for connections"

# Test database connection
docker compose exec db mysql -u ceramic_user -p -e "SELECT 1"
```

#### Issue 3: Permission Denied Errors

```bash
# Fix directory permissions
chmod 755 uploads logs backups

# Restart containers
docker compose restart
```

#### Issue 4: API Returns 502 Bad Gateway

```bash
# Check if API container is running
docker compose ps api

# Check API logs for errors
docker compose logs api --tail=50

# Restart API container
docker compose restart api
```

### Health Check Failures

```bash
# Check health endpoint manually
curl http://localhost:8002/health

# If fails, check application logs
docker compose logs api | grep -i error

# Verify database connection
docker compose exec api python -c "from app.database import engine; engine.connect()"
```

---

## Management Commands

### Docker Compose Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose stop

# Restart services
docker compose restart

# Restart specific service
docker compose restart api

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f api

# View last 100 lines
docker compose logs api --tail=100

# Check status
docker compose ps

# Remove all containers and networks
docker compose down

# Remove all containers, networks, and volumes
docker compose down -v
```

### Container Management

```bash
# Execute command in container
docker compose exec api bash

# Execute Python command
docker compose exec api python -c "print('Hello')"

# Copy files to/from container
docker compose cp local_file.txt api:/app/
docker compose cp api:/app/remote_file.txt ./
```

### Image Management

```bash
# Rebuild images
docker compose build

# Rebuild without cache
docker compose build --no-cache

# Rebuild specific service
docker compose build api

# Pull latest base images
docker compose pull
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect back_end_mysql_data

# Remove specific volume
docker volume rm back_end_mysql_data

# Remove all unused volumes
docker volume prune
```

### Network Management

```bash
# List networks
docker network ls

# Inspect network
docker network inspect back_end_ceramic_network

# View container IPs
docker compose exec api hostname -i
```

---

## Environment Variables

### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Environment mode | production |
| `DEBUG` | Enable debug mode | false |
| `SECRET_KEY` | JWT secret key | (change in production) |
| `API_PORT` | API server port | 8002 |

### Database Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | Database host | db |
| `DB_PORT` | Database port | 3306 |
| `DB_NAME` | Database name | ceramic_marketplace |
| `DB_USER` | Database user | ceramic_user |
| `DB_PASSWORD` | Database password | Mysql_2025 |
| `DB_EXTERNAL_PORT` | External MySQL port | 3308 |

### Security Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `ALGORITHM` | JWT algorithm | HS256 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | 30 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration | 30 |

### Email Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_SERVER` | SMTP server | smtp.gmail.com |
| `SMTP_PORT` | SMTP port | 587 |
| `SMTP_USERNAME` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `SMTP_FROM_EMAIL` | From email address | - |
| `SMTP_USE_TLS` | Use TLS | true |

---

## API Endpoints Overview

### Authentication

- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

### Users

- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update current user
- `GET /api/v1/users/{user_id}` - Get user by ID

### Products

- `GET /api/v1/products` - List products
- `GET /api/v1/products/{product_id}` - Get product details
- `POST /api/v1/products` - Create product (seller only)
- `PUT /api/v1/products/{product_id}` - Update product
- `DELETE /api/v1/products/{product_id}` - Delete product

### Orders

- `GET /api/v1/orders` - List user orders
- `GET /api/v1/orders/{order_id}` - Get order details
- `POST /api/v1/orders` - Create order
- `PUT /api/v1/orders/{order_id}` - Update order status

For complete API documentation, visit:
- Swagger UI: http://localhost:8002/api/docs
- ReDoc: http://localhost:8002/api/redoc

---

## Performance Monitoring

### Check Service Health

```bash
# API health
curl http://localhost:8002/health

# Database health
docker compose exec db mysqladmin ping -u ceramic_user -p

# Container resource usage
docker stats
```

### View Metrics

```bash
# Container CPU and memory
docker compose top

# Disk usage
docker system df

# Network statistics
docker network inspect back_end_ceramic_network
```

---

## Security Best Practices

1. **Change Default Passwords**: Update `SECRET_KEY` and database passwords in production
2. **Use HTTPS**: Configure SSL certificates for production deployment
3. **Environment Variables**: Never commit `.env` file with sensitive data
4. **Database Access**: Restrict database port exposure in production
5. **Rate Limiting**: Configure rate limiting for API endpoints
6. **CORS**: Update `ALLOWED_ORIGINS` for production domains
7. **Backups**: Schedule regular database backups

---

## Quick Reference

### Start Everything

```bash
docker compose up -d
```

### Stop Everything

```bash
docker compose down
```

### View Logs

```bash
docker compose logs -f api
```

### Restart API

```bash
docker compose restart api
```

### Access Database

```bash
docker compose exec db mysql -u ceramic_user -p
```

### Test API

```bash
curl http://localhost:8002/api/v1/health
```

### Access API Documentation

Open in browser: http://localhost:8002/api/docs

---

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Review troubleshooting section above
3. Check API documentation: http://localhost:8002/api/docs
4. Verify environment configuration in `.env` file

---

**Version**: 1.0.0
**Last Updated**: November 2025
