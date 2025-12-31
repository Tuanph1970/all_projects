# Deployment Workflow - Docker & Kubernetes

## Overview

This document outlines the complete deployment strategy for the Homework Solver system, covering both local development with Docker and production deployment with Kubernetes. The system consists of two main services: .NET Core Web API and Python ML Service.

## Architecture Overview

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Frontend Tier"
            LB[Load Balancer]
            INGRESS[Nginx Ingress Controller]
        end
        
        subgraph "Application Tier"
            API[.NET API Service]
            ML[Python ML Service]
        end
        
        subgraph "Data Tier"
            MYSQL[(MySQL)]
            REDIS[(Redis)]
            RABBIT[RabbitMQ]
        end
        
        subgraph "Storage"
            PVC[Persistent Volume]
            S3[Object Storage]
        end
    end
    
    MOBILE[Mobile App] --> LB
    LB --> INGRESS
    INGRESS --> API
    API --> ML
    API --> PG
    API --> REDIS
    API --> RABBIT
    ML --> RABBIT
    ML --> REDIS
    ML --> PVC
    API --> S3
```

## Docker Configuration

### .NET Core API Service Dockerfile

```dockerfile
# Dockerfile.api
FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS base
WORKDIR /app
EXPOSE 80
EXPOSE 443

FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY ["HomeworkSolver.API/HomeworkSolver.API.csproj", "HomeworkSolver.API/"]
COPY ["HomeworkSolver.Core/HomeworkSolver.Core.csproj", "HomeworkSolver.Core/"]
COPY ["HomeworkSolver.Infrastructure/HomeworkSolver.Infrastructure.csproj", "HomeworkSolver.Infrastructure/"]

RUN dotnet restore "HomeworkSolver.API/HomeworkSolver.API.csproj"
COPY . .
WORKDIR "/src/HomeworkSolver.API"
RUN dotnet build "HomeworkSolver.API.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "HomeworkSolver.API.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Create non-root user
RUN groupadd -r apiuser && useradd -r -g apiuser apiuser
RUN chown -R apiuser:apiuser /app
USER apiuser

ENTRYPOINT ["dotnet", "HomeworkSolver.API.dll"]
```

### Python ML Service Dockerfile

```dockerfile
# Dockerfile.ml
FROM nvidia/cuda:12.1-runtime-ubuntu22.04 AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set python3.11 as default python
RUN ln -sf /usr/bin/python3.11 /usr/bin/python
RUN ln -sf /usr/bin/pip3 /usr/bin/pip

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy application code
COPY . .

# Download and cache ML models
RUN python -c "
import torch
from transformers import AutoTokenizer, AutoModel
from huggingface_hub import hf_hub_download

# Download models to cache
models = [
    'microsoft/DialoGPT-small',
    'facebook/opt-350m'
]

for model in models:
    try:
        tokenizer = AutoTokenizer.from_pretrained(model)
        model_obj = AutoModel.from_pretrained(model)
        print(f'Cached {model}')
    except Exception as e:
        print(f'Failed to cache {model}: {e}')
"

# Create non-root user
RUN groupadd -r mluser && useradd -r -g mluser mluser
RUN chown -R mluser:mluser /app
USER mluser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  # MySQL Database
  mysql:
    image: mysql:8.0
    container_name: homework-solver-mysql
    environment:
      MYSQL_ROOT_PASSWORD: mysql123
      MYSQL_DATABASE: homework_solver
      MYSQL_USER: homework_user
      MYSQL_PASSWORD: homework_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    command: --default-authentication-plugin=mysql_native_password
    networks:
      - homework-solver-network

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: homework-solver-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - homework-solver-network

  # RabbitMQ Message Queue
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: homework-solver-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: admin123
    ports:
      - "5672:5672"
      - "15672:15672"  # Management UI
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - homework-solver-network

  # .NET API Service
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: homework-solver-api
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - ConnectionStrings__DefaultConnection=Server=mysql;Database=homework_solver;Uid=homework_user;Pwd=homework_password;
      - ConnectionStrings__Redis=redis:6379
      - ConnectionStrings__RabbitMQ=amqp://admin:admin123@rabbitmq:5672
      - MLService__BaseUrl=http://ml-service:8000
      - Jwt__SecretKey=your-super-secret-jwt-key-here-make-it-long
      - Jwt__Issuer=HomeworkSolver
      - Jwt__Audience=HomeworkSolverApp
    ports:
      - "5000:80"
      - "5001:443"
    depends_on:
      - mysql
      - redis
      - rabbitmq
    networks:
      - homework-solver-network
    volumes:
      - ./uploads:/app/uploads

  # Python ML Service
  ml-service:
    build:
      context: ./homework-solver-ml
      dockerfile: Dockerfile.ml
    container_name: homework-solver-ml
    environment:
      - REDIS_URL=redis://redis:6379/0
      - RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672
      - MODEL_CACHE_DIR=/app/model_cache
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - rabbitmq
    networks:
      - homework-solver-network
    volumes:
      - ml_models:/app/model_cache
      - ./homework-solver-ml/models:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Nginx Load Balancer
  nginx:
    image: nginx:alpine
    container_name: homework-solver-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - homework-solver-network

