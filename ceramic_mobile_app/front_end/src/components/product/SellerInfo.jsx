import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { Card, Title, Text, Avatar, Button, Chip, Divider } from 'react-native-paper';
import { colors, spacing, typography, borderRadius, shadows } from '../../constants/theme.js';

export const SellerInfo = ({
  seller,
  onSellerPress,
  onChatPress,
  showActions = true,
}) => {
  const formatRating = (rating) => {
    return rating ? rating.toFixed(1) : '0.0';
  };

  const getRatingColor = (rating) => {
    if (rating >= 4.5) return colors.success;
    if (rating >= 4.0) return colors.warning;
    if (rating >= 3.5) return colors.info;
    return colors.error;
  };

  const renderRatingStars = (rating) => {
    const fullStars = Math.floor(rating || 0);
    const hasHalfStar = (rating || 0) % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    const stars = [];
    
    for (let i = 0; i < fullStars; i++) {
      stars.push(<Text key={`full-${i}`} style={styles.starFull}>★</Text>);
    }
    
    if (hasHalfStar) {
      stars.push(<Text key="half" style={styles.starHalf}>★</Text>);
    }
    
    for (let i = 0; i < emptyStars; i++) {
      stars.push(<Text key={`empty-${i}`} style={styles.starEmpty}>☆</Text>);
    }
    
    return stars;
  };

  return (
    <Card style={styles.container}>
      <Card.Content style={styles.content}>
        <View style={styles.header}>
          <View style={styles.sellerInfo}>
            <Avatar.Image
              size={50}
              source={{ uri: seller.avatar || 'https://via.placeholder.com/50' }}
              style={styles.avatar}
            />
            <View style={styles.sellerDetails}>
              <View style={styles.nameContainer}>
                <Title style={styles.businessName}>
                  {seller.businessName || seller.displayName}
                </Title>
                {seller.isVerified && (
                  <Chip
                    icon="check-decagram"
                    style={styles.verifiedChip}
                    textStyle={styles.verifiedText}
                    compact
                  >
                    ✓ Xác thực
                  </Chip>
                )}
              </View>
              
              <Text style={styles.displayName}>
                {seller.displayName}
              </Text>

              {seller.location && (
                <Text style={styles.location}>
                  📍 {seller.location}
                </Text>
              )}
            </View>
          </View>

          {onSellerPress && (
            <Button
              mode="text"
              onPress={onSellerPress}
              compact
            >
              Xem cửa hàng
            </Button>
          )}
        </View>

        <View style={styles.ratingSection}>
          <View style={styles.ratingContainer}>
            <View style={styles.starsContainer}>
              {renderRatingStars(seller.rating)}
            </View>
            <Text style={styles.ratingText}>
              {formatRating(seller.rating)}
            </Text>
            <Text style={styles.reviewCount}>
              ({seller.reviewCount || 0} đánh giá)
            </Text>
          </View>
        </View>

        <View style={styles.statsContainer}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>
              {seller.reviewCount || 0}
            </Text>
            <Text style={styles.statLabel}>
              Đánh giá
            </Text>
          </View>

          <Divider style={styles.statDivider} />

          <View style={styles.statItem}>
            <Text style={[styles.statValue, { color: getRatingColor(seller.rating) }]}>
              {formatRating(seller.rating)}
            </Text>
            <Text style={styles.statLabel}>
              Xếp hạng
            </Text>
          </View>

          <Divider style={styles.statDivider} />

          <View style={styles.statItem}>
            <Text style={styles.statValue}>
              {seller.isVerified ? 'Có' : 'Chưa'}
            </Text>
            <Text style={styles.statLabel}>
              Xác thực
            </Text>
          </View>
        </View>

        {showActions && (
          <View style={styles.actionsContainer}>
            {onSellerPress && (
              <Button
                mode="outlined"
                onPress={onSellerPress}
                style={[styles.actionButton, styles.viewStoreButton]}
                contentStyle={styles.actionButtonContent}
                labelStyle={styles.actionButtonLabel}
              >
                Xem cửa hàng
              </Button>
            )}
            {onChatPress && (
              <Button
                mode="contained"
                onPress={onChatPress}
                style={[styles.actionButton, styles.chatButton]}
                contentStyle={styles.actionButtonContent}
                labelStyle={styles.actionButtonLabel}
              >
                Nhắn tin
              </Button>
            )}
          </View>
        )}
      </Card.Content>
    </Card>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: colors.surface,
    borderRadius: borderRadius.md,
    marginBottom: spacing.lg,
    ...shadows.sm,
  },
  content: {
    padding: spacing.lg,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    marginBottom: spacing.md,
  },
  sellerInfo: {
    flexDirection: 'row',
    flex: 1,
    alignItems: 'flex-start',
  },
  avatar: {
    marginRight: spacing.md,
  },
  sellerDetails: {
    flex: 1,
  },
  nameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  businessName: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    flex: 1,
    marginRight: spacing.sm,
  },
  verifiedChip: {
    backgroundColor: colors.successContainer,
    borderColor: colors.success,
  },
  verifiedText: {
    fontSize: typography.sizes.xs,
    color: colors.onSuccessContainer,
    fontWeight: typography.weights.medium,
  },
  displayName: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    marginBottom: spacing.xs,
  },
  location: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  ratingSection: {
    paddingBottom: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.outlineVariant,
    marginBottom: spacing.md,
  },
  ratingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  starsContainer: {
    flexDirection: 'row',
    marginRight: spacing.sm,
  },
  starFull: {
    fontSize: typography.sizes.md,
    color: colors.warning,
  },
  starHalf: {
    fontSize: typography.sizes.md,
    color: colors.warning,
    opacity: 0.5,
  },
  starEmpty: {
    fontSize: typography.sizes.md,
    color: colors.outline,
  },
  ratingText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginRight: spacing.xs,
  },
  reviewCount: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.surfaceVariant,
    borderRadius: borderRadius.sm,
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statValue: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.bold,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  statLabel: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  statDivider: {
    width: 1,
    height: 40,
    backgroundColor: colors.outlineVariant,
    marginHorizontal: spacing.md,
  },
  actionsContainer: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  actionButton: {
    flex: 1,
    borderRadius: borderRadius.md,
  },
  viewStoreButton: {
    borderColor: colors.primary,
  },
  chatButton: {
    backgroundColor: colors.primary,
  },
  actionButtonContent: {
    paddingVertical: spacing.sm,
  },
  actionButtonLabel: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
  },
});