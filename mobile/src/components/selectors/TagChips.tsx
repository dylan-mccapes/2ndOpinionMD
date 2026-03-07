/**
 * 2OPMD Mobile — Tag Chips / Pill Selector
 *
 * Multi-select chip layout for symptoms, emotions, etc.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → D. Selection Controls
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import { colors, typography, spacing, radius } from '../../theme';

interface ChipItem {
  id: string;
  label: string;
}

interface TagChipsProps {
  items: ChipItem[];
  selectedIds: string[];
  onToggle: (id: string) => void;
  maxSelections?: number;
  style?: ViewStyle;
}

export function TagChips({
  items,
  selectedIds,
  onToggle,
  maxSelections,
  style,
}: TagChipsProps) {
  const handlePress = (id: string) => {
    const isSelected = selectedIds.includes(id);
    if (!isSelected && maxSelections && selectedIds.length >= maxSelections) {
      return;
    }
    onToggle(id);
  };

  return (
    <View style={[styles.container, style]}>
      {items.map((item) => {
        const isSelected = selectedIds.includes(item.id);
        return (
          <TouchableOpacity
            key={item.id}
            style={[styles.chip, isSelected && styles.chipSelected]}
            onPress={() => handlePress(item.id)}
            activeOpacity={0.7}
          >
            <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.separator,
  },
  chipSelected: {
    backgroundColor: colors.accentPrimary,
    borderColor: colors.accentPrimary,
  },
  chipText: {
    color: colors.textPrimary,
    fontSize: typography.sizes.label,
    fontWeight: typography.weights.medium,
  },
  chipTextSelected: {
    color: colors.white,
    fontWeight: typography.weights.semibold,
  },
});
