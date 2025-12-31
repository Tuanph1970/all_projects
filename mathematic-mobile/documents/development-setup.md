# Development Setup Guide

## Overview

This guide provides step-by-step instructions for setting up the Homework Solver development environment on both local machines and development containers. The system consists of two main services: .NET Core Web API and Python ML Service.

## System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, macOS 10.15+, or Ubuntu 20.04+
- **RAM**: 16GB (32GB recommended for ML development)
- **Storage**: 50GB free space
- **GPU**: NVIDIA GPU with CUDA support (recommended for ML service)

### Required Software
- **Docker**: 20.10+ with Docker Compose
- **Git**: 2.30+
- **.NET SDK**: 8.0+
- **Python**: 3.11+
- **Node.js**: 18+ (for tooling)
- **Visual Studio Code** or **Visual Studio 2022**

## Quick Start (Docker)

### 1. Clone Repository

```bash
git clone https://github.com/your-org/homework-solver.git
cd homework-solver
```

### 2. Environment Configuration

```bash
# Copy environment templates
cp .env.example .env
cp homework-solver-ml/.env.example homework-solver-ml/.env

# Edit environment files with your settings
nano .env
```

### 3. Docker Development

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Or start specific services
docker-compose -f docker-compose.dev.yml up mysql redis rabbitmq
docker-compose -f docker-compose.dev.yml up api ml-service
```

### 4. Verify Setup

```bash
# Check API health
curl http://localhost:5000/health

# Check ML service health
curl http://localhost:8000/health

# Access services
# API: http://localhost:5000
# ML Service: http://localhost:8000
# RabbitMQ Management: http://localhost:15672 (admin/admin123)
```

## Local Development Setup

### .NET Core API Service Setup

#### 1. Install Prerequisites

```bash
# Install .NET 8 SDK (Windows/macOS/Linux)
# Download from: https://dotnet.microsoft.com/download/dotnet/8.0

# Verify installation
dotnet --version
```

#### 2. Database Setup

```bash
# Install MySQL 8.0+
# Windows: Download from mysql.com/downloads
# macOS: brew install mysql
# Ubuntu: sudo apt install mysql-server-8.0

# Create database
sudo mysql
mysql> CREATE DATABASE homework_solver;
mysql> CREATE USER 'homework_user'@'localhost' IDENTIFIED BY 'secure_password';
mysql> GRANT ALL PRIVILEGES ON homework_solver.* TO 'homework_user'@'localhost';
mysql> FLUSH PRIVILEGES;
mysql> exit;
```

#### 3. Project Setup

```bash
# Navigate to API project
cd HomeworkSolver.API

# Restore packages
dotnet restore

# Update database connection string
nano appsettings.Development.json
```

**appsettings.Development.json:**
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Server=localhost;Database=homework_solver;Uid=homework_user;Pwd=secure_password;",
    "Redis": "localhost:6379",
    "RabbitMQ": "amqp://admin:admin123@localhost:5672"
  },
  "MLService": {
    "BaseUrl": "http://localhost:8000"
  },
  "Jwt": {
    "SecretKey": "your-development-secret-key-make-it-very-long-and-secure",
    "Issuer": "HomeworkSolver",
    "Audience": "HomeworkSolverApp",
    "ExpiryMinutes": 1440
  },
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  }
}
```

#### 4. Database Migration

```bash
# Install EF Core tools
dotnet tool install --global dotnet-ef

# Create initial migration
dotnet ef migrations add InitialCreate

# Update database
dotnet ef database update
```

#### 5. Run API Service

```bash
# Run in development mode
dotnet run

# Or with hot reload
dotnet watch run

# API will be available at: https://localhost:5001 or http://localhost:5000
```

### Python ML Service Setup

#### 1. Install Python 3.11

```bash
# Windows: Download from python.org
# macOS: brew install python@3.11
# Ubuntu: 
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv
```

#### 2. Setup Virtual Environment

```bash
# Navigate to ML service directory
cd homework-solver-ml

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### 3. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-eng libgl1-mesa-glx libglib2.0-0

# macOS
brew install tesseract

# Windows: Download Tesseract from github.com/UB-Mannheim/tesseract/wiki
```

#### 4. Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# Install PyTorch with CUDA (if GPU available)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Or CPU-only version
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### 5. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**.env file:**
```env
# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# RabbitMQ Configuration
RABBITMQ_URL=amqp://admin:admin123@localhost:5672

# Model Configuration
MODEL_CACHE_DIR=./model_cache
HF_TOKEN=your_huggingface_token_here

# OCR Configuration
MATHPIX_API_KEY=your_mathpix_key_here
MATHPIX_API_SECRET=your_mathpix_secret_here

# Service Configuration
LOG_LEVEL=INFO
MAX_WORKERS=4
DEVICE=cuda  # or cpu
```

#### 6. Download Models

```bash
# Create models directory
mkdir -p models model_cache

# Download pre-trained models
python scripts/download_models.py
```

