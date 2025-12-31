# Development Setup Guide

This guide provides step-by-step instructions for setting up the Mathematics Mobile Application development environment.

## 📋 Prerequisites

### System Requirements

- **Operating System**: macOS, Windows 10+, or Ubuntu 20.04+
- **Memory**: Minimum 8GB RAM (16GB recommended for ML development)
- **Storage**: At least 10GB free space
- **Network**: Stable internet connection for downloading dependencies

### Required Software

1. **Docker & Docker Compose**
   - [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows/Mac
   - Docker Engine + Docker Compose for Linux
   - Minimum version: Docker 24.0+, Compose 2.0+

2. **Git**
   - [Git](https://git-scm.com/downloads) for version control
   - Configure with your GitHub credentials

3. **Node.js & npm** (for React Native development)
   - [Node.js 18+](https://nodejs.org/en/download/)
   - npm comes bundled with Node.js

4. **.NET 8 SDK** (for backend development)
   - [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)

5. **Python 3.11+** (for ML service development)
   - [Python 3.11](https://www.python.org/downloads/)
   - pip package manager

### Mobile Development Tools

**Expo Go SDK 5.3 (Recommended for Mobile Testing):**
- [Expo Go app](https://expo.dev/client) on your iOS/Android device
- [Expo CLI](https://docs.expo.dev/workflow/expo-cli/) installed globally
- Compatible with Expo SDK 51+ and React Native 0.74+

**For Android Development:**
- [Android Studio](https://developer.android.com/studio)
- Android SDK (API level 31+)
- Java Development Kit (JDK 11+)
- Android emulator or physical device

**For iOS Development (macOS only):**
- [Xcode 14+](https://developer.apple.com/xcode/)
- iOS Simulator
- Apple Developer Account (for device testing)

**Expo CLI Installation:**
```bash
npm install -g @expo/cli@latest
```

## 🚀 Setup Methods

Choose one of the following setup methods based on your preference:

### Method 1: Docker Development (Recommended)

This method uses Docker containers for all services, providing a consistent development environment.

#### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/mathematic-mobile.git
cd mathematic-mobile
```

#### Step 2: Environment Configuration

Create environment files for each service:

**Root .env file:**
```bash
cp .env.example .env
```

Edit the `.env` file:
```env
# Database
MYSQL_ROOT_PASSWORD=rootpassword
MYSQL_DATABASE=mathematics_solver
MYSQL_USER=mathsolver
MYSQL_PASSWORD=password123

# Redis
REDIS_PASSWORD=

# Backend API
JWT_SECRET_KEY=your-super-secret-jwt-key-minimum-32-characters
BACKEND_API_PORT=8001

# ML Service  
ML_SERVICE_PORT=8002
ML_DEVICE=cpu
OPENAI_API_KEY=your-openai-api-key-optional

# Frontend
FRONTEND_METRO_PORT=8081
```

#### Step 3: Build and Start Services

**For Expo Go Development (Recommended):**
```bash
# Start all services including Expo development server
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or run in background
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

**Alternative - Backend Services Only:**
```bash
# Start only backend services (if you want to run Expo locally)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build backend-api llm-service mysql redis

# Run Expo development server locally
cd frontend
npm install
npx expo start --dev-client
```

#### Step 4: Verify Services

Wait for all services to start (2-3 minutes), then verify:

```bash
# Check service status
docker-compose ps

# Check logs if needed
docker-compose logs backend-api
docker-compose logs llm-service
```

Access the services:
- Backend API: http://localhost:8001/health
- ML Service: http://localhost:8002/health  
- API Documentation: http://localhost:8001/swagger
- ML Documentation: http://localhost:8002/docs
- Expo Dev Tools: http://localhost:19002 (when running locally)

#### Step 5: Connect with Expo Go

**Install Expo Go on your mobile device:**
- iOS: [Download from App Store](https://apps.apple.com/app/expo-go/id982107779)
- Android: [Download from Google Play](https://play.google.com/store/apps/details?id=host.exp.exponent)

**Connect to your development server:**

1. **Same WiFi Network (Recommended):**
   - Ensure your mobile device and development machine are on the same WiFi network
   - Open Expo Go app on your device
   - Scan the QR code from the Expo development server terminal or web interface
   - The app will load automatically

2. **Different Networks/Tunnel Mode:**
   ```bash
   # If you're running Expo locally (not in Docker)
   cd frontend
   npx expo start --tunnel
   
   # Scan the QR code with Expo Go app
   ```

3. **Manual Connection:**
   - Open Expo Go app
   - Enter your development server URL manually: `exp://YOUR_IP_ADDRESS:19000`
   - Replace YOUR_IP_ADDRESS with your machine's local IP

**Finding your IP address:**
```bash
# On macOS/Linux
ifconfig | grep "inet " | grep -v 127.0.0.1

# On Windows
ipconfig | findstr "IPv4"
```

### Method 2: Manual Development Setup

This method installs and runs each service directly on your machine.

#### Step 1: Clone and Setup Repository

```bash
git clone https://github.com/your-org/mathematic-mobile.git
cd mathematic-mobile
```

#### Step 2: Database Setup (MySQL & Redis)

**Option A: Using Docker for databases only**
```bash
docker run -d --name mysql-dev \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=mathematics_solver \
  -e MYSQL_USER=mathsolver \
  -e MYSQL_PASSWORD=password123 \
  -p 3306:3306 mysql:8.0

docker run -d --name redis-dev \
  -p 6379:6379 redis:7-alpine
```

**Option B: Local installation**
- Install MySQL 8.0 locally and create database
- Install Redis locally

#### Step 3: Backend Setup (.NET Core 8.0)

```bash
cd backend

# Restore NuGet packages
dotnet restore

# Update database
dotnet ef database update -p src/Infrastructure -s src/Presentation

# Run in development mode
dotnet run --project src/Presentation/MathematicsSolver.WebAPI.csproj
```

Backend will be available at: http://localhost:8001

#### Step 4: ML Service Setup (Python)

```bash
cd llmOCR

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download initial ML models
python scripts/download_models.py

# Start the service
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8002 --reload
```

ML Service will be available at: http://localhost:8002

#### Step 5: Frontend Setup (React Native)

```bash
cd frontend

# Install dependencies
npm install

# For iOS (macOS only)
cd ios && pod install && cd ..

# Start Metro bundler
npm start
```

Metro bundler will be available at: http://localhost:8081

## 📱 Mobile App Development

### Android Setup

1. **Install Android Studio**
   - Download from [Android Studio](https://developer.android.com/studio)
   - Install Android SDK (API level 31+)
   - Create virtual device (AVD)

2. **Configure Environment Variables**
   ```bash
   # Add to your shell profile (.bashrc, .zshrc, etc.)
   export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS
   export ANDROID_HOME=$HOME/Android/Sdk          # Linux
   export PATH=$PATH:$ANDROID_HOME/emulator
   export PATH=$PATH:$ANDROID_HOME/tools
   export PATH=$PATH:$ANDROID_HOME/tools/bin
   export PATH=$PATH:$ANDROID_HOME/platform-tools
   ```

3. **Run Android App**
   ```bash
   cd frontend
   
   # Start emulator or connect device
   npm run android
   ```

### iOS Setup (macOS only)

1. **Install Xcode**
   - Download from Mac App Store
   - Install command line tools: `xcode-select --install`

2. **Install CocoaPods**
   ```bash
   sudo gem install cocoapods
   cd frontend/ios && pod install
   ```

3. **Run iOS App**
   ```bash
   cd frontend
   npm run ios
   ```

## 🔧 Development Tools

### Recommended VS Code Extensions

```json
{
  "recommendations": [
    "ms-dotnettools.csharp",
    "ms-python.python",
    "ms-vscode.vscode-typescript-next",
    "msjsdiag.vscode-react-native",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.vscode-json"
  ]
}
```

### Database Management Tools

- **MySQL Workbench** or **DBeaver** for MySQL
- **Redis Desktop Manager** or **RedisInsight** for Redis
- **Postman** or **Insomnia** for API testing

## 🧪 Testing Setup

### Backend Testing

```bash
cd backend

# Run unit tests
dotnet test

# Run with coverage
dotnet test --collect:"XPlat Code Coverage"

# Generate coverage report
reportgenerator -reports:"TestResults/*/coverage.cobertura.xml" -targetdir:"CoverageReport"
```

### Frontend Testing

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage

# Run E2E tests (after setting up device/emulator)
npm run test:e2e
```

### ML Service Testing

```bash
cd llmOCR

# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=src --cov-report=html

# Run specific test
python -m pytest tests/test_ocr.py -v
```

## 🐛 Troubleshooting

### Common Issues

#### Docker Issues

**Services won't start:**
```bash
# Check Docker daemon is running
docker info

# Clean up containers and images
docker-compose down -v
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
```

**Permission errors (Linux):**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

#### Expo Go Development Issues

**Expo Go can't connect to development server:**
```bash
# Check if development server is running
curl http://localhost:19000/

# Restart Expo development server
cd frontend
npx expo start --clear

# For Docker setup, restart the expo-dev service
docker-compose restart expo-dev
```

**"Unable to resolve module" errors:**
```bash
# Clear Expo cache
cd frontend
npx expo start --clear

# Clear npm cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API connection issues from mobile device:**
```bash
# Check if your mobile device can reach the API
# From your mobile browser, visit: http://YOUR_IP_ADDRESS:8001/health

# Update API URL for your environment
# In frontend/.env, set:
EXPO_PUBLIC_API_BASE_URL=http://YOUR_IP_ADDRESS:8001/api

# Restart the development server after changing .env
```

**QR code scanning issues:**
- Ensure adequate lighting when scanning
- Try manual URL entry instead of QR code
- Check if both devices are on the same WiFi network
- Use tunnel mode for different networks: `npx expo start --tunnel`

**App won't reload after changes:**
```bash
# Shake your device to open Expo Go developer menu
# Select "Reload" or "Enable Fast Refresh"

# Or force reload from terminal
# Press 'r' in the Expo development server terminal
```

#### Mobile Development Issues

**Metro bundler can't connect:**
```bash
# Reset Metro cache
npm start -- --reset-cache

# For Android emulator, use 10.0.2.2 instead of localhost in API_BASE_URL
```

**Android build failures:**
```bash
# Clean build
cd android
./gradlew clean
cd ..
npm run android
```

**iOS build failures:**
```bash
# Clean build
cd ios
xcodebuild clean
pod install
cd ..
npm run ios
```

#### Backend Issues

**Database connection errors:**
```bash
# Check MySQL is running
docker ps | grep mysql

# Check connection string in appsettings.json
# Ensure database exists
```

**Package restore issues:**
```bash
# Clear NuGet cache
dotnet nuget locals all --clear
dotnet restore --force
```

#### ML Service Issues

**Model loading errors:**
```bash
# Check if models directory exists
ls -la llmOCR/models/

# Download models manually
cd llmOCR
python scripts/download_models.py
```

**Memory issues:**
```bash
# Reduce batch size in settings
export ML_BATCH_SIZE=1

# Use CPU instead of GPU
export ML_DEVICE=cpu
```

### Getting Help

1. **Check logs:**
   ```bash
   # Docker logs
   docker-compose logs [service-name]
   
   # Service-specific logs
   tail -f backend/logs/app.log
   tail -f llmOCR/logs/app.log
   ```

2. **Verify service health:**
   ```bash
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   ```

3. **Database connectivity:**
   ```bash
   # Test MySQL connection
   mysql -h localhost -P 3306 -u mathsolver -p mathematics_solver
   
   # Test Redis connection
   redis-cli -h localhost -p 6379 ping
   ```

## 📚 Next Steps

After completing the setup:

1. **Explore the codebase:**
   - Review architecture documentation
   - Understand the folder structure
   - Check coding standards and conventions

2. **Run the development workflow:**
   - Make a small change
   - Run tests
   - Create a commit
   - Push to a feature branch

3. **Start development:**
   - Pick up a task from the project board
   - Follow the contributing guidelines
   - Submit your first pull request

## 📞 Support

If you encounter issues not covered in this guide:

1. Check the main [README.md](README.md) for additional information
2. Search existing [GitHub Issues](link-to-issues)
3. Create a new issue with detailed error information
4. Join our development chat for real-time help

---

**Happy Coding! 🚀**