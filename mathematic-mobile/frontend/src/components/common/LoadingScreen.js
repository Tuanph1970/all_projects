import React from 'react';
import { View, ActivityIndicator, Text, StyleSheet } from 'react-native';
import { useTheme } from '../../hooks/useTheme';

const LoadingScreen = ({ message = 'Loading...', size = 'large' }) => {
  const { colors } = useTheme();

  const styles = createStyles(colors);

  return (
    <View style={styles.container}>
      <ActivityIndicator size={size} color={colors.primary} />
      <Text style={styles.message}>{message}</Text>
    </View>
  );
};

const createStyles = (colors) =>
  StyleSheet.create({
    container: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: colors.background,
    },
    message: {
      marginTop: 16,
      fontSize: 16,
      color: colors.textSecondary,
      textAlign: 'center',
    },
  });

export default LoadingScreen;