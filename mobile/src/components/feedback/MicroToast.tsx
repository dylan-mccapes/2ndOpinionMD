/**
 * 2OPMD Mobile — Save Confirmation Micro-Toast
 *
 * Subtle fade-in/out toast for save confirmations.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → H. Check-in System
 * Motion: save confirmation toast fade.
 */

import React, { useEffect, useRef } from 'react';
import { Animated, Text, StyleSheet, ViewStyle } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors, typography, spacing, radius } from '../../theme';

interface MicroToastProps {
  message: string;
  visible: boolean;
  duration?: number;
  onDismiss?: () => void;
  style?: ViewStyle;
}

export function MicroToast({
  message,
  visible,
  duration = 2000,
  onDismiss,
  style,
}: MicroToastProps) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(20)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(translateY, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start();

      const timer = setTimeout(() => {
        Animated.parallel([
          Animated.timing(opacity, {
            toValue: 0,
            duration: 250,
            useNativeDriver: true,
          }),
          Animated.timing(translateY, {
            toValue: 20,
            duration: 250,
            useNativeDriver: true,
          }),
        ]).start(() => onDismiss?.());
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [visible, duration, onDismiss, opacity, translateY]);

  if (!visible) return null;

  return (
    <Animated.View
      style={[
        styles.container,
        { opacity, transform: [{ translateY }] },
        style,
      ]}
    >
      <Ionicons name="checkmark-circle" size={18} color={colors.accentGreen} />
      <Text style={styles.text}>{message}</Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 100,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.bgElevated,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.pill,
    gap: spacing.sm,
  },
  text: {
    color: colors.textPrimary,
    fontSize: typography.sizes.caption,
    fontWeight: typography.weights.medium,
  },
});
