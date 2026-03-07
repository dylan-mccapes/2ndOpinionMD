/**
 * 2OPMD Mobile — Onboarding Navigator
 *
 * Native stack navigator for onboarding flow O1-O17.
 * Branching logic at O8: diagnosed → O9A, searching → O9B,
 * both reconverge at O10.
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { colors } from '../theme';

import { O1_Splash } from '../screens/onboarding/O1_Splash';
import { O2_Welcome } from '../screens/onboarding/O2_Welcome';
import { O3_Promise } from '../screens/onboarding/O3_Promise';
import { O4_Credibility } from '../screens/onboarding/O4_Credibility';
import { O5_Name } from '../screens/onboarding/O5_Name';
import { O6_Age } from '../screens/onboarding/O6_Age';
import { O7_GenderIdentity } from '../screens/onboarding/O7_GenderIdentity';
import { O8_DiagnosedVsSearching } from '../screens/onboarding/O8_DiagnosedVsSearching';
import { O9A_DiagnosedPath } from '../screens/onboarding/O9A_DiagnosedPath';
import { O9B_SearchingPath } from '../screens/onboarding/O9B_SearchingPath';
import { O10_BadDayMap } from '../screens/onboarding/O10_BadDayMap';
import { O11_EmotionalContext } from '../screens/onboarding/O11_EmotionalContext';
import { O12_TopSymptoms } from '../screens/onboarding/O12_TopSymptoms';
import { O13_JournalingValue } from '../screens/onboarding/O13_JournalingValue';
import { O14_BaselineCommitment } from '../screens/onboarding/O14_BaselineCommitment';
import { O15_SaveProgress } from '../screens/onboarding/O15_SaveProgress';
import { O16_OptionalRecords } from '../screens/onboarding/O16_OptionalRecords';
import { O17_StartingSnapshot } from '../screens/onboarding/O17_StartingSnapshot';

export type OnboardingStackParamList = {
  O1_Splash: undefined;
  O2_Welcome: undefined;
  O3_Promise: undefined;
  O4_Credibility: undefined;
  O5_Name: undefined;
  O6_Age: undefined;
  O7_GenderIdentity: undefined;
  O8_DiagnosedVsSearching: undefined;
  O9A_DiagnosedPath: undefined;
  O9B_SearchingPath: undefined;
  O10_BadDayMap: undefined;
  O11_EmotionalContext: undefined;
  O12_TopSymptoms: undefined;
  O13_JournalingValue: undefined;
  O14_BaselineCommitment: undefined;
  O15_SaveProgress: undefined;
  O16_OptionalRecords: undefined;
  O17_StartingSnapshot: undefined;
};

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export function OnboardingNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="O1_Splash"
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.bgPrimary },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="O1_Splash" component={O1_Splash} />
      <Stack.Screen name="O2_Welcome" component={O2_Welcome} />
      <Stack.Screen name="O3_Promise" component={O3_Promise} />
      <Stack.Screen name="O4_Credibility" component={O4_Credibility} />
      <Stack.Screen name="O5_Name" component={O5_Name} />
      <Stack.Screen name="O6_Age" component={O6_Age} />
      <Stack.Screen name="O7_GenderIdentity" component={O7_GenderIdentity} />
      <Stack.Screen name="O8_DiagnosedVsSearching" component={O8_DiagnosedVsSearching} />
      <Stack.Screen name="O9A_DiagnosedPath" component={O9A_DiagnosedPath} />
      <Stack.Screen name="O9B_SearchingPath" component={O9B_SearchingPath} />
      <Stack.Screen name="O10_BadDayMap" component={O10_BadDayMap} />
      <Stack.Screen name="O11_EmotionalContext" component={O11_EmotionalContext} />
      <Stack.Screen name="O12_TopSymptoms" component={O12_TopSymptoms} />
      <Stack.Screen name="O13_JournalingValue" component={O13_JournalingValue} />
      <Stack.Screen name="O14_BaselineCommitment" component={O14_BaselineCommitment} />
      <Stack.Screen name="O15_SaveProgress" component={O15_SaveProgress} />
      <Stack.Screen name="O16_OptionalRecords" component={O16_OptionalRecords} />
      <Stack.Screen name="O17_StartingSnapshot" component={O17_StartingSnapshot} />
    </Stack.Navigator>
  );
}
