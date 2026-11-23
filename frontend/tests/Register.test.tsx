import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Register } from '@/routes/Register';
import * as authApi from '@/lib/api/auth';
import { ApiClientError } from '@/lib/api/client';
import { AuthProvider } from '@/lib/auth/AuthContext';

function renderRegister() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <Register />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('Register Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders registration form with all required and optional fields', () => {
    renderRegister();

    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password \*/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/company \/ organization/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/job title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/phone number/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText('+91 98765 43210')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('validates client-side required fields and displays validation messages', async () => {
    renderRegister();

    const submitBtn = screen.getByRole('button', { name: /create account/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Full name is required.')).toBeInTheDocument();
      expect(screen.getByText('Username is required.')).toBeInTheDocument();
      expect(screen.getByText('Email address is required.')).toBeInTheDocument();
      expect(screen.getByText('Password is required.')).toBeInTheDocument();
      expect(screen.getByText('Please correct the highlighted errors before submitting.')).toBeInTheDocument();
    });
  });

  it('prevents entering an email address into username and surfaces helpful error', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Sanjana Sharma' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'sanjnamaahi2001@gmail.com' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'sanjnamaahi2001@gmail.com' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ValidPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'ValidPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Username cannot be an email address/i)).toBeInTheDocument();
    });
  });

  it('validates proper email address format', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Sanjana Sharma' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'sanjana_m' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'invalid-email-format' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ValidPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'ValidPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Please provide a valid email address/i)).toBeInTheDocument();
    });
  });

  it('validates Indian +91 phone numbers strictly when provided', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Sanjana Sharma' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'sanjana_m' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'sanjana@example.com' } });
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '12345' } }); // invalid phone
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ValidPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'ValidPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText(/Please enter a valid 10-digit Indian mobile number/i)).toBeInTheDocument();
    });
  });

  it('validates password complexity requirements on the client (minimum 10 characters)', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alex_morgan' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'alex@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'weak' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'weak' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Password must be at least 10 characters long.')).toBeInTheDocument();
    });
  });

  it('validates password matching confirmation', async () => {
    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alex_morgan' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'alex@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ComplexPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'DifferentPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    });
  });

  it('displays successful registration view when API returns 201', async () => {
    const registerSpy = vi.spyOn(authApi, 'registerUser').mockResolvedValue({
      id: '1234',
      username: 'alex_morgan',
      email: 'alex@example.com',
      full_name: 'Alex Morgan',
      company_name: 'Alcon',
      job_title: 'Engineer',
      is_active: true,
      created_at: '2026-10-23T10:00:00Z',
    });

    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alex_morgan' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'alex@example.com' } });
    fireEvent.change(screen.getByLabelText(/phone number/i), { target: { value: '+91 98765 43210' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ComplexPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'ComplexPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText('Registration Complete')).toBeInTheDocument();
      expect(screen.getByText(/Account Created Successfully!/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /proceed to log in/i })).toBeInTheDocument();
    });

    expect(registerSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        phone_number: '+91 98765 43210',
      })
    );
  });

  it('handles duplicate username conflict (409) gracefully', async () => {
    vi.spyOn(authApi, 'registerUser').mockRejectedValue(
      new ApiClientError(409, "Username 'alex_morgan' is already taken.")
    );

    renderRegister();

    fireEvent.change(screen.getByLabelText(/full name/i), { target: { value: 'Alex Morgan' } });
    fireEvent.change(screen.getByLabelText(/username/i), { target: { value: 'alex_morgan' } });
    fireEvent.change(screen.getByLabelText(/email address/i), { target: { value: 'alex@example.com' } });
    fireEvent.change(screen.getByLabelText(/^password \*/i), { target: { value: 'ComplexPassword123!' } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: 'ComplexPassword123!' } });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(screen.getByText("Username 'alex_morgan' is already taken.")).toBeInTheDocument();
    });
  });
});
