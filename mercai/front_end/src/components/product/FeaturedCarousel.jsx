import React, { useRef, useState, useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  Dimensions,
  TouchableOpacity,
  Image,
} from 'react-native';
import { Card, Title, Text } from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

const { width: screenWidth } = Dimensions.get('window');
const CARD_WIDTH = screenWidth * 0.8;
const CARD_SPACING = spacing.md;

export const FeaturedCarousel = ({
  products = [],
  onProductPress,
  autoPlay = true,
  autoPlayInterval = 4000,
}) => {
  const flatListRef = useRef(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const autoPlayRef = useRef(null);

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(price);
  };

  const startAutoPlay = useCallback(() => {
    if (autoPlay && products.length > 1) {
      autoPlayRef.current = setInterval(() => {
        setCurrentIndex((prevIndex) => {
          const nextIndex = (prevIndex + 1) % products.length;
          flatListRef.current?.scrollToIndex({
            index: nextIndex,
            animated: true,
          });
          return nextIndex;
        });
      }, autoPlayInterval);
    }
  }, [autoPlay, products.length, autoPlayInterval]);

  const stopAutoPlay = useCallback(() => {
    if (autoPlayRef.current) {
      clearInterval(autoPlayRef.current);
      autoPlayRef.current = null;
    }
  }, []);

  React.useEffect(() => {
    startAutoPlay();
    return stopAutoPlay;
  }, [startAutoPlay, stopAutoPlay]);

  const handleScrollBegin = useCallback(() => {
    stopAutoPlay();
  }, [stopAutoPlay]);

  const handleScrollEnd = useCallback(() => {
    startAutoPlay();
  }, [startAutoPlay]);

  const onViewableItemsChanged = useCallback(
    ({ viewableItems }) => {
      if (viewableItems.length > 0) {
        setCurrentIndex(viewableItems[0].index || 0);
      }
    },
    []
  );

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 80,
  };

  const renderFeaturedProduct = useCallback(
    ({ item }) => (
      <TouchableOpacity
        onPress={() => onProductPress(item)}
        activeOpacity={0.9}
        style={styles.cardContainer}
      >
        <Card style={styles.card}>
          <View style={styles.imageContainer}>
            <Image
              source={{ uri: item.images?.[0]?.url || item.image }}
              style={styles.image}
              resizeMode="cover"
            />
            
            {item.original_price && item.original_price > item.price && (
              <View style={styles.saleBadge}>
                <Text style={styles.saleBadgeText}>
                  -{Math.round(((item.original_price - item.price) / item.original_price) * 100)}%
                </Text>
              </View>
            )}
            
            <View style={styles.gradient}>
              <Text style={styles.category}>
                {item.category?.name}
              </Text>
              <Title style={styles.title}>
                {item.name}
              </Title>
              <View style={styles.sellerContainer}>
                <Text style={styles.seller}>
                  bởi {item.seller?.display_name || 'Seller'}
                  {item.seller?.is_verified && (
                    <Text style={styles.verifiedIcon}> ✓</Text>
                  )}
                </Text>
              </View>
              <View style={styles.priceContainer}>
                <Text style={styles.currentPrice}>
                  {formatPrice(item.price)}
                </Text>
                {item.original_price && item.original_price > item.price && (
                  <Text style={styles.originalPrice}>
                    {formatPrice(item.original_price)}
                  </Text>
                )}
              </View>
              <Text style={styles.rating}>
                ⭐ {item.avg_rating?.toFixed(1) || '0.0'} ({item.review_count || 0} đánh giá)
              </Text>
            </View>
          </View>
        </Card>
      </TouchableOpacity>
    ),
    [onProductPress]
  );

  const renderPagination = () => {
    if (products.length <= 1) return null;

    return (
      <View style={styles.pagination}>
        {products.map((_, index) => (
          <TouchableOpacity
            key={index}
            style={[
              styles.paginationDot,
              index === currentIndex && styles.paginationDotActive,
            ]}
            onPress={() => {
              flatListRef.current?.scrollToIndex({ index, animated: true });
              setCurrentIndex(index);
            }}
          />
        ))}
      </View>
    );
  };

  if (products.length === 0) return null;

  return (
    <View style={styles.container}>
      <FlatList
        ref={flatListRef}
        data={products}
        renderItem={renderFeaturedProduct}
        keyExtractor={(item) => `featured-${item.id}`}
        horizontal
        showsHorizontalScrollIndicator={false}
        pagingEnabled
        decelerationRate="fast"
        snapToInterval={CARD_WIDTH + CARD_SPACING}
        snapToAlignment="center"
        contentInset={{ left: CARD_SPACING / 2, right: CARD_SPACING / 2 }}
        contentContainerStyle={styles.contentContainer}
        onScrollBeginDrag={handleScrollBegin}
        onScrollEndDrag={handleScrollEnd}
        onViewableItemsChanged={onViewableItemsChanged}
        viewabilityConfig={viewabilityConfig}
        getItemLayout={(data, index) => ({
          length: CARD_WIDTH + CARD_SPACING,
          offset: (CARD_WIDTH + CARD_SPACING) * index,
          index,
        })}
      />
      {renderPagination()}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: spacing.md,
  },
  contentContainer: {
    paddingHorizontal: spacing.sm,
  },
  cardContainer: {
    width: CARD_WIDTH,
    marginRight: CARD_SPACING,
  },
  card: {
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 8,
  },
  imageContainer: {
    position: 'relative',
    height: 250,
  },
  image: {
    width: '100%',
    height: '100%',
  },
  saleBadge: {
    position: 'absolute',
    top: 16,
    left: 16,
    backgroundColor: colors.error,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: 12,
    zIndex: 1,
  },
  saleBadgeText: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.bold,
    color: colors.onError,
  },
  gradient: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 120,
    backgroundColor: 'rgba(0,0,0,0.7)',
    padding: spacing.md,
    justifyContent: 'flex-end',
  },
  category: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    fontWeight: typography.weights.medium,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  title: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.bold,
    color: colors.onPrimary,
    marginBottom: spacing.sm,
    lineHeight: 24,
  },
  sellerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  seller: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    opacity: 0.9,
  },
  verifiedIcon: {
    fontSize: typography.sizes.sm,
    color: colors.success || '#4CAF50',
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  currentPrice: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.bold,
    color: colors.onPrimary,
    marginRight: spacing.sm,
  },
  originalPrice: {
    fontSize: typography.sizes.md,
    color: colors.onPrimary,
    opacity: 0.7,
    textDecorationLine: 'line-through',
  },
  rating: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    opacity: 0.9,
  },
  pagination: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: spacing.md,
  },
  paginationDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.outline,
    marginHorizontal: 4,
  },
  paginationDotActive: {
    backgroundColor: colors.primary,
    width: 20,
  },
});