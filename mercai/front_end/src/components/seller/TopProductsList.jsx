import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Surface, Text, Card, Avatar, Chip, SegmentedButtons } from 'react-native-paper';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';
import sellerAnalyticsService from '../../services/sellerAnalyticsService.js';

export const TopProductsList = ({
  days = 30,
  limit = 10,
  onProductPress
}) => {
  const [products, setProducts] = useState([]);
  const [metric, setMetric] = useState('revenue');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTopProducts();
  }, [days, metric, limit]);

  const loadTopProducts = async () => {
    try {
      setLoading(true);
      const response = await sellerAnalyticsService.getTopProducts(days, metric, limit);

      // Transform API response to component format
      if (response && response.products && response.products.length > 0) {
        const formattedProducts = response.products.map(product => ({
          id: product.product_id?.toString() || product.id?.toString(),
          name: product.name || product.product_name,
          price: product.price || 0,
          total_revenue: product.total_revenue || 0,
          order_count: product.order_count || 0,
          quantity_sold: product.quantity_sold || 0,
          avg_rating: product.avg_rating || 0,
          review_count: product.review_count || 0,
          stock: product.stock || product.stock_quantity || 0,
          is_featured: product.is_featured || false,
          image: product.image_url || product.image || null
        }));
        setProducts(formattedProducts);
      } else {
        // No products available
        setProducts([]);
      }
    } catch (error) {
      console.error('Failed to load top products:', error);
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  const getMetricValue = (product) => {
    switch (metric) {
      case 'revenue':
        return `${(product.total_revenue || 0).toLocaleString('vi-VN')} ₫`;
      case 'orders':
        return `${product.order_count || 0} orders`;
      case 'quantity':
        return `${product.quantity_sold || 0} sold`;
      case 'rating':
        return `⭐ ${(product.avg_rating || 0).toFixed(1)} (${product.review_count || 0})`;
      default:
        return '';
    }
  };

  const getStatusColor = (product) => {
    if (product.stock <= 0) return colors.error;
    if (product.stock <= 5) return colors.warning;
    return colors.success;
  };

  const getStatusText = (product) => {
    if (product.stock <= 0) return 'Out of Stock';
    if (product.stock <= 5) return `Low Stock (${product.stock})`;
    return `In Stock (${product.stock})`;
  };

  const renderProduct = ({ item, index }) => (
    <TouchableOpacity
      onPress={() => onProductPress?.(item)}
      activeOpacity={0.7}
    >
      <Card style={styles.productCard}>
        <View style={styles.productHeader}>
          <Avatar.Text
            size={32}
            label={`${index + 1}`}
            style={[styles.rankAvatar, { backgroundColor: getRankColor(index) }]}
            labelStyle={{ color: colors.onPrimary, fontSize: 14, fontWeight: '600' }}
          />
          <View style={styles.productInfo}>
            <View style={styles.productNameRow}>
              <Text style={styles.productName}>
                {item.name}
              </Text>
              <Text style={styles.productPrice}>
                {item.price.toLocaleString('vi-VN')} ₫
              </Text>
            </View>
            {item.is_featured && (
              <Chip
                style={styles.featuredChip}
                textStyle={styles.featuredText}
                compact
              >
                Featured
              </Chip>
            )}
          </View>
        </View>

        <View style={styles.productDetails}>
          <View style={styles.metricRow}>
            <Text style={styles.metricLabel}>Performance</Text>
            <Text style={styles.metricValue}>
              {getMetricValue(item)}
            </Text>
          </View>
          
          <View style={styles.statusRow}>
            <View style={styles.stockInfo}>
              <Text style={styles.stockLabel}>Stock</Text>
              <Text style={[styles.stockValue, { color: getStatusColor(item) }]}>
                {getStatusText(item)}
              </Text>
            </View>
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );

  const getRankColor = (index) => {
    if (index === 0) return colors.primary;
    if (index === 1) return colors.secondary;
    if (index === 2) return colors.tertiary;
    return colors.outline;
  };

  if (loading) {
    return (
      <Surface style={styles.container}>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={styles.loadingText}>Loading top products...</Text>
      </Surface>
    );
  }

  return (
    <Surface style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Top Performing Products</Text>
        <Text style={styles.subtitle}>Last {days} days</Text>
      </View>

      <View style={styles.controls}>
        <SegmentedButtons
          value={metric}
          onValueChange={(value) => setMetric(value)}
          buttons={[
            { value: 'revenue', label: 'Revenue' },
            { value: 'orders', label: 'Orders' },
            { value: 'quantity', label: 'Quantity' },
            { value: 'rating', label: 'Rating' },
          ]}
          density="small"
        />
      </View>

      {products.length === 0 ? (
        <View style={styles.noData}>
          <Text style={styles.noDataText}>
            No products found for this period
          </Text>
        </View>
      ) : (
        <FlatList
          data={products}
          renderItem={renderProduct}
          keyExtractor={(item) => item.id.toString()}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.list}
        />
      )}
    </Surface>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    elevation: 2,
    marginBottom: spacing.lg,
    padding: spacing.lg,
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
  controls: {
    marginBottom: spacing.lg,
  },
  list: {
    paddingBottom: spacing.md,
  },
  productContainer: {
    marginBottom: spacing.md,
  },
  productCard: {
    backgroundColor: colors.surfaceVariant,
    padding: spacing.md,
    borderRadius: borderRadius.sm,
    elevation: 1,
  },
  productHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  rankAvatar: {
    marginRight: spacing.md,
  },
  productInfo: {
    flex: 1,
  },
  productNameRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  productName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    flex: 1,
    marginRight: spacing.sm,
  },
  productPrice: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  featuredChip: {
    alignSelf: 'flex-start',
    backgroundColor: colors.primaryContainer,
    borderColor: colors.primary,
  },
  featuredText: {
    fontSize: typography.sizes.xs,
    color: colors.onPrimaryContainer,
  },
  productDetails: {
    paddingTop: spacing.sm,
  },
  metricRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  metricLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  metricValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stockInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stockLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginRight: spacing.sm,
  },
  stockValue: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
  loadingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    padding: spacing.lg,
  },
  noData: {
    padding: spacing.lg,
    alignItems: 'center',
  },
  noDataText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
  },
});

export default TopProductsList;