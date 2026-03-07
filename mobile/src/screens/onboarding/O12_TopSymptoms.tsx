/**
 * O12 — Top Symptoms
 *
 * Elements: search, chips, selected state.
 */

import React, { useState, useMemo } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { SearchField } from '../../components/inputs/SearchField';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O12_TopSymptoms'>;

const COMMON_SYMPTOMS = [
  'Fatigue',
  'Joint pain',
  'Brain fog',
  'Muscle aches',
  'Headaches',
  'Insomnia',
  'Skin rashes',
  'Digestive issues',
  'Numbness / tingling',
  'Swelling',
  'Dry eyes / mouth',
  'Hair loss',
  'Light sensitivity',
  'Chest tightness',
  'Shortness of breath',
  'Weight changes',
  'Fever / chills',
  'Dizziness',
  'Mouth sores',
  'Stiffness',
];

export function O12_TopSymptoms({ navigation }: Props) {
  const { selectedSymptoms, toggleSymptom, currentStep, totalSteps } = useOnboardingStore();
  const [searchQuery, setSearchQuery] = useState('');

  const filteredSymptoms = useMemo(() => {
    if (!searchQuery.trim()) return COMMON_SYMPTOMS;
    const query = searchQuery.toLowerCase();
    return COMMON_SYMPTOMS.filter((s) => s.toLowerCase().includes(query));
  }, [searchQuery]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <Text style={styles.headline}>
          What are your top symptoms?
        </Text>
        <Text style={styles.subhead}>
          Select the ones you experience most often.
        </Text>

        <SearchField
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search symptoms..."
        />

        <ScrollView
          style={styles.chipScroll}
          contentContainerStyle={styles.chipContainer}
          showsVerticalScrollIndicator={false}
        >
          {filteredSymptoms.map((symptom) => {
            const selected = selectedSymptoms.includes(symptom);
            return (
              <TouchableOpacity
                key={symptom}
                style={[styles.chip, selected && styles.chipSelected]}
                onPress={() => toggleSymptom(symptom)}
                activeOpacity={0.7}
              >
                <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                  {symptom}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {selectedSymptoms.length > 0 && (
          <Text style={styles.selectedCount}>
            {selectedSymptoms.length} selected
          </Text>
        )}
      </View>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O13_JournalingValue')}
          disabled={selectedSymptoms.length === 0}
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
    paddingTop: spacing.xxl,
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
    marginBottom: spacing.lg,
  },
  chipScroll: {
    flex: 1,
    marginTop: spacing.lg,
  },
  chipContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    paddingBottom: spacing.lg,
  },
  chip: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderWidth: 1,
    borderColor: colors.separator,
  },
  chipSelected: {
    backgroundColor: colors.accentGreen,
    borderColor: colors.accentGreen,
  },
  chipText: {
    fontSize: typography.sizes.label,
    color: colors.textPrimary,
  },
  chipTextSelected: {
    color: colors.bgPrimary,
    fontWeight: typography.weights.semibold,
  },
  selectedCount: {
    fontSize: typography.sizes.caption,
    color: colors.textSecondary,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
