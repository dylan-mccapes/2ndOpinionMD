/**
 * O9A — Diagnosed Path
 *
 * Elements: searchable diagnosis field, quick chips, credibility through breadth.
 */

import React, { useState, useMemo, useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { SearchField } from '../../components/inputs/SearchField';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O9A_DiagnosedPath'>;

const COMMON_DIAGNOSES = [
  'Lupus (SLE)',
  'Rheumatoid Arthritis',
  'Multiple Sclerosis',
  'Hashimoto\'s',
  'Crohn\'s Disease',
  'Ulcerative Colitis',
  'Fibromyalgia',
  'Psoriatic Arthritis',
  'Sjogren\'s Syndrome',
  'Celiac Disease',
  'Type 1 Diabetes',
  'Ankylosing Spondylitis',
  'Myasthenia Gravis',
  'Vasculitis',
  'Scleroderma',
];

export function O9A_DiagnosedPath({ navigation }: Props) {
  const { diagnoses, toggleDiagnosis, currentStep, totalSteps, setCurrentStep } = useOnboardingStore();
  useEffect(() => { setCurrentStep(9); }, [setCurrentStep]);
  const [searchQuery, setSearchQuery] = useState('');

  const filteredDiagnoses = useMemo(() => {
    if (!searchQuery.trim()) return COMMON_DIAGNOSES;
    const query = searchQuery.toLowerCase();
    return COMMON_DIAGNOSES.filter((d) => d.toLowerCase().includes(query));
  }, [searchQuery]);

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <Text style={styles.headline}>What have you been diagnosed with?</Text>
        <Text style={styles.subhead}>Select all that apply.</Text>

        <SearchField
          value={searchQuery}
          onChangeText={setSearchQuery}
          placeholder="Search conditions..."
        />

        <ScrollView
          style={styles.chipScroll}
          contentContainerStyle={styles.chipContainer}
          showsVerticalScrollIndicator={false}
        >
          {filteredDiagnoses.map((diagnosis) => {
            const selected = diagnoses.includes(diagnosis);
            return (
              <TouchableOpacity
                key={diagnosis}
                style={[styles.chip, selected && styles.chipSelected]}
                onPress={() => toggleDiagnosis(diagnosis)}
                activeOpacity={0.7}
              >
                <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                  {diagnosis}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O10_BadDayMap')}
          disabled={diagnoses.length === 0}
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
    backgroundColor: colors.accentPrimary,
    borderColor: colors.accentPrimary,
  },
  chipText: {
    fontSize: typography.sizes.label,
    color: colors.textPrimary,
  },
  chipTextSelected: {
    color: colors.bgPrimary,
    fontWeight: typography.weights.semibold,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
