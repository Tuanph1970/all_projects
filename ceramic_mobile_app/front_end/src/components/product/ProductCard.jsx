import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Text,
} from 'react-native';
import { Card, Title, IconButton } from 'react-native-paper';
import FastImage from 'react-native-fast-image';
import { colors, spacing, typography, shadows, borderRadius } from '../../constants/theme.js';

const { width } = Dimensions.get('window');
const GRID_SPACING = spacing.md;

export const ProductCard = ({
  product,
  onPress,
  onFavoritePress,
  isFavorite = false,
  viewType = 'grid',
  containerWidth,
}) => {
  const isListView = viewType === 'list';
  const cardWidth = containerWidth 
    ? (containerWidth - GRID_SPACING * 3) / 2 
    : (width - GRID_SPACING * 3) / 2;

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(price);
  };

  const renderRating = () => {
    const stars = [];
    const fullStars = Math.floor(product.rating || 0);
    const hasHalfStar = (product.rating || 0) % 1 !== 0;

    for (let i = 0; i < fullStars; i++) {
      stars.push('⭐');
    }

    if (hasHalfStar && stars.length < 5) {
      stars.push('⭐');
    }

    return (
      <View style={styles.ratingContainer}>
        <View style={styles.starsContainer}>
          {stars.map((star, index) => (
            <Text key={index} style={styles.star}>{star}</Text>
          ))}
        </View>
        <Text style={styles.ratingText}>
          {(product.rating || 0).toFixed(1)} ({product.reviewCount || 0})
        </Text>
      </View>
    );
  };

  const cardStyle = isListView
    ? [styles.card, styles.listCard]
    : [styles.card, styles.gridCard, { width: cardWidth }];

  const imageStyle = isListView
    ? styles.listImage
    : styles.gridImage;

  const contentStyle = isListView
    ? styles.listContent
    : styles.gridContent;

  return (
    <TouchableOpacity onPress={() => onPress(product)} activeOpacity={0.8}>
      <Card style={cardStyle}>
        <View style={styles.cardContainer}>
          <View style={styles.imageContainer}>
            <FastImage
              source={{ uri: product.images?.[0]?.url || product.image }}
              style={imageStyle}
              resizeMode={FastImage.resizeMode.cover}
            />

            {product.originalPrice && product.originalPrice > product.price && (
              <View style={styles.saleBadge}>
                <Text style={styles.saleBadgeText}>
                  -{Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)}%
                </Text>
              </View>
            )}

            {onFavoritePress && (
              <IconButton
                icon={isFavorite ? "heart" : "heart-outline"}
                iconColor={isFavorite ? colors.error : colors.onSurface}
                size={20}
                onPress={() => onFavoritePress(product)}
                style={styles.favoriteButton}
              />
            )}

            {product.stock === 0 && (
              <View style={styles.outOfStockOverlay}>
                <Text style={styles.outOfStockText}>
                  Hết hàng
                </Text>
              </View>
            )}
          </View>

          <View style={contentStyle}>
            <Text style={styles.categoryText}>
              {product.category?.name}
            </Text>
            <Title style={styles.productTitle}>
              {product.title}
            </Title>

            <View style={styles.sellerContainer}>
              <Text style={styles.sellerText}>
                {product.seller?.displayName}
                {product.seller?.isVerified && (
                  <Text style={styles.verifiedIcon}> ✓</Text>
                )}
              </Text>
            </View>

            {renderRating()}

            <View style={styles.priceContainer}>
              <Text style={styles.currentPrice}>
                {formatPrice(product.price)}
              </Text>
              {product.originalPrice && product.originalPrice > product.price && (
                <Text style={styles.originalPrice}>
                  {formatPrice(product.originalPrice)}
                </Text>
              )}
            </View>

            {product.stock > 0 && product.stock <= 10 && (
              <Text style={styles.stockWarning}>
                Chỉ còn {product.stock} sản phẩm
              </Text>
            )}
          </View>
        </View>
      </Card>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    marginBottom: spacing.md,
    ...shadows.md,
  },
  gridCard: {
    flex: 1,
  },
  listCard: {
    marginHorizontal: spacing.md,
  },
  cardContainer: {
    flex: 1,
  },
  imageContainer: {
    position: 'relative',
  },
  gridImage: {
    width: '100%',
    height: 180,
    borderTopLeftRadius: borderRadius.md,
    borderTopRightRadius: borderRadius.md,
  },
  listImage: {
    width: '100%',
    height: 120,
    borderTopLeftRadius: borderRadius.md,
    borderTopRightRadius: borderRadius.md,
  },
  saleBadge: {
    position: 'absolute',
    top: spacing.sm,
    left: spacing.sm,
    backgroundColor: colors.error,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
    borderRadius: borderRadius.sm,
    zIndex: 1,
  },
  saleBadgeText: {
    fontSize: typography.sizes.xs,
    fontWeight: typography.weights.bold,
    color: colors.onError,
  },
  favoriteButton: {
    position: 'absolute',
    top: spacing.xs,
    right: spacing.xs,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
    borderRadius: borderRadius.full,
    margin: 0,
  },
  outOfStockOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    borderTopLeftRadius: borderRadius.md,
    borderTopRightRadius: borderRadius.md,
  },
  outOfStockText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onPrimary,
  },
  gridContent: {
    padding: spacing.md,
  },
  listContent: {
    padding: spacing.md,
  },
  categoryText: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    marginBottom: spacing.xs,
    textTransform: 'uppercase',
  },
  productTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    lineHeight: 20,
  },
  sellerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  sellerText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    flex: 1,
  },
  verifiedIcon: {
    fontSize: typography.sizes.sm,
    color: colors.success || '#4CAF50',
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  starsContainer: {
    flexDirection: 'row',
    marginRight: spacing.xs,
  },
  star: {
    fontSize: typography.sizes.sm,
  },
  ratingText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  currentPrice: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.bold,
    color: colors.onSurface,
    marginRight: spacing.sm,
  },
  originalPrice: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    textDecorationLine: 'line-through',
  },
  stockWarning: {
    fontSize: typography.sizes.xs,
    color: colors.error,
    fontWeight: typography.weights.medium,
  },
});