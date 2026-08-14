import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';

const PerformanceMetricsCard = ({ data }) => {
  const getMetricGrade = (value, type) => {
    switch (type) {
      case 'conversion':
        return sellerAnalyticsService.getPerformanceGrade(value, { 
          excellent: 5, 
          good: 3, 
          fair: 1 
        });
      case 'refund':
        return sellerAnalyticsService.getPerformanceGrade(100 - value, { 
          excellent: 95, 
          good: 85, 
          fair: 70 
        });
      case 'cancellation':
        return sellerAnalyticsService.getPerformanceGrade(100 - value, { 
          excellent: 95, 
          good: 85, 
          fair: 70 
        });
      case 'fulfillment':
        return sellerAnalyticsService.getPerformanceGrade(10 - value, { 
          excellent: 8, 
          good: 6, 
          fair: 4 
        });
      default:
        return { 
          grade: 'fair', 
          color: '#F59E0B', 
          description: 'Fair' 
        };
    }
  };

  const metricsData = [
    {
      title: 'Conversion Rate',
      value: data?.efficiency_metrics?.conversion_rate 
        ? `${(data.efficiency_metrics.conversion_rate * 100).toFixed(1)}%`
        : '2.8%',
      icon: 'trending-up',
      grade: getMetricGrade(data?.efficiency_metrics?.conversion_rate || 0.028, 'conversion'),
      subtitle: 'Visitors to customers',
    },
    {
      title: 'Refund Rate',
      value: data?.efficiency_metrics?.refund_rate 
        ? `${(data.efficiency_metrics.refund_rate * 100).toFixed(1)}%`
        : '3.2%',
      icon: 'undo',
      grade: getMetricGrade(data?.efficiency_metrics?.refund_rate || 0.032, 'refund'),
      subtitle: 'Refunds vs. orders',
    },
    {
      title: 'Cancellation Rate',
      value: data?.efficiency_metrics?.cancellation_rate 
        ? `${(data.efficiency_metrics.cancellation_rate * 100).toFixed(1)}%`
        : '1.8%',
      icon: 'cancel',
      grade: getMetricGrade(data?.efficiency_metrics?.cancellation_rate || 0.018, 'cancellation'),
      subtitle: 'Cancelled orders',
    },
    {
      title: 'Avg Fulfillment',
      value: data?.efficiency_metrics?.avg_fulfillment_time 
        ? `${data.efficiency_metrics.avg_fulfillment_time.toFixed(1)} days`
        : '2.5 days',
      icon: 'local-shipping',
      grade: getMetricGrade(data?.efficiency_metrics?.avg_fulfillment_time || 2.5, 'fulfillment'),
      subtitle: 'Days to ship',
    },
  ];

  const growthData = [
    {
      title: 'Revenue Growth',
      value: data?.growth_rates?.revenue_growth || 12.5,
      icon: 'attach-money',
    },
    {
      title: 'Order Growth',
      value: data?.growth_rates?.order_growth || 8.3,
      icon: 'shopping-cart',
    },
    {
      title: 'Customer Growth',
      value: data?.growth_rates?.customer_growth || 15.2,
      icon: 'people',
    },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Performance Metrics</Text>
      <Text style={styles.subtitle}>
        {data?.period_days || 30} days period analysis
      </Text>

      {/* Current Period Overview */}
      <View style={styles.overviewContainer}>
        <Text style={styles.sectionTitle}>Current Period</Text>
        <View style={styles.overviewGrid}>
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Total Orders</Text>
            <Text style={styles.overviewValue}>
              {data?.current_period?.total_orders || 145}
            </Text>
          </View>
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Revenue</Text>
            <Text style={styles.overviewValue}>
              {data?.current_period?.total_revenue 
                ? sellerAnalyticsService.formatCurrency(data.current_period.total_revenue)
                : '$18,450'
              }
            </Text>
          </View>
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Avg Order Value</Text>
            <Text style={styles.overviewValue}>
              {data?.current_period?.avg_order_value
                ? sellerAnalyticsService.formatCurrency(data.current_period.avg_order_value)
                : '$127'
              }
            </Text>
          </View>
          <View style={styles.overviewItem}>
            <Text style={styles.overviewLabel}>Customers</Text>
            <Text style={styles.overviewValue}>
              {data?.current_period?.unique_customers || 89}
            </Text>
          </View>
        </View>
      </View>

      {/* Efficiency Metrics */}
      <View style={styles.metricsContainer}>
        <Text style={styles.sectionTitle}>Efficiency Metrics</Text>
        <View style={styles.metricsGrid}>
          {metricsData.map((metric, index) => (
            <View key={index} style={styles.metricCard}>
              <View style={styles.metricHeader}>
                <Icon name={metric.icon} size={24} color={metric.grade.color} />
                <View style={[styles.gradeBadge, { backgroundColor: metric.grade.color + '20' }]}>
                  <Text style={[styles.gradeText, { color: metric.grade.color }]}>
                    {metric.grade.description}
                  </Text>
                </View>
              </View>
              <Text style={styles.metricTitle}>{metric.title}</Text>
              <Text style={styles.metricValue}>{metric.value}</Text>
              <Text style={styles.metricSubtitle}>{metric.subtitle}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Growth Rates */}
      <View style={styles.growthContainer}>
        <Text style={styles.sectionTitle}>Growth Rates</Text>
        <View style={styles.growthGrid}>
          {growthData.map((growth, index) => (
            <View key={index} style={styles.growthCard}>
              <View style={styles.growthHeader}>
                <Icon name={growth.icon} size={20} color="#6B7280" />
                <Text style={styles.growthTitle}>{growth.title}</Text>
              </View>
              <View style={styles.growthValueContainer}>
                <Text style={styles.growthIcon}>
                  {sellerAnalyticsService.getGrowthIcon 
                    ? sellerAnalyticsService.getGrowthIcon(growth.value)
                    : (growth.value > 0 ? '📈' : '📉')
                  }
                </Text>
                <Text style={[
                  styles.growthValue,
                  { color: sellerAnalyticsService.getGrowthColor 
                    ? sellerAnalyticsService.getGrowthColor(growth.value)
                    : (growth.value > 0 ? '#10B981' : '#EF4444')
                  }
                ]}>
                  {sellerAnalyticsService.formatPercentage 
                    ? sellerAnalyticsService.formatPercentage(growth.value)
                    : `${growth.value > 0 ? '+' : ''}${growth.value.toFixed(1)}%`
                  }
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* Customer Lifetime Value */}
      <View style={styles.clvContainer}>
        <View style={styles.clvHeader}>
          <Icon name="loyalty" size={24} color="#8B5CF6" />
          <Text style={styles.clvTitle}>Customer Lifetime Value</Text>
        </View>
        <Text style={styles.clvValue}>
          {data?.efficiency_metrics?.customer_lifetime_value
            ? sellerAnalyticsService.formatCurrency(data.efficiency_metrics.customer_lifetime_value)
            : '$2,450'
          }
        </Text>
        <Text style={styles.clvSubtitle}>
          Average revenue per customer over their lifetime
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 14,
    color: '#6B7280',
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 12,
  },
  overviewContainer: {
    marginBottom: 24,
  },
  overviewGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  overviewItem: {
    width: '48%',
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    alignItems: 'center',
  },
  overviewLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginBottom: 4,
  },
  overviewValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1F2937',
  },
  metricsContainer: {
    marginBottom: 24,
  },
  metricsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  metricCard: {
    width: '48%',
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
  },
  metricHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  gradeBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 12,
  },
  gradeText: {
    fontSize: 10,
    fontWeight: '600',
  },
  metricTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 20,
    fontWeight: '600',
    color: '#1F2937',
    marginBottom: 4,
  },
  metricSubtitle: {
    fontSize: 12,
    color: '#6B7280',
  },
  growthContainer: {
    marginBottom: 24,
  },
  growthGrid: {
    gap: 8,
  },
  growthCard: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  growthHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  growthTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#374151',
    marginLeft: 8,
  },
  growthValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  growthIcon: {
    fontSize: 14,
    marginRight: 4,
  },
  growthValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  clvContainer: {
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
  },
  clvHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  clvTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#374151',
    marginLeft: 8,
  },
  clvValue: {
    fontSize: 28,
    fontWeight: '700',
    color: '#8B5CF6',
    marginBottom: 4,
  },
  clvSubtitle: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
  },
});

export default PerformanceMetricsCard;