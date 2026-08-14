import React from 'react';
import { StyleSheet } from 'react-native';
import { Button as PaperButton } from 'react-native-paper';
import { colors, spacing, borderRadius, typography } from '../../constants/theme.js';

export const Button  = ({
  variant = 'contained',
  size = 'medium',
  fullWidth = false,
  style,
  textStyle,
  children,
  disabled,
  ...props
}) => {
  const buttonStyle = [
    styles.base,
    styles[size],
    fullWidth && styles.fullWidth,
    disabled && styles.disabled,
    style,
  ];

  const labelStyle = [
    styles.text,
    styles[`${size}Text`],
    disabled && styles.disabledText,
    textStyle,
  ];

  return (
    <PaperButton
      mode={variant}
      disabled={disabled}
      style={buttonStyle}
      labelStyle={labelStyle}
      buttonColor={variant === 'contained' ? colors.primary : undefined}
      textColor={variant === 'contained' ? colors.white : colors.primary}
      {...props}
    >
      {children}
    </PaperButton>
  );
};

const styles = StyleSheet.create({
  base: {
    borderRadius: borderRadius.sm,
  },
  small: {
    paddingHorizontal: spacing.sm,
    minHeight: 32,
  },
  medium: {
    paddingHorizontal: spacing.md,
    minHeight: 40,
  },
  large: {
    paddingHorizontal: spacing.lg,
    minHeight: 48,
  },
  fullWidth: {
    width: '100%',
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    fontFamily: typography.medium,
  },
  smallText: {
    fontSize: typography.fontSizes.sm,
  },
  mediumText: {
    fontSize: typography.fontSizes.md,
  },
  largeText: {
    fontSize: typography.fontSizes.lg,
  },
  disabledText: {
    opacity: 0.7,
  },
});