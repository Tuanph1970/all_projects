import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { LineChart } from 'react-native-chart-kit';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';

const screenWidth = Dimensions.get('window').width;

const RevenueTrendChart = ({ data, detailed = false }) => {
  const chartConfig = {
    backgroundColor: '#ffffff',
    backgroundGradientFrom: '#ffffff',
    backgroundGradientTo: '#ffffff',
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(99, 102, 241, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
    style: {
      borderRadius: 16,
    },
    propsForDots: {
      r: '4',
      strokeWidth: '2',
      stroke: '#6366f1',
    },
    propsForBackgroundLines: {
      strokeDasharray: '',
      stroke: '#e5e7eb',
      strokeWidth: 1,
    },
  };

  // Generate mock data if service data is unavailable
  const mockData = {
    trends: [
      { period: '2024-01', revenue: 12500, orders: 45 },
      { period: '2024-02', revenue: 15800, orders: 52 },
      { period: '2024-03', revenue: 18200, orders: 61 },
      { period: '2024-04', revenue: 16900, orders: 58 },
      { period: '2024-05', revenue: 21300, orders: 67 },
      { period: '2024-06', revenue: 19800, orders: 63 },
    ],
    granularity: 'month'
  };

  const chartData = data || mockData;

  const processedChartData = {
    labels: chartData.trends.slice(-6).map(trend => 
      sellerAnalyticsService.formatTrendPeriod 
        ? sellerAnalyticsService.formatTrendPeriod(trend.period, chartData.granularity)
        : trend.period.substring(5) // Fallback: show MM from YYYY-MM
    ),
    datasets: [
      {
        data: chartData.trends.slice(-6).map(trend => trend.revenue),
        color: (opacity = 1) => `rgba(99, 102, 241, ${opacity})`,
        strokeWidth: 2,
      },
    ],
  };

  const formatYLabel = (value) => {
    const num = parseFloat(value);
    if (sellerAnalyticsService.formatNumber) {
      return sellerAnalyticsService.formatNumber(num);
    }
    // Fallback formatting
    if (num >= 1000000) {
      return `$${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `$${(num / 1000).toFixed(0)}K`;
    }
    return `$${num.toFixed(0)}`;
  };

  const totalRevenue = chartData.trends.reduce((sum, trend) => sum + trend.revenue, 0);
  const totalOrders = chartData.trends.reduce((sum, trend) => sum + trend.orders, 0);
  const averageOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0;

  const getGrowthRate = () => {
    if (chartData.trends.length < 2) return 0;
    const current = chartData.trends[chartData.trends.length - 1].revenue;
    const previous = chartData.trends[chartData.trends.length - 2].revenue;
    return previous > 0 ? ((current - previous) / previous) * 100 : 0;
  };

  const getGrowthColor = (rate) => {
    if (rate > 0) return '#10B981';
    if (rate < 0) return '#EF4444';
    return '#6B7280';
  };

  const formatCurrency = (amount) => {
    return sellerAnalyticsService.formatCurrency 
      ? sellerAnalyticsService.formatCurrency(amount)
      : `$${amount.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  };

  const formatPercentage = (value) => {
    return sellerAnalyticsService.formatPercentage 
      ? sellerAnalyticsService.formatPercentage(value)
      : `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  const getGrowthIcon = (rate) => {
    if (sellerAnalyticsService.getGrowthIcon) {
      return sellerAnalyticsService.getGrowthIcon(rate);
    }
    return rate > 0 ? '📈' : rate < 0 ? '📉' : '➡️';
  };

  const growthRate = getGrowthRate();

  return (
    <View style={styles.container}>
      {detailed && (
        <View style={styles.header}>
          <View style={styles.summaryStats}>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Total Revenue</Text>
              <Text style={styles.statValue}>
                {formatCurrency(totalRevenue)}
              </Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Total Orders</Text>
              <Text style={styles.statValue}>{totalOrders}</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statLabel}>Avg Order Value</Text>
              <Text style={styles.statValue}>
                {formatCurrency(averageOrderValue)}
              </Text>
            </View>
          </View>
          
          <View style={styles.growthIndicator}>
            <Text style={styles.growthLabel}>Growth Rate</Text>
            <Text style={[
              styles.growthValue,
              { color: getGrowthColor(growthRate) }
            ]}>
              {getGrowthIcon(growthRate)} {formatPercentage(growthRate)}
            </Text>
          </View>
        </View>
      )}

      <LineChart
        data={processedChartData}
        width={screenWidth - (detailed ? 32 : 16)}
        height={220}
        chartConfig={chartConfig}
        formatYLabel={formatYLabel}
        style={styles.chart}
        withInnerLines={true}
        withOuterLines={true}
        withHorizontalLabels={true}
        withVerticalLabels={true}
        withDots={true}
        bezier
      />

      {!detailed && chartData.trends.length > 0 && (
        <View style={styles.summary}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Latest</Text>
            <Text style={styles.summaryValue}>
              {formatCurrency(chartData.trends[chartData.trends.length - 1]?.revenue || 0)}
            </Text>
          </View>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryLabel}>Period Growth</Text>
            <Text style={[
              styles.summaryValue,
              { color: getGrowthColor(growthRate) }
            ]}>
              {formatPercentage(growthRate)}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 8,
  },
  header: {
    marginBottom: 16,
  },
  summaryStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  growthIndicator: {
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  growthLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  growthValue: {
    fontSize: 18,
    fontWeight: '600',
  },
  chart: {
    marginVertical: 8,
    borderRadius: 16,
  },
  summary: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#E5E7EB',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  summaryValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
});

export default RevenueTrendChart;