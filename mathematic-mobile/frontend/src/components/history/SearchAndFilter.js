import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Modal,
  ScrollView,
  Animated,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const { width: screenWidth } = Dimensions.get('window');

const CATEGORIES = [
  { id: 'all', name: 'All Categories', icon: 'apps' },
  { id: 'algebra', name: 'Algebra', icon: 'calculator' },
  { id: 'geometry', name: 'Geometry', icon: 'shapes' },
  { id: 'calculus', name: 'Calculus', icon: 'trending-up' },
  { id: 'statistics', name: 'Statistics', icon: 'bar-chart' },
  { id: 'trigonometry', name: 'Trigonometry', icon: 'radio-button-on' },
];

const STATUS_OPTIONS = [
  { id: 'all', name: 'All Status', icon: 'list', color: null },
  { id: 'solved', name: 'Solved', icon: 'checkmark-circle', color: 'success' },
  { id: 'pending', name: 'Pending', icon: 'time', color: 'warning' },
  { id: 'failed', name: 'Failed', icon: 'close-circle', color: 'error' },
];

const SORT_OPTIONS = [
  { id: 'newest', name: 'Newest First', icon: 'chevron-down' },
  { id: 'oldest', name: 'Oldest First', icon: 'chevron-up' },
  { id: 'category', name: 'By Category', icon: 'folder' },
  { id: 'confidence', name: 'By Confidence', icon: 'star' },
];

