/**
 * O11 — Emotional Context
 *
 * Purpose: capture mental / emotional signal as context.
 * Elements: bubble selection field, choose up to 5, clinical framing copy.
 */

import React, { useEffect } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O11_EmotionalContext'>;

const EMOTIONS = [
  'Exhausted',
  'Frustrated',
  'Anxious',
  'Hopeful',
  'Foggy',
  'Irritable',
  'Calm',
  'Overwhelmed',
  'Resigned',
  'Determined',
  'Grateful',
  'Isolated',
  'Numb',
  'Restless',
  'Sad',
  'Relieved',
];

export function O11_EmotionalContext({ navigation }: Props) {
  const { selectedEmotions, toggleEmotion, currentStep, totalSteps, setCurrentStep } = useOnboardingStore();
  useEffect(() => { setCurrentStep(11); }, [setCurrentStep]);

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
          How have you been feeling emotionally?
        </Text>
        <Text style={styles.subhead}>
          Choose up to 5. Emotional context helps us detect patterns between mind and body.
        </Text>

        <View style={styles.bubbleContainer}>
          {EMOTIONS.map((emotion) => {
            const selected = selectedEmotions.includes(emotion);
            const atLimit = selectedEmotions.length >= 5 && !selected;
            return (
              <TouchableOpacity
                key={emotion}
                style={[
                  styles.bubble,
                  selected && styles.bubbleSelected,
                  atLimit && styles.bubbleDisabled,
                ]}
                onPress={() => toggleEmotion(emotion)}
                activeOpacity={0.7}
                disabled={atLimit}
              >
                <Text
                  style={[
                    styles.bubbleText,
                    selected && styles.bubbleTextSelected,
                    atLimit && styles.bubbleTextDisabled,
                  ]}
                >
                  {emotion}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.clinicalNote}>
          Emotional data is used as clinical context — not as a mood tracker.
        </Text>
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O12_TopSymptoms')}
          disabled={selectedEmotions.length === 0}
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
    marginBottom: spacing.sm,
  },
  subhead: {
    fontSize: typography.sizes.label,
    color: colors.textSecondary,
    lineHeight: 20,
    marginBottom: spacing.xxl,
  },
  bubbleContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.xxl,
  },
  bubble: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radius.pill,
    backgroundColor: colors.bgSurface,
    borderWidth: 1,
    borderColor: colors.separator,
  },
  bubbleSelected: {
    backgroundColor: colors.emotionCool,
    borderColor: colors.emotionCool,
  },
  bubbleDisabled: {
    opacity: 0.4,
  },
  bubbleText: {
    fontSize: typography.sizes.label,
    color: colors.textPrimary,
  },
  bubbleTextSelected: {
    color: colors.bgPrimary,
    fontWeight: typography.weights.semibold,
  },
  bubbleTextDisabled: {
    color: colors.textTertiary,
  },
  clinicalNote: {
    fontSize: typography.sizes.caption,
    color: colors.textTertiary,
    fontStyle: 'italic',
    textAlign: 'center',
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
