import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import {
  View,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  FlatList,
  RefreshControl,
} from 'react-native';
import {
  Appbar,
  Searchbar,
  Menu,
  IconButton,
  FAB,
  Chip,
  Text,
  Button,
  ActivityIndicator,
  Card,
} from 'react-native-paper';
import { useSelector, useDispatch } from 'react-redux';
import { useFocusEffect, useNavigation, useRoute } from '@react-navigation/native';
import {
  fetchProducts,
  fetchProductsByCategory,
  searchProducts,
  fetchCategories,
  toggleFavorite,
  setFilters,
  setSearchQuery,
  setViewType,
  clearProducts,
} from '../../store/slices/productSlice.js';
import { colors, spacing, typography } from '../../constants/theme.js';

const ProductCard = ({ product, onPress, onFavoritePress, isFavorite }) => {
  // Format price - handle both number and string values from API
  const formatPrice = (price) => {
    if (price === null || price === undefined) return '0.00';
    const numPrice = typeof price === 'string' ? parseFloat(price) : price;
    return isNaN(numPrice) ? '0.00' : numPrice.toFixed(2);
  };

  return (
    <Card style={styles.productCard} onPress={() => onPress(product)} testID={`product-card-${product.id}`}>
      <Card.Content>
        <Text style={styles.productName} testID={`product-name-${product.id}`}>{product.name}</Text>
        <Text style={styles.productPrice} testID={`product-price-${product.id}`}>${formatPrice(product.price)}</Text>
        {product.category && (
          <Text style={styles.productCategory} testID={`product-category-${product.id}`}>{product.category}</Text>
        )}
      </Card.Content>
      <Card.Actions>
        <IconButton
          icon={isFavorite ? 'heart' : 'heart-outline'}
          iconColor={isFavorite ? colors.error : colors.outline}
          onPress={() => onFavoritePress(product)}
          testID={`product-favorite-${product.id}`}
        />
      </Card.Actions>
    </Card>
  );
};

