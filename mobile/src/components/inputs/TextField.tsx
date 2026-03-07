/**
 * 2OPMD Mobile — Text Field (single-line + multiline)
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → C. Inputs
 */

import React from 'react';
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  TextInputProps,
  ViewStyle,
} from 'react-native';
import { colors, typography, spacing, radius } from '../../theme';

interface TextFieldProps extends TextInputProps {
  label?: string;
  helperText?: string;
  error?: string;
  containerStyle?: ViewStyle;
}

export function TextField({
  label,
  helperText,
  error,
  containerStyle,
  multiline,
  ...rest
}: TextFieldProps) {
  return (
    <View style={[styles.container, containerStyle]}>
      {label && <Text style={styles.label}>{label}</Text>}
      <TextInput
        style={[
          styles.input,
          multiline && styles.multiline,
          error ? styles.inputError : null,
        ]}
        placeholderTextColor={colors.textTertiary}
        selectionColor={colors.accentPrimary}
        multiline={multiline}
        {...rest}
      />
      {error && <Text style={styles.errorText}>{error}</Text>}
      {!error && helperText && <Text style={styles.helperText}>{helperText}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: spacing.lg,
  },
  label: {
    color: colors.textSecondary,
    fontSize: typography.sizes.label,
    fontWeight: typography.weights.medium,
    marginBottom: spacing.sm,
  },
  input: {
    backgroundColor: colors.bgSurface,
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    minHeight: 48,
    borderWidth: 1,
    borderColor: colors.separator,
  },
  multiline: {
    minHeight: 100,
    textAlignVertical: 'top',
    paddingTop: spacing.md,
  },
  inputError: {
    borderColor: colors.statusError,
  },
  errorText: {
    color: colors.statusError,
    fontSize: typography.sizes.small,
    marginTop: spacing.xs,
  },
  helperText: {
    color: colors.textTertiary,
    fontSize: typography.sizes.small,
    marginTop: spacing.xs,
  },
});
