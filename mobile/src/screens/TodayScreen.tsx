/**
 * 2OPMD Mobile — Today Screen (H1 – Home)
 *
 * Primary home tab. Tree + streak, today check-in card, patterns emerging,
 * next step, collapsed timeline preview, advanced analysis CTA, prepare for visit CTA.
 *
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Screen Checklist → H1
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NextStepCard } from '../components/cards/NextStepCard';
import { EmptyState } from '../components/feedback/EmptyState';
import { colors, typography, spacing } from '../theme';

export function TodayScreen() {
  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        {/* Tree + Streak placeholder */}
        <View style={styles.treeContainer}>
          <Text style={styles.treeEmoji}>🌳</Text>
          <Text style={styles.streakText}>Signal strengthens with consistency.</Text>
        </View>

        {/* Today check-in CTA */}
        <NextStepCard
          title="2-Second Check-In"
          description="How are you feeling right now?"
          icon="pulse"
          onPress={() => {}}
          style={styles.card}
        />

        {/* Patterns Emerging placeholder */}
        <EmptyState
          icon="analytics-outline"
          title="Not enough data yet."
          message="Log a few days to see patterns emerge."
          style={styles.emptyState}
        />

        {/* Quick actions */}
        <NextStepCard
          title="Prepare for Visit"
          description="Summary, timeline, questions to ask."
          icon="document-text"
          onPress={() => {}}
          style={styles.card}
        />

        <NextStepCard
          title="Advanced Analysis"
          description="Consistency, patterns, confidence."
          icon="bar-chart"
          onPress={() => {}}
          style={styles.card}
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
  scroll: {
    flex: 1,
  },
  content: {
    padding: spacing.screenHorizontal,
    paddingBottom: spacing.xxxl,
  },
  treeContainer: {
    alignItems: 'center',
    paddingVertical: spacing.xxl,
  },
  treeEmoji: {
    fontSize: 64,
  },
  streakText: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    fontWeight: typography.weights.medium,
    marginTop: spacing.sm,
  },
  card: {
    marginBottom: spacing.lg,
  },
  emptyState: {
    marginBottom: spacing.lg,
  },
});
