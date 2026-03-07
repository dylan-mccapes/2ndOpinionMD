/**
 * 2OPMD Mobile — Ask Screen
 *
 * Clinical Q&A. ASK mode. SSE stream.
 * When journal entries exist, include context for richer answers.
 *
 * Source: 2opmd_mobile_spellbook.json → screens.main_tabs.Ask
 */

import React, { useState } from 'react';
import { View, Text, ScrollView, StyleSheet, KeyboardAvoidingView, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { TextField } from '../components/inputs/TextField';
import { PrimaryButton } from '../components/buttons/PrimaryButton';
import { EmptyState } from '../components/feedback/EmptyState';
import { colors, typography, spacing } from '../theme';

export function AskScreen() {
  const [question, setQuestion] = useState('');

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <View style={styles.header}>
          <Text style={styles.title}>Ask</Text>
          <Text style={styles.subtitle}>
            Built to support your clinician conversation.
          </Text>
        </View>
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <EmptyState
            icon="chatbubble-ellipses-outline"
            title="Ask a clinical question."
            message="Get evidence-based answers drawn from your timeline and medical literature."
          />
        </ScrollView>
        <View style={styles.inputContainer}>
          <TextField
            value={question}
            onChangeText={setQuestion}
            placeholder="What would you like to know?"
            containerStyle={styles.inputField}
          />
          <PrimaryButton
            title="Ask"
            onPress={() => {}}
            disabled={question.trim().length === 0}
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
  header: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  title: {
    color: colors.textPrimary,
    fontSize: typography.sizes.sectionTitle,
    fontWeight: typography.weights.bold,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: typography.sizes.caption,
    marginTop: spacing.xs,
  },
  scroll: {
    flex: 1,
  },
  content: {
    padding: spacing.screenHorizontal,
    paddingBottom: spacing.xxxl,
  },
  inputContainer: {
    paddingHorizontal: spacing.screenHorizontal,
    paddingBottom: spacing.xxl,
    paddingTop: spacing.md,
    backgroundColor: colors.bgPrimary,
  },
  inputField: {
    marginBottom: spacing.md,
  },
});
