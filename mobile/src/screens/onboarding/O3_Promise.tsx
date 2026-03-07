/**
 * O3 — Promise
 *
 * Purpose: show what happens when they use it.
 * Elements: 3 compact cards, one-line subhead, continue CTA, how-it-works link.
 */

import React, { useEffect } from 'react';
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

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O3_Promise'>;

export function O3_Promise({ navigation }: Props) {
  const { currentStep, totalSteps, setCurrentStep } = useOnboardingStore();
  useEffect(() => { setCurrentStep(3); }, [setCurrentStep]);

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
        <Text style={styles.subhead}>Here's what happens when you use 2OPMD</Text>

        <IntroCard
          icon="pulse"
          title="Track what matters"
          description="2-second daily check-ins build a timeline your doctor can actually use."
          style={styles.card}
        />
        <IntroCard
          icon="analytics"
          title="See patterns emerge"
          description="We watch for connections between symptoms, triggers, and timing."
          style={styles.card}
        />
        <IntroCard
          icon="document-text"
          title="Prepare for your visit"
          description="Walk in with a clear summary, not a scattered memory."
          style={styles.card}
        />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O4_Credibility')}
        />
        <TextButton
          title="How does it work?"
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
  subhead: {
    fontSize: typography.sizes.body,
    color: colors.textSecondary,
    marginBottom: spacing.xxl,
    lineHeight: 24,
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
