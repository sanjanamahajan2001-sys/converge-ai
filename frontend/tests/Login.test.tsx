import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Login } from '@/routes/Login';
import * as authApi from '@/lib/api/auth';
import { ApiClientError } from '@/lib/api/client';
import { AuthProvider } from '@/lib/auth/AuthContext';

function renderLogin(initialEntries?: Array<{ pathname: string; state?: any }>) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <Login />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('Login Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders login credentials form', () => {
    renderLogin();

    expect(screen.getByLabelText(/username or email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('pre-populates username and displays success alert when arriving from registration redirect', () => {
    renderLogin([
      {
        pathname: '/login',
        state: {
          registeredUsername: 'sanjana_m',
          successMessage: 'Account created successfully! Please sign in with your credentials.',
        },
      },
    ]);

    const identifierInput = screen.getByLabelText(/username or email address/i) as HTMLInputElement;
    expect(identifierInput.value).toBe('sanjana_m');
    expect(screen.getByText(/Account created successfully! Please sign in with your credentials./i)).toBeInTheDocument();
  });

  it('disables submit button when inputs are empty', () => {
    renderLogin();
    const button = screen.getByRole('button', { name: /sign in/i });
    expect(button).toBeDisabled();
  });

  it('displays generic error on 401 invalid credentials', async () => {
    vi.spyOn(authApi, 'loginUser').mockRejectedValue(
      new ApiClientError(401, 'Invalid credentials.')
    );

    renderLogin();

    fireEvent.change(screen.getByLabelText(/username or email address/i), {
      target: { value: 'user_unknown' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'wrongpassword' },
    });

    const button = screen.getByRole('button', { name: /sign in/i });
    expect(button).not.toBeDisabled();
    fireEvent.click(button);

    await waitFor(() => {
      expect(
        screen.getByText(/Invalid username\/email or password. Please verify your credentials./i)
      ).toBeInTheDocument();
    });
  });

  it('displays rate limiting throttling message on 429 response', async () => {
    vi.spyOn(authApi, 'loginUser').mockRejectedValue(
      new ApiClientError(429, 'Too many failed login attempts. Preflight IP locked.')
    );

    renderLogin();

    fireEvent.change(screen.getByLabelText(/username or email address/i), {
      target: { value: 'user_throttled' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/Too many failed login attempts. Preflight IP locked./i)
      ).toBeInTheDocument();
    });
  });

  it('submits credentials and transitions on successful login', async () => {
    vi.spyOn(authApi, 'loginUser').mockResolvedValue({
      status: 'authenticated',
      user_id: '1234',
      username: 'valid_user',
      email: 'valid@example.com',
      expires_at: '2026-10-24T00:00:00Z',
    });
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '1234',
      username: 'valid_user',
      email: 'valid@example.com',
      full_name: 'Valid User',
      company_name: 'Tech Corp',
      job_title: 'Architect',
      is_active: true,
    });

    renderLogin();

    fireEvent.change(screen.getByLabelText(/username or email address/i), {
      target: { value: 'valid_user' },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: 'ValidPass123!' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(authApi.loginUser).toHaveBeenCalledWith({
        identifier: 'valid_user',
        password: 'ValidPass123!',
      });
    });
  });
});
