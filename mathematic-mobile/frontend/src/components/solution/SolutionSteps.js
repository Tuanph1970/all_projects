import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Dimensions,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';
import MathRenderer from '../common/MathRenderer';

const { width: screenWidth } = Dimensions.get('window');

const SolutionSteps = ({ solution, currentStep, onStepChange }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const [expandedSteps, setExpandedSteps] = useState(new Set());
  const scrollViewRef = useRef(null);
  const stepRefs = useRef([]);
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Auto-scroll to current step when it changes
    if (scrollViewRef.current && stepRefs.current[currentStep]) {
      stepRefs.current[currentStep].measureLayout(
        scrollViewRef.current,
        (x, y) => {
          scrollViewRef.current.scrollTo({ y: y - 100, animated: true });
        },
        () => {}
      );
    }

    // Animate step highlight
    Animated.spring(animatedValue, {
      toValue: currentStep,
      useNativeDriver: false,
      tension: 100,
      friction: 8,
    }).start();
  }, [currentStep, animatedValue]);

  const toggleStepExpansion = (stepIndex) => {
    const newExpanded = new Set(expandedSteps);
    if (newExpanded.has(stepIndex)) {
      newExpanded.delete(stepIndex);
    } else {
      newExpanded.add(stepIndex);
    }
    setExpandedSteps(newExpanded);
  };

  const navigateToStep = (stepIndex) => {
    if (onStepChange) {
      onStepChange(stepIndex);
    }
  };

  const renderMathFormula = (formula) => {
    // Use MathRenderer component with KaTeX for proper math rendering
    return (
      <MathRenderer 
        formula={formula} 
        size={18}
        showCopyButton={true}
      />
    );
  };

  const renderStepContent = (step, index) => {
    const isCurrentStep = index === currentStep;
    const isExpanded = expandedSteps.has(index);
    const isCompleted = index < currentStep;

    return (
      <View
        key={step.stepNumber}
        ref={(ref) => (stepRefs.current[index] = ref)}
        style={[
          styles.stepContainer,
          isCurrentStep && styles.currentStepContainer,
          isCompleted && styles.completedStepContainer,
        ]}
      >
        {/* Step Header */}
        <TouchableOpacity
          style={styles.stepHeader}
          onPress={() => navigateToStep(index)}
          activeOpacity={0.7}
        >
          <View style={styles.stepIndicator}>
            <View
              style={[
                styles.stepNumber,
                isCurrentStep && styles.currentStepNumber,
                isCompleted && styles.completedStepNumber,
              ]}
            >
              {isCompleted ? (
                <Ionicons
                  name="checkmark"
                  size={16}
                  color={colors.white}
                />
              ) : (
                <Text
                  style={[
                    styles.stepNumberText,
                    isCurrentStep && styles.currentStepNumberText,
                  ]}
                >
                  {step.stepNumber}
                </Text>
              )}
            </View>
            {index < (solution?.steps?.length - 1) && (
              <View
                style={[
                  styles.stepConnector,
                  isCompleted && styles.completedStepConnector,
                ]}
              />
            )}
          </View>

          <View style={styles.stepHeaderContent}>
            <Text
              style={[
                styles.stepTitle,
                isCurrentStep && styles.currentStepTitle,
              ]}
            >
              Step {step.stepNumber}: {step.title || 'Solution Step'}
            </Text>
            <Text
              style={[
                styles.stepDescription,
                isCurrentStep && styles.currentStepDescription,
              ]}
              numberOfLines={isExpanded ? undefined : 2}
            >
              {step.description}
            </Text>
          </View>

          <TouchableOpacity
            style={styles.expandButton}
            onPress={() => toggleStepExpansion(index)}
          >
            <Ionicons
              name={isExpanded ? 'chevron-up' : 'chevron-down'}
              size={20}
              color={colors.textSecondary}
            />
          </TouchableOpacity>
        </TouchableOpacity>

        {/* Step Content */}
        {(isExpanded || isCurrentStep) && (
          <View style={styles.stepContent}>
            {step.formula && renderMathFormula(step.formula)}
            
            {step.explanation && (
              <View style={styles.explanationContainer}>
                <Text style={styles.explanationLabel}>Explanation:</Text>
                <Text style={styles.explanationText}>{step.explanation}</Text>
              </View>
            )}

            {step.workingOut && (
              <View style={styles.workingContainer}>
                <Text style={styles.workingLabel}>Working:</Text>
                <Text style={styles.workingText}>{step.workingOut}</Text>
              </View>
            )}

            {step.keyPoints && step.keyPoints.length > 0 && (
              <View style={styles.keyPointsContainer}>
                <Text style={styles.keyPointsLabel}>Key Points:</Text>
                {step.keyPoints.map((point, pointIndex) => (
                  <View key={pointIndex} style={styles.keyPointItem}>
                    <View style={styles.bulletPoint} />
                    <Text style={styles.keyPointText}>{point}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}
      </View>
    );
  };

  if (!solution || !solution.steps || solution.steps.length === 0) {
    return (
      <View style={styles.emptyContainer}>
        <Ionicons name="document-outline" size={48} color={colors.textSecondary} />
        <Text style={styles.emptyText}>No solution steps available</Text>
      </View>
    );
  }

  return (
    <ScrollView
      ref={scrollViewRef}
      style={styles.container}
      contentContainerStyle={styles.contentContainer}
      showsVerticalScrollIndicator={false}
    >
      {/* Solution Header */}
      <View style={styles.solutionHeader}>
        <Text style={styles.solutionTitle}>Step-by-Step Solution</Text>
        <View style={styles.confidenceContainer}>
          <Text style={styles.confidenceLabel}>Confidence:</Text>
          <View style={styles.confidenceBar}>
            <View
              style={[
                styles.confidenceFill,
                { width: `${(solution.confidence || 0) * 100}%` },
              ]}
            />
          </View>
          <Text style={styles.confidenceText}>
            {Math.round((solution.confidence || 0) * 100)}%
          </Text>
        </View>
      </View>

      {/* Progress Indicator */}
      <View style={styles.progressContainer}>
        <View style={styles.progressBar}>
          <Animated.View
            style={[
              styles.progressFill,
              {
                width: animatedValue.interpolate({
                  inputRange: [0, solution.steps.length - 1],
                  outputRange: ['0%', '100%'],
                  extrapolate: 'clamp',
                }),
              },
            ]}
          />
        </View>
        <Text style={styles.progressText}>
          Step {currentStep + 1} of {solution.steps.length}
        </Text>
      </View>

      {/* Solution Steps */}
      <View style={styles.stepsContainer}>
        {solution.steps.map((step, index) => renderStepContent(step, index))}
      </View>

      {/* Solution Footer */}
      {solution.finalAnswer && (
        <View style={styles.finalAnswerContainer}>
          <Text style={styles.finalAnswerLabel}>Final Answer:</Text>
          {renderMathFormula(solution.finalAnswer)}
        </View>
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
    emptyContainer: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      padding: 32,
    },
    emptyText: {
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
      marginTop: 16,
    },
    solutionHeader: {
      marginBottom: 24,
    },
    solutionTitle: {
      fontSize: 24,
      fontWeight: 'bold',
      color: colors.text,
      marginBottom: 12,
    },
    confidenceContainer: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    confidenceLabel: {
      fontSize: 14,
      color: colors.textSecondary,
      marginRight: 8,
    },
    confidenceBar: {
      flex: 1,
      height: 6,
      backgroundColor: colors.surfaceVariant,
      borderRadius: 3,
      marginRight: 8,
    },
    confidenceFill: {
      height: '100%',
      backgroundColor: colors.primary,
      borderRadius: 3,
    },
    confidenceText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.primary,
    },
    progressContainer: {
      marginBottom: 24,
    },
    progressBar: {
      height: 4,
      backgroundColor: colors.surfaceVariant,
      borderRadius: 2,
      marginBottom: 8,
    },
    progressFill: {
      height: '100%',
      backgroundColor: colors.primary,
      borderRadius: 2,
    },
    progressText: {
      fontSize: 14,
      color: colors.textSecondary,
      textAlign: 'center',
    },
    stepsContainer: {
      marginBottom: 24,
    },
    stepContainer: {
      backgroundColor: colors.surface,
      borderRadius: 12,
      marginBottom: 12,
      ...Platform.select({
        ios: {
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 1 },
          shadowOpacity: 0.1,
          shadowRadius: 2,
        },
        android: {
          elevation: 2,
        },
      }),
    },
    currentStepContainer: {
      backgroundColor: colors.primaryContainer,
      borderColor: colors.primary,
      borderWidth: 1.5,
    },
    completedStepContainer: {
      backgroundColor: colors.surfaceVariant,
      opacity: 0.8,
    },
    stepHeader: {
      flexDirection: 'row',
      padding: 16,
      alignItems: 'flex-start',
    },
    stepIndicator: {
      alignItems: 'center',
      marginRight: 12,
    },
    stepNumber: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.surfaceVariant,
      justifyContent: 'center',
      alignItems: 'center',
    },
    currentStepNumber: {
      backgroundColor: colors.primary,
    },
    completedStepNumber: {
      backgroundColor: colors.secondary,
    },
    stepNumberText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
    },
    currentStepNumberText: {
      color: colors.onPrimary,
    },
    stepConnector: {
      width: 2,
      height: 20,
      backgroundColor: colors.surfaceVariant,
      marginTop: 4,
    },
    completedStepConnector: {
      backgroundColor: colors.secondary,
    },
    stepHeaderContent: {
      flex: 1,
    },
    stepTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 4,
    },
    currentStepTitle: {
      color: colors.onPrimaryContainer,
    },
    stepDescription: {
      fontSize: 14,
      color: colors.textSecondary,
      lineHeight: 20,
    },
    currentStepDescription: {
      color: colors.onPrimaryContainer,
    },
    expandButton: {
      padding: 4,
    },
    stepContent: {
      paddingHorizontal: 16,
      paddingBottom: 16,
      paddingLeft: 60,
    },
    formulaContainer: {
      backgroundColor: colors.surfaceVariant,
      borderRadius: 8,
      padding: 12,
      marginBottom: 12,
      alignItems: 'center',
    },
    formulaText: {
      fontSize: 16,
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
      color: colors.onSurfaceVariant,
    },
    explanationContainer: {
      marginBottom: 12,
    },
    explanationLabel: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 4,
    },
    explanationText: {
      fontSize: 14,
      color: colors.textSecondary,
      lineHeight: 20,
    },
    workingContainer: {
      marginBottom: 12,
    },
    workingLabel: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 4,
    },
    workingText: {
      fontSize: 14,
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
      color: colors.textSecondary,
      backgroundColor: colors.surfaceVariant,
      padding: 8,
      borderRadius: 4,
    },
    keyPointsContainer: {
      marginBottom: 12,
    },
    keyPointsLabel: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 8,
    },
    keyPointItem: {
      flexDirection: 'row',
      alignItems: 'flex-start',
      marginBottom: 6,
    },
    bulletPoint: {
      width: 6,
      height: 6,
      borderRadius: 3,
      backgroundColor: colors.primary,
      marginTop: 7,
      marginRight: 8,
    },
    keyPointText: {
      flex: 1,
      fontSize: 14,
      color: colors.textSecondary,
      lineHeight: 20,
    },
    finalAnswerContainer: {
      backgroundColor: colors.primaryContainer,
      borderRadius: 12,
      padding: 16,
      alignItems: 'center',
    },
    finalAnswerLabel: {
      fontSize: 18,
      fontWeight: 'bold',
      color: colors.onPrimaryContainer,
      marginBottom: 12,
    },
  });

export default SolutionSteps;