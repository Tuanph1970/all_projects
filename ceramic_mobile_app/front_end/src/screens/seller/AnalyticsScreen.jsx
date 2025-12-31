import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { Text, Appbar, Card, ActivityIndicator, Chip } from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
// Note: Components below need to be implemented
// import SalesChart from '../../components/seller/SalesChart.js';
// import TopProductsList from '../../components/seller/TopProductsList.js';
// import InventoryOverview from '../../components/seller/InventoryOverview.js';
// import PerformanceWidget from '../../components/seller/PerformanceWidget.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';
import { useTranslation } from '@i18n';

export const AnalyticsScreen = () => {
  const navigation = useNavigation();
  const t = useTranslation();

  // State
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAnalytics();
  }, [selectedPeriod]);

  const loadAnalytics = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const analyticsData = await sellerAnalyticsService.getDashboardAnalytics(selectedPeriod);
      setAnalytics(analyticsData);
    } catch (error) {
      console.error('Error loading analytics:', error);
      setError(error.message || t('analytics.loadError'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadAnalytics(true);
  };

  const handlePeriodChange = (period) => {
    setSelectedPeriod(period);
  };

  const handleProductPress = (product) => {
    navigation.navigate('ProductDetails', { productId: product.id });
  };

  const formatCurrency = (amount) => {
    return `$${amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatPercentage = (value) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  if (loading && !analytics) {
    return (
      <View style={styles.container} testID="analytics-screen">
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="analytics-back-button" />
          <Appbar.Content title={t('analytics.title')} />
        </Appbar.Header>
        <View style={styles.loadingContainer} testID="analytics-loading">
          <ActivityIndicator size="large" color={colors.primary} testID="analytics-loading-indicator" />
          <Text style={styles.loadingText}>{t('analytics.loading')}</Text>
        </View>
      </View>
    );
  }

  if (error && !analytics) {
    return (
      <View style={styles.container} testID="analytics-screen-error">
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} testID="analytics-back-button" />
          <Appbar.Content title={t('analytics.title')} />
        </Appbar.Header>
        <View style={styles.errorContainer} testID="analytics-error-container">
          <Text style={styles.errorTitle} testID="analytics-error-title">{t('analytics.loadFailed')}</Text>
          <Text style={styles.errorText} testID="analytics-error-text">{error}</Text>
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
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            testID="analytics-refresh"
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {/* Period Selection */}
        <Card style={styles.periodCard} testID="analytics-period-card">
          <Text style={styles.sectionTitle}>{t('analytics.timePeriod')}</Text>
          <View style={styles.chipContainer} testID="analytics-period-chips">
            {[7, 30, 90, 365].map((days) => (
              <Chip
                key={days}
                testID={`analytics-period-${days}`}
                mode={selectedPeriod === days ? 'flat' : 'outlined'}
                selected={selectedPeriod === days}
                onPress={() => handlePeriodChange(days)}
                style={styles.periodChip}
              >
                {days === 7 ? t('analytics.7days') : days === 30 ? t('analytics.30days') : days === 90 ? t('analytics.3months') : t('analytics.1year')}
              </Chip>
            ))}
          </View>
        </Card>

        {/* Sales Analytics */}
        <Card style={styles.card} testID="analytics-sales-card">
          <Text style={styles.sectionTitle}>{t('analytics.salesAnalytics')}</Text>
          {analytics && (
            <View style={styles.metricsContainer} testID="analytics-sales-metrics">
              <View style={styles.metricItem} testID="analytics-revenue-metric">
                <Text style={styles.metricTitle}>{t('analytics.totalRevenue')}</Text>
                <Text style={styles.metricValue} testID="analytics-revenue-value">{formatCurrency(analytics.total_revenue || 0)}</Text>
                <Text style={[styles.metricChange, analytics.revenue_growth >= 0 ? styles.positiveChange : styles.negativeChange]} testID="analytics-revenue-growth">
                  {formatPercentage(analytics.revenue_growth || 0)}
                </Text>
              </View>
              <View style={styles.metricItem} testID="analytics-orders-metric">
                <Text style={styles.metricTitle}>{t('analytics.totalOrders')}</Text>
                <Text style={styles.metricValue} testID="analytics-orders-value">{analytics.total_orders?.toString() || '0'}</Text>
                <Text style={[styles.metricChange, analytics.order_growth >= 0 ? styles.positiveChange : styles.negativeChange]} testID="analytics-orders-growth">
                  {formatPercentage(analytics.order_growth || 0)}
                </Text>
              </View>
            </View>
          )}
          <Text style={styles.comingSoon}>{t('analytics.salesChartComingSoon')}</Text>
        </Card>

        {/* Inventory Management */}
        <Card style={styles.card} testID="analytics-inventory-card">
          <Text style={styles.sectionTitle}>{t('analytics.inventoryOverview')}</Text>
          <Text style={styles.comingSoon}>{t('analytics.inventoryComingSoon')}</Text>
        </Card>

        {/* Top Products Performance */}
        <Card style={styles.card} testID="analytics-top-products-card">
          <Text style={styles.sectionTitle}>{t('analytics.topProducts')}</Text>
          <Text style={styles.comingSoon}>{t('analytics.topProductsComingSoon')}</Text>
        </Card>

        {/* Customer Analytics */}
        <Card style={styles.card} testID="analytics-customer-card">
          <Text style={styles.sectionTitle}>{t('analytics.customerInsights')}</Text>
          {analytics?.customer_data ? (
            <View style={styles.metricsContainer} testID="analytics-customer-metrics">
              <View style={styles.metricItem} testID="analytics-new-customers-metric">
                <Text style={styles.metricTitle}>{t('analytics.newCustomers')}</Text>
                <Text style={styles.metricValue} testID="analytics-new-customers-value">{analytics.customer_data.new_customers?.toString() || '0'}</Text>
                <Text style={[styles.metricChange, analytics.customer_data.customer_growth >= 0 ? styles.positiveChange : styles.negativeChange]} testID="analytics-new-customers-growth">
                  {formatPercentage(analytics.customer_data.customer_growth || 0)}
                </Text>
              </View>
              <View style={styles.metricItem} testID="analytics-repeat-rate-metric">
                <Text style={styles.metricTitle}>{t('analytics.repeatRate')}</Text>
                <Text style={styles.metricValue} testID="analytics-repeat-rate-value">{`${analytics.customer_data.repeat_rate?.toFixed(1) || '0'}%`}</Text>
                <Text style={[styles.metricChange, analytics.customer_data.repeat_rate_change >= 0 ? styles.positiveChange : styles.negativeChange]} testID="analytics-repeat-rate-growth">
                  {formatPercentage(analytics.customer_data.repeat_rate_change || 0)}
                </Text>
              </View>
            </View>
          ) : (
            <Text style={styles.comingSoon}>{t('analytics.customerComingSoon')}</Text>
          )}
        </Card>
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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  errorTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.error,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  errorText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
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
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  periodChip: {
    marginBottom: spacing.xs,
  },
  metricsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  metricItem: {
    flex: 0.48,
    padding: spacing.sm,
    backgroundColor: colors.surfaceVariant,
    borderRadius: 8,
    alignItems: 'center',
  },
  metricTitle: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  metricValue: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  metricChange: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    textAlign: 'center',
  },
  positiveChange: {
    color: colors.success || '#4CAF50',
  },
  negativeChange: {
    color: colors.error,
  },
  comingSoon: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    fontStyle: 'italic',
    padding: spacing.lg,
  },
});