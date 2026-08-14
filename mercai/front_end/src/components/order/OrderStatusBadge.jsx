import React from 'react';
import { StyleSheet } from 'react-native';
import { Chip } from 'react-native-paper';
import { colors, spacing } from '../../constants/theme.js';

const OrderStatus = {
  PENDING: 'PENDING',
  CONFIRMED: 'CONFIRMED',
  PROCESSING: 'PROCESSING',
  SHIPPED: 'SHIPPED',
  DELIVERED: 'DELIVERED',
  CANCELLED: 'CANCELLED',
  REFUNDED: 'REFUNDED'
};

export const OrderStatusBadge = ({ 
  status, 
  size = 'medium' 
}) => {
  const getStatusConfig = (status) => {
    const configs = {
      [OrderStatus.PENDING]: {
        color: colors.warning || '#FF9800',
        backgroundColor: colors.warning + '20' || '#FF980020',
        textColor: colors.warning || '#FF9800',
        label: 'Pending'
      },
      [OrderStatus.CONFIRMED]: {
        color: colors.info || '#2196F3',
        backgroundColor: colors.info + '20' || '#2196F320',
        textColor: colors.info || '#2196F3',
        label: 'Confirmed'
      },
      [OrderStatus.PROCESSING]: {
        color: colors.primary,
        backgroundColor: colors.primary + '20',
        textColor: colors.primary,
        label: 'Processing'
      },
      [OrderStatus.SHIPPED]: {
        color: colors.success || '#4CAF50',
        backgroundColor: colors.success + '20' || '#4CAF5020',
        textColor: colors.success || '#4CAF50',
        label: 'Shipped'
      },
      [OrderStatus.DELIVERED]: {
        color: colors.success || '#4CAF50',
        backgroundColor: colors.success + '20' || '#4CAF5020',
        textColor: colors.success || '#4CAF50',
        label: 'Delivered'
      },
      [OrderStatus.CANCELLED]: {
        color: colors.error,
        backgroundColor: colors.error + '20',
        textColor: colors.error,
        label: 'Cancelled'
      },
      [OrderStatus.REFUNDED]: {
        color: colors.outline,
        backgroundColor: colors.outline + '20',
        textColor: colors.outline,
        label: 'Refunded'
      }
    };

    return configs[status] || configs[OrderStatus.PENDING];
  };

  const config = getStatusConfig(status);

  return (
    <Chip
      style={[
        styles.chip,
        size === 'small' && styles.smallChip,
        { backgroundColor: config.backgroundColor }
      ]}
      textStyle={[
        styles.chipText,
        size === 'small' && styles.smallText,
        { color: config.textColor }
      ]}
      mode="flat"
    >
      {config.label}
    </Chip>
  );
};

const styles = StyleSheet.create({
  chip: {
    marginVertical: 2,
    alignSelf: 'flex-start',
  },
  smallChip: {
    height: 24,
  },
  chipText: {
    fontWeight: '600',
    fontSize: 12,
  },
  smallText: {
    fontSize: 10,
  },
});

export default OrderStatusBadge;