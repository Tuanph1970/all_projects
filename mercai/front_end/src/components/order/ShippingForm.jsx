import React, { useState } from 'react';
import { View, StyleSheet, ScrollView } from 'react-native';
import {
  Surface,
  Text,
  TextInput,
  Button,
  Menu,
  Divider,
  HelperText
} from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

const shippingCarriers = [
  { label: 'UPS', value: 'ups' },
  { label: 'FedEx', value: 'fedex' },
  { label: 'USPS', value: 'usps' },
  { label: 'DHL', value: 'dhl' },
  { label: 'Other', value: 'other' },
];

export const ShippingForm = ({
  onSubmit,
  loading = false,
  onCancel
}) => {
  const [carrierMenuVisible, setCarrierMenuVisible] = useState(false);
  const [formData, setFormData] = useState({
    tracking_number: '',
    carrier: '',
    estimated_delivery: '',
    notes: ''
  });
  const [errors, setErrors] = useState({});

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.tracking_number.trim()) {
      newErrors.tracking_number = 'Tracking number is required';
    } else if (formData.tracking_number.length < 6) {
      newErrors.tracking_number = 'Tracking number must be at least 6 characters';
    }

    if (!formData.carrier) {
      newErrors.carrier = 'Shipping carrier is required';
    }

    if (formData.notes && formData.notes.length > 500) {
      newErrors.notes = 'Notes must be less than 500 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (!validateForm()) {
      return;
    }

    const shippingInfo = {
      tracking_number: formData.tracking_number.trim(),
      carrier: formData.carrier,
      estimated_delivery: formData.estimated_delivery || null,
      notes: formData.notes.trim() || null
    };

    onSubmit(shippingInfo);
  };

  const formatDateForInput = (date) => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  const getCarrierLabel = (value) => {
    const carrier = shippingCarriers.find(c => c.value === value);
    return carrier ? carrier.label : 'Select Carrier';
  };

  return (
    <Surface style={styles.container}>
      <Text style={styles.title}>Shipping Information</Text>
      <Text style={styles.subtitle}>
        Enter the shipping details to mark this order as shipped
      </Text>

      <ScrollView style={styles.form} showsVerticalScrollIndicator={false}>
        <View style={styles.fieldContainer}>
          <TextInput
            label="Tracking Number *"
            value={formData.tracking_number}
            onChangeText={(text) => updateField('tracking_number', text)}
            error={!!errors.tracking_number}
            mode="outlined"
            style={styles.input}
            placeholder="Enter tracking number"
          />
          <HelperText type="error" visible={!!errors.tracking_number}>
            {errors.tracking_number}
          </HelperText>
        </View>

        <View style={styles.fieldContainer}>
          <Menu
            visible={carrierMenuVisible}
            onDismiss={() => setCarrierMenuVisible(false)}
            anchor={
              <TextInput
                label="Shipping Carrier *"
                value={getCarrierLabel(formData.carrier)}
                onPress={() => setCarrierMenuVisible(true)}
                error={!!errors.carrier}
                mode="outlined"
                style={styles.input}
                right={<TextInput.Icon icon="menu-down" />}
                editable={false}
              />
            }
          >
            {shippingCarriers.map((carrier, index) => (
              <Menu.Item
                key={index}
                onPress={() => {
                  updateField('carrier', carrier.value);
                  setCarrierMenuVisible(false);
                }}
                title={carrier.label}
              />
            ))}
          </Menu>
          <HelperText type="error" visible={!!errors.carrier}>
            {errors.carrier}
          </HelperText>
        </View>

        <View style={styles.fieldContainer}>
          <TextInput
            label="Estimated Delivery Date (Optional)"
            value={formData.estimated_delivery}
            onChangeText={(text) => updateField('estimated_delivery', text)}
            mode="outlined"
            style={styles.input}
            placeholder="YYYY-MM-DD"
            keyboardType="numeric"
            right={<TextInput.Icon icon="calendar" />}
          />
          <HelperText type="info" visible={true}>
            Optional delivery date in YYYY-MM-DD format
          </HelperText>
        </View>

        <View style={styles.fieldContainer}>
          <TextInput
            label="Notes (Optional)"
            value={formData.notes}
            onChangeText={(text) => updateField('notes', text)}
            error={!!errors.notes}
            mode="outlined"
            style={styles.input}
            multiline
            numberOfLines={3}
            placeholder="Additional shipping notes..."
          />
          <HelperText type="info" visible={true}>
            {formData.notes.length}/500 characters
          </HelperText>
        </View>

        <View style={styles.buttonContainer}>
          <Button
            mode="outlined"
            onPress={onCancel}
            style={[styles.button, styles.cancelButton]}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            mode="contained"
            onPress={handleSubmit}
            style={[styles.button, styles.submitButton]}
            loading={loading}
            disabled={loading}
          >
            Ship Order
          </Button>
        </View>

        <View style={styles.helperSection}>
          <Text style={styles.helperTitle}>Shipping Guidelines</Text>
          <Text style={styles.helperText}>
            • Double-check the tracking number for accuracy
          </Text>
          <Text style={styles.helperText}>
            • Select the correct shipping carrier
          </Text>
          <Text style={styles.helperText}>
            • Estimated delivery helps set customer expectations
          </Text>
          <Text style={styles.helperText}>
            • Order status will be updated to "Shipped" automatically
          </Text>
        </View>
      </ScrollView>
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.md,
    margin: spacing.md,
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  subtitle: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    marginBottom: spacing.lg,
    lineHeight: 20,
  },
  form: {
    maxHeight: 400,
  },
  fieldContainer: {
    marginBottom: spacing.md,
  },
  input: {
    backgroundColor: colors.surface,
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: spacing.md,
    marginTop: spacing.lg,
    marginBottom: spacing.lg,
  },
  button: {
    flex: 1,
    borderRadius: 8,
  },
  cancelButton: {
    borderColor: colors.outline,
  },
  submitButton: {
    backgroundColor: colors.primary,
  },
  helperSection: {
    backgroundColor: colors.surfaceVariant,
    padding: spacing.md,
    borderRadius: 8,
    marginTop: spacing.md,
  },
  helperTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  helperText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
    lineHeight: 18,
  },
});

export default ShippingForm;