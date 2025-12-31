import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  SafeAreaView,
  Alert,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { useFocusEffect } from '@react-navigation/native';

import { useTheme } from '../../hooks/useTheme';
import ProblemHistory from '../../components/history/ProblemHistory';
import SearchAndFilter from '../../components/history/SearchAndFilter';
import {
  fetchUserProblems,
  deleteProblem,
  setFilters,
  clearFilters,
  setSearchQuery,
} from '../../store/slices/problemSlice';

const HistoryScreen = ({ navigation }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const dispatch = useDispatch();

  // Redux state
  const {
    problems,
    isLoading,
    error,
    pagination,
    filters,
  } = useSelector((state) => state.problem);

  // Local state for UI
  const [searchQuery, setLocalSearchQuery] = useState(filters.searchQuery || '');
  const [selectedCategory, setSelectedCategory] = useState(filters.category || 'all');
  const [selectedStatus, setSelectedStatus] = useState(filters.status || 'all');
  const [sortBy, setSortBy] = useState('newest');
  const [refreshing, setRefreshing] = useState(false);

  // Load problems on screen focus
  useFocusEffect(
    useCallback(() => {
      loadProblems();
    }, [])
  );

  const loadProblems = async () => {
    try {
      const filterParams = {
        page: 1,
        limit: 20,
        category: selectedCategory !== 'all' ? selectedCategory : undefined,
        status: selectedStatus !== 'all' ? selectedStatus : undefined,
        searchQuery: searchQuery || undefined,
        sortBy,
      };
      
      await dispatch(fetchUserProblems(filterParams)).unwrap();
    } catch (error) {
      console.error('Failed to load problems:', error);
      Alert.alert('Error', 'Failed to load problems. Please try again.');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await loadProblems();
    } finally {
      setRefreshing(false);
    }
  };

  const handleSearchChange = useCallback((query) => {
    setLocalSearchQuery(query);
    dispatch(setSearchQuery(query));
    
    // Debounce search
    const timeoutId = setTimeout(() => {
      loadProblems();
    }, 500);
    
    return () => clearTimeout(timeoutId);
  }, [dispatch, loadProblems]);

  const handleCategoryChange = useCallback((category) => {
    setSelectedCategory(category);
    dispatch(setFilters({ category: category !== 'all' ? category : null }));
    loadProblems();
  }, [dispatch, loadProblems]);

  const handleStatusChange = useCallback((status) => {
    setSelectedStatus(status);
    dispatch(setFilters({ status: status !== 'all' ? status : null }));
    loadProblems();
  }, [dispatch, loadProblems]);

  const handleSortChange = useCallback((sort) => {
    setSortBy(sort);
    loadProblems();
  }, [loadProblems]);

  const handleClearFilters = useCallback(() => {
    setLocalSearchQuery('');
    setSelectedCategory('all');
    setSelectedStatus('all');
    setSortBy('newest');
    dispatch(clearFilters());
    loadProblems();
  }, [dispatch, loadProblems]);

  const handleProblemPress = useCallback((problem) => {
    // Navigate to problem detail screen or solution screen
    if (problem.status === 'solved' && problem.solutionId) {
      navigation.navigate('Solution', { 
        problemId: problem.id,
        solutionId: problem.solutionId 
      });
    } else {
      navigation.navigate('ProblemDetail', { problemId: problem.id });
    }
  }, [navigation]);

  const handleProblemDelete = useCallback((problemId) => {
    Alert.alert(
      'Delete Problem',
      'Are you sure you want to delete this problem? This action cannot be undone.',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            try {
              await dispatch(deleteProblem(problemId)).unwrap();
              Alert.alert('Success', 'Problem deleted successfully.');
            } catch (error) {
              console.error('Failed to delete problem:', error);
              Alert.alert('Error', 'Failed to delete problem. Please try again.');
            }
          },
        },
      ]
    );
  }, [dispatch]);

  // Apply sorting to problems
  const sortedProblems = React.useMemo(() => {
    const sorted = [...problems];
    
    switch (sortBy) {
      case 'oldest':
        return sorted.sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
      case 'category':
        return sorted.sort((a, b) => {
          const categoryA = a.category || '';
          const categoryB = b.category || '';
          return categoryA.localeCompare(categoryB);
        });
      case 'confidence':
        return sorted.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
      case 'newest':
      default:
        return sorted.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    }
  }, [problems, sortBy]);

  return (
    <SafeAreaView style={styles.container}>
      <SearchAndFilter
        searchQuery={searchQuery}
        selectedCategory={selectedCategory}
        selectedStatus={selectedStatus}
        sortBy={sortBy}
        onSearchChange={handleSearchChange}
        onCategoryChange={handleCategoryChange}
        onStatusChange={handleStatusChange}
        onSortChange={handleSortChange}
        onClearFilters={handleClearFilters}
        problemCount={sortedProblems.length}
      />
      
      <ProblemHistory
        problems={sortedProblems}
        isLoading={isLoading}
        onRefresh={handleRefresh}
        onProblemPress={handleProblemPress}
        onProblemDelete={handleProblemDelete}
        searchQuery={searchQuery}
        selectedCategory={selectedCategory}
        selectedStatus={selectedStatus}
      />
    </SafeAreaView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
  });

export default HistoryScreen;