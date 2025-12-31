import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Surface, Text } from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

export const OrderStatsCard = ({
  title,
  value,
  subtitle,
  color = colors.primary,
  icon,
  trend
}) => {
  const formatValue = (val) => {
    if (typeof val === 'number') {
      if (val >= 1000000) {
        return `${(val / 1000000).toFixed(1)}M`;
      } else if (val >= 1000) {
        return `${(val / 1000).toFixed(1)}K`;
      }
      return val.toString();
    }
    return val;
  };

  const getTrendColor = (trend) => {
    if (trend > 0) return colors.success || '#4CAF50';
    if (trend < 0) return colors.error;
    return colors.outline;
  };

  return (
    <Surface style={styles.card}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.title}>{title}</Text>
          {icon && (
            <View style={[styles.iconContainer, { backgroundColor: color + '20' }]}>
              <Text style={[styles.iconText, { color }]}>{icon}</Text>
            </View>
          )}
        </View>

        <Text style={[styles.value, { color }]}>
          {formatValue(value)}
        </Text>

        <View style={styles.bottom}>
          {subtitle && (
            <Text style={styles.subtitle}>{subtitle}</Text>
          )}
          
          {trend !== undefined && (
            <View style={styles.trendContainer}>
              <Text 
                style={[
                  styles.trendText,
                  { color: getTrendColor(trend) }
                ]}
              >
                {trend > 0 ? '+' : ''}{trend}%
              </Text>
            </View>
          )}
        </View>
      </View>
    </Surface>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    overflow: 'hidden',
    flex: 1,
    minHeight: 120,
    elevation: 2,
  },
  content: {
    flex: 1,
    padding: spacing.md,
    justifyContent: 'space-between',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  title: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    fontWeight: typography.weights.medium,
    flex: 1,
  },
  iconContainer: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginLeft: spacing.sm,
  },
  iconText: {
    fontSize: 16,
  },
  value: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    marginBottom: spacing.sm,
  },
  bottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  subtitle: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    flex: 1,
  },
  trendContainer: {
    marginLeft: spacing.sm,
  },
  trendText: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.medium,
  },
});

export default OrderStatsCard;