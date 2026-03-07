/**
 * O14 — 3-Day Baseline Commitment
 *
 * Elements: short mission card, "Start 3-day baseline" CTA.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O14_BaselineCommitment'>;

export function O14_BaselineCommitment({ navigation }: Props) {
  const { currentStep, totalSteps } = useOnboardingStore();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <View style={styles.spacerTop} />

        {/* Mission card */}
        <View style={styles.missionCard}>
          <Text style={styles.missionIcon}>🌱</Text>
          <Text style={styles.missionHeadline}>
            Your 3-day baseline.
          </Text>
          <Text style={styles.missionBody}>
            Three days of quick check-ins gives us enough signal to start finding patterns. It takes less than 30 seconds each day.
          </Text>
          <View style={styles.commitmentRow}>
            <View style={styles.dayDot} />
            <View style={styles.dayDot} />
            <View style={styles.dayDot} />
          </View>
          <Text style={styles.commitmentLabel}>
            Day 1 — Day 2 — Day 3
          </Text>
        </View>

        <Text style={styles.tagline}>
          Signal strengthens with consistency.
        </Text>

        <View style={styles.spacerBottom} />

        <PrimaryButton
          title="Start 3-day baseline"
          onPress={() => navigation.navigate('O15_SaveProgress')}
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
  content: {
    flex: 1,
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
  },
  spacerTop: {
    flex: 1,
  },
  missionCard: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xxl,
    alignItems: 'center',
  },
  missionIcon: {
    fontSize: 40,
    marginBottom: spacing.lg,
  },
  missionHeadline: {
    fontFamily: typography.fonts.serif,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: spacing.md,
  },
  missionBody: {
    fontSize: typography.sizes.body,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: spacing.xxl,
  },
  commitmentRow: {
    flexDirection: 'row',
    gap: spacing.xxxl,
    marginBottom: spacing.sm,
  },
  dayDot: {
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: colors.accentGreen,
    opacity: 0.5,
  },
  commitmentLabel: {
    fontSize: typography.sizes.caption,
    color: colors.textTertiary,
  },
  tagline: {
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing.xxl,
    fontStyle: 'italic',
  },
  spacerBottom: {
    flex: 1,
  },
});
