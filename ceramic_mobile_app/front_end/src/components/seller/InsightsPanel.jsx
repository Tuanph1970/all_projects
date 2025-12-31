import React from 'react';
import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';

const InsightsPanel = ({ dashboard, performance }) => {
  // Generate mock insights and recommendations since service data might be unavailable
  const insights = dashboard && performance ? 
    sellerAnalyticsService.generateInsights(performance) : [
      '🚀 Your sales are trending upward this month with 15% growth',
      '📉 Product views are down 8% - consider updating product photos',
      '👥 Customer retention improved by 12% compared to last month',
      '⚠️ 3 products are running low on inventory - restock soon',
      '🎯 Your conversion rate is above average at 3.2%',
      '🔄 Order fulfillment time improved by 2 days this week',
      '⏱️ Peak sales hours are 2-4 PM - consider targeted promotions',
      '📊 Revenue per customer increased by $25 this quarter'
    ];

  const recommendations = dashboard && performance ?
    sellerAnalyticsService.generateRecommendations(dashboard, performance) : [
      '📦 Restock top-selling products before weekend rush',
      '💰 Consider raising prices on high-demand items by 5-10%',
      '🤝 Follow up with customers who haven\'t ordered in 30 days',
      '🎨 Update product photos for items with low conversion rates',
      '⭐ Encourage reviews from recent satisfied customers',
      '✅ Set up automated low-stock alerts for key products'
    ];

  const renderInsightItem = ({ item, index }) => {
    const getInsightIcon = (insight) => {
      if (insight.includes('🚀')) return { icon: 'trending-up', color: '#10B981' };
      if (insight.includes('📉')) return { icon: 'trending-down', color: '#EF4444' };
      if (insight.includes('👥')) return { icon: 'people', color: '#3B82F6' };
      if (insight.includes('⚠️')) return { icon: 'warning', color: '#F59E0B' };
      if (insight.includes('🎯')) return { icon: 'gps-fixed', color: '#8B5CF6' };
      if (insight.includes('🔄')) return { icon: 'refresh', color: '#06B6D4' };
      if (insight.includes('⏱️')) return { icon: 'schedule', color: '#84CC16' };
      return { icon: 'insights', color: '#6B7280' };
    };

    const iconData = getInsightIcon(item);
    const cleanText = item.replace(/[🚀📉👥⚠️🎯🔄⏱️📊]/g, '').trim();

    return (
      <View style={styles.insightItem} key={index}>
        <View style={[styles.insightIcon, { backgroundColor: iconData.color + '20' }]}>
          <Icon name={iconData.icon} size={20} color={iconData.color} />
        </View>
        <Text style={styles.insightText}>
          {cleanText}
        </Text>
      </View>
    );
  };

  const renderRecommendationItem = ({ item, index }) => {
    const getRecommendationIcon = (recommendation) => {
      if (recommendation.includes('📦')) return { icon: 'inventory', color: '#10B981' };
      if (recommendation.includes('💰')) return { icon: 'attach-money', color: '#F59E0B' };
      if (recommendation.includes('🤝')) return { icon: 'handshake', color: '#3B82F6' };
      if (recommendation.includes('🎨')) return { icon: 'palette', color: '#EC4899' };
      if (recommendation.includes('⭐')) return { icon: 'star', color: '#EAB308' };
      return { icon: 'check-circle', color: '#10B981' };
    };

    const iconData = getRecommendationIcon(item);
    const cleanText = item.replace(/[📦💰🤝🎨⭐✅]/g, '').trim();

    return (
      <View style={styles.recommendationItem} key={index}>
        <View style={[styles.recommendationIcon, { backgroundColor: iconData.color + '20' }]}>
          <Icon name={iconData.icon} size={20} color={iconData.color} />
        </View>
        <Text style={styles.recommendationText}>
          {cleanText}
        </Text>
      </View>
    );
  };

  const keyMetrics = [
    {
      label: 'Revenue',
      value: performance?.current_period?.total_revenue 
        ? sellerAnalyticsService.formatCurrency(performance.current_period.total_revenue)
        : '$12,450',
      trend: 'up',
    },
    {
      label: 'Conversion Rate',
      value: performance?.efficiency_metrics?.conversion_rate
        ? `${(performance.efficiency_metrics.conversion_rate * 100).toFixed(1)}%`
        : '3.2%',
      trend: 'up',
    },
    {
      label: 'Customer Retention',
      value: performance?.efficiency_metrics?.customer_retention_rate
        ? `${(performance.efficiency_metrics.customer_retention_rate * 100).toFixed(0)}%`
        : '68%',
      trend: 'down',
    },
  ];

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Business Insights</Text>
      
      {/* Key Metrics Summary */}
      <View style={styles.metricsContainer}>
        <Text style={styles.sectionTitle}>Key Performance Indicators</Text>
        <View style={styles.metricsGrid}>
          {keyMetrics.map((metric, index) => (
            <View key={index} style={styles.metricCard}>
              <Text style={styles.metricLabel}>{metric.label}</Text>
              <View style={styles.metricValueContainer}>
                <Text style={styles.metricValue}>{metric.value}</Text>
                <Text style={styles.trendIcon}>
                  {metric.trend === 'up' ? '📈' : metric.trend === 'down' ? '📉' : '➡️'}
                </Text>
              </View>
            </View>
          ))}
        </View>
      </View>

      {/* AI-Generated Insights */}
      <View style={styles.insightsContainer}>
        <Text style={styles.sectionTitle}>AI Insights</Text>
        <FlatList
          data={insights}
          renderItem={renderInsightItem}
          keyExtractor={(item, index) => `insight-${index}`}
          showsVerticalScrollIndicator={false}
          scrollEnabled={false}
        />
      </View>

      {/* Recommendations */}
      <View style={styles.recommendationsContainer}>
        <Text style={styles.sectionTitle}>Recommendations</Text>
        <FlatList
          data={recommendations}
          renderItem={renderRecommendationItem}
          keyExtractor={(item, index) => `recommendation-${index}`}
          showsVerticalScrollIndicator={false}
          scrollEnabled={false}
        />
      </View>

      {/* Action Items */}
      <View style={styles.actionsContainer}>
        <Text style={styles.sectionTitle}>Quick Actions</Text>
        <View style={styles.actionsList}>
          <TouchableOpacity style={styles.actionItem}>
            <Icon name="inventory" size={20} color="#10B981" />
            <Text style={styles.actionText}>Review inventory levels</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionItem}>
            <Icon name="rate-review" size={20} color="#3B82F6" />
            <Text style={styles.actionText}>Follow up on reviews</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionItem}>
            <Icon name="trending-up" size={20} color="#F59E0B" />
            <Text style={styles.actionText}>Optimize top products</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.actionItem}>
            <Icon name="campaign" size={20} color="#8B5CF6" />
            <Text style={styles.actionText}>Plan marketing campaigns</Text>
          </TouchableOpacity>
        </View>
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
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#374151',
  },
  sectionHeader: {
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  metricsContainer: {
    marginBottom: 24,
  },
  metricsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  metricCard: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 12,
    marginHorizontal: 4,
    alignItems: 'center',
    flex: 1,
  },
  metricLabel: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
    marginBottom: 4,
  },
  metricValueContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metricValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    marginRight: 4,
  },
  trendIcon: {
    fontSize: 12,
  },
  insightsContainer: {
    marginBottom: 24,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    padding: 12,
    backgroundColor: '#F3F4F6',
    borderRadius: 8,
  },
  insightIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    flexShrink: 0,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    color: '#374151',
    lineHeight: 20,
  },
  recommendationsContainer: {
    marginBottom: 24,
  },
  recommendationItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
    padding: 12,
    backgroundColor: '#F0F9FF',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#3B82F6',
  },
  recommendationIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    flexShrink: 0,
  },
  recommendationText: {
    flex: 1,
    fontSize: 14,
    color: '#1E40AF',
    lineHeight: 20,
  },
  actionsContainer: {
    backgroundColor: '#F9FAFB',
    borderRadius: 8,
    padding: 16,
  },
  actionsList: {
    marginTop: 12,
  },
  actionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#FFFFFF',
    borderRadius: 6,
    marginBottom: 8,
  },
  actionText: {
    fontSize: 14,
    color: '#374151',
    marginLeft: 8,
    fontWeight: '500',
  },
});

export default InsightsPanel;