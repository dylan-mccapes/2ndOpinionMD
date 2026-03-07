/**
 * 2OPMD Mobile — Error State
 *
 * Honest failure display. Cause + recovery. No softening.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → M. Feedback States
 * UX Invariant: No optimistic UI. Honest failures.
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing } from '../../theme';
import { PrimaryButton } from '../buttons/PrimaryButton';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  style?: ViewStyle;
}

export function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
  style,
}: ErrorStateProps) {
  return (
    <View style={[styles.container, style]}>
      <Ionicons name="alert-circle" size={48} color={colors.statusError} />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.message}>{message}</Text>
      {onRetry && (
        <PrimaryButton
          title="Try again"
          onPress={onRetry}
          style={styles.retryButton}
        />
      )}
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
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    marginTop: spacing.lg,
    textAlign: 'center',
  },
  message: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    marginTop: spacing.sm,
    textAlign: 'center',
    lineHeight: 18,
  },
  retryButton: {
    marginTop: spacing.xl,
    minWidth: 140,
  },
});
