# Mathematics Mobile Backend - Microservices Migration Guide

## Overview
This guide provides a comprehensive plan for migrating the Mathematics Mobile backend from a monolithic architecture to a microservices architecture, similar to the Ceramic and Stock Predict projects.

## Architecture Design

### Microservices Breakdown

1. **API Gateway (Traefik)**
   - Port: 8003 (main gateway)
   - Dashboard: 8083
   - Routes all incoming requests to appropriate services
   - Handles load balancing and service discovery

2. **Auth Service**
   - Port: 5001 (internal)
   - Responsibilities:
     - User registration and login
     - JWT token generation and validation
     - Password management
     - User profile management

3. **Problem Service**
   - Port: 5002 (internal)
   - Responsibilities:
     - Problem submission
     - Problem history management
     - File upload handling
     - Problem status tracking

4. **Solution Service (ML/AI)**
   - Port: 5003 (internal)
   - Responsibilities:
     - Mathematical problem solving
     - OCR processing
     - Solution generation
     - AI/ML model management

### Shared Infrastructure

1. **MySQL Database**
   - Port: 3310
   - Shared by all services
   - User: mathematic_user
   - Password: Mysql_2025

2. **Redis Cache**
   - Port: 6380
   - Session storage
   - Caching layer
   - Rate limiting

3. **RabbitMQ**
   - Port: 5672
   - Management: 15673
   - Asynchronous communication between services
   - Event-driven architecture

## Migration Steps

### Phase 1: Service Extraction

1. **Create Service Projects**
```bash
# Auth Service
dotnet new webapi -n AuthService -o microservices/auth-service/src
dotnet add microservices/auth-service/src package Microsoft.AspNetCore.Authentication.JwtBearer
dotnet add microservices/auth-service/src package BCrypt.Net-Next
dotnet add microservices/auth-service/src package RabbitMQ.Client

# Problem Service
dotnet new webapi -n ProblemService -o microservices/problem-service/src
dotnet add microservices/problem-service/src package Microsoft.EntityFrameworkCore.Design
dotnet add microservices/problem-service/src package Pomelo.EntityFrameworkCore.MySql

# Solution Service
dotnet new webapi -n SolutionService -o microservices/solution-service/src
dotnet add microservices/solution-service/src package Microsoft.ML
dotnet add microservices/solution-service/src package Tesseract
```

2. **Extract Domain Logic**
   - Move authentication logic to Auth Service
   - Move problem management to Problem Service
   - Move solution processing to Solution Service

### Phase 2: Inter-Service Communication

1. **Synchronous Communication (HTTP)**
   - Use HttpClient for direct service-to-service calls
   - Implement retry policies with Polly

2. **Asynchronous Communication (RabbitMQ)**
   - Problem submission events
   - Solution processing events
   - User registration events

### Phase 3: Data Management

1. **Database Schema**
   - Keep shared database initially
   - Plan for future database per service pattern
   - Use database views for service isolation

2. **Data Synchronization**
   - Implement event sourcing for data consistency
   - Use saga pattern for distributed transactions

## Service Configurations

### Auth Service Configuration
```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information"
    }
  },
  "ConnectionStrings": {
    "DefaultConnection": "Server=mysql;Database=mathematic_db;User=mathematic_user;Password=Mysql_2025;",
    "Redis": "redis:6379"
  },
  "Jwt": {
    "SecretKey": "your-secret-key-here-min-32-characters!",
    "Issuer": "MathematicsSolverAPI",
    "Audience": "MathematicsSolverClient",
    "ExpirationMinutes": 60
  },
  "RabbitMQ": {
    "Host": "rabbitmq",
    "Username": "admin",
    "Password": "admin123",
    "VirtualHost": "math"
  }
}
```

### Problem Service Configuration
```json
{
  "Services": {
    "AuthService": "http://auth-service:5001",
    "SolutionService": "http://solution-service:5003"
  },
  "FileStorage": {
    "UploadPath": "/app/uploads",
    "MaxFileSizeInBytes": 10485760
  }
}
```

### Solution Service Configuration
```json
{
  "ML": {
    "ModelPath": "/app/models",
    "MaxConcurrentRequests": 10,
    "RequestTimeoutSeconds": 300
  }
}
```

## API Endpoints Mapping

### Before (Monolithic)
- `/api/auth/login`
- `/api/auth/register`
- `/api/problems/submit`
- `/api/problems/{id}`
- `/api/problems/user/{userId}`

### After (Microservices)
- `/api/v1/auth/login` → Auth Service
- `/api/v1/auth/register` → Auth Service
- `/api/v1/problems/submit` → Problem Service
- `/api/v1/problems/{id}` → Problem Service
- `/api/v1/solutions/{problemId}` → Solution Service

## Docker Compose Structure

```yaml
services:
  # Gateway
  traefik:
    # Configuration...

  # Services
  auth-service:
    # Configuration...

  problem-service:
    # Configuration...

  solution-service:
    # Configuration...

  # Infrastructure
  mysql:
    # Configuration...

  redis:
    # Configuration...

  rabbitmq:
    # Configuration...
```

## Health Checks

Each service should implement:
- `/health` - Basic health check
- `/health/ready` - Readiness probe
- `/health/live` - Liveness probe

## Security Considerations

1. **Service-to-Service Authentication**
   - Use internal JWT tokens
   - Implement mTLS for production

2. **API Gateway Security**
   - Rate limiting per service
   - CORS configuration
   - Request validation

3. **Data Security**
   - Encrypt sensitive data at rest
   - Use SSL/TLS for all communications

## Monitoring and Observability

1. **Prometheus Metrics**
   - Service response times
   - Request counts
   - Error rates

2. **Grafana Dashboards**
   - Service health overview
   - Performance metrics
   - Business metrics

3. **Distributed Tracing**
   - Implement OpenTelemetry
   - Trace requests across services

## Deployment Strategy

1. **Local Development**
   ```bash
   docker-compose -f docker-compose.microservices.yml up -d
   ```

2. **Production Deployment**
   - Use Kubernetes for orchestration
   - Implement rolling updates
   - Blue-green deployments

## Rollback Plan

1. Keep monolithic version running
2. Implement feature flags
3. Gradual traffic migration
4. Quick rollback capability

## Testing Strategy

1. **Unit Tests**
   - Test each service independently
   - Mock external dependencies

2. **Integration Tests**
   - Test service interactions
   - Use test containers

3. **End-to-End Tests**
   - Test complete user flows
   - Performance testing

## Timeline

- Week 1-2: Service extraction and basic setup
- Week 3-4: Inter-service communication
- Week 5-6: Testing and debugging
- Week 7-8: Deployment and monitoring setup

## Benefits of Microservices Architecture

1. **Scalability**
   - Scale services independently
   - Optimize resource usage

2. **Development Speed**
   - Teams work independently
   - Faster deployment cycles

3. **Fault Isolation**
   - Service failures don't affect entire system
   - Better error handling

4. **Technology Diversity**
   - Use best technology for each service
   - Easier to adopt new technologies

## Challenges and Solutions

1. **Data Consistency**
   - Solution: Event sourcing and saga pattern

2. **Service Discovery**
   - Solution: Use Traefik with Docker labels

3. **Monitoring Complexity**
   - Solution: Centralized logging and monitoring

4. **Testing Complexity**
   - Solution: Contract testing and test automation