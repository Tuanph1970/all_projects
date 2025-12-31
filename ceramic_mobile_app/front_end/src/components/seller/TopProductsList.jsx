import React, { useState, useEffect } from 'react';
import { View, StyleSheet, FlatList, TouchableOpacity, ActivityIndicator } from 'react-native';
import { Surface, Text, Card, Avatar, Chip, SegmentedButtons } from 'react-native-paper';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';

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
      // Mock data for now - replace with actual service call
      const mockProducts = [
        {
          id: '1',
          name: 'Ceramic Vase Premium',
          price: 299000,
          total_revenue: 8970000,
          order_count: 30,
          quantity_sold: 45,
          avg_rating: 4.8,
          review_count: 24,
          stock: 12,
          is_featured: true,
          image: 'https://via.placeholder.com/80'
        },
        {
          id: '2', 
          name: 'Handmade Pottery Set',
          price: 450000,
          total_revenue: 6750000,
          order_count: 15,
          quantity_sold: 15,
          avg_rating: 4.6,
          review_count: 12,
          stock: 3,
          is_featured: false,
          image: 'https://via.placeholder.com/80'
        }
      ];
      setProducts(mockProducts);
    } catch (error) {
      console.error('Failed to load top products:', error);
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