volumes:
  mysql_data:
  redis_data:
  rabbitmq_data:
  ml_models:

networks:
  homework-solver-network:
    driver: bridge
```

### Nginx Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:80;
    }
    
    upstream ml_backend {
        server ml-service:8000;
    }

    server {
        listen 80;
        server_name localhost;

        # API endpoints
        location /api/ {
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support for SignalR
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # ML service endpoints (internal only)
        location /ml/ {
            deny all;
            return 403;
        }

        # Health check
        location /health {
            proxy_pass http://api_backend;
        }

        # Rate limiting
        location / {
            limit_req zone=api burst=10 nodelay;
            proxy_pass http://api_backend;
        }
    }

    # Rate limiting zone
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

## Kubernetes Deployment

### Namespace Configuration

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: homework-solver
  labels:
    name: homework-solver
    environment: production
```

### ConfigMaps and Secrets

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: homework-solver-config
  namespace: homework-solver
data:
  # API Configuration
  ASPNETCORE_ENVIRONMENT: "Production"
  ML_SERVICE_BASE_URL: "http://ml-service:8000"
  JWT_ISSUER: "HomeworkSolver"
  JWT_AUDIENCE: "HomeworkSolverApp"
  
  # ML Service Configuration
  MODEL_CACHE_DIR: "/app/model_cache"
  MAX_BATCH_SIZE: "32"
  INFERENCE_TIMEOUT: "30"
  
  # Database Configuration
  MYSQL_HOST: "mysql-service"
  MYSQL_PORT: "3306"
  MYSQL_DATABASE: "homework_solver"
  
  # Redis Configuration
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  
  # RabbitMQ Configuration
  RABBITMQ_HOST: "rabbitmq-service"
  RABBITMQ_PORT: "5672"

---
apiVersion: v1
kind: Secret
metadata:
  name: homework-solver-secrets
  namespace: homework-solver
type: Opaque
stringData:
  # Database secrets
  MYSQL_USERNAME: "homework_user"
  MYSQL_PASSWORD: "secure-mysql-password"
  MYSQL_ROOT_PASSWORD: "secure-mysql-root-password"
  
  # JWT secrets
  JWT_SECRET_KEY: "your-super-secure-jwt-secret-key-for-production"
  
  # RabbitMQ secrets
  RABBITMQ_USERNAME: "admin"
  RABBITMQ_PASSWORD: "secure-rabbitmq-password"
  
  # External API keys
  MATHPIX_API_KEY: "your-mathpix-api-key"
  MATHPIX_API_SECRET: "your-mathpix-api-secret"
```

### Persistent Storage

```yaml
# k8s/persistent-volumes.yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: mysql-pv
  namespace: homework-solver
spec:
  capacity:
    storage: 20Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: fast-ssd
  hostPath:
    path: /mnt/data/mysql

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: mysql-pvc
  namespace: homework-solver
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: fast-ssd

---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: ml-models-pv
  namespace: homework-solver
spec:
  capacity:
    storage: 50Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: fast-ssd
  hostPath:
    path: /mnt/data/ml-models

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ml-models-pvc
  namespace: homework-solver
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 50Gi
  storageClassName: fast-ssd
```

### Database Deployment

```yaml
# k8s/mysql-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysql-deployment
  namespace: homework-solver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
        env:
        - name: MYSQL_DATABASE
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: MYSQL_DATABASE
        - name: MYSQL_USER
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MYSQL_USERNAME
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MYSQL_PASSWORD
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MYSQL_ROOT_PASSWORD
        args:
        - --default-authentication-plugin=mysql_native_password
        volumeMounts:
        - name: mysql-storage
          mountPath: /var/lib/mysql
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: mysql-storage
        persistentVolumeClaim:
          claimName: mysql-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: mysql-service
  namespace: homework-solver
spec:
  selector:
    app: mysql
  ports:
  - protocol: TCP
    port: 3306
    targetPort: 3306
  type: ClusterIP
```

### Redis Deployment

```yaml
# k8s/redis-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-deployment
  namespace: homework-solver
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
        command: ["redis-server"]
        args: ["--appendonly", "yes", "--maxmemory", "512mb", "--maxmemory-policy", "allkeys-lru"]
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          tcpSocket:
            port: 6379
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: homework-solver
spec:
  selector:
    app: redis
  ports:
  - protocol: TCP
    port: 6379
    targetPort: 6379
  type: ClusterIP
