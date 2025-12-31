# Multi-Project Deployment Guide

This guide provides comprehensive instructions for deploying three backend API projects on the same server without port conflicts.

## Project Overview

1. **Ceramic Mobile App Backend**
   - API Port: 8002
   - Database Port: 3308 (MySQL)
   - Redis Port: 6379
   - Technologies: Python/FastAPI, MySQL, Redis

2. **Stock Predict Backend**
   - API Port: 8080
   - Database Port: 3309 (MySQL)
   - Technologies: Python/Django, MySQL

3. **Mathematics Mobile Backend**
   - API Port: 8003
   - Database Port: 3310 (MySQL)
   - Redis Port: 6380
   - Technologies: C#/.NET, MySQL, Redis
   - Note: Includes transitional microservices support

## Quick Start

### Method 1: Interactive Deployment (Recommended)

```bash
# Make scripts executable
chmod +x deploy-interactive.sh
chmod +x stop-interactive.sh

# Run interactive deployment
./deploy-interactive.sh

# Stop services interactively
./stop-interactive.sh
```

The interactive script will:
- Ask you which projects to deploy (Yes/No for each)
- Ask if you want to build images
- Show current status of all services
- Deploy only selected projects

### Method 2: Command Line Deployment

```bash
# Make the deployment script executable
chmod +x deploy-projects.sh

# Start all projects
./deploy-projects.sh start all

# Start specific projects
./deploy-projects.sh start ceramic stock

# Check status
./deploy-projects.sh status

# View logs for a specific project
./deploy-projects.sh logs ceramic
```

## Port Allocation Summary

### API Services
| Service | Port | URL |
|---------|------|-----|
| Ceramic API | 8002 | http://localhost:8002 |
| Stock API | 8080 | http://localhost:8080 |
| Math API | 8003 | http://localhost:8003 |

### Database Services
| Service | Port | Credentials |
|---------|------|-------------|
| Ceramic MySQL | 3308 | ceramic_user / Mysql_2025 |
| Stock MySQL | 3309 | stock_user / Mysql_2025 |
| Math MySQL | 3310 | mathematic_user / Mysql_2025 |

### Cache Services
| Service | Port |
|---------|------|
| Ceramic Redis | 6379 |
| Math Redis | 6380 |

### Additional Services (Mathematics)
| Service | Port | Notes |
|---------|------|-------|
| RabbitMQ | 5673 | Management UI: 15673 |
| Traefik Dashboard | 8083 | For future microservices |

## Deployment Options

### 1. Deploy Individual Projects

```bash
# Deploy only Ceramic
./deploy-projects.sh start ceramic

# Deploy only Stock Predict
./deploy-projects.sh start stock

# Deploy only Mathematics
./deploy-projects.sh start math
```

### 2. Deploy Multiple Projects

```bash
# Deploy Ceramic and Stock
./deploy-projects.sh start ceramic stock

# Deploy Stock and Math
./deploy-projects.sh start stock math
```

### 3. Build and Deploy

```bash
# Build and start all projects
./deploy-projects.sh start all --build

# Build without cache
./deploy-projects.sh start all --build --no-cache
```

## Environment Configuration

The deployment script automatically creates a `.deploy-env` file with default configurations. You can edit this file to customize:

```bash
# Edit environment variables
nano .deploy-env
```

Key variables include:
- `MYSQL_ROOT_PASSWORD`: Root password for all MySQL instances
- `*_API_PORT`: API ports for each service
- `*_DB_PORT`: Database ports for each service
- `*_DB_NAME`: Database names
- `*_DB_USER`: Database users
- `*_DB_PASSWORD`: Database passwords

## Nginx Configuration

For production deployment with a single entry point, use the provided nginx configuration:

