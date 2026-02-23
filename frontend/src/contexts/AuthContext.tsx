import React, { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '@/services/api';
import type { CurrentUser } from '@/types';

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  refetch: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  refetch: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    try {
      const data = await authApi.getMe();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refetch: fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useRequireRole(minRole: string): boolean {
  const { user } = useAuth();
  const hierarchy = ['developer', 'reviewer', 'release_manager', 'admin'];
  if (!user) return false;
  return hierarchy.indexOf(user.role) >= hierarchy.indexOf(minRole);
}
