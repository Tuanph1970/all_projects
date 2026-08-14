import React, { useCallback } from 'react';
import {
  View,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Text,
  Dimensions,
} from 'react-native';
import { ProductCard } from './ProductCard.jsx';
import { colors, spacing, typography } from '../../constants/theme.js';

const { width: screenWidth } = Dimensions.get('window');

export const ProductList = ({
  products,
  onProductPress,
  onFavoritePress,
  favorites = [],
  viewType = 'grid',
  isLoading = false,
  isLoadingMore = false,
  isRefreshing = false,
  hasMore = false,
  onLoadMore,
  onRefresh,
  emptyMessage = 'Không có sản phẩm nào',
  numColumns,
}) => {
  const isGridView = viewType === 'grid';
  const columns = numColumns || (isGridView ? 2 : 1);
  const containerWidth = screenWidth - spacing.md * 2;

  const renderProduct = useCallback(
    ({ item }) => {
      const isFavorite = favorites.includes(item.id);
      
      return (
        <ProductCard
          product={item}
          onPress={() => onProductPress(item)}
          onFavoritePress={onFavoritePress ? () => onFavoritePress(item) : undefined}
          isFavorite={isFavorite}
          viewType={viewType}
          containerWidth={containerWidth}
        />
      );
    },
    [favorites, onProductPress, onFavoritePress, viewType, containerWidth]
  );

  const renderFooter = useCallback(() => {
    if (!isLoadingMore) return null;
    
    return (
      <View style={styles.footerLoader}>
        <ActivityIndicator size="small" color={colors.primary} />
        <Text style={styles.loadingText}>
          Đang tải thêm...
        </Text>
      </View>
    );
  }, [isLoadingMore]);

  const renderEmpty = useCallback(() => {
    if (isLoading) {
      return (
        <View style={styles.emptyContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>
            Đang tải sản phẩm...
          </Text>
        </View>
      );
    }

    return (
      <View style={styles.emptyContainer}>
        <Text style={styles.emptyIcon}>📦</Text>
        <Text style={styles.emptyTitle}>Trống</Text>
        <Text style={styles.emptyMessage}>
          {emptyMessage}
        </Text>
      </View>
    );
  }, [isLoading, emptyMessage]);

  const handleEndReached = useCallback(() => {
    if (hasMore && !isLoadingMore && onLoadMore) {
      onLoadMore();
    }
  }, [hasMore, isLoadingMore, onLoadMore]);

  const keyExtractor = useCallback((item) => item.id?.toString() || Math.random().toString(), []);

  const getItemLayout = useCallback(
    (data, index) => {
      const itemHeight = isGridView ? 280 : 200;
      const offset = Math.floor(index / columns) * itemHeight;
      return {
        length: itemHeight,
        offset,
        index,
      };
    },
    [isGridView, columns]
  );

  return (
    <View style={styles.container}>
      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={keyExtractor}
        numColumns={columns}
        key={`${viewType}-${columns}`}
        contentContainerStyle={[
          styles.contentContainer,
          isGridView && styles.gridContainer,
        ]}
        columnWrapperStyle={isGridView ? styles.row : null}
        showsVerticalScrollIndicator={false}
        onEndReached={handleEndReached}
        onEndReachedThreshold={0.5}
        getItemLayout={getItemLayout}
        removeClippedSubviews={true}
        maxToRenderPerBatch={10}
        windowSize={10}
        initialNumToRender={8}
        ListEmptyComponent={renderEmpty}
        ListFooterComponent={renderFooter}
        refreshControl={
          onRefresh ? (
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={onRefresh}
              colors={[colors.primary]}
              tintColor={colors.primary}
            />
          ) : undefined
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  contentContainer: {
    paddingBottom: spacing.xl,
  },
  gridContainer: {
    paddingHorizontal: spacing.md,
  },
  row: {
    justifyContent: 'space-between',
    paddingHorizontal: spacing.md,
  },
  footerLoader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.lg,
  },
  loadingText: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
    marginLeft: spacing.sm,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: spacing.xl * 2,
    paddingHorizontal: spacing.lg,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: spacing.md,
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  emptyMessage: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    lineHeight: 20,
  },
});