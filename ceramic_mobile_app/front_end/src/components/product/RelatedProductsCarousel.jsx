import React from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator,
} from 'react-native';
import { Title, Text, Button } from 'react-native-paper';
import { ProductCard } from './ProductCard.jsx';
import { colors, spacing, typography } from '../../constants/theme.js';

const { width: screenWidth } = Dimensions.get('window');
const CARD_WIDTH = screenWidth * 0.45;
const CARD_SPACING = spacing.md;

export const RelatedProductsCarousel = ({
  products,
  title = 'Sản phẩm liên quan',
  onProductPress,
  onFavoritePress,
  onViewAllPress,
  favorites = [],
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Title style={styles.title}>
            {title}
          </Title>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>
            Đang tải sản phẩm...
          </Text>
        </View>
      </View>
    );
  }

  if (!products || products.length === 0) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Title style={styles.title}>
            {title}
          </Title>
        </View>
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>🏺</Text>
          <Text style={styles.emptyText}>
            Không có sản phẩm liên quan
          </Text>
        </View>
      </View>
    );
  }

  const renderProduct = ({ item, index }) => {
    const isFavorite = favorites.includes(item.id);
    
    return (
      <View style={styles.cardContainer}>
        <ProductCard
          product={item}
          onPress={() => onProductPress(item)}
          onFavoritePress={onFavoritePress ? () => onFavoritePress(item) : undefined}
          isFavorite={isFavorite}
          viewType="grid"
          containerWidth={CARD_WIDTH}
        />
      </View>
    );
  };

  const keyExtractor = (item, index) => `related-${item.id}-${index}`;

  const getItemLayout = (data, index) => ({
    length: CARD_WIDTH + CARD_SPACING,
    offset: (CARD_WIDTH + CARD_SPACING) * index,
    index,
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Title style={styles.title}>
          {title}
        </Title>
        {onViewAllPress && products.length > 0 && (
          <Button
            mode="text"
            onPress={onViewAllPress}
            compact
          >
            Xem tất cả
          </Button>
        )}
      </View>

      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={keyExtractor}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
        snapToInterval={CARD_WIDTH + CARD_SPACING}
        snapToAlignment="start"
        decelerationRate="fast"
        getItemLayout={getItemLayout}
        removeClippedSubviews={true}
        maxToRenderPerBatch={5}
        windowSize={10}
        initialNumToRender={3}
      />

      {products.length >= 5 && onViewAllPress && (
        <View style={styles.showMoreContainer}>
          <Button
            mode="outlined"
            onPress={onViewAllPress}
            style={styles.showMoreButton}
            contentStyle={styles.showMoreButtonContent}
          >
            Xem thêm sản phẩm tương tự
          </Button>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.background,
    paddingVertical: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.outlineVariant,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  listContent: {
    paddingHorizontal: spacing.md,
  },
  cardContainer: {
    width: CARD_WIDTH,
    marginRight: CARD_SPACING,
  },
  separator: {
    width: 0,
  },
  loadingContainer: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surfaceVariant,
    marginHorizontal: spacing.md,
    borderRadius: 12,
  },
  loadingText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginTop: spacing.sm,
  },
  emptyContainer: {
    height: 200,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.surfaceVariant,
    marginHorizontal: spacing.md,
    borderRadius: 12,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: spacing.sm,
  },
  emptyText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
  },
  showMoreContainer: {
    alignItems: 'center',
    paddingTop: spacing.md,
  },
  showMoreButton: {
    borderColor: colors.primary,
  },
  showMoreButtonContent: {
    paddingHorizontal: spacing.lg,
  },
});