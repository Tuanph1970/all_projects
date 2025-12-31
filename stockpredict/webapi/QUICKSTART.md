# Stock Predict WebAPI - Quick Start Guide

This guide will help you quickly set up and run the Stock Predict Django API using Docker.

> **Deploying to a Remote Server?** See [DEPLOYMENT.md](DEPLOYMENT.md) for complete production deployment guide with MySQL on the same server.

## Prerequisites

Before you begin, make sure you have the following installed:

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Git**
- **MySQL Server** (external, managed separately)

### Check Docker Installation

```bash
docker --version
docker-compose --version
```

## Quick Installation (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/stockpredict-webapi.git
cd stockpredict-webapi
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your settings
nano .env  # or use any text editor
```

**Required settings to change:**

```env
# Database Configuration (your MySQL server)
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your-mysql-server.com
DB_PORT=3306

# Django Security (generate a new secret key for production)
DJANGO_SECRET_KEY=your-secure-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
```

### Step 3: Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the container
docker-compose up -d
```

### Step 4: Verify Installation

```bash
# Check if the container is running
docker-compose ps

# Check the logs
docker-compose logs -f stockapi

# Test the API endpoint
curl http://localhost:8000/stock/api/
```

You should see a JSON response indicating the API is running.

---

## Detailed Configuration

### Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key for security | (insecure default) |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1` |
| `DB_ENGINE` | Database engine | `django.db.backends.mysql` |
| `DB_NAME` | Database name | `defaultdb` |
| `DB_USER` | Database username | - |
| `DB_PASSWORD` | Database password | - |
| `DB_HOST` | Database host | - |
| `DB_PORT` | Database port | `3306` |
| `DB_SSL` | Enable SSL for database | `true` |
| `API_PORT` | Port to expose API | `8000` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | `http://localhost:3000` |

### Generate a Secure Secret Key

```bash
# Using Python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Or using OpenSSL
openssl rand -base64 50
```

---

## Common Operations

### Start/Stop the Container

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart
```

### View Logs

```bash
# Follow logs in real-time
docker-compose logs -f stockapi

# View last 100 lines
docker-compose logs --tail=100 stockapi
```

### Access Container Shell

```bash
docker-compose exec stockapi bash
```

### Run Django Management Commands

```bash
# Run migrations
docker-compose exec stockapi python manage.py migrate

# Create superuser
docker-compose exec stockapi python manage.py createsuperuser

# Collect static files
docker-compose exec stockapi python manage.py collectstatic
```

### Update the Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose build
docker-compose up -d
```

---

## GPU Support (Optional)

If you have an NVIDIA GPU and want to use GPU acceleration for ML models:

### Prerequisites for GPU

1. NVIDIA GPU with CUDA support
2. NVIDIA Driver installed
3. NVIDIA Container Toolkit installed

### Install NVIDIA Container Toolkit

```bash
# Ubuntu/Debian
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

### Run with GPU Support

```bash
docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker-compose logs stockapi

# Verify .env file exists and is configured
cat .env

# Check Docker status
docker info
```

### Database Connection Issues

1. Verify MySQL server is running and accessible
2. Check firewall rules allow connections from Docker
3. Verify credentials in `.env` file
4. Test connection manually:

```bash
docker-compose exec stockapi python -c "
import pymysql
conn = pymysql.connect(
    host='your-host',
    user='your-user',
    password='your-password',
    database='your-db'
)
print('Connection successful!')
conn.close()
"
```

### Port Already in Use

```bash
# Change the port in .env file
API_PORT=8001

# Or find and stop the process using port 8000
sudo lsof -i :8000
```

### Out of Memory

Adjust memory limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G  # Reduce from 8G
```

### Permission Denied Errors

```bash
# Fix volume permissions
sudo chown -R 1000:1000 ./media ./logs
```

---

## Production Deployment

### Security Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Generate a new `DJANGO_SECRET_KEY`
- [ ] Configure `DJANGO_ALLOWED_HOSTS` with your domain
- [ ] Use HTTPS (configure reverse proxy like Nginx)
- [ ] Set strong database credentials
- [ ] Enable database SSL (`DB_SSL=true`)
- [ ] Configure firewall rules

### Using with Nginx (Reverse Proxy)

Example Nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Using with SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com
```

---

## API Endpoints

Once running, access the API at:

- **Base URL**: `http://localhost:8000/stock/api/`
- **Admin Panel**: `http://localhost:8000/admin/` (after creating superuser)

### Example API Calls

```bash
# Get stock list
curl http://localhost:8000/stock/api/stocks/

# Get stock data
curl http://localhost:8000/stock/api/stock-data/?symbol=VNM

# Get predictions
curl http://localhost:8000/stock/api/predict/?symbol=VNM
```

---

## Support

If you encounter any issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker-compose logs stockapi`
3. Open an issue on GitHub

---

## License

This project is licensed under the MIT License.
