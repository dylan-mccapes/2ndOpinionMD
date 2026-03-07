/**
 * 2OPMD Mobile — Primary Button
 *
 * Full-width, pill-shaped, white bg, black text, min height 52px.
 * States: default / pressed / disabled / loading.
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → B. Buttons
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
} from 'react-native';
import { colors, typography, spacing, radius, components } from '../../theme';

interface PrimaryButtonProps {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  loading?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export function PrimaryButton({
  title,
  onPress,
  disabled = false,
  loading = false,
  style,
  textStyle,
}: PrimaryButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      style={[
        styles.button,
        isDisabled && styles.buttonDisabled,
        style,
      ]}
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.8}
    >
      {loading ? (
        <ActivityIndicator color={colors.buttonText} size="small" />
      ) : (
        <Text style={[styles.text, isDisabled && styles.textDisabled, textStyle]}>
          {title}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    backgroundColor: colors.buttonBg,
    minHeight: components.button.minHeight,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xxl,
    paddingVertical: spacing.md,
  },
  buttonDisabled: {
    opacity: 0.4,
  },
  text: {
    color: colors.buttonText,
    fontSize: typography.sizes.button,
    fontWeight: typography.weights.bold,
  },
  textDisabled: {
    opacity: 0.6,
  },
});
