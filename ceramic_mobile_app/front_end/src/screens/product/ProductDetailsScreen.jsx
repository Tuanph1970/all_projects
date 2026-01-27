import React, { useEffect, useState } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  Share,
  Alert,
} from 'react-native';
import {
  Appbar,
  Text,
  Title,
  Paragraph,
  Button,
  Chip,
  Divider,
  Card,
  ActivityIndicator,
} from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import { useSelector, useDispatch } from 'react-redux';
import { fetchProduct, toggleFavorite } from '../../store/slices/productSlice.js';
import { addToCart } from '../../store/slices/cartSlice.js';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';
import { useTranslation } from '@i18n';
import { productService } from '../../services/productService.js';
import { reviewService } from '../../services/reviewService.js';

export const ProductDetailsScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const dispatch = useDispatch();
  const t = useTranslation();
  const { productId } = route.params;
  
  const {
    currentProduct: product,
    relatedProducts,
    favorites,
    isProductLoading,
    productError,
  } = useSelector((state) => state.products);

  const { loading: cartLoading } = useSelector((state) => state.cart);
  const { isAuthenticated, user } = useSelector((state) => state.auth);

  const [quantity, setQuantity] = useState(1);
  const [reviews, setReviews] = useState([]);
  const [reviewStats, setReviewStats] = useState(null);
  const [reviewsLoading, setReviewsLoading] = useState(false);

  useEffect(() => {
    if (productId) {
      dispatch(fetchProduct(productId));
    }
  }, [productId, dispatch]);

  // Track product view for analytics
  useEffect(() => {
    if (productId && product) {
      productService.trackProductView(productId);
    }
  }, [productId, product]);

  // Fetch reviews for product
  useEffect(() => {
    const fetchReviews = async () => {
      if (!productId) return;

      setReviewsLoading(true);
      try {
        const [reviewsData, statsData] = await Promise.all([
          reviewService.getProductReviews(productId, { limit: 5 }),
          reviewService.getProductReviewStats(productId),
        ]);
        setReviews(reviewsData || []);
        setReviewStats(statsData);
      } catch (error) {
        console.log('Error fetching reviews:', error);
        // Silently fail - reviews are not critical
      } finally {
        setReviewsLoading(false);
      }
    };

    fetchReviews();
  }, [productId]);

  const handleShare = async () => {
    if (!product) return;
    
    try {
      await Share.share({
        message: `Check out this amazing product: ${product.name} - ${product.description}`,
        title: product.name,
      });
    } catch (error) {
      console.error('Error sharing product:', error);
    }
  };

  const handleFavoriteToggle = () => {
    if (product) {
      dispatch(toggleFavorite(product.id));
    }
  };

  const handleAddToCart = async () => {
    if (!product) return;

    try {
      await dispatch(addToCart({
        product_id: product.id,
        quantity: quantity
      })).unwrap();

      Alert.alert(
        t('product.addedToCart'),
        t('product.addedToCartMessage', { quantity, name: product.name }),
        [
          { text: t('product.continueShopping'), style: 'cancel' },
          { text: t('product.viewCart'), onPress: () => navigation.navigate('Cart') }
        ]
      );
    } catch (error) {
      Alert.alert(
        t('common.error'),
        error.message || t('product.addToCartError'),
        [{ text: t('common.ok') }]
      );
    }
  };

  const handleBuyNow = () => {
    if (!product) return;

    Alert.alert(
      t('product.comingSoon'),
      t('product.buyNowComingSoon'),
      [{ text: t('common.ok') }]
    );
  };

  const handleSellerPress = () => {
    if (!product?.seller) return;
    
    // Navigate to seller profile
    navigation.navigate('SellerProfile', { sellerId: product.seller.id });
  };

  const handleChatPress = () => {
    if (!product?.seller) return;

    // Navigate to chat with seller - pass sellerId and productId for room creation
    navigation.navigate('ChatScreen', {
      sellerId: product.seller.id,
      productId: product.id,
      recipientName: product.seller.name
    });
  };

  const handleRelatedProductPress = (relatedProduct) => {
    navigation.push('ProductDetails', { productId: relatedProduct.id });
  };

  const handleQuantityChange = (change) => {
    const newQuantity = quantity + change;
    if (newQuantity >= 1 && newQuantity <= (product?.stock || 1)) {
      setQuantity(newQuantity);
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('vi-VN', {
      style: 'currency',
      currency: 'VND',
    }).format(price);
  };

  const renderSpecifications = () => {
    if (!product?.specifications || product.specifications.length === 0) {
      return null;
    }

    return (
      <Card style={styles.specCard}>
        <View style={styles.cardHeader}>
          <Text style={styles.sectionTitle}>{t('product.specifications')}</Text>
        </View>
        <View style={styles.specContainer}>
          {product.specifications.map((spec, index) => (
            <View key={index} style={styles.specRow}>
              <Text style={styles.specName}>{spec.name}:</Text>
              <Text style={styles.specValue}>
                {spec.value} {spec.unit || ''}
              </Text>
            </View>
          ))}
        </View>
      </Card>
    );
  };

  const renderTags = () => {
    // Handle tags as string (comma-separated) or array
    let tagsArray = product?.tags;

    if (!tagsArray) {
      return null;
    }

    // If tags is a string, split it into an array
    if (typeof tagsArray === 'string') {
      tagsArray = tagsArray.split(',').map(tag => tag.trim()).filter(tag => tag);
    }

    // Ensure it's an array
    if (!Array.isArray(tagsArray) || tagsArray.length === 0) {
      return null;
    }

    return (
      <View style={styles.tagsContainer}>
        <Text style={styles.tagsLabel}>{t('product.tags')}:</Text>
        <View style={styles.tagsRow}>
          {tagsArray.map((tag, index) => (
            <Chip key={index} style={styles.tag}>
              <Text style={styles.tagText}>{tag}</Text>
            </Chip>
          ))}
        </View>
      </View>
    );
  };

  const renderStars = (rating) => {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push('⭐');
      } else if (i === fullStars && hasHalfStar) {
        stars.push('⭐');
      } else {
        stars.push('☆');
      }
    }
    return stars.join('');
  };

  const handleMarkHelpful = async (reviewId) => {
    try {
      await reviewService.markHelpful(reviewId);
      // Update local state
      setReviews(prev => prev.map(r =>
        r.id === reviewId
          ? { ...r, is_helpful_count: (r.is_helpful_count || 0) + 1 }
          : r
      ));
    } catch (error) {
      console.log('Error marking review helpful:', error);
    }
  };

  const handleWriteReview = () => {
    if (!isAuthenticated) {
      Alert.alert(
        t('auth.loginRequired') || 'Login Required',
        t('auth.loginToReview') || 'Please login to write a review',
        [
          { text: t('common.cancel') || 'Cancel', style: 'cancel' },
          { text: t('auth.signIn') || 'Sign In', onPress: () => navigation.navigate('Auth') },
        ]
      );
      return;
    }
    navigation.navigate('WriteReview', { productId, productName: product?.name });
  };

  const handleEditReview = (review) => {
    navigation.navigate('WriteReview', {
      productId,
      productName: product?.name,
      reviewId: review.id,
      existingReview: {
        rating: review.rating,
        title: review.title,
        comment: review.comment,
        order_id: review.order_id,
        product_name: product?.name,
      },
    });
  };

  const renderReviews = () => {
    return (
      <Card style={styles.reviewsCard}>
        <View style={styles.cardHeader}>
          <Text style={styles.sectionTitle}>{t('product.customerReviews') || 'Customer Reviews'}</Text>
        </View>

        {/* Review Stats */}
        {reviewStats && (
          <View style={styles.reviewStatsContainer}>
            <View style={styles.reviewStatsMain}>
              <Text style={styles.avgRating}>{reviewStats.average_rating?.toFixed(1) || '0.0'}</Text>
              <Text style={styles.avgRatingStars}>{renderStars(reviewStats.average_rating || 0)}</Text>
              <Text style={styles.totalReviews}>
                {reviewStats.total_reviews || 0} {t('product.reviews', { count: reviewStats.total_reviews || 0 })}
              </Text>
            </View>

            {/* Rating Distribution */}
            <View style={styles.ratingDistribution}>
              {[5, 4, 3, 2, 1].map(star => {
                const count = reviewStats.rating_distribution?.[star] || 0;
                const percentage = reviewStats.total_reviews > 0
                  ? (count / reviewStats.total_reviews) * 100
                  : 0;
                return (
                  <View key={star} style={styles.ratingBar}>
                    <Text style={styles.ratingBarLabel}>{star}⭐</Text>
                    <View style={styles.ratingBarTrack}>
                      <View style={[styles.ratingBarFill, { width: `${percentage}%` }]} />
                    </View>
                    <Text style={styles.ratingBarCount}>{count}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* Review List */}
        {reviewsLoading ? (
          <View style={styles.reviewsLoading}>
            <ActivityIndicator size="small" color={colors.primary} />
          </View>
        ) : reviews.length > 0 ? (
          <View style={styles.reviewsList}>
            {reviews.map((review) => (
              <View key={review.id} style={styles.reviewItem}>
                <View style={styles.reviewHeader}>
                  <Text style={styles.reviewRating}>{renderStars(review.rating)}</Text>
                  {review.is_verified_purchase && (
                    <Chip style={styles.verifiedChip} textStyle={styles.verifiedChipText}>
                      {t('product.verifiedPurchase') || 'Verified'}
                    </Chip>
                  )}
                </View>
                {review.title && <Text style={styles.reviewTitle}>{review.title}</Text>}
                {review.comment && <Text style={styles.reviewComment}>{review.comment}</Text>}
                <View style={styles.reviewFooter}>
                  <Text style={styles.reviewDate}>
                    {new Date(review.created_at).toLocaleDateString()}
                  </Text>
                  <View style={styles.reviewActions}>
                    {user && String(user.id) === String(review.reviewer_id) && (
                      <Button
                        mode="text"
                        compact
                        onPress={() => handleEditReview(review)}
                        style={styles.editButton}
                        testID={`edit-review-${review.id}`}
                      >
                        {t('common.edit') || 'Edit'}
                      </Button>
                    )}
                    <Button
                      mode="text"
                      compact
                      onPress={() => handleMarkHelpful(review.id)}
                      style={styles.helpfulButton}
                    >
                      {t('product.helpful') || 'Helpful'} ({review.is_helpful_count || 0})
                    </Button>
                  </View>
                </View>
                {review.seller_response && (
                  <View style={styles.sellerResponse}>
                    <Text style={styles.sellerResponseLabel}>
                      {t('product.sellerResponse') || 'Seller Response'}:
                    </Text>
                    <Text style={styles.sellerResponseText}>{review.seller_response}</Text>
                  </View>
                )}
              </View>
            ))}
          </View>
        ) : (
          <View style={styles.noReviews}>
            <Text style={styles.noReviewsText}>
              {t('product.noReviews') || 'No reviews yet. Be the first to review!'}
            </Text>
          </View>
        )}

        {/* Write Review Button */}
        <Button
          mode="outlined"
          onPress={handleWriteReview}
          style={styles.writeReviewButton}
          icon="pencil"
        >
          {t('product.writeReview') || 'Write a Review'}
        </Button>
      </Card>
    );
  };

  if (isProductLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('common.loading')} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('product.loadingProduct')}</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (productError || !product) {
    return (
      <SafeAreaView style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('common.error')} />
        </Appbar.Header>
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>❌</Text>
          <Text style={styles.errorTitle}>{t('product.notFound')}</Text>
          <Text style={styles.errorMessage}>
            {productError || t('product.notFoundMessage')}
          </Text>
          <Button
            mode="contained"
            onPress={() => navigation.goBack()}
            style={styles.backButton}
          >
            {t('common.goBack')}
          </Button>
        </View>
      </SafeAreaView>
    );
  }

  const isFavorite = favorites.some(fav => fav.id === product.id);
  const isOutOfStock = product.stock === 0;

  return (
    <SafeAreaView style={styles.container} testID="product-details-screen">
      {/* Header */}
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="product-details-back-button" />
        <Appbar.Content title={product.name} />
        <Appbar.Action icon={isFavorite ? "heart" : "heart-outline"} onPress={handleFavoriteToggle} testID="product-favorite-button" />
        <Appbar.Action icon="share" onPress={handleShare} />
      </Appbar.Header>

      <ScrollView style={styles.scrollView}>
        {/* Image Gallery */}
        {product.images && product.images.length > 0 && (
          <View style={styles.imageContainer}>
            <Text style={styles.imagePlaceholder}>
              📷 Product Images ({product.images.length})
            </Text>
          </View>
        )}

        {/* Product Info */}
        <Card style={styles.productInfo}>
          {/* Category */}
          <Text style={styles.category}>{product.category?.name || 'Product'}</Text>
          
          {/* Title */}
          <Text style={styles.productTitle}>{product.name}</Text>
          
          {/* Price */}
          <View style={styles.priceContainer}>
            <Text style={styles.currentPrice}>
              {formatPrice(product.price)}
            </Text>
            {product.originalPrice && product.originalPrice > product.price && (
              <>
                <Text style={styles.originalPrice}>
                  {formatPrice(product.originalPrice)}
                </Text>
                <Chip style={styles.discountChip}>
                  <Text style={styles.discountText}>
                    -{Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)}%
                  </Text>
                </Chip>
              </>
            )}
          </View>

          {/* Rating */}
          <View style={styles.ratingContainer}>
            <Text style={styles.ratingText}>
              ⭐ {product.rating?.toFixed(1) || '0.0'} ({t('product.reviews', { count: product.reviewCount || 0 })})
            </Text>
          </View>

          {/* Stock Status */}
          <View style={styles.stockContainer}>
            {isOutOfStock ? (
              <Chip style={styles.outOfStockChip}>
                <Text style={styles.outOfStockText}>{t('product.outOfStock')}</Text>
              </Chip>
            ) : product.stock <= 10 ? (
              <Text style={styles.lowStockText}>
                {t('product.lowStock', { count: product.stock })}
              </Text>
            ) : (
              <Text style={styles.inStockText}>{t('product.inStock')}</Text>
            )}
          </View>

          {/* Category */}
          {product.seller_category && (
            <View style={styles.categoryContainer}>
              <Text style={styles.categoryLabel}>{t('product.category')}:</Text>
              <Chip style={styles.categoryChip} textStyle={styles.categoryChipText}>
                {product.seller_category.full_path_name || product.seller_category.name}
              </Chip>
            </View>
          )}

          {/* Tags */}
          {renderTags()}
        </Card>

        {/* Description */}
        <Card style={styles.descriptionCard}>
          <View style={styles.cardHeader}>
            <Text style={styles.sectionTitle}>{t('product.description')}</Text>
          </View>
          <Text style={styles.description}>
            {product.description}
          </Text>
        </Card>

        {/* Specifications */}
        {renderSpecifications()}

        {/* Seller Info */}
        {product.seller && (
          <Card style={styles.sellerCard}>
            <View style={styles.cardHeader}>
              <Text style={styles.sectionTitle}>{t('product.sellerInfo')}</Text>
            </View>
            <View style={styles.sellerInfo}>
              <Text style={styles.sellerName}>{product.seller.name}</Text>
              <Text style={styles.sellerRating}>
                ⭐ {product.seller.rating?.toFixed(1) || '0.0'} ({t('product.reviews', { count: product.seller.reviewCount || 0 })})
              </Text>
              <View style={styles.sellerActions}>
                <Button mode="outlined" onPress={handleSellerPress} style={styles.sellerButton}>
                  {t('product.viewProfile')}
                </Button>
                <Button mode="contained" onPress={handleChatPress} style={styles.chatButton}>
                  {t('product.chatNow')}
                </Button>
              </View>
            </View>
          </Card>
        )}

        {/* Customer Reviews */}
        {renderReviews()}

        {/* Related Products */}
        {relatedProducts && relatedProducts.length > 0 && (
          <Card style={styles.relatedCard}>
            <View style={styles.cardHeader}>
              <Text style={styles.sectionTitle}>{t('product.relatedProducts')}</Text>
            </View>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {relatedProducts.slice(0, 5).map((relatedProduct) => (
                <View key={relatedProduct.id} style={styles.relatedItem}>
                  <Button
                    mode="outlined"
                    onPress={() => handleRelatedProductPress(relatedProduct)}
                    style={styles.relatedButton}
                  >
                    {relatedProduct.name}
                  </Button>
                </View>
              ))}
            </ScrollView>
          </Card>
        )}
      </ScrollView>

      {/* Bottom Actions */}
      <View style={styles.bottomActions}>
        {/* Quantity Selector */}
        {!isOutOfStock && (
          <View style={styles.quantityContainer}>
            <Text style={styles.quantityLabel}>{t('product.quantity')}:</Text>
            <View style={styles.quantitySelector}>
              <Button
                mode="outlined"
                onPress={() => handleQuantityChange(-1)}
                disabled={quantity <= 1}
                style={styles.quantityButton}
                contentStyle={styles.quantityButtonContent}
                testID="product-quantity-minus"
              >
                -
              </Button>
              <Text style={styles.quantityText} testID="product-quantity-text">{quantity}</Text>
              <Button
                mode="outlined"
                onPress={() => handleQuantityChange(1)}
                disabled={quantity >= product.stock}
                style={styles.quantityButton}
                contentStyle={styles.quantityButtonContent}
                testID="product-quantity-plus"
              >
                +
              </Button>
            </View>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <Button
            mode="outlined"
            onPress={handleAddToCart}
            disabled={isOutOfStock || cartLoading}
            style={[styles.actionButton, styles.addToCartButton]}
            contentStyle={styles.actionButtonContent}
            testID="product-add-to-cart-button"
          >
            {t('product.addToCart')}
          </Button>
          <Button
            mode="contained"
            onPress={handleBuyNow}
            disabled={isOutOfStock}
            style={[styles.actionButton, styles.buyNowButton]}
            contentStyle={styles.actionButtonContent}
            testID="product-buy-now-button"
          >
            {t('product.buyNow')}
          </Button>
        </View>
      </View>
    </SafeAreaView>
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
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    fontSize: typography.sizes.md,
    color: colors.onSurface,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  errorTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  errorMessage: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.lg,
    lineHeight: 20,
  },
  backButton: {
    marginTop: spacing.md,
  },
  imageContainer: {
    height: 200,
    backgroundColor: colors.surfaceVariant,
    justifyContent: 'center',
    alignItems: 'center',
  },
  imagePlaceholder: {
    fontSize: typography.sizes.lg,
    color: colors.outline,
  },
  productInfo: {
    margin: spacing.md,
    padding: spacing.md,
    backgroundColor: colors.surface,
  },
  category: {
    fontSize: typography.sizes.sm,
    color: colors.primary,
    fontWeight: typography.weights.medium,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  productTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.md,
    lineHeight: 28,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  currentPrice: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
    marginRight: spacing.sm,
  },
  originalPrice: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textDecorationLine: 'line-through',
    marginRight: spacing.sm,
  },
  discountChip: {
    backgroundColor: colors.error,
  },
  discountText: {
    color: colors.onError,
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
  },
  ratingContainer: {
    marginBottom: spacing.md,
  },
  ratingText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
  },
  stockContainer: {
    marginBottom: spacing.md,
  },
  outOfStockChip: {
    backgroundColor: colors.error,
    alignSelf: 'flex-start',
  },
  outOfStockText: {
    color: colors.onError,
    fontWeight: typography.weights.medium,
  },
  lowStockText: {
    color: colors.error,
    fontWeight: typography.weights.medium,
  },
  inStockText: {
    color: colors.success,
    fontWeight: typography.weights.medium,
  },
  categoryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.md,
    flexWrap: 'wrap',
  },
  categoryLabel: {
    fontSize: typography.sizes.sm,
    color: colors.textSecondary,
    marginRight: spacing.xs,
  },
  categoryChip: {
    backgroundColor: colors.primaryLight || '#E3F2FD',
  },
  categoryChipText: {
    fontSize: typography.sizes.sm,
    color: colors.primary,
  },
  tagsContainer: {
    marginTop: spacing.sm,
  },
  tagsLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  tagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  tag: {
    marginRight: spacing.xs,
    marginBottom: spacing.xs,
  },
  tagText: {
    fontSize: typography.sizes.sm,
  },
  descriptionCard: {
    margin: spacing.md,
    backgroundColor: colors.surface,
  },
  specCard: {
    margin: spacing.md,
    backgroundColor: colors.surface,
  },
  sellerCard: {
    margin: spacing.md,
    backgroundColor: colors.surface,
  },
  relatedCard: {
    margin: spacing.md,
    backgroundColor: colors.surface,
  },
  cardHeader: {
    padding: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  description: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    lineHeight: 20,
    padding: spacing.md,
  },
  specContainer: {
    padding: spacing.md,
  },
  specRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  specName: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    flex: 1,
  },
  specValue: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    fontWeight: typography.weights.medium,
  },
  sellerInfo: {
    padding: spacing.md,
  },
  sellerName: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  sellerRating: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    marginBottom: spacing.md,
  },
  sellerActions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  sellerButton: {
    flex: 1,
  },
  chatButton: {
    flex: 1,
  },
  relatedItem: {
    marginRight: spacing.sm,
    marginBottom: spacing.sm,
  },
  relatedButton: {
    minWidth: 120,
  },
  bottomActions: {
    backgroundColor: colors.surface,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.outline,
    ...shadows.lg,
  },
  quantityContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  quantityLabel: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    fontWeight: typography.weights.medium,
  },
  quantitySelector: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  quantityButton: {
    minWidth: 40,
    borderColor: colors.outline,
  },
  quantityButtonContent: {
    height: 32,
  },
  quantityText: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginHorizontal: spacing.md,
    minWidth: 40,
    textAlign: 'center',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionButton: {
    flex: 1,
    borderRadius: borderRadius.md,
  },
  addToCartButton: {
    borderColor: colors.primary,
  },
  buyNowButton: {
    backgroundColor: colors.primary,
  },
  actionButtonContent: {
    height: 48,
  },
  // Review styles
  reviewsCard: {
    margin: spacing.md,
    backgroundColor: colors.surface,
  },
  reviewStatsContainer: {
    padding: spacing.md,
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  reviewStatsMain: {
    alignItems: 'center',
    marginRight: spacing.lg,
    minWidth: 80,
  },
  avgRating: {
    fontSize: 36,
    fontWeight: typography.weights.bold,
    color: colors.onSurface,
  },
  avgRatingStars: {
    fontSize: typography.sizes.md,
    marginVertical: spacing.xs,
  },
  totalReviews: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  ratingDistribution: {
    flex: 1,
  },
  ratingBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 2,
  },
  ratingBarLabel: {
    fontSize: typography.sizes.xs,
    width: 30,
  },
  ratingBarTrack: {
    flex: 1,
    height: 8,
    backgroundColor: colors.surfaceVariant,
    borderRadius: 4,
    marginHorizontal: spacing.xs,
  },
  ratingBarFill: {
    height: '100%',
    backgroundColor: colors.primary,
    borderRadius: 4,
  },
  ratingBarCount: {
    fontSize: typography.sizes.xs,
    color: colors.outline,
    width: 20,
    textAlign: 'right',
  },
  reviewsLoading: {
    padding: spacing.lg,
    alignItems: 'center',
  },
  reviewsList: {
    padding: spacing.md,
  },
  reviewItem: {
    marginBottom: spacing.md,
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  reviewHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  reviewRating: {
    fontSize: typography.sizes.md,
  },
  verifiedChip: {
    marginLeft: spacing.sm,
    backgroundColor: colors.success,
    height: 24,
  },
  verifiedChipText: {
    fontSize: typography.sizes.xs,
    color: colors.onSuccess || '#fff',
  },
  reviewTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  reviewComment: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    lineHeight: 20,
  },
  reviewFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: spacing.sm,
  },
  reviewDate: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  reviewActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  editButton: {
    marginRight: spacing.xs,
  },
  helpfulButton: {
    marginRight: -spacing.sm,
  },
  sellerResponse: {
    marginTop: spacing.sm,
    padding: spacing.sm,
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
  },
  sellerResponseLabel: {
    fontSize: typography.sizes.sm,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  sellerResponseText: {
    fontSize: typography.sizes.sm,
    color: colors.onSurface,
  },
  noReviews: {
    padding: spacing.lg,
    alignItems: 'center',
  },
  noReviewsText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
  },
  writeReviewButton: {
    margin: spacing.md,
    borderColor: colors.primary,
  },
});