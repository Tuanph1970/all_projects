import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';

import { LoginScreen } from '../screens/auth/LoginScreen.jsx';
import RegisterScreen from '../screens/auth/RegisterScreen.jsx';
import ForgotPasswordScreen from '../screens/auth/ForgotPasswordScreen.jsx';
import ResetPasswordScreen from '../screens/auth/ResetPasswordScreen.jsx';
import EmailVerificationScreen from '../screens/auth/EmailVerificationScreen.jsx';
import { ErrorBoundary } from '../components/common/ErrorBoundary.jsx';


const AuthStack = createStackNavigator();

export const AuthNavigator  = () => {
  return (
    <ErrorBoundary>
      <AuthStack.Navigator screenOptions={{ headerShown: false }}>
        <AuthStack.Screen name="Login" component={LoginScreen} />
        <AuthStack.Screen name="Register" component={RegisterScreen} />
        <AuthStack.Screen name="ForgotPassword" component={ForgotPasswordScreen} />
        <AuthStack.Screen name="ResetPassword" component={ResetPasswordScreen} />
        <AuthStack.Screen name="EmailVerification" component={EmailVerificationScreen} />
      </AuthStack.Navigator>
    </ErrorBoundary>
  );
};