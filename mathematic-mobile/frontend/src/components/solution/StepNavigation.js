import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

const { width: screenWidth } = Dimensions.get('window');

const StepNavigation = ({
  currentStep,
  totalSteps,
  onPrevious,
  onNext,
  onStepSelect,
  showStepIndicators = true,
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  const canGoBack = currentStep > 0;
  const canGoNext = currentStep < totalSteps - 1;

  const renderStepIndicators = () => {
    if (!showStepIndicators || totalSteps > 10) return null;

    return (
      <View style={styles.stepIndicatorsContainer}>
        {Array.from({ length: totalSteps }, (_, index) => (
          <TouchableOpacity
            key={index}
            style={[
              styles.stepIndicator,
              index === currentStep && styles.activeStepIndicator,
              index < currentStep && styles.completedStepIndicator,
            ]}
            onPress={() => onStepSelect && onStepSelect(index)}
            activeOpacity={0.7}
          >
            <Text
              style={[
                styles.stepIndicatorText,
                index === currentStep && styles.activeStepIndicatorText,
                index < currentStep && styles.completedStepIndicatorText,
              ]}
            >
              {index < currentStep ? '✓' : index + 1}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const renderProgressBar = () => {
    if (totalSteps <= 1) return null;

    const progress = (currentStep / (totalSteps - 1)) * 100;

    return (
      <View style={styles.progressBarContainer}>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              { width: `${progress}%` },
            ]}
          />
        </View>
        <Text style={styles.progressText}>
          {currentStep + 1} of {totalSteps}
        </Text>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {renderProgressBar()}
      {renderStepIndicators()}
      
      <View style={styles.navigationControls}>
        <TouchableOpacity
          style={[
            styles.navButton,
            styles.prevButton,
            !canGoBack && styles.disabledButton,
          ]}
          onPress={onPrevious}
          disabled={!canGoBack}
          activeOpacity={0.7}
        >
          <Ionicons
            name="chevron-back"
            size={20}
            color={canGoBack ? colors.onPrimary : colors.onSurfaceDisabled}
          />
          <Text
            style={[
              styles.navButtonText,
              !canGoBack && styles.disabledButtonText,
            ]}
          >
            Previous
          </Text>
        </TouchableOpacity>

        <View style={styles.stepCounter}>
          <Text style={styles.stepCounterText}>
            Step {currentStep + 1}
          </Text>
        </View>

        <TouchableOpacity
          style={[
            styles.navButton,
            styles.nextButton,
            !canGoNext && styles.disabledButton,
          ]}
          onPress={onNext}
          disabled={!canGoNext}
          activeOpacity={0.7}
        >
          <Text
            style={[
              styles.navButtonText,
              !canGoNext && styles.disabledButtonText,
            ]}
          >
            {canGoNext ? 'Next' : 'Complete'}
          </Text>
          <Ionicons
            name={canGoNext ? "chevron-forward" : "checkmark"}
            size={20}
            color={canGoNext ? colors.onPrimary : colors.onSurfaceDisabled}
          />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const StepJumpMenu = ({ 
  currentStep, 
  totalSteps, 
  onStepSelect, 
  visible, 
  onClose 
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  if (!visible) return null;

  return (
    <View style={styles.jumpMenuOverlay}>
      <TouchableOpacity
        style={styles.jumpMenuBackdrop}
        onPress={onClose}
        activeOpacity={1}
      />
      <View style={styles.jumpMenuContainer}>
        <View style={styles.jumpMenuHeader}>
          <Text style={styles.jumpMenuTitle}>Jump to Step</Text>
          <TouchableOpacity
            style={styles.jumpMenuCloseButton}
            onPress={onClose}
          >
            <Ionicons name="close" size={24} color={colors.text} />
          </TouchableOpacity>
        </View>
        
        <View style={styles.jumpMenuSteps}>
          {Array.from({ length: totalSteps }, (_, index) => (
            <TouchableOpacity
              key={index}
              style={[
                styles.jumpMenuStep,
                index === currentStep && styles.jumpMenuActiveStep,
                index < currentStep && styles.jumpMenuCompletedStep,
              ]}
              onPress={() => {
                onStepSelect(index);
                onClose();
              }}
              activeOpacity={0.7}
            >
              <View style={styles.jumpMenuStepIndicator}>
                <Text
                  style={[
                    styles.jumpMenuStepNumber,
                    index === currentStep && styles.jumpMenuActiveStepNumber,
                    index < currentStep && styles.jumpMenuCompletedStepNumber,
                  ]}
                >
                  {index < currentStep ? '✓' : index + 1}
                </Text>
              </View>
              <Text
                style={[
                  styles.jumpMenuStepText,
                  index === currentStep && styles.jumpMenuActiveStepText,
                ]}
              >
                Step {index + 1}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      backgroundColor: colors.surface,
      borderTopWidth: 1,
      borderTopColor: colors.outline,
      paddingTop: 16,
      paddingBottom: 16,
      paddingHorizontal: 16,
    },
    progressBarContainer: {
      marginBottom: 16,
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
      fontSize: 12,
      color: colors.textSecondary,
      textAlign: 'center',
    },
    stepIndicatorsContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      flexWrap: 'wrap',
      marginBottom: 16,
      paddingHorizontal: 8,
    },
    stepIndicator: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.surfaceVariant,
      justifyContent: 'center',
      alignItems: 'center',
      marginHorizontal: 4,
      marginVertical: 2,
    },
    activeStepIndicator: {
      backgroundColor: colors.primary,
    },
    completedStepIndicator: {
      backgroundColor: colors.secondary,
    },
    stepIndicatorText: {
      fontSize: 12,
      fontWeight: '600',
      color: colors.onSurfaceVariant,
    },
    activeStepIndicatorText: {
      color: colors.onPrimary,
    },
    completedStepIndicatorText: {
      color: colors.onSecondary,
    },
    navigationControls: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    navButton: {
      flexDirection: 'row',
      alignItems: 'center',
      backgroundColor: colors.primary,
      paddingHorizontal: 16,
      paddingVertical: 12,
      borderRadius: 8,
      minWidth: 100,
    },
    prevButton: {
      justifyContent: 'flex-start',
    },
    nextButton: {
      justifyContent: 'flex-end',
    },
    disabledButton: {
      backgroundColor: colors.surfaceVariant,
    },
    navButtonText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.onPrimary,
      marginHorizontal: 4,
    },
    disabledButtonText: {
      color: colors.onSurfaceDisabled,
    },
    stepCounter: {
      alignItems: 'center',
    },
    stepCounterText: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.text,
    },
    // Jump Menu Styles
    jumpMenuOverlay: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 1000,
    },
    jumpMenuBackdrop: {
      flex: 1,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
    },
    jumpMenuContainer: {
      position: 'absolute',
      top: '20%',
      left: '10%',
      right: '10%',
      maxHeight: '60%',
      backgroundColor: colors.surface,
      borderRadius: 16,
      overflow: 'hidden',
    },
    jumpMenuHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 16,
      borderBottomWidth: 1,
      borderBottomColor: colors.outline,
    },
    jumpMenuTitle: {
      fontSize: 18,
      fontWeight: 'bold',
      color: colors.text,
    },
    jumpMenuCloseButton: {
      padding: 4,
    },
    jumpMenuSteps: {
      maxHeight: 300,
    },
    jumpMenuStep: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
      borderBottomWidth: 1,
      borderBottomColor: colors.surfaceVariant,
    },
    jumpMenuActiveStep: {
      backgroundColor: colors.primaryContainer,
    },
    jumpMenuCompletedStep: {
      backgroundColor: colors.secondaryContainer,
    },
    jumpMenuStepIndicator: {
      width: 32,
      height: 32,
      borderRadius: 16,
      backgroundColor: colors.surfaceVariant,
      justifyContent: 'center',
      alignItems: 'center',
      marginRight: 12,
    },
    jumpMenuStepNumber: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.onSurfaceVariant,
    },
    jumpMenuActiveStepNumber: {
      color: colors.onPrimaryContainer,
    },
    jumpMenuCompletedStepNumber: {
      color: colors.onSecondaryContainer,
    },
    jumpMenuStepText: {
      fontSize: 16,
      color: colors.text,
    },
    jumpMenuActiveStepText: {
      color: colors.onPrimaryContainer,
      fontWeight: '600',
    },
  });

export { StepNavigation, StepJumpMenu };
export default StepNavigation;