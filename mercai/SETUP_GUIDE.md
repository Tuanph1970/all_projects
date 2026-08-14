# 🏺 Mercai - Setup Guide

Complete guide to run the Mercai React Native app from GitHub source code.

## 📋 Quick Start Checklist

- [ ] Node.js 18+ installed
- [ ] Git installed
- [ ] Clone repository
- [ ] Install dependencies
- [ ] Start development server
- [ ] Connect device/emulator

## 🔧 Prerequisites

### Required Software
```bash
# Check if you have the required tools
node --version    # Should be 18.0.0 or higher
npm --version     # Should be 8.0.0 or higher
git --version     # Any recent version
```

### Install Node.js (if needed)
```bash
# Option 1: Using Node Version Manager (Recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20.13.1
nvm use 20.13.1

# Option 2: Direct download
# Visit https://nodejs.org and download LTS version
```

### Install Expo CLI
```bash
# Install Expo CLI globally
npm install -g @expo/cli
```

## 📥 Getting the Source Code

### 1. Clone Repository
```bash
git clone <your-github-repo-url>
cd mercai
```

### 2. Project Structure
```
mercai/
├── front_end/          # React Native app
├── back_end/           # FastAPI backend
└── documents/          # Documentation
```

## 🚀 Frontend Setup (React Native)

### 1. Navigate to Frontend Directory
```bash
cd front_end
```

### 2. Install Dependencies
```bash
# Install all required packages
npm install

# Fix any dependency compatibility issues
npx expo install --fix
```

### 3. Start Development Server
```bash
# Start the Expo development server
npm start
```

**Expected Output:**
```
🚀 Starting Expo with enhanced module resolution...
📦 NODE_PATH: /path/to/your/project/node_modules:/path/to/global/node_modules
Starting project at /path/to/your/project/front_end
Starting Metro Bundler
Waiting on http://localhost:8081
```

### 4. Connect Device/Emulator

#### Option A: Physical Device
1. Install **Expo Go** app from App Store/Google Play
2. Scan the QR code displayed in terminal
3. App will load on your device

#### Option B: iOS Simulator (macOS only)
```bash
# Install iOS Simulator
npm run ios
```

#### Option C: Android Emulator
```bash
# Make sure Android Studio is installed with emulator
npm run android
```

#### Option D: Web Browser
```bash
npm run web
```

## 🐍 Backend Setup (Optional - FastAPI)

### 1. Navigate to Backend Directory
```bash
cd ../back_end  # From front_end directory
```

### 2. Create Python Virtual Environment
```bash
# Create virtual environment
python -m venv mercai_env

# Activate virtual environment
# On Linux/macOS:
source mercai_env/bin/activate
# On Windows:
mercai_env\Scripts\activate
```

### 3. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:** http://localhost:8000

## 🔧 Troubleshooting

### Problem: "Cannot find module 'cross-spawn'" Error

**Solution:** The project includes a custom startup script to fix this issue.
```bash
# This should work automatically with npm start
npm start

# If still having issues, try:
node start-expo.js
```

### Problem: Expo CLI Not Found
```bash
# Install Expo CLI globally
npm install -g @expo/cli

# Or use local version
npx expo start
```

### Problem: Metro Bundler Issues
```bash
# Clear Metro cache
npm start -- --clear

# Or manually:
npx expo start --clear
```

### Problem: Dependency Version Conflicts
```bash
# Fix dependencies to match Expo SDK version
npx expo install --fix

# Or clean install
rm -rf node_modules package-lock.json
npm install
```

### Problem: TypeScript Errors
```bash
# TypeScript configuration is automatically updated by Expo
# If issues persist, check tsconfig.json includes the right files
```

### Problem: Port Already in Use
```bash
# Kill process using port 8081
lsof -ti:8081 | xargs kill -9

# Or use different port
npm start -- --port 8082
```

## 📱 Testing the Application

### Available Features

#### ✅ Implemented (Weeks 1-6)
- **User Authentication** (Login/Register)
- **Product Catalog** (Browse ceramics)
- **Product Details** (View individual items)
- **Search & Filters** (Find specific products)
- **Shopping Cart** (Add/remove items)
- **Checkout Flow** (Complete purchases)

#### 🔧 Backend Features
- **Advanced Search** (Text, category, price filters)
- **Product Analytics** (Trending, recommendations)
- **Image Management** (Upload, optimization)
- **User Management** (Profiles, preferences)
- **Order Management** (Complete order processing)

### Test User Accounts
```javascript
// Test credentials (if backend is running)
{
  email: "test@example.com",
  password: "testpassword"
}
```

## 🛠️ Development Commands

### Frontend (React Native)
```bash
# Start development server
npm start

# Platform-specific builds
npm run android    # Android emulator
npm run ios        # iOS simulator  
npm run web        # Web browser

# Code quality
npm run lint       # Check code style
npm run lint:fix   # Fix linting issues

# Testing
npm test           # Run tests
```

### Backend (FastAPI)
```bash
# Start development server
uvicorn app.main:app --reload

# API documentation
# Visit: http://localhost:8000/docs
```

## 📚 Additional Resources

### Documentation
- **React Native:** https://reactnative.dev/docs/getting-started
- **Expo:** https://docs.expo.dev/
- **FastAPI:** https://fastapi.tiangolo.com/

### Project-Specific Docs
- `documents/development-roadmap.md` - Feature implementation timeline
- `front_end/README.md` - Frontend-specific documentation
- `back_end/README.md` - Backend-specific documentation

## 🆘 Getting Help

### Common Issues & Solutions

1. **Build Errors:** Clear cache with `npm start -- --clear`
2. **Dependency Issues:** Run `npx expo install --fix`
3. **Network Issues:** Check firewall/antivirus settings
4. **Performance Issues:** Close other applications to free memory

### Support Channels
- Check existing GitHub Issues
- Create new issue with error details
- Include system information and error logs

---

## 🎉 Success!

If you see this message in your terminal, you're ready to develop:
```
Waiting on http://localhost:8081
Logs for your project will appear below.
```

**Next Steps:**
1. Open Expo Go app on your phone
2. Scan the QR code
3. Start exploring the Mercai! 🏺

---

*Happy coding! 🚀*