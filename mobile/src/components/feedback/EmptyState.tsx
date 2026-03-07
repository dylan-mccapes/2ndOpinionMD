/**
 * 2OPMD Mobile — Empty State
 *
 * Shown when there's no data to display.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → M. Feedback States
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing } from '../../theme';

interface EmptyStateProps {
  icon?: keyof typeof Ionicons.glyphMap;
  title: string;
  message?: string;
  style?: ViewStyle;
}

export function EmptyState({
  icon = 'leaf-outline',
  title,
  message,
  style,
}: EmptyStateProps) {
  return (
    <View style={[styles.container, style]}>
      <Ionicons name={icon} size={48} color={colors.textTertiary} />
      <Text style={styles.title}>{title}</Text>
      {message && <Text style={styles.message}>{message}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: spacing.xxxl,
    paddingHorizontal: spacing.xxl,
  },
  title: {
    color: colors.textSecondary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    marginTop: spacing.lg,
    textAlign: 'center',
  },
  message: {
    color: colors.textTertiary,
    fontSize: typography.sizes.caption,
    marginTop: spacing.sm,
    textAlign: 'center',
    lineHeight: 18,
  },
});
