import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { Text, Title, Divider, RadioButton } from 'react-native-paper';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { useForm, Controller } from 'react-hook-form';
import Toast from 'react-native-toast-message';

import { registerUser, clearError } from '../../store/slices/authSlice';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Card } from '../../components/common/Card';
import { useTranslation } from '@i18n';

const RegisterScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();
  const { isLoading, error } = useSelector((state) => state.auth);
  const [selectedRole, setSelectedRole] = useState('customer');

  const {
    control,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm({
    defaultValues: {
      firstName: '',
      lastName: '',
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      role: 'customer',
    },
  });

  const password = watch('password');


  useEffect(() => {
    if (error) {
      Toast.show({
        type: 'error',
        text1: t('auth.registrationFailed'),
        text2: error,
      });
      dispatch(clearError());
    }
  }, [error, dispatch, t]);

  const onSubmit = async (data) => {
    try {
      const { confirmPassword, firstName, lastName, ...otherData } = data;
      const registerData = {
        email: data.email,
        username: data.username,
        password: data.password,
        full_name: `${firstName} ${lastName}`.trim(),
        phone_number: null,
        role: selectedRole,
      };

      console.log('📝 [RegisterScreen] Submitting registration:', {
        email: registerData.email,
        username: registerData.username,
        full_name: registerData.full_name,
        role: registerData.role,
      });

      const result = await dispatch(registerUser(registerData));

      console.log('📝 [RegisterScreen] Registration result:', {
        type: result.type,
        payload: result.payload,
        error: result.error,
      });

      if (registerUser.fulfilled.match(result)) {
        console.log('✅ [RegisterScreen] Registration successful!');
        Toast.show({
          type: 'success',
          text1: t('auth.registrationSuccess'),
          text2: t('auth.checkEmailVerify'),
        });
        navigation.navigate('Login');
      } else {
        console.log('❌ [RegisterScreen] Registration failed:', result.payload || result.error);
      }
    } catch (err) {
      console.error('❌ [RegisterScreen] Registration exception:', err);
    }
  };

  const validatePasswordMatch = (value) => {
    return value === password || t('auth.passwordMismatch');
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Card style={styles.card}>
          <Title style={styles.title}>{t('auth.createAccount')}</Title>

          <View style={styles.form}>
            <Controller
              control={control}
              name="firstName"
              rules={{
                required: t('register.firstNameRequired'),
                minLength: {
                  value: 2,
                  message: t('register.firstNameMinLength'),
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  testID="register-firstname-input"
                  label={t('register.firstName')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={!!errors.firstName}
                  errorMessage={errors.firstName?.message}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              )}
            />

            <Controller
              control={control}
              name="lastName"
              rules={{
                required: t('register.lastNameRequired'),
                minLength: {
                  value: 2,
                  message: t('register.lastNameMinLength'),
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  testID="register-lastname-input"
                  label={t('register.lastName')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={!!errors.lastName}
                  errorMessage={errors.lastName?.message}
                  autoCapitalize="words"
                  returnKeyType="next"
                />
              )}
            />

            <Controller
              control={control}
              name="username"
              rules={{
                required: t('register.usernameRequired'),
                minLength: {
                  value: 1,
                  message: t('register.usernameMinLength'),
                },
                maxLength: {
                  value: 50,
                  message: t('register.usernameMaxLength'),
                },
                pattern: {
                  value: /^[a-zA-Z0-9_-]+$/,
                  message: t('register.usernameFormat'),
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  testID="register-username-input"
                  label={t('register.username')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={!!errors.username}
                  errorMessage={errors.username?.message}
                  autoCapitalize="none"
                  returnKeyType="next"
                />
              )}
            />

            <Controller
              control={control}
              name="email"
              rules={{
                required: t('auth.emailRequired'),
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: t('auth.invalidEmail'),
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  testID="register-email-input"
                  label={t('register.email')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={!!errors.email}
                  errorMessage={errors.email?.message}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  returnKeyType="next"
                />
              )}
            />

            <Controller
              control={control}
              name="password"
              rules={{
                required: t('auth.passwordRequired'),
                minLength: {
                  value: 8,
                  message: t('auth.passwordMinLength8'),
                },
                pattern: {
                  value: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>])/,
                  message: t('auth.passwordStrength'),
                },
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <>
                  <Input
                    testID="register-password-input"
                    label={t('register.password')}
                    value={value}
                    onChangeText={onChange}
                    onBlur={onBlur}
                    error={!!errors.password}
                    errorMessage={errors.password?.message}
                    secureTextEntry
                    returnKeyType="next"
                  />
                  {!errors.password && (
                    <Text style={styles.passwordHint}>
                      {t('auth.passwordStrength')}
                    </Text>
                  )}
                </>
              )}
            />

            <Controller
              control={control}
              name="confirmPassword"
              rules={{
                required: t('auth.pleaseConfirmPassword'),
                validate: validatePasswordMatch,
              }}
              render={({ field: { onChange, onBlur, value } }) => (
                <Input
                  testID="register-confirm-password-input"
                  label={t('auth.confirmPassword')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={!!errors.confirmPassword}
                  errorMessage={errors.confirmPassword?.message}
                  secureTextEntry
                  returnKeyType="done"
                />
              )}
            />

            <View style={styles.roleSelection}>
              <Text style={styles.roleLabel}>{t('register.accountType')}</Text>
              <RadioButton.Group
                onValueChange={(value) => setSelectedRole(value)}
                value={selectedRole}
              >
                <View style={styles.radioOption} testID="register-role-customer">
                  <RadioButton value="customer" />
                  <Text style={styles.radioLabel}>{t('register.customer')}</Text>
                </View>
                <View style={styles.radioOption} testID="register-role-seller">
                  <RadioButton value="seller" />
                  <Text style={styles.radioLabel}>{t('register.seller')}</Text>
                </View>
              </RadioButton.Group>
            </View>

            <Button
              testID="register-submit-button"
              mode="contained"
              onPress={handleSubmit(onSubmit)}
              loading={isLoading}
              disabled={isLoading}
              style={styles.submitButton}
            >
              {t('auth.createAccount')}
            </Button>

            <Divider style={styles.divider} />

            <Button
              testID="register-login-link"
              mode="outlined"
              onPress={() => navigation.navigate('Login')}
              style={styles.loginButton}
            >
              {t('auth.alreadyHaveAccount')}
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
    marginBottom: 24,
    fontSize: 24,
    fontWeight: 'bold',
  },
  form: {
    gap: 16,
  },
  roleSelection: {
    marginVertical: 8,
  },
  roleLabel: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
  },
  radioOption: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 4,
  },
  radioLabel: {
    marginLeft: 8,
    fontSize: 14,
  },
  submitButton: {
    marginTop: 16,
  },
  divider: {
    marginVertical: 16,
  },
  loginButton: {
    marginTop: 8,
  },
  passwordHint: {
    fontSize: 11,
    color: '#888',
    marginTop: -8,
    marginBottom: 4,
    paddingHorizontal: 4,
  },
});

export default RegisterScreen;
