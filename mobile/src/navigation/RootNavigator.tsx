/**
 * 2OPMD Mobile — Root Navigator
 *
 * Stack navigator wrapping:
 *   - Onboarding flow (to be built in Phase 3)
 *   - Main tab navigator
 *   - Settings screen (optional)
 *
 * Auth-gated: shows onboarding if not authenticated, main tabs if authenticated.
 * For now, always shows main tabs (auth wiring in later phase).
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { TabNavigator } from './TabNavigator';
import { colors } from '../theme';

export type RootStackParamList = {
  MainTabs: undefined;
  // Onboarding screens will be added in Phase 3
  // Settings will be added later
};

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bgPrimary },
        animation: 'fade',
      }}
    >
      <Stack.Screen name="MainTabs" component={TabNavigator} />
    </Stack.Navigator>
  );
}
