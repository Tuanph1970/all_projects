import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createStackNavigator } from '@react-navigation/stack';
import { useSelector } from 'react-redux';
import { Linking } from 'react-native';

// RootState type removed for JavaScript
import { AuthNavigator } from './AuthNavigator.jsx';
import { MainNavigator } from './MainNavigator.jsx';
import { LoadingScreen } from '../components/common/LoadingScreen.jsx';

// Deep linking configuration
const linking = {
  prefixes: ['mercaiapp://'],
  config: {
    screens: {
      Auth: {
        screens: {
          ResetPassword: 'reset-password',
          ForgotPassword: 'forgot-password',
          Login: 'login',
          Register: 'register',
          EmailVerification: 'email-verification',
        },
      },
      Main: {
        path: 'main',
      },
    },
  },
};

const RootStack = createStackNavigator();

export const AppNavigator  = ({ onReady }) => {
  const { isAuthenticated, isLoading } = useSelector((state) => state.auth);

  return (
    <NavigationContainer
      linking={linking}
      onReady={onReady}
      fallback={<LoadingScreen />}
    >
      <RootStack.Navigator screenOptions={{ headerShown: false }}>
        {isAuthenticated ? (
          <RootStack.Screen name="Main" component={MainNavigator} />
        ) : (
          <RootStack.Screen name="Auth" component={AuthNavigator} />
        )}
      </RootStack.Navigator>
    </NavigationContainer>
  );
};