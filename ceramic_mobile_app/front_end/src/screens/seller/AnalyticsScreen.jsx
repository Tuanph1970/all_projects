import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, Dimensions } from 'react-native';
import { Text, Appbar, Card, ActivityIndicator, Chip, Divider, ProgressBar } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';
import { useTranslation } from '@i18n';

const { width } = Dimensions.get('window');

export const AnalyticsScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();

  // State
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [error, setError] = useState(null);

  // Analytics data
  const [dashboard, setDashboard] = useState(null);
  const [revenueTrends, setRevenueTrends] = useState(null);
  const [categoryPerformance, setCategoryPerformance] = useState(null);
  const [customerDemographics, setCustomerDemographics] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [topProducts, setTopProducts] = useState(null);

  useEffect(() => {
    loadAllAnalytics();
  }, [selectedPeriod]);

  const loadAllAnalytics = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      // Load all analytics data in parallel
      const [
        dashboardData,
        trendsData,
        categoryData,
        customerData,
        metricsData,
        productsData
      ] = await Promise.allSettled([
        sellerAnalyticsService.getDashboardAnalytics(selectedPeriod),
        sellerAnalyticsService.getRevenueTrends(selectedPeriod, 'day'),
        sellerAnalyticsService.getCategoryPerformance(selectedPeriod),
        sellerAnalyticsService.getCustomerDemographics(selectedPeriod),
        sellerAnalyticsService.getPerformanceMetrics(selectedPeriod),
        sellerAnalyticsService.getTopProducts(selectedPeriod, 'revenue', 5)
      ]);

      // Set data from successful requests
      if (dashboardData.status === 'fulfilled') setDashboard(dashboardData.value);
      if (trendsData.status === 'fulfilled') setRevenueTrends(trendsData.value);
      if (categoryData.status === 'fulfilled') setCategoryPerformance(categoryData.value);
      if (customerData.status === 'fulfilled') setCustomerDemographics(customerData.value);
      if (metricsData.status === 'fulfilled') setPerformanceMetrics(metricsData.value);
      if (productsData.status === 'fulfilled') setTopProducts(productsData.value);

    } catch (error) {
      console.error('Error loading analytics:', error);
      setError(error.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadAllAnalytics(true);
  };

  const handlePeriodChange = (period) => {
    setSelectedPeriod(period);
  };

  const formatCurrency = (amount) => {
    if (amount == null) return '$0.00';
    return `$${Number(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (value) => {
    if (value == null) return '+0.0%';
    const sign = value >= 0 ? '+' : '';
    return `${sign}${Number(value).toFixed(1)}%`;
  };

  const formatNumber = (num) => {
    if (num == null) return '0';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
  };

  if (loading && !dashboard) {
    return (
      <View style={styles.container} testID="analytics-screen">
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="analytics-back-button" />
          <Appbar.Content title={t('analytics.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer} testID="analytics-loading">
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading analytics...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container} testID="analytics-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="analytics-back-button" />
        <Appbar.Content title={t('analytics.title')} />
      </Appbar.Header>

      <ScrollView
        style={styles.content}
        testID="analytics-scroll"
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Period Selection */}
        <Card style={styles.periodCard} testID="analytics-period-card">
          <Text style={styles.sectionTitle}>Time Period</Text>
          <View style={styles.chipContainer}>
            {[7, 30, 90, 365].map((days) => (
              <Chip
                key={days}
                testID={`analytics-period-${days}`}
                mode={selectedPeriod === days ? 'flat' : 'outlined'}
                selected={selectedPeriod === days}
                onPress={() => handlePeriodChange(days)}
                style={styles.periodChip}
              >
                {days === 7 ? '7 Days' : days === 30 ? '30 Days' : days === 90 ? '3 Months' : '1 Year'}
              </Chip>
            ))}
          </View>
        </Card>

        {/* Sales Overview */}
        <Card style={styles.card} testID="analytics-sales-card">
          <Text style={styles.sectionTitle}>📊 Sales Overview</Text>
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>Total Revenue</Text>
              <Text style={styles.metricValue}>{formatCurrency(dashboard?.total_revenue)}</Text>
              <Text style={[styles.metricChange, (dashboard?.revenue_growth || 0) >= 0 ? styles.positive : styles.negative]}>
                {formatPercentage(dashboard?.revenue_growth)}
              </Text>
            </View>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>Total Orders</Text>
              <Text style={styles.metricValue}>{formatNumber(dashboard?.total_orders)}</Text>
              <Text style={[styles.metricChange, (dashboard?.order_growth || 0) >= 0 ? styles.positive : styles.negative]}>
                {formatPercentage(dashboard?.order_growth)}
              </Text>
            </View>
          </View>
          <View style={styles.metricsRow}>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>Avg Order Value</Text>
              <Text style={styles.metricValue}>{formatCurrency(dashboard?.avg_order_value)}</Text>
            </View>
            <View style={styles.metricBox}>
              <Text style={styles.metricLabel}>Total Customers</Text>
              <Text style={styles.metricValue}>{formatNumber(dashboard?.total_customers)}</Text>
            </View>
          </View>
        </Card>

        {/* Revenue Trends */}
        <Card style={styles.card} testID="analytics-trends-card">
          <Text style={styles.sectionTitle}>📈 Revenue Trends</Text>
          {revenueTrends?.trends && revenueTrends.trends.length > 0 ? (
            <View>
              <View style={styles.trendSummary}>
                <Text style={styles.trendLabel}>Period Total:</Text>
                <Text style={styles.trendValue}>{formatCurrency(revenueTrends.summary?.total_revenue)}</Text>
              </View>
              <View style={styles.trendSummary}>
                <Text style={styles.trendLabel}>Daily Average:</Text>
                <Text style={styles.trendValue}>{formatCurrency(revenueTrends.summary?.avg_daily_revenue)}</Text>
              </View>
              <Divider style={styles.divider} />
              <Text style={styles.subTitle}>Recent Days</Text>
              {revenueTrends.trends.slice(-5).map((trend, index) => (
                <View key={index} style={styles.trendRow}>
                  <Text style={styles.trendDate}>{new Date(trend.period).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</Text>
                  <Text style={styles.trendAmount}>{formatCurrency(trend.revenue)}</Text>
                  <Text style={styles.trendOrders}>{trend.orders} orders</Text>
                </View>
              ))}
            </View>
          ) : (
            <Text style={styles.noData}>No revenue trend data available</Text>
          )}
        </Card>

        {/* Category Performance */}
        <Card style={styles.card} testID="analytics-category-card">
          <Text style={styles.sectionTitle}>🏷️ Category Performance</Text>
          {categoryPerformance?.categories && categoryPerformance.categories.length > 0 ? (
            <View>
              {categoryPerformance.categories.slice(0, 5).map((category, index) => (
                <View key={index} style={styles.categoryRow}>
                  <View style={styles.categoryInfo}>
                    <Text style={styles.categoryName}>{category.category_name || 'Unknown'}</Text>
                    <Text style={styles.categoryStats}>
                      {category.total_orders} orders • {formatCurrency(category.total_revenue)}
                    </Text>
                  </View>
                  <View style={styles.categoryShare}>
                    <Text style={styles.shareText}>{(category.revenue_share || 0).toFixed(1)}%</Text>
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <Text style={styles.noData}>No category data available</Text>
          )}
        </Card>

        {/* Top Products */}
        <Card style={styles.card} testID="analytics-products-card">
          <Text style={styles.sectionTitle}>🏆 Top Products</Text>
          {topProducts?.products && topProducts.products.length > 0 ? (
            <View>
              {topProducts.products.slice(0, 5).map((product, index) => (
                <View key={index} style={styles.productRow}>
                  <Text style={styles.productRank}>#{index + 1}</Text>
                  <View style={styles.productInfo}>
                    <Text style={styles.productName} numberOfLines={1}>{product.product_name}</Text>
                    <Text style={styles.productStats}>
                      {product.total_quantity} sold • {formatCurrency(product.total_revenue)}
                    </Text>
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <Text style={styles.noData}>No top products data available</Text>
          )}
        </Card>

        {/* Customer Demographics */}
        <Card style={styles.card} testID="analytics-customer-card">
          <Text style={styles.sectionTitle}>👥 Customer Insights</Text>
          {customerDemographics ? (
            <View>
              <View style={styles.metricsRow}>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>New Customers</Text>
                  <Text style={styles.metricValue}>{formatNumber(customerDemographics.acquisition?.new_customers)}</Text>
                </View>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>Returning</Text>
                  <Text style={styles.metricValue}>{formatNumber(customerDemographics.acquisition?.returning_customers)}</Text>
                </View>
              </View>
              {customerDemographics.geographic?.top_locations && (
                <View>
                  <Text style={styles.subTitle}>Top Locations</Text>
                  {customerDemographics.geographic.top_locations.slice(0, 3).map((loc, index) => (
                    <View key={index} style={styles.locationRow}>
                      <Text style={styles.locationName}>{loc.city || loc.state || 'Unknown'}</Text>
                      <Text style={styles.locationCount}>{loc.customer_count} customers</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          ) : (
            <Text style={styles.noData}>No customer data available</Text>
          )}
        </Card>

        {/* Performance Metrics */}
        <Card style={styles.card} testID="analytics-performance-card">
          <Text style={styles.sectionTitle}>⚡ Performance Metrics</Text>
          {performanceMetrics ? (
            <View>
              <View style={styles.metricsRow}>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>Conversion Rate</Text>
                  <Text style={styles.metricValue}>{(performanceMetrics.efficiency_metrics?.conversion_rate || 0).toFixed(1)}%</Text>
                </View>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>Refund Rate</Text>
                  <Text style={styles.metricValue}>{(performanceMetrics.efficiency_metrics?.refund_rate || 0).toFixed(1)}%</Text>
                </View>
              </View>
              <View style={styles.metricsRow}>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>Avg Fulfillment</Text>
                  <Text style={styles.metricValue}>{(performanceMetrics.current_period?.avg_fulfillment_days || 0).toFixed(1)} days</Text>
                </View>
                <View style={styles.metricBox}>
                  <Text style={styles.metricLabel}>Customer LTV</Text>
                  <Text style={styles.metricValue}>{formatCurrency(performanceMetrics.efficiency_metrics?.customer_lifetime_value)}</Text>
                </View>
              </View>
              {performanceMetrics.growth_rates && (
                <View style={styles.growthSection}>
                  <Text style={styles.subTitle}>Growth Rates</Text>
                  <View style={styles.growthRow}>
                    <Text style={styles.growthLabel}>Revenue:</Text>
                    <Text style={[styles.growthValue, (performanceMetrics.growth_rates.revenue_growth || 0) >= 0 ? styles.positive : styles.negative]}>
                      {formatPercentage(performanceMetrics.growth_rates.revenue_growth)}
                    </Text>
                  </View>
                  <View style={styles.growthRow}>
                    <Text style={styles.growthLabel}>Orders:</Text>
                    <Text style={[styles.growthValue, (performanceMetrics.growth_rates.order_growth || 0) >= 0 ? styles.positive : styles.negative]}>
                      {formatPercentage(performanceMetrics.growth_rates.order_growth)}
                    </Text>
                  </View>
                  <View style={styles.growthRow}>
                    <Text style={styles.growthLabel}>Customers:</Text>
                    <Text style={[styles.growthValue, (performanceMetrics.growth_rates.customer_growth || 0) >= 0 ? styles.positive : styles.negative]}>
                      {formatPercentage(performanceMetrics.growth_rates.customer_growth)}
                    </Text>
                  </View>
                </View>
              )}
            </View>
          ) : (
            <Text style={styles.noData}>No performance data available</Text>
          )}
        </Card>

        {/* Bottom spacing */}
        <View style={{ height: 20 }} />
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.surface,
  },
  header: {
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
    padding: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
    fontSize: typography.sizes.md,
  },
  periodCard: {
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  card: {
    marginBottom: spacing.md,
    padding: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  subTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: '#666666',
    marginTop: spacing.sm,
    marginBottom: spacing.sm,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  periodChip: {
    marginBottom: spacing.xs,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  metricBox: {
    flex: 0.48,
    padding: spacing.sm,
    backgroundColor: colors.surfaceVariant,
    borderRadius: 8,
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: typography.sizes.sm,
    color: '#666666',
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  metricValue: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    textAlign: 'center',
  },
  metricChange: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    marginTop: spacing.xs,
  },
  positive: {
    color: '#4CAF50',
  },
  negative: {
    color: '#F44336',
  },
  divider: {
    marginVertical: spacing.sm,
  },
  noData: {
    fontSize: typography.sizes.md,
    color: '#999999',
    textAlign: 'center',
    fontStyle: 'italic',
    padding: spacing.md,
  },
  // Trend styles
  trendSummary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
  },
  trendLabel: {
    fontSize: typography.sizes.md,
    color: '#666666',
  },
  trendValue: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  trendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  trendDate: {
    fontSize: typography.sizes.sm,
    color: '#666666',
    width: 60,
  },
  trendAmount: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.primary,
    flex: 1,
    textAlign: 'center',
  },
  trendOrders: {
    fontSize: typography.sizes.sm,
    color: '#999999',
    width: 70,
    textAlign: 'right',
  },
  // Category styles
  categoryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  categoryInfo: {
    flex: 1,
  },
  categoryName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  categoryStats: {
    fontSize: typography.sizes.sm,
    color: '#666666',
    marginTop: 2,
  },
  categoryShare: {
    backgroundColor: colors.primary,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 12,
  },
  shareText: {
    fontSize: typography.sizes.sm,
    color: '#FFFFFF',
    fontWeight: typography.weights.medium,
  },
  // Product styles
  productRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  productRank: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.bold,
    color: colors.primary,
    width: 30,
  },
  productInfo: {
    flex: 1,
  },
  productName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
  },
  productStats: {
    fontSize: typography.sizes.sm,
    color: '#666666',
    marginTop: 2,
  },
  // Location styles
  locationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
  },
  locationName: {
    fontSize: typography.sizes.sm,
    color: colors.onSurface,
  },
  locationCount: {
    fontSize: typography.sizes.sm,
    color: '#666666',
  },
  // Growth styles
  growthSection: {
    marginTop: spacing.sm,
    paddingTop: spacing.sm,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  growthRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: spacing.xs,
  },
  growthLabel: {
    fontSize: typography.sizes.sm,
    color: '#666666',
  },
  growthValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
});
