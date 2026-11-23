import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Matching } from '@/routes/Matching';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import * as matchingApi from '@/lib/api/matching';
import { MatchEvaluationResult } from '@/types/matching';

const mockUser = {
  id: 'user-host-1111',
  username: 'sanjana_host',
  email: 'sanjana@example.com',
  full_name: 'Sanjana Maahi',
  is_active: true,
};

const mockMatchResult: MatchEvaluationResult = {
  requester_id: 'user-host-1111',
  total_evaluated: 10,
  eligible_count: 3,
  matched_count: 3,
  limit: 10,
  offset: 0,
  candidates: [
    {
      candidate_id: 'cand-1',
      full_name: 'Vikram Singhania',
      company_name: 'Deccan Clinker Ltd',
      job_title: 'Chief Commercial Officer',
      intent: 'NETWORKING',
      availability: 'AVAILABLE',
      bio_summary: 'Heading commercial operations for cement clinker.',
      topics: ['Decarbonization Policy', 'LC3 Cement'],
      hobbies: ['Chess'],
      composite_score: 0.88,
      common_topics: ['LC3 Cement'],
      common_hobbies: [],
      common_sessions_count: 2,
      match_reasons: ['Shared focus on LC3 Cement'],
      score_breakdown: {
        intent: { raw_similarity: 1.0, baseline_weight: 0.25, effective_weight: 0.25, is_active: true },
        topics: { raw_similarity: 0.8, baseline_weight: 0.45, effective_weight: 0.45, is_active: true },
        agenda: { raw_similarity: 0.5, baseline_weight: 0.2, effective_weight: 0.2, is_active: true },
        hobbies: { raw_similarity: 0.0, baseline_weight: 0.1, effective_weight: 0.1, is_active: false },
        composite_score: 0.88,
      },
    },
    {
      candidate_id: 'cand-2',
      full_name: 'Rohit Mehta',
      company_name: 'Apex Building Materials Ltd',
      job_title: 'Managing Director',
      intent: 'BOTH',
      availability: 'AVAILABLE',
      bio_summary: 'Leading regional stockist and distributor.',
      topics: ['Cement Distribution', 'Supply Chain Logistics'],
      hobbies: ['Cricket'],
      composite_score: 0.76,
      common_topics: ['Supply Chain Logistics'],
      common_hobbies: [],
      common_sessions_count: 1,
      match_reasons: ['Shared focus on Supply Chain Logistics'],
      score_breakdown: {
        intent: { raw_similarity: 0.9, baseline_weight: 0.25, effective_weight: 0.25, is_active: true },
        topics: { raw_similarity: 0.7, baseline_weight: 0.45, effective_weight: 0.45, is_active: true },
        agenda: { raw_similarity: 0.5, baseline_weight: 0.2, effective_weight: 0.2, is_active: true },
        hobbies: { raw_similarity: 0.0, baseline_weight: 0.1, effective_weight: 0.1, is_active: false },
        composite_score: 0.76,
      },
    },
    {
      candidate_id: 'cand-3',
      full_name: 'Maahi Sharma',
      company_name: 'Deccan Green Cement Ltd',
      job_title: 'Head of Sales',
      intent: 'NETWORKING',
      availability: 'AVAILABLE',
      bio_summary: 'Heading institutional sales.',
      topics: ['Low-Carbon Cement', 'Green Procurement'],
      hobbies: [],
      composite_score: 0.72,
      common_topics: ['Low-Carbon Cement'],
      common_hobbies: [],
      common_sessions_count: 1,
      match_reasons: ['Shared interest in Low-Carbon Cement'],
      score_breakdown: {
        intent: { raw_similarity: 1.0, baseline_weight: 0.25, effective_weight: 0.25, is_active: true },
        topics: { raw_similarity: 0.6, baseline_weight: 0.45, effective_weight: 0.45, is_active: true },
        agenda: { raw_similarity: 0.5, baseline_weight: 0.2, effective_weight: 0.2, is_active: true },
        hobbies: { raw_similarity: 0.0, baseline_weight: 0.1, effective_weight: 0.1, is_active: false },
        composite_score: 0.72,
      },
    },
    {
      candidate_id: 'cand-4',
      full_name: 'Ananya Deshmukh',
      company_name: 'Western Grinding Units Ltd',
      job_title: 'Operations Director',
      intent: 'NETWORKING',
      availability: 'AVAILABLE',
      bio_summary: 'Managing clinker grinding operations.',
      topics: ['Grinding Efficiency', 'Low-Carbon Cement'],
      hobbies: [],
      composite_score: 0.69,
      common_topics: ['Low-Carbon Cement'],
      common_hobbies: [],
      common_sessions_count: 1,
      match_reasons: ['Shared focus on Low-Carbon Cement'],
      score_breakdown: {
        intent: { raw_similarity: 1.0, baseline_weight: 0.25, effective_weight: 0.25, is_active: true },
        topics: { raw_similarity: 0.6, baseline_weight: 0.45, effective_weight: 0.45, is_active: true },
        agenda: { raw_similarity: 0.5, baseline_weight: 0.2, effective_weight: 0.2, is_active: true },
        hobbies: { raw_similarity: 0.0, baseline_weight: 0.1, effective_weight: 0.1, is_active: false },
        composite_score: 0.69,
      },
    },
    {
      candidate_id: 'cand-5',
      full_name: 'Suresh Patil',
      company_name: 'Sahyadri Concrete Solutions',
      job_title: 'Chief Technical Officer',
      intent: 'NETWORKING',
      availability: 'AVAILABLE',
      bio_summary: 'Ready-mix concrete formulation specialist.',
      topics: ['Ready-Mix Concrete', 'LC3 Cement'],
      hobbies: [],
      composite_score: 0.65,
      common_topics: ['LC3 Cement'],
      common_hobbies: [],
      common_sessions_count: 1,
      match_reasons: ['Shared focus on LC3 Cement'],
      score_breakdown: {
        intent: { raw_similarity: 1.0, baseline_weight: 0.25, effective_weight: 0.25, is_active: true },
        topics: { raw_similarity: 0.5, baseline_weight: 0.45, effective_weight: 0.45, is_active: true },
        agenda: { raw_similarity: 0.5, baseline_weight: 0.2, effective_weight: 0.2, is_active: true },
        hobbies: { raw_similarity: 0.0, baseline_weight: 0.1, effective_weight: 0.1, is_active: false },
        composite_score: 0.65,
      },
    },
  ],
};

