/**
 * 2OPMD Mobile — Base Card
 *
 * Foundation card component. All card variants build on this.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → E. Cards
 */

import React, { ReactNode } from 'react';
import { View, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, radius, shadows } from '../../theme';

interface BaseCardProps {
  children: ReactNode;
  elevated?: boolean;
  style?: ViewStyle;
}

export function BaseCard({ children, elevated = false, style }: BaseCardProps) {
  return (
    <View
      style={[
        styles.card,
        elevated && styles.elevated,
        style,
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.separator,
    ...shadows.card,
  },
  elevated: {
    backgroundColor: colors.bgElevated,
    ...shadows.elevated,
  },
});
