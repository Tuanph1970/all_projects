// Patch console methods BEFORE any other imports to prevent initialization errors
const originalWarn = console.warn;
const originalError = console.error;

console.warn = function(...args) {
  try {
    const message = args.join(' ');
    if (message.includes('level') || message.includes('runtime not ready')) {
      return; // Silently ignore known harmless warnings
    }
    originalWarn.apply(console, args);
  } catch (e) {
    // Prevent console errors from crashing the app during initialization
  }
};

console.error = function(...args) {
  try {
    const message = args.join(' ');
    if (message.includes('[runtime not ready]') && message.includes('level')) {
      return; // Silently ignore this specific runtime error
    }
    originalError.apply(console, args);
  } catch (e) {
    // Prevent console errors from crashing the app during initialization
  }
};

import { registerRootComponent } from 'expo';
import { LogBox } from 'react-native';

import App from './App.jsx';

// Ignore specific warnings that occur before runtime is ready
LogBox.ignoreLogs([
  '[runtime not ready]',
  'Cannot read property \'level\' of undefined',
]);

// registerRootComponent calls AppRegistry.registerComponent('main', () => App);
// It also ensures that whether you load the app in Expo Go or in a native build,
// the environment is set up appropriately
try {
  registerRootComponent(App);
} catch (error) {
  console.error('Failed to register root component:', error);
  throw error;
}