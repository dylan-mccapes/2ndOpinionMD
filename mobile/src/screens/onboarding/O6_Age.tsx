/**
 * O6 — Age
 *
 * Elements: age range cards / radio rows, continue.
 */

import React from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { RadioCardSelector } from '../../components/selectors/RadioCardSelector';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O6_Age'>;

const AGE_OPTIONS = [
  { id: '18-24', title: '18–24' },
  { id: '25-34', title: '25–34' },
  { id: '35-44', title: '35–44' },
  { id: '45-54', title: '45–54' },
  { id: '55-64', title: '55–64' },
  { id: '65+', title: '65+' },
];

export function O6_Age({ navigation }: Props) {
  const { ageRange, setAgeRange, currentStep, totalSteps } = useOnboardingStore();

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
        <Text style={styles.headline}>How old are you?</Text>

        <RadioCardSelector
          options={AGE_OPTIONS}
          selectedId={ageRange}
          onSelect={setAgeRange}
        />
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O7_GenderIdentity')}
          disabled={!ageRange}
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
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
