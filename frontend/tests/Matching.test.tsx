import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Matching } from '@/routes/Matching';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import * as matchingApi from '@/lib/api/matching';
import { ApiClientError } from '@/lib/api/client';
import { MatchEvaluationResult } from '@/types/matching';

function renderMatching(initialEntry = '/matching') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Matching />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

const mockMatchResult: MatchEvaluationResult = {
  requester_id: '11111111-1111-1111-1111-111111111111',
  candidates: [
    {
      candidate_id: '22222222-2222-2222-2222-222222222222',
      full_name: 'Dr. Sarah Connor',
      company_name: 'Cyberdyne Systems',
      job_title: 'Chief Robotics Architect',
      intent: 'NETWORKING',
      availability: 'AVAILABLE',
      bio_summary: 'Leading autonomous systems architecture.',
      topics: ['Autonomous Agents', 'Kiln Decarbonization', 'CCUS'],
      hobbies: ['Tea / Coffee', 'Technical Deep-dives'],
      composite_score: 0.85,
      score_breakdown: {
        intent: {
          raw_similarity: 1.0,
          baseline_weight: 0.25,
          effective_weight: 0.25,
          is_active: true,
        },
        topics: {
          raw_similarity: 0.8,
          baseline_weight: 0.35,
          effective_weight: 0.35,
          is_active: true,
        },
        agenda: {
          raw_similarity: 0.67,
          baseline_weight: 0.25,
          effective_weight: 0.25,
          is_active: true,
        },
        hobbies: {
          raw_similarity: 1.0,
          baseline_weight: 0.15,
          effective_weight: 0.15,
          is_active: true,
        },
        composite_score: 0.85,
      },
      common_topics: ['Kiln Decarbonization', 'CCUS'],
      common_hobbies: ['Tea / Coffee'],
      common_sessions_count: 2,
      match_reasons: [
        'Aligned intent (NETWORKING & NETWORKING)',
        '2 shared topic(s): Kiln Decarbonization, CCUS',
        '2 mutually bookmarked conference session(s)',
      ],
    },
    {
      candidate_id: '33333333-3333-3333-3333-333333333333',
      full_name: 'Marcus Wright',
      company_name: 'Resistance Dynamics',
      job_title: 'Operations Director',
      intent: 'BOTH',
      availability: 'IN_SESSION',
      bio_summary: 'Managing hybrid conference logistics.',
      topics: ['Kiln Decarbonization'],
      hobbies: [],
      composite_score: 0.68,
      score_breakdown: {
        intent: {
          raw_similarity: 0.8,
          baseline_weight: 0.25,
          effective_weight: 0.25,
          is_active: true,
        },
        topics: {
          raw_similarity: 0.5,
          baseline_weight: 0.35,
          effective_weight: 0.41,
          is_active: true,
        },
        agenda: {
          raw_similarity: 0.5,
          baseline_weight: 0.25,
          effective_weight: 0.29,
          is_active: true,
        },
        hobbies: {
          raw_similarity: 0.0,
          baseline_weight: 0.15,
          effective_weight: 0.0,
          is_active: false,
        },
        composite_score: 0.68,
      },
      common_topics: ['Kiln Decarbonization'],
      common_hobbies: [],
      common_sessions_count: 1,
      match_reasons: [
        'Aligned intent (NETWORKING & BOTH)',
        '1 shared topic(s): Kiln Decarbonization',
      ],
    },
  ],
  total_evaluated: 5,
  eligible_count: 3,
  matched_count: 2,
  limit: 10,
  offset: 0,
};

