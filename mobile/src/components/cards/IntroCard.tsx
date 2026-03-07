/**
 * 2OPMD Mobile — Intro / Explanation Card
 *
 * Used in onboarding for promise cards, credibility tiles, journaling value bullets.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → E. Cards
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius, shadows } from '../../theme';

interface IntroCardProps {
  icon?: keyof typeof Ionicons.glyphMap;
  title: string;
  description?: string;
  style?: ViewStyle;
}

export function IntroCard({ icon, title, description, style }: IntroCardProps) {
  return (
    <View style={[styles.card, style]}>
      {icon && (
        <View style={styles.iconContainer}>
          <Ionicons name={icon} size={24} color={colors.accentPrimary} />
        </View>
      )}
      <Text style={styles.title}>{title}</Text>
      {description && <Text style={styles.description}>{description}</Text>}
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
  iconContainer: {
    marginBottom: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    marginBottom: spacing.xs,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    lineHeight: 18,
  },
});
