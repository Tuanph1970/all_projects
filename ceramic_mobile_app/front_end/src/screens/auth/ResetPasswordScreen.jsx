import React, { useEffect } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { Text, Title } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useForm, Controller } from 'react-hook-form';
import Toast from 'react-native-toast-message';

import { resetPassword, clearError } from '../../store/slices/authSlice';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Card } from '../../components/common/Card';

const ResetPasswordScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const dispatch = useDispatch();
  
  const { token } = route.params || {};
  const { loading, error } = useSelector((state) => state.auth);

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    watch,
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      password: '',
      confirmPassword: '',
    },
  });

  const password = watch('password');

  useEffect(() => {
    if (error) {
      Toast.show({
        type: 'error',
        text1: 'Password Reset Failed',
        text2: error,
      });
      dispatch(clearError());
    }
  }, [error, dispatch]);

  useEffect(() => {
    if (!token) {
      Toast.show({
        type: 'error',
        text1: 'Invalid Reset Link',
        text2: 'The password reset link is invalid or has expired',
      });
      navigation.navigate('ForgotPassword');
    }
  }, [token, navigation]);

  const onSubmit = async (data) => {
    try {
      const result = await dispatch(resetPassword({
        token,
        password: data.password,
      }));
      
      if (resetPassword.fulfilled.match(result)) {
        Toast.show({
          type: 'success',
          text1: 'Password Reset Successful',
          text2: 'Your password has been updated successfully',
        });
        navigation.navigate('Login');
      }
    } catch (err) {
      console.error('Password reset error:', err);
    }
  };

  const validatePasswordMatch = (value) => {
    return value === password || 'Passwords do not match';
  };

  if (!token) {
    return null;
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Card style={styles.card}>
          <Title style={styles.title}>Reset Password</Title>
          <Text style={styles.subtitle}>
            Enter your new password below.
          </Text>
          
          <View style={styles.form}>
            <Controller
              control={control}
              name="password"
              rules={{
                required: 'Password is required',
                minLength: {
                  value: 8,
                  message: 'Password must be at least 8 characters',
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
                  message: 'Password must contain at least one uppercase letter, one lowercase letter, and one number',
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  label="New Password"
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={errors.password?.message}
                  secureTextEntry
                  returnKeyType="next"
                />
              )}
            />

            <Controller
              control={control}
              name="confirmPassword"
              rules={{
                required: 'Please confirm your password',
                validate: validatePasswordMatch,
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  label="Confirm New Password"
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={errors.confirmPassword?.message}
                  secureTextEntry
                  returnKeyType="done"
                  onSubmitEditing={handleSubmit(onSubmit)}
                />
              )}
            />

            <Button
              mode="contained"
              onPress={handleSubmit(onSubmit)}
              loading={loading}
              disabled={loading || !isValid}
              style={styles.submitButton}
            >
              Reset Password
            </Button>

            <Button
              mode="outlined"
              onPress={() => navigation.navigate('Login')}
              style={styles.backButton}
            >
              Back to Sign In
            </Button>
          </View>
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 16,
  },
  card: {
    padding: 24,
    marginHorizontal: 16,
  },
  title: {
    textAlign: 'center',
    marginBottom: 16,
    fontSize: 24,
    fontWeight: 'bold',
  },
  subtitle: {
    textAlign: 'center',
    marginBottom: 24,
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
  form: {
    gap: 16,
  },
  submitButton: {
    marginTop: 16,
  },
  backButton: {
    marginTop: 8,
  },
});

export default ResetPasswordScreen;