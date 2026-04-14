import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { apiFetch, authHeaders } from '../lib/api';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  birthdate: string | null;
  subscription_tier: string;
  user_type: 'patient' | 'doctor';
  created_at: string;
}

interface AuthContextValue {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setToken: (t: string | null) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const DEV_BYPASS = import.meta.env.VITE_DEV_BYPASS_AUTH === 'true';
const DEV_USER_TYPE = (import.meta.env.VITE_DEV_USER_TYPE ?? 'patient').toLowerCase() === 'doctor'
  ? 'doctor'
  : 'patient';

const DEV_USER: UserProfile = {
  id: DEV_USER_TYPE === 'doctor' ? 'dr-house-mock' : 'user-norman-dev',
  email: DEV_USER_TYPE === 'doctor' ? 'house@ppth.dev' : 'dev@local',
  full_name: DEV_USER_TYPE === 'doctor' ? 'Gregory House' : 'Norman Eric Roberts',
  birthdate: null,
  subscription_tier: 'pro',
  user_type: DEV_USER_TYPE,
  created_at: new Date().toISOString(),
};

function getStoredToken(): string | null {
  if (DEV_BYPASS) return 'dev-bypass';
  return sessionStorage.getItem('2opmd-token');
}

export function AuthProvider({ children }: { children: ReactNode }) {
  if (DEV_BYPASS) {
    return (
      <AuthContext.Provider
        value={{
          token: 'dev-bypass',
          user: DEV_USER,
          isAuthenticated: true,
          isLoading: false,
          setToken: () => {},
          logout: () => {},
          refreshUser: async () => {},
        }}
      >
        {children}
      </AuthContext.Provider>
    );
  }

  return <AuthProviderReal>{children}</AuthProviderReal>;
}

function AuthProviderReal({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getStoredToken);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(!!getStoredToken());

  const setToken = (t: string | null) => {
    if (t) {
      sessionStorage.setItem('2opmd-token', t);
    } else {
      sessionStorage.removeItem('2opmd-token');
    }
    setTokenState(t);
    if (!t) {
      setUser(null);
    }
  };

  const logout = () => setToken(null);

  const refreshUser = useCallback(async () => {
    const currentToken = getStoredToken();
    if (!currentToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }
    try {
      const profile = await apiFetch<UserProfile>('/api/auth/me', {
        headers: authHeaders(currentToken),
      });
      setUser(profile);
    } catch {
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      refreshUser();
    } else {
      setIsLoading(false);
    }
  }, [token, refreshUser]);

  return (
    <AuthContext.Provider
      value={{ token, user, isAuthenticated: token !== null, isLoading, setToken, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