```bash
# Copy nginx configuration
sudo cp nginx-unified-projects.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/nginx-unified-projects.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

This will expose all services under a single domain:
- `/ceramic/*` → Ceramic API
- `/stock/*` → Stock API  
- `/math/*` → Mathematics API

## Database Management

### Creating Users

All MySQL instances are pre-configured with the required users:
- `root` (password: Mysql_2025)
- `ceramic_user` (password: Mysql_2025)
- `stock_user` (password: Mysql_2025)
- `mathematic_user` (password: Mysql_2025)

### Accessing Databases

```bash
# Access Ceramic database
mysql -h 127.0.0.1 -P 3308 -u ceramic_user -pMysql_2025 ceramic_db

# Access Stock database
mysql -h 127.0.0.1 -P 3309 -u stock_user -pMysql_2025 stockpredict_db

# Access Math database
mysql -h 127.0.0.1 -P 3310 -u mathematic_user -pMysql_2025 mathematic_db
```

## Monitoring and Management

### View Container Status

```bash
# All projects status
./deploy-projects.sh status

# Docker native command
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### View Logs

```bash
# Ceramic logs
./deploy-projects.sh logs ceramic

# Stock logs
./deploy-projects.sh logs stock

# Math logs
./deploy-projects.sh logs math
```

### Access Service UIs

- **RabbitMQ Management**: http://localhost:15673 (admin/admin123)
- **Traefik Dashboard**: http://localhost:8083
- **Swagger/API Docs**:
  - Ceramic: http://localhost:8002/docs
  - Stock: http://localhost:8080/stock/api/
  - Math: http://localhost:8003/swagger

## Troubleshooting

### Port Conflicts

If you encounter port conflicts:

1. Check what's using the port:
   ```bash
   sudo lsof -i :PORT_NUMBER
   ```

2. Stop conflicting services or modify port in `.deploy-env`

### Database Connection Issues

1. Ensure MySQL containers are healthy:
   ```bash
   docker ps | grep mysql
   ```

2. Check logs:
   ```bash
   docker logs ceramic_mysql
   docker logs stock_mysql
   docker logs math_mysql
   ```

### Service Dependencies

If services fail to start due to dependencies:

1. Start infrastructure first:
   ```bash
   # Start databases and cache services
   docker-compose up -d mysql redis rabbitmq
   ```

2. Wait for health checks:
   ```bash
   # Check health status
   docker ps --format "table {{.Names}}\t{{.Health}}"
   ```

3. Start application services

## Production Deployment

For production deployment on a static IP server:

1. **Update Environment**
   ```bash
   # Edit .deploy-env
   ENVIRONMENT=production
   ```

2. **Configure Domain/IP**
   - Update nginx configuration with your domain/IP
   - Configure SSL certificates

3. **Security Hardening**
   - Change default passwords in `.deploy-env`
   - Configure firewall rules
   - Enable SSL/TLS

4. **Backup Strategy**
   ```bash
   # Backup databases
   docker exec ceramic_mysql mysqldump -u root -pMysql_2025 ceramic_db > ceramic_backup.sql
   docker exec stock_mysql mysqldump -u root -pMysql_2025 stockpredict_db > stock_backup.sql
   docker exec math_mysql mysqldump -u root -pMysql_2025 mathematic_db > math_backup.sql
   ```

## Maintenance

### Stop All Services

```bash
# Interactive stop
./stop-interactive.sh

# Or command line
./deploy-projects.sh stop all
```

### Restart Services

```bash
./deploy-projects.sh restart all
```

### Update Services

```bash
# Pull latest changes
git pull

# Rebuild and restart
./deploy-projects.sh restart all --build
```

### Clean Up and Redeploy

#### Option 1: Quick Reset (Preserves Data)
```bash
# Reset and redeploy interactively
./reset-and-deploy.sh
```

#### Option 2: Manual Cleanup
```bash
# Clean all containers and networks (preserves data)
./cleanup-all.sh

# Clean everything including data volumes (WARNING: Deletes all data!)
./cleanup-all.sh --volumes

# Skip confirmation prompts
./cleanup-all.sh --force
./cleanup-all.sh --volumes --force
```

#### Option 3: Complete Fresh Start
```bash
# 1. Stop everything
./deploy-projects.sh stop all

# 2. Clean all resources including data
./cleanup-all.sh --volumes

# 3. Redeploy with fresh builds
./deploy-interactive.sh  # Choose which projects and select "Yes" to build
# OR
./deploy-projects.sh start all --build
```

## Advanced Usage

### Mathematics Mobile Microservices

The Mathematics project includes a transitional architecture supporting future microservices:

```bash
# Use transitional architecture
cd mathematic-mobile/backend
docker-compose -f docker-compose.transition.yml up -d

# Or use full microservices (future)
docker-compose -f docker-compose.microservices.yml up -d
```

### Custom Docker Networks

Each project runs in its own network:
- Ceramic: 172.20.0.0/16
- Stock: 172.21.0.0/16
- Mathematics: 172.22.0.0/16

## Support

For issues or questions:
1. Check logs: `./deploy-projects.sh logs [project]`
2. Verify configuration: `cat .deploy-env`
3. Check container health: `docker ps`
4. Review this documentation

## License

Each project maintains its own license. Please refer to individual project directories for specific licensing information.