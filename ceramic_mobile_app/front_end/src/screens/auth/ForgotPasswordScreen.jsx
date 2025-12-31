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
import { useNavigation } from '@react-navigation/native';
import { useForm, Controller } from 'react-hook-form';
import Toast from 'react-native-toast-message';

import { requestPasswordReset, clearError } from '../../store/slices/authSlice';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Card } from '../../components/common/Card';
import { useTranslation } from '@i18n';

const ForgotPasswordScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();

  const { loading, error } = useSelector((state) => state.auth);

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    reset,
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      email: '',
    },
  });

  useEffect(() => {
    if (error) {
      Toast.show({
        type: 'error',
        text1: t('auth.passwordResetFailed'),
        text2: error,
      });
      dispatch(clearError());
    }
  }, [error, dispatch, t]);

  const onSubmit = async (data) => {
    try {
      const result = await dispatch(requestPasswordReset(data.email));

      if (requestPasswordReset.fulfilled.match(result)) {
        Toast.show({
          type: 'success',
          text1: t('auth.resetEmailSent'),
          text2: t('auth.checkEmailReset'),
        });
        reset();
        navigation.navigate('Login');
      }
    } catch (err) {
      console.error('Password reset error:', err);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scrollContainer}>
        <Card style={styles.card}>
          <Title style={styles.title}>{t('auth.resetPassword')}</Title>
          <Text style={styles.subtitle}>
            {t('auth.enterEmailReset')}
          </Text>

          <View style={styles.form}>
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
                  testID="forgot-password-email-input"
                  label={t('register.email')}
                  value={value}
                  onChangeText={onChange}
                  onBlur={onBlur}
                  error={errors.email?.message}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  returnKeyType="send"
                  onSubmitEditing={handleSubmit(onSubmit)}
                />
              )}
            />

            <Button
              testID="forgot-password-submit-button"
              mode="contained"
              onPress={handleSubmit(onSubmit)}
              loading={loading}
              disabled={loading || !isValid}
              style={styles.submitButton}
            >
              {t('auth.sendResetLink')}
            </Button>

            <Button
              testID="forgot-password-back-button"
              mode="outlined"
              onPress={() => navigation.navigate('Login')}
              style={styles.backButton}
            >
              {t('auth.backToSignIn')}
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

export default ForgotPasswordScreen;
