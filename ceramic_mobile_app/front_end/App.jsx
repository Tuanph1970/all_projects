import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { View, Text } from 'react-native';
import { Provider } from 'react-redux';
import { PersistGate } from 'redux-persist/integration/react';
import { PaperProvider } from 'react-native-paper';
import Toast, { BaseToast, ErrorToast } from 'react-native-toast-message';
import * as SplashScreen from 'expo-splash-screen';

import { store, persistor } from '@store/index';
import { AppNavigator } from '@navigation/AppNavigator';
import { theme } from '@constants/theme';
import { LoadingScreen } from '@components/common/LoadingScreen';
import { LanguageProvider } from '@i18n';

// Keep the splash screen visible while we fetch resources
SplashScreen.preventAutoHideAsync();

// Toast configuration with testIDs for E2E testing
const toastConfig = {
  success: (props) => (
    <BaseToast
      {...props}
      testID="toast-success"
      text1NumberOfLines={2}
      text2NumberOfLines={3}
      style={{ borderLeftColor: '#4CAF50' }}
      contentContainerStyle={{ paddingHorizontal: 15 }}
      text1Style={{
        fontSize: 16,
        fontWeight: '600',
      }}
      text2Style={{
        fontSize: 14,
      }}
    />
  ),
  error: (props) => (
    <ErrorToast
      {...props}
      testID="toast-error"
      text1NumberOfLines={2}
      text2NumberOfLines={3}
      style={{ borderLeftColor: '#F44336' }}
      contentContainerStyle={{ paddingHorizontal: 15 }}
      text1Style={{
        fontSize: 16,
        fontWeight: '600',
      }}
      text2Style={{
        fontSize: 14,
      }}
    />
  ),
};

export default function App() {
  const [appIsReady, setAppIsReady] = React.useState(false);

  React.useEffect(() => {
    async function prepare() {
      try {
        // Pre-load fonts, make any API calls you need to do here
        // await Font.loadAsync(customFonts);
        // Skip delay in E2E test mode
        const isE2E = typeof global.__E2E__ !== 'undefined';
        if (!isE2E) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      } catch (e) {
        console.warn(e);
      } finally {
        setAppIsReady(true);
      }
    }

    prepare();
  }, []);

  const onLayoutRootView = React.useCallback(async () => {
    if (appIsReady) {
      await SplashScreen.hideAsync();
    }
  }, [appIsReady]);

  if (!appIsReady) {
    return <LoadingScreen />;
  }

  return (
    <Provider store={store}>
      <PersistGate loading={<LoadingScreen />} persistor={persistor}>
        <LanguageProvider>
          <PaperProvider theme={theme}>
            <View style={{ flex: 1 }}>
              <StatusBar style="auto" />
              <AppNavigator onReady={onLayoutRootView} />
              <Toast
                config={toastConfig}
                position="top"
                topOffset={60}
                visibilityTime={3000}
              />
            </View>
          </PaperProvider>
        </LanguageProvider>
      </PersistGate>
    </Provider>
  );
}