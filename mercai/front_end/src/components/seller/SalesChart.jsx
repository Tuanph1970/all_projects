import React, { useState, useEffect } from 'react';
import { View, StyleSheet, Dimensions, ScrollView, ActivityIndicator } from 'react-native';
import { Surface, Text, SegmentedButtons } from 'react-native-paper';
import { colors, spacing, typography, borderRadius } from '../../constants/theme.js';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';

const screenWidth = Dimensions.get('window').width;

export const SalesChart = ({ days = 30 }) => {
  const [chartData, setChartData] = useState(null);
  const [granularity, setGranularity] = useState('day');
  const [metric, setMetric] = useState('revenue');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadChartData();
  }, [days, granularity]);

  const loadChartData = async () => {
    try {
      setLoading(true);
      const response = await sellerAnalyticsService.getRevenueTrends(days, granularity);

      // Transform API response to chart data format
      if (response && response.trends && response.trends.length > 0) {
        const chartData = {
          data: response.trends.map(item => ({
            date: item.period,
            revenue: item.revenue || 0,
            orders: item.orders || 0,
            quantity: item.items_sold || 0
          }))
        };
        setChartData(chartData);
      } else {
        // No data available
        setChartData(null);
      }
    } catch (error) {
      console.error('Failed to load chart data:', error);
      setChartData(null);
    } finally {
      setLoading(false);
    }
  };

  const formatChartData = () => {
    if (!chartData) return null;

    const labels = chartData.data.map(item => {
      const date = new Date(item.date);
      if (granularity === 'day') {
        return `${date.getMonth() + 1}/${date.getDate()}`;
      } else if (granularity === 'week') {
        return `W${Math.ceil(date.getDate() / 7)}`;
      } else {
        return date.toLocaleDateString('en-US', { month: 'short' });
      }
    });

    const datasets = [
      {
        data: chartData.data.map(item => {
          switch (metric) {
            case 'revenue':
              return item.revenue;
            case 'orders':
              return item.orders;
            case 'quantity':
              return item.quantity;
            default:
              return item.revenue;
          }
        }),
        color: (opacity = 1) => `rgba(46, 125, 50, ${opacity})`,
        strokeWidth: 2,
      },
    ];

    return { labels, datasets };
  };

  const getMetricLabel = () => {
    switch (metric) {
      case 'revenue':
        return 'Revenue (₫)';
      case 'orders':
        return 'Orders';
      case 'quantity':
        return 'Items Sold';
      default:
        return 'Revenue (₫)';
    }
  };

  const formatValue = (value) => {
    if (metric === 'revenue') {
      return `${value.toLocaleString('vi-VN')} ₫`;
    }
    return value.toString();
  };

  if (loading) {
    return (
      <Surface style={styles.container}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading chart data...</Text>
      </Surface>
    );
  }

  if (!chartData || chartData.data.length === 0) {
    return (
      <Surface style={styles.container}>
        <Text style={styles.title}>Sales Performance</Text>
        <Text style={styles.noDataText}>No sales data available for this period</Text>
      </Surface>
    );
  }

  const formattedData = formatChartData();

  return (
    <Surface style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Sales Performance</Text>
        <Text style={styles.subtitle}>{getMetricLabel()}</Text>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.controls}>
          <SegmentedButtons
            value={granularity}
            onValueChange={(value) => setGranularity(value)}
            buttons={[
              { value: 'day', label: 'Daily' },
              { value: 'week', label: 'Weekly' },
              { value: 'month', label: 'Monthly' },
            ]}
            density="small"
          />
        </View>
      </ScrollView>

      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={styles.controls}>
          <SegmentedButtons
            value={metric}
            onValueChange={(value) => setMetric(value)}
            buttons={[
              { value: 'revenue', label: 'Revenue' },
              { value: 'orders', label: 'Orders' },
              { value: 'quantity', label: 'Quantity' },
            ]}
            density="small"
          />
        </View>
      </ScrollView>

      <View style={styles.chartPlaceholder}>
        <Text style={styles.chartPlaceholderText}>📊 Sales Chart</Text>
        <Text style={styles.chartSubtext}>Chart visualization coming soon</Text>
        <View style={styles.dataPreview}>
          {chartData?.data.slice(0, 5).map((item, index) => (
            <View key={index} style={styles.dataRow}>
              <Text style={styles.dataDate}>
                {new Date(item.date).toLocaleDateString()}
              </Text>
              <Text style={styles.dataValue}>
                {formatValue(
                  metric === 'revenue' ? item.revenue :
                  metric === 'orders' ? item.orders : item.quantity
                )}
              </Text>
            </View>
          ))}
        </View>
      </View>

      <View style={styles.summary}>
        <Text style={styles.summaryText}>
          Total for period: {' '}
          {metric === 'revenue' && 
            `${chartData.data.reduce((sum, item) => sum + item.revenue, 0).toLocaleString('vi-VN')} ₫`}
          {metric === 'orders' && 
            `${chartData.data.reduce((sum, item) => sum + item.orders, 0)} orders`}
          {metric === 'quantity' && 
            `${chartData.data.reduce((sum, item) => sum + item.quantity, 0)} items`}
        </Text>
      </View>
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    elevation: 2,
    marginBottom: spacing.lg,
    padding: spacing.lg,
  },
  header: {
    marginBottom: spacing.md,
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  subtitle: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  controls: {
    marginBottom: spacing.lg,
  },
  chart: {
    marginVertical: spacing.md,
    borderRadius: borderRadius.sm,
  },
  chartPlaceholder: {
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
    padding: spacing.lg,
    alignItems: 'center',
    marginVertical: spacing.md,
  },
  chartPlaceholderText: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  chartSubtext: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.lg,
  },
  dataPreview: {
    width: '100%',
  },
  dataRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
  },
  dataDate: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  dataValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  summary: {
    marginTop: spacing.md,
    paddingTop: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.outlineVariant,
  },
  summaryText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    textAlign: 'center',
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    padding: spacing.lg,
  },
  noDataText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    padding: spacing.lg,
  },
});

export default SalesChart;