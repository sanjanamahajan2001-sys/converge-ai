import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { UserIdentityResponse, UserLoginRequest } from '@/types/auth';
import { adminLogin as apiAdminLogin, adminLogout as apiAdminLogout, getAdminMe } from '@/lib/api/admin';
import { useQueryClient } from '@tanstack/react-query';

interface AdminAuthContextType {
  adminUser: UserIdentityResponse | null;
  isAdminAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: UserLoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshAdmin: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

export const AdminAuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [adminUser, setAdminUser] = useState<UserIdentityResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const queryClient = useQueryClient();

  const fetchAdminSession = useCallback(async () => {
    try {
      const identity = await getAdminMe();
      if (identity && identity.is_admin) {
        setAdminUser(identity);
      } else {
        setAdminUser(null);
      }
    } catch (err) {
      setAdminUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAdminSession();
  }, [fetchAdminSession]);

  const login = async (credentials: UserLoginRequest): Promise<void> => {
    setIsLoading(true);
    try {
      await apiAdminLogin(credentials);
      const identity = await getAdminMe();
      setAdminUser(identity);
      await queryClient.invalidateQueries();
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await apiAdminLogout();
    } catch {
      // Clear state even on network error
    } finally {
      setAdminUser(null);
      queryClient.clear();
    }
  };

  const refreshAdmin = async (): Promise<void> => {
    await fetchAdminSession();
  };

  return (
    <AdminAuthContext.Provider
      value={{
        adminUser,
        isAdminAuthenticated: !!adminUser,
        isLoading,
        login,
        logout,
        refreshAdmin,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
};

export function useAdminAuth(): AdminAuthContextType {
  const context = useContext(AdminAuthContext);
  if (!context) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
}
