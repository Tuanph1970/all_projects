import React from 'react';
import {
  View,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from 'react-native';
import { useTheme } from '../../hooks/useTheme';

const CARD_ELEVATIONS = {
  none: 0,
  low: Platform.select({ ios: 2, android: 2 }),
  medium: Platform.select({ ios: 4, android: 4 }),
  high: Platform.select({ ios: 8, android: 8 }),
};

const Card = ({
  // Content
  children,
  
  // Styling
  variant = 'elevated', // elevated, filled, outlined
  elevation = 'medium',
  borderRadius = 12,
  
  // Interaction
  onPress,
  onLongPress,
  disabled = false,
  
  // Layout
  style,
  contentStyle,
  
  // Accessibility
  accessibilityLabel,
  testID,
  
  ...props
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  
  const getVariantStyles = () => {
    switch (variant) {
      case 'elevated':
        return {
          backgroundColor: colors.surface,
          ...Platform.select({
            ios: {
              shadowColor: '#000',
              shadowOffset: { width: 0, height: CARD_ELEVATIONS[elevation] / 2 },
              shadowOpacity: 0.1,
              shadowRadius: CARD_ELEVATIONS[elevation],
            },
            android: {
              elevation: CARD_ELEVATIONS[elevation],
            },
          }),
        };
      case 'filled':
        return {
          backgroundColor: colors.surfaceVariant,
        };
      case 'outlined':
        return {
          backgroundColor: colors.surface,
          borderWidth: 1,
          borderColor: colors.outline,
        };
      default:
        return {};
    }
  };
  
  const cardStyles = [
    styles.card,
    {
      borderRadius,
    },
    getVariantStyles(),
    disabled && styles.disabled,
    style,
  ];
  
  const CardComponent = onPress || onLongPress ? TouchableOpacity : View;
  
  return (
    <CardComponent
      style={cardStyles}
      onPress={disabled ? undefined : onPress}
      onLongPress={disabled ? undefined : onLongPress}
      disabled={disabled}
      activeOpacity={onPress ? 0.7 : 1}
      accessibilityLabel={accessibilityLabel}
      testID={testID}
      {...props}
    >
      <View style={[styles.content, contentStyle]}>
        {children}
      </View>
    </CardComponent>
  );
};

// Specialized Card variants
export const ProblemCard = ({
  imageUri,
  title,
  category,
  date,
  status,
  confidence,
  onPress,
  onDelete,
  style,
  ...props
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  
  return (
    <Card
      onPress={onPress}
      style={[styles.problemCard, style]}
      {...props}
    >
      {/* Problem card content would go here */}
      {/* This is a simplified version - full implementation in ProblemHistory component */}
    </Card>
  );
};

export const SolutionStepCard = ({
  stepNumber,
  title,
  description,
  formula,
  isActive = false,
  isCompleted = false,
  onPress,
  style,
  children,
  ...props
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  
  const getStepCardStyles = () => {
    if (isActive) {
      return {
        backgroundColor: colors.primaryContainer,
        borderColor: colors.primary,
        borderWidth: 1.5,
      };
    }
    if (isCompleted) {
      return {
        backgroundColor: colors.surfaceVariant,
        opacity: 0.8,
      };
    }
    return {};
  };
  
  return (
    <Card
      variant="elevated"
      onPress={onPress}
      style={[
        styles.stepCard,
        getStepCardStyles(),
        style,
      ]}
      {...props}
    >
      {children}
    </Card>
  );
};

export const InfoCard = ({
  icon,
  title,
  description,
  action,
  variant = 'info', // info, warning, error, success
  style,
  ...props
}) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);
  
  const getInfoCardStyles = () => {
    switch (variant) {
      case 'warning':
        return {
          backgroundColor: `${colors.warning}10`,
          borderLeftWidth: 4,
          borderLeftColor: colors.warning,
        };
      case 'error':
        return {
          backgroundColor: `${colors.error}10`,
          borderLeftWidth: 4,
          borderLeftColor: colors.error,
        };
      case 'success':
        return {
          backgroundColor: `${colors.success}10`,
          borderLeftWidth: 4,
          borderLeftColor: colors.success,
        };
      case 'info':
      default:
        return {
          backgroundColor: `${colors.primary}10`,
          borderLeftWidth: 4,
          borderLeftColor: colors.primary,
        };
    }
  };
  
  return (
    <Card
      variant="filled"
      style={[
        styles.infoCard,
        getInfoCardStyles(),
        style,
      ]}
      {...props}\n    >\n      {/* Info card content would go here */}\n      {/* Implementation depends on specific use case */}\n    </Card>\n  );\n};\n\n// Loading Card skeleton\nexport const SkeletonCard = ({ height = 120, style, ...props }) => {\n  const { colors } = useTheme();\n  const styles = createStyles(colors);\n  \n  return (\n    <Card\n      variant=\"filled\"\n      style={[\n        styles.skeletonCard,\n        { height },\n        style,\n      ]}\n      {...props}\n    >\n      <View style={styles.skeletonContent}>\n        <View style={[styles.skeletonLine, { width: '60%' }]} />\n        <View style={[styles.skeletonLine, { width: '40%' }]} />\n        <View style={[styles.skeletonLine, { width: '80%' }]} />\n      </View>\n    </Card>\n  );\n};\n\nconst createStyles = (colors) =>\n  StyleSheet.create({\n    card: {\n      overflow: 'hidden',\n    },\n    content: {\n      // Base content padding - can be overridden\n    },\n    disabled: {\n      opacity: 0.6,\n    },\n    problemCard: {\n      marginBottom: 12,\n    },\n    stepCard: {\n      marginBottom: 12,\n    },\n    infoCard: {\n      padding: 16,\n    },\n    skeletonCard: {\n      backgroundColor: colors.surfaceVariant,\n      justifyContent: 'center',\n    },\n    skeletonContent: {\n      padding: 16,\n    },\n    skeletonLine: {\n      height: 12,\n      backgroundColor: colors.outline,\n      borderRadius: 6,\n      marginBottom: 8,\n    },\n  });\n\nexport default Card;"
},
{"old_string": "    >\n      {/* Info card content would go here */}\n      {/* Implementation depends on specific use case */}\n    </Card>\n  );\n};\n\n// Loading Card skeleton\nexport const SkeletonCard = ({ height = 120, style, ...props }) => {\n  const { colors } = useTheme();\n  const styles = createStyles(colors);\n  \n  return (\n    <Card\n      variant=\"filled\"\n      style={[\n        styles.skeletonCard,\n        { height },\n        style,\n      ]}\n      {...props}\n    >\n      <View style={styles.skeletonContent}>\n        <View style={[styles.skeletonLine, { width: '60%' }]} />\n        <View style={[styles.skeletonLine, { width: '40%' }]} />\n        <View style={[styles.skeletonLine, { width: '80%' }]} />\n      </View>\n    </Card>\n  );\n};", "new_string": "    >\n      {/* Info card content would go here */}\n      {/* Implementation depends on specific use case */}\n    </Card>\n  );\n};\n\n// Loading Card skeleton\nexport const SkeletonCard = ({ height = 120, style, ...props }) => {\n  const { colors } = useTheme();\n  const styles = createStyles(colors);\n  \n  return (\n    <Card\n      variant=\"filled\"\n      style={[\n        styles.skeletonCard,\n        { height },\n        style,\n      ]}\n      {...props}\n    >\n      <View style={styles.skeletonContent}>\n        <View style={[styles.skeletonLine, { width: '60%' }]} />\n        <View style={[styles.skeletonLine, { width: '40%' }]} />\n        <View style={[styles.skeletonLine, { width: '80%' }]} />\n      </View>\n    </Card>\n  );\n};"}]