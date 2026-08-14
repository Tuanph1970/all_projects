# Mercai Frontend Setup Guide

## Overview

This guide provides step-by-step instructions to set up and run the Mercai React Native frontend application.

## Prerequisites

Before starting, ensure you have the following installed on your development machine:

### Required Software
- **Node.js** (v16.0 or higher)
- **npm** (v8.0 or higher) or **Yarn** (v1.22 or higher)
- **Expo CLI** (latest version)
- **Git** (for version control)

### Development Environment Setup

#### For iOS Development (macOS only)
- **Xcode** (latest version from Mac App Store)
- **iOS Simulator** (included with Xcode)
- **Cocoapods** (`sudo gem install cocoapods`)

#### For Android Development
- **Android Studio** (latest version)
- **Android SDK** (API level 30 or higher)
- **Android Emulator** or physical Android device

### Mobile Development Tools
- **Expo Go app** installed on your physical device (optional for testing)
- **EAS CLI** for building: `npm install -g @expo/eas-cli`

## Project Setup

### 1. Clone the Repository
```bash
# Clone the project
git clone <repository-url>
cd mercai/front_end
```

### 2. Install Dependencies
```bash
# Install all project dependencies
npm install

# Alternative with Yarn
yarn install
```

### 3. Environment Configuration
The project uses Expo's configuration system. Key configuration files:

- `app.json` - Main Expo configuration
- `package.json` - Dependencies and scripts
- `tsconfig.json` - TypeScript configuration
- `babel.config.js` - Babel transpilation settings

### 4. Install Expo CLI (if not already installed)
```bash
npm install -g @expo/eas-cli
npm install -g @expo/cli
```

## Running the Application

### Development Server
Start the Expo development server:

```bash
# Start the development server
npm start

# Alternative commands
npm run start
expo start
```

This will open the Expo Developer Tools in your browser at `http://localhost:19002`.

### Running on Different Platforms

#### iOS Simulator (macOS only)
```bash
# Start iOS simulator
npm run ios
expo start --ios
```

#### Android Emulator
```bash
# Start Android emulator
npm run android
expo start --android
```

#### Web Browser (for testing)
```bash
# Run in web browser
npm run web
expo start --web
```

#### Physical Device
1. Install **Expo Go** app from App Store (iOS) or Google Play (Android)
2. Scan the QR code displayed in the terminal or Expo Developer Tools
3. The app will load on your device

## Development Workflow

### File Structure
```
front_end/
├── App.tsx                 # Main application entry point
├── app.json               # Expo configuration
├── package.json           # Dependencies and scripts
├── tsconfig.json          # TypeScript configuration
└── src/
    ├── components/        # Reusable UI components
    │   ├── common/       # Generic components (Button, Card, etc.)
    │   └── product/      # Product-specific components
    ├── constants/        # App constants (theme, config)
    ├── navigation/       # Navigation configuration
    ├── screens/          # Screen components
    │   ├── auth/        # Authentication screens
    │   ├── customer/    # Customer-facing screens
    │   └── seller/      # Seller dashboard screens
    ├── services/        # API services and external integrations
    ├── store/           # Redux store configuration
    │   └── slices/      # Redux state slices
    ├── types/           # TypeScript type definitions
    └── utils/           # Utility functions
```

### Available Scripts

| Command | Description |
|---------|-------------|
| `npm start` | Start Expo development server |
| `npm run android` | Run on Android emulator/device |
| `npm run ios` | Run on iOS simulator/device |
| `npm run web` | Run in web browser |
| `npm run build:android` | Build Android APK/AAB |
| `npm run build:ios` | Build iOS IPA |
| `npm test` | Run Jest tests |
| `npm run lint` | Run ESLint code linting |
| `npm run lint:fix` | Fix ESLint issues automatically |

### Hot Reloading
The development server includes hot reloading, so changes to your code will automatically refresh the app on your device/simulator.

## Backend Integration

### API Configuration
The frontend communicates with a FastAPI backend. Configure the API endpoint in:

```typescript
// src/constants/config.ts
export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000/api/v1', // Update this for your backend
  TIMEOUT: 10000,
};
```

### Backend Requirements
Ensure your backend server is running before testing frontend functionality:
- Backend should be running on `http://localhost:8000`
- All API endpoints should be accessible
- CORS should be configured for frontend domain

## Troubleshooting

### Common Issues

#### 1. Metro bundler issues
```bash
# Clear Metro cache
npx expo start --clear

# Reset npm cache
npm start -- --reset-cache
```

#### 2. Dependency conflicts
```bash
# Clear node_modules and reinstall
rm -rf node_modules
rm package-lock.json
npm install
```

#### 3. iOS build issues
```bash
# Clear iOS build cache
cd ios && rm -rf build && cd ..
npx expo run:ios --clear
```

#### 4. Android build issues
```bash
# Clean Android build
cd android && ./gradlew clean && cd ..
npx expo run:android --clear
```

#### 5. Expo CLI issues
```bash
# Update Expo CLI
npm install -g @expo/cli@latest

# Login to Expo (if needed)
npx expo login
```

### Performance Optimization

#### For Development
- Use physical devices for better performance
- Close unnecessary applications
- Ensure stable internet connection
- Use `--tunnel` flag if local network has issues: `expo start --tunnel`

#### For Production Builds
- Run `npm run build:android` or `npm run build:ios`
- Test on multiple devices and screen sizes
- Optimize images and assets
- Use EAS Build for production-ready builds

## Testing

### Running Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Testing on Devices
1. **iOS Testing**: Use iOS Simulator or physical iOS device
2. **Android Testing**: Use Android Emulator or physical Android device
3. **Cross-platform Testing**: Test on both platforms for consistency

## Building for Production

### EAS Build Setup
```bash
# Install EAS CLI
npm install -g @expo/eas-cli

# Login to Expo
eas login

# Configure EAS build
eas build:configure

# Build for Android
eas build --platform android

# Build for iOS
eas build --platform ios
```

### Local Builds (Alternative)
```bash
# Build Android APK locally
npx expo run:android --variant release

# Build iOS app locally (macOS only)
npx expo run:ios --configuration Release
```

## Code Quality

### Linting
```bash
# Run linter
npm run lint

# Fix linting issues
npm run lint:fix
```

### TypeScript
The project uses TypeScript for type safety. Ensure all files use proper typing:
```bash
# Check TypeScript compilation
npx tsc --noEmit
```

## Additional Resources

### Expo Documentation
- [Expo Documentation](https://docs.expo.dev/)
- [React Native Documentation](https://reactnative.dev/docs/getting-started)
- [Redux Toolkit](https://redux-toolkit.js.org/)
- [React Navigation](https://reactnavigation.org/)

### Development Tools
- **React Native Debugger** - Enhanced debugging
- **Flipper** - Mobile app debugging platform  
- **Expo DevTools** - Built-in development tools

## Support

### Getting Help
1. Check this documentation first
2. Search existing issues in the project repository
3. Check Expo and React Native documentation
4. Create a new issue with detailed error information

### Development Best Practices
- Follow the existing code structure and naming conventions
- Write TypeScript interfaces for all data structures
- Use Redux for global state management
- Implement proper error handling and loading states
- Test on both iOS and Android platforms
- Follow React Native performance best practices

---

**Last Updated**: December 2024  
**Version**: 1.0.0  
**Maintained By**: Mercai Development Team