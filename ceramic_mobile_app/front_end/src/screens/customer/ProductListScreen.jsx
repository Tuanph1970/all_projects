import React, { useEffect, useState, useCallback } from 'react';
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

export const ProductListScreen = () => {
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

  // Get route parameters
  const categoryId = route.params?.categoryId;
  const categoryName = route.params?.categoryName;
  const initialSearchQuery = route.params?.searchQuery;

  useFocusEffect(
    useCallback(() => {
      // Clear products when screen focuses
      dispatch(clearProducts());
      
      // Load categories if not loaded
      if (categories.length === 0) {
        dispatch(fetchCategories());
      }

      // Set initial search query if provided
      if (initialSearchQuery && initialSearchQuery !== localSearchQuery) {
        setLocalSearchQuery(initialSearchQuery);
        dispatch(setSearchQuery(initialSearchQuery));
      }

      // Find selected category
      if (categoryId) {
        const category = categories.find(c => c.id === categoryId);
        if (category) {
          setSelectedCategory(category);
        }
      }

      // Load initial data
      loadProducts(1);
    }, [categoryId, initialSearchQuery, categories])
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
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} />
        <Appbar.Content title={getScreenTitle()} />
        <Menu
          visible={sortMenuVisible}
          onDismiss={() => setSortMenuVisible(false)}
          anchor={
            <IconButton
              icon="sort"
              onPress={() => setSortMenuVisible(true)}
            />
          }
        >
          <Menu.Item
            onPress={() => handleSort('newest', 'desc')}
            title="Newest"
            leadingIcon="clock-outline"
          />
          <Menu.Item
            onPress={() => handleSort('popular', 'desc')}
            title="Popular"
            leadingIcon="trending-up"
          />
          <Menu.Item
            onPress={() => handleSort('price', 'asc')}
            title="Price: Low to High"
            leadingIcon="arrow-up"
          />
          <Menu.Item
            onPress={() => handleSort('price', 'desc')}
            title="Price: High to Low"
            leadingIcon="arrow-down"
          />
          <Menu.Item
            onPress={() => handleSort('rating', 'desc')}
            title="Highest Rated"
            leadingIcon="star"
          />
        </Menu>
        <IconButton
          icon={viewType === 'grid' ? 'view-list' : 'view-grid'}
          onPress={handleViewToggle}
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
        />
      </View>

      {/* Category Filter Chips */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.categoryChips}
      >
        <Chip
          selected={!selectedCategory}
          onPress={() => handleCategorySelect(null)}
          style={styles.categoryChip}
          textStyle={styles.chipText}
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
          >
            {category.name}
          </Chip>
        ))}
      </ScrollView>

      {/* Sort & Filter Info */}
      <View style={styles.filtersInfo}>
        <Text style={styles.resultsCount}>
          {products.length} products
        </Text>
        <Text style={styles.sortInfo}>
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
        contentContainerStyle={styles.listContainer}
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