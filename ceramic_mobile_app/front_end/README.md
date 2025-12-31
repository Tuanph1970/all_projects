# Ceramic Marketplace Mobile App

A React Native mobile application for the Ceramic Marketplace, connecting ceramic artisans with customers.

## Features

- **User Authentication**: Registration, login, email verification, password reset
- **Role-Based Access**: Customer, Seller, and Dual user roles
- **Product Catalog**: Browse and search ceramic products
- **Shopping Cart**: Add products and checkout process
- **Real-time Chat**: Direct messaging between buyers and sellers
- **Seller Dashboard**: Product management and analytics
- **User Profiles**: Profile management and address book

## Tech Stack

- **Framework**: React Native with Expo
- **Navigation**: React Navigation v6
- **State Management**: Redux Toolkit with Redux Persist
- **UI Components**: React Native Paper + Custom Components
- **HTTP Client**: Axios with interceptors
- **Forms**: React Hook Form
- **Storage**: Expo SecureStore for tokens, AsyncStorage for app data
- **Icons**: React Native Vector Icons
- **Development**: TypeScript, ESLint

## Getting Started

### Prerequisites

- Node.js (v16 or later)
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator (for iOS development)
- Android Studio (for Android development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ceramic_mobile_app/front_end
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment:
   - Update API base URL in `src/constants/config.ts`
   - Ensure backend server is running

4. Start the development server:
```bash
npm start
```
Note: This uses a custom `start-expo.js` script that resolves Node.js module path issues.

5. Run on device/simulator:
```bash
# iOS
npm run ios

# Android
npm run android

# Web (for testing)
npm run web
```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   └── common/         # Common components (Button, Input, Card, etc.)
├── constants/          # App constants and configuration
├── navigation/         # Navigation configuration
├── screens/           # Screen components
│   ├── auth/          # Authentication screens
│   ├── customer/      # Customer-specific screens
│   ├── seller/        # Seller-specific screens
│   ├── chat/          # Chat screens
│   ├── product/       # Product-related screens
│   └── checkout/      # Checkout screens
├── services/          # API services and HTTP client
├── store/             # Redux store and slices
├── types/             # TypeScript type definitions
└── utils/             # Utility functions
```

## Key Components

### Authentication System
- JWT-based authentication with refresh tokens
- Secure token storage using Expo SecureStore
- Automatic token refresh on API calls
- Role-based navigation and access control

### Navigation Structure
- **AuthNavigator**: Login, Register, Password Reset flows
- **MainNavigator**: Role-based tab navigation
- **Stack Navigation**: Product details, chat, checkout screens

### State Management
- Redux Toolkit for global state
- Redux Persist for data persistence
- Async thunks for API calls
- Centralized error handling

### API Integration
- Axios client with request/response interceptors
- Automatic token attachment and refresh
- Error handling and retry logic
- File upload support

## Configuration

### API Configuration
Update `src/constants/config.ts` with your backend API details:

```typescript
export const API_CONFIG = {
  BASE_URL: 'http://your-backend-url.com',
  // ... other config
};
```

### Theme Customization
Modify `src/constants/theme.ts` to customize colors, spacing, and typography.

## Development Guidelines

### Code Style
- Use TypeScript for type safety
- Follow ESLint rules
- Use functional components with hooks
- Implement proper error boundaries

### Component Guidelines
- Create reusable components in `components/common/`
- Use React Native Paper components as base
- Apply consistent styling with theme system
- Include proper TypeScript interfaces

### State Management
- Use Redux for global state (auth, app settings)
- Use local state for component-specific data
- Implement proper loading and error states
- Use selectors for computed state

## Testing

```bash
# Run tests
npm test

# Run linter
npm run lint

# Fix linting issues
npm run lint:fix
```

## Building for Production

### Android
```bash
npm run build:android
```

### iOS
```bash
npm run build:ios
```

## Environment Variables

Create a `.env` file in the root directory:

```
API_BASE_URL=http://112.213.91.103:8002
ENVIRONMENT=production
```

For local development:
```
API_BASE_URL=http://192.168.1.7:8000
ENVIRONMENT=development
```

## Troubleshooting

### Common Issues

1. **"Cannot find module 'cross-spawn'" Error**:
This is a known issue with global Expo CLI and Node.js module resolution. The project includes a custom startup script to fix this:

```bash
# Use npm start (automatically uses start-expo.js)
npm start

# Or run directly:
node start-expo.js

# If still having issues, try clearing cache:
npm start -- --clear
```

The custom `start-expo.js` script sets up the correct NODE_PATH to resolve global dependencies.

2. **Metro bundler cache issues**:
```bash
npx expo start --clear
```

3. **iOS simulator not launching**:
```bash
npx expo run:ios --device
```

4. **Android build issues**:
```bash
cd android && ./gradlew clean && cd ..
```

5. **Dependency version conflicts**:
```bash
# Fix Expo dependencies
npx expo install --fix

# Clean reinstall if needed
rm -rf node_modules package-lock.json
npm install
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For support, email support@ceramicmarketplace.com or create an issue in the repository.