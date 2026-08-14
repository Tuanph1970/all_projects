import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';

export const AnalyticsCard = ({
  title,
  value,
  change,
  icon,
  color,
  subtitle,
  trend,
}) => {
  const getTrendIcon = () => {
    if (trend) {
      switch (trend) {
        case 'up':
          return '📈';
        case 'down':
          return '📉';
        default:
          return '➡️';
      }
    }
    
    if (change !== undefined) {
      if (change > 0) return '📈';
      if (change < 0) return '📉';
      return '➡️';
    }
    
    return null;
  };

  const getTrendColor = () => {
    if (trend) {
      switch (trend) {
        case 'up':
          return colors.success || '#10B981';
        case 'down':
          return colors.error || '#EF4444';
        default:
          return colors.outline || '#6B7280';
      }
    }
    
    if (change !== undefined) {
      if (change > 0) return colors.success || '#10B981';
      if (change < 0) return colors.error || '#EF4444';
      return colors.outline || '#6B7280';
    }
    
    return colors.outline || '#6B7280';
  };

  const getChangeText = () => {
    if (change !== undefined) {
      const isPositive = change > 0;
      const prefix = isPositive ? '+' : '';
      return `${prefix}${Math.abs(change).toFixed(1)}%`;
    }
    return null;
  };

  return (
    <Card style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          {icon && (
            <View style={[styles.iconContainer, { backgroundColor: color || colors.primary }]}>
              <Icon name={icon} size={24} color={colors.onPrimary} />
            </View>
          )}
          
          {(change !== undefined || trend) && (
            <View style={styles.changeContainer}>
              <Text style={styles.trendIcon}>
                {getTrendIcon()}
              </Text>
              {change !== undefined && (
                <Text style={[styles.changeText, { color: getTrendColor() }]}>
                  {getChangeText()}
                </Text>
              )}
            </View>
          )}
        </View>

        <Text style={styles.title}>{title}</Text>
        <Text style={styles.value}>{value}</Text>
        {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    ...shadows.sm,
  },
  content: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: borderRadius.full,
    justifyContent: 'center',
    alignItems: 'center',
  },
  changeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  trendIcon: {
    fontSize: 16,
    marginRight: spacing.xs,
  },
  changeText: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
  },
  title: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    fontWeight: typography.weights.medium,
    marginBottom: spacing.xs,
  },
  value: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
  },
});

export default AnalyticsCard;