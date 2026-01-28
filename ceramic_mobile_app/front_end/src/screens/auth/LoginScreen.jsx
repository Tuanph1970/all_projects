import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Text, Title, Divider, TextInput } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { useForm, Controller } from 'react-hook-form';
import Toast from 'react-native-toast-message';

import { loginUser, clearError, clearTempPasswordFlag } from '../../store/slices/authSlice.js';

import { Button } from '../../components/common/Button.jsx';
import { Input } from '../../components/common/Input.jsx';
import { Card } from '../../components/common/Card.jsx';

import { colors, spacing, typography, borderRadius } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

export const LoginScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();

  const { isLoading, error, hasTempPassword } = useSelector((state) => state.auth);
  const [showPassword, setShowPassword] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      username: '',
      password: '',
    },
  });

  React.useEffect(() => {
    if (error) {
      Toast.show({
        type: 'error',
        text1: t('auth.loginFailed'),
        text2: error,
        visibilityTime: 3000,
        topOffset: 60,
      });
      dispatch(clearError());
    }
  }, [error, dispatch, t]);

  const onSubmit = async (data) => {
    try {
      const result = await dispatch(loginUser(data));

      if (loginUser.fulfilled.match(result)) {
        // Check if user logged in with temporary password
        const hasTempPwd = !!result.payload?.tokens?.temp_password_warning;

        if (hasTempPwd) {
          // Show warning alert and prompt to change password
          Alert.alert(
            t('auth.tempPasswordWarning').split('.')[0],
            t('auth.tempPasswordWarning'),
            [
              {
                text: t('auth.changePassword'),
                onPress: () => {
                  // Navigation to change password will be handled by app after login
                  Toast.show({
                    type: 'info',
                    text1: t('auth.loginSuccess'),
                    text2: t('auth.tempPasswordWarning'),
                    visibilityTime: 5000,
                    topOffset: 60,
                  });
                },
              },
              {
                text: t('common.ok'),
                onPress: () => {
                  Toast.show({
                    type: 'success',
                    text1: t('auth.loginSuccess'),
                    text2: t('auth.welcomeBackMsg'),
                    visibilityTime: 3000,
                    topOffset: 60,
                  });
                },
              },
            ]
          );
        } else {
          Toast.show({
            type: 'success',
            text1: t('auth.loginSuccess'),
            text2: t('auth.welcomeBackMsg'),
            visibilityTime: 3000,
            topOffset: 60,
          });
        }
        reset();
      }
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  const navigateToRegister = () => {
    navigation.navigate('Register');
  };

  const navigateToForgotPassword = () => {
    navigation.navigate('ForgotPassword');
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <Title style={styles.title}>{t('auth.welcomeBack')}</Title>
          <Text style={styles.subtitle}>{t('auth.signInToAccount')}</Text>
        </View>

        <Card style={styles.formCard}>
          <Controller
            control={control}
            name="username"
            rules={{
              required: t('auth.usernameRequired'),
              minLength: {
                value: 3,
                message: t('auth.usernameMinLength'),
              },
            }}
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                testID="login-username-input"
                label={t('register.username') + ' / ' + t('register.email')}
                value={value}
                onBlur={onBlur}
                onChangeText={onChange}
                error={!!errors.username}
                errorMessage={errors.username?.message}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                returnKeyType="next"
                left={<TextInput.Icon icon="account" />}
              />
            )}
          />

          <Controller
            control={control}
            name="password"
            rules={{
              required: t('auth.passwordRequired'),
              minLength: {
                value: 6,
                message: t('auth.passwordMinLength'),
              },
            }}
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                testID="login-password-input"
                label={t('register.password')}
                value={value}
                onBlur={onBlur}
                onChangeText={onChange}
                error={!!errors.password}
                errorMessage={errors.password?.message}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="done"
                onSubmitEditing={handleSubmit(onSubmit)}
                left={<TextInput.Icon icon="lock" />}
                right={
                  <TextInput.Icon
                    testID="login-password-toggle"
                    icon={showPassword ? "eye-off" : "eye"}
                    onPress={() => setShowPassword(!showPassword)}
                  />
                }
              />
            )}
          />

          <View style={styles.forgotPasswordContainer}>
            <Button
              testID="login-forgot-password-link"
              variant="text"
              onPress={navigateToForgotPassword}
              style={styles.forgotPasswordButton}
            >
              {t('auth.forgotPassword')}
            </Button>
          </View>

          {isLoading && (
            <ActivityIndicator
              testID="login-loading-indicator"
              size="large"
              color={colors.primary}
              style={styles.loadingIndicator}
            />
          )}

          <Button
            testID="login-submit-button"
            onPress={handleSubmit(onSubmit)}
            loading={isLoading}
            disabled={isLoading}
            style={styles.loginButton}
          >
            {t('auth.signIn')}
          </Button>
        </Card>

        <Divider style={styles.divider} />

        <View style={styles.signUpContainer}>
          <Text style={styles.signUpText}>{t('auth.dontHaveAccount')}</Text>
          <Button
            testID="login-register-link"
            variant="text"
            onPress={navigateToRegister}
            style={styles.signUpButton}
          >
            {t('auth.signUp')}
          </Button>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xl,
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing.xl,
  },
  title: {
    fontSize: typography.fontSizes['2xl'],
    fontWeight: typography.bold,
    color: colors.primary,
    marginBottom: spacing.sm,
  },
  subtitle: {
    fontSize: typography.fontSizes.md,
    color: colors.textSecondary,
  },
  formCard: {
    padding: spacing.lg,
    marginBottom: spacing.lg,
  },
  forgotPasswordContainer: {
    alignItems: 'flex-end',
    marginBottom: spacing.lg,
  },
  forgotPasswordButton: {
    marginRight: -spacing.sm,
  },
  loadingIndicator: {
    marginVertical: spacing.md,
  },
  loginButton: {
    marginTop: spacing.md,
  },
  divider: {
    marginVertical: spacing.xl,
  },
  signUpContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  signUpText: {
    fontSize: typography.fontSizes.md,
    color: colors.textSecondary,
  },
  signUpButton: {
    marginLeft: spacing.xs,
  },
});

export default LoginScreen;