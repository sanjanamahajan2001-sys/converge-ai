import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/lib/auth/AuthContext';
import { LoadingState } from '@/components/ui/LoadingState';

interface OrganizerProtectedRouteProps {
  children?: React.ReactNode;
}

export const OrganizerProtectedRoute: React.FC<OrganizerProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="py-16">
        <LoadingState message="Verifying organizer credentials..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login?role=organizer" state={{ from: location }} replace />;
  }

  // If user is authenticated as regular attendee without organizer profile, redirect to onboarding
  if (user && !user.is_organizer && !user.is_admin) {
    return <Navigate to="/organizer/register" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
