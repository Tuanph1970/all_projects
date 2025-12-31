# Mathematics Mobile Application

A comprehensive mathematics problem-solving mobile application that leverages AI and ML technologies to help high school students solve mathematical problems through image capture and step-by-step solutions.

## 🏗️ Architecture Overview

The system consists of three main components:

- **Frontend**: React Native mobile application (iOS/Android)
- **Backend**: .NET Core 8.0 Web API service with Clean Architecture
- **ML Service**: Python-based AI/ML microservice with OCR and LLM capabilities

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  React Native   │    │   .NET Core 8    │    │   Python ML     │
│  Mobile App     │◄──►│    Web API       │◄──►│   OCR Service   │
│  (TypeScript)   │    │ (Clean Arch)     │    │   (FastAPI)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  │
                    ┌─────────────────────────┐
                    │     Infrastructure      │
                    │  MySQL + Redis + Docker │
                    └─────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **Node.js 18+** and **npm** (for frontend development)
- **.NET 8 SDK** (for backend development)
- **Python 3.11+** (for ML service development)
- **Android Studio** or **Xcode** (for mobile development)

### Option 1: Docker Development (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd mathematic-mobile
   ```

2. **Start all services with Docker**
   ```bash
   # Development mode with Expo Go support (Recommended)
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

   # Or just backend services (run Expo locally)
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend-api llm-service mysql redis
   
   # Production-like mode
   docker-compose up
   ```

3. **Access the services**
   - Backend API: http://localhost:8001
   - ML Service: http://localhost:8002
   - API Documentation: http://localhost:8001/swagger
   - ML Documentation: http://localhost:8002/docs
   - Expo Dev Tools: http://localhost:19002 (when running locally)

4. **Connect mobile app**
   - Install Expo Go on your mobile device
   - Scan QR code from Expo development server or terminal
   - App will load automatically on your device

### Option 2: Manual Setup

See individual setup guides in each service directory:
- [Frontend Setup](./frontend/README.md)
- [Backend Setup](./backend/README.md)
- [ML Service Setup](./llmOCR/README.md)

## 📱 Mobile Development with Expo Go

### Expo Setup (Recommended)

1. **Install Expo Go on your mobile device**
   - iOS: [Download from App Store](https://apps.apple.com/app/expo-go/id982107779)
   - Android: [Download from Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent)

2. **Install dependencies and start development server**
   ```bash
   cd frontend
   npm install
   npx expo start --dev-client
   ```

3. **Connect to your app**
   - Scan the QR code with Expo Go app on your device
   - Ensure both your device and computer are on the same WiFi network
   - The app will load automatically

### Alternative: Native Development

For full native development capabilities:

1. **Android Development**
   ```bash
   # Install Android dependencies first
   cd frontend
   npm run android
   ```

2. **iOS Development** (macOS only)
   ```bash
   # Install iOS dependencies first
   cd ios && pod install && cd ..
   npm run ios
   ```

### Environment Configuration

Create `.env` files in each service directory:

**Frontend (.env)**
```
# For development with Expo Go
EXPO_PUBLIC_API_BASE_URL=http://YOUR_IP_ADDRESS:8001/api
EXPO_PUBLIC_API_TIMEOUT=10000
EXPO_PUBLIC_ENV=development

# Replace YOUR_IP_ADDRESS with your machine's local IP address
# For Android emulator: use 10.0.2.2 instead of localhost
# For iOS simulator: use localhost or your machine's IP
```

**Backend (.env)**
```
ConnectionStrings__DefaultConnection=Server=localhost;Database=mathematics_solver;User=sa;Password=YourPassword123;
ConnectionStrings__Redis=localhost:6379
JWT__SecretKey=your-super-secret-jwt-key-here
ML__ServiceUrl=http://localhost:8002
```

**ML Service (.env)**
```
SECRET_KEY=your-super-secret-key-here
REDIS_URL=redis://localhost:6379/0
BACKEND_API_URL=http://localhost:8001/api
ML_DEVICE=cpu
LOG_LEVEL=INFO
```

## 🧪 Testing

### Running Tests

```bash
# Frontend tests
cd frontend && npm test

# Backend tests
cd backend && dotnet test

# ML Service tests
cd llmOCR && python -m pytest
```

### Test Coverage

```bash
# Frontend coverage
cd frontend && npm run test:coverage

# Backend coverage
cd backend && dotnet test --collect:"XPlat Code Coverage"

