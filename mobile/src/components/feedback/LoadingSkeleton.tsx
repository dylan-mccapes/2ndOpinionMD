/**
 * 2OPMD Mobile — Loading Skeleton
 *
 * Placeholder shimmer for content loading.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → M. Feedback States
 */

import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet, ViewStyle } from 'react-native';
import { colors, spacing, radius } from '../../theme';

interface LoadingSkeletonProps {
  width?: number | string;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
}

export function LoadingSkeleton({
  width = '100%',
  height = 16,
  borderRadius = radius.sm,
  style,
}: LoadingSkeletonProps) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const animation = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 0.7,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.3,
          duration: 800,
          useNativeDriver: true,
        }),
      ]),
    );
    animation.start();
    return () => animation.stop();
  }, [opacity]);

  return (
    <Animated.View
      style={[
        styles.skeleton,
        {
          width: width as number,
          height,
          borderRadius,
          opacity,
        },
        style,
      ]}
    />
  );
}

interface CardSkeletonProps {
  style?: ViewStyle;
}

export function CardSkeleton({ style }: CardSkeletonProps) {
  return (
    <View style={[styles.cardContainer, style]}>
      <LoadingSkeleton height={14} width="40%" style={{ marginBottom: spacing.sm }} />
      <LoadingSkeleton height={20} width="70%" style={{ marginBottom: spacing.md }} />
      <LoadingSkeleton height={12} width="90%" />
    </View>
  );
}

const styles = StyleSheet.create({
  skeleton: {
    backgroundColor: colors.bgElevated,
  },
  cardContainer: {
    backgroundColor: colors.bgSurface,
    borderRadius: radius.lg,
    padding: spacing.xl,
    borderWidth: 1,
    borderColor: colors.separator,
  },
});
