/**
 * O4 — Credibility
 *
 * Purpose: establish that this is more than a tracker.
 * Elements: headline, 2 proof tiles, optional learn-more link.
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

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O4_Credibility'>;

export function O4_Credibility({ navigation }: Props) {
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
          More than a symptom tracker.
        </Text>

        <IntroCard
          icon="medical"
          title="Built on real clinical data"
          description="75,000+ medical codes. Guidelines from NICE, CDC, ACR, and EULAR. Pattern detection grounded in evidence."
          style={styles.card}
        />
        <IntroCard
          icon="shield-checkmark"
          title="Designed for your clinician"
          description="Everything you track is structured to support a real medical conversation."
          style={styles.card}
        />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O5_Name')}
        />
        <TextButton
          title="Learn more"
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
