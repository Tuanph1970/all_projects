import React, { useState, useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl } from 'react-native';
import { Text, Appbar, Surface, Snackbar } from 'react-native-paper';
import { Card } from '../../components/common/Card.jsx';
import PerformanceWidget from '../../components/seller/PerformanceWidget.jsx';
import SalesChart from '../../components/seller/SalesChart.jsx';
import TopProductsList from '../../components/seller/TopProductsList.jsx';
import { colors, spacing, typography } from '../../constants/theme.js';
import sellerService, { DashboardOverview, InventoryAlert } from '../../services/sellerService.js';
import { useLanguage } from '@i18n';

export const SellerDashboardScreen = () => {
  const { t, formatCurrency } = useLanguage();
  const [overview, setOverview] = useState(null);
  const [inventoryAlerts, setInventoryAlerts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [snackbarVisible, setSnackbarVisible] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  useEffect(() => {
    loadDashboardData();
  }, [selectedPeriod]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [overviewData, alertsData] = await Promise.all([
        sellerService.getDashboardOverview(selectedPeriod),
        sellerService.getInventoryAlerts(5)
      ]);
      setOverview(overviewData);
      setInventoryAlerts(alertsData);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      showSnackbar(t('seller.loadDashboardError'));
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const showSnackbar = (message) => {
    setSnackbarMessage(message);
    setSnackbarVisible(true);
  };

  const getAlertCount = () => {
    if (!inventoryAlerts) return 0;
    return inventoryAlerts.alerts.out_of_stock.count + inventoryAlerts.alerts.low_stock.count;
  };

  return (
    <View style={styles.container} testID="seller-dashboard-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.Content title={t('seller.dashboard')} />
      </Appbar.Header>

      <ScrollView
        style={styles.content}
        testID="seller-dashboard-scroll"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            testID="seller-dashboard-refresh"
          />
        }
      >
        {/* Performance Widgets */}
        <View style={styles.widgetsContainer} testID="seller-dashboard-widgets">
          {overview && (
            <View style={styles.widgetRow}>
              <PerformanceWidget
                testID="seller-dashboard-total-sales"
                title={t('seller.totalSales')}
                value={formatCurrency(overview.total_sales)}
                style={styles.widgetHalf}
              />
              <PerformanceWidget
                testID="seller-dashboard-total-orders"
                title={t('seller.orders')}
                value={(overview.total_orders ?? 0).toString()}
                style={styles.widgetHalf}
              />
            </View>
          )}
        </View>

        {/* Inventory Alerts */}
        {getAlertCount() > 0 && (
          <Card style={styles.alertCard} testID="seller-dashboard-alerts">
            <View style={styles.alertHeader}>
              <Text style={styles.alertTitle} testID="seller-dashboard-alerts-title">⚠️ {t('seller.inventoryAlerts')}</Text>
              <Text style={styles.alertCount} testID="seller-dashboard-alerts-count">{getAlertCount()}</Text>
            </View>
            {inventoryAlerts?.alerts.out_of_stock.count > 0 && (
              <Text style={styles.alertText} testID="seller-dashboard-out-of-stock">
                {t('seller.productsOutOfStock', { count: inventoryAlerts.alerts.out_of_stock.count })}
              </Text>
            )}
            {inventoryAlerts?.alerts.low_stock.count > 0 && (
              <Text style={styles.alertText} testID="seller-dashboard-low-stock">
                {t('seller.productsLowStock', { count: inventoryAlerts.alerts.low_stock.count })}
              </Text>
            )}
          </Card>
        )}

        {/* Sales Chart */}
        {overview && (
          <SalesChart
            testID="seller-dashboard-sales-chart"
            data={overview.sales_data}
            period={selectedPeriod}
          />
        )}

        {/* Top Products */}
        <TopProductsList
          testID="seller-dashboard-top-products"
          products={overview?.top_products || []}
          onProductPress={(product) => {
            showSnackbar(t('seller.productSelected', { name: product.name }));
          }}
        />
      </ScrollView>

      {/* Snackbar for notifications */}
      <Snackbar
        visible={snackbarVisible}
        onDismiss={() => setSnackbarVisible(false)}
        duration={3000}
      >
        {snackbarMessage}
      </Snackbar>
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
  widgetsContainer: {
    marginBottom: spacing.lg,
  },
  widgetRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  widgetHalf: {
    flex: 0.48,
    marginHorizontal: spacing.xs,
  },
  alertCard: {
    elevation: 2,
    backgroundColor: colors.errorContainer,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  alertTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onErrorContainer,
  },
  alertCount: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.bold,
    color: colors.onErrorContainer,
    backgroundColor: colors.error,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 12,
  },
  alertText: {
    fontSize: typography.sizes.sm,
    color: colors.onErrorContainer,
    marginBottom: spacing.xs,
  },
});