import React from 'react';
import { View, Text, StyleSheet, FlatList, Dimensions, ActivityIndicator } from 'react-native';
import { Surface } from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';
import { useLanguage } from '@i18n';

const screenWidth = Dimensions.get('window').width;

export const CategoryPerformanceChart = ({ data }) => {
  const { formatCurrency } = useLanguage();
  const chartConfig = {
    backgroundColor: colors.surface,
    backgroundGradientFrom: colors.surface,
    backgroundGradientTo: colors.surface,
    decimalPlaces: 0,
    color: (opacity = 1) => `rgba(139, 92, 246, ${opacity})`,
    labelColor: (opacity = 1) => `rgba(107, 114, 128, ${opacity})`,
    style: {
      borderRadius: borderRadius.md,
    },
    propsForBackgroundLines: {
      stroke: colors.outlineVariant,
      strokeWidth: 1,
    },
  };

  if (!data || !data.categories) {
    return (
      <Surface style={styles.container}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading category performance...</Text>
      </Surface>
    );
  }

  const sortedCategories = [...data.categories]
    .sort((a, b) => b.total_revenue - a.total_revenue)
    .slice(0, 6);

  const chartData = {
    labels: sortedCategories.map(cat => 
      cat.category_name.length > 8 
        ? cat.category_name.substring(0, 8) + '...'
        : cat.category_name
    ),
    datasets: [
      {
        data: sortedCategories.map(cat => cat.total_revenue),
        colors: sortedCategories.map((_, index) => () => {
          const colors = ['#8B5CF6', '#EC4899', '#10B981', '#F59E0B', '#3B82F6', '#EF4444'];
          return colors[index % colors.length];
        }),
      },
    ],
  };

  const formatNumber = (num) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    }
    if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  const renderCategoryItem = ({ item, index }) => {
    const colorOptions = ['#8B5CF6', '#EC4899', '#10B981', '#F59E0B', '#3B82F6', '#EF4444'];
    const color = colorOptions[index % colorOptions.length];

    const getPerformanceGrade = (rating) => {
      if (rating >= 4.5) return 'Excellent';
      if (rating >= 4.0) return 'Good';
      if (rating >= 3.5) return 'Fair';
      return 'Poor';
    };

    return (
      <View style={styles.categoryItem}>
        <View style={styles.categoryHeader}>
          <View style={styles.categoryInfo}>
            <View style={[styles.categoryIndicator, { backgroundColor: color }]} />
            <View style={styles.categoryDetails}>
              <Text style={styles.categoryName}>
                {item.category_name}
              </Text>
              <Text style={styles.categorySubtext}>
                {item.product_count} products • {item.total_orders} orders
              </Text>
            </View>
          </View>
          <View style={styles.categoryMetrics}>
            <Text style={styles.categoryRevenue}>
              {formatCurrency(item.total_revenue)}
            </Text>
            <View style={styles.ratingContainer}>
              <Text style={styles.categoryRating}>
                ⭐ {(item.avg_rating || 0).toFixed(1)}
              </Text>
              <Text style={[styles.categoryRating, { color }]}>
                {getPerformanceGrade(item.avg_rating || 0)}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.categoryStats}>
          <View style={styles.statGroup}>
            <Text style={styles.statLabel}>Avg Revenue/Product</Text>
            <Text style={styles.statValue}>
              {formatCurrency(item.avg_revenue_per_product || 0)}
            </Text>
          </View>
          <View style={styles.statGroup}>
            <Text style={styles.statLabel}>Items Sold</Text>
            <Text style={styles.statValue}>{item.total_quantity_sold || 0}</Text>
          </View>
          <View style={styles.statGroup}>
            <Text style={styles.statLabel}>Reviews</Text>
            <Text style={styles.statValue}>{item.review_count || 0}</Text>
          </View>
        </View>
      </View>
    );
  };

  const totalRevenue = data.categories.reduce((sum, cat) => sum + cat.total_revenue, 0);
  const totalProducts = data.categories.reduce((sum, cat) => sum + cat.product_count, 0);

  return (
    <Surface style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Category Performance</Text>
        <Text style={styles.subtitle}>
          {data.categories.length} categories • {totalProducts} total products
        </Text>
      </View>

      {sortedCategories.length > 0 && (
        <View style={styles.summaryCards}>
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>Top Performer</Text>
            <Text style={styles.summaryValue}>
              {sortedCategories[0]?.category_name || 'N/A'}
            </Text>
            <Text style={styles.summarySubtext}>
              {sortedCategories[0] 
                ? formatCurrency(sortedCategories[0].total_revenue)
                : '-'
              }
            </Text>
          </View>
          
          <View style={styles.summaryCard}>
            <Text style={styles.summaryLabel}>Best Rating</Text>
            <Text style={styles.summaryValue}>
              ⭐ {data.categories.length > 0 
                ? Math.max(...data.categories.map(c => c.avg_rating || 0)).toFixed(1)
                : 'N/A'
              }
            </Text>
            <Text style={styles.summarySubtext}>Average rating</Text>
          </View>
        </View>
      )}

      <View style={styles.categoryList}>
        <Text style={styles.listTitle}>Detailed Breakdown</Text>
        <FlatList
          data={sortedCategories}
          renderItem={renderCategoryItem}
          keyExtractor={(item) => item.category_id?.toString() || Math.random().toString()}
          showsVerticalScrollIndicator={false}
          scrollEnabled={false}
        />
      </View>
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
  chart: {
    marginVertical: spacing.md,
    borderRadius: borderRadius.sm,
  },
  summaryCards: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: spacing.md,
  },
  summaryCard: {
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    marginHorizontal: spacing.xs,
    alignItems: 'center',
    flex: 1,
  },
  summaryLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  summaryValue: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
    textAlign: 'center',
  },
  summarySubtext: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    textAlign: 'center',
  },
  categoryList: {
    marginTop: spacing.md,
  },
  listTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  categoryItem: {
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  categoryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
  },
  categoryInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  categoryIndicator: {
    width: 4,
    height: 40,
    borderRadius: borderRadius.xs,
    marginRight: spacing.sm,
  },
  categoryDetails: {
    flex: 1,
  },
  categoryName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  categorySubtext: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  categoryMetrics: {
    alignItems: 'flex-end',
  },
  categoryRevenue: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  categoryRating: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    marginLeft: spacing.xs,
  },
  categoryStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  statGroup: {
    alignItems: 'center',
    flex: 1,
  },
  statLabel: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  statValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginTop: spacing.md,
  },
});

export default CategoryPerformanceChart;