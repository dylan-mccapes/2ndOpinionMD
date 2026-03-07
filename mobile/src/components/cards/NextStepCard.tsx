/**
 * 2OPMD Mobile — Next Step Card
 *
 * Actionable CTA card used on Home screen.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → E. Cards
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius, shadows } from '../../theme';

interface NextStepCardProps {
  title: string;
  description?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  style?: ViewStyle;
}

export function NextStepCard({
  title,
  description,
  icon = 'arrow-forward-circle',
  onPress,
  style,
}: NextStepCardProps) {
  return (
    <TouchableOpacity
      style={[styles.card, style]}
      onPress={onPress}
      activeOpacity={0.8}
    >
      <View style={styles.content}>
        <View style={styles.textContainer}>
          <Text style={styles.title}>{title}</Text>
          {description && <Text style={styles.description}>{description}</Text>}
        </View>
        <Ionicons name={icon} size={24} color={colors.accentPrimary} />
      </View>
    </TouchableOpacity>
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
  content: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  textContainer: {
    flex: 1,
    marginRight: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    marginTop: spacing.xs,
    lineHeight: 18,
  },
});
