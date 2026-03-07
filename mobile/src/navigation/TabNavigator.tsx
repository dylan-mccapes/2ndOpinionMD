/**
 * 2OPMD Mobile — Bottom Tab Navigator
 *
 * 4-tab version: Today, Journal, Timeline, Ask.
 * Source: FIGMA_PAGE_STRUCTURE_COMPONENTS.md → Components Checklist → A. Navigation
 * Source: 2opmd_mobile_spellbook.json → screens.main_tabs
 */

import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Ionicons } from '@expo/vector-icons';
import { TodayScreen } from '../screens/TodayScreen';
import { JournalScreen } from '../screens/JournalScreen';
import { TimelineScreen } from '../screens/TimelineScreen';
import { AskScreen } from '../screens/AskScreen';
import { colors, typography, components } from '../theme';

export type MainTabParamList = {
  Today: undefined;
  Journal: undefined;
  Timeline: undefined;
  Ask: undefined;
};

const Tab = createBottomTabNavigator<MainTabParamList>();

function getTabIcon(
  routeName: keyof MainTabParamList,
  focused: boolean,
): keyof typeof Ionicons.glyphMap {
  switch (routeName) {
    case 'Today':
      return focused ? 'pulse' : 'pulse-outline';
    case 'Journal':
      return focused ? 'book' : 'book-outline';
    case 'Timeline':
      return focused ? 'git-branch' : 'git-branch-outline';
    case 'Ask':
      return focused ? 'chatbubble-ellipses' : 'chatbubble-ellipses-outline';
  }
}

export function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused, color, size }) => (
          <Ionicons
            name={getTabIcon(route.name as keyof MainTabParamList, focused)}
            size={size}
            color={color}
          />
        ),
        tabBarActiveTintColor: colors.accentPrimary,
        tabBarInactiveTintColor: colors.textTertiary,
        tabBarStyle: {
          backgroundColor: colors.bgPrimary,
          borderTopColor: colors.separator,
          borderTopWidth: 0.5,
          height: components.bottomNav.height,
          paddingBottom: 20,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: typography.sizes.small,
          fontWeight: typography.weights.medium,
        },
      })}
    >
      <Tab.Screen name="Today" component={TodayScreen} />
      <Tab.Screen name="Journal" component={JournalScreen} />
      <Tab.Screen name="Timeline" component={TimelineScreen} />
      <Tab.Screen name="Ask" component={AskScreen} />
    </Tab.Navigator>
  );
}
