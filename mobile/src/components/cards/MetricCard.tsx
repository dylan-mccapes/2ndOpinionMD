/**
 * 2OPMD Mobile — Metric Summary Card
 *
 * Displays a single metric with label, value, and optional trend.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → E. Cards
 */

import React from 'react';
import { View, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius, shadows } from '../../theme';

type Trend = 'up' | 'down' | 'stable';

interface MetricCardProps {
  label: string;
  value: string;
  trend?: Trend;
  trendLabel?: string;
  style?: ViewStyle;
}

function getTrendIcon(trend: Trend): keyof typeof Ionicons.glyphMap {
  switch (trend) {
    case 'up':
      return 'arrow-up';
    case 'down':
      return 'arrow-down';
    case 'stable':
      return 'remove';
  }
}

function getTrendColor(trend: Trend): string {
  switch (trend) {
    case 'up':
      return colors.statusWarning;
    case 'down':
      return colors.accentGreen;
    case 'stable':
      return colors.textSecondary;
  }
}

export function MetricCard({
  label,
  value,
  trend,
  trendLabel,
  style,
}: MetricCardProps) {
  return (
    <View style={[styles.card, style]}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
      {trend && (
        <View style={styles.trendRow}>
          <Ionicons
            name={getTrendIcon(trend)}
            size={14}
            color={getTrendColor(trend)}
          />
          {trendLabel && (
            <Text style={[styles.trendLabel, { color: getTrendColor(trend) }]}>
              {trendLabel}
            </Text>
          )}
        </View>
      )}
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
  label: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    fontWeight: typography.weights.medium,
    marginBottom: spacing.xs,
  },
  value: {
    color: colors.textPrimary,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
  },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: spacing.sm,
    gap: spacing.xs,
  },
  trendLabel: {
    fontSize: typography.sizes.small,
    fontWeight: typography.weights.medium,
  },
});
