# Mathematics Solver Backend - Docker Guide

This guide provides comprehensive instructions for building, running, and managing the Mathematics Solver backend application using Docker.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Docker Configuration Files](#docker-configuration-files)
4. [Building the Application](#building-the-application)
5. [Running with Docker Compose](#running-with-docker-compose)
6. [Environment Configuration](#environment-configuration)
7. [Database Setup](#database-setup)
8. [Development Workflow](#development-workflow)
9. [Production Deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)
11. [Useful Commands](#useful-commands)

## Prerequisites

### System Requirements
- **Docker**: Version 20.10 or later
- **Docker Compose**: Version 2.0 or later
- **Git**: For cloning the repository
- **Minimum System Resources**:
  - RAM: 4GB minimum, 8GB recommended
  - Disk Space: 10GB free space
  - CPU: Multi-core processor recommended

### Installation Instructions

#### Windows
1. Install [Docker Desktop for Windows](https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe)
2. Enable WSL 2 backend if using Windows 10/11
3. Restart your computer after installation

#### macOS
1. Install [Docker Desktop for Mac](https://desktop.docker.com/mac/main/amd64/Docker.dmg)
2. Drag Docker to Applications folder
3. Launch Docker from Applications

#### Linux (Ubuntu/Debian)
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/mathematic-mobile.git
cd mathematic-mobile/backend
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit environment variables (optional)
nano .env
```

### 3. Build and Run
```bash
# Start all services
docker-compose up --build

# Run in background (detached mode)
docker-compose up -d --build
```

### 4. Verify Installation
- **API Health Check**: http://localhost:8001/health
- **Swagger Documentation**: http://localhost:8001/swagger
- **API Base URL**: http://localhost:8001/api

## Docker Configuration Files

### Dockerfile
Multi-stage build configuration:
- **Base Stage**: ASP.NET Core 8.0 runtime
- **Build Stage**: .NET SDK 8.0 for compilation
- **Publish Stage**: Application publishing
- **Final Stage**: Optimized runtime image

### Docker Compose Files

| File | Purpose | Environment |
|------|---------|------------|
| `docker-compose.yml` | Main configuration | Development/Production |
| `docker-compose.override.yml` | Development overrides | Development |
| `docker-compose.prod.yml` | Production settings | Production |

### Services Architecture

```
┌─────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│                     │    │                  │    │                 │
│ mathematics-solver- │────│   SQL Server     │    │     Redis       │
│      api            │    │   Database       │    │     Cache       │
│   (Port: 8001)      │    │ (Port: 1433)     │    │ (Port: 6379)    │
│                     │    │                  │    │   (Optional)    │
└─────────────────────┘    └──────────────────┘    └─────────────────┘
```

## Building the Application

### Build Docker Image
```bash
# Build the API image
docker build -t mathematics-solver-api .

# Build with custom tag
docker build -t mathematics-solver-api:v1.0 .

# Build for production
docker build -t mathematics-solver-api:prod --target runtime .
```

### Build Arguments (Optional)
```bash
# Build with different .NET version
docker build --build-arg DOTNET_VERSION=8.0 -t mathematics-solver-api .

# Build with configuration
docker build --build-arg CONFIGURATION=Release -t mathematics-solver-api .
```

## Running with Docker Compose

### Development Environment
```bash
# Start all services
docker-compose up

# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Environment
```bash
# Use production configuration
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With environment file
docker-compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Service Management
```bash
# Start specific service
docker-compose up mathematics-solver-api

# Restart service
docker-compose restart mathematics-solver-api

# View service logs
docker-compose logs mathematics-solver-api

# Scale service (production)
docker-compose up -d --scale mathematics-solver-api=3
```

## Environment Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ASPNETCORE_ENVIRONMENT` | Application environment | Development | Yes |
| `ASPNETCORE_URLS` | URLs to bind | http://+:8001 | Yes |
| `ConnectionStrings__DefaultConnection` | Database connection | See docker-compose.yml | Yes |
| `DB_PASSWORD` | Database password | YourStrong@Passw0rd | Yes |
| `ALLOWED_ORIGINS` | CORS origins | localhost:3000,8081 | No |
| `MAX_FILE_SIZE` | Max upload size | 10485760 | No |
| `PROCESSING_TIMEOUT` | Processing timeout | 30 | No |

### Environment Files
```bash
# Development
.env                    # Local development settings
.env.example           # Template file

# Production
.env.prod             # Production settings
.env.staging          # Staging settings
```

### Creating Environment File
```bash
# Copy template
cp .env.example .env

# Edit configuration
cat > .env << EOF
DB_PASSWORD=YourNewSecurePassword123!
API_PORT=8001
ASPNETCORE_ENVIRONMENT=Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8081
EOF
```

## Database Setup

### Automatic Setup
The SQL Server container automatically:
1. Creates the database instance
2. Runs initialization scripts from `/scripts/init-db.sql`
3. Sets up development and production databases

### Manual Database Operations
```bash
# Connect to SQL Server container
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd

# Run SQL script
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -i /scripts/init-db.sql

# Backup database
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "BACKUP DATABASE MathematicsSolverDb TO DISK = '/var/opt/mssql/backup/MathematicsSolverDb.bak'"

# Restore database
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "RESTORE DATABASE MathematicsSolverDb FROM DISK = '/var/opt/mssql/backup/MathematicsSolverDb.bak'"
```

### Entity Framework Migrations
```bash
# Generate migration (if using EF Core)
docker-compose exec mathematics-solver-api dotnet ef migrations add InitialCreate

# Update database
docker-compose exec mathematics-solver-api dotnet ef database update
```

## Development Workflow

### Local Development Setup
```bash
# 1. Clone repository
git clone https://github.com/your-username/mathematic-mobile.git
cd mathematic-mobile/backend

# 2. Setup environment
cp .env.example .env

# 3. Start development environment
docker-compose up -d

# 4. View logs
docker-compose logs -f mathematics-solver-api
```

### Development with Volume Mounting
```bash
# Mount source code for live reload (add to docker-compose.override.yml)
volumes:
  - ./src:/app/src:ro
  - ./appsettings.Development.json:/app/appsettings.Development.json:ro
```

### Debugging
```bash
# Start with debug port exposed
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up

# Attach debugger to port 5000
# Configure your IDE to connect to localhost:5000
```

### Testing
```bash
# Run unit tests
docker-compose exec mathematics-solver-api dotnet test

# Run with coverage
docker-compose exec mathematics-solver-api dotnet test --collect:"XPlat Code Coverage"

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Production Deployment

### Pre-deployment Checklist
- [ ] Update environment variables in `.env.prod`
- [ ] Configure secure database passwords
- [ ] Set up SSL/TLS certificates
- [ ] Configure logging and monitoring
- [ ] Set up backup strategies
- [ ] Review security settings

### Production Deployment
```bash
# 1. Prepare environment
cp .env.example .env.prod
# Edit .env.prod with production values

# 2. Deploy with production settings
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Verify deployment
curl -f http://localhost:8001/health

# 4. Monitor logs
docker-compose logs -f
```

### Docker Swarm Deployment
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml mathematics-solver

# List services
docker service ls

# Scale service
docker service scale mathematics-solver_mathematics-solver-api=3
```

### Health Checks and Monitoring
```bash
# Check container health
docker-compose ps

# View health check logs
docker inspect mathematics-solver-api | grep -A 20 Health

# Monitor resource usage
docker stats
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
netstat -tulpn | grep :8001

# Kill process using port
sudo kill -9 $(sudo lsof -t -i:8001)

# Use different port in docker-compose.yml
ports:
  - "8002:8001"
```

#### 2. Database Connection Issues
```bash
# Check SQL Server container
docker-compose logs sqlserver

# Test database connection
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "SELECT 1"

# Restart database
docker-compose restart sqlserver
```

#### 3. Build Errors
```bash
# Clear Docker cache
docker system prune -f

# Rebuild without cache
docker-compose build --no-cache

# Check build logs
docker-compose up --build
```

#### 4. Permission Issues (Linux)
```bash
# Fix permissions
sudo chown -R $USER:$USER .

# Check Docker permissions
sudo chmod 666 /var/run/docker.sock
```

#### 5. Memory Issues
```bash
# Check memory usage
docker stats

# Increase Docker memory limit (Docker Desktop)
# Settings > Resources > Advanced > Memory

# Clean up unused containers
docker container prune
```

### Logs and Debugging
```bash
# View application logs
docker-compose logs mathematics-solver-api

# Follow logs in real-time
docker-compose logs -f --tail=100 mathematics-solver-api

# View all service logs
docker-compose logs

# Access container shell
docker-compose exec mathematics-solver-api bash

# Check container processes
docker-compose exec mathematics-solver-api ps aux
```

### Performance Optimization
```bash
# Monitor performance
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Optimize images
docker image ls
docker image prune

# Limit resources in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 512M
    reservations:
      memory: 256M
```

## Useful Commands

### Docker Management
```bash
# View running containers
docker ps

# View all containers
docker ps -a

# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# System cleanup
docker system prune -f

# View Docker disk usage
docker system df
```

### Docker Compose Commands
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart <service-name>

# View service status
docker-compose ps

# Execute command in container
docker-compose exec <service-name> <command>

# View logs
docker-compose logs -f <service-name>

# Pull latest images
docker-compose pull

# Rebuild and start
docker-compose up --build --force-recreate
```

### Application Commands
```bash
# Health check
curl http://localhost:8001/health

# API documentation
curl http://localhost:8001/swagger

# Test API endpoint
curl -X GET http://localhost:8001/api/health

# Check application version
curl http://localhost:8001/health | jq '.Version'
```

### Database Commands
```bash
# Connect to SQL Server
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd

# List databases
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "SELECT name FROM sys.databases"

# Backup database
docker-compose exec sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong@Passw0rd -Q "BACKUP DATABASE MathematicsSolverDb TO DISK = '/tmp/backup.bak'"
```

## Security Best Practices

### Container Security
- Use non-root user in containers ✅
- Scan images for vulnerabilities
- Keep base images updated
- Use specific image tags (avoid `latest`)
- Limit container capabilities

### Network Security
- Use Docker networks for service isolation ✅
- Don't expose unnecessary ports
- Configure firewall rules
- Use reverse proxy for production

### Data Security
- Use environment variables for secrets ✅
- Encrypt sensitive data at rest
- Use Docker secrets in swarm mode
- Regular database backups ✅

### Example Security Commands
```bash
# Scan image for vulnerabilities
docker scan mathematics-solver-api

# Use Docker secrets (Swarm mode)
echo "MySecretPassword" | docker secret create db_password -

# Run security scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image mathematics-solver-api
```

## Additional Resources

### Documentation
- [.NET Docker Guide](https://docs.microsoft.com/en-us/dotnet/core/docker/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [ASP.NET Core in Docker](https://docs.microsoft.com/en-us/aspnet/core/host-and-deploy/docker/)

### Tools
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Portainer](https://www.portainer.io/) - Docker GUI management
- [ctop](https://github.com/bcicen/ctop) - Container monitoring

### Support
- Create issues on GitHub repository
- Check Docker Hub for image updates
- Monitor application logs for errors

---

## Quick Reference Card

```bash
# Essential Commands
docker-compose up -d --build    # Build and start all services
docker-compose down             # Stop and remove containers
docker-compose logs -f          # Follow logs
docker-compose ps               # View service status
curl http://localhost:8001/health  # Health check

# Development
docker-compose up               # Start with logs
docker-compose restart api     # Restart API service
docker-compose exec api bash   # Access container shell

# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker service ls               # List swarm services
docker stack deploy            # Deploy to swarm
```

This guide should help you get started with Docker for the Mathematics Solver backend. For specific issues or questions, please refer to the troubleshooting section or create an issue in the project repository.