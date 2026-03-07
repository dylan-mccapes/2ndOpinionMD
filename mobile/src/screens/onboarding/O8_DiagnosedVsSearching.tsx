/**
 * O8 — Diagnosed vs Searching
 *
 * Elements: two large cards, one CTA, minimal explanatory copy.
 * Branching: diagnosed → O9A, searching → O9B.
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { UserPath } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O8_DiagnosedVsSearching'>;

export function O8_DiagnosedVsSearching({ navigation }: Props) {
  const { userPath, setUserPath, currentStep, totalSteps, setCurrentStep } = useOnboardingStore();
  useEffect(() => { setCurrentStep(8); }, [setCurrentStep]);

  const handleContinue = () => {
    if (userPath === 'diagnosed') {
      navigation.navigate('O9A_DiagnosedPath');
    } else if (userPath === 'searching') {
      navigation.navigate('O9B_SearchingPath');
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <Text style={styles.headline}>Which describes you best?</Text>

        <TouchableOpacity
          style={[styles.pathCard, userPath === 'diagnosed' && styles.pathCardSelected]}
          onPress={() => setUserPath('diagnosed')}
          activeOpacity={0.8}
        >
          <Text style={styles.pathIcon}>🔬</Text>
          <Text style={styles.pathTitle}>I have a diagnosis</Text>
          <Text style={styles.pathDescription}>
            I've been diagnosed with an autoimmune or chronic condition.
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.pathCard, userPath === 'searching' && styles.pathCardSelected]}
          onPress={() => setUserPath('searching')}
          activeOpacity={0.8}
        >
          <Text style={styles.pathIcon}>🔍</Text>
          <Text style={styles.pathTitle}>I'm still searching</Text>
          <Text style={styles.pathDescription}>
            I have symptoms but no clear diagnosis yet.
          </Text>
        </TouchableOpacity>

        <View style={styles.spacer} />

        <PrimaryButton
          title="Continue"
          onPress={handleContinue}
          disabled={!userPath}
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
    paddingTop: spacing.xxxl,
    paddingBottom: spacing.xxl,
  },
  headline: {
    fontFamily: typography.fonts.serif,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
    marginBottom: spacing.xxl,
  },
  pathCard: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xxl,
    marginBottom: spacing.lg,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  pathCardSelected: {
    borderColor: colors.accentPrimary,
  },
  pathIcon: {
    fontSize: 32,
    marginBottom: spacing.md,
  },
  pathTitle: {
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  pathDescription: {
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  spacer: {
    flex: 1,
  },
});
