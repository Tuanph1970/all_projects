import React from 'react';
import { StyleSheet } from 'react-native';
import { Card as PaperCard } from 'react-native-paper';
import { colors, spacing, borderRadius, shadows } from '../../constants/theme.js';

export const Card  = ({
  elevation = 'sm',
  style,
  children,
  ...props
}) => {
  const cardStyle = [
    styles.base,
    elevation !== 'none' && shadows[elevation],
    style,
  ];

  return (
    <PaperCard style={cardStyle} {...props}>
      {children}
    </PaperCard>
  );
};

const styles = StyleSheet.create({
  base: {
    borderRadius: borderRadius.md,
    padding: spacing.md,
    margin: spacing.xs,
    backgroundColor: colors.card,
  },
});