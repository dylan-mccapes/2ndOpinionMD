/**
 * 2OPMD Mobile — Toggle Switch
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → D. Selection Controls
 */

import React from 'react';
import { View, Text, Switch, StyleSheet, ViewStyle } from 'react-native';
import { colors, typography, spacing } from '../../theme';

interface ToggleSwitchProps {
  label: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  style?: ViewStyle;
}

export function ToggleSwitch({
  label,
  value,
  onValueChange,
  style,
}: ToggleSwitchProps) {
  return (
    <View style={[styles.container, style]}>
      <Text style={styles.label}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onValueChange}
        trackColor={{ false: colors.separator, true: colors.accentPrimary }}
        thumbColor={colors.white}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.md,
  },
  label: {
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.regular,
    flex: 1,
    marginRight: spacing.md,
  },
});
