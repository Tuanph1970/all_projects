# Product Requirements Document (PRD)
# AI-Powered Homework Solver for High School Students

## 1. Executive Summary

### Product Vision
An intelligent mobile application that empowers Vietnamese high school students to understand and solve mathematical problems through photo capture, providing detailed step-by-step solutions using advanced AI technology with continuous improvement through user feedback.

### Key Value Proposition
- **Instant Learning**: Convert homework photos into comprehensive solutions
- **Localized Education**: Tailored for Vietnamese curriculum and language
- **Expert-Level Guidance**: Specialized AI models for different mathematical domains
- **Certificate Exam Preparation**: Focused training for standardized tests
- **Continuous Improvement**: User feedback drives solution quality enhancement

## 2. Product Overview

### 2.1 Problem Statement
Vietnamese high school students struggle with:
- Complex mathematical problems without immediate help
- Language barriers in international educational resources
- Lack of step-by-step guidance for exam preparation
- Limited access to subject-specific tutoring
- No personalized learning path based on their progress

### 2.2 Solution
A mobile application leveraging computer vision and specialized LLM agents to provide instant, detailed mathematical solutions with explanations in Vietnamese, enhanced by community feedback and personalized user profiles.

### 2.3 Success Metrics
- User engagement: Daily active users > 10,000 within 6 months
- Solution accuracy: > 95% for standard problems
- User satisfaction: > 4.5/5 app store rating
- Problem resolution time: < 30 seconds per problem
- Retention rate: > 60% monthly active users
- Feedback participation: > 30% of solutions receive ratings
- Account creation rate: > 70% of users create accounts

## 3. User Personas

### Primary Persona: High School Student
- **Age**: 15-18 years
- **Goals**: Pass exams, understand concepts, quick homework completion, track progress
- **Pain Points**: Complex problems, limited tutoring access, time constraints
- **Tech Savvy**: High smartphone usage, familiar with educational apps

### Secondary Persona: Parents/Tutors
- **Goals**: Support student learning, track progress, monitor usage
- **Needs**: Reliable solutions, educational value, safe platform, progress reports

### Tertiary Persona: Teachers
- **Goals**: Understand student difficulties, provide better support
- **Needs**: Analytics on common problem areas, class performance insights

## 4. Functional Requirements

### 4.1 Authentication & User Management

#### Feature 1: User Registration (Sign Up)
- **Description**: Create user account for personalized experience
- **Registration Methods**:
  - Email & Password
  - Phone Number (SMS OTP)
  - Social Login (Google, Facebook)
  - Apple ID (for iOS)
- **Required Information**:
  - Full Name
  - Grade Level (10, 11, 12)
  - School (optional)
  - Target Exam (optional)
- **Acceptance Criteria**:
  - Email/Phone verification required
  - Password strength requirements (min 8 chars, mixed case, numbers)
  - Terms of Service and Privacy Policy acceptance
  - Age verification (13+ years)
  - Profile completion wizard for new users

#### Feature 2: User Login
- **Description**: Secure authentication system
- **Features**:
  - Email/Phone + Password
  - Social Login integration
  - Biometric authentication (Face ID, Touch ID, Fingerprint)
  - Remember Me option
  - Forgot Password flow
- **Security Features**:
  - Account lockout after 5 failed attempts
  - Two-factor authentication (optional)
  - Session management
  - JWT token with refresh mechanism
- **Acceptance Criteria**:
  - Login time < 2 seconds
  - Secure token storage
  - Auto-logout after 30 days of inactivity
  - Multi-device support

#### Feature 3: User Profile Management
- **Description**: Comprehensive user profile system
- **Profile Information**:
  - Personal Details (editable)
  - Academic Information (grade, subjects, target exams)
  - Learning Preferences (language, difficulty level)
  - Avatar upload
  - Notification settings
- **Features**:
  - Progress statistics dashboard
  - Achievement badges
  - Study streak tracking
  - Subscription status
- **Acceptance Criteria**:
  - Real-time profile updates
  - Image upload with compression
  - Privacy settings (public/private profile)

### 4.2 Core Features

#### Feature 4: Problem Category Selection
- **Description**: Students select mathematical domain before solving
- **Categories**:
  - Algebra (Linear, Quadratic, Polynomial)
  - Geometry (2D shapes, theorems, proofs)
  - 3D Geometry (Spatial reasoning, volumes)
  - Probability & Statistics
  - Complex Numbers
  - Calculus (Differentiation, Integration)
  - Trigonometry
- **Personalization**:
  - Recently used categories
  - Favorite categories (user-defined)
  - Recommended based on history
- **Acceptance Criteria**:
  - Visual category cards with icons
  - Search functionality
  - Usage analytics per category

#### Feature 5: Photo Capture & Processing
- **Description**: Capture mathematical problems via camera
- **Functionality**:
  - Auto-focus and image stabilization
  - Multiple image capture for long problems
  - Handwriting recognition support
  - Printed text recognition
  - Image quality checker
- **Acceptance Criteria**:
  - Support for both camera and gallery upload
  - Image quality validation with user guidance
  - Crop and rotate functionality
  - Multi-page problem support
  - Save original images to history

#### Feature 6: AI-Powered Solution Generation
- **Description**: Convert image to LaTeX and generate solutions
- **Process Flow**:
  1. OCR processing (image → text/LaTeX)
  2. Problem classification and validation
  3. Expert agent routing
  4. Solution generation with steps
  5. Vietnamese language adaptation
  6. Confidence score calculation
- **Acceptance Criteria**:
  - LaTeX rendering accuracy > 95%
  - Step-by-step breakdown
  - Multiple solution methods when applicable
  - Explanation in Vietnamese and English
  - Display confidence level
  - Alternative solutions suggestion

