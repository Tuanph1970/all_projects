import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  StyleSheet,
  RefreshControl,
  Dimensions,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const { width: screenWidth } = Dimensions.get('window');
const CARD_WIDTH = (screenWidth - 48) / 2;

const ProblemHistory = ({
  problems = [],
  isLoading = false,
  onRefresh,
  onProblemPress,
  onProblemDelete,
  searchQuery = '',
  selectedCategory = null,
  selectedStatus = null,
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await onRefresh?.();
    } finally {
      setRefreshing(false);
    }
  }, [onRefresh]);

  const filteredProblems = problems.filter(problem => {
    const matchesSearch = !searchQuery || 
      problem.category?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      problem.description?.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesCategory = !selectedCategory || problem.category === selectedCategory;
    const matchesStatus = !selectedStatus || problem.status === selectedStatus;
    
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    
    return date.toLocaleDateString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'solved':
        return colors.success;
      case 'pending':
        return colors.warning;
      case 'failed':
        return colors.error;
      default:
        return colors.textSecondary;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'solved':
        return 'checkmark-circle';
      case 'pending':
        return 'time';
      case 'failed':
        return 'close-circle';
      default:
        return 'help-circle';
    }
  };

  const getCategoryIcon = (category) => {
    switch (category?.toLowerCase()) {
      case 'algebra':
        return 'calculator';
      case 'geometry':
        return 'shapes';
      case 'calculus':
        return 'trending-up';
      case 'statistics':
        return 'bar-chart';
      case 'trigonometry':
        return 'radio-button-on';
      default:
        return 'school';
    }
  };

  const renderProblemCard = (problem, index) => (
    <TouchableOpacity
      key={problem.id}
      style={styles.problemCard}
      onPress={() => onProblemPress?.(problem)}
      activeOpacity={0.7}
    >
      {/* Problem Image */}
      <View style={styles.imageContainer}>
        {problem.imageUri ? (
          <Image
            source={{ uri: problem.imageUri }}
            style={styles.problemImage}
            resizeMode="cover"
          />
        ) : (
          <View style={styles.placeholderImage}>
            <Ionicons
              name={getCategoryIcon(problem.category)}
              size={32}
              color={colors.textSecondary}
            />
          </View>
        )}
        
        {/* Status Badge */}
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(problem.status) }]}>
          <Ionicons
            name={getStatusIcon(problem.status)}
            size={12}
            color={colors.onPrimary}
          />
        </View>

        {/* Delete Button */}
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => onProblemDelete?.(problem.id)}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Ionicons name="trash" size={16} color={colors.error} />
        </TouchableOpacity>
      </View>

      {/* Problem Info */}
      <View style={styles.problemInfo}>
        <Text style={styles.problemCategory} numberOfLines={1}>
          {problem.category || 'General'}
        </Text>
        
        {problem.description && (
          <Text style={styles.problemDescription} numberOfLines={2}>
            {problem.description}
          </Text>
        )}
        
        <View style={styles.problemMeta}>
          <Text style={styles.problemDate}>
            {formatDate(problem.createdAt)}
          </Text>
          
          {problem.confidence && (
            <View style={styles.confidenceContainer}>
              <Text style={styles.confidenceText}>
                {Math.round(problem.confidence * 100)}%
              </Text>
            </View>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );

  const renderEmptyState = () => (
    <View style={styles.emptyContainer}>
      <Ionicons name="document-outline" size={64} color={colors.textSecondary} />
      <Text style={styles.emptyTitle}>No problems found</Text>
      <Text style={styles.emptyDescription}>
        {searchQuery || selectedCategory || selectedStatus
          ? 'Try adjusting your search filters'
          : 'Start by taking a photo of a math problem to solve'}
      </Text>
    </View>
  );

  const renderSectionHeader = (title, count) => (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {count > 0 && (
        <Text style={styles.sectionCount}>
          {count} problem{count !== 1 ? 's' : ''}
        </Text>
      )}
    </View>
  );

  // Group problems by date
  const groupedProblems = filteredProblems.reduce((groups, problem) => {
    const date = new Date(problem.createdAt);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    let groupKey;
    if (date.toDateString() === today.toDateString()) {
      groupKey = 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      groupKey = 'Yesterday';
    } else {
      groupKey = date.toLocaleDateString();
    }
    
    if (!groups[groupKey]) {
      groups[groupKey] = [];
    }
    groups[groupKey].push(problem);
    
    return groups;
  }, {});

  if (isLoading && filteredProblems.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading problems...</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={handleRefresh}
          colors={[colors.primary]}
          tintColor={colors.primary}
        />
      }
      showsVerticalScrollIndicator={false}
    >
      {filteredProblems.length === 0 ? (
        renderEmptyState()
      ) : (
        Object.entries(groupedProblems).map(([dateGroup, problemsInGroup]) => (
          <View key={dateGroup} style={styles.dateGroup}>
            {renderSectionHeader(dateGroup, problemsInGroup.length)}
            
            <View style={styles.problemsGrid}>
              {problemsInGroup.map((problem, index) =>
                renderProblemCard(problem, index)
              )}
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    contentContainer: {
      padding: 16,
      paddingBottom: 32,
    },
    loadingContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    loadingText: {
      fontSize: 16,
      color: colors.textSecondary,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
      minHeight: 200,
    },
    emptyTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.text,
      marginTop: 16,
      marginBottom: 8,
    },
    emptyDescription: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
      lineHeight: 22,
    },
    dateGroup: {
      marginBottom: 24,
    },
    sectionHeader: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: 12,
    },
    sectionTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      color: colors.text,
    },
    sectionCount: {
      fontSize: 14,
      color: colors.textSecondary,
    },
    problemsGrid: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      justifyContent: 'space-between',
    },
    problemCard: {
      width: CARD_WIDTH,
      backgroundColor: colors.surface,
      borderRadius: 12,
      marginBottom: 16,
      ...Platform.select({
        ios: {
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
        },
        android: {
          elevation: 3,
        },
      }),
    },
    imageContainer: {
      position: 'relative',
      height: 120,
      borderTopLeftRadius: 12,
      borderTopRightRadius: 12,
      overflow: 'hidden',
    },
    problemImage: {
      width: '100%',
      height: '100%',
    },
    placeholderImage: {
      width: '100%',
      height: '100%',
      backgroundColor: colors.surfaceVariant,
      justifyContent: 'center',
      alignItems: 'center',
    },
    statusBadge: {
      position: 'absolute',
      top: 8,
      right: 8,
      width: 24,
      height: 24,
      borderRadius: 12,
      justifyContent: 'center',
      alignItems: 'center',
    },
    deleteButton: {
      position: 'absolute',
      top: 8,
      left: 8,
      width: 28,
      height: 28,
      borderRadius: 14,
      backgroundColor: colors.surface,
      justifyContent: 'center',
      alignItems: 'center',
      ...Platform.select({
        ios: {
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.2,
          shadowRadius: 2,
        },
        android: {
          elevation: 2,
        },
      }),
    },
    problemInfo: {
      padding: 12,
    },
    problemCategory: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.primary,
      marginBottom: 4,
      textTransform: 'capitalize',
    },
    problemDescription: {
      fontSize: 12,
      color: colors.textSecondary,
      lineHeight: 16,
      marginBottom: 8,
    },
    problemMeta: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
    },
    problemDate: {
      fontSize: 12,
      color: colors.textSecondary,
    },
    confidenceContainer: {
      backgroundColor: colors.primaryContainer,
      paddingHorizontal: 6,
      paddingVertical: 2,
      borderRadius: 4,
    },
    confidenceText: {
      fontSize: 10,
      fontWeight: '600',
      color: colors.onPrimaryContainer,
    },
  });

export default ProblemHistory;