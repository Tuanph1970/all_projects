import React, { useState } from 'react';
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { Text, Title, TextInput } from 'react-native-paper';
import { useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { useForm, Controller } from 'react-hook-form';
import Toast from 'react-native-toast-message';

import { authService } from '../../services/authService';
import { Button } from '../../components/common/Button';
import { Input } from '../../components/common/Input';
import { Card } from '../../components/common/Card';
import { colors, spacing, typography } from '../../constants/theme';
import { useTranslation } from '@i18n';

export const ChangePasswordScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const {
    control,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    reset,
  } = useForm({
    mode: 'onChange',
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    },
  });

  const newPassword = watch('newPassword');

  const onSubmit = async (data) => {
    try {
      setIsLoading(true);

      await authService.changePassword(data.currentPassword, data.newPassword);

      Toast.show({
        type: 'success',
        text1: t('auth.passwordChanged'),
        text2: t('auth.passwordChangedSuccess'),
        visibilityTime: 3000,
        topOffset: 60,
      });

      reset();
      navigation.goBack();
    } catch (error) {
      Toast.show({
        type: 'error',
        text1: t('auth.passwordChangeFailed'),
        text2: error.response?.data?.detail || t('auth.failedChangePassword'),
        visibilityTime: 3000,
        topOffset: 60,
      });
    } finally {
      setIsLoading(false);
    }
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
          <Title style={styles.title}>{t('auth.changePassword')}</Title>
          <Text style={styles.subtitle}>{t('auth.updatePassword')}</Text>
        </View>

        <Card style={styles.formCard}>
          <Controller
            control={control}
            name="currentPassword"
            rules={{
              required: t('auth.currentPasswordRequired'),
              minLength: {
                value: 6,
                message: t('auth.passwordMinLength'),
              },
            }}
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                testID="change-password-current-input"
                label={t('auth.currentPassword')}
                value={value}
                onBlur={onBlur}
                onChangeText={onChange}
                error={!!errors.currentPassword}
                errorMessage={errors.currentPassword?.message}
                secureTextEntry={!showCurrentPassword}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="next"
                left={<TextInput.Icon icon="lock" />}
                right={
                  <TextInput.Icon
                    testID="change-password-current-toggle"
                    icon={showCurrentPassword ? 'eye-off' : 'eye'}
                    onPress={() => setShowCurrentPassword(!showCurrentPassword)}
                  />
                }
              />
            )}
          />

          <Controller
            control={control}
            name="newPassword"
            rules={{
              required: t('auth.newPasswordRequired'),
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
              <Input
                testID="change-password-new-input"
                label={t('auth.newPassword')}
                value={value}
                onBlur={onBlur}
                onChangeText={onChange}
                error={!!errors.newPassword}
                errorMessage={errors.newPassword?.message}
                secureTextEntry={!showNewPassword}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="next"
                left={<TextInput.Icon icon="lock-plus" />}
                right={
                  <TextInput.Icon
                    testID="change-password-new-toggle"
                    icon={showNewPassword ? 'eye-off' : 'eye'}
                    onPress={() => setShowNewPassword(!showNewPassword)}
                  />
                }
              />
            )}
          />

          <Controller
            control={control}
            name="confirmPassword"
            rules={{
              required: t('auth.pleaseConfirmPassword'),
              validate: (value) =>
                value === newPassword || t('auth.passwordMismatch'),
            }}
            render={({ field: { onChange, onBlur, value } }) => (
              <Input
                testID="change-password-confirm-input"
                label={t('auth.confirmNewPassword')}
                value={value}
                onBlur={onBlur}
                onChangeText={onChange}
                error={!!errors.confirmPassword}
                errorMessage={errors.confirmPassword?.message}
                secureTextEntry={!showConfirmPassword}
                autoCapitalize="none"
                autoCorrect={false}
                returnKeyType="done"
                onSubmitEditing={handleSubmit(onSubmit)}
                left={<TextInput.Icon icon="lock-check" />}
                right={
                  <TextInput.Icon
                    testID="change-password-confirm-toggle"
                    icon={showConfirmPassword ? 'eye-off' : 'eye'}
                    onPress={() => setShowConfirmPassword(!showConfirmPassword)}
                  />
                }
              />
            )}
          />

          <Button
            testID="change-password-submit-button"
            onPress={handleSubmit(onSubmit)}
            loading={isLoading}
            disabled={!isValid || isLoading}
            style={styles.submitButton}
          >
            {t('auth.changePassword')}
          </Button>

          <Button
            testID="change-password-cancel-button"
            variant="outlined"
            onPress={() => navigation.goBack()}
            disabled={isLoading}
            style={styles.cancelButton}
          >
            {t('common.cancel')}
          </Button>
        </Card>
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
  submitButton: {
    marginTop: spacing.lg,
  },
  cancelButton: {
    marginTop: spacing.md,
  },
});

export default ChangePasswordScreen;
