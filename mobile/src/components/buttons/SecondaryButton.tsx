/**
 * 2OPMD Mobile — Secondary Button (Outline)
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → B. Buttons
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, typography, spacing, radius, components } from '../../theme';

interface SecondaryButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export function SecondaryButton({
  title,
  onPress,
  disabled = false,
  style,
  textStyle,
}: SecondaryButtonProps) {
  return (
    <TouchableOpacity
      style={[styles.button, disabled && styles.buttonDisabled, style]}
      onPress={onPress}
      disabled={disabled}
      activeOpacity={0.8}
    >
      <Text style={[styles.text, disabled && styles.textDisabled, textStyle]}>
        {title}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: colors.transparent,
    minHeight: components.button.minHeight,
    borderRadius: radius.pill,
    borderWidth: components.button.borderWidth,
    borderColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.md,
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  text: {
    color: colors.white,
    fontSize: typography.sizes.button,
    fontWeight: typography.weights.semibold,
  },
  textDisabled: {
    opacity: 0.6,
  },
});
