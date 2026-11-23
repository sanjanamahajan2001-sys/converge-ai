import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from '@/components/layout/Header';
import { Home } from '@/routes/Home';
import { NotFound } from '@/routes/NotFound';
import { Register } from '@/routes/Register';
import { Login } from '@/routes/Login';
import { Profile } from '@/routes/Profile';
import { ProfileEdit } from '@/routes/ProfileEdit';
import { PublicProfile } from '@/routes/PublicProfile';
import { Agenda } from '@/routes/Agenda';
import { Matching } from '@/routes/Matching';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { LoadingState } from '@/components/ui/LoadingState';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import * as profileApi from '@/lib/api/profile';
import * as agendaApi from '@/lib/api/agenda';
import * as matchingApi from '@/lib/api/matching';

// Create isolated React Query client for testing
function renderWithProviders(ui: React.ReactElement, initialEntry = '/') {
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
        <MemoryRouter initialEntries={[initialEntry]}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('UI Terminology Guard (Zero Development Phase / Workstream Terms)', () => {
  const forbiddenPatterns = [
    /\bphase\s*\d+/i,
    /\bworkstream\b/i,
    /\bws-\d+/i,
    /\bp2-ws\d+/i,
  ];

  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      username: 'guard_user',
      email: 'guard@example.com',
      full_name: 'Guard User',
      is_active: true,
    });
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Clean bio summary',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: ['Tea / Coffee'],
      topics: ['Kiln Decarbonization'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    vi.spyOn(profileApi, 'getHobbiesCatalog').mockResolvedValue(['Tea / Coffee', 'Casual Conversations']);
    vi.spyOn(profileApi, 'getPublicProfile').mockResolvedValue({
      user_id: '22222222-2222-2222-2222-222222222222',
      full_name: 'Public Participant',
      company_name: 'Alcon',
      job_title: 'Engineer',
      intent: 'NETWORKING',
      bio_summary: 'Clean public bio',
      availability: 'AVAILABLE',
      hobbies: ['Tea / Coffee'],
      topics: ['Automation'],
    });
    vi.spyOn(agendaApi, 'getConferences').mockResolvedValue([
      {
        id: '33333333-3333-3333-3333-333333333333',
        title: 'Converge AI Global Summit 2026',
        description: 'Global AI Summit for enterprise agents.',
        venue_name: 'Moscone Convention Center',
        timezone: 'America/Los_Angeles',
        start_date: '2026-11-10',
        end_date: '2026-11-12',
        is_active: true,
        created_at: '2026-10-26T00:00:00Z',
        updated_at: '2026-10-26T00:00:00Z',
      },
    ]);
    vi.spyOn(agendaApi, 'getSessions').mockResolvedValue([
      {
        id: '44444444-4444-4444-4444-444444444444',
        conference_id: '33333333-3333-3333-3333-333333333333',
        title: 'Keynote: Autonomous Agents in Action',
        abstract: 'An in-depth presentation on multi-agent architectures.',
        start_time: '2026-11-10T17:00:00Z',
        end_time: '2026-11-10T18:00:00Z',
        hall_room: 'Grand Ballroom',
        track_name: 'Keynote',
        is_cancelled: false,
        speaker_names: 'Dr. Sarah Connor',
        created_at: '2026-10-26T00:00:00Z',
        updated_at: '2026-10-26T00:00:00Z',
      },
    ]);
    vi.spyOn(agendaApi, 'getMyBookmarks').mockResolvedValue([]);
  });

  function assertCleanTerminology(container: HTMLElement) {
    const htmlContent = container.innerHTML;
    const textContent = container.textContent || '';
    for (const pattern of forbiddenPatterns) {
      expect(htmlContent).not.toMatch(pattern);
      expect(textContent).not.toMatch(pattern);
    }
  }

  it('verifies Header renders zero internal phase or workstream terminology', () => {
    const { container } = renderWithProviders(<Header />);
    assertCleanTerminology(container);
  });

  it('verifies Home overview page renders zero internal phase or workstream terminology', () => {
    const { container } = renderWithProviders(<Home />);
    assertCleanTerminology(container);
  });

  it('verifies NotFound route renders zero internal phase or workstream terminology', () => {
    const { container } = renderWithProviders(<NotFound />);
    assertCleanTerminology(container);
  });

  it('verifies Register screen renders zero internal phase terminology', () => {
    const { container } = renderWithProviders(<Register />);
    assertCleanTerminology(container);
  });

  it('verifies Login screen renders zero internal phase terminology', () => {
    const { container } = renderWithProviders(<Login />);
    assertCleanTerminology(container);
  });

  it('verifies Profile screen renders zero internal phase terminology', () => {
    const { container } = renderWithProviders(<Profile />);
    assertCleanTerminology(container);
  });

  it('verifies ProfileEdit screen renders zero internal phase terminology', () => {
    const { container } = renderWithProviders(<ProfileEdit />);
    assertCleanTerminology(container);
  });

  it('verifies PublicProfile screen renders zero internal phase terminology', () => {
    const { container } = renderWithProviders(
      <Routes>
        <Route path="/profile/:id" element={<PublicProfile />} />
      </Routes>,
      '/profile/22222222-2222-2222-2222-222222222222'
    );
    assertCleanTerminology(container);
  });

  it('verifies Agenda screen renders zero internal phase or workstream terminology', async () => {
    const { container, findByText } = renderWithProviders(<Agenda />);
    await findByText('Converge AI Global Summit 2026');
    assertCleanTerminology(container);
  });

  it('verifies Matching screen renders zero internal phase or workstream terminology', async () => {
    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue({
      requester_id: '11111111-1111-1111-1111-111111111111',
      candidates: [],
      total_evaluated: 0,
      eligible_count: 0,
      matched_count: 0,
      limit: 10,
      offset: 0,
    });
    const { container, findByText } = renderWithProviders(<Matching />);
    await findByText('Participant Discovery & Matching');
    assertCleanTerminology(container);
  });

  it('verifies UI foundational components render zero internal phase terminology', () => {
    const { container: cardContainer } = renderWithProviders(
      <Card title="Participant Directory" subtitle="Conference Delegates">
        <p>Networking details and session schedule.</p>
      </Card>
    );
    assertCleanTerminology(cardContainer);

    const { container: emptyContainer } = renderWithProviders(
      <EmptyState
        emoji="📭"
        title="No Messages"
        description="Your conversations with participants will appear here."
      />
    );
    assertCleanTerminology(emptyContainer);

    const { container: badgeContainer } = renderWithProviders(
      <StatusBadge emoji="🟢" label="Operational" variant="success" />
    );
    assertCleanTerminology(badgeContainer);

    const { container: loadingContainer } = renderWithProviders(
      <LoadingState message="Connecting to local services..." />
    );
    assertCleanTerminology(loadingContainer);
  });
});
