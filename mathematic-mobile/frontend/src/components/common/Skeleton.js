import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, Easing } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

/**
 * Skeleton Component
 * Displays a shimmer loading placeholder
 */
const Skeleton = ({ 
  width, 
  height, 
  borderRadius = 4, 
  variant = 'rect', 
  style,
  animationDuration = 1500,
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  const animatedValue = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(animatedValue, {
          toValue: 1,
          duration: animationDuration,
          easing: Easing.easeInOut,
          useNativeDriver: true,
        }),
        Animated.timing(animatedValue, {
          toValue: 0,
          duration: animationDuration,
          easing: Easing.easeInOut,
          useNativeDriver: true,
        }),
      ])
    );

    animation.start();

    return () => {
      animation.stop();
    };
  }, [animatedValue, animationDuration]);

  const opacity = animatedValue.interpolate({
    inputRange: [0, 1],
    outputRange: [0.3, 0.8],
  });

  const variantStyles = {
    rect: {
      width: width || '100%',
      height: height || 16,
    },
    circular: {
      width: width || height || 40,
      height: width || height || 40,
      borderRadius: (width || height || 40) / 2,
    },
    text: {
      width: width || '80%',
      height: height || 16,
    },
    avatar: {
      width: width || 56,
      height: height || 56,
      borderRadius: 28,
    },
  };

  return (
    <Animated.View
      style={[
        styles.skeleton,
        variantStyles[variant],
        { borderRadius, opacity },
        style,
      ]}
    />
  );
};

/**
 * SkeletonList Component
 * Displays multiple skeleton items in a list
 */
const SkeletonList = ({ 
  count = 5, 
  height = 16, 
  spacing = 12,
  variant = 'rect',
}) => {
  const styles = createStylesWithSpacing(spacing);
  
  return (
    <View style={styles.container}>
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton
          key={index}
          height={height}
          variant={variant}
          style={styles.item}
        />
      ))}
    </View>
  );
};

/**
 * SolutionSkeleton Component
 * Skeleton loader for solution screen
 */
const SolutionSkeleton = () => {
  const { colors } = useTheme();
  const styles = createSolutionSkeletonStyles(colors);

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Skeleton width={40} height={40} variant="circular" />
        <Skeleton width={150} height={24} />
        <View style={styles.headerActions}>
          <Skeleton width={32} height={32} variant="circular" />
          <Skeleton width={32} height={32} variant="circular" />
        </View>
      </View>

      {/* Solution Title */}
      <View style={styles.content}>
        <Skeleton width="60%" height={28} />
        <Skeleton width="80%" height={20} style={styles.marginTop} />
        
        {/* Steps */}
        <View style={styles.steps}>
          {Array.from({ length: 3 }).map((_, index) => (
            <View key={index} style={styles.step}>
              <View style={styles.stepHeader}>
                <Skeleton width={32} height={32} variant="circular" />
                <Skeleton width="70%" height={20} style={styles.marginLeft} />
              </View>
              <Skeleton width="90%" height={16} style={styles.marginTop} />
              <Skeleton width="60%" height={16} style={styles.marginTop} />
            </View>
          ))}
        </View>

        {/* Navigation */}
        <View style={styles.navigation}>
          <Skeleton width={100} height={44} />
          <Skeleton width={50} height={20} />
          <Skeleton width={100} height={44} />
        </View>
      </View>
    </View>
  );
};

/**
 * ProblemListSkeleton Component
 * Skeleton loader for problem list/history screen
 */
const ProblemListSkeleton = ({ count = 5 }) => {
  const { colors } = useTheme();
  const styles = createProblemListStyles(colors);

  return (
    <View style={styles.container}>
      {Array.from({ length: count }).map((_, index) => (
        <View key={index} style={styles.problemCard}>
          <View style={styles.problemHeader}>
            <Skeleton width={48} height={48} variant="circular" />
            <View style={styles.problemInfo}>
              <Skeleton width="70%" height={18} />
              <Skeleton width="50%" height={14} style={styles.marginTop} />
            </View>
          </View>
          <Skeleton width="90%" height={14} style={styles.marginTop} />
          <View style={styles.problemFooter}>
            <Skeleton width={60} height={20} />
            <Skeleton width={80} height={20} />
          </View>
        </View>
      ))}
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    skeleton: {
      backgroundColor: colors.surfaceVariant,
    },
  });

const createStylesWithSpacing = (spacing) =>
  StyleSheet.create({
    container: {
      gap: spacing,
    },
    item: {
      width: '100%',
    },
  });

const createSolutionSkeletonStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    header: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingHorizontal: 16,
      paddingVertical: 12,
      gap: 12,
    },
    headerActions: {
      flexDirection: 'row',
      marginLeft: 'auto',
      gap: 8,
    },
    content: {
      flex: 1,
      padding: 16,
    },
    marginTop: {
      marginTop: 8,
    },
    marginLeft: {
      marginLeft: 12,
    },
    steps: {
      marginTop: 24,
      gap: 16,
    },
    step: {
      backgroundColor: colors.surface,
      padding: 16,
      borderRadius: 12,
    },
    stepHeader: {
      flexDirection: 'row',
      alignItems: 'center',
    },
    navigation: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginTop: 24,
      paddingHorizontal: 16,
    },
  });

const createProblemListStyles = (colors) =>
  StyleSheet.create({
    container: {
      padding: 16,
      gap: 12,
    },
    problemCard: {
      backgroundColor: colors.surface,
      padding: 16,
      borderRadius: 12,
    },
    problemHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      gap: 12,
    },
    problemInfo: {
      flex: 1,
    },
    problemFooter: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginTop: 12,
    },
    marginTop: {
      marginTop: 8,
    },
  });

export { 
  Skeleton, 
  SkeletonList, 
  SolutionSkeleton, 
  ProblemListSkeleton 
};
export default Skeleton;
