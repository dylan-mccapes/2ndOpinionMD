/**
 * O17 — Starting Snapshot
 *
 * Elements: what we know, what we'll watch, what improves accuracy, go to home CTA.
 */

import React, { useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { useAuthStore } from '../../store/authStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O17_StartingSnapshot'>;

interface SectionProps {
  title: string;
  items: string[];
}

function SnapshotSection({ title, items }: SectionProps) {
  return (
    <View style={sectionStyles.container}>
      <Text style={sectionStyles.title}>{title}</Text>
      {items.map((item) => (
        <View key={item} style={sectionStyles.row}>
          <View style={sectionStyles.dot} />
          <Text style={sectionStyles.text}>{item}</Text>
        </View>
      ))}
    </View>
  );
}

const sectionStyles = StyleSheet.create({
  container: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    marginBottom: spacing.lg,
  },
  title: {
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: spacing.sm,
    gap: spacing.sm,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.accentPrimary,
    marginTop: 7,
  },
  text: {
    flex: 1,
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    lineHeight: 20,
  },
});

export function O17_StartingSnapshot({ navigation }: Props) {
  const {
    name,
    userPath,
    diagnoses,
    searchingExplanation,
    selectedSymptoms,
    selectedEmotions,
    currentStep,
    totalSteps,
    setCurrentStep,
  } = useOnboardingStore();
  useEffect(() => { setCurrentStep(17); }, [setCurrentStep]);

  // Build dynamic "what we know" based on user inputs
  const whatWeKnow: string[] = [];
  if (name) whatWeKnow.push(`Name: ${name}`);
  if (userPath === 'diagnosed' && diagnoses.length > 0) {
    whatWeKnow.push(`Diagnoses: ${diagnoses.join(', ')}`);
  }
  if (userPath === 'searching' && searchingExplanation) {
    whatWeKnow.push(`Searching: ${searchingExplanation}`);
  }
  if (selectedSymptoms.length > 0) {
    whatWeKnow.push(`Top symptoms: ${selectedSymptoms.slice(0, 3).join(', ')}${selectedSymptoms.length > 3 ? ` +${selectedSymptoms.length - 3} more` : ''}`);
  }
  if (selectedEmotions.length > 0) {
    whatWeKnow.push(`Emotional context: ${selectedEmotions.join(', ')}`);
  }

  const whatWeWatch = [
    'Symptom trends over time',
    'Trigger-symptom correlations',
    'Sleep and energy patterns',
    'Flare frequency and severity',
  ];

  const whatImprovesAccuracy = [
    'Consistent daily check-ins',
    'Honest emotional context',
    'Structured journaling entries',
    'Uploaded medical records',
  ];

  const completeOnboarding = useAuthStore((s) => s.completeOnboarding);

  const handleGoHome = async () => {
    // Mark onboarding complete — RootNavigator will swap to MainTabs
    await completeOnboarding();
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
      >
        <Text style={styles.headline}>
          Your starting snapshot.
        </Text>
        <Text style={styles.subhead}>
          Here's where you begin. Every check-in sharpens the picture.
        </Text>

        <SnapshotSection title="What we know" items={whatWeKnow} />
        <SnapshotSection title="What we'll watch" items={whatWeWatch} />
        <SnapshotSection title="What improves accuracy" items={whatImprovesAccuracy} />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Go to Home"
          onPress={handleGoHome}
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
  scroll: {
    flex: 1,
  },
  content: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.lg,
  },
  headline: {
    fontFamily: typography.fonts.serif,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
    marginBottom: spacing.sm,
  },
  subhead: {
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    lineHeight: 20,
    marginBottom: spacing.xxl,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
