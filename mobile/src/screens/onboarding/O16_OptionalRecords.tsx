/**
 * O16 — Optional Records
 *
 * Elements: upload PDF, upload image, skip for now.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { TextButton } from '../../components/buttons/TextButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O16_OptionalRecords'>;

export function O16_OptionalRecords({ navigation }: Props) {
  const { currentStep, totalSteps, setHasUploadedRecords } = useOnboardingStore();

  const handleUpload = () => {
    // Defer actual upload to Phase 4 — mark as attempted
    setHasUploadedRecords(true);
    navigation.navigate('O17_StartingSnapshot');
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <TopAppBar
        showBack
        onBack={() => navigation.goBack()}
        progress={{ current: currentStep, total: totalSteps }}
      />
      <View style={styles.content}>
        <Text style={styles.headline}>
          Have medical records to share?
        </Text>
        <Text style={styles.subhead}>
          Uploading records helps us build a more complete picture. You can always do this later.
        </Text>

        <TouchableOpacity
          style={styles.uploadCard}
          onPress={handleUpload}
          activeOpacity={0.8}
        >
          <Text style={styles.uploadIcon}>📄</Text>
          <Text style={styles.uploadTitle}>Upload PDF</Text>
          <Text style={styles.uploadDescription}>
            Lab results, visit summaries, or discharge notes.
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.uploadCard}
          onPress={handleUpload}
          activeOpacity={0.8}
        >
          <Text style={styles.uploadIcon}>📷</Text>
          <Text style={styles.uploadTitle}>Upload Image</Text>
          <Text style={styles.uploadDescription}>
            Photos of prescriptions, test results, or notes.
          </Text>
        </TouchableOpacity>

        <View style={styles.spacer} />

        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O17_StartingSnapshot')}
        />
        <TextButton
          title="Skip for now"
          onPress={() => navigation.navigate('O17_StartingSnapshot')}
          style={styles.skipButton}
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
    marginBottom: spacing.xxl,
  },
  uploadCard: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xxl,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.separator,
    borderStyle: 'dashed',
  },
  uploadIcon: {
    fontSize: 28,
    marginBottom: spacing.md,
  },
  uploadTitle: {
    fontSize: typography.sizes.body,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
    marginBottom: spacing.xs,
  },
  uploadDescription: {
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    lineHeight: 20,
  },
  spacer: {
    flex: 1,
  },
  skipButton: {
    alignSelf: 'center',
    marginTop: spacing.md,
  },
});