describe('Mode A Multi-Select & Thematic Circle Modal (Phase 5)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(mockUser);
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue(mockMatchResult);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders candidate selection checkboxes and "Add to Circle" buttons in Mode A', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/matching']}>
            <Matching />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Vikram Singhania')).toBeInTheDocument();
    expect(screen.getByText('Rohit Mehta')).toBeInTheDocument();
    expect(screen.getByText('Maahi Sharma')).toBeInTheDocument();

    // Checkboxes should exist for each candidate
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(5);

    // "Add to Circle" buttons should be rendered
    const addButtons = screen.getAllByRole('button', { name: /Add to Circle/i });
    expect(addButtons.length).toBe(5);
  });

  it('shows the floating dock when a candidate is selected and updates count', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/matching']}>
            <Matching />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Vikram Singhania')).toBeInTheDocument();

    // Select Vikram Singhania
    const addButtons = screen.getAllByRole('button', { name: /Add to Circle/i });
    fireEvent.click(addButtons[0]);

    // Floating dock should appear
    expect(await screen.findByLabelText('Thematic Circle Selection')).toBeInTheDocument();
    expect(screen.getByText('1 / 4')).toBeInTheDocument();
    expect(screen.getByText(/Need at least 2 peers for circle/)).toBeInTheDocument();

    // Start button should be disabled for only 1 peer
    const startBtn = screen.getByRole('button', { name: /Start Networking Circle/i });
    expect(startBtn).toBeDisabled();

    // Select second candidate (Rohit Mehta)
    fireEvent.click(screen.getAllByRole('button', { name: /Add to Circle/i })[0]); // now Rohit is first unselected

    // Now 2 peers selected -> Start button enabled!
    expect(screen.getByText('2 / 4')).toBeInTheDocument();
    expect(screen.getByText(/3 delegates total • 25 turns/)).toBeInTheDocument();
    expect(startBtn).not.toBeDisabled();
  });

  it('enforces maximum 4 peers selection limit (5 delegates total)', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/matching']}>
            <Matching />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Vikram Singhania')).toBeInTheDocument();

    const checkboxes = screen.getAllByRole('checkbox');
    // Select 4 candidates (max allowed for 5 delegates total)
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);
    fireEvent.click(checkboxes[2]);
    fireEvent.click(checkboxes[3]);

    expect(await screen.findByText('4 / 4')).toBeInTheDocument();
    expect(screen.getByText(/5 delegates total • 35 turns/)).toBeInTheDocument();

    // Attempting to select 5th candidate is prevented
    fireEvent.click(checkboxes[4]);
    expect(screen.getByText('4 / 4')).toBeInTheDocument();

    const startBtn = screen.getByRole('button', { name: /Start Networking Circle/i });
    expect(startBtn).not.toBeDisabled();
  });

  it('opens Launch Circle modal pre-populated with selected candidates and auto-fills title', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/matching']}>
            <Matching />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Vikram Singhania')).toBeInTheDocument();

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]); // Vikram
    fireEvent.click(checkboxes[1]); // Rohit

    const startBtn = await screen.findByRole('button', { name: /Start Networking Circle/i });
    fireEvent.click(startBtn);

    // Modal opens
    expect(await screen.findByText('Launch Thematic Networking Circle')).toBeInTheDocument();
    expect(screen.getByText('Select Peers (2/4 selected)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Launch Circle/i })).toBeInTheDocument();
  });
});
