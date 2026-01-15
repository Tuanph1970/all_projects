import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl
} from 'react-native';
import {
  Surface,
  Text,
  Card,
  ActivityIndicator,
  Appbar,
  Chip
} from 'react-native-paper';
import { useNavigation } from '@react-navigation/native';
import orderFulfillmentService from '../../services/orderFulfillmentService.js';
import { colors, spacing } from '../../constants/theme.js';

const StatCard = ({ title, value, subtitle, color, icon }) => (
  <Card style={styles.statCard}>
    <Card.Content>
      <View style={styles.statHeader}>
        <Text style={styles.statIcon}>{icon}</Text>
        <Text style={[styles.statValue, { color: color || colors.primary }]}>{value}</Text>
      </View>
      <Text style={styles.statTitle}>{title}</Text>
      {subtitle && <Text style={styles.statSubtitle}>{subtitle}</Text>}
    </Card.Content>
  </Card>
);

const OrderAnalyticsScreen = () => {
  const navigation = useNavigation();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState(null);

  const loadAnalytics = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);

      console.log('[DEBUG] Fetching fulfillment analytics...');
      const response = await orderFulfillmentService.getFulfillmentAnalytics(30);
      console.log('[DEBUG] Fulfillment analytics response:', JSON.stringify(response));

      setAnalytics(response.data || response);
    } catch (err) {
      console.error('[DEBUG] Failed to load analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, []);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading analytics...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title="Fulfillment Analytics" />
      </Appbar.Header>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => loadAnalytics(true)}
            colors={[colors.primary]}
          />
        }
      >
        {error ? (
          <Card style={styles.errorCard}>
            <Card.Content>
              <Text style={styles.errorText}>{error}</Text>
            </Card.Content>
          </Card>
        ) : (
          <>
            {/* Period Info */}
            <Chip style={styles.periodChip} icon="calendar">
              Last {analytics?.period_days || 30} days
            </Chip>

            {/* Processing Metrics */}
            <Text style={styles.sectionTitle}>Processing Metrics</Text>
            <View style={styles.statsRow}>
              <StatCard
                title="Avg Processing"
                value={`${(analytics?.processing_metrics?.avg_processing_days || 0).toFixed(1)} days`}
                icon="📦"
                color="#3b82f6"
              />
              <StatCard
                title="Avg Shipping"
                value={`${(analytics?.processing_metrics?.avg_shipping_days || 0).toFixed(1)} days`}
                icon="🚚"
                color="#8b5cf6"
              />
            </View>

            {/* Quality Metrics */}
            <Text style={styles.sectionTitle}>Quality Metrics</Text>
            <View style={styles.statsRow}>
              <StatCard
                title="Delivered"
                value={analytics?.quality_metrics?.total_delivered || 0}
                icon="✅"
                color="#10b981"
              />
              <StatCard
                title="Refunded"
                value={analytics?.quality_metrics?.total_refunded || 0}
                icon="💸"
                color="#ef4444"
              />
            </View>
            <View style={styles.statsRow}>
              <StatCard
                title="Refund Rate"
                value={`${(analytics?.quality_metrics?.refund_rate || 0).toFixed(1)}%`}
                subtitle="Lower is better"
                icon="📊"
                color={analytics?.quality_metrics?.refund_rate > 5 ? '#ef4444' : '#10b981'}
              />
              <StatCard
                title="On-Time Delivery"
                value={`${(analytics?.quality_metrics?.on_time_delivery_rate || 0).toFixed(1)}%`}
                subtitle="Higher is better"
                icon="⏱️"
                color={analytics?.quality_metrics?.on_time_delivery_rate >= 90 ? '#10b981' : '#f59e0b'}
              />
            </View>

            {/* Fulfillment Health */}
            <Text style={styles.sectionTitle}>Fulfillment Health</Text>
            <View style={styles.statsRow}>
              <StatCard
                title="Need Attention"
                value={analytics?.fulfillment_health?.orders_needing_attention || 0}
                subtitle="Pending/Processing orders"
                icon="⚠️"
                color="#f59e0b"
              />
              <StatCard
                title="Overdue Shipments"
                value={analytics?.fulfillment_health?.overdue_shipments || 0}
                subtitle="Processing > 2 days"
                icon="🚨"
                color={analytics?.fulfillment_health?.overdue_shipments > 0 ? '#ef4444' : '#10b981'}
              />
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.background,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.textSecondary,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: spacing.md,
  },
  periodChip: {
    alignSelf: 'flex-start',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: colors.text,
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  statCard: {
    flex: 1,
    marginHorizontal: 4,
    backgroundColor: colors.surface,
  },
  statHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  statIcon: {
    fontSize: 24,
    marginRight: spacing.sm,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  statTitle: {
    fontSize: 14,
    color: colors.textSecondary,
    marginTop: spacing.xs,
  },
  statSubtitle: {
    fontSize: 12,
    color: colors.textSecondary,
    fontStyle: 'italic',
  },
  errorCard: {
    backgroundColor: '#fee2e2',
  },
  errorText: {
    color: '#ef4444',
    textAlign: 'center',
  },
});

export default OrderAnalyticsScreen;
