import React from 'react';
import {
  View,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Image,
} from 'react-native';
import { Card, Text } from 'react-native-paper';
import { colors, spacing, typography } from '../../constants/theme.js';

const { width: screenWidth } = Dimensions.get('window');

export const CategoryCard = ({
  category,
  onPress,
  size = 'medium',
}) => {
  const getCardDimensions = () => {
    const padding = spacing.md;
    const availableWidth = screenWidth - padding * 2;
    
    switch (size) {
      case 'small':
        return {
          width: (availableWidth - spacing.sm * 2) / 3,
          height: 80,
        };
      case 'large':
        return {
          width: availableWidth,
          height: 200,
        };
      default:
        return {
          width: (availableWidth - spacing.sm) / 2,
          height: 120,
        };
    }
  };

  const { width, height } = getCardDimensions();

  const formatProductCount = (count) => {
    if (count >= 1000) {
      return `${(count / 1000).toFixed(1)}K`;
    }
    return count.toString();
  };

  const cardStyle = [
    styles.card,
    {
      width,
      height,
    },
    size === 'large' && styles.largeCard,
  ];

  const contentStyle = [
    styles.content,
    size === 'large' && styles.largeContent,
  ];

  const titleStyle = [
    styles.title,
    size === 'small' && styles.smallTitle,
    size === 'large' && styles.largeTitle,
  ];

  return (
    <TouchableOpacity onPress={() => onPress(category)} activeOpacity={0.8}>
      <Card style={cardStyle}>
        <View style={styles.container}>
          {category.image && (
            <Image
              source={{ uri: category.image }}
              style={styles.backgroundImage}
              resizeMode="cover"
            />
          )}
          
          <View style={styles.overlay} />

          <View style={contentStyle}>
            <Text style={titleStyle}>
              {category.name}
            </Text>
            {size !== 'small' && (
              <Text style={styles.productCount}>
                {formatProductCount(category.product_count || 0)} sản phẩm
              </Text>
            )}
            
            {size === 'large' && category.description && (
              <Text style={styles.description}>
                {category.description}
              </Text>
            )}
          </View>

          {!category.is_active && (
            <View style={styles.inactiveOverlay}>
              <Text style={styles.inactiveText}>
                Tạm ngừng
              </Text>
            </View>
          )}
        </View>
      </Card>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    marginRight: spacing.sm,
    borderRadius: 12,
    overflow: 'hidden',
    elevation: 4,
  },
  largeCard: {
    marginHorizontal: 0,
  },
  container: {
    flex: 1,
    position: 'relative',
  },
  backgroundImage: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: '100%',
    height: '100%',
  },
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
  },
  content: {
    flex: 1,
    justifyContent: 'flex-end',
    padding: spacing.md,
    zIndex: 1,
  },
  largeContent: {
    justifyContent: 'center',
  },
  title: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onPrimary,
    marginBottom: spacing.xs,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  smallTitle: {
    fontSize: typography.sizes.sm,
    marginBottom: 0,
  },
  largeTitle: {
    fontSize: typography.sizes.lg,
    marginBottom: spacing.sm,
  },
  productCount: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    opacity: 0.9,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  description: {
    fontSize: typography.sizes.sm,
    color: colors.onPrimary,
    opacity: 0.8,
    marginTop: spacing.sm,
    lineHeight: 18,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
  inactiveOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 2,
  },
  inactiveText: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onPrimary,
    textShadowColor: 'rgba(0, 0, 0, 0.8)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },
});