#### Feature 7: Solution Display & Interaction
- **Description**: Interactive solution presentation with feedback integration
- **Features**:
  - Step-by-step navigation
  - Mathematical notation rendering
  - Graph/diagram generation
  - Voice explanation (optional)
  - Save/bookmark solutions
  - Share functionality
  - Print-friendly format
- **Interactive Elements**:
  - Tap to expand/collapse steps
  - Swipe between solution methods
  - Pinch to zoom equations
  - Long-press for term definitions
- **Acceptance Criteria**:
  - Clean LaTeX/MathML rendering
  - Smooth animations
  - Offline viewing for saved solutions
  - Export to PDF

### 4.3 Feedback System

#### Feature 8: Solution Feedback & Rating
- **Description**: Comprehensive feedback system for continuous improvement
- **Feedback Types**:
  
  **A. Quick Rating**
  - 5-star rating system
  - One-tap helpful/not helpful
  - Emoji reactions (😊 Clear, 😕 Confusing, 😢 Wrong)
  
  **B. Detailed Feedback**
  - Accuracy feedback (Correct/Partially Correct/Incorrect)
  - Clarity rating for each step
  - Missing steps identification
  - Alternative solution suggestion
  - Language quality feedback
  
  **C. Error Reporting**
  - OCR recognition errors
  - Mathematical errors
  - Translation issues
  - App bugs/crashes
  
- **Feedback Collection Points**:
  - Immediately after solution display
  - From solution history
  - Weekly feedback prompts
  - After exam results (outcome tracking)
  
- **Acceptance Criteria**:
  - Feedback submission < 2 seconds
  - Anonymous feedback option
  - Feedback acknowledgment message
  - Reward points for quality feedback

#### Feature 9: Community Feedback Features
- **Description**: Leverage community for solution improvement
- **Features**:
  
  **A. Solution Comments**
  - Add comments to specific steps
  - Upvote/downvote comments
  - Teacher-verified badge for comments
  - Reply threads
  
  **B. Alternative Solutions**
  - Submit alternative solution methods
  - Community voting on best approach
  - Expert verification process
  
  **C. Difficulty Rating**
  - Community-driven difficulty assessment
  - Problem complexity indicators
  
- **Moderation**:
  - Automated spam detection
  - Report inappropriate content
  - Trusted user privileges
  - Teacher/Expert moderators
  
- **Acceptance Criteria**:
  - Real-time comment updates
  - Notification for responses
  - Karma/reputation system
  - Top contributors leaderboard

#### Feature 10: Feedback Analytics Dashboard
- **Description**: Insights from collected feedback
- **For Students**:
  - Personal accuracy trends
  - Problem areas identification
  - Improvement suggestions
  
- **For System (Admin)**:
  - Solution quality metrics
  - Common error patterns
  - Model performance by category
  - User satisfaction trends
  
- **AI Model Improvement**:
  - Automatic retraining triggers
  - A/B testing different solutions
  - Feedback loop to fine-tuning pipeline
  
- **Acceptance Criteria**:
  - Real-time dashboard updates
  - Exportable reports
  - Predictive analytics for problem areas

### 4.4 Additional Features

#### Feature 11: Practice Mode with Adaptive Learning
- **Description**: Generate similar problems based on performance
- **Functionality**:
  - Difficulty adjustment based on feedback
  - Personalized problem sets
  - Timed practice sessions
  - Progress tracking
  - Weak area focus

#### Feature 12: Exam Preparation
- **Description**: Targeted preparation for specific exams
- **Content**:
  - Previous year questions
  - Mock tests with timer
  - Performance analytics
  - Predicted score based on practice
  - Study plan generator

#### Feature 13: Learning History & Progress
- **Description**: Comprehensive tracking system
- **Features**:
  - Solution history with search
  - Mistake patterns analysis
  - Strength/weakness identification
  - Study time tracking
  - Achievement system
  - Progress sharing with parents/teachers

#### Feature 14: Social Learning Features
- **Description**: Collaborative learning environment
- **Features**:
  - Study groups creation
  - Problem sharing with classmates
  - Peer-to-peer help requests
  - Class leaderboards
  - Challenge friends

## 5. Technical Requirements

### 5.0 Architecture Overview

The system follows a clean separation architecture with:
- **Frontend**: React Native mobile application
- **API Layer**: .NET Core 8.0 Web API (Authentication, CRUD, Business Logic)
- **ML Service**: Python + PyTorch service (OCR, LLM, Fine-tuning, AI Agents)
- **Database**: MySQL with Redis caching
- **Message Queue**: RabbitMQ for async ML processing
- **Containerization**: Docker for development, Kubernetes for production
- **Monitoring**: Application Insights, Prometheus, Grafana

**Service Communication**: 
- Frontend ↔ .NET API (REST/GraphQL)
- .NET API ↔ Python ML Service (HTTP/gRPC + Message Queue)

### 5.1 Frontend (React Native)

#### Technology Stack
- **Framework**: React Native 0.72+
- **State Management**: Redux Toolkit with RTK Query
- **Navigation**: React Navigation 6
- **Authentication**: React Native App Auth
- **Camera**: react-native-vision-camera
- **Image Processing**: react-native-image-picker, react-native-image-resizer
- **Math Rendering**: react-native-mathjax or KaTeX
- **Networking**: Axios with interceptors
- **Storage**: MMKV for secure storage
- **Analytics**: Firebase Analytics / Mixpanel
- **Push Notifications**: Firebase Cloud Messaging / OneSignal

