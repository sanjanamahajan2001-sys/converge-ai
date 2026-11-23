import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import { ApiClientError } from '@/lib/api/client';

function renderWithAuth(initialEntry: string, authApiMock: () => Promise<any>) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  vi.spyOn(authApi, 'getCurrentUser').mockImplementation(authApiMock);

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Routes>
            <Route path="/login" element={<div>Login Page Target</div>} />
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div>Secret Protected Area</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('ProtectedRoute Guard Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders loading indicator while resolving session to avoid content flash', () => {
    // Return a promise that does not resolve immediately
    renderWithAuth('/protected', () => new Promise(() => {}));
    expect(screen.getByText(/Verifying session credentials/i)).toBeInTheDocument();
    expect(screen.queryByText('Secret Protected Area')).not.toBeInTheDocument();
  });

  it('redirects to /login when user has no active session (401)', async () => {
    renderWithAuth('/protected', async () => {
      throw new ApiClientError(401, 'Authentication required.');
    });

    await waitFor(() => {
      expect(screen.getByText('Login Page Target')).toBeInTheDocument();
      expect(screen.queryByText('Secret Protected Area')).not.toBeInTheDocument();
    });
  });

  it('renders protected child component when session is active', async () => {
    renderWithAuth('/protected', async () => ({
      id: '1234',
      username: 'active_user',
      email: 'active@example.com',
      full_name: 'Active User',
      is_active: true,
    }));

    await waitFor(() => {
      expect(screen.getByText('Secret Protected Area')).toBeInTheDocument();
    });
  });
});
