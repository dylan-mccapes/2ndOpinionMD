/**
 * O10 — 30-Day Bad-Day Map
 *
 * Purpose: serious interaction that creates immediate signal.
 * Elements: month grid, severity legend, "estimate is fine" helper copy,
 *           counters, continue CTA.
 */

import React, { useMemo } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { TopAppBar } from '../../components/navigation/TopAppBar';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { useOnboardingStore, SeverityLevel } from '../../store/onboardingStore';
import { colors, typography, spacing, radius } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O10_BadDayMap'>;

const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  mild: colors.severityMild,
  moderate: colors.severityModerate,
  severe: colors.severitySevere,
  flare: colors.severityFlare,
};

const SEVERITY_LABELS: { key: SeverityLevel; label: string }[] = [
  { key: 'mild', label: 'Mild' },
  { key: 'moderate', label: 'Moderate' },
  { key: 'severe', label: 'Severe' },
  { key: 'flare', label: 'Flare' },
];

export function O10_BadDayMap({ navigation }: Props) {
  const { dayMap, setDaySeverity, currentStep, totalSteps } = useOnboardingStore();
  const [activeSeverity, setActiveSeverity] = React.useState<SeverityLevel>('moderate');

  const counters = useMemo(() => {
    const counts: Record<SeverityLevel, number> = { mild: 0, moderate: 0, severe: 0, flare: 0 };
    dayMap.forEach((entry) => {
      if (entry.severity) counts[entry.severity]++;
    });
    return counts;
  }, [dayMap]);

  const markedDays = dayMap.filter((d) => d.severity !== null).length;

  const handleDayPress = (day: number) => {
    const current = dayMap.find((d) => d.day === day);
    if (current?.severity === activeSeverity) {
      setDaySeverity(day, null);
    } else {
      setDaySeverity(day, activeSeverity);
    }
  };

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
          Map your last 30 days.
        </Text>
        <Text style={styles.subhead}>
          Tap a severity below, then tap the days that match. An estimate is fine.
        </Text>

        {/* Severity selector */}
        <View style={styles.severityRow}>
          {SEVERITY_LABELS.map(({ key, label }) => (
            <TouchableOpacity
              key={key}
              style={[
                styles.severityButton,
                { borderColor: SEVERITY_COLORS[key] },
                activeSeverity === key && { backgroundColor: SEVERITY_COLORS[key] },
              ]}
              onPress={() => setActiveSeverity(key)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.severityButtonText,
                  activeSeverity === key && styles.severityButtonTextActive,
                ]}
              >
                {label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Month grid */}
        <View style={styles.grid}>
          {dayMap.map((entry) => {
            const severity = entry.severity;
            const bgColor = severity ? SEVERITY_COLORS[severity] : colors.bgSurface;
            return (
              <TouchableOpacity
                key={entry.day}
                style={[styles.dayCell, { backgroundColor: bgColor }]}
                onPress={() => handleDayPress(entry.day)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.dayText,
                    severity ? styles.dayTextMarked : null,
                  ]}
                >
                  {entry.day}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Counters */}
        <View style={styles.counterRow}>
          {SEVERITY_LABELS.map(({ key, label }) => (
            <View key={key} style={styles.counter}>
              <View style={[styles.counterDot, { backgroundColor: SEVERITY_COLORS[key] }]} />
              <Text style={styles.counterLabel}>{label}</Text>
              <Text style={styles.counterValue}>{counters[key]}</Text>
            </View>
          ))}
        </View>
      </ScrollView>
      <View style={styles.ctaContainer}>
        <PrimaryButton
          title="Continue"
          onPress={() => navigation.navigate('O11_EmotionalContext')}
          disabled={markedDays === 0}
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
  severityRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.xxl,
  },
  severityButton: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 2,
    alignItems: 'center',
  },
  severityButtonText: {
    fontSize: typography.sizes.small,
    fontWeight: typography.weights.semibold,
    color: colors.textPrimary,
  },
  severityButtonTextActive: {
    color: colors.bgPrimary,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginBottom: spacing.xxl,
  },
  dayCell: {
    width: 40,
    height: 40,
    borderRadius: radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayText: {
    fontSize: typography.sizes.small,
    color: colors.textSecondary,
    fontWeight: typography.weights.medium,
  },
  dayTextMarked: {
    color: colors.bgPrimary,
    fontWeight: typography.weights.bold,
  },
  counterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  counter: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  counterDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  counterLabel: {
    fontSize: typography.sizes.small,
    color: colors.textSecondary,
  },
  counterValue: {
    fontSize: typography.sizes.small,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
  },
  ctaContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
  },
});