#### Enhanced Component Structure
```
src/
├── components/
│   ├── Auth/
│   │   ├── LoginForm.jsx
│   │   ├── SignUpForm.jsx
│   │   └── SocialLogin.jsx
│   ├── Camera/
│   ├── MathRenderer/
│   ├── CategorySelector/
│   ├── SolutionViewer/
│   ├── Feedback/
│   │   ├── RatingModal.jsx
│   │   ├── DetailedFeedback.jsx
│   │   └── CommentSection.jsx
│   └── Profile/
│       ├── ProfileHeader.jsx
│       └── ProgressChart.jsx
├── screens/
│   ├── Auth/
│   │   ├── LoginScreen.jsx
│   │   ├── SignUpScreen.jsx
│   │   └── ForgotPasswordScreen.jsx
│   ├── HomeScreen.jsx
│   ├── CameraScreen.jsx
│   ├── SolutionScreen.jsx
│   ├── FeedbackScreen.jsx
│   ├── ProfileScreen.jsx
│   └── HistoryScreen.jsx
├── services/
│   ├── api/
│   ├── auth/
│   ├── feedback/
│   ├── imageProcessing/
│   └── storage/
├── store/
│   ├── authSlice.js
│   ├── feedbackSlice.js
│   └── solutionSlice.js
└── utils/
    ├── validators/
    ├── mathHelpers/
    └── feedbackAnalytics/
```

### 5.2 Backend Architecture

#### 5.2.1 .NET Core Web API Service

Pure API service focused on web application concerns:

**Core Responsibilities:**
- **Authentication & Authorization**: User management, JWT tokens, OAuth integration
- **CRUD Operations**: Database operations, data validation, business logic
- **API Gateway**: Request routing, rate limiting, API versioning
- **Real-time Communication**: SignalR for live updates and notifications
- **File Management**: Image upload, storage management (delegates processing to Python service)
- **Caching**: Redis integration for performance optimization

**What it does NOT handle:**
- OCR processing
- Machine learning model operations
- Image processing algorithms
- Model training or fine-tuning

**Service Communication:**
- **REST APIs**: HTTP/HTTPS for client communication
- **ML Service Integration**: HTTP API calls + RabbitMQ messaging to Python service
- **Real-time**: SignalR for live updates to mobile app

#### 5.2.2 Python ML Service

Dedicated machine learning service for AI operations:

**Core Responsibilities:**
- **OCR Processing**: Image-to-text conversion using EasyOCR, Tesseract, Mathpix
- **LLM Operations**: Model inference, solution generation, text processing
- **Model Management**: Loading, fine-tuning, version management of AI models
- **Mixture of Experts (MoE)**: Routing problems to specialized expert models
- **Training Pipeline**: Continuous learning from feedback data
- **Image Processing**: Computer vision preprocessing and enhancement

**Technology Stack:**
- **Framework**: FastAPI for high-performance async API
- **ML Libraries**: PyTorch, Transformers, Hugging Face
- **OCR**: EasyOCR, Tesseract, Mathpix API integration
- **Image Processing**: OpenCV, Pillow, scikit-image
- **Model Serving**: TorchServe, custom inference engines
- **GPU Acceleration**: CUDA support for training and inference

**Service Communication:**
- **HTTP API**: Receives requests from .NET API service
- **Message Queue**: RabbitMQ for long-running ML tasks
- **Model Storage**: S3/Azure Blob for model artifacts
- **Results Cache**: Redis for inference result caching

#### 5.2.3 Docker Containerization

**Dockerfile for .NET Core API:**

```dockerfile
# .NET API Service Dockerfile
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
RUN dotnet publish "HomeworkSolver.API.csproj" -c Release -o /app/publish

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .

ENTRYPOINT ["dotnet", "HomeworkSolver.API.dll"]
```

**Dockerfile for Python ML Service:**

```dockerfile
# Python ML Service Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-vie \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create model directory
RUN mkdir -p /app/models

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV MODEL_PATH=/app/models
ENV CUDA_VISIBLE_DEVICES=0

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Docker Compose for Local Development:**

```yaml
# docker-compose.yml
version: '3.8'
services:
  # .NET API Service
  homework-solver-api:
    build:
      context: ./HomeworkSolver.API
      dockerfile: Dockerfile
    ports:
      - "5000:80"
      - "5001:443"
    environment:
      - ASPNETCORE_ENVIRONMENT=Development
      - ConnectionStrings__DefaultConnection=Server=mysql;Database=HomeworkSolver;Uid=root;Pwd=password123;
      - Redis__ConnectionString=redis:6379
      - MLService__BaseUrl=http://ml-service:8000
      - RabbitMQ__ConnectionString=amqp://admin:admin123@rabbitmq:5672/
    depends_on:
      - mysql
      - redis
      - rabbitmq
      - ml-service
    volumes:
      - ./logs/api:/app/logs
      - ./uploads:/app/uploads

  # Python ML Service
  ml-service:
    build:
      context: ./homework-solver-ml
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=mysql://root:password123@mysql/HomeworkSolver
      - REDIS_URL=redis://redis:6379
      - MODEL_CACHE_DIR=/app/models
      - RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
    depends_on:
      - mysql
      - redis
      - rabbitmq
    volumes:
      - ./models:/app/models
      - ./logs/ml:/app/logs
      - ./uploads:/app/uploads:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  # Database
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password123
      - MYSQL_DATABASE=HomeworkSolver
      - MYSQL_USER=homework_user
      - MYSQL_PASSWORD=homework_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    command: --default-authentication-plugin=mysql_native_password
  
  # Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  # Message Queue
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      - RABBITMQ_DEFAULT_USER=admin
      - RABBITMQ_DEFAULT_PASS=admin123
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

volumes:
  mysql_data:
  redis_data:
  rabbitmq_data:
```

#### 5.2.4 Kubernetes Production Environment

**Namespace and ConfigMap:**

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: homework-solver
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: homework-solver-config
  namespace: homework-solver
data:
  ASPNETCORE_ENVIRONMENT: "Production"
  Redis__ConnectionString: "redis-service:6379"
  RabbitMQ__HostName: "rabbitmq-service"
  LLM__UseLocalModel: "true"
  LLM__ModelPath: "/app/models/math-solver-model.onnx"
```

**Deployment Configuration:**

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: homework-solver-api
  namespace: homework-solver
  labels:
    app: homework-solver-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: homework-solver-api
  template:
    metadata:
      labels:
        app: homework-solver-api
    spec:
      containers:
      - name: api
        image: homework-solver/api:latest
        ports:
        - containerPort: 80
        envFrom:
        - configMapRef:
            name: homework-solver-config
        - secretRef:
            name: homework-solver-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: model-storage
          mountPath: /app/models
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 80
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: model-storage
        persistentVolumeClaim:
          claimName: llm-models-pvc
---
# k8s/api-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: homework-solver-api-service
  namespace: homework-solver
spec:
  selector:
    app: homework-solver-api
  ports:
    - protocol: TCP
      port: 80
      targetPort: 80
  type: ClusterIP
```

**Horizontal Pod Autoscaler:**

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: homework-solver-api-hpa
  namespace: homework-solver
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: homework-solver-api
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

**Ingress Configuration:**

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: homework-solver-ingress
  namespace: homework-solver
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.homework-solver.com
    secretName: homework-solver-tls
  rules:
  - host: api.homework-solver.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: homework-solver-api-service
            port:
              number: 80
```

**Persistent Volume for LLM Models:**

```yaml
# k8s/pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: llm-models-pvc
  namespace: homework-solver
spec:
  accessModes:
    - ReadOnlyMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: managed-premium
```

#### .NET Core Web API Architecture
```csharp
# Technology Stack
- Framework: ASP.NET Core 8.0 Web API
- Authentication: ASP.NET Core Identity, JWT Bearer
- Database ORM: Entity Framework Core 8.0
- HTTP Client: HttpClient with Polly for resilience
- Message Queue: RabbitMQ.Client for ML service communication
- Caching: StackExchange.Redis
- Email Service: SendGrid / AWS SES
- SMS Service: Twilio
- Monitoring: Application Insights, Serilog
- Containerization: Docker
- Orchestration: Kubernetes for production

# .NET API Project Structure
HomeworkSolver.API/
├── Controllers/
│   ├── AuthController.cs
│   ├── SolutionController.cs
│   ├── FeedbackController.cs
│   ├── UserController.cs
│   └── FileController.cs
├── Services/
│   ├── AuthService.cs
│   ├── UserService.cs
│   ├── FeedbackService.cs
│   ├── NotificationService.cs
│   └── MLServiceClient.cs          # HTTP client for Python ML service
├── Models/
│   ├── DTOs/
│   │   ├── SolutionRequestDto.cs
│   │   ├── SolutionResponseDto.cs
│   │   └── MLServiceDto.cs
│   ├── Entities/
│   │   ├── User.cs
│   │   ├── Problem.cs
│   │   ├── Solution.cs
│   │   ├── Feedback.cs
│   │   └── Analytics.cs
│   └── Requests/
├── Data/
│   ├── ApplicationDbContext.cs
│   ├── Repositories/
│   │   ├── UserRepository.cs
│   │   ├── SolutionRepository.cs
│   │   └── FeedbackRepository.cs
│   └── Migrations/
├── Core/
│   ├── Configuration/
│   ├── Security/
│   ├── Extensions/
│   └── Middleware/
├── Integration/
│   ├── MLServiceClient.cs          # Python ML service integration
│   ├── MessageQueue/
│   │   ├── MLTaskProducer.cs
│   │   └── MLTaskConsumer.cs
│   └── FileStorage/
└── Program.cs

# Python ML Service Project Structure
homework-solver-ml/
├── app/
│   ├── main.py                     # FastAPI application
│   ├── api/
│   │   ├── ocr.py                  # OCR endpoints
│   │   ├── solution.py             # Solution generation endpoints
│   │   ├── training.py             # Model training endpoints
│   │   └── models.py               # Model management endpoints
│   ├── core/
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── security.py
│   ├── services/
│   │   ├── ocr_service.py          # OCR processing logic
│   │   ├── llm_service.py          # LLM inference service
│   │   ├── moe_service.py          # Mixture of Experts routing
│   │   ├── training_service.py     # Model training service
│   │   └── image_processing.py     # Image preprocessing
│   ├── models/
│   │   ├── algebra_expert.py
│   │   ├── geometry_expert.py
│   │   ├── calculus_expert.py
│   │   └── base_expert.py
│   ├── ml/
│   │   ├── inference/
│   │   │   ├── model_loader.py
│   │   │   └── prediction_engine.py
│   │   ├── training/
│   │   │   ├── trainer.py
│   │   │   └── fine_tuner.py
│   │   └── preprocessing/
│   │       ├── image_enhancer.py
│   │       └── text_processor.py
│   └── utils/
│       ├── logger.py
│       ├── metrics.py
│       └── model_utils.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### 5.3 Database Schema

```sql
-- Users Table
CREATE TABLE users (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255),
    full_name VARCHAR(255) NOT NULL,
    grade_level INTEGER,
    school VARCHAR(255),
    avatar_url VARCHAR(500),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    role VARCHAR(50) DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    preferences JSON
);

-- Problems Table
CREATE TABLE problems (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id CHAR(36),
    category VARCHAR(100) NOT NULL,
    image_url VARCHAR(500),
    latex_input TEXT,
    ocr_confidence FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Solutions Table
CREATE TABLE solutions (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    problem_id CHAR(36),
    user_id CHAR(36),
    steps JSON NOT NULL,
    confidence FLOAT,
    model_version VARCHAR(50),
    processing_time INTEGER,
    language VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Feedback Table
CREATE TABLE feedback (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    solution_id CHAR(36),
    user_id CHAR(36),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    accuracy_feedback VARCHAR(50),
    clarity_ratings JSON,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES solutions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Comments Table
CREATE TABLE comments (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    solution_id CHAR(36),
    user_id CHAR(36),
    parent_id CHAR(36) NULL,
    content TEXT NOT NULL,
    step_number INTEGER,
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES solutions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
);

-- User Sessions Table
CREATE TABLE user_sessions (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    user_id CHAR(36),
    token VARCHAR(500) UNIQUE NOT NULL,
    device_info JSON,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Feedback Analytics Table
CREATE TABLE feedback_analytics (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    category VARCHAR(100),
    avg_rating FLOAT,
    total_feedback INTEGER,
    accuracy_stats JSON,
    common_issues JSON,
    date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.4 AI/ML Pipeline (Python Service)

#### Python ML Service Architecture

```python
# FastAPI ML Service - main.py
from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import uvicorn

from app.services.ocr_service import OCRService
from app.services.llm_service import LLMService
from app.services.moe_service import MixtureOfExpertsService
from app.services.training_service import TrainingService

app = FastAPI(title="Homework Solver ML Service", version="1.0.0")

# Initialize services
ocr_service = OCRService()
llm_service = LLMService()
moe_service = MixtureOfExpertsService()
training_service = TrainingService()

# Request/Response Models
class SolutionRequest(BaseModel):
    problem_text: Optional[str] = None
    image_base64: Optional[str] = None
    category: str
    difficulty_level: str
    language: str = "vi"
    user_preferences: Dict = {}

class SolutionResponse(BaseModel):
    solution_id: str
    steps: List[Dict]
    confidence: float
    category: str
    processing_time: float
    alternative_methods: List[Dict] = []

# ML Service Endpoints
@app.post("/api/ml/solve", response_model=SolutionResponse)
async def solve_problem(request: SolutionRequest):
    """Main endpoint for solving mathematical problems"""
    
    # Step 1: OCR processing if image provided
    if request.image_base64:
        ocr_result = await ocr_service.process_image(
            request.image_base64,
            language=request.language
        )
        problem_text = ocr_result.text
        latex_input = ocr_result.latex
    else:
        problem_text = request.problem_text
        latex_input = request.problem_text
    
    # Step 2: Route to appropriate expert via MoE
    expert_selection = await moe_service.route_problem(
        problem_text=problem_text,
        latex_input=latex_input,
        category=request.category,
        difficulty=request.difficulty_level
    )
    
    # Step 3: Generate solution using selected expert
    solution = await expert_selection.expert.solve(
        problem_text=problem_text,
        latex_input=latex_input,
        language=request.language,
        user_preferences=request.user_preferences
    )
    
    return SolutionResponse(
        solution_id=solution.id,
        steps=solution.steps,
        confidence=solution.confidence,
        category=request.category,
        processing_time=solution.processing_time,
        alternative_methods=solution.alternatives
    )

@app.post("/api/ml/ocr")
async def process_ocr(file: UploadFile = File(...), language: str = "vi"):
    """Dedicated OCR processing endpoint"""
    image_bytes = await file.read()
    result = await ocr_service.process_image_bytes(image_bytes, language)
    return {
        "text": result.text,
        "latex": result.latex,
        "confidence": result.confidence,
        "detected_language": result.detected_language
    }

@app.post("/api/ml/train")
async def trigger_training(background_tasks: BackgroundTasks):
    """Trigger model retraining based on feedback"""
    background_tasks.add_task(training_service.start_training_pipeline)
    return {"message": "Training pipeline started", "status": "queued"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=4)
```

#### Mixture of Experts Implementation

```python
# services/moe_service.py
from typing import Dict, List
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel

from app.models.algebra_expert import AlgebraExpert
from app.models.geometry_expert import GeometryExpert
from app.models.calculus_expert import CalculusExpert
from app.ml.inference.model_loader import ModelLoader

class MixtureOfExpertsService:
    def __init__(self):
        self.experts = {
            'algebra': AlgebraExpert(),
            'geometry': GeometryExpert(),
            'calculus': CalculusExpert(),
            'trigonometry': TrigonometryExpert(),
            'probability': ProbabilityExpert(),
            'complex_numbers': ComplexNumbersExpert()
        }
        
        # Load routing model for expert selection
        self.routing_model = ModelLoader.load_routing_model()
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")
        
    async def route_problem(self, 
                          problem_text: str,
                          latex_input: str, 
                          category: str,
                          difficulty: str) -> ExpertSelection:
        """Route problem to appropriate expert(s)"""
        
        # Extract features for routing
        features = await self._extract_features(problem_text, latex_input)
        
        # Get expert scores from routing model
        expert_scores = await self._score_experts(features, category, difficulty)
        
        # Select primary expert
        primary_expert_name = max(expert_scores.items(), key=lambda x: x[1])[0]
        primary_expert = self.experts[primary_expert_name]
        
        # Check if multi-expert approach is needed
        selected_experts = [primary_expert]
        if self._needs_multiple_experts(expert_scores, features):
            # Select top 2-3 experts for ensemble approach
            top_experts = sorted(expert_scores.items(), 
                               key=lambda x: x[1], 
                               reverse=True)[:3]
            selected_experts = [self.experts[name] for name, _ in top_experts]
        
        return ExpertSelection(
            primary=primary_expert,
            experts=selected_experts,
            scores=expert_scores,
            routing_confidence=max(expert_scores.values())
        )
    
    async def _extract_features(self, text: str, latex: str) -> Dict:
        """Extract features for expert routing"""
        # Tokenize and encode text
        inputs = self.tokenizer(text, return_tensors="pt", 
                               truncation=True, max_length=512)
        
        # Mathematical feature extraction
        features = {
            'has_integration': '\\int' in latex,
            'has_derivatives': '\\frac{d' in latex,
            'has_matrices': '\\begin{matrix}' in latex,
            'has_geometry_terms': any(term in text.lower() 
                                    for term in ['triangle', 'circle', 'angle']),
            'has_algebra_terms': any(term in text.lower() 
                                   for term in ['equation', 'solve', 'variable']),
            'complexity_score': self._calculate_complexity(latex),
            'text_length': len(text),
            'latex_length': len(latex)
        }
        
        return features
    
    def _calculate_complexity(self, latex: str) -> float:
        """Calculate problem complexity score"""
        complexity_indicators = [
            ('\\frac', 0.2),      # Fractions
            ('\\sqrt', 0.3),      # Square roots
            ('\\int', 0.5),       # Integration
            ('\\sum', 0.4),       # Summation
            ('\\prod', 0.4),      # Product
            ('\\lim', 0.6),       # Limits
            ('^{', 0.2),          # Exponents
            ('\\sin', 0.3),       # Trigonometric functions
            ('\\log', 0.3),       # Logarithms
        ]
        
        score = 0.0
        for indicator, weight in complexity_indicators:
            count = latex.count(indicator)
            score += count * weight
        
        # Normalize to 0-1 range
        return min(score / 10.0, 1.0)
```

#### Individual Expert Implementation

```python
# models/algebra_expert.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Dict
import sympy as sp
from sympy import symbols, solve, expand, factor, simplify

from app.models.base_expert import BaseExpert
from app.utils.vietnamese_adapter import VietnameseAdapter

class AlgebraExpert(BaseExpert):
    """Expert model specialized for algebra problems"""
    
    def __init__(self):
        super().__init__()
        self.model_name = "microsoft/Phi-3-mini-4k-instruct"
        self.model = None
        self.tokenizer = None
        self.vietnamese_adapter = VietnameseAdapter()
        self.load_model()
    
    def load_model(self):
        """Load the fine-tuned algebra model"""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True
        )
    
    async def solve(self, 
                   problem_text: str,
                   latex_input: str,
                   language: str = "vi",
                   user_preferences: Dict = {}) -> AlgebraSolution:
        """Solve algebra problem with step-by-step explanation"""
        
        # Step 1: Analyze problem type
        analysis = await self._analyze_problem(problem_text, latex_input)
        
        # Step 2: Generate solution approach
        approach = await self._generate_approach(analysis)
        
        # Step 3: Solve using symbolic computation + LLM
        steps = []
        if analysis.problem_type in ['linear_equation', 'quadratic_equation']:
            # Use SymPy for symbolic solving
            steps = await self._solve_symbolically(latex_input, approach)
        else:
            # Use LLM for complex problems
            steps = await self._solve_with_llm(problem_text, approach)
        
        # Step 4: Verify solution
        verification = await self._verify_solution(latex_input, steps)
        
        # Step 5: Generate explanations
        explanations = await self._generate_explanations(
            steps, language, user_preferences
        )
        
        # Step 6: Find alternative methods
        alternatives = await self._find_alternatives(
            problem_text, latex_input, steps
        )
        
        return AlgebraSolution(
            steps=steps,
            explanations=explanations,
            verification=verification,
            alternatives=alternatives,
            confidence=self._calculate_confidence(analysis, verification),
            processing_time=self.processing_time
        )
    
    async def _solve_symbolically(self, latex: str, approach: Dict) -> List[Dict]:
        """Solve using SymPy symbolic computation"""
        steps = []
        
        try:
            # Convert LaTeX to SymPy expression
            expr = sp.latex2sympy(latex)
            
            # Extract variables
            variables = list(expr.free_symbols)
            
            if approach['method'] == 'factoring':
                # Factor the expression
                factored = sp.factor(expr)
                steps.append({
                    'step_type': 'factoring',
                    'input': str(expr),
                    'output': str(factored),
                    'explanation': 'Factor the expression'
                })
                
                # Solve factored equation
                if variables:
                    solutions = sp.solve(factored, variables[0])
                    steps.append({
                        'step_type': 'solving',
                        'input': str(factored),
                        'output': f'{variables[0]} = {solutions}',
                        'explanation': 'Solve for the variable'
                    })
            
            elif approach['method'] == 'quadratic_formula':
                # Apply quadratic formula
                if variables:
                    solutions = sp.solve(expr, variables[0])
                    steps.append({
                        'step_type': 'quadratic_formula',
                        'input': str(expr),
                        'output': f'{variables[0]} = {solutions}',
                        'explanation': 'Apply quadratic formula'
                    })
            
        except Exception as e:
            # Fallback to LLM if symbolic solving fails
            steps = await self._solve_with_llm_fallback(latex, approach)
        
        return steps
    
    async def _solve_with_llm(self, problem: str, approach: Dict) -> List[Dict]:
        """Solve using LLM when symbolic methods aren't sufficient"""
        
        prompt = f"""Solve this algebra problem step by step:
        
        Problem: {problem}
        Approach: {approach['description']}
        
        Provide a detailed solution with clear steps. Format each step as:
        Step X: [operation] -> [result]
        Explanation: [why this step is needed]
        
        Steps:"""
        
        inputs = self.tokenizer.encode(prompt, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=1000,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        solution_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Parse the generated solution into structured steps
        steps = self._parse_llm_solution(solution_text)
        
        return steps
```

### 5.3 .NET API ↔ Python ML Service Integration

#### .NET ML Service Client

```csharp
// Services/MLServiceClient.cs
public interface IMLServiceClient
{
    Task<SolutionResponseDto> SolveProblemAsync(SolutionRequestDto request);
    Task<OCRResultDto> ProcessOCRAsync(byte[] imageBytes, string language = "vi");
    Task<bool> TriggerModelTrainingAsync();
    Task<ModelHealthDto> CheckHealthAsync();
}

public class MLServiceClient : IMLServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly IConfiguration _configuration;
    private readonly ILogger<MLServiceClient> _logger;
    private readonly IMessageProducer _messageProducer;
    
    public MLServiceClient(
        HttpClient httpClient,
        IConfiguration configuration,
        ILogger<MLServiceClient> logger,
        IMessageProducer messageProducer)
    {
        _httpClient = httpClient;
        _configuration = configuration;
        _logger = logger;
        _messageProducer = messageProducer;
        
        _httpClient.BaseAddress = new Uri(_configuration["MLService:BaseUrl"]);
        _httpClient.Timeout = TimeSpan.FromSeconds(30);
    }
    
    public async Task<SolutionResponseDto> SolveProblemAsync(SolutionRequestDto request)
    {
        try
        {
            _logger.LogInformation("Sending solution request to ML service for category: {Category}", request.Category);
            
            var response = await _httpClient.PostAsJsonAsync("/api/ml/solve", request);
            response.EnsureSuccessStatusCode();
            
            var result = await response.Content.ReadFromJsonAsync<SolutionResponseDto>();
            
            _logger.LogInformation("Received solution from ML service with confidence: {Confidence}", result.Confidence);
            
            return result;
        }
        catch (HttpRequestException ex)
        {
            _logger.LogError(ex, "HTTP error calling ML service");
            
            // Fallback: Queue the request for later processing
            await _messageProducer.PublishAsync("ml.solve.retry", request);
            
            throw new MLServiceException("ML service temporarily unavailable", ex);
        }
        catch (TaskCanceledException ex) when (ex.CancellationToken.IsCancellationRequested)
        {
            _logger.LogWarning("ML service request timed out");
            throw new MLServiceTimeoutException("ML service request timed out", ex);
        }
    }
}
```

#### Service Communication Patterns

**Synchronous Communication (HTTP/REST):**
- Real-time problem solving requests
- OCR processing for immediate response
- Health checks and status monitoring

**Asynchronous Communication (Message Queue):**
- Long-running training tasks
- Batch feedback processing
- Retry mechanisms for failed requests
- Model deployment notifications

**Data Flow:**
```
1. Mobile App → .NET API (Authentication + Validation)
2. .NET API → Python ML Service (Problem Solving)
3. Python ML Service → .NET API (Solution Response)
4. .NET API → Database (Persist Results)
5. .NET API → Mobile App (Final Response)
```
```

## 6. API Specification

### 6.1 Authentication Endpoints

```yaml
POST /api/v1/auth/register
  Request:
    - email: string
    - password: string
    - full_name: string
    - grade_level: integer
    - phone: string (optional)
  Response:
    - user_id: uuid
    - verification_required: boolean
    - token: string (if email verification disabled)

POST /api/v1/auth/login
  Request:
    - email_or_phone: string
    - password: string
    - device_info: object
  Response:
    - access_token: string
    - refresh_token: string
    - user: UserProfile

POST /api/v1/auth/refresh
  Request:
    - refresh_token: string
  Response:
    - access_token: string
    - refresh_token: string

POST /api/v1/auth/logout
  Request:
    - refresh_token: string
  Response:
    - success: boolean

POST /api/v1/auth/forgot-password
  Request:
    - email_or_phone: string
  Response:
    - reset_link_sent: boolean

GET /api/v1/auth/verify-email/{token}
  Response:
    - verified: boolean
    - user_id: uuid
```

### 6.2 Solution & Feedback Endpoints

```yaml
POST /api/v1/solve
  Headers:
    - Authorization: Bearer {token}
  Request:
    - image: base64_encoded_string
    - category: string
    - language: string (vi/en)
    - user_level: string (optional)
  Response:
    - solution_id: uuid
    - latex_input: string
    - steps: array
    - confidence: float
    - alternative_methods: array

POST /api/v1/feedback/rating
  Headers:
    - Authorization: Bearer {token}
  Request:
    - solution_id: uuid
    - rating: integer (1-5)
    - accuracy: string (correct/partial/incorrect)
    - clarity_ratings: object
  Response:
    - feedback_id: uuid
    - points_earned: integer

POST /api/v1/feedback/comment
  Headers:
    - Authorization: Bearer {token}
  Request:
    - solution_id: uuid
    - content: string
    - step_number: integer (optional)
    - parent_id: uuid (optional)
  Response:
    - comment_id: uuid
    - comment: CommentObject

GET /api/v1/feedback/solution/{solution_id}
  Response:
    - average_rating: float
    - total_ratings: integer
    - comments: array
    - accuracy_stats: object

POST /api/v1/feedback/report-error
  Headers:
    - Authorization: Bearer {token}
  Request:
    - solution_id: uuid
    - error_type: string
    - description: string
    - suggested_correction: string (optional)
  Response:
    - report_id: uuid
    - status: string
```

### 6.3 User Profile Endpoints

```yaml
GET /api/v1/users/profile
  Headers:
    - Authorization: Bearer {token}
  Response:
    - user: UserProfile
    - statistics: UserStats
    - achievements: array

PUT /api/v1/users/profile
  Headers:
    - Authorization: Bearer {token}
  Request:
    - full_name: string (optional)
    - grade_level: integer (optional)
    - preferences: object (optional)
  Response:
    - user: UpdatedUserProfile

GET /api/v1/users/history
  Headers:
    - Authorization: Bearer {token}
  Query:
    - page: integer
    - limit: integer
    - category: string (optional)
  Response:
    - problems: array
    - total: integer
    - page_info: object

GET /api/v1/users/analytics
  Headers:
    - Authorization: Bearer {token}
  Response:
    - accuracy_by_category: object
    - improvement_trends: array
    - weak_areas: array
    - study_time: object
```

### 6.4 WebSocket for Real-time Features

```javascript
// Real-time solution updates
ws://api.example.com/ws/solution/{session_id}

// Real-time comments and feedback
ws://api.example.com/ws/feedback/{solution_id}

// Study group collaboration
ws://api.example.com/ws/group/{group_id}
```

## 7. Security & Privacy

### 7.1 Authentication Security
- **Password Policy**: Minimum 8 characters, complexity requirements
- **Session Management**: JWT with 15-minute access token, 30-day refresh token
- **Multi-factor Authentication**: Optional SMS/Email OTP
- **Account Recovery**: Secure password reset with time-limited tokens
- **Rate Limiting**: Max 5 login attempts per 15 minutes

### 7.2 Data Protection
- **Encryption**: TLS 1.3 for transit, AES-256 for storage
- **PII Protection**: Anonymization of personal data in analytics
- **Data Retention**: User data retained for 2 years after last activity
- **GDPR Compliance**: Right to deletion, data portability
- **Minor Protection**: Special handling for users under 18

### 7.3 Content Moderation
- **Automated Filtering**: Inappropriate content detection
- **Manual Review**: Flagged content review within 24 hours
- **User Blocking**: Ability to block/report users
- **Teacher Verification**: Verified badge system

## 8. Monitoring & Analytics

### 8.1 System Monitoring
- **Performance Metrics**: Response time, error rates, uptime
- **User Analytics**: DAU, MAU, retention, engagement
- **Feedback Analytics**: Rating trends, common issues
- **Model Performance**: Accuracy by category, confidence scores

### 8.2 User Behavior Analytics
- **Learning Patterns**: Study time, problem-solving speed
- **Progress Tracking**: Improvement over time
- **Feature Usage**: Most/least used features
- **Drop-off Points**: Where users abandon tasks

## 9. Development Phases

### Phase 1: Foundation (3 months)
- User authentication system
- Basic photo capture and OCR
- Single LLM model for all math types
- Core categories (Algebra, Geometry)
- Simple rating system

### Phase 2: Enhanced Features (2 months)
- Complete feedback system
- User profiles and history
- Implement MoE architecture
- Vietnamese fine-tuning
- Social login integration

### Phase 3: Community & Analytics (2 months)
- Comment system
- Community features
- Feedback analytics dashboard
- Practice mode
- Progress tracking

### Phase 4: Advanced Features (2 months)
- Exam preparation
- Study groups
- Parent/Teacher portals
- Advanced analytics
- Gamification elements

### Phase 5: Scale & Optimize (1 month)
- Performance optimization
- Load testing
- Security audit
- A/B testing framework
- Market launch preparation

## 10. Success Metrics & KPIs

### 10.1 User Engagement
- **Target**: 70% of users create accounts
- **Daily Active Users**: 5,000 by month 3
- **Session Duration**: Average 15 minutes
- **Problems Solved per User**: 10+ per week

### 10.2 Feedback Metrics
- **Feedback Rate**: 30% of solutions rated
- **Average Rating**: 4.2+ stars
- **Comment Participation**: 10% of users
- **Error Report Resolution**: < 48 hours

### 10.3 Learning Outcomes
- **Accuracy Improvement**: 15% after 1 month of use
- **Exam Score Improvement**: 10% average increase
- **Concept Understanding**: 80% report better understanding

## 11. Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low user registration rate | High | Offer limited free tier without account |
| Poor feedback quality | High | Implement quality scoring and incentives |
| Privacy concerns | High | Clear privacy policy, parental controls |
| Spam/Abuse in comments | Medium | Automated moderation, user reporting |
| Authentication failures | High | Multiple auth methods, quick recovery |
| Feedback manipulation | Medium | Rate limiting, duplicate detection |
| Data breaches | Critical | Security audits, encryption, compliance |

## 12. Compliance & Legal

### 12.1 Regulatory Compliance
- **COPPA/GDPR**: Age verification, parental consent for minors
- **Data Protection**: Vietnamese Personal Data Protection Decree
- **Educational Standards**: Ministry of Education guidelines
- **Content Guidelines**: Age-appropriate content filters

### 12.2 Terms of Service
- User responsibilities
- Acceptable use policy
- Intellectual property rights
- Limitation of liability
- Privacy policy

## 13. Monetization Strategy

### 13.1 Freemium Model
- **Free Tier**: 10 problems/day, basic features
- **Premium**: Unlimited problems, all features
- **Family Plan**: Multiple student accounts
- **School License**: Bulk pricing for institutions

### 13.2 Pricing
- **Individual**: $4.99/month or $39.99/year
- **Family**: $9.99/month (up to 4 students)
- **School**: Custom pricing based on volume

## 14. Appendices

### A. Competitor Analysis with Feedback Systems
- **Photomath**: Basic thumbs up/down
- **Mathway**: No feedback system
- **Our Differentiation**: Comprehensive feedback driving continuous improvement

### B. Feedback Loop Architecture
```
User Feedback → Analytics Engine → Pattern Recognition 
     ↓                                      ↓
Quality Metrics ← Model Retraining ← Training Data Generation
```

### C. User Journey Maps
1. **New User Journey**: Discovery → Sign Up → Onboarding → First Problem → Feedback
2. **Returning User Journey**: Login → History → New Problem → Community Interaction
3. **Power User Journey**: Advanced Features → Study Groups → Contribution → Rewards

---

**Document Version**: 2.0
**Last Updated**: December 2024
**Author**: AI Homework Solver Team
**Status**: Enhanced with Authentication & Feedback Systems
**Change Log**: Added comprehensive feedback system, user authentication, and community features