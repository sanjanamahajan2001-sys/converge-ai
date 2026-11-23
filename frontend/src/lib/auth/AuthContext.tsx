import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { UserIdentityResponse, UserLoginRequest, UserRegisterRequest, UserRegisterResponse } from '@/types/auth';
import { getCurrentUser, loginUser, logoutUser, registerUser } from '@/lib/api/auth';
import { ApiClientError } from '@/lib/api/client';
import { useQueryClient } from '@tanstack/react-query';

interface AuthContextType {
  user: UserIdentityResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: UserLoginRequest) => Promise<void>;
  register: (payload: UserRegisterRequest) => Promise<UserRegisterResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserIdentityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const queryClient = useQueryClient();

  const fetchSessionUser = useCallback(async () => {
    try {
      const identity = await getCurrentUser();
      setUser(identity);
    } catch (err) {
      if (err instanceof ApiClientError && err.status === 401) {
        // Expected when no active session cookie exists
        setUser(null);
      } else {
        setUser(null);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessionUser();
  }, [fetchSessionUser]);

  const login = async (credentials: UserLoginRequest): Promise<void> => {
    setIsLoading(true);
    try {
      await loginUser(credentials);
      const identity = await getCurrentUser();
      setUser(identity);
      await queryClient.invalidateQueries();
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: UserRegisterRequest): Promise<UserRegisterResponse> => {
    return await registerUser(payload);
  };

  const logout = async (): Promise<void> => {
    try {
      await logoutUser();
    } catch {
      // Even if network or server errors occur during logout, clear frontend session state
    } finally {
      setUser(null);
      queryClient.clear();
    }
  };

  const refreshUser = async (): Promise<void> => {
    await fetchSessionUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

const defaultAuthContext: AuthContextType = {
  user: null,
  isAuthenticated: false,
  isLoading: false,
  login: async () => {},
  register: async () => ({} as any),
  logout: async () => {},
  refreshUser: async () => {},
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  return context || defaultAuthContext;
}
