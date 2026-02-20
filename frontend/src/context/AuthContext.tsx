import { createContext, useContext, useState, type ReactNode } from 'react';

interface AuthContextValue {
  token: string | null;
  setToken: (t: string | null) => void;
  isAuthenticated: boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function getStoredToken(): string | null {
  return sessionStorage.getItem('2opmd-token');
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getStoredToken);

  const setToken = (t: string | null) => {
    if (t) {
      sessionStorage.setItem('2opmd-token', t);
    } else {
      sessionStorage.removeItem('2opmd-token');
    }
    setTokenState(t);
  };

  const logout = () => setToken(null);

  return (
    <AuthContext.Provider
      value={{ token, setToken, isAuthenticated: token !== null, logout }}
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