```

### .NET API Service Deployment

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
  namespace: homework-solver
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: homework-solver-api:latest
        ports:
        - containerPort: 80
        env:
        - name: ASPNETCORE_ENVIRONMENT
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: ASPNETCORE_ENVIRONMENT
        - name: ConnectionStrings__DefaultConnection
          value: "Server=$(MYSQL_HOST);Port=$(MYSQL_PORT);Database=$(MYSQL_DATABASE);Uid=$(MYSQL_USERNAME);Pwd=$(MYSQL_PASSWORD);"
        - name: MYSQL_HOST
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: MYSQL_HOST
        - name: MYSQL_PORT
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: MYSQL_PORT
        - name: MYSQL_DATABASE
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: MYSQL_DATABASE
        - name: MYSQL_USERNAME
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MYSQL_USERNAME
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MYSQL_PASSWORD
        - name: ConnectionStrings__Redis
          value: "$(REDIS_HOST):$(REDIS_PORT)"
        - name: REDIS_HOST
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: REDIS_HOST
        - name: REDIS_PORT
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: REDIS_PORT
        - name: MLService__BaseUrl
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: ML_SERVICE_BASE_URL
        - name: Jwt__SecretKey
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: JWT_SECRET_KEY
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: uploads
          mountPath: /app/uploads
      volumes:
      - name: uploads
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: homework-solver
spec:
  selector:
    app: api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 80
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: api-hpa
  namespace: homework-solver
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api-deployment
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Python ML Service Deployment

```yaml
# k8s/ml-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ml-deployment
  namespace: homework-solver
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ml-service
  template:
    metadata:
      labels:
        app: ml-service
    spec:
      containers:
      - name: ml-service
        image: homework-solver-ml:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://$(REDIS_HOST):$(REDIS_PORT)/0"
        - name: REDIS_HOST
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: REDIS_HOST
        - name: REDIS_PORT
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: REDIS_PORT
        - name: MODEL_CACHE_DIR
          valueFrom:
            configMapKeyRef:
              name: homework-solver-config
              key: MODEL_CACHE_DIR
        - name: MATHPIX_API_KEY
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MATHPIX_API_KEY
        - name: MATHPIX_API_SECRET
          valueFrom:
            secretKeyRef:
              name: homework-solver-secrets
              key: MATHPIX_API_SECRET
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
            nvidia.com/gpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
            nvidia.com/gpu: "1"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
        volumeMounts:
        - name: model-storage
          mountPath: /app/model_cache
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: ml-models-pvc
      nodeSelector:
        nvidia.com/gpu.present: "true"
      tolerations:
      - key: "nvidia.com/gpu"
        operator: "Exists"
        effect: "NoSchedule"

---
apiVersion: v1
kind: Service
metadata:
  name: ml-service
  namespace: homework-solver
spec:
  selector:
    app: ml-service
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ml-hpa
  namespace: homework-solver
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ml-deployment
  minReplicas: 2
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 85
```

### Ingress Configuration

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: homework-solver-ingress
  namespace: homework-solver
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.homeworksolver.com
    secretName: homework-solver-tls
  rules:
  - host: api.homeworksolver.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
      - path: /health
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: homework-solver

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: mysql123
          MYSQL_DATABASE: test_db
          MYSQL_USER: test_user
          MYSQL_PASSWORD: test_password
        options: >-
          --health-cmd="mysqladmin ping -h localhost"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v4
    
    - name: Setup .NET
      uses: actions/setup-dotnet@v3
      with:
        dotnet-version: 8.0.x
        
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Cache .NET packages
      uses: actions/cache@v3
      with:
        path: ~/.nuget/packages
        key: ${{ runner.os }}-nuget-${{ hashFiles('**/*.csproj') }}
        
    - name: Cache Python packages
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        
    # Test .NET API
    - name: Restore .NET dependencies
      run: dotnet restore
      
    - name: Build .NET project
      run: dotnet build --no-restore
      
    - name: Test .NET project
      run: dotnet test --no-build --verbosity normal
      env:
        ConnectionStrings__DefaultConnection: "Server=localhost;Database=test_db;Uid=test_user;Pwd=test_password;"
        ConnectionStrings__Redis: "localhost:6379"
        
    # Test Python ML Service
    - name: Install Python dependencies
      run: |
        cd homework-solver-ml
        pip install -r requirements.txt
        
    - name: Test Python ML Service
      run: |
        cd homework-solver-ml
        python -m pytest tests/ -v
      env:
        REDIS_URL: "redis://localhost:6379/0"

  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    strategy:
      matrix:
        service: [api, ml]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ github.repository }}-${{ matrix.service }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}
          
    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: ${{ matrix.service == 'ml' && './homework-solver-ml' || '.' }}
        file: ${{ matrix.service == 'ml' && './homework-solver-ml/Dockerfile.ml' || './Dockerfile.api' }}
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      
    - name: Set up Kubeconfig
      run: |
        mkdir -p ~/.kube
        echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
        
    - name: Update deployment images
      run: |
        kubectl set image deployment/api-deployment api=${{ env.REGISTRY }}/${{ github.repository }}-api:${{ github.sha }} -n homework-solver
        kubectl set image deployment/ml-deployment ml-service=${{ env.REGISTRY }}/${{ github.repository }}-ml:${{ github.sha }} -n homework-solver
        
    - name: Wait for rollout to complete
      run: |
        kubectl rollout status deployment/api-deployment -n homework-solver --timeout=300s
        kubectl rollout status deployment/ml-deployment -n homework-solver --timeout=300s
        
    - name: Verify deployment
      run: |
        kubectl get pods -n homework-solver
        kubectl get services -n homework-solver
```

