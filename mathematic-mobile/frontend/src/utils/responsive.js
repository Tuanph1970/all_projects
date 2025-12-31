import { Dimensions, PixelRatio } from 'react-native';

// Get device dimensions
const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Define breakpoints following common mobile patterns
export const BREAKPOINTS = {
  xs: 0,     // Extra small devices (phones in portrait)
  sm: 576,   // Small devices (phones in landscape)
  md: 768,   // Medium devices (tablets in portrait)
  lg: 992,   // Large devices (tablets in landscape)
  xl: 1200,  // Extra large devices (small desktops)
};

// Device type detection
export const getDeviceType = () => {
  if (SCREEN_WIDTH < BREAKPOINTS.sm) return 'phone-portrait';
  if (SCREEN_WIDTH < BREAKPOINTS.md) return 'phone-landscape';
  if (SCREEN_WIDTH < BREAKPOINTS.lg) return 'tablet-portrait';
  if (SCREEN_WIDTH < BREAKPOINTS.xl) return 'tablet-landscape';
  return 'desktop';
};

// Check if device is tablet
export const isTablet = () => {
  const deviceType = getDeviceType();
  return deviceType.includes('tablet');
};

// Check if device is in landscape mode
export const isLandscape = () => SCREEN_WIDTH > SCREEN_HEIGHT;

// Responsive font size based on screen width
export const responsiveFontSize = (size) => {
  const scale = SCREEN_WIDTH / 375; // Base on iPhone X width
  const newSize = size * scale;
  
  // Ensure font size doesn't get too small or too large
  const minSize = size * 0.8;
  const maxSize = size * 1.2;
  
  return Math.max(minSize, Math.min(newSize, maxSize));
};

// Responsive spacing
export const responsiveSpacing = (spacing) => {
  const deviceType = getDeviceType();
  
  switch (deviceType) {
    case 'phone-portrait':
      return spacing;
    case 'phone-landscape':
      return spacing * 1.1;
    case 'tablet-portrait':
      return spacing * 1.3;
    case 'tablet-landscape':
      return spacing * 1.4;
    case 'desktop':
      return spacing * 1.5;
    default:
      return spacing;
  }
};

// Responsive width/height
export const responsiveWidth = (percentage) => {
  return (SCREEN_WIDTH * percentage) / 100;
};

export const responsiveHeight = (percentage) => {
  return (SCREEN_HEIGHT * percentage) / 100;
};

// Get appropriate number of columns for grid layouts
export const getGridColumns = (minItemWidth = 150) => {
  return Math.floor(SCREEN_WIDTH / minItemWidth);
};

// Responsive padding/margin
export const responsivePadding = (base = 16) => {
  const deviceType = getDeviceType();
  
  switch (deviceType) {
    case 'phone-portrait':
      return base;
    case 'phone-landscape':
      return Math.max(base, 20);
    case 'tablet-portrait':
      return Math.max(base, 24);
    case 'tablet-landscape':
      return Math.max(base, 32);
    case 'desktop':
      return Math.max(base, 40);
    default:
      return base;
  }
};

// Responsive card width for grid layouts
export const getCardWidth = (columns = 2, spacing = 16) => {
  const totalSpacing = spacing * (columns + 1);
  return (SCREEN_WIDTH - totalSpacing) / columns;
};

// Safe area helpers for different devices
export const getSafeAreaPadding = () => {
  const deviceType = getDeviceType();
  
  // These values should be adjusted based on actual device testing
  const basePadding = {
    top: 44,     // Status bar height
    bottom: 34,  // Home indicator height (iOS)
    left: 0,
    right: 0,
  };
  
  if (deviceType.includes('tablet')) {
    return {
      ...basePadding,
      top: Math.max(basePadding.top, 24),
      bottom: Math.max(basePadding.bottom, 20),
    };
  }
  
  return basePadding;
};

// Responsive hook for React components
export const useResponsive = () => {
  return {
    screenWidth: SCREEN_WIDTH,
    screenHeight: SCREEN_HEIGHT,
    deviceType: getDeviceType(),
    isTablet: isTablet(),
    isLandscape: isLandscape(),
    responsiveFontSize,
    responsiveSpacing,
    responsiveWidth,
    responsiveHeight,
    responsivePadding,
    getGridColumns,
    getCardWidth,
    getSafeAreaPadding,
  };
};

// Responsive style generator
export const createResponsiveStyle = (baseStyle, responsiveOverrides = {}) => {
  const deviceType = getDeviceType();
  
  let responsiveStyle = { ...baseStyle };
  
  // Apply device-specific overrides
  if (responsiveOverrides[deviceType]) {
    responsiveStyle = { ...responsiveStyle, ...responsiveOverrides[deviceType] };
  }
  
  // Apply general tablet overrides
  if (isTablet() && responsiveOverrides.tablet) {
    responsiveStyle = { ...responsiveStyle, ...responsiveOverrides.tablet };
  }
  
  // Apply landscape overrides
  if (isLandscape() && responsiveOverrides.landscape) {
    responsiveStyle = { ...responsiveStyle, ...responsiveOverrides.landscape };
  }
  
  return responsiveStyle;
};

// Media query-like function for conditional rendering
export const mediaQuery = (conditions) => {
  const deviceType = getDeviceType();
  
  if (conditions.minWidth && SCREEN_WIDTH < conditions.minWidth) return false;
  if (conditions.maxWidth && SCREEN_WIDTH > conditions.maxWidth) return false;
  if (conditions.minHeight && SCREEN_HEIGHT < conditions.minHeight) return false;
  if (conditions.maxHeight && SCREEN_HEIGHT > conditions.maxHeight) return false;
  if (conditions.deviceType && deviceType !== conditions.deviceType) return false;
  if (conditions.isTablet !== undefined && isTablet() !== conditions.isTablet) return false;
  if (conditions.isLandscape !== undefined && isLandscape() !== conditions.isLandscape) return false;
  
  return true;
};

// Layout helpers for mathematical content
export const getMathLayoutConfig = () => {
  const deviceType = getDeviceType();
  
  switch (deviceType) {
    case 'phone-portrait':
      return {
        formulaFontSize: 14,
        stepCardPadding: 12,
        navigationHeight: 80,
        headerHeight: 56,
      };
    case 'phone-landscape':
      return {
        formulaFontSize: 16,
        stepCardPadding: 16,
        navigationHeight: 70,
        headerHeight: 50,
      };
    case 'tablet-portrait':
    case 'tablet-landscape':
      return {
        formulaFontSize: 18,
        stepCardPadding: 20,
        navigationHeight: 90,
        headerHeight: 64,
      };
    default:
      return {
        formulaFontSize: 16,
        stepCardPadding: 16,
        navigationHeight: 80,
        headerHeight: 56,
      };
  }
};

// Export dimensions for direct use
export { SCREEN_WIDTH, SCREEN_HEIGHT };