**scripts/download_models.py:**
```python
#!/usr/bin/env python3
"""Download and cache required ML models."""

import os
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

def download_models():
    """Download all required models."""
    models = [
        'microsoft/DialoGPT-small',
        'facebook/opt-350m',
        'microsoft/codebert-base'
    ]
    
    for model_name in models:
        print(f"Downloading {model_name}...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(model_name)
            
            # Save to local cache
            cache_dir = f"./model_cache/{model_name.replace('/', '_')}"
            os.makedirs(cache_dir, exist_ok=True)
            
            tokenizer.save_pretrained(cache_dir)
            model.save_pretrained(cache_dir)
            
            print(f"✓ {model_name} downloaded and cached")
        except Exception as e:
            print(f"✗ Failed to download {model_name}: {e}")

if __name__ == "__main__":
    download_models()
```

#### 7. Run ML Service

```bash
# Start the service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or with multiple workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# Service will be available at: http://localhost:8000
```

### Supporting Services Setup

#### Redis Installation

```bash
# Windows: Download from redis.io/download
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test Redis
redis-cli ping
# Should return: PONG
```

#### RabbitMQ Installation

```bash
# Windows: Download from rabbitmq.com/install-windows.html

# macOS
brew install rabbitmq
brew services start rabbitmq

# Ubuntu
sudo apt update
sudo apt install rabbitmq-server
sudo systemctl start rabbitmq-server
sudo systemctl enable rabbitmq-server

# Enable management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Create admin user
sudo rabbitmqctl add_user admin admin123
sudo rabbitmqctl set_user_tags admin administrator
sudo rabbitmqctl set_permissions -p / admin ".*" ".*" ".*"

# Access management UI: http://localhost:15672
```

## IDE Configuration

### Visual Studio Code Setup

#### 1. Install Extensions

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-dotnettools.csharp",
    "ms-python.python",
    "ms-python.pylint",
    "ms-python.black-formatter",
    "ms-vscode.docker",
    "ms-kubernetes-tools.vscode-kubernetes-tools",
    "humao.rest-client",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode"
  ]
}
```

#### 2. Workspace Configuration

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "./homework-solver-ml/venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "dotnet.completion.showCompletionItemsFromUnimportedNamespaces": true,
  "omnisharp.enableRoslynAnalyzers": true,
  "files.exclude": {
    "**/bin": true,
    "**/obj": true,
    "**/__pycache__": true,
    "**/venv": true,
    "**/node_modules": true
  }
}
```

#### 3. Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch API",
      "type": "coreclr",
      "request": "launch",
      "preLaunchTask": "build-api",
      "program": "${workspaceFolder}/HomeworkSolver.API/bin/Debug/net8.0/HomeworkSolver.API.dll",
      "args": [],
      "cwd": "${workspaceFolder}/HomeworkSolver.API",
      "console": "internalConsole",
      "stopAtEntry": false,
      "env": {
        "ASPNETCORE_ENVIRONMENT": "Development"
      }
    },
    {
      "name": "Launch ML Service",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/homework-solver-ml/app/main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}/homework-solver-ml",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/homework-solver-ml"
      },
      "args": []
    }
  ]
}
```

#### 4. Tasks Configuration

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "build-api",
      "command": "dotnet",
      "type": "process",
      "args": ["build", "${workspaceFolder}/HomeworkSolver.API/HomeworkSolver.API.csproj"],
      "problemMatcher": "$msCompile"
    },
    {
      "label": "test-api",
      "command": "dotnet",
      "type": "process",
      "args": ["test", "${workspaceFolder}/HomeworkSolver.Tests/HomeworkSolver.Tests.csproj"],
      "problemMatcher": "$msCompile",
      "group": "test"
    },
    {
      "label": "test-ml",
      "command": "python",
      "type": "shell",
      "args": ["-m", "pytest", "tests/", "-v"],
      "options": {
        "cwd": "${workspaceFolder}/homework-solver-ml"
      },
      "group": "test"
    }
  ]
}
```

### Visual Studio 2022 Setup

#### 1. Install Workloads
- ASP.NET and web development
- .NET Multi-platform App UI development
- Python development (optional)

#### 2. Solution Structure

```
HomeworkSolver.sln
├── src/
│   ├── HomeworkSolver.API/
│   ├── HomeworkSolver.Core/
│   ├── HomeworkSolver.Infrastructure/
│   └── HomeworkSolver.Shared/
├── tests/
│   ├── HomeworkSolver.API.Tests/
│   ├── HomeworkSolver.Core.Tests/
│   └── HomeworkSolver.Integration.Tests/
└── homework-solver-ml/
    ├── app/
    ├── tests/
    └── requirements.txt
```

## Development Containers (DevContainers)

### 1. DevContainer Configuration