## Monitoring and Logging

### Prometheus Configuration

```yaml
# k8s/monitoring/prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: homework-solver
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s

    rule_files:
      - "alerts.yml"

    scrape_configs:
      - job_name: 'api-service'
        kubernetes_sd_configs:
          - role: endpoints
            namespaces:
              names:
                - homework-solver
        relabel_configs:
          - source_labels: [__meta_kubernetes_service_name]
            action: keep
            regex: api-service
          - source_labels: [__meta_kubernetes_endpoint_port_name]
            action: keep
            regex: metrics

      - job_name: 'ml-service'
        kubernetes_sd_configs:
          - role: endpoints
            namespaces:
              names:
                - homework-solver
        relabel_configs:
          - source_labels: [__meta_kubernetes_service_name]
            action: keep
            regex: ml-service
          - source_labels: [__meta_kubernetes_endpoint_port_name]
            action: keep
            regex: metrics

      - job_name: 'kubernetes-nodes'
        kubernetes_sd_configs:
          - role: node
        relabel_configs:
          - action: labelmap
            regex: __meta_kubernetes_node_label_(.+)
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Homework Solver Metrics",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "title": "ML Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(solution_generation_seconds_bucket[5m])) by (le))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))"
          }
        ]
      }
    ]
  }
}
```

## Security Configuration

### Network Policies

```yaml
# k8s/security/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-network-policy
  namespace: homework-solver
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 80
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: ml-service
    ports:
    - protocol: TCP
      port: 8000

---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: ml-network-policy
  namespace: homework-solver
spec:
  podSelector:
    matchLabels:
      app: ml-service
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: api
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Backup and Disaster Recovery

### Database Backup CronJob

```yaml
# k8s/backup/mysql-backup.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mysql-backup
  namespace: homework-solver
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: mysql-backup
            image: mysql:8.0
            env:
            - name: MYSQL_PWD
              valueFrom:
                secretKeyRef:
                  name: homework-solver-secrets
                  key: MYSQL_PASSWORD
            command:
            - /bin/sh
            - -c
            - |
              mysqldump -h mysql-service -u homework_user homework_solver > /backup/backup-$(date +%Y%m%d-%H%M%S).sql
              # Upload to S3 or other storage
              aws s3 cp /backup/backup-$(date +%Y%m%d-%H%M%S).sql s3://homework-solver-backups/
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            emptyDir: {}
```

## Scaling and Performance

### Resource Quotas

```yaml
# k8s/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: homework-solver-quota
  namespace: homework-solver
spec:
  hard:
    requests.cpu: "8"
    requests.memory: 16Gi
    limits.cpu: "16"
    limits.memory: 32Gi
    nvidia.com/gpu: "4"
    persistentvolumeclaims: "5"
    count/deployments.apps: "10"
    count/services: "10"
    count/secrets: "10"
    count/configmaps: "10"
```

## Deployment Commands

### Local Development

```bash
# Build and start services
docker-compose up --build -d

# View logs
docker-compose logs -f api
docker-compose logs -f ml-service

# Scale ML service
docker-compose up --scale ml-service=3 -d

# Stop services
docker-compose down
```

### Production Deployment

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/persistent-volumes.yaml

# Deploy services
kubectl apply -f k8s/mysql-deployment.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/rabbitmq-deployment.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=mysql -n homework-solver --timeout=300s

# Deploy applications
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/ml-deployment.yaml

# Apply ingress
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get all -n homework-solver
```

### Health Check and Troubleshooting

```bash
# Check pod status
kubectl get pods -n homework-solver

# View pod logs
kubectl logs -f deployment/api-deployment -n homework-solver
kubectl logs -f deployment/ml-deployment -n homework-solver

# Port forward for local testing
kubectl port-forward service/api-service 5000:80 -n homework-solver

# Execute into pod
kubectl exec -it deployment/api-deployment -n homework-solver -- /bin/bash

# Check resource usage
kubectl top pods -n homework-solver
kubectl top nodes
```