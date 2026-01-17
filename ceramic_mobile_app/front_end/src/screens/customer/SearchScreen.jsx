import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ScrollView,
  Modal,
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
  Divider,
  Portal,
  RadioButton,
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
import { productService } from '../../services/productService.js';
import { colors, spacing, typography } from '../../constants/theme.js';
import { useTranslation } from '@i18n';

// Simple ProductCard component since the imported one doesn't exist
const ProductCard = ({ product, onPress, onFavoritePress, isFavorite }) => {
  const formatPrice = (price) => {
    const numPrice = typeof price === 'string' ? parseFloat(price) : price;
    return numPrice && !isNaN(numPrice) ? numPrice.toFixed(2) : '0.00';
  };

  return (
  <Card style={styles.productCard} onPress={() => onPress(product)} testID={`search-product-card-${product.id}`}>
    <Card.Content>
      <Text style={styles.productName}>{product.name}</Text>
      <Text style={styles.productPrice}>${formatPrice(product.price)}</Text>
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
};

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
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [showSuggestionDropdown, setShowSuggestionDropdown] = useState(false);
  const debounceTimerRef = useRef(null);

  // Filter state
  const [showFilterModal, setShowFilterModal] = useState(false);
  const [filterOptions, setFilterOptions] = useState({
    categories: [],
    priceRanges: [],
    sortOptions: [],
  });
  const [selectedFilters, setSelectedFilters] = useState({
    categoryId: '',
    priceRange: '',
    sortOption: 'newest',
  });
  const [activeFiltersCount, setActiveFiltersCount] = useState(0);

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

      // Load filter options
      loadFilterOptions();
    }, [dispatch, categories.length, popularProducts.length])
  );

  // Load filter options from service
  const loadFilterOptions = useCallback(async () => {
    try {
      const options = await productService.getFilterOptions();
      setFilterOptions(options);
    } catch (error) {
      // Use default options on error
    }
  }, []);

  // Fetch search suggestions with debounce
  const fetchSuggestions = useCallback(async (query) => {
    if (!query || query.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestionDropdown(false);
      return;
    }

    setLoadingSuggestions(true);
    try {
      const results = await productService.getSearchSuggestions(query, 8);
      setSuggestions(results);
      setShowSuggestionDropdown(results.length > 0);
    } catch (error) {
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  }, []);

  // Handle text change with debounced suggestions
  const handleSearchTextChange = useCallback((text) => {
    setLocalSearchQuery(text);

    // Clear previous timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // If text is cleared, reset search state immediately
    if (!text.trim()) {
      setSuggestions([]);
      setShowSuggestionDropdown(false);
      setShowSuggestions(true);
      dispatch(clearProducts());
      dispatch(setSearchQuery(''));
      return;
    }

    // Set new debounced call for suggestions
    debounceTimerRef.current = setTimeout(() => {
      fetchSuggestions(text);
    }, 300); // 300ms debounce
  }, [fetchSuggestions, dispatch]);

  // Handle suggestion tap
  const handleSuggestionTap = useCallback((suggestion) => {
    const query = typeof suggestion === 'string' ? suggestion : suggestion.name || suggestion.query;
    setLocalSearchQuery(query);
    setShowSuggestionDropdown(false);
    setSuggestions([]);
    handleSearch(query);
  }, []);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const handleSearch = useCallback(
    (query, filters = selectedFilters) => {
      if (query.trim()) {
        setLocalSearchQuery(query);
        dispatch(setSearchQuery(query));
        dispatch(clearProducts());

        // Build params object for the Redux thunk
        // The thunk expects { query, params } structure
        const params = { page: 1 };

        if (filters.categoryId) {
          // Convert string to number for API
          params.categoryId = parseInt(filters.categoryId, 10);
        }

        if (filters.priceRange) {
          const range = filterOptions.priceRanges.find(r => r.id === filters.priceRange);
          if (range) {
            params.minPrice = range.min;
            if (range.max) params.maxPrice = range.max;
          }
        }

        if (filters.sortOption) {
          const sort = filterOptions.sortOptions.find(s => s.id === filters.sortOption);
          if (sort) {
            params.sortBy = sort.sortBy;
            params.sortOrder = sort.sortOrder;
          }
        }

        // Dispatch with correct structure: { query, params }
        dispatch(searchProducts({ query, params }));
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
    [dispatch, selectedFilters, filterOptions]
  );

  // Filter handlers
  const updateActiveFiltersCount = useCallback((filters) => {
    let count = 0;
    if (filters.categoryId) count++;
    if (filters.priceRange) count++;
    if (filters.sortOption && filters.sortOption !== 'newest') count++;
    setActiveFiltersCount(count);
  }, []);

  const handleFilterChange = useCallback((filterType, value) => {
    setSelectedFilters(prev => {
      const newFilters = { ...prev, [filterType]: value };
      updateActiveFiltersCount(newFilters);
      return newFilters;
    });
  }, [updateActiveFiltersCount]);

  const applyFilters = useCallback(() => {
    setShowFilterModal(false);
    if (localSearchQuery.trim()) {
      handleSearch(localSearchQuery, selectedFilters);
    }
  }, [localSearchQuery, selectedFilters, handleSearch]);

  const clearFilters = useCallback(() => {
    const defaultFilters = {
      categoryId: '',
      priceRange: '',
      sortOption: 'newest',
    };
    setSelectedFilters(defaultFilters);
    setActiveFiltersCount(0);
  }, []);

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
      // Build params with current filters and next page
      const params = { page: currentPage + 1 };

      if (selectedFilters.categoryId) {
        // Convert string to number for API
        params.categoryId = parseInt(selectedFilters.categoryId, 10);
      }

      if (selectedFilters.priceRange) {
        const range = filterOptions.priceRanges.find(r => r.id === selectedFilters.priceRange);
        if (range) {
          params.minPrice = range.min;
          if (range.max) params.maxPrice = range.max;
        }
      }

      if (selectedFilters.sortOption) {
        const sort = filterOptions.sortOptions.find(s => s.id === selectedFilters.sortOption);
        if (sort) {
          params.sortBy = sort.sortBy;
          params.sortOrder = sort.sortOrder;
        }
      }

      dispatch(searchProducts({ query: searchQuery, params }));
    }
  }, [hasMore, isLoadingMore, searchQuery, currentPage, dispatch, selectedFilters, filterOptions]);

  const handleRefresh = useCallback(async () => {
    if (searchQuery) {
      setIsRefreshing(true);
      dispatch(clearProducts());

      // Build params with current filters
      const params = { page: 1 };

      if (selectedFilters.categoryId) {
        // Convert string to number for API
        params.categoryId = parseInt(selectedFilters.categoryId, 10);
      }

      if (selectedFilters.priceRange) {
        const range = filterOptions.priceRanges.find(r => r.id === selectedFilters.priceRange);
        if (range) {
          params.minPrice = range.min;
          if (range.max) params.maxPrice = range.max;
        }
      }

      if (selectedFilters.sortOption) {
        const sort = filterOptions.sortOptions.find(s => s.id === selectedFilters.sortOption);
        if (sort) {
          params.sortBy = sort.sortBy;
          params.sortOrder = sort.sortOrder;
        }
      }

      await dispatch(searchProducts({ query: searchQuery, params }));
      setIsRefreshing(false);
    }
  }, [searchQuery, dispatch, selectedFilters, filterOptions]);

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
    <SafeAreaView style={styles.container} testID="search-screen">
      <Appbar.Header style={styles.header}>
        <Appbar.BackAction onPress={() => navigation.goBack()} testID="search-back-button" />
        <Appbar.Content title={t('search.title')} />
      </Appbar.Header>

      {/* Search Bar with Filter Button */}
      <View style={styles.searchContainer}>
        <View style={styles.searchRow}>
          <Searchbar
            placeholder={t('search.placeholder')}
            value={localSearchQuery}
            onChangeText={handleSearchTextChange}
            onSubmitEditing={() => handleSearch(localSearchQuery)}
            onClearIconPress={() => {
              setLocalSearchQuery('');
              handleSearch('');
              setShowSuggestions(true);
            }}
            style={styles.searchBar}
            testID="search-input"
          />
          <TouchableOpacity
            style={styles.filterButton}
            onPress={() => setShowFilterModal(true)}
            testID="filter-button"
          >
            <IconButton
              icon="filter-variant"
              size={24}
              iconColor={activeFiltersCount > 0 ? colors.primary : colors.onSurface}
            />
            {activeFiltersCount > 0 && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>{activeFiltersCount}</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </View>

      {/* Filter Modal */}
      <Modal
        visible={showFilterModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowFilterModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Filters</Text>
              <IconButton
                icon="close"
                size={24}
                onPress={() => setShowFilterModal(false)}
              />
            </View>

            <ScrollView style={styles.modalBody}>
              {/* Sort Options */}
              <View style={styles.filterSection}>
                <Text style={styles.filterSectionTitle}>Sort By</Text>
                <RadioButton.Group
                  onValueChange={(value) => handleFilterChange('sortOption', value)}
                  value={selectedFilters.sortOption}
                >
                  {filterOptions.sortOptions.map((option) => (
                    <TouchableOpacity
                      key={option.id}
                      style={styles.radioItem}
                      onPress={() => handleFilterChange('sortOption', option.id)}
                    >
                      <RadioButton value={option.id} />
                      <Text style={styles.radioLabel}>{option.label}</Text>
                    </TouchableOpacity>
                  ))}
                </RadioButton.Group>
              </View>

              <Divider style={styles.filterDivider} />

              {/* Price Range */}
              <View style={styles.filterSection}>
                <Text style={styles.filterSectionTitle}>Price Range</Text>
                <RadioButton.Group
                  onValueChange={(value) => handleFilterChange('priceRange', value)}
                  value={selectedFilters.priceRange}
                >
                  <TouchableOpacity
                    style={styles.radioItem}
                    onPress={() => handleFilterChange('priceRange', '')}
                  >
                    <RadioButton value="" />
                    <Text style={styles.radioLabel}>All Prices</Text>
                  </TouchableOpacity>
                  {filterOptions.priceRanges.map((range) => (
                    <TouchableOpacity
                      key={range.id}
                      style={styles.radioItem}
                      onPress={() => handleFilterChange('priceRange', range.id)}
                    >
                      <RadioButton value={range.id} />
                      <Text style={styles.radioLabel}>{range.label}</Text>
                    </TouchableOpacity>
                  ))}
                </RadioButton.Group>
              </View>

              <Divider style={styles.filterDivider} />

              {/* Categories */}
              {filterOptions.categories.length > 0 && (
                <View style={styles.filterSection}>
                  <Text style={styles.filterSectionTitle}>Category</Text>
                  <RadioButton.Group
                    onValueChange={(value) => handleFilterChange('categoryId', value)}
                    value={selectedFilters.categoryId?.toString() || ''}
                  >
                    <TouchableOpacity
                      style={styles.radioItem}
                      onPress={() => handleFilterChange('categoryId', '')}
                    >
                      <RadioButton value="" />
                      <Text style={styles.radioLabel}>All Categories</Text>
                    </TouchableOpacity>
                    {filterOptions.categories.map((category) => (
                      <TouchableOpacity
                        key={category.id}
                        style={styles.radioItem}
                        onPress={() => handleFilterChange('categoryId', category.id.toString())}
                      >
                        <RadioButton value={category.id.toString()} />
                        <Text style={styles.radioLabel}>{category.name}</Text>
                      </TouchableOpacity>
                    ))}
                  </RadioButton.Group>
                </View>
              )}
            </ScrollView>

            <View style={styles.modalFooter}>
              <Button
                mode="outlined"
                onPress={clearFilters}
                style={styles.clearButton}
              >
                Clear
              </Button>
              <Button
                mode="contained"
                onPress={applyFilters}
                style={styles.applyButton}
              >
                Apply
              </Button>
            </View>
          </View>
        </View>
      </Modal>

      {/* Autocomplete Suggestions - Rendered outside searchContainer */}
      {showSuggestionDropdown && (
        <View style={styles.suggestionsDropdown}>
          {loadingSuggestions ? (
            <View style={styles.suggestionLoading}>
              <ActivityIndicator size="small" color={colors.primary} />
              <Text style={styles.suggestionLoadingText}>{t('search.loadingSuggestions') || 'Loading suggestions...'}</Text>
            </View>
          ) : (
            suggestions.map((suggestion, index) => {
              const suggestionText = typeof suggestion === 'string'
                ? suggestion
                : suggestion.name || suggestion.query || suggestion.title;
              return (
                <React.Fragment key={`suggestion-${index}`}>
                  <TouchableOpacity
                    style={styles.suggestionItem}
                    onPress={() => handleSuggestionTap(suggestion)}
                    testID={`search-suggestion-${index}`}
                  >
                    <IconButton icon="magnify" size={16} style={styles.suggestionIcon} />
                    <Text style={styles.suggestionText} numberOfLines={1}>
                      {suggestionText}
                    </Text>
                  </TouchableOpacity>
                  {index < suggestions.length - 1 && <Divider />}
                </React.Fragment>
              );
            })
          )}
        </View>
      )}

      {!showSuggestionDropdown && renderContent()}
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
    flex: 1,
    elevation: 0,
    backgroundColor: colors.surfaceVariant,
  },
  suggestionsDropdown: {
    backgroundColor: colors.surface,
    marginHorizontal: spacing.md,
    borderRadius: 8,
    maxHeight: 300,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
  },
  suggestionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  suggestionIcon: {
    margin: 0,
    marginRight: spacing.xs,
  },
  suggestionText: {
    flex: 1,
    fontSize: typography.sizes.md,
    color: colors.onSurface,
  },
  suggestionLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.md,
  },
  suggestionLoadingText: {
    marginLeft: spacing.sm,
    fontSize: typography.sizes.sm,
    color: colors.outline,
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
  // Filter styles
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  filterButton: {
    position: 'relative',
    marginLeft: spacing.xs,
  },
  filterBadge: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: colors.primary,
    borderRadius: 10,
    minWidth: 18,
    height: 18,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filterBadgeText: {
    color: colors.onPrimary || '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: colors.outline + '30',
  },
  modalTitle: {
    fontSize: typography.sizes.lg,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
  },
  modalBody: {
    padding: spacing.md,
  },
  modalFooter: {
    flexDirection: 'row',
    padding: spacing.md,
    borderTopWidth: 1,
    borderTopColor: colors.outline + '30',
    gap: spacing.md,
  },
  clearButton: {
    flex: 1,
  },
  applyButton: {
    flex: 1,
  },
  filterSection: {
    marginBottom: spacing.md,
  },
  filterSectionTitle: {
    fontSize: typography.sizes.md,
    fontWeight: typography.weights.semibold,
    color: colors.onSurface,
    marginBottom: spacing.sm,
  },
  filterDivider: {
    marginVertical: spacing.md,
  },
  radioItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  radioLabel: {
    fontSize: typography.sizes.md,
    color: colors.onSurface,
    marginLeft: spacing.xs,
  },
});