/**
 * 2OPMD Mobile — Auth Store (Zustand)
 *
 * Manages JWT token and user state.
 * Token persisted in expo-secure-store.
 */

import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = '2opmd_jwt_token';
const ONBOARDING_KEY = '2opmd_onboarding_complete';

interface User {
  id: string;
  email: string;
  user_type: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  hasCompletedOnboarding: boolean;

  setToken: (token: string) => Promise<void>;
  clearToken: () => Promise<void>;
  loadToken: () => Promise<void>;
  setUser: (user: User) => void;
  clearUser: () => void;
  completeOnboarding: () => Promise<void>;
  loadOnboardingStatus: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isLoading: true,
  isAuthenticated: false,
  hasCompletedOnboarding: false,

  setToken: async (token: string) => {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    set({ token, isAuthenticated: true });
  },

  clearToken: async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    set({ token: null, user: null, isAuthenticated: false });
  },

  loadToken: async () => {
    try {
      const token = await SecureStore.getItemAsync(TOKEN_KEY);
      set({
        token,
        isAuthenticated: !!token,
        isLoading: false,
      });
    } catch {
      set({ token: null, isAuthenticated: false, isLoading: false });
    }
  },

  setUser: (user: User) => set({ user }),
  clearUser: () => set({ user: null }),

  completeOnboarding: async () => {
    await SecureStore.setItemAsync(ONBOARDING_KEY, 'true');
    set({ hasCompletedOnboarding: true });
  },

  loadOnboardingStatus: async () => {
    try {
      const value = await SecureStore.getItemAsync(ONBOARDING_KEY);
      set({ hasCompletedOnboarding: value === 'true' });
    } catch {
      set({ hasCompletedOnboarding: false });
    }
  },
}));
