/**
 * 2OPMD Mobile — Radio Card Selector
 *
 * Large tap targets for single-selection choices (e.g., diagnosed vs searching).
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → D. Selection Controls
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, typography, spacing, radius, shadows } from '../../theme';

interface RadioCardOption {
  id: string;
  title: string;
  description?: string;
}

interface RadioCardSelectorProps {
  options: RadioCardOption[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  style?: ViewStyle;
}

export function RadioCardSelector({
  options,
  selectedId,
  onSelect,
  style,
}: RadioCardSelectorProps) {
  return (
    <View style={[styles.container, style]}>
      {options.map((option) => {
        const isSelected = option.id === selectedId;
        return (
          <TouchableOpacity
            key={option.id}
            style={[styles.card, isSelected && styles.cardSelected]}
            onPress={() => onSelect(option.id)}
            activeOpacity={0.8}
          >
            <View style={styles.radioRow}>
              <View style={[styles.radio, isSelected && styles.radioSelected]}>
                {isSelected && <View style={styles.radioDot} />}
              </View>
              <View style={styles.textContainer}>
                <Text style={[styles.title, isSelected && styles.titleSelected]}>
                  {option.title}
                </Text>
                {option.description && (
                  <Text style={styles.description}>{option.description}</Text>
                )}
              </View>
            </View>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
  },
  card: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    borderWidth: 1.5,
    borderColor: colors.separator,
    ...shadows.card,
  },
  cardSelected: {
    borderColor: colors.accentPrimary,
    backgroundColor: colors.bgElevated,
  },
  radioRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colors.textTertiary,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: spacing.md,
    marginTop: 2,
  },
  radioSelected: {
    borderColor: colors.accentPrimary,
  },
  radioDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: colors.accentPrimary,
  },
  textContainer: {
    flex: 1,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
  },
  titleSelected: {
    color: colors.white,
  },
  description: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    marginTop: spacing.xs,
    lineHeight: 18,
  },
});
