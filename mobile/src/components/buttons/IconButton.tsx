/**
 * 2OPMD Mobile — Icon Button (small + circular variants)
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → B. Buttons
 */

import React from 'react';
import { TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, spacing, radius, components } from '../../theme';

interface IconButtonProps {
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
  size?: number;
  color?: string;
  circular?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
}

export function IconButton({
  icon,
  onPress,
  size = components.icon.standard,
  color = colors.white,
  circular = false,
  disabled = false,
  style,
}: IconButtonProps) {
  return (
    <TouchableOpacity
      style={[
        styles.base,
        circular && styles.circular,
        disabled && styles.disabled,
        style,
      ]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.6}
    >
      <Ionicons name={icon} size={size} color={color} />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    padding: spacing.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  circular: {
    backgroundColor: colors.bgElevated,
    borderRadius: radius.full,
    width: 44,
    height: 44,
  },
  disabled: {
    opacity: 0.4,
  },
});
