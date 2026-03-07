/**
 * O2 — Welcome
 *
 * Purpose: instantly call out the ICP.
 * Elements: small oak mark top center, headline, subhead, primary CTA,
 *           secondary login link, micro trust line.
 * Copy: "Chronic symptoms deserve clarity."
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { PrimaryButton } from '../../components/buttons/PrimaryButton';
import { TextButton } from '../../components/buttons/TextButton';
import { TrustCard } from '../../components/cards/TrustCard';
import { colors, typography, spacing } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O2_Welcome'>;

export function O2_Welcome({ navigation }: Props) {
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.content}>
        {/* Oak mark */}
        <Text style={styles.oakMark}>🌳</Text>

        {/* Headline */}
        <Text style={styles.headline}>
          Chronic symptoms{'\n'}deserve clarity.
        </Text>

        {/* Subhead */}
        <Text style={styles.subhead}>
          For autoimmune, chronic illness, and anyone still searching for answers.
        </Text>

        <View style={styles.spacer} />

        {/* Primary CTA */}
        <PrimaryButton
          title="Get Started"
          onPress={() => navigation.navigate('O3_Promise')}
        />

        {/* Secondary login link */}
        <TextButton
          title="I already have an account"
          onPress={() => {}}
          style={styles.loginLink}
        />

        {/* Micro trust line */}
        <TrustCard text="Your data stays yours. Always." />
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
  oakMark: {
    fontSize: 36,
    textAlign: 'center',
    marginBottom: spacing.xxxl,
  },
  headline: {
    fontFamily: typography.fonts.serif,
    fontSize: typography.sizes.headline,
    fontWeight: typography.weights.bold,
    color: colors.textPrimary,
    textAlign: 'center',
    lineHeight: 38,
  },
  subhead: {
    fontSize: typography.sizes.body,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: spacing.lg,
    lineHeight: 24,
    paddingHorizontal: spacing.lg,
  },
  spacer: {
    flex: 1,
  },
  loginLink: {
    alignSelf: 'center',
    marginTop: spacing.md,
  },
});
