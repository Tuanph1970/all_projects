import { useSelector } from 'react-redux';
import { useColorScheme } from 'react-native';
import { selectApp } from '../store';

// Light theme colors
const lightTheme = {
  primary: '#007AFF',
  primaryDark: '#0051D5',
  secondary: '#5856D6',
  background: '#FFFFFF',
  surface: '#F2F2F7',
  card: '#FFFFFF',
  border: '#C6C6C8',
  notification: '#FF3B30',
  success: '#34C759',
  warning: '#FF9500',
  error: '#FF3B30',
  text: '#000000',
  textSecondary: '#8E8E93',
  textTertiary: '#C7C7CC',
  placeholder: '#8E8E93',
  disabled: '#C7C7CC',
  shadow: '#000000',
};

// Dark theme colors
const darkTheme = {
  primary: '#0A84FF',
  primaryDark: '#0051D5',
  secondary: '#5E5CE6',
  background: '#000000',
  surface: '#1C1C1E',
  card: '#2C2C2E',
  border: '#38383A',
  notification: '#FF453A',
  success: '#30D158',
  warning: '#FF9F0A',
  error: '#FF453A',
  text: '#FFFFFF',
  textSecondary: '#8E8E93',
  textTertiary: '#48484A',
  placeholder: '#8E8E93',
  disabled: '#48484A',
  shadow: '#000000',
};

export const useTheme = () => {
  const systemColorScheme = useColorScheme();
  const appState = useSelector(selectApp);
  const appTheme = appState?.theme || 'light'; // Fallback to 'light' if app state not loaded

  // Determine the effective theme
  const getEffectiveTheme = () => {
    if (appTheme === 'system') {
      return systemColorScheme === 'dark' ? 'dark' : 'light';
    }
    return appTheme;
  };

  const effectiveTheme = getEffectiveTheme();
  const isDark = effectiveTheme === 'dark';
  const colors = isDark ? darkTheme : lightTheme;

  return {
    colors,
    isDark,
    theme: effectiveTheme,
  };
};