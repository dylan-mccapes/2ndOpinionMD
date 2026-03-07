/**
 * O7 — Gender Identity
 *
 * Elements: female / male / another identity / prefer not to say,
 *           text input shown only if "another identity" selected.
 */

import React, { useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { RadioCardSelector } from '../../components/selectors/RadioCardSelector';
import { TextField } from '../../components/inputs/TextField';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { GenderIdentity } from '../../store/onboardingStore';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O7_GenderIdentity'>;

const GENDER_OPTIONS = [
  { id: 'female', title: 'Female' },
  { id: 'male', title: 'Male' },
  { id: 'another', title: 'Another identity' },
  { id: 'prefer_not_to_say', title: 'Prefer not to say' },
];

export function O7_GenderIdentity({ navigation }: Props) {
  const {
    genderIdentity,
    genderIdentityCustom,
    setGenderIdentity,
    setGenderIdentityCustom,
    currentStep,
    totalSteps,
    setCurrentStep,
  } = useOnboardingStore();
  useEffect(() => { setCurrentStep(7); }, [setCurrentStep]);

  const canContinue =
    genderIdentity !== null &&
    (genderIdentity !== 'another' || genderIdentityCustom.trim().length > 0);

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
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <Text style={styles.headline}>How do you identify?</Text>

          <RadioCardSelector
            options={GENDER_OPTIONS}
            selectedId={genderIdentity}
            onSelect={(id) => setGenderIdentity(id as GenderIdentity)}
          />

          {genderIdentity === 'another' && (
            <View style={styles.customInput}>
              <TextField
                value={genderIdentityCustom}
                onChangeText={setGenderIdentityCustom}
                placeholder="How you identify"
                autoFocus
              />
            </View>
          )}
        </ScrollView>
        <View style={styles.ctaContainer}>
          <PrimaryButton
            title="Continue"
            onPress={() => navigation.navigate('O8_DiagnosedVsSearching')}
            disabled={!canContinue}
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
  scroll: {
    flex: 1,
  },
  content: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingTop: spacing.xxxl,
    paddingBottom: spacing.lg,
  },
  headline: {
    fontFamily: typography.fonts.serif,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
    marginBottom: spacing.xxl,
  },
  customInput: {
    marginTop: spacing.lg,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
