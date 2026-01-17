import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import {
  Text,
  Appbar,
  Avatar,
  List,
  Card,
  Button,
  Divider,
  TextInput,
  Portal,
  Modal,
  ActivityIndicator
} from 'react-native-paper';
import { useSelector, useDispatch } from 'react-redux';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import { logoutUser, getCurrentUser } from '../../store/slices/authSlice.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import LanguageToggle from '../../components/common/LanguageToggle';
import sellerProfileService from '../../services/sellerProfileService.js';

export const SellerProfileScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const { user, loading } = useSelector((state) => state.auth);

  const [sellerProfile, setSellerProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editForm, setEditForm] = useState({
    full_name: '',
    phone_number: '',
    shop_name: '',
    shop_description: '',
  });
  const [saving, setSaving] = useState(false);

  // Fetch seller profile on mount and when screen is focused
  const fetchSellerProfile = useCallback(async () => {
    try {
      setProfileLoading(true);
      const response = await sellerProfileService.getProfile();
      setSellerProfile(response.data || response);
    } catch (error) {
      console.log('Failed to fetch seller profile:', error);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchSellerProfile();
    }, [fetchSellerProfile])
  );

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: () => dispatch(logoutUser())
        }
      ]
    );
  };

  const handleEditProfile = () => {
    setEditForm({
      full_name: user?.fullName || user?.full_name || '',
      phone_number: user?.phoneNumber || user?.phone_number || sellerProfile?.business_phone || '',
      shop_name: sellerProfile?.store_name || '',
      shop_description: sellerProfile?.store_description || '',
    });
    setEditModalVisible(true);
  };

  const handleSaveProfile = async () => {
    if (!editForm.full_name.trim()) {
      Alert.alert('Validation Error', 'Full name is required');
      return;
    }

    setSaving(true);
    try {
      // Map form fields to backend expected field names
      const profileData = {
        full_name: editForm.full_name,
        phone_number: editForm.phone_number,
        store_name: editForm.shop_name,
        store_description: editForm.shop_description,
      };

      await sellerProfileService.updateProfile(profileData);
      // Refresh both user data and seller profile after update
      await dispatch(getCurrentUser());
      await fetchSellerProfile();
      setEditModalVisible(false);
      Alert.alert('Success', 'Profile updated successfully');
    } catch (error) {
      Alert.alert('Error', error.response?.data?.detail || error.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelEdit = () => {
    setEditModalVisible(false);
  };

  const getInitials = () => {
    const fullName = user?.fullName || user?.full_name;
    if (fullName) {
      return fullName.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (user?.username) {
      return user.username.slice(0, 2).toUpperCase();
    }
    return 'S';
  };

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.Content title="Seller Profile" />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Profile Information */}
        <Card style={styles.profileCard}>
          <View style={styles.profileHeader}>
            <Avatar.Text
              size={80}
              label={getInitials()}
              style={styles.avatar}
            />
            <Text style={styles.name}>
              {user?.fullName || user?.full_name || user?.username || 'Seller'}
            </Text>
            <Text style={styles.email}>
              {user?.email || 'No email'}
            </Text>
            <View style={styles.roleBadge}>
              <Text style={styles.roleText}>SELLER</Text>
            </View>
            {sellerProfile?.store_name && (
              <Text style={styles.shopName}>{sellerProfile.store_name}</Text>
            )}
          </View>
        </Card>

        {/* Shop Information */}
        <Card style={styles.infoCard}>
          <Card.Title title="Shop Information" />
          <Card.Content>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Shop Name</Text>
              <Text style={styles.infoValue}>{sellerProfile?.store_name || 'Not set'}</Text>
            </View>
            <Divider style={styles.divider} />
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Description</Text>
              <Text style={styles.infoValue}>{sellerProfile?.store_description || 'Not set'}</Text>
            </View>
            <Divider style={styles.divider} />
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Phone</Text>
              <Text style={styles.infoValue}>{user?.phoneNumber || user?.phone_number || sellerProfile?.business_phone || 'Not set'}</Text>
            </View>
          </Card.Content>
        </Card>

        {/* Language Toggle */}
        <Card style={styles.languageCard}>
          <LanguageToggle />
        </Card>

        {/* Menu Options */}
        <Card style={styles.menuCard}>
          <List.Item
            title="Edit Profile"
            description="Update your personal and shop information"
            left={props => <List.Icon {...props} icon="account-edit" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={handleEditProfile}
            testID="edit-profile-button"
          />
          <Divider />
          <List.Item
            title="Store Settings"
            description="Configure your store settings"
            left={props => <List.Icon {...props} icon="store-cog" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={() => navigation.navigate('StoreSettings')}
            testID="store-settings-button"
          />
          <Divider />
          <List.Item
            title="Theme Management"
            description="Customize your store appearance"
            left={props => <List.Icon {...props} icon="palette" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={() => navigation.navigate('ThemeManagement')}
            testID="theme-management-button"
          />
          <Divider />
          <List.Item
            title="Order Management"
            description="View and manage customer orders"
            left={props => <List.Icon {...props} icon="receipt" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={() => navigation.navigate('Orders')}
          />
          <Divider />
          <List.Item
            title="Product Management"
            description="Manage your product listings"
            left={props => <List.Icon {...props} icon="package-variant" />}
            right={props => <List.Icon {...props} icon="chevron-right" />}
            onPress={() => navigation.navigate('Products')}
          />
        </Card>

        {/* Logout Button */}
        <Button
          mode="outlined"
          onPress={handleLogout}
          style={styles.logoutButton}
          textColor={colors.error}
          icon="logout"
          testID="logout-button"
        >
          Logout
        </Button>

        <View style={styles.bottomSpacing} />
      </ScrollView>

      {/* Edit Profile Modal */}
      <Portal>
        <Modal
          visible={editModalVisible}
          onDismiss={handleCancelEdit}
          contentContainerStyle={styles.modalContainer}
        >
          <Text style={styles.modalTitle}>Edit Profile</Text>

          <TextInput
            label="Full Name *"
            value={editForm.full_name}
            onChangeText={(text) => setEditForm(prev => ({ ...prev, full_name: text }))}
            style={styles.input}
            mode="outlined"
            testID="edit-full-name"
          />

          <TextInput
            label="Phone Number"
            value={editForm.phone_number}
            onChangeText={(text) => setEditForm(prev => ({ ...prev, phone_number: text }))}
            style={styles.input}
            mode="outlined"
            keyboardType="phone-pad"
            testID="edit-phone"
          />

          <TextInput
            label="Shop Name"
            value={editForm.shop_name}
            onChangeText={(text) => setEditForm(prev => ({ ...prev, shop_name: text }))}
            style={styles.input}
            mode="outlined"
            testID="edit-shop-name"
          />

          <TextInput
            label="Shop Description"
            value={editForm.shop_description}
            onChangeText={(text) => setEditForm(prev => ({ ...prev, shop_description: text }))}
            style={styles.input}
            mode="outlined"
            multiline
            numberOfLines={3}
            testID="edit-shop-description"
          />

          <View style={styles.modalButtons}>
            <Button
              mode="outlined"
              onPress={handleCancelEdit}
              style={styles.modalButton}
              testID="cancel-edit-button"
            >
              Cancel
            </Button>
            <Button
              mode="contained"
              onPress={handleSaveProfile}
              style={styles.modalButton}
              loading={saving}
              disabled={saving}
              testID="save-profile-button"
            >
              Save
            </Button>
          </View>
        </Modal>
      </Portal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.surface,
    elevation: 2,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  profileCard: {
    marginBottom: spacing.md,
    borderRadius: 12,
    overflow: 'hidden',
  },
  profileHeader: {
    alignItems: 'center',
    padding: spacing.lg,
    backgroundColor: colors.primary,
  },
  avatar: {
    backgroundColor: colors.surface,
    marginBottom: spacing.md,
  },
  name: {
    fontSize: typography.sizes.xl,
    fontWeight: 'bold',
    color: colors.surface,
    marginBottom: spacing.xs,
  },
  email: {
    fontSize: typography.sizes.md,
    color: colors.surface,
    opacity: 0.9,
    marginBottom: spacing.sm,
  },
  roleBadge: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: 20,
    marginBottom: spacing.sm,
  },
  roleText: {
    color: colors.primary,
    fontWeight: 'bold',
    fontSize: typography.sizes.sm,
  },
  shopName: {
    fontSize: typography.sizes.md,
    color: colors.surface,
    opacity: 0.9,
    fontStyle: 'italic',
  },
  infoCard: {
    marginBottom: spacing.md,
    borderRadius: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  infoLabel: {
    fontSize: typography.sizes.md,
    color: colors.textSecondary,
  },
  infoValue: {
    fontSize: typography.sizes.md,
    color: colors.text,
    fontWeight: '500',
    flex: 1,
    textAlign: 'right',
    marginLeft: spacing.md,
  },
  divider: {
    marginVertical: spacing.xs,
  },
  languageCard: {
    marginBottom: spacing.md,
    borderRadius: 12,
    padding: spacing.sm,
  },
  menuCard: {
    marginBottom: spacing.md,
    borderRadius: 12,
    overflow: 'hidden',
  },
  logoutButton: {
    marginTop: spacing.sm,
    marginBottom: spacing.md,
    borderColor: colors.error,
  },
  bottomSpacing: {
    height: spacing.xl,
  },
  modalContainer: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    margin: spacing.lg,
    borderRadius: 12,
  },
  modalTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: 'bold',
    marginBottom: spacing.lg,
    textAlign: 'center',
  },
  input: {
    marginBottom: spacing.md,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: spacing.md,
  },
  modalButton: {
    flex: 1,
    marginHorizontal: spacing.xs,
  },
});

export default SellerProfileScreen;
