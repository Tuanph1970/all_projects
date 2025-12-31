// Design System Components Export
// This file serves as the main entry point for the design system components

// Typography components
export {
  Display,
  Headline,
  Title,
  Label,
  Body,
  MathFormula,
  StepNumber,
  ProblemCategory,
  ErrorText,
  SuccessText,
  TYPOGRAPHY_SCALE,
} from './Typography';

// Button components
export {
  default as Button,
  PrimaryButton,
  SecondaryButton,
  TextButton,
  TonalButton,
  IconButton,
  FAB,
  ToggleButton,
} from './Button';

// Card components
export {
  default as Card,
  ProblemCard,
  SolutionStepCard,
  InfoCard,
  SkeletonCard,
} from './Card';

// Design tokens and constants
export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const BORDER_RADIUS = {
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  xxl: 20,
  full: 9999,
};

export const ELEVATION = {
  none: 0,
  sm: 2,
  md: 4,
  lg: 8,
  xl: 12,
  xxl: 16,
};

// Component sizes
export const COMPONENT_SIZES = {
  small: 'small',
  medium: 'medium',
  large: 'large',
};

// Animation durations (in milliseconds)
export const ANIMATION = {
  fast: 150,
  medium: 250,
  slow: 400,
};

// Common component props for consistency
export const COMMON_PROPS = {
  // Accessibility
  accessibilityLabel: 'string',
  testID: 'string',
  
  // Styling
  style: 'object',
  
  // State
  disabled: 'boolean',
};

// Utility functions for design system
export const getSpacing = (size) => SPACING[size] || size;
export const getBorderRadius = (size) => BORDER_RADIUS[size] || size;
export const getElevation = (size) => ELEVATION[size] || size;