import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Profile } from '@/routes/Profile';
import * as profileApi from '@/lib/api/profile';
import { ApiClientError } from '@/lib/api/client';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';

function renderProfile() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <Profile />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('Profile Route Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      username: 'maria_rossi',
      email: 'maria@example.com',
      full_name: 'Maria Rossi',
      company_name: 'Italcementi',
      job_title: 'Plant Manager',
      is_active: true,
    });
  });

  it('renders initialized profile with availability, bio, gender, date_of_birth and interest tags', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'BOTH',
      bio_summary: 'Managing clinker calcination facilities.',
      availability: 'AVAILABLE',
      allow_agent_matching: true,
      gender: 'Non-binary',
      date_of_birth: '12-04-1988',
      location: 'Jio World Convention Centre, Mumbai',
      hobbies: ['Tea / Coffee', 'Technical Deep-dives'],
      topics: ['Kiln Decarbonization', 'CCUS'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfile();

    await waitFor(() => {
      expect(screen.getByText('Maria Rossi')).toBeInTheDocument();
      expect(screen.getByText(/@maria_rossi/)).toBeInTheDocument();
      expect(screen.getByText('Managing clinker calcination facilities.')).toBeInTheDocument();
      expect(screen.getByText('Tea / Coffee')).toBeInTheDocument();
      expect(screen.getByText('Kiln Decarbonization')).toBeInTheDocument();
      expect(screen.getByText('Opted In')).toBeInTheDocument();
      expect(screen.getByText('Non-binary')).toBeInTheDocument();
      expect(screen.getByText('12-04-1988')).toBeInTheDocument();
      expect(screen.getByText('Jio World Convention Centre, Mumbai')).toBeInTheDocument();
      expect(screen.getByText(/Activity & Session Analytics/i)).toBeInTheDocument();
    });
  });

  it('renders 404 uninitialized setup prompt without crashing', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockRejectedValue(
      new ApiClientError(404, 'Participant profile not found. Please initialize your profile.')
    );

    renderProfile();

    await waitFor(() => {
      expect(screen.getByText('Profile Not Yet Initialized')).toBeInTheDocument();
      expect(screen.getByText(/You have not yet configured your conference participation intent/i)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /complete your profile/i })).toBeInTheDocument();
    });
  });

  it('handles general network error with retry option', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockRejectedValue(
      new ApiClientError(500, 'Internal server connection timeout.')
    );

    renderProfile();

    await waitFor(() => {
      expect(screen.getByText('Profile Unavailable')).toBeInTheDocument();
      expect(screen.getByText(/Internal server connection timeout/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
    });
  });
});
