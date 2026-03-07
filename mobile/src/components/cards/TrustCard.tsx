/**
 * 2OPMD Mobile — Trust / Privacy Card
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → E. Cards
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius } from '../../theme';

interface TrustCardProps {
  text: string;
  style?: ViewStyle;
}

export function TrustCard({ text, style }: TrustCardProps) {
  return (
    <View style={[styles.card, style]}>
      <Ionicons name="shield-checkmark" size={16} color={colors.accentGreen} />
      <Text style={styles.text}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    gap: spacing.sm,
  },
  text: {
    color: colors.textTertiary,
    fontSize: typography.sizes.small,
    fontWeight: typography.weights.regular,
    flex: 1,
  },
});
