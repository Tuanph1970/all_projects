import React, { useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Provider, useDispatch } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import * as SplashScreen from 'expo-splash-screen';
import * as Font from 'expo-font';

import { initSentry } from './src/utils/sentry';
import { store, persistor } from './src/store';

// Initialise Sentry before anything else renders.
// No-op when EXPO_PUBLIC_SENTRY_DSN is not set.
initSentry();
import { initializeAuth } from './src/store/slices/authSlice';
import AppNavigator from './src/navigation/AppNavigator';
import LoadingScreen from './src/components/common/LoadingScreen';
import ErrorBoundary from './src/components/common/ErrorBoundary';

// Prevent the splash screen from auto-hiding
SplashScreen.preventAutoHideAsync();

// Inner app component that has access to dispatch
const AppContent = () => {
  const dispatch = useDispatch();
  const [fontsLoaded, setFontsLoaded] = React.useState(false);

  useEffect(() => {
    async function initializeApp() {
      try {
        // Load custom fonts if needed
        await Font.loadAsync({
          // Add custom fonts here if required
        });
        
        // Initialize auth state
        dispatch(initializeAuth());
        
        setFontsLoaded(true);
        await SplashScreen.hideAsync();
      } catch (error) {
        console.warn('Error initializing app:', error);
        dispatch(initializeAuth());
        setFontsLoaded(true);
        await SplashScreen.hideAsync();
      }
    }

    initializeApp();
  }, [dispatch]);

  if (!fontsLoaded) {
    return <LoadingScreen />;
  }

  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <AppNavigator />
    </SafeAreaProvider>
  );
};

// Main app component
export default function App() {
  return (
    <ErrorBoundary>
      <Provider store={store}>
        <PersistGate 
          loading={<LoadingScreen message="Loading your data..." />} 
          persistor={persistor}
          onBeforeLift={() => {
            // Optional: You can add logic here that runs before rehydration
            console.log('PersistGate: About to rehydrate state');
          }}
        >
          <AppContent />
        </PersistGate>
      </Provider>
    </ErrorBoundary>
  );
}