describe('Participant Matching & Discovery UX (P4-WS3)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Default mock user is authenticated
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      username: 'requester_alice',
      email: 'alice@example.com',
      full_name: 'Alice Requester',
      is_active: true,
    });
  });

  it('renders page header and candidate cards upon successful API response', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);

    renderMatching();

    expect(await screen.findByText('Participant Discovery & Matching')).toBeInTheDocument();
    expect(await screen.findByText('Dr. Sarah Connor')).toBeInTheDocument();
    expect(screen.getByText(/Chief Robotics Architect/)).toBeInTheDocument();
    expect(screen.getByText(/Cyberdyne Systems/)).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();

    // Second candidate
    expect(screen.getByText('Marcus Wright')).toBeInTheDocument();
    expect(screen.getByText('68%')).toBeInTheDocument();
    expect(screen.getByText('In Session')).toBeInTheDocument();
  });

  it('displays shared topics, hobbies, and bookmarked sessions count', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);

    renderMatching();

    expect(await screen.findByText('Dr. Sarah Connor')).toBeInTheDocument();
    expect(screen.getByText('Shared Technical Topics (2)')).toBeInTheDocument();
    expect(screen.getByText('CCUS')).toBeInTheDocument();
    expect(screen.getByText('Shared Interests (1)')).toBeInTheDocument();
    expect(screen.getByText('Tea / Coffee')).toBeInTheDocument();
    expect(screen.getByText('2 Mutually Bookmarked Sessions')).toBeInTheDocument();
  });

  it('toggles score breakdown and displays explainable 4-factor metrics', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);

    renderMatching();

    const explainBtns = await screen.findAllByRole('button', { name: /explain score/i });
    expect(explainBtns.length).toBeGreaterThan(0);

    // Expand breakdown for Sarah Connor
    fireEvent.click(explainBtns[0]);

    expect(screen.getByText('Deterministic 4-Factor Breakdown')).toBeInTheDocument();
    expect(screen.getByText('TST-007 Model')).toBeInTheDocument();
    expect(screen.getAllByText(/Weight: 25%/i).length).toBeGreaterThan(0);

    // Toggle back
    fireEvent.click(screen.getByRole('button', { name: /hide breakdown/i }));
    await waitFor(() => {
      expect(screen.queryByText('Deterministic 4-Factor Breakdown')).not.toBeInTheDocument();
    });
  });

  it('handles empty results gracefully with actionable suggestion', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue({
      requester_id: '11111111-1111-1111-1111-111111111111',
      candidates: [],
      total_evaluated: 4,
      eligible_count: 0,
      matched_count: 0,
      limit: 10,
      offset: 0,
    });

    renderMatching();

    expect(await screen.findByText('No Candidates Found')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /show all compatible attendees/i })
    ).toBeInTheDocument();
  });

  it('renders consent disabled state when backend returns 403 consent error (GAP-06)', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockRejectedValue(
      new ApiClientError(
        403,
        'Autonomous agent matching consent is not granted. Explicit opt-in (allow_agent_matching=True) is required (GAP-06).'
      )
    );

    renderMatching();

    expect(
      await screen.findByText('Autonomous Agent Matching is Disabled')
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /enable matching consent in profile/i })
    ).toBeInTheDocument();
  });

  it('renders availability paused state when backend returns 403 DO_NOT_DISTURB error', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockRejectedValue(
      new ApiClientError(
        403,
        'Candidate discovery is paused while your availability is set to DO_NOT_DISTURB.'
      )
    );

    renderMatching();

    expect(await screen.findByText('Candidate Matching Paused')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /update availability in profile/i })
    ).toBeInTheDocument();
  });

  it('renders uninitialized profile guidance when backend returns 404', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockRejectedValue(
      new ApiClientError(404, 'Participant profile not found.')
    );

    renderMatching();

    expect(await screen.findByText('Profile Initialization Required')).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: /create participant profile/i })
    ).toBeInTheDocument();
  });

  it('toggles threshold filter and updates query parameter', async () => {
    const matchSpy = vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);

    renderMatching();

    await screen.findByText('Participant Discovery & Matching');

    // Click "All Compatible" button
    const allCompatBtn = screen.getByRole('button', { name: /all compatible/i });
    fireEvent.click(allCompatBtn);

    await waitFor(() => {
      expect(matchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          filter_by_threshold: false,
        })
      );
    });
  });

  it('preserves privacy boundaries with zero leaked credentials in candidate cards', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);

    const { container } = renderMatching();

    await screen.findByText('Dr. Sarah Connor');
    const text = container.textContent || '';

    // Must not leak private credentials, emails, or phone numbers of candidates
    expect(text).not.toContain('password_hash');
    expect(text).not.toContain('+1-555');
    expect(text).not.toContain('user_sessions');
    expect(text).not.toContain('allow_agent_matching');
  });

  it('renders sign in prompt when unauthenticated', async () => {
    vi.spyOn(authApi, 'getCurrentUser').mockRejectedValue(new ApiClientError(401, 'Unauthorized'));

    renderMatching();

    expect(await screen.findByText('Sign In Required')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
  });
});
