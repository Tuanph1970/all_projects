import React, { useEffect } from 'react';
import { View, StyleSheet, ScrollView, RefreshControl, FlatList } from 'react-native';
import { Text, Title, Appbar, Button, Card } from 'react-native-paper';
import { useSelector, useDispatch } from 'react-redux';
import {
  fetchFeaturedProducts,
  fetchPopularProducts,
  fetchNewArrivals,
  toggleFavorite
} from '../../store/slices/productSlice.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

export const HomeScreen = () => {
  const dispatch = useDispatch();
  const t = useTranslation();
  const { user } = useSelector((state) => state.auth);
  const {
    featuredProducts,
    mainCategories,
    popularProducts,
    newArrivals,
    favorites,
    isFeaturedLoading,
    isLoading,
    error,
  } = useSelector((state) => state.products);

  useEffect(() => {
    // Skip data loading during E2E tests to prevent Detox timeouts
    if (global.__E2E__) {
      console.log('[E2E] Skipping HomeScreen data load');
      return;
    }
    loadHomeData();
  }, []);

  const loadHomeData = async () => {
    try {
      await Promise.all([
        dispatch(fetchFeaturedProducts()),
        dispatch(fetchPopularProducts(10)),
        dispatch(fetchNewArrivals(10)),
      ]);
    } catch (error) {
      console.error('Failed to load home data:', error);
    }
  };

  const handleProductPress = (product) => {
    // TODO, product.title);
  };

  const handleCategoryPress = (category) => {
    // TODO, category.name);
  };

  const handleFavoritePress = (product) => {
    dispatch(toggleFavorite(product.id));
  };

  const handleRefresh = () => {
    loadHomeData();
  };

  const renderCategoryItem = ({ item }) => (
    <Card style={styles.categoryCard} onPress={() => handleCategoryPress(item)}>
      <Card.Content>
        <Text style={styles.categoryName}>{item.name}</Text>
        <Text style={styles.categoryCount}>{item.productCount || 0} {t('home.products')}</Text>
      </Card.Content>
    </Card>
  );

  const renderPopularProduct = ({ item }) => (
    <Card style={styles.productCard} onPress={() => handleProductPress(item)}>
      <Card.Content>
        <Text style={styles.productName}>{item.name}</Text>
        <Text style={styles.productPrice}>${parseFloat(item.price || 0).toFixed(2)}</Text>
      </Card.Content>
    </Card>
  );

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={isLoading}
          onRefresh={handleRefresh}
        />
      }
    >
        {/* Welcome Section - Always visible */}
        <Card style={styles.welcomeCard}>
          <Card.Content>
            <Text style={styles.welcomeTitle}>
              {t('home.greeting', { name: user?.fullName || t('home.greetingGuest').replace(t('home.greeting', { name: '' }).split('{name}')[0], '').replace('!', '') })}
            </Text>
            <Text style={styles.welcomeText}>
              {t('home.subtitle')}
            </Text>
          </Card.Content>
        </Card>

        {/* Loading State */}
        {isLoading && !featuredProducts?.length && !popularProducts?.length && (
          <View style={styles.loadingContainer}>
            <Card style={styles.loadingCard}>
              <Card.Content style={styles.loadingContent}>
                <Text style={styles.loadingText}>{t('home.loadingProducts')}</Text>
                <Text style={styles.loadingSubtext}>{t('common.pleaseWait')}</Text>
              </Card.Content>
            </Card>
          </View>
        )}

        {/* Featured Products */}
        {featuredProducts && featuredProducts.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {t('home.featuredProducts')}
            </Text>
            <FlatList
              data={featuredProducts.slice(0, 3)}
              renderItem={renderPopularProduct}
              keyExtractor={item => `featured-${item.id}`}
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.featuredList}
            />
          </View>
        )}

        {/* Categories Grid */}
        {mainCategories?.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>
              {t('home.categories')}
            </Text>
            <FlatList
              data={mainCategories.slice(0, 6)}
              renderItem={renderCategoryItem}
              keyExtractor={item => item.id}
              numColumns={2}
              scrollEnabled={false}
              contentContainerStyle={styles.categoriesGrid}
              columnWrapperStyle={styles.categoryRow}
            />
            {mainCategories?.length > 6 && (
              <Button
                mode="outlined"
                onPress={() => {/* TODO to all categories */}}
                style={styles.viewAllButton}
              >
                {t('home.viewAllCategories')}
              </Button>
            )}
          </View>
        )}

        {/* Popular Products */}
        {popularProducts?.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>
                {t('home.popularProducts')}
              </Text>
              <Button
                mode="text"
                onPress={() => {/* TODO to popular products */}}
                compact
              >
                {t('common.viewAll')}
              </Button>
            </View>
            <FlatList
              data={popularProducts.slice(0, 4)}
              renderItem={renderPopularProduct}
              keyExtractor={item => `popular-${item.id}`}
              numColumns={2}
              scrollEnabled={false}
              contentContainerStyle={styles.productsGrid}
              columnWrapperStyle={styles.productRow}
            />
          </View>
        )}

        {/* New Arrivals */}
        {newArrivals?.length > 0 && (
          <View style={styles.section}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>
                {t('home.newProducts')}
              </Text>
              <Button
                mode="text"
                onPress={() => {/* TODO to new arrivals */}}
                compact
              >
                {t('common.viewAll')}
              </Button>
            </View>
            <FlatList
              data={newArrivals.slice(0, 4)}
              renderItem={renderPopularProduct}
              keyExtractor={item => `new-${item.id}`}
              numColumns={2}
              scrollEnabled={false}
              contentContainerStyle={styles.productsGrid}
              columnWrapperStyle={styles.productRow}
            />
          </View>
        )}

        {/* Error State */}
        {error && (
          <Card style={styles.errorCard}>
            <Card.Content style={styles.errorContent}>
              <Text style={styles.errorText}>
                {error}
              </Text>
              <Button
                mode="contained"
                onPress={handleRefresh}
                style={styles.retryButton}
              >
                {t('common.retry')}
              </Button>
            </Card.Content>
          </Card>
        )}

        {/* Empty State - When no products are available */}
        {!isLoading && !error &&
         (featuredProducts?.length ?? 0) === 0 &&
         (popularProducts?.length ?? 0) === 0 &&
         (newArrivals?.length ?? 0) === 0 && (
          <View style={styles.emptyStateContainer}>
            <Card style={styles.emptyStateCard}>
              <Card.Content style={styles.emptyStateContent}>
                <Text style={styles.emptyStateIcon}></Text>
                <Text style={styles.emptyStateTitle}>
                  {t('home.noProducts')}
                </Text>
                <Text style={styles.emptyStateText}>
                  {t('home.noProductsMessage')}
                </Text>
                <Button
                  mode="contained"
                  onPress={handleRefresh}
                  style={styles.emptyStateButton}
                >
                  {t('common.reload')}
                </Button>
              </Card.Content>
            </Card>
          </View>
        )}

    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.background,
  },
  header: {
    backgroundColor: colors.primary,
  },
  content: {
    padding: spacing.medium,
  },
  welcomeCard: {
    margin: spacing.medium,
    marginBottom: spacing.large,
  },
  welcomeTitle: {
    fontSize: typography.sizes.large,
    fontWeight: typography.weights.bold,
  },
  welcomeText: {
    fontSize: typography.sizes.medium,
    marginTop: spacing.small,
    opacity: 0.8,
  },
  section: {
    marginBottom: spacing.large,
  },
  sectionTitle: {
    fontWeight: typography.weights.bold,
    color: colors.text,
    marginHorizontal: spacing.medium,
    marginBottom: spacing.medium,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginHorizontal: spacing.medium,
    marginBottom: spacing.medium,
  },
  categoriesGrid: {
    paddingHorizontal: spacing.medium,
  },
  categoryRow: {
    justifyContent: 'space-between',
  },
  productsGrid: {
    paddingHorizontal: spacing.medium,
  },
  productRow: {
    justifyContent: 'space-between',
  },
  viewAllButton: {
    marginTop: spacing.medium,
  },
  errorCard: {
    margin: spacing.medium,
    padding: spacing.large,
    backgroundColor: colors.error,
    alignItems: 'center',
  },
  errorText: {
    color: colors.onError,
    textAlign: 'center',
    marginBottom: spacing.medium,
  },
  retryButton: {
    backgroundColor: colors.onError,
  },
  featuredList: {
    paddingHorizontal: spacing.medium,
  },
  categoryCard: {
    flex: 1,
    margin: spacing.small,
    maxWidth: '48%',
  },
  categoryName: {
    fontSize: typography.sizes.medium,
    fontWeight: typography.weights.semibold,
    marginBottom: spacing.small,
  },
  categoryCount: {
    fontSize: typography.sizes.small,
    color: colors.outline,
  },
  productCard: {
    flex: 1,
    margin: spacing.small,
    maxWidth: '48%',
  },
  productName: {
    fontSize: typography.sizes.medium,
    fontWeight: typography.weights.medium,
    marginBottom: spacing.small,
  },
  productPrice: {
    fontSize: typography.sizes.large,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
  },
  // Loading state styles
  loadingContainer: {
    marginHorizontal: spacing.medium,
    marginVertical: spacing.large,
  },
  loadingCard: {
    padding: spacing.large,
  },
  loadingContent: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  loadingText: {
    fontSize: typography.sizes.large,
    fontWeight: typography.weights.semibold,
    color: colors.text,
    marginTop: spacing.medium,
    textAlign: 'center',
  },
  loadingSubtext: {
    fontSize: typography.sizes.medium,
    color: colors.outline,
    marginTop: spacing.small,
    textAlign: 'center',
  },
  // Empty state styles
  emptyStateContainer: {
    flex: 1,
    marginHorizontal: spacing.medium,
    marginVertical: spacing.xl,
  },
  emptyStateCard: {
    padding: spacing.large,
  },
  emptyStateContent: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xl,
  },
  emptyStateIcon: {
    fontSize: 64,
    marginBottom: spacing.large,
  },
  emptyStateTitle: {
    fontSize: typography.sizes.xl,
    fontWeight: typography.weights.bold,
    color: colors.text,
    marginBottom: spacing.medium,
    textAlign: 'center',
  },
  emptyStateText: {
    fontSize: typography.sizes.medium,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.large,
    paddingHorizontal: spacing.medium,
  },
  emptyStateButton: {
    marginTop: spacing.medium,
    minWidth: 120,
  },
  // Error state styles
  errorContent: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.large,
  },
});
