/**
 * O9B — Searching Path
 *
 * Elements: short text explanation field, helper text with example.
 */

import React from 'react';
import { View, Text, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { TextField } from '../../components/inputs/TextField';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O9B_SearchingPath'>;

export function O9B_SearchingPath({ navigation }: Props) {
  const {
    searchingExplanation,
    setSearchingExplanation,
    currentStep,
    totalSteps,
  } = useOnboardingStore();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.content}>
          <Text style={styles.headline}>
            Tell us what you're experiencing.
          </Text>

          <TextField
            value={searchingExplanation}
            onChangeText={setSearchingExplanation}
            placeholder="e.g. joint pain, fatigue, brain fog for 6 months"
            multiline
            numberOfLines={4}
          />

          <Text style={styles.helper}>
            A short description is fine. We'll help you track the details over time.
          </Text>

          <View style={styles.spacer} />

          <PrimaryButton
            title="Continue"
            onPress={() => navigation.navigate('O10_BadDayMap')}
            disabled={searchingExplanation.trim().length === 0}
          />
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.bgPrimary,
  },
  flex: {
    flex: 1,
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
  helper: {
    fontSize: typography.sizes.caption,
    color: colors.textTertiary,
    marginTop: spacing.md,
    lineHeight: 18,
  },
  spacer: {
    flex: 1,
  },
});
