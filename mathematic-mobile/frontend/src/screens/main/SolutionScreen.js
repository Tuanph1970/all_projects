import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { useSelector, useDispatch } from 'react-redux';
import { Ionicons } from '@expo/vector-icons';

import { useTheme } from '../../hooks/useTheme';
import SolutionSteps from '../../components/solution/SolutionSteps';
import StepNavigation from '../../components/solution/StepNavigation';
import {
  fetchSolutionByProblemId,
  setCurrentStep,
  nextStep,
  previousStep,
  rateSolution,
} from '../../store/slices/solutionSlice';

const SolutionScreen = ({ route, navigation }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const dispatch = useDispatch();
  
  const { problemId, solutionId } = route.params || {};
  
  const {
    currentSolution,
    isLoading,
    error,
    currentStep,
    userRating,
    isRatingSubmitted,
  } = useSelector((state) => state.solution);
  
  const [showRating, setShowRating] = useState(false);

  useEffect(() => {
    if (problemId) {
      loadSolution();
    }
  }, [problemId]);

  const loadSolution = async () => {
    try {
      await dispatch(fetchSolutionByProblemId(problemId)).unwrap();
    } catch (error) {
      console.error('Failed to load solution:', error);
      Alert.alert('Error', 'Failed to load solution. Please try again.');
    }
  };

  const handleStepChange = (stepIndex) => {
    dispatch(setCurrentStep(stepIndex));
  };

  const handleNextStep = () => {
    dispatch(nextStep());
  };

  const handlePreviousStep = () => {
    dispatch(previousStep());
  };

  const handleRateSolution = async (rating, feedback = '') => {
    try {
      await dispatch(rateSolution({ 
        solutionId: currentSolution.id, 
        rating, 
        feedback 
      })).unwrap();
      setShowRating(false);
      Alert.alert('Thank you!', 'Your rating has been submitted.');
    } catch (error) {
      console.error('Failed to rate solution:', error);
      Alert.alert('Error', 'Failed to submit rating. Please try again.');
    }
  };

  const renderHeader = () => (
    <View style={styles.header}>
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => navigation.goBack()}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
      >
        <Ionicons name="arrow-back" size={24} color={colors.text} />
      </TouchableOpacity>
      
      <Text style={styles.headerTitle}>Solution</Text>
      
      <View style={styles.headerActions}>
        {currentSolution && !isRatingSubmitted && (
          <TouchableOpacity
            style={styles.rateButton}
            onPress={() => setShowRating(true)}
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Ionicons name="star-outline" size={24} color={colors.text} />
          </TouchableOpacity>
        )}
        
        <TouchableOpacity
          style={styles.shareButton}
          onPress={() => {
            // Implement share functionality
            Alert.alert('Share', 'Share functionality coming soon!');
          }}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="share-outline" size={24} color={colors.text} />
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderRatingModal = () => (
    showRating && (
      <View style={styles.ratingOverlay}>
        <View style={styles.ratingModal}>
          <Text style={styles.ratingTitle}>Rate this solution</Text>
          <Text style={styles.ratingDescription}>
            How helpful was this step-by-step solution?
          </Text>
          
          <View style={styles.ratingStars}>
            {[1, 2, 3, 4, 5].map((rating) => (
              <TouchableOpacity
                key={rating}
                style={styles.starButton}
                onPress={() => handleRateSolution(rating)}
              >
                <Ionicons
                  name="star"
                  size={32}
                  color={colors.warning}
                />
              </TouchableOpacity>
            ))}
          </View>
          
          <View style={styles.ratingActions}>
            <TouchableOpacity
              style={styles.cancelButton}
              onPress={() => setShowRating(false)}
            >
              <Text style={styles.cancelButtonText}>Cancel</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    )
  );

  if (isLoading && !currentSolution) {
    return (
      <SafeAreaView style={styles.container}>
        {renderHeader()}
        <View style={styles.loadingContainer}>
          <Text style={styles.loadingText}>Loading solution...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={styles.container}>
        {renderHeader()}
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={64} color={colors.error} />
          <Text style={styles.errorTitle}>Failed to load solution</Text>
          <Text style={styles.errorMessage}>{error}</Text>
          <TouchableOpacity
            style={styles.retryButton}
            onPress={loadSolution}
          >
            <Text style={styles.retryButtonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (!currentSolution) {
    return (
      <SafeAreaView style={styles.container}>
        {renderHeader()}
        <View style={styles.emptyContainer}>
          <Ionicons name="document-outline" size={64} color={colors.textSecondary} />
          <Text style={styles.emptyTitle}>No solution found</Text>
          <Text style={styles.emptyMessage}>
            The solution for this problem is not available.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {renderHeader()}
      
      <View style={styles.content}>
        <SolutionSteps
          solution={currentSolution}
          currentStep={currentStep}
          onStepChange={handleStepChange}
        />
      </View>
      
      <StepNavigation
        currentStep={currentStep}
        totalSteps={currentSolution?.steps?.length || 0}
        onPrevious={handlePreviousStep}
        onNext={handleNextStep}
        onStepSelect={handleStepChange}
        showStepIndicators={true}
      />
      
      {renderRatingModal()}
    </SafeAreaView>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderBottomWidth: 1,
      borderBottomColor: colors.outline,
    },
    backButton: {
      padding: 4,
    },
    headerTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      color: colors.text,
    },
    headerActions: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    rateButton: {
      padding: 4,
      marginRight: 8,
    },
    shareButton: {
      padding: 4,
    },
    content: {
      flex: 1,
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
    errorContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    errorTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.error,
      marginTop: 16,
      marginBottom: 8,
    },
    errorMessage: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
      marginBottom: 24,
    },
    retryButton: {
      backgroundColor: colors.primary,
      paddingHorizontal: 24,
      paddingVertical: 12,
      borderRadius: 8,
    },
    retryButtonText: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.onPrimary,
    },
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    emptyTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.text,
      marginTop: 16,
      marginBottom: 8,
    },
    emptyMessage: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
    },
    // Rating Modal Styles
    ratingOverlay: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      justifyContent: 'center',
      alignItems: 'center',
      zIndex: 1000,
    },
    ratingModal: {
      backgroundColor: colors.surface,
      borderRadius: 16,
      padding: 24,
      marginHorizontal: 32,
      alignItems: 'center',
    },
    ratingTitle: {
      fontSize: 20,
      fontWeight: 'bold',
      color: colors.text,
      marginBottom: 8,
    },
    ratingDescription: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
      marginBottom: 24,
    },
    ratingStars: {
      flexDirection: 'row',
      marginBottom: 24,
    },
    starButton: {
      padding: 8,
    },
    ratingActions: {
      flexDirection: 'row',
    },
    cancelButton: {
      paddingHorizontal: 16,
      paddingVertical: 8,
    },
    cancelButtonText: {
      fontSize: 16,
      color: colors.textSecondary,
    },
  });

export default SolutionScreen;