# ML Service coverage
cd llmOCR && python -m pytest --cov=src --cov-report=html
```

## 🔧 Development Workflow

### Git Workflow

1. **Create feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes and commit**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

3. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Quality

We use automated code formatting and linting:

```bash
# Frontend (ESLint + Prettier)
cd frontend
npm run lint
npm run lint:fix

# Backend (EditorConfig + StyleCop)
cd backend
dotnet format

# ML Service (Black + isort + flake8)
cd llmOCR
black src/
isort src/
flake8 src/
```

## 📊 Monitoring & Debugging

### Development Tools

- **API Documentation**: http://localhost:8001/swagger (Backend)
- **ML API Documentation**: http://localhost:8002/docs (ML Service)
- **Database**: MySQL on port 3306
- **Cache**: Redis on port 6379

### Logging

Logs are structured and available in:
- Backend: `/app/logs` (in container) or `./backend/logs` (host)
- ML Service: `/app/logs` (in container) or `./llmOCR/logs` (host)

### Performance Monitoring

Optional Prometheus + Grafana stack:

```bash
# Start with monitoring
docker-compose --profile monitoring up
```

Access Grafana at http://localhost:3000 (admin/admin123)

## 🔐 Security

### Authentication Flow

1. User registers/logs in through mobile app
2. Backend generates JWT token
3. Mobile app stores token securely
4. API requests include Bearer token
5. Backend validates token and authorizes requests

### API Security

- JWT Bearer authentication
- HTTPS in production
- CORS configured for allowed origins
- Rate limiting on API endpoints
- Input validation and sanitization

### ML Service Security

- API key authentication for external calls
- Input size and type validation
- Secure model file handling
- No sensitive data in logs

## 🚀 Deployment

### Production Deployment

1. **Build production images**
   ```bash
   docker-compose -f docker-compose.yml build
   ```

2. **Deploy to production**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### Environment Variables

Set these in your production environment:
- `JWT__SecretKey`: Strong secret key for JWT signing
- `ConnectionStrings__DefaultConnection`: Production database connection
- `ML__ServiceUrl`: Production ML service URL
- `CORS__AllowedOrigins`: Production domain origins

## 📚 API Documentation

### Backend API

Once running, visit:
- Swagger UI: http://localhost:8001/swagger
- OpenAPI spec: http://localhost:8001/swagger/v1/swagger.json

### Key Endpoints

- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `POST /api/problems/solve` - Submit problem for solving
- `GET /api/problems` - Get user's problems
- `GET /api/solutions/{id}` - Get solution details

### ML Service API

Once running, visit:
- FastAPI docs: http://localhost:8002/docs
- OpenAPI spec: http://localhost:8002/openapi.json

### Key Endpoints

- `POST /ocr` - Extract text from mathematical images
- `POST /solve` - Generate step-by-step solutions
- `GET /models` - List available ML models
- `GET /health` - Service health check

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests for your changes**
5. **Ensure all tests pass**
6. **Submit a pull request**

### Development Guidelines

- Follow existing code style and patterns
- Write meaningful commit messages
- Add tests for new functionality
- Update documentation as needed
- Ensure Docker builds work correctly

## 📋 Project Status

### Phase 1: MVP Development (Current)
- [x] Project setup and infrastructure
- [x] Basic authentication system
- [x] OCR processing pipeline
- [x] Problem submission workflow
- [x] Solution display interface
- [ ] Testing and quality assurance
- [ ] MVP deployment

### Phase 2: Enhanced Features
- [ ] Advanced ML capabilities
- [ ] Real-time chat assistance
- [ ] Performance optimization
- [ ] Advanced UI/UX features

## 🐛 Troubleshooting

### Common Issues

**Docker services won't start:**
```bash
# Clear Docker cache
docker system prune -a
docker-compose down -v
docker-compose up --build
```

**Mobile app can't connect to API:**
- Check API_BASE_URL in frontend/.env
- For Android emulator, use `10.0.2.2` instead of `localhost`
- For iOS simulator, use `localhost` or your machine's IP

**ML Service out of memory:**
- Reduce `ML_BATCH_SIZE` in environment
- Switch to `ML_DEVICE=cpu` if using GPU
- Increase Docker memory limits

### Getting Help

- Check the [Issues](link-to-issues) page for known problems
- Review individual service README files
- Join our [Discord/Slack](link-to-chat) for community support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- TrOCR for mathematical OCR capabilities
- FastAPI for the ML service framework
- .NET Core team for the backend framework
- React Native community for mobile development tools

---

For detailed setup instructions for each component, please refer to the individual README files in each service directory.