export const ProductListScreen = () => {
  const insets = useSafeAreaInsets();
  const navigation = useNavigation();
  const route = useRoute();
  const dispatch = useDispatch();
  
  const {
    products = [],
    categories = [],
    mainCategories = [],
    favorites = [],
    filters = {},
    searchQuery = '',
    viewType = 'grid',
    currentPage = 1,
    hasMore = false,
    isLoading = false,
    isLoadingMore = false,
    isRefreshing = false,
    error = null,
  } = useSelector((state) => state.products || {});

  const [localSearchQuery, setLocalSearchQuery] = useState('');
  const [sortMenuVisible, setSortMenuVisible] = useState(false);
  const [filterMenuVisible, setFilterMenuVisible] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [sortBy, setSortBy] = useState('newest');
  const [sortOrder, setSortOrder] = useState('desc');

  // Ref to prevent duplicate loads
  const isInitialLoadDone = useRef(false);
  const categoriesLoadedRef = useRef(false);

  // Get route parameters
  const categoryId = route.params?.categoryId;
  const categoryName = route.params?.categoryName;
  const initialSearchQuery = route.params?.searchQuery;

  // Load categories only once
  useEffect(() => {
    if (!categoriesLoadedRef.current && categories.length === 0) {
      categoriesLoadedRef.current = true;
      dispatch(fetchCategories());
    }
  }, [dispatch, categories.length]);

  useFocusEffect(
    useCallback(() => {
      // Reset on focus
      isInitialLoadDone.current = false;

      // Clear products when screen focuses
      dispatch(clearProducts());

      // Set initial search query if provided
      if (initialSearchQuery && initialSearchQuery !== localSearchQuery) {
        setLocalSearchQuery(initialSearchQuery);
        dispatch(setSearchQuery(initialSearchQuery));
      }

      // Find selected category
      if (categoryId && categories.length > 0) {
        const category = categories.find(c => c.id === categoryId);
        if (category) {
          setSelectedCategory(category);
        }
      }

      // Load initial data only once per focus
      if (!isInitialLoadDone.current) {
        isInitialLoadDone.current = true;
        loadProducts(1);
      }
    }, [categoryId, initialSearchQuery])
  );

  const loadProducts = useCallback(
    async (page = 1) => {
      try {
        const params = {
          page,
          limit: 20,
          sortBy,
          sortOrder,
          ...filters,
        };

        if (searchQuery) {
          await dispatch(searchProducts({ query: searchQuery, params }));
        } else if (categoryId) {
          await dispatch(fetchProductsByCategory({ categoryId, params }));
        } else {
          await dispatch(fetchProducts(params));
        }
      } catch (error) {
        console.error('Failed to load products:', error);
      }
    },
    [dispatch, categoryId, searchQuery, sortBy, sortOrder, filters]
  );

  const handleSearch = useCallback(
    (query) => {
      dispatch(setSearchQuery(query));
      dispatch(clearProducts());
      setSelectedCategory(null);
      
      if (query.trim()) {
        navigation.setParams({ searchQuery: query, categoryId: undefined });
      }
      
      loadProducts(1);
    },
    [dispatch, navigation, loadProducts]
  );

  const handleCategorySelect = useCallback(
    (category) => {
      setSelectedCategory(category);
      dispatch(clearProducts());
      dispatch(setSearchQuery(''));
      setLocalSearchQuery('');
      
      if (category) {
        navigation.setParams({ 
          categoryId: category.id, 
          categoryName: category.name,
          searchQuery: undefined
        });
      } else {
        navigation.setParams({ 
          categoryId: undefined, 
          categoryName: undefined,
          searchQuery: undefined
        });
      }
      
      loadProducts(1);
    },
    [dispatch, navigation, loadProducts]
  );

  const handleSort = useCallback(
    (newSortBy, newSortOrder) => {
      setSortBy(newSortBy);
      setSortOrder(newSortOrder);
      setSortMenuVisible(false);
      dispatch(clearProducts());
      
      // Reload with new sorting
      setTimeout(() => loadProducts(1), 100);
    },
    [dispatch, loadProducts]
  );

  const handleFilter = useCallback(
    (newFilters) => {
      dispatch(setFilters(newFilters));
      dispatch(clearProducts());
      setFilterMenuVisible(false);
      
      // Reload with new filters
      setTimeout(() => loadProducts(1), 100);
    },
    [dispatch, loadProducts]
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
    if (hasMore && !isLoadingMore) {
      loadProducts(currentPage + 1);
    }
  }, [hasMore, isLoadingMore, currentPage, loadProducts]);

  const handleRefresh = useCallback(() => {
    dispatch(clearProducts());
    loadProducts(1);
  }, [dispatch, loadProducts]);

  const handleViewToggle = useCallback(() => {
    const newViewType = viewType === 'grid' ? 'list' : 'grid';
    dispatch(setViewType(newViewType));
  }, [dispatch, viewType]);

  const getScreenTitle = () => {
    if (searchQuery) {
      return `Search results for "${searchQuery}"`;
    }
    if (selectedCategory) {
      return selectedCategory.name;
    }
    return 'All Products';
  };

  const getSortLabel = () => {
    const sortLabels = {
      newest: 'Newest',
      popular: 'Popular',
      price: sortOrder === 'asc' ? 'Price: Low to High' : 'Price: High to Low',
      rating: 'Highest Rated',
    };
    return sortLabels[sortBy] || 'Newest';
  };

  const renderProduct = ({ item }) => (
    <ProductCard
      product={item}
      onPress={handleProductPress}
      onFavoritePress={handleFavoritePress}
      isFavorite={favorites.some(fav => fav.id === item.id)}
    />
  );

  const renderEmpty = () => (
    <View style={styles.emptyContainer}>
      <Text style={styles.emptyTitle}>No products found</Text>
      <Text style={styles.emptySubtitle}>
        {searchQuery
          ? `No products found for "${searchQuery}"`
          : selectedCategory
          ? `No products in "${selectedCategory.name}"`
          : 'No products available'}
      </Text>
      <Button 
        mode="contained" 
        style={styles.emptyButton}
        onPress={() => {
          setLocalSearchQuery('');
          handleSearch('');
          setSelectedCategory(null);
        }}
      >
        Show All Products
      </Button>
    </View>
  );

  const renderFooter = () => {
    if (!isLoadingMore) return null;
    return (
      <View style={styles.footerLoader}>
        <ActivityIndicator size="small" color={colors.primary} />
      </View>
    );
  };

  if (isLoading && products.length === 0) {
    return (
      <SafeAreaView style={styles.container}>
        <Appbar.Header style={styles.header}>
          <Appbar.BackAction onPress={() => navigation.goBack()} />
          <Appbar.Content title={getScreenTitle()} />
        </Appbar.Header>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={styles.loadingText}>Loading products...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} testID="product-list-screen">
      {/* Header */}
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="product-list-back-button" />
        <Appbar.Content title={getScreenTitle()} />
        <Menu
          visible={sortMenuVisible}
          onDismiss={() => setSortMenuVisible(false)}
          anchor={
            <IconButton
              icon="sort"
              onPress={() => setSortMenuVisible(true)}
              testID="product-sort-button"
            />
          }
        >
          <Menu.Item
            onPress={() => handleSort('newest', 'desc')}
            title="Newest"
            leadingIcon="clock-outline"
            testID="sort-newest"
          />
          <Menu.Item
            onPress={() => handleSort('popular', 'desc')}
            title="Popular"
            leadingIcon="trending-up"
            testID="sort-popular"
          />
          <Menu.Item
            onPress={() => handleSort('price', 'asc')}
            title="Price: Low to High"
            leadingIcon="arrow-up"
            testID="sort-price-low-high"
          />
          <Menu.Item
            onPress={() => handleSort('price', 'desc')}
            title="Price: High to Low"
            leadingIcon="arrow-down"
            testID="sort-price-high-low"
          />
          <Menu.Item
            onPress={() => handleSort('rating', 'desc')}
            title="Highest Rated"
            leadingIcon="star"
            testID="sort-rating"
          />
        </Menu>
        <IconButton
          icon={viewType === 'grid' ? 'view-list' : 'view-grid'}
          onPress={handleViewToggle}
          testID="product-view-toggle"
        />
      </Appbar.Header>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <Searchbar
          placeholder="Search products..."
          value={localSearchQuery}
          onChangeText={setLocalSearchQuery}
          onSubmitEditing={() => handleSearch(localSearchQuery)}
          onClearIconPress={() => {
            setLocalSearchQuery('');
            handleSearch('');
          }}
          style={styles.searchBar}
          testID="product-list-search-bar"
        />
      </View>

      {/* Category Filter Chips */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        style={styles.categoryChips}
        testID="category-filter-container"
      >
        <Chip
          selected={!selectedCategory}
          onPress={() => handleCategorySelect(null)}
          style={styles.categoryChip}
          textStyle={styles.chipText}
          testID="category-all"
        >
          All
        </Chip>
        {mainCategories.slice(0, 4).map((category) => (
          <Chip
            key={category.id}
            selected={selectedCategory?.id === category.id}
            onPress={() => handleCategorySelect(category)}
            style={styles.categoryChip}
            textStyle={styles.chipText}
            testID={`category-${category.name.toLowerCase().replace(/\s+/g, '-')}`}
          >
            {category.name}
          </Chip>
        ))}
      </ScrollView>

      {/* Sort & Filter Info */}
      <View style={styles.filtersInfo} testID="filter-info-container">
        <Text style={styles.resultsCount} testID="results-count">
          {products.length} products
        </Text>
        <Text style={styles.sortInfo} testID="sort-info">
          Sorted by: {getSortLabel()}
        </Text>
      </View>

      {/* Product List */}
      <FlatList
        data={products}
        renderItem={renderProduct}
        keyExtractor={(item) => item.id.toString()}
        numColumns={viewType === 'grid' ? 2 : 1}
        key={viewType} // Force re-render when view type changes
        contentContainerStyle={[styles.listContainer, { paddingBottom: Math.max(insets.bottom, 16) }]}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
          />
        }
        onEndReached={handleLoadMore}
        onEndReachedThreshold={0.5}
        ListFooterComponent={renderFooter}
        ListEmptyComponent={!isLoading ? renderEmpty : null}
        showsVerticalScrollIndicator={false}
        testID="product-list"
      />

      {/* Filter FAB - TODO: Implement filter modal */}
      {/* <FAB
        style={styles.filterFab}
        icon="filter"
        onPress={() => setFilterMenuVisible(true)}
        label="Filter"
      /> */}
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
  searchContainer: {
    padding: spacing.md,
    paddingVertical: spacing.sm,
    backgroundColor: colors.surface,
  },
  searchBar: {
    elevation: 0,
    backgroundColor: colors.surfaceVariant,
  },
  categoryChips: {
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
    maxHeight: 50,
  },
  categoryChip: {
    marginRight: spacing.sm,
  },
  chipText: {
    fontSize: typography.sizes.sm,
  },
  filtersContainer: {
    paddingBottom: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline,
  },
  filtersInfo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.sm,
  },
  resultsCount: {
    fontSize: typography.sizes.sm,
    color: colors.onSurface,
    fontWeight: typography.weights.medium,
  },
  sortInfo: {
    fontSize: typography.sizes.sm,
    color: colors.outline,
  },
  listContainer: {
    padding: spacing.md,
    flexGrow: 1,
  },
  productCard: {
    flex: 1,
    margin: spacing.xs,
    maxWidth: '48%', // For grid view
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
  footerLoader: {
    padding: spacing.md,
    alignItems: 'center',
  },
  filterFab: {
    position: 'absolute',
    margin: spacing.md,
    right: 0,
    bottom: 0,
    backgroundColor: colors.primary,
  },
});