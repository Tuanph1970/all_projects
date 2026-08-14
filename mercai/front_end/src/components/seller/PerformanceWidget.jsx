import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Surface, Text } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography } from '../../constants/theme.js';

export const PerformanceWidget = ({
  title,
  value,
  subtitle,
  growth,
  icon,
  loading = false,
  color = colors.primary
}) => {
  const formatGrowth = (growth) => {
    if (growth > 0) return `+${growth.toFixed(1)}%`;
    return `${growth.toFixed(1)}%`;
  };

  const getGrowthColor = (growth) => {
    if (growth > 0) return colors.success || '#10B981';
    if (growth < 0) return colors.error || '#EF4444';
    return colors.textSecondary || '#6B7280';
  };

  if (loading) {
    return (
      <Surface style={styles.container}>
        <View style={styles.content}>
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </Surface>
    );
  }

  return (
    <Surface style={styles.container}>
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={[styles.title, { color: color }]}>{title}</Text>
          {icon && (
            <Icon name={icon} size={24} color={color} style={styles.icon} />
          )}
        </View>
        
        <View style={styles.valueContainer}>
          <Text style={[styles.value, { color: color }]}>{value}</Text>
          {growth !== undefined && (
            <Text style={[styles.growth, { color: getGrowthColor(growth) }]}>
              {formatGrowth(growth)}
            </Text>
          )}
        </View>

        {subtitle && (
          <Text style={styles.subtitle}>{subtitle}</Text>
        )}
      </View>
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    elevation: 2,
    backgroundColor: colors.surface || '#FFFFFF',
    marginBottom: spacing?.md || 16,
    borderRadius: 12,
    minHeight: 120,
  },
  content: {
    padding: spacing?.lg || 16,
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing?.sm || 8,
  },
  title: {
    fontSize: typography?.sizes?.sm || 14,
    color: colors.onSurface || '#374151',
    fontWeight: typography?.weights?.medium || '500',
    flex: 1,
  },
  icon: {
    marginLeft: spacing?.xs || 4,
  },
  valueContainer: {
    flexDirection: 'row',
    alignItems: 'baseline',
    marginBottom: spacing?.xs || 4,
  },
  value: {
    fontSize: typography?.sizes?.xl || 24,
    fontWeight: typography?.weights?.bold || '700',
    marginRight: spacing?.sm || 8,
  },
  growth: {
    fontSize: typography?.sizes?.sm || 14,
    fontWeight: typography?.weights?.semibold || '600',
  },
  subtitle: {
    fontSize: typography?.sizes?.xs || 12,
    color: colors.outline || '#6B7280',
  },
  loadingText: {
    fontSize: typography?.sizes?.md || 16,
    color: colors.outline || '#6B7280',
    textAlign: 'center',
  },
});

export default PerformanceWidget;