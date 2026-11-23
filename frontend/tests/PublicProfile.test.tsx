import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PublicProfile } from '@/routes/PublicProfile';
import * as profileApi from '@/lib/api/profile';
import { ApiClientError } from '@/lib/api/client';

function renderPublicProfile(profileId: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/profile/${profileId}`]}>
        <Routes>
          <Route path="/profile/:id" element={<PublicProfile />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('PublicProfile Component', () => {
  const testId = '44444444-4444-4444-4444-444444444444';

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('renders participant public attributes and tags, excluding sensitive credentials', async () => {
    vi.spyOn(profileApi, 'getPublicProfile').mockResolvedValue({
      user_id: testId,
      full_name: 'Dr. Klaus Richter',
      company_name: 'Heidelberg Materials',
      job_title: 'Head of R&D',
      intent: 'NETWORKING',
      bio_summary: 'Researching clinker efficiency.',
      availability: 'AVAILABLE',
      gender: 'Male',
      date_of_birth: '10-10-1980',
      hobbies: ['Technical Deep-dives'],
      topics: ['Alternative Fuels', 'Kiln Control'],
    });

    renderPublicProfile(testId);

    await waitFor(() => {
      expect(screen.getByText('Dr. Klaus Richter')).toBeInTheDocument();
      expect(screen.getByText('Heidelberg Materials')).toBeInTheDocument();
      expect(screen.getByText('Head of R&D')).toBeInTheDocument();
      expect(screen.getByText('Male')).toBeInTheDocument();
      expect(screen.getByText('10-10-1980')).toBeInTheDocument();
      expect(screen.getByText('Researching clinker efficiency.')).toBeInTheDocument();
      expect(screen.getByText('Technical Deep-dives')).toBeInTheDocument();
      expect(screen.getByText('Alternative Fuels')).toBeInTheDocument();
    });

    // Verify sensitive PII is absent
    expect(screen.queryByText(/klaus@/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/555-/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/password/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/allow_agent_matching/i)).not.toBeInTheDocument();
  });

  it('renders 401 Authentication Required when user is anonymous', async () => {
    vi.spyOn(profileApi, 'getPublicProfile').mockRejectedValue(
      new ApiClientError(401, 'Authentication required.')
    );

    renderPublicProfile(testId);

    await waitFor(() => {
      expect(screen.getByText('Authentication Required')).toBeInTheDocument();
      expect(
        screen.getByText(/You must be signed in with an active conference account to view participant profiles/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in to continue/i })).toBeInTheDocument();
    });
  });

  it('renders 404 Participant Not Found when ID does not exist', async () => {
    vi.spyOn(profileApi, 'getPublicProfile').mockRejectedValue(
      new ApiClientError(404, 'Participant not found.')
    );

    renderPublicProfile(testId);

    await waitFor(() => {
      expect(screen.getByText('Participant Not Found')).toBeInTheDocument();
      expect(
        screen.getByText(/The requested conference participant profile does not exist/i)
      ).toBeInTheDocument();
    });
  });
});
