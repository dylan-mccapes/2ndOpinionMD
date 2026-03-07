/**
 * 2OPMD Mobile — Top App Bar
 *
 * Variants: centered title, back + title, back + progress.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → A. Navigation
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { IconButton } from '../buttons/IconButton';
import { colors, typography, spacing } from '../../theme';

interface TopAppBarProps {
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
  progress?: { current: number; total: number };
  rightAction?: React.ReactNode;
  style?: ViewStyle;
}

export function TopAppBar({
  title,
  showBack = false,
  onBack,
  progress,
  rightAction,
  style,
}: TopAppBarProps) {
  return (
    <View style={[styles.container, style]}>
      <View style={styles.leftSlot}>
        {showBack && onBack && (
          <IconButton icon="arrow-back" onPress={onBack} size={22} />
        )}
      </View>

      <View style={styles.centerSlot}>
        {progress ? (
          <View style={styles.progressContainer}>
            <View style={styles.progressTrack}>
              <View
                style={[
                  styles.progressFill,
                  { width: `${(progress.current / progress.total) * 100}%` },
                ]}
              />
            </View>
            <Text style={styles.progressLabel}>
              {progress.current} / {progress.total}
            </Text>
          </View>
        ) : title ? (
          <Text style={styles.title} numberOfLines={1}>
            {title}
          </Text>
        ) : null}
      </View>

      <View style={styles.rightSlot}>
        {rightAction}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.bgPrimary,
    minHeight: 48,
  },
  leftSlot: {
    width: 44,
    alignItems: 'flex-start',
  },
  centerSlot: {
    flex: 1,
    alignItems: 'center',
  },
  rightSlot: {
    width: 44,
    alignItems: 'flex-end',
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
  },
  progressContainer: {
    alignItems: 'center',
    width: '80%',
  },
  progressTrack: {
    width: '100%',
    height: 2,
    backgroundColor: colors.separator,
    borderRadius: 1,
  },
  progressFill: {
    height: 2,
    backgroundColor: colors.white,
    borderRadius: 1,
  },
  progressLabel: {
    color: colors.textTertiary,
    fontSize: typography.sizes.small,
    marginTop: spacing.xs,
  },
});
