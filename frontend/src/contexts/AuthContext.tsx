import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { authApi, tokenStore, type User } from '../services/api';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Forget the session locally (e.g. after deleting the account). */
  clear: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(() => Boolean(tokenStore.get()));

  const clear = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    if (!tokenStore.get()) return;
    authApi.me()
      .then(setUser)
      .catch(() => clear())
      .finally(() => setIsLoading(false));
  }, [clear]);

  useEffect(() => {
    const onExpired = () => setUser(null);
    window.addEventListener('auth:expired', onExpired);
    return () => window.removeEventListener('auth:expired', onExpired);
  }, []);

  const login = async (email: string, password: string) => {
    const data = await authApi.login(email, password);
    tokenStore.set(data.access_token);
    setUser(data.user);
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch {
      // the token is discarded locally either way
    }
    clear();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, clear }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
