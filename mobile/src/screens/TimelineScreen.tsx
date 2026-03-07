/**
 * 2OPMD Mobile — Timeline Screen (H9 – Timeline Detail)
 *
 * Event rows, pattern markers, symptom spikes, context chips.
 * Visual timeline of entries. Pattern summary when data exists.
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Screen Checklist → H9
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { EmptyState } from '../components/feedback/EmptyState';
import { colors, typography, spacing } from '../theme';

export function TimelineScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Timeline</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <EmptyState
          icon="git-branch-outline"
          title="Signal building."
          message="More entries strengthen pattern detection. Your timeline will appear here."
        />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },
  header: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
  },
  scroll: {
    flex: 1,
  },
  content: {
    padding: spacing.screenHorizontal,
    paddingBottom: spacing.xxxl,
  },
});
