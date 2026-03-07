/**
 * 2OPMD Mobile — Tertiary Text Button / Inline Link Button
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → B. Buttons
 */

import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ViewStyle, TextStyle } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface TextButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export function TextButton({
  title,
  onPress,
  disabled = false,
  style,
  textStyle,
}: TextButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.container, style]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.6}
    >
      <Text style={[styles.text, disabled && styles.textDisabled, textStyle]}>
        {title}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  text: {
    color: colors.accentPrimary,
    fontSize: typography.sizes.secondaryAction,
    fontWeight: typography.weights.medium,
  },
  textDisabled: {
    opacity: 0.4,
  },
});
