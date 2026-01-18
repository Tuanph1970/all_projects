import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import {
  Appbar,
  Text,
  TextInput,
  Button,
  Card,
  ActivityIndicator,
} from 'react-native-paper';
import { useRoute, useNavigation } from '@react-navigation/native';
import { useSelector } from 'react-redux';
import { colors, spacing, typography, borderRadius } from '../../constants/theme.js';
import { useTranslation } from '@i18n';
import { reviewService } from '../../services/reviewService.js';
import { apiClient } from '../../services/apiClient.js';
import { API_CONFIG } from '../../constants/config.js';

export const WriteReviewScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const t = useTranslation();
  const { productId, productName } = route.params || {};

  const { user } = useSelector((state) => state.auth);

  const [rating, setRating] = useState(0);
  const [title, setTitle] = useState('');
  const [comment, setComment] = useState('');
  const [orderId, setOrderId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [eligibleOrders, setEligibleOrders] = useState([]);

  useEffect(() => {
    fetchEligibleOrders();
  }, [productId]);

  const fetchEligibleOrders = async () => {
    try {
      // Fetch user's orders that contain this product and are delivered
      const response = await apiClient.get(`${API_CONFIG.ENDPOINTS.ORDERS}/`);
      const orders = response?.orders || response || [];

      // Filter orders that:
      // 1. Contain the product
      // 2. Are delivered (completed)
      const eligible = orders.filter(order => {
        const hasProduct = order.items?.some(item => item.product_id === productId);
        const isDelivered = order.status?.toLowerCase() === 'delivered';
        return hasProduct && isDelivered;
      });

      setEligibleOrders(eligible);
      if (eligible.length > 0) {
        setOrderId(eligible[0].id);
      }
    } catch (error) {
      console.log('Error fetching orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (rating === 0) {
      Alert.alert(
        t('review.error') || 'Error',
        t('review.selectRating') || 'Please select a rating'
      );
      return;
    }

    if (!orderId) {
      Alert.alert(
        t('review.error') || 'Error',
        t('review.noEligibleOrder') || 'You need to purchase this product before reviewing'
      );
      return;
    }

    setSubmitting(true);

    try {
      await reviewService.createReview({
        product_id: productId,
        order_id: orderId,
        rating,
        title: title.trim() || null,
        comment: comment.trim() || null,
      });

      Alert.alert(
        t('review.success') || 'Success',
        t('review.reviewSubmitted') || 'Your review has been submitted!',
        [
          {
            text: t('common.ok') || 'OK',
            onPress: () => navigation.goBack(),
          },
        ]
      );
    } catch (error) {
      console.error('Error submitting review:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to submit review';
      Alert.alert(
        t('review.error') || 'Error',
        errorMessage
      );
    } finally {
      setSubmitting(false);
    }
  };

  const renderStarSelector = () => {
    return (
      <View style={styles.starContainer}>
        {[1, 2, 3, 4, 5].map((star) => (
          <TouchableOpacity
            key={star}
            onPress={() => setRating(star)}
            style={styles.starButton}
          >
            <Text style={[styles.star, star <= rating && styles.starSelected]}>
              {star <= rating ? '⭐' : '☆'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const getRatingLabel = () => {
    const labels = {
      1: t('review.terrible') || 'Terrible',
      2: t('review.poor') || 'Poor',
      3: t('review.average') || 'Average',
      4: t('review.good') || 'Good',
      5: t('review.excellent') || 'Excellent',
    };
    return rating > 0 ? labels[rating] : t('review.tapToRate') || 'Tap to rate';
  };

  if (loading) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('review.writeReview') || 'Write Review'} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      </View>
    );
  }

  if (eligibleOrders.length === 0) {
    return (
      <View style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={t('review.writeReview') || 'Write Review'} />
        </Appbar.Header>
        <View style={styles.notEligibleContainer}>
          <Text style={styles.notEligibleIcon}>📦</Text>
          <Text style={styles.notEligibleTitle}>
            {t('review.purchaseRequired') || 'Purchase Required'}
          </Text>
          <Text style={styles.notEligibleText}>
            {t('review.purchaseRequiredText') ||
              'You can only review products you have purchased and received.'}
          </Text>
          <Button
            mode="contained"
            onPress={() => navigation.goBack()}
            style={styles.goBackButton}
          >
            {t('common.goBack') || 'Go Back'}
          </Button>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={t('review.writeReview') || 'Write Review'} />
      </Appbar.Header>

      <ScrollView style={styles.content}>
        {/* Product Info */}
        <Card style={styles.productCard}>
          <Text style={styles.productName}>{productName || 'Product'}</Text>
        </Card>

        {/* Rating Section */}
        <Card style={styles.ratingCard}>
          <Text style={styles.sectionTitle}>
            {t('review.yourRating') || 'Your Rating'}
          </Text>
          {renderStarSelector()}
          <Text style={styles.ratingLabel}>{getRatingLabel()}</Text>
        </Card>

        {/* Review Form */}
        <Card style={styles.formCard}>
          <TextInput
            label={t('review.titleOptional') || 'Title (Optional)'}
            value={title}
            onChangeText={setTitle}
            style={styles.input}
            mode="outlined"
            placeholder={t('review.titlePlaceholder') || 'Summarize your experience'}
          />

          <TextInput
            label={t('review.commentOptional') || 'Comment (Optional)'}
            value={comment}
            onChangeText={setComment}
            style={styles.input}
            mode="outlined"
            multiline
            numberOfLines={5}
            placeholder={t('review.commentPlaceholder') || 'Tell others about your experience with this product'}
          />
        </Card>

        {/* Submit Button */}
        <Button
          mode="contained"
          onPress={handleSubmit}
          loading={submitting}
          disabled={submitting || rating === 0}
          style={styles.submitButton}
          contentStyle={styles.submitButtonContent}
        >
          {t('review.submitReview') || 'Submit Review'}
        </Button>
      </ScrollView>
    </View>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  notEligibleContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  notEligibleIcon: {
    fontSize: 64,
    marginBottom: spacing.md,
  },
  notEligibleTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  notEligibleText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.lg,
    lineHeight: 22,
  },
  goBackButton: {
    marginTop: spacing.md,
  },
  content: {
    flex: 1,
    padding: spacing.md,
  },
  productCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  productName: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    textAlign: 'center',
  },
  ratingCard: {
    padding: spacing.lg,
    marginBottom: spacing.md,
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.md,
  },
  starContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  starButton: {
    padding: spacing.sm,
  },
  star: {
    fontSize: 40,
    color: colors.outline,
  },
  starSelected: {
    color: colors.primary,
  },
  ratingLabel: {
    marginTop: spacing.sm,
    fontSize: typography.sizes.md,
    color: colors.primary,
    fontWeight: typography.weights.medium,
  },
  formCard: {
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  input: {
    marginBottom: spacing.md,
    backgroundColor: colors.surface,
  },
  submitButton: {
    marginVertical: spacing.lg,
    backgroundColor: colors.primary,
  },
  submitButtonContent: {
    height: 48,
  },
});
