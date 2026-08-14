import React, { useEffect, useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { Text, Title } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useRoute } from '@react-navigation/native';
import Toast from 'react-native-toast-message';

import { verifyEmail, resendVerificationEmail, clearError } from '../../store/slices/authSlice';
import { Button } from '../../components/common/Button';
import { Card } from '../../components/common/Card';

const EmailVerificationScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const dispatch = useDispatch();
  
  const { email, token } = route.params || {};
  const { loading, error } = useSelector((state) => state.auth);
  const [resendLoading, setResendLoading] = useState(false);

  useEffect(() => {
    if (error) {
      Toast.show({
        type: 'error',
        text1: 'Verification Failed',
        text2: error,
      });
      dispatch(clearError());
    }
  }, [error, dispatch]);

  useEffect(() => {
    // Auto-verify if token is provided in the URL
    if (token) {
      handleVerification(token);
    }
  }, [token]);

  const handleVerification = async (verificationToken) => {
    try {
      const result = await dispatch(verifyEmail(verificationToken));
      
      if (verifyEmail.fulfilled.match(result)) {
        Toast.show({
          type: 'success',
          text1: 'Email Verified',
          text2: 'Your email has been successfully verified',
        });
        navigation.navigate('Login');
      }
    } catch (err) {
      console.error('Email verification error:', err);
    }
  };

  const handleResendVerification = async () => {
    if (!email) {
      Toast.show({
        type: 'error',
        text1: 'Error',
        text2: 'No email address found',
      });
      return;
    }

    setResendLoading(true);
    try {
      const result = await dispatch(resendVerificationEmail(email));
      
      if (resendVerificationEmail.fulfilled.match(result)) {
        Toast.show({
          type: 'success',
          text1: 'Verification Email Sent',
          text2: 'Please check your email for the verification link',
        });
      }
    } catch (err) {
      console.error('Resend verification error:', err);
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Card style={styles.card}>
        <View style={styles.content}>
          <Title style={styles.title}>Verify Your Email</Title>
          
          <Text style={styles.subtitle}>
            We've sent a verification link to {email || 'your email address'}
          </Text>
          
          <Text style={styles.description}>
            Please check your email and click on the verification link to activate your account.
            If you don't see the email, check your spam folder.
          </Text>

          <View style={styles.actions}>
            <Button
              mode="contained"
              onPress={handleResendVerification}
              loading={resendLoading}
              disabled={resendLoading || !email}
              style={styles.resendButton}
            >
              Resend Verification Email
            </Button>

            <Button
              mode="outlined"
              onPress={() => navigation.navigate('Login')}
              style={styles.backButton}
            >
              Back to Sign In
            </Button>
          </View>
        </View>
      </Card>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  card: {
    padding: 24,
    marginHorizontal: 16,
  },
  content: {
    alignItems: 'center',
  },
  title: {
    textAlign: 'center',
    marginBottom: 16,
    fontSize: 24,
    fontWeight: 'bold',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 16,
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  description: {
    textAlign: 'center',
    marginBottom: 32,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  actions: {
    width: '100%',
    gap: 16,
  },
  resendButton: {
    marginTop: 8,
  },
  backButton: {
    marginTop: 8,
  },
});

export default EmailVerificationScreen;