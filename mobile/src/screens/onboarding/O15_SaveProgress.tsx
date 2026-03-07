/**
 * O15 — Save Progress
 *
 * Elements: Apple / Google / Email options, privacy line.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { SecondaryButton } from '../../components/buttons/SecondaryButton';
import { TrustCard } from '../../components/cards/TrustCard';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O15_SaveProgress'>;

export function O15_SaveProgress({ navigation }: Props) {
  const { currentStep, totalSteps } = useOnboardingStore();

  const handleSave = () => {
    // Defer actual auth to Phase 4 — navigate forward
    navigation.navigate('O16_OptionalRecords');
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <Text style={styles.headline}>Save your progress.</Text>
        <Text style={styles.subhead}>
          Create an account so your data is safe and ready when you come back.
        </Text>

        <View style={styles.optionsContainer}>
          <TouchableOpacity style={styles.socialButton} onPress={handleSave} activeOpacity={0.8}>
            <Text style={styles.socialIcon}>🍎</Text>
            <Text style={styles.socialText}>Continue with Apple</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.socialButton} onPress={handleSave} activeOpacity={0.8}>
            <Text style={styles.socialIcon}>G</Text>
            <Text style={styles.socialText}>Continue with Google</Text>
          </TouchableOpacity>

          <SecondaryButton
            title="Continue with Email"
            onPress={handleSave}
          />
        </View>

        <View style={styles.spacer} />

        <TrustCard text="We never sell your data. Your health information stays private." />
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
    paddingTop: spacing.xxxl,
    paddingBottom: spacing.xxl,
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
    marginBottom: spacing.xxxl,
  },
  optionsContainer: {
    gap: spacing.md,
  },
  socialButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bgSurface,
    borderRadius: radius.md,
    paddingVertical: spacing.lg,
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.separator,
  },
  socialIcon: {
    fontSize: 20,
  },
  socialText: {
    fontSize: typography.sizes.button,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  spacer: {
    flex: 1,
  },
});
