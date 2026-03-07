/**
 * O5 — Name
 *
 * Elements: text field, continue.
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { TextField } from '../../components/inputs/TextField';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O5_Name'>;

export function O5_Name({ navigation }: Props) {
  const { name, setName, currentStep, totalSteps, setCurrentStep } = useOnboardingStore();
  useEffect(() => { setCurrentStep(5); }, [setCurrentStep]);

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
          <Text style={styles.headline}>What should we call you?</Text>

          <TextField
            value={name}
            onChangeText={setName}
            placeholder="First name"
            autoCapitalize="words"
            autoFocus
            returnKeyType="done"
          />

          <View style={styles.spacer} />

          <PrimaryButton
            title="Continue"
            onPress={() => navigation.navigate('O6_Age')}
            disabled={name.trim().length === 0}
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
  spacer: {
    flex: 1,
  },
});