```json
// .devcontainer/devcontainer.json
{
  "name": "Homework Solver Dev",
  "dockerComposeFile": "../docker-compose.dev.yml",
  "service": "dev",
  "workspaceFolder": "/workspace",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-dotnettools.csharp",
        "ms-python.python",
        "ms-vscode.docker"
      ],
      "settings": {
        "terminal.integrated.defaultProfile.linux": "bash"
      }
    }
  },
  "forwardPorts": [5000, 8000, 5432, 6379, 15672],
  "postCreateCommand": "bash .devcontainer/setup.sh",
  "remoteUser": "vscode"
}
```

### 2. Development Docker Compose

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  dev:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile
    volumes:
      - .:/workspace:cached
      - /var/run/docker.sock:/var/run/docker.sock
    command: sleep infinity
    environment:
      - DOCKER_BUILDKIT=1
    networks:
      - dev-network

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: mysql123
      MYSQL_DATABASE: homework_solver_dev
      MYSQL_USER: homework_user
      MYSQL_PASSWORD: homework_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_dev_data:/var/lib/mysql
    command: --default-authentication-plugin=mysql_native_password
    networks:
      - dev-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - dev-network

  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin123
    ports:
      - "5672:5672"
      - "15672:15672"
    networks:
      - dev-network

volumes:
  mysql_dev_data:

networks:
  dev-network:
    driver: bridge
```

### 3. Development Dockerfile

```dockerfile
# .devcontainer/Dockerfile
FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    wget \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install .NET SDK
RUN wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && apt-get install -y dotnet-sdk-8.0

# Install Python 3.11
RUN add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y python3.11 python3.11-pip python3.11-venv python3.11-dev

# Install Docker CLI
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install additional tools
RUN apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up user
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && usermod -aG docker $USERNAME

USER $USERNAME
```

## Testing Setup

### .NET API Tests

```bash
# Install test dependencies
cd HomeworkSolver.Tests
dotnet add package Microsoft.AspNetCore.Mvc.Testing
dotnet add package Testcontainers.MySql
dotnet add package Testcontainers.Redis

# Run tests
dotnet test --logger "console;verbosity=detailed"

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"
```

### Python ML Service Tests

```bash
# Install test dependencies
cd homework-solver-ml
pip install pytest pytest-asyncio pytest-mock httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Integration Tests

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
dotnet test HomeworkSolver.Integration.Tests/

# Cleanup
docker-compose -f docker-compose.test.yml down
```

## Debugging Setup

### .NET API Debugging

```csharp
// Add to Program.cs for development
if (app.Environment.IsDevelopment())
{
    app.UseDeveloperExceptionPage();
    app.UseSwagger();
    app.UseSwaggerUI();
}

// Enable detailed errors
app.UseDeveloperExceptionPage();
```

### Python ML Service Debugging

```python
# app/main.py - Add debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable uvicorn debugging
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )
```

## Performance Monitoring

### Local Monitoring Stack

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```

## Troubleshooting

### Common Issues

#### 1. Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :5000
lsof -i :5000

# Kill process using port
kill -9 $(lsof -ti:5000)
```

#### 2. Database Connection Issues
```bash
# Test MySQL connection
mysql -h localhost -u homework_user -p homework_solver

# Reset database
docker-compose down mysql
docker volume rm homework-solver_mysql_data
docker-compose up mysql -d
```

#### 3. Python Dependencies
```bash
# Rebuild virtual environment
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 4. Docker Issues
```bash
# Clean Docker system
docker system prune -a

# Rebuild images
docker-compose build --no-cache

# Check logs
docker-compose logs -f service-name
```

### Development Scripts

```bash
# scripts/dev-setup.sh
#!/bin/bash
echo "Setting up Homework Solver development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }
command -v dotnet >/dev/null 2>&1 || { echo ".NET SDK is required"; exit 1; }
command -v python3.11 >/dev/null 2>&1 || { echo "Python 3.11 is required"; exit 1; }

# Start infrastructure services
docker-compose -f docker-compose.dev.yml up -d mysql redis rabbitmq

# Setup .NET API
cd HomeworkSolver.API
dotnet restore
dotnet ef database update

# Setup Python ML service
cd ../homework-solver-ml
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/download_models.py

echo "Development environment setup complete!"
echo "API: http://localhost:5000"
echo "ML Service: http://localhost:8000"
echo "RabbitMQ Management: http://localhost:15672"
```

```bash
# scripts/run-tests.sh
#!/bin/bash
echo "Running all tests..."

# .NET API tests
echo "Running .NET API tests..."
dotnet test HomeworkSolver.Tests/

# Python ML service tests
echo "Running Python ML service tests..."
cd homework-solver-ml
source venv/bin/activate
pytest tests/ -v

# Integration tests
echo "Running integration tests..."
cd ..
dotnet test HomeworkSolver.Integration.Tests/

echo "All tests completed!"
```

Make both scripts executable:
```bash
chmod +x scripts/dev-setup.sh
chmod +x scripts/run-tests.sh
```