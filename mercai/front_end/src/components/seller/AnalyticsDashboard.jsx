import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { Dimensions } from 'react-native';
import { Surface, Button, SegmentedButtons } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';

import AnalyticsCard from './AnalyticsCard.jsx';
import RevenueTrendChart from './RevenueTrendChart.jsx';
import CategoryPerformanceChart from './CategoryPerformanceChart.jsx';
import CustomerDemographicsChart from './CustomerDemographicsChart.jsx';
import TopProductsList from './TopProductsList.jsx';
import PerformanceMetricsCard from './PerformanceMetricsCard.jsx';
import InsightsPanel from './InsightsPanel.jsx';

const screenWidth = Dimensions.get('window').width;

export const AnalyticsDashboard = ({ navigation }) => {
  const [state, setState] = useState({
    dashboard: null,
    revenueTrends: null,
    categoryPerformance: null,
    customerDemographics: null,
    performanceMetrics: null,
    topProducts: null,
    comparison: null,
    selectedPeriod: 30,
    selectedTab: 'overview',
    isLoading: true,
    isRefreshing: false,
    error: null,
  });

  const periodOptions = [
    { label: '7 days', value: 7 },
    { label: '30 days', value: 30 },
    { label: '90 days', value: 90 },
    { label: '1 year', value: 365 },
  ];

  const tabOptions = [
    { key: 'overview', label: 'Overview', icon: 'dashboard' },
    { key: 'revenue', label: 'Revenue', icon: 'attach-money' },
    { key: 'customers', label: 'Customers', icon: 'people' },
    { key: 'products', label: 'Products', icon: 'inventory' },
    { key: 'insights', label: 'Insights', icon: 'lightbulb-outline' },
  ];

  useEffect(() => {
    loadAnalyticsData();
  }, [state.selectedPeriod]);

  const loadAnalyticsData = async () => {
    try {
      setState(prev => ({ ...prev, isLoading: true, error: null }));

      // Mock data for now - replace with actual service calls
      const mockDashboard = {
        total_revenue: 12500000,
        total_orders: 156,
        avg_order_value: 80128,
        customer_count: 89,
        product_views: 2341,
        conversion_rate: 6.7,
      };

      const mockRevenueTrends = {
        data: Array.from({ length: 30 }, (_, i) => ({
          date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toISOString(),
          revenue: Math.random() * 500000 + 200000,
        }))
      };

      setState(prev => ({
        ...prev,
        dashboard: mockDashboard,
        revenueTrends: mockRevenueTrends,
        categoryPerformance: null,
        customerDemographics: null,
        performanceMetrics: mockDashboard,
        topProducts: null,
        comparison: null,
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error loading analytics data:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to load analytics data',
        isLoading: false,
      }));
    }
  };

  const handleRefresh = async () => {
    setState(prev => ({ ...prev, isRefreshing: true }));
    await loadAnalyticsData();
    setState(prev => ({ ...prev, isRefreshing: false }));
  };

  const handlePeriodChange = (period) => {
    setState(prev => ({ ...prev, selectedPeriod: period }));
  };

  const handleTabChange = (tab) => {
    setState(prev => ({ ...prev, selectedTab: tab }));
  };

  const handleExportData = async () => {
    try {
      Alert.alert('Export', 'Analytics data exported successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to export data');
    }
  };

  const renderPeriodSelector = () => (
    <View style={styles.periodSelector}>
      <SegmentedButtons
        value={state.selectedPeriod}
        onValueChange={handlePeriodChange}
        buttons={periodOptions.map(option => ({
          value: option.value,
          label: option.label
        }))}
        density="small"
      />
    </View>
  );

  const renderTabSelector = () => (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.tabSelector}>
      {tabOptions.map((tab) => (
        <TouchableOpacity
          key={tab.key}
          style={[
            styles.tabButton,
            state.selectedTab === tab.key && styles.selectedTabButton,
          ]}
          onPress={() => handleTabChange(tab.key)}
        >
          <Icon
            name={tab.icon}
            size={20}
            color={state.selectedTab === tab.key ? colors.primary : colors.outline}
          />
          <Text
            style={[
              styles.tabButtonText,
              state.selectedTab === tab.key && styles.selectedTabButtonText,
            ]}
          >
            {tab.label}
          </Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );

  const renderOverviewTab = () => {
    if (!state.dashboard) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.metricsGrid}>
          <AnalyticsCard
            title="Total Revenue"
            value={`${state.dashboard.total_revenue.toLocaleString('vi-VN')} ₫`}
            icon="attach-money"
            color={colors.success}
          />
          <AnalyticsCard
            title="Total Orders"
            value={state.dashboard.total_orders.toString()}
            icon="shopping-cart"
            color={colors.primary}
          />
          <AnalyticsCard
            title="Average Order"
            value={`${state.dashboard.avg_order_value.toLocaleString('vi-VN')} ₫`}
            icon="receipt"
            color={colors.info}
          />
          <AnalyticsCard
            title="Customers"
            value={state.dashboard.customer_count.toString()}
            icon="people"
            color={colors.warning}
          />
        </View>

        {state.revenueTrends && (
          <View style={styles.chartContainer}>
            <Text style={styles.chartTitle}>Revenue Trend</Text>
            <RevenueTrendChart data={state.revenueTrends} />
          </View>
        )}
      </View>
    );
  };

  const renderRevenueTab = () => {
    if (!state.revenueTrends) return null;

    return (
      <View style={styles.tabContent}>
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Revenue Analysis</Text>
          <RevenueTrendChart data={state.revenueTrends} />
        </View>
      </View>
    );
  };

  const renderCustomersTab = () => {
    return (
      <View style={styles.tabContent}>
        <Text style={styles.sectionTitle}>Customer Analytics Coming Soon</Text>
      </View>
    );
  };

  const renderProductsTab = () => {
    return (
      <View style={styles.tabContent}>
        <TopProductsList
          days={state.selectedPeriod}
          onProductPress={(product) => {
            // Navigate to product details
          }}
        />
      </View>
    );
  };

  const renderInsightsTab = () => {
    if (!state.dashboard) return null;

    return (
      <View style={styles.tabContent}>
        <InsightsPanel
          data={state.dashboard}
          metrics={state.performanceMetrics}
        />
      </View>
    );
  };

  const renderTabContent = () => {
    switch (state.selectedTab) {
      case 'overview':
        return renderOverviewTab();
      case 'revenue':
        return renderRevenueTab();
      case 'customers':
        return renderCustomersTab();
      case 'products':
        return renderProductsTab();
      case 'insights':
        return renderInsightsTab();
      default:
        return renderOverviewTab();
    }
  };

  if (state.isLoading && !state.dashboard) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading Analytics...</Text>
      </View>
    );
  }

  if (state.error) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>{state.error}</Text>
        <TouchableOpacity style={styles.retryButton} onPress={loadAnalyticsData}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Surface style={styles.header}>
        <View style={styles.headerContent}>
          <Text style={styles.headerTitle}>Analytics Dashboard</Text>
          <Button
            mode="outlined"
            onPress={handleExportData}
            icon="file-download"
            style={styles.exportButton}
            compact
          >
            Export
          </Button>
        </View>
        {renderPeriodSelector()}
        {renderTabSelector()}
      </Surface>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={state.isRefreshing}
            onRefresh={handleRefresh}
            colors={[colors.primary]}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {renderTabContent()}
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
    paddingTop: spacing.md,
    paddingBottom: spacing.lg,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  headerTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    color: colors.onSurface,
  },
  exportButton: {
    borderColor: colors.primary,
  },
  periodSelector: {
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  tabSelector: {
    paddingHorizontal: spacing.md,
  },
  tabButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginRight: spacing.sm,
    borderRadius: borderRadius.sm,
    backgroundColor: colors.surfaceVariant,
  },
  selectedTabButton: {
    backgroundColor: colors.primaryContainer,
  },
  tabButtonText: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.outline,
    marginLeft: spacing.xs,
  },
  selectedTabButtonText: {
    color: colors.primary,
  },
  content: {
    flex: 1,
  },
  tabContent: {
    padding: spacing.md,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: spacing.lg,
    gap: spacing.md,
  },
  chartContainer: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    ...shadows.sm,
  },
  chartTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    marginTop: spacing.md,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
    padding: spacing.lg,
  },
  errorText: {
    fontSize: typography.sizes.md,
    color: colors.error,
    textAlign: 'center',
    marginVertical: spacing.md,
  },
  retryButton: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.md,
  },
  retryButtonText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onPrimary,
  },
});

export default AnalyticsDashboard;