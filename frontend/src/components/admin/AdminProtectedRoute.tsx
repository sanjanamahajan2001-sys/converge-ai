import React from 'react';
import { Navigate, Link } from 'react-router-dom';
import { useAdminAuth } from '@/lib/auth/AdminAuthContext';
import { LoadingState } from '@/components/ui/LoadingState';

interface AdminProtectedRouteProps {
  children: React.ReactNode;
}

export const AdminProtectedRoute: React.FC<AdminProtectedRouteProps> = ({ children }) => {
  const { adminUser, isAdminAuthenticated, isLoading } = useAdminAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas-base">
        <LoadingState message="Verifying administrative credentials..." />
      </div>
    );
  }

  if (!isAdminAuthenticated || !adminUser) {
    return <Navigate to="/admin/login" replace />;
  }

  if (!adminUser.is_admin) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas-base p-4">
        <div className="max-w-md w-full bg-canvas-elevated border border-canvas-border rounded-xl p-6 text-center space-y-4 shadow-md">
          <div className="w-12 h-12 mx-auto rounded-full bg-rose-100 dark:bg-rose-950/50 flex items-center justify-center text-rose-600 text-2xl font-bold">
            🛡️
          </div>
          <h2 className="text-lg font-bold text-ink-primary font-serif">
            Administrative Access Required
          </h2>
          <p className="text-xs sm:text-sm text-ink-secondary">
            Your authenticated account does not possess administrator permissions for the Converge AI control plane.
          </p>
          <div className="pt-2">
            <Link
              to="/"
              className="inline-block px-4 py-2 text-xs font-semibold rounded-lg bg-brass text-white hover:bg-brass-hover transition"
            >
              Return to Conference Portal
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
