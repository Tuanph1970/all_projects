import React, { useState, useCallback, useEffect } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  FlatList,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import {
  Appbar,
  Searchbar,
  Text,
  Chip,
  Card,
  IconButton,
  ActivityIndicator,
  Button,
} from 'react-native-paper';
import { useSelector, useDispatch } from 'react-redux';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import {
  searchProducts,
  fetchCategories,
  fetchPopularProducts,
  toggleFavorite,
  setSearchQuery,
  clearProducts,
} from '../../store/slices/productSlice.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

// Simple ProductCard component since the imported one doesn't exist
const ProductCard = ({ product, onPress, onFavoritePress, isFavorite }) => (
  <Card style={styles.productCard} onPress={() => onPress(product)}>
    <Card.Content>
      <Text style={styles.productName}>{product.name}</Text>
      <Text style={styles.productPrice}>${product.price?.toFixed(2)}</Text>
      {product.category && (
        <Text style={styles.productCategory}>{product.category}</Text>
      )}
    </Card.Content>
    <Card.Actions>
      <IconButton
        icon={isFavorite ? 'heart' : 'heart-outline'}
        iconColor={isFavorite ? colors.error : colors.outline}
        onPress={() => onFavoritePress(product)}
      />
    </Card.Actions>
  </Card>
);

export const SearchScreen = () => {
  const navigation = useNavigation();
  const dispatch = useDispatch();
  const t = useTranslation();
  
  const {
    products = [],
    categories = [],
    mainCategories = [],
    popularProducts = [],
    favorites = [],
    searchQuery = '',
    currentPage = 1,
    hasMore = false,
    isLoading = false,
    isLoadingMore = false,
    error = null,
  } = useSelector((state) => state.products || {});

  const [localSearchQuery, setLocalSearchQuery] = useState('');
  const [searchHistory, setSearchHistory] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useFocusEffect(
    useCallback(() => {
      // Load categories if not loaded
      if (categories.length === 0) {
        dispatch(fetchCategories());
      }
      
      // Load popular products for suggestions
      if (popularProducts.length === 0) {
        dispatch(fetchPopularProducts({ limit: 10 }));
      }
    }, [dispatch, categories.length, popularProducts.length])
  );

  const handleSearch = useCallback(
    (query) => {
      if (query.trim()) {
        setLocalSearchQuery(query);
        dispatch(setSearchQuery(query));
        dispatch(clearProducts());
        dispatch(searchProducts({ query, page: 1 }));
        setShowSuggestions(false);
        
        // Add to search history
        setSearchHistory(prev => {
          const newHistory = [query, ...prev.filter(item => item !== query)].slice(0, 5);
          return newHistory;
        });
      } else {
        setShowSuggestions(true);
        dispatch(clearProducts());
        dispatch(setSearchQuery(''));
      }
    },
    [dispatch]
  );

  const handleCategorySelect = useCallback(
    (category) => {
      setSelectedCategory(category);
      const query = `category:${category.name}`;
      handleSearch(query);
    },
    [handleSearch]
  );

  const handleProductPress = useCallback(
    (product) => {
      navigation.navigate('ProductDetails', { productId: product.id });
    },
    [navigation]
  );

  const handleFavoritePress = useCallback(
    (product) => {
      dispatch(toggleFavorite(product.id));
    },
    [dispatch]
  );

  const handleLoadMore = useCallback(() => {
    if (hasMore && !isLoadingMore && searchQuery) {
      dispatch(searchProducts({ 
        query: searchQuery, 
        page: currentPage + 1 
      }));
    }
  }, [hasMore, isLoadingMore, searchQuery, currentPage, dispatch]);

  const handleRefresh = useCallback(async () => {
    if (searchQuery) {
      setIsRefreshing(true);
      dispatch(clearProducts());
      await dispatch(searchProducts({ query: searchQuery, page: 1 }));
      setIsRefreshing(false);
    }
  }, [searchQuery, dispatch]);

  const handleHistoryItemPress = (historyItem) => {
    setLocalSearchQuery(historyItem);
    handleSearch(historyItem);
  };

  const clearSearchHistory = () => {
    setSearchHistory([]);
  };

  const renderProduct = ({ item }) => (
    <ProductCard
      product={item}
      onPress={handleProductPress}
      onFavoritePress={handleFavoritePress}
      isFavorite={favorites.some(fav => fav.id === item.id)}
    />
  );

  const renderCategory = ({ item }) => (
    <Chip
      mode={selectedCategory?.id === item.id ? 'flat' : 'outlined'}
      selected={selectedCategory?.id === item.id}
      onPress={() => handleCategorySelect(item)}
      style={styles.categoryChip}
    >
      {item.name}
    </Chip>
  );

  const renderHistoryItem = ({ item }) => (
    <TouchableOpacity
      style={styles.historyItem}
      onPress={() => handleHistoryItemPress(item)}
    >
      <IconButton icon="history" size={16} />
      <Text style={styles.historyText}>{item}</Text>
    </TouchableOpacity>
  );

  const renderPopularProduct = ({ item }) => (
    <ProductCard
      product={item}
      onPress={handleProductPress}
      onFavoritePress={handleFavoritePress}
      isFavorite={favorites.some(fav => fav.id === item.id)}
    />
  );

  const renderSearchResults = () => {
    if (!searchQuery) return null;

    if (isLoading && products.length === 0) {
      return (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>{t('search.searching')}</Text>
        </View>
      );
    }

    if (products.length === 0 && !isLoading) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyTitle}>{t('search.noProductsFound')}</Text>
          <Text style={styles.emptySubtitle}>
            {t('search.noProductsFoundFor', { query: searchQuery })}
          </Text>
          <Button
            mode="contained"
            style={styles.emptyButton}
            onPress={() => handleSearch('')}
          >
            {t('search.clearSearch')}
          </Button>
        </View>
      );
    }

    return (
      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={(item) => item.id.toString()}
        numColumns={2}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
          />
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={
          isLoadingMore ? (
            <View style={styles.footerLoader}>
              <ActivityIndicator size="small" color={colors.primary} />
            </View>
          ) : null
        }
        showsVerticalScrollIndicator={false}
      />
    );
  };

  const renderSuggestions = () => (
    <View style={styles.suggestionsContainer}>
      {/* Search History */}
      {searchHistory.length > 0 && (
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t('search.recentSearches')}</Text>
            <Button mode="text" onPress={clearSearchHistory} compact>
              {t('search.clearAll')}
            </Button>
          </View>
          <FlatList
            data={searchHistory}
            renderItem={renderHistoryItem}
            keyExtractor={(item, index) => `history-${index}`}
            showsVerticalScrollIndicator={false}
          />
        </View>
      )}

      {/* Categories */}
      {mainCategories.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('home.categories')}</Text>
          <FlatList
            data={mainCategories.slice(0, 6)}
            renderItem={renderCategory}
            keyExtractor={(item) => item.id.toString()}
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.categoriesList}
          />
        </View>
      )}

      {/* Popular Products */}
      {popularProducts.length > 0 && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t('home.popularProducts')}</Text>
          <FlatList
            data={popularProducts.slice(0, 4)}
            renderItem={renderPopularProduct}
            keyExtractor={(item) => `popular-${item.id}`}
            numColumns={2}
            scrollEnabled={false}
            contentContainerStyle={styles.listContainer}
          />
        </View>
      )}
    </View>
  );

  const renderEmptySearch = () => (
    <View style={styles.emptySearchContainer}>
      <Text style={styles.emptySearchIcon}>🔍</Text>
      <Text style={styles.emptySearchText}>
        {t('search.enterKeyword')}
      </Text>
    </View>
  );

  const renderContent = () => {
    if (searchQuery) {
      return renderSearchResults();
    }
    
    if (showSuggestions) {
      return renderSuggestions();
    }
    
    return renderEmptySearch();
  };

  return (
    <SafeAreaView style={styles.container}>
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={t('search.title')} />
      </Appbar.Header>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Searchbar
          placeholder={t('search.placeholder')}
          value={localSearchQuery}
          onChangeText={setLocalSearchQuery}
          onSubmitEditing={() => handleSearch(localSearchQuery)}
          onClearIconPress={() => {
            setLocalSearchQuery('');
            handleSearch('');
            setShowSuggestions(true);
          }}
          style={styles.searchBar}
        />
      </View>

      {renderContent()}
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
  searchContainer: {
    padding: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
  },
  searchBar: {
    elevation: 0,
    backgroundColor: colors.surfaceVariant,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.lg,
  },
  loadingText: {
    marginTop: spacing.md,
    color: colors.onSurface,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptyTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
    marginBottom: spacing.lg,
  },
  emptyButton: {
    marginTop: spacing.md,
  },
  emptySearchContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  emptySearchIcon: {
    fontSize: 48,
    marginBottom: spacing.lg,
  },
  emptySearchText: {
    fontSize: typography.sizes.md,
    color: colors.outline,
    textAlign: 'center',
  },
  suggestionsContainer: {
    flex: 1,
    padding: spacing.md,
  },
  section: {
    marginBottom: spacing.lg,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.md,
  },
  sectionTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  historyItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.xs,
    backgroundColor: colors.surfaceVariant,
    borderRadius: 8,
  },
  historyText: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    marginLeft: spacing.sm,
  },
  categoriesList: {
    paddingVertical: spacing.sm,
  },
  categoryChip: {
    marginRight: spacing.sm,
    marginBottom: spacing.xs,
  },
  listContainer: {
    paddingBottom: spacing.lg,
  },
  productCard: {
    flex: 1,
    margin: spacing.xs,
    maxWidth: '48%',
  },
  productName: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.medium,
    color: colors.onSurface,
    marginBottom: spacing.xs,
  },
  productPrice: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.primary,
    marginBottom: spacing.xs,
  },
  productCategory: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  footerLoader: {
    padding: spacing.md,
    alignItems: 'center',
  },
});