const SearchAndFilter = ({
  searchQuery = '',
  selectedCategory = 'all',
  selectedStatus = 'all',
  sortBy = 'newest',
  onSearchChange,
  onCategoryChange,
  onStatusChange,
  onSortChange,
  onClearFilters,
  problemCount = 0,
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [showFilters, setShowFilters] = useState(false);
  const [activeFilterCount, setActiveFilterCount] = useState(0);
  const searchInputRef = useRef(null);
  const filterHeight = useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    let count = 0;
    if (selectedCategory !== 'all') count++;
    if (selectedStatus !== 'all') count++;
    if (sortBy !== 'newest') count++;
    setActiveFilterCount(count);
  }, [selectedCategory, selectedStatus, sortBy]);

  const toggleFilters = () => {
    const toValue = showFilters ? 0 : 1;
    setShowFilters(!showFilters);
    
    Animated.spring(filterHeight, {
      toValue,
      useNativeDriver: false,
      tension: 100,
      friction: 8,
    }).start();
  };

  const clearAllFilters = () => {
    onSearchChange?.('');
    onCategoryChange?.('all');
    onStatusChange?.('all');
    onSortChange?.('newest');
    onClearFilters?.();
    searchInputRef.current?.clear();
  };

  const getStatusColor = (colorType) => {
    switch (colorType) {
      case 'success':
        return colors.success;
      case 'warning':
        return colors.warning;
      case 'error':
        return colors.error;
      default:
        return colors.primary;
    }
  };

  const renderSearchBar = () => (
    <View style={styles.searchContainer}>
      <View style={styles.searchInputContainer}>
        <Ionicons name="search" size={20} color={colors.textSecondary} />
        <TextInput
          ref={searchInputRef}
          style={styles.searchInput}
          placeholder="Search problems..."
          placeholderTextColor={colors.textSecondary}
          value={searchQuery}
          onChangeText={onSearchChange}
          returnKeyType="search"
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity
            onPress={() => {
              onSearchChange?.('');
              searchInputRef.current?.clear();
            }}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="close" size={20} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>
      
      <TouchableOpacity
        style={[
          styles.filterToggleButton,
          showFilters && styles.filterToggleButtonActive,
        ]}
        onPress={toggleFilters}
        activeOpacity={0.7}
      >
        <Ionicons
          name="options"
          size={20}
          color={showFilters ? colors.onPrimary : colors.text}
        />
        {activeFilterCount > 0 && (
          <View style={styles.filterBadge}>
            <Text style={styles.filterBadgeText}>{activeFilterCount}</Text>
          </View>
        )}
      </TouchableOpacity>
    </View>
  );

  const renderFilterSection = (title, options, selectedValue, onSelect, renderItem) => (
    <View style={styles.filterSection}>
      <Text style={styles.filterSectionTitle}>{title}</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filterOptionsContainer}
      >
        {options.map((option) =>
          renderItem ? renderItem(option, selectedValue, onSelect) : (
            <TouchableOpacity
              key={option.id}
              style={[
                styles.filterOption,
                selectedValue === option.id && styles.filterOptionSelected,
              ]}
              onPress={() => onSelect?.(option.id)}
              activeOpacity={0.7}
            >
              <Ionicons
                name={option.icon}
                size={16}
                color={
                  selectedValue === option.id
                    ? colors.onPrimary
                    : colors.textSecondary
                }
              />
              <Text
                style={[
                  styles.filterOptionText,
                  selectedValue === option.id && styles.filterOptionTextSelected,
                ]}
              >
                {option.name}
              </Text>
            </TouchableOpacity>
          )
        )}
      </ScrollView>
    </View>
  );

  const renderStatusOption = (option, selectedValue, onSelect) => (
    <TouchableOpacity
      key={option.id}
      style={[
        styles.filterOption,
        selectedValue === option.id && styles.filterOptionSelected,
        selectedValue === option.id && option.color && {
          backgroundColor: getStatusColor(option.color),
        },
      ]}
      onPress={() => onSelect?.(option.id)}
      activeOpacity={0.7}
    >
      <Ionicons
        name={option.icon}
        size={16}
        color={
          selectedValue === option.id
            ? colors.onPrimary
            : option.color
            ? getStatusColor(option.color)
            : colors.textSecondary
        }
      />
      <Text
        style={[
          styles.filterOptionText,
          selectedValue === option.id && styles.filterOptionTextSelected,
        ]}
      >
        {option.name}
      </Text>
    </TouchableOpacity>
  );

  const renderFilters = () => (
    <Animated.View
      style={[
        styles.filtersContainer,
        {
          maxHeight: filterHeight.interpolate({
            inputRange: [0, 1],
            outputRange: [0, 300],
          }),
          opacity: filterHeight,
        },
      ]}
    >
      <ScrollView
        style={styles.filtersScrollView}
        showsVerticalScrollIndicator={false}
      >
        {renderFilterSection(
          'Category',
          CATEGORIES,
          selectedCategory,
          onCategoryChange
        )}
        
        {renderFilterSection(
          'Status',
          STATUS_OPTIONS,
          selectedStatus,
          onStatusChange,
          renderStatusOption
        )}
        
        {renderFilterSection(
          'Sort By',
          SORT_OPTIONS,
          sortBy,
          onSortChange
        )}
        
        {activeFilterCount > 0 && (
          <View style={styles.filterActions}>
            <TouchableOpacity
              style={styles.clearFiltersButton}
              onPress={clearAllFilters}
              activeOpacity={0.7}
            >
              <Ionicons name="refresh" size={16} color={colors.text} />
              <Text style={styles.clearFiltersText}>Clear All</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>
    </Animated.View>
  );

  const renderResultsInfo = () => (
    <View style={styles.resultsInfo}>
      <Text style={styles.resultsText}>
        {problemCount} problem{problemCount !== 1 ? 's' : ''}
        {activeFilterCount > 0 && ' (filtered)'}
      </Text>
    </View>
  );

  return (
    <View style={styles.container}>
      {renderSearchBar()}
      {renderFilters()}
      {renderResultsInfo()}
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      backgroundColor: colors.surface,
      borderBottomWidth: 1,
      borderBottomColor: colors.outline,
    },
    searchContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingHorizontal: 16,
      paddingVertical: 12,
    },
    searchInputContainer: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.surfaceVariant,
      borderRadius: 8,
      paddingHorizontal: 12,
      paddingVertical: 8,
      marginRight: 12,
    },
    searchInput: {
      flex: 1,
      fontSize: 16,
      color: colors.text,
      marginLeft: 8,
      marginRight: 8,
    },
    filterToggleButton: {
      width: 40,
      height: 40,
      borderRadius: 8,
      backgroundColor: colors.surfaceVariant,
      justifyContent: 'center',
      alignItems: 'center',
      position: 'relative',
    },
    filterToggleButtonActive: {
      backgroundColor: colors.primary,
    },
    filterBadge: {
      position: 'absolute',
      top: -4,
      right: -4,
      width: 16,
      height: 16,
      borderRadius: 8,
      backgroundColor: colors.error,
      justifyContent: 'center',
      alignItems: 'center',
    },
    filterBadgeText: {
      fontSize: 10,
      fontWeight: 'bold',
      color: colors.onError,
    },
    filtersContainer: {
      overflow: 'hidden',
      backgroundColor: colors.surfaceVariant,
    },
    filtersScrollView: {
      paddingHorizontal: 16,
      paddingVertical: 12,
    },
    filterSection: {
      marginBottom: 16,
    },
    filterSectionTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 8,
    },
    filterOptionsContainer: {
      paddingRight: 16,
    },
    filterOption: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.surface,
      paddingHorizontal: 12,
      paddingVertical: 8,
      borderRadius: 20,
      marginRight: 8,
      borderWidth: 1,
      borderColor: colors.outline,
    },
    filterOptionSelected: {
      backgroundColor: colors.primary,
      borderColor: colors.primary,
    },
    filterOptionText: {
      fontSize: 14,
      color: colors.text,
      marginLeft: 4,
    },
    filterOptionTextSelected: {
      color: colors.onPrimary,
      fontWeight: '600',
    },
    filterActions: {
      alignItems: 'center',
      paddingTop: 8,
    },
    clearFiltersButton: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.surface,
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: colors.outline,
    },
    clearFiltersText: {
      fontSize: 14,
      color: colors.text,
      marginLeft: 4,
    },
    resultsInfo: {
      paddingHorizontal: 16,
      paddingVertical: 8,
      backgroundColor: colors.surfaceVariant,
    },
    resultsText: {
      fontSize: 12,
      color: colors.textSecondary,
      textAlign: 'center',
    },
  });

export default SearchAndFilter;