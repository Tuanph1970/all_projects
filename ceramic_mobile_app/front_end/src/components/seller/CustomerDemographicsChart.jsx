import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions, ActivityIndicator, ScrollView } from 'react-native';
import { Surface, SegmentedButtons } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';

const screenWidth = Dimensions.get('window').width;

export const CustomerDemographicsChart = ({ data }) => {
  const [activeTab, setActiveTab] = useState('segments');

  const chartConfig = {
    backgroundColor: colors.surface,
    backgroundGradientFrom: colors.surface,
    backgroundGradientTo: colors.surface,
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(59, 130, 246, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
    style: {
      borderRadius: borderRadius.md,
    },
    propsForBackgroundLines: {
      strokeDasharray: '',
      stroke: colors.outlineVariant,
      strokeWidth: 1,
    },
  };

  const tabs = [
    { key: 'segments', label: 'Customer Segments', icon: 'people' },
    { key: 'geography', label: 'Geography', icon: 'location-on' },
    { key: 'patterns', label: 'Order Patterns', icon: 'timeline' },
  ];

  if (!data) {
    return (
      <Surface style={styles.container}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading customer demographics...</Text>
      </Surface>
    );
  }

  const renderSegmentsChart = () => {
    const colorOptions = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];
    
    const mockSegments = [
      { segment: 'Premium Buyers', customer_count: 45, percentage: 35, avg_order_value: 450000 },
      { segment: 'Regular Customers', customer_count: 89, percentage: 45, avg_order_value: 280000 },
      { segment: 'Occasional Buyers', customer_count: 34, percentage: 20, avg_order_value: 150000 },
    ];

    return (
      <View style={styles.chartContainer}>
        <View style={styles.segmentDetails}>
          {mockSegments.map((segment, index) => (
            <View key={segment.segment} style={styles.segmentRow}>
              <View style={styles.segmentInfo}>
                <View style={[
                  styles.segmentColorIndicator, 
                  { backgroundColor: colorOptions[index % colorOptions.length] }
                ]} />
                <Text style={styles.segmentName}>{segment.segment}</Text>
              </View>
              <View style={styles.segmentMetrics}>
                <Text style={styles.segmentCount}>{segment.customer_count}</Text>
                <Text style={styles.segmentPercentage}>
                  {segment.percentage}%
                </Text>
                <Text style={styles.segmentValue}>
                  {segment.avg_order_value.toLocaleString('vi-VN')} ₫
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>
    );
  };

  const renderGeographyChart = () => {
    const mockGeography = [
      { state: 'Ho Chi Minh', customer_count: 89, order_count: 156, total_revenue: 8500000 },
      { state: 'Hanoi', customer_count: 67, order_count: 134, total_revenue: 7200000 },
      { state: 'Da Nang', customer_count: 34, order_count: 78, total_revenue: 4100000 },
      { state: 'Can Tho', customer_count: 23, order_count: 45, total_revenue: 2800000 },
    ];
    
    return (
      <View style={styles.chartContainer}>
        <View style={styles.geographyDetails}>
          {mockGeography.map((state, index) => (
            <View key={state.state} style={styles.geographyRow}>
              <Text style={styles.stateName}>{state.state}</Text>
              <View style={styles.stateMetrics}>
                <Text style={styles.stateCustomers}>
                  {state.customer_count} customers
                </Text>
                <Text style={styles.stateOrders}>
                  {state.order_count} orders
                </Text>
                <Text style={styles.stateRevenue}>
                  {state.total_revenue.toLocaleString('vi-VN')} ₫
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>
    );
  };

  const renderPatternsChart = () => {
    const mockPatterns = [
      { hour: 9, order_count: 23, percentage: 15, revenue: 890000 },
      { hour: 14, order_count: 34, percentage: 22, revenue: 1340000 },
      { hour: 19, order_count: 45, percentage: 28, revenue: 1780000 },
      { hour: 21, order_count: 32, percentage: 20, revenue: 1200000 },
    ];

    const peakHours = [...mockPatterns].sort((a, b) => b.order_count - a.order_count).slice(0, 2);

    return (
      <View style={styles.chartContainer}>
        <View style={styles.patternsInsights}>
          <View style={styles.insightCard}>
            <Icon name="schedule" size={24} color="#10B981" />
            <Text style={styles.insightTitle}>Peak Hours</Text>
            <Text style={styles.insightValue}>
              {peakHours[0]?.hour}:00 - {(peakHours[0]?.hour || 0) + 1}:00
            </Text>
            <Text style={styles.insightSubtext}>
              {peakHours[0]?.percentage || 0}% of orders
            </Text>
          </View>
          
          <View style={styles.insightCard}>
            <Icon name="trending-up" size={24} color="#3B82F6" />
            <Text style={styles.insightTitle}>Best Hour Revenue</Text>
            <Text style={styles.insightValue}>
              {Math.max(...mockPatterns.map(h => h.revenue)).toLocaleString('vi-VN')} ₫
            </Text>
            <Text style={styles.insightSubtext}>Peak hour revenue</Text>
          </View>
        </View>
      </View>
    );
  };

  const renderActiveChart = () => {
    switch (activeTab) {
      case 'segments':
        return renderSegmentsChart();
      case 'geography':
        return renderGeographyChart();
      case 'patterns':
        return renderPatternsChart();
      default:
        return renderSegmentsChart();
    }
  };

  return (
    <Surface style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Customer Demographics</Text>
        <Text style={styles.subtitle}>
          Analytics Overview
        </Text>
      </View>

      <View style={styles.tabContainer}>
        <SegmentedButtons
          value={activeTab}
          onValueChange={setActiveTab}
          buttons={tabs.map(tab => ({
            value: tab.key,
            label: tab.label,
            icon: tab.icon
          }))}
          density="small"
        />
      </View>

      {renderActiveChart()}
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    marginVertical: spacing.md,
    ...shadows.sm,
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
  tabContainer: {
    marginBottom: spacing.lg,
  },
  chartContainer: {
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
    padding: spacing.lg,
  },
  chart: {
    marginVertical: spacing.md,
    borderRadius: borderRadius.sm,
  },
  segmentDetails: {
    marginTop: spacing.md,
  },
  segmentRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
  },
  segmentInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  segmentColorIndicator: {
    width: 12,
    height: 12,
    borderRadius: borderRadius.xs,
    marginRight: spacing.sm,
  },
  segmentName: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  segmentMetrics: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  segmentCount: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    minWidth: 30,
    textAlign: 'center',
  },
  segmentPercentage: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    minWidth: 40,
    textAlign: 'center',
  },
  segmentValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.primary,
    minWidth: 80,
    textAlign: 'right',
  },
  geographyDetails: {
    marginTop: spacing.md,
  },
  geographyRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
  },
  stateName: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    flex: 1,
  },
  stateMetrics: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  stateCustomers: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    minWidth: 70,
    textAlign: 'center',
  },
  stateOrders: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    minWidth: 60,
    textAlign: 'center',
  },
  stateRevenue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.primary,
    minWidth: 100,
    textAlign: 'right',
  },
  patternsInsights: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: spacing.md,
  },
  insightCard: {
    flex: 1,
    alignItems: 'center',
    padding: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: borderRadius.sm,
    marginHorizontal: spacing.xs,
    ...shadows.sm,
  },
  insightTitle: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginVertical: spacing.xs,
  },
  insightValue: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  insightSubtext: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    textAlign: 'center',
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});

export default CustomerDemographicsChart;