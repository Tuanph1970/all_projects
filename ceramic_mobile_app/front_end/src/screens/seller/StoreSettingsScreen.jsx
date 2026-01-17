import React, { useState, useEffect, useCallback } from 'react';
import { View, StyleSheet, ScrollView, Alert } from 'react-native';
import {
  Text,
  Appbar,
  Card,
  Button,
  TextInput,
  Divider,
  ActivityIndicator,
  Switch,
  SegmentedButtons
} from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import { useFocusEffect } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerProfileService from '../../services/sellerProfileService.js';

export const StoreSettingsScreen = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [storeData, setStoreData] = useState({
    store_tagline: '',
    business_phone: '',
    business_email: '',
    business_address_line1: '',
    business_address_line2: '',
    business_city: '',
    business_state: '',
    business_postal_code: '',
    business_country: '',
    website_url: '',
    tax_id: '',
    business_type: 'individual',
    shipping_policy: '',
    return_policy: '',
    processing_time: '',
    minimum_order_amount: '',
    accepts_custom_orders: false,
    about_us: '',
    specialties: '',
    meta_description: '',
  });

  // Fetch store settings on mount and focus
  const fetchStoreSettings = useCallback(async () => {
    try {
      setLoading(true);
      const response = await sellerProfileService.getProfile();
      const profile = response.data || response;

      setStoreData({
        store_tagline: profile.store_tagline || '',
        business_phone: profile.business_phone || '',
        business_email: profile.business_email || '',
        business_address_line1: profile.business_address_line1 || '',
        business_address_line2: profile.business_address_line2 || '',
        business_city: profile.business_city || '',
        business_state: profile.business_state || '',
        business_postal_code: profile.business_postal_code || '',
        business_country: profile.business_country || '',
        website_url: profile.website_url || '',
        tax_id: profile.tax_id || '',
        business_type: profile.business_type || 'individual',
        shipping_policy: profile.shipping_policy || '',
        return_policy: profile.return_policy || '',
        processing_time: profile.processing_time || '',
        minimum_order_amount: profile.minimum_order_amount?.toString() || '',
        accepts_custom_orders: profile.accepts_custom_orders || false,
        about_us: profile.about_us || '',
        specialties: profile.specialties?.join(', ') || '',
        meta_description: profile.meta_description || '',
      });
    } catch (error) {
      console.log('Failed to fetch store settings:', error);
      Alert.alert('Error', 'Failed to load store settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      fetchStoreSettings();
    }, [fetchStoreSettings])
  );

  const handleSave = async () => {
    // Validate email if provided
    if (storeData.business_email && !sellerProfileService.isValidEmail(storeData.business_email)) {
      Alert.alert('Validation Error', 'Please enter a valid email address');
      return;
    }

    // Validate website URL if provided
    if (storeData.website_url && !sellerProfileService.isValidUrl(storeData.website_url)) {
      Alert.alert('Validation Error', 'Please enter a valid website URL');
      return;
    }

    // Validate phone if provided
    if (storeData.business_phone && !sellerProfileService.isValidPhone(storeData.business_phone)) {
      Alert.alert('Validation Error', 'Please enter a valid phone number (at least 10 digits)');
      return;
    }

    setSaving(true);
    try {
      const updateData = {
        ...storeData,
        minimum_order_amount: storeData.minimum_order_amount
          ? parseFloat(storeData.minimum_order_amount)
          : null,
        specialties: storeData.specialties
          ? storeData.specialties.split(',').map(s => s.trim()).filter(s => s)
          : [],
      };

      await sellerProfileService.updateProfile(updateData);
      Alert.alert('Success', 'Store settings saved successfully');
    } catch (error) {
      Alert.alert('Error', error.response?.data?.detail || error.message || 'Failed to save store settings');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field, value) => {
    setStoreData(prev => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title="Store Settings" />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading store settings...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="back-button" />
        <Appbar.Content title="Store Settings" />
        <Appbar.Action
          icon="content-save"
          onPress={handleSave}
          disabled={saving}
          testID="save-button"
        />
      </Appbar.Header>

      <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
        {/* Store Information */}
        <Card style={styles.card}>
          <Card.Title title="Store Information" />
          <Card.Content>
            <TextInput
              label="Store Tagline"
              value={storeData.store_tagline}
              onChangeText={(text) => updateField('store_tagline', text)}
              style={styles.input}
              mode="outlined"
              placeholder="A short description of your store"
              testID="store-tagline-input"
            />

            <TextInput
              label="About Us"
              value={storeData.about_us}
              onChangeText={(text) => updateField('about_us', text)}
              style={styles.input}
              mode="outlined"
              multiline
              numberOfLines={4}
              placeholder="Tell customers about your business"
              testID="about-us-input"
            />

            <TextInput
              label="Specialties (comma separated)"
              value={storeData.specialties}
              onChangeText={(text) => updateField('specialties', text)}
              style={styles.input}
              mode="outlined"
              placeholder="e.g., Handmade ceramics, Custom orders"
              testID="specialties-input"
            />

            <TextInput
              label="Meta Description (SEO)"
              value={storeData.meta_description}
              onChangeText={(text) => updateField('meta_description', text)}
              style={styles.input}
              mode="outlined"
              multiline
              numberOfLines={2}
              placeholder="Description for search engines"
              testID="meta-description-input"
            />
          </Card.Content>
        </Card>

        {/* Contact Information */}
        <Card style={styles.card}>
          <Card.Title title="Contact Information" />
          <Card.Content>
            <TextInput
              label="Business Phone"
              value={storeData.business_phone}
              onChangeText={(text) => updateField('business_phone', text)}
              style={styles.input}
              mode="outlined"
              keyboardType="phone-pad"
              testID="business-phone-input"
            />

            <TextInput
              label="Business Email"
              value={storeData.business_email}
              onChangeText={(text) => updateField('business_email', text)}
              style={styles.input}
              mode="outlined"
              keyboardType="email-address"
              autoCapitalize="none"
              testID="business-email-input"
            />

            <TextInput
              label="Website URL"
              value={storeData.website_url}
              onChangeText={(text) => updateField('website_url', text)}
              style={styles.input}
              mode="outlined"
              keyboardType="url"
              autoCapitalize="none"
              placeholder="https://www.yourwebsite.com"
              testID="website-url-input"
            />
          </Card.Content>
        </Card>

        {/* Business Address */}
        <Card style={styles.card}>
          <Card.Title title="Business Address" />
          <Card.Content>
            <TextInput
              label="Address Line 1"
              value={storeData.business_address_line1}
              onChangeText={(text) => updateField('business_address_line1', text)}
              style={styles.input}
              mode="outlined"
              testID="address-line1-input"
            />

            <TextInput
              label="Address Line 2"
              value={storeData.business_address_line2}
              onChangeText={(text) => updateField('business_address_line2', text)}
              style={styles.input}
              mode="outlined"
              testID="address-line2-input"
            />

            <View style={styles.row}>
              <TextInput
                label="City"
                value={storeData.business_city}
                onChangeText={(text) => updateField('business_city', text)}
                style={[styles.input, styles.halfInput]}
                mode="outlined"
                testID="city-input"
              />
              <TextInput
                label="State"
                value={storeData.business_state}
                onChangeText={(text) => updateField('business_state', text)}
                style={[styles.input, styles.halfInput]}
                mode="outlined"
                testID="state-input"
              />
            </View>

            <View style={styles.row}>
              <TextInput
                label="Postal Code"
                value={storeData.business_postal_code}
                onChangeText={(text) => updateField('business_postal_code', text)}
                style={[styles.input, styles.halfInput]}
                mode="outlined"
                keyboardType="numeric"
                testID="postal-code-input"
              />
              <TextInput
                label="Country"
                value={storeData.business_country}
                onChangeText={(text) => updateField('business_country', text)}
                style={[styles.input, styles.halfInput]}
                mode="outlined"
                testID="country-input"
              />
            </View>
          </Card.Content>
        </Card>

        {/* Business Details */}
        <Card style={styles.card}>
          <Card.Title title="Business Details" />
          <Card.Content>
            <Text style={styles.label}>Business Type</Text>
            <SegmentedButtons
              value={storeData.business_type}
              onValueChange={(value) => updateField('business_type', value)}
              buttons={[
                { value: 'individual', label: 'Individual' },
                { value: 'business', label: 'Business' },
                { value: 'corporation', label: 'Corporation' },
              ]}
              style={styles.segmentedButtons}
              testID="business-type-selector"
            />

            <TextInput
              label="Tax ID / Business Number"
              value={storeData.tax_id}
              onChangeText={(text) => updateField('tax_id', text)}
              style={styles.input}
              mode="outlined"
              testID="tax-id-input"
            />

            <TextInput
              label="Minimum Order Amount"
              value={storeData.minimum_order_amount}
              onChangeText={(text) => updateField('minimum_order_amount', text)}
              style={styles.input}
              mode="outlined"
              keyboardType="decimal-pad"
              placeholder="0.00"
              testID="minimum-order-input"
            />

            <View style={styles.switchRow}>
              <Text style={styles.switchLabel}>Accept Custom Orders</Text>
              <Switch
                value={storeData.accepts_custom_orders}
                onValueChange={(value) => updateField('accepts_custom_orders', value)}
                testID="custom-orders-switch"
              />
            </View>
          </Card.Content>
        </Card>

        {/* Policies */}
        <Card style={styles.card}>
          <Card.Title title="Store Policies" />
          <Card.Content>
            <TextInput
              label="Processing Time"
              value={storeData.processing_time}
              onChangeText={(text) => updateField('processing_time', text)}
              style={styles.input}
              mode="outlined"
              placeholder="e.g., 3-5 business days"
              testID="processing-time-input"
            />

            <TextInput
              label="Shipping Policy"
              value={storeData.shipping_policy}
              onChangeText={(text) => updateField('shipping_policy', text)}
              style={styles.input}
              mode="outlined"
              multiline
              numberOfLines={4}
              placeholder="Describe your shipping terms"
              testID="shipping-policy-input"
            />

            <TextInput
              label="Return Policy"
              value={storeData.return_policy}
              onChangeText={(text) => updateField('return_policy', text)}
              style={styles.input}
              mode="outlined"
              multiline
              numberOfLines={4}
              placeholder="Describe your return/refund policy"
              testID="return-policy-input"
            />
          </Card.Content>
        </Card>

        {/* Save Button */}
        <Button
          mode="contained"
          onPress={handleSave}
          style={styles.saveButton}
          loading={saving}
          disabled={saving}
          testID="save-settings-button"
        >
          Save Settings
        </Button>

        <View style={styles.bottomSpacing} />
      </ScrollView>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.textSecondary,
  },
  card: {
    marginBottom: spacing.md,
    borderRadius: 12,
  },
  input: {
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    flex: 0.48,
  },
  label: {
    fontSize: typography.sizes.md,
    color: colors.textSecondary,
    marginBottom: spacing.sm,
  },
  segmentedButtons: {
    marginBottom: spacing.md,
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  switchLabel: {
    fontSize: typography.sizes.md,
    color: colors.text,
  },
  saveButton: {
    marginTop: spacing.sm,
    marginBottom: spacing.md,
    paddingVertical: spacing.xs,
  },
  bottomSpacing: {
    height: spacing.xl,
  },
});

export default StoreSettingsScreen;
