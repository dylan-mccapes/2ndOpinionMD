/**
 * O13 — Journaling Value
 *
 * Purpose: explain why journaling matters.
 * Elements: headline, 3 bullet cards, continue CTA, example summary link optional.
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { IntroCard } from '../../components/cards/IntroCard';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { TextButton } from '../../components/buttons/TextButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O13_JournalingValue'>;

export function O13_JournalingValue({ navigation }: Props) {
  const { currentStep, totalSteps } = useOnboardingStore();

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
          Why journaling changes the conversation.
        </Text>

        <IntroCard
          icon="time"
          title="2 seconds a day"
          description="A quick check-in builds a timeline without effort."
          style={styles.card}
        />
        <IntroCard
          icon="trending-up"
          title="Patterns surface"
          description="We connect the dots between triggers, symptoms, and timing."
          style={styles.card}
        />
        <IntroCard
          icon="chatbubbles"
          title="Walk in prepared"
          description="Your clinician sees a structured summary, not a scattered story."
          style={styles.card}
        />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O14_BaselineCommitment')}
        />
        <TextButton
          title="See an example summary"
          onPress={() => {}}
          style={styles.linkButton}
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
    marginBottom: spacing.xxl,
    lineHeight: 32,
  },
  card: {
    marginBottom: spacing.lg,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
  linkButton: {
    alignSelf: 'center',
    marginTop: spacing.sm,
  },
});
