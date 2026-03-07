/**
 * O1 — Splash
 *
 * Purpose: create premium first impression.
 * Elements: off-white background, centered Great Oak symbol, no text,
 *           subtle heartbeat / pulse motion.
 */

import React, { useEffect, useRef } from 'react';
import { View, Animated, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../../navigation/OnboardingNavigator';
import { colors } from '../../theme';

type Props = NativeStackScreenProps<OnboardingStackParamList, 'O1_Splash'>;

export function O1_Splash({ navigation }: Props) {
  const scale = useRef(new Animated.Value(1)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // Fade in
    Animated.timing(opacity, {
      toValue: 1,
      duration: 600,
      useNativeDriver: true,
    }).start();

    // Subtle heartbeat pulse
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(scale, {
          toValue: 1.05,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(scale, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();

    // Auto-advance after 2.5s
    const timer = setTimeout(() => {
      navigation.replace('O2_Welcome');
    }, 2500);

    return () => {
      pulse.stop();
      clearTimeout(timer);
    };
  }, [navigation, scale, opacity]);

  return (
    <View style={styles.container}>
      <Animated.Text
        style={[styles.oak, { opacity, transform: [{ scale }] }]}
      >
        🌳
      </Animated.Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.offWhite,
    alignItems: 'center',
    justifyContent: 'center',
  },
  oak: {
    fontSize: 80,
  },
});
