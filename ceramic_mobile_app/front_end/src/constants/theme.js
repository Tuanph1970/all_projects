import { DefaultTheme } from 'react-native-paper';

export const colors = {
  primary: '#007bff',
  primaryDark: '#0056b3',
  primaryLight: '#4dabf7',
  primaryContainer: '#e3f2fd',
  
  secondary: '#6c757d',
  secondaryDark: '#495057',
  secondaryLight: '#adb5bd',
  
  tertiary: '#20c997',
  
  success: '#28a745',
  warning: '#ffc107',
  error: '#dc3545',
  info: '#17a2b8',
  
  errorContainer: '#ffebee',
  onErrorContainer: '#b71c1c',
  
  background: '#ffffff',
  surface: '#f8f9fa',
  surfaceVariant: '#e9ecef',
  card: '#ffffff',
  outline: '#dee2e6',
  
  text: '#212529',
  textSecondary: '#6c757d',
  textMuted: '#adb5bd',
  
  border: '#dee2e6',
  borderLight: '#f8f9fa',
  
  white: '#ffffff',
  black: '#000000',
  
  gray: {
    50: '#f8f9fa',
    100: '#f1f3f4',
    200: '#e9ecef',
    300: '#dee2e6',
    400: '#ced4da',
    500: '#adb5bd',
    600: '#6c757d',
    700: '#495057',
    800: '#343a40',
    900: '#212529',
  },
};

export const spacing = {
  xs: 4,
  sm: 8,
  base: 16,
  md: 20,
  lg: 24,
  large: 24, // Add missing 'large' property
  xl: 32,
  '2xl': 48,
  '3xl': 64,
  '4xl': 80,
};

export const borderRadius = {
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  full: 9999,
};

export const typography = {
  fontSizes: {
    xs: 12,
    sm: 14,
    base: 16,
    md: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
  },
  sizes: {
    xs: 12,
    sm: 14,
    base: 16,
    md: 16,
    lg: 18,
    large: 18, // Add missing 'large' property
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
  },
  fontWeights: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  weights: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  bold: '700', // Direct access
  lineHeights: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.8,
  },
  medium: '500',
};

export const shadows = {
  sm: {
    shadowOffset: {
      width: 0,
      height: 1,
    },
    shadowOpacity: 0.18,
    shadowRadius: 1.0,
    elevation: 1,
  },
  md: {
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  lg: {
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.32,
    shadowRadius: 5.46,
    elevation: 9,
  },
};

export const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.primary,
    accent: colors.secondary,
    background: colors.background,
    surface: colors.surface,
    text: colors.text,
    disabled: colors.gray[400],
    placeholder: colors.gray[500],
    backdrop: 'rgba(0, 0, 0, 0.5)',
    notification: colors.error,
  },
  spacing,
  borderRadius,
  typography,
  shadows,
  custom: {
    colors,
    spacing,
    borderRadius,
    typography,
    shadows,
  },
};