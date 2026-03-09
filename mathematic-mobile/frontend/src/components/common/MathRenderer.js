import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Platform,
  ActivityIndicator,
  TouchableOpacity,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../hooks/useTheme';

/**
 * MathRenderer Component
 * Renders mathematical formulas using react-native-math-view (KaTeX based)
 * Falls back to text rendering if library is not available
 */
const MathRenderer = ({ 
  formula, 
  style, 
  textStyle, 
  size = 16,
  color,
  onLongPress,
  showCopyButton = false,
}) => {
  const { colors } = useTheme();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [MathView, setMathView] = useState(null);

  useEffect(() => {
    // Load MathView component
    const loadMathView = async () => {
      try {
        const { MathView: MathViewComponent } = await import('react-native-math-view');
        setMathView(() => MathViewComponent);
        setIsLoading(false);
      } catch (err) {
        console.error('Failed to load MathView:', err);
        setError('Math rendering not available');
        setIsLoading(false);
      }
    };

    loadMathView();
  }, []);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formula);
      // Could show toast notification here
    } catch (err) {
      console.error('Failed to copy formula:', err);
    }
  };

  if (!formula) {
    return null;
  }

  if (isLoading) {
    return (
      <View style={[styles.container, style]}>
        <ActivityIndicator size="small" color={colors.primary} />
        <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
          Loading formula...
        </Text>
      </View>
    );
  }

  if (error || !MathView) {
    // Fallback to simple text rendering
    return (
      <View style={[styles.container, styles.fallbackContainer, style]}>
        <Text style={[styles.fallbackText, { fontSize: size, color: color || colors.text }]}>
          {formula}
        </Text>
        {showCopyButton && (
          <TouchableOpacity style={styles.copyButton} onPress={handleCopy}>
            <Ionicons name="copy-outline" size={16} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>
    );
  }

  // Render with MathView (KaTeX)
  return (
    <View style={[styles.container, style]}>
      <MathView
        math={formula}
        size={size}
        color={color || colors.text}
        onError={(err) => {
          console.error('MathView error:', err);
          setError(err.message);
        }}
      />
      {showCopyButton && (
        <TouchableOpacity style={styles.copyButton} onPress={handleCopy}>
          <Ionicons name="copy-outline" size={16} color={colors.textSecondary} />
        </TouchableOpacity>
      )}
    </View>
  );
};

/**
 * MathText Component
 * Inline math rendering for simple expressions
 */
const MathText = ({ formula, style, size = 14 }) => {
  const { colors } = useTheme();

  return (
    <Text style={[styles.inlineMath, { fontSize: size, color: colors.text }, style]}>
      {formula}
    </Text>
  );
};

/**
 * MathBlock Component
 * Block-level math rendering for displayed equations
 */
const MathBlock = ({ formula, style, label }) => {
  const { colors } = useTheme();
  const styles = createStyles(colors);

  return (
    <View style={styles.mathBlock}>
      {label && <Text style={styles.mathBlockLabel}>{label}</Text>}
      <MathRenderer formula={formula} style={styles.mathBlockContent} size={18} />
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      padding: 12,
      marginVertical: 8,
      borderRadius: 8,
      backgroundColor: colors.surfaceVariant,
      alignItems: 'center',
      justifyContent: 'center',
      position: 'relative',
    },
    loadingText: {
      fontSize: 12,
      marginTop: 8,
    },
    fallbackContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    fallbackText: {
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
      flex: 1,
    },
    copyButton: {
      padding: 8,
    },
    inlineMath: {
      fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    },
    mathBlock: {
      backgroundColor: colors.surfaceVariant,
      borderRadius: 8,
      padding: 16,
      marginVertical: 8,
    },
    mathBlockLabel: {
      fontSize: 12,
      fontWeight: '600',
      color: colors.textSecondary,
      marginBottom: 8,
      textTransform: 'uppercase',
      letterSpacing: 0.5,
    },
    mathBlockContent: {
      alignItems: 'center',
    },
  });

export { MathRenderer, MathText, MathBlock };
export default MathRenderer;
