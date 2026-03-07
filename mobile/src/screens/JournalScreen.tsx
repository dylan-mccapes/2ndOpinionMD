/**
 * 2OPMD Mobile — Journal Screen (H4 – Structured Journal)
 *
 * Symptom entries list + create. 4 modules (symptom shift, trigger selection,
 * context note, environment/behavior), optional attachments, completion CTA.
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Screen Checklist → H4
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { PrimaryButton } from '../components/buttons/PrimaryButton';
import { EmptyState } from '../components/feedback/EmptyState';
import { colors, typography, spacing } from '../theme';

export function JournalScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Journal</Text>
      </View>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <EmptyState
          icon="book-outline"
          title="No entries yet."
          message="Your first journal entry will start building your timeline."
        />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="New Entry"
          onPress={() => {}}
        />
      </View>
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
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
    backgroundColor: colors.bgPrimary,
  },
});
