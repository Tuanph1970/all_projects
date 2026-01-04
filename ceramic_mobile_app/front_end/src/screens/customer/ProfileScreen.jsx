import React from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import { Text, Appbar, Avatar, List, Card, Button, Divider } from 'react-native-paper';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { logoutUser } from '../../store/slices/authSlice.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';
import LanguageToggle from '../../components/common/LanguageToggle';

export const ProfileScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();
  const { user } = useSelector((state) => state.auth);

  const handleLogout = () => {
    Alert.alert(
      t('auth.logout'),
      t('auth.logoutConfirm'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('auth.logout'),
          style: 'destructive',
          onPress: () => dispatch(logoutUser())
        }
      ]
    );
  };

  const handleEditProfile = () => {
    // TODO: Navigate to edit profile screen
    console.log('Navigate to edit profile');
  };

  const handleOrderHistory = () => {
    // TODO: Navigate to order history screen
    console.log('Navigate to order history');
  };

  const handleChangePassword = () => {
    navigation.navigate('ChangePassword');
  };

  const handleSettings = () => {
    // TODO: Navigate to settings screen
    console.log('Navigate to settings');
  };

  const handleSupport = () => {
    // TODO: Navigate to support screen
    console.log('Navigate to support');
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={t('profile.title')} />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Profile Information */}
        <Card style={styles.profileCard}>
          <View style={styles.profileHeader}>
            <Avatar.Text
              size={80}
              label={user?.fullName?.charAt(0) || 'U'}
              style={styles.avatar}
            />
            <Text style={styles.name}>
              {user?.fullName || t('profile.username')}
            </Text>
            <Text style={styles.email}>
              {user?.email || t('profile.defaultEmail')}
            </Text>
            <Text style={styles.role}>
              {t('register.customer')}
            </Text>
          </View>
        </Card>

        {/* Language Toggle */}
        <Card style={styles.languageCard}>
          <LanguageToggle />
        </Card>

        {/* Menu Options */}
        <Card style={styles.menuCard}>
          <List.Item
            title={t('profile.editInfo')}
            description={t('profile.updatePersonalInfo')}
            left={props => <List.Icon {...props} icon="account-edit" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleEditProfile}
          />
          <Divider />
          <List.Item
            title={t('profile.orderHistory')}
            description={t('profile.viewOrders')}
            left={props => <List.Icon {...props} icon="history" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleOrderHistory}
          />
          <Divider />
          <List.Item
            title={t('profile.changePassword')}
            description={t('profile.changeAccountPassword')}
            testID="profile-change-password-button"
            left={props => <List.Icon {...props} icon="lock-reset" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleChangePassword}
          />
          <Divider />
          <List.Item
            title={t('profile.settings')}
            description={t('profile.customizeApp')}
            left={props => <List.Icon {...props} icon="cog" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleSettings}
          />
          <Divider />
          <List.Item
            title={t('profile.support')}
            description={t('profile.contactUs')}
            left={props => <List.Icon {...props} icon="help-circle" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleSupport}
          />
        </Card>

        {/* Logout Button */}
        <Button
          testID="profile-logout-button"
          mode="outlined"
          style={styles.logoutButton}
          textColor={colors.error}
          onPress={handleLogout}
        >
          {t('auth.logout')}
        </Button>
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  header: {
    elevation: 2,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  profileCard: {
    marginBottom: spacing.md,
  },
  profileHeader: {
    alignItems: 'center',
    padding: spacing.lg,
  },
  avatar: {
    marginBottom: spacing.md,
  },
  name: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  email: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  role: {
    fontSize: typography.sizes.sm,
    color: colors.primary,
    textTransform: 'uppercase',
    fontWeight: typography.weights.medium,
  },
  languageCard: {
    marginBottom: spacing.md,
  },
  menuCard: {
    marginBottom: spacing.lg,
    paddingVertical: spacing.xs,
  },
  logoutButton: {
    marginTop: spacing.md,
    borderColor: colors.error,
  },
});
