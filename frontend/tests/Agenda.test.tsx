import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Agenda } from '@/routes/Agenda';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import * as agendaApi from '@/lib/api/agenda';
import { ConferenceResponse, SessionResponse, BookmarkedSessionResponse } from '@/types/agenda';

function renderAgenda(initialEntry = '/agenda') {
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
          <Agenda />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

const mockConferences: ConferenceResponse[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    title: 'Converge AI Global Summit 2026',
    description: 'Premier summit exploring agent collaboration.',
    venue_name: 'Moscone Convention Center',
    timezone: 'America/Los_Angeles',
    start_date: '2026-11-10',
    end_date: '2026-11-12',
    is_active: true,
    created_at: '2026-10-26T00:00:00Z',
    updated_at: '2026-10-26T00:00:00Z',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    title: 'European AI Colloquium 2026',
    description: 'Autonomous systems conference in Berlin.',
    venue_name: 'Berlin Congress Center',
    timezone: 'Europe/Berlin',
    start_date: '2026-12-01',
    end_date: '2026-12-03',
    is_active: true,
    created_at: '2026-10-26T00:00:00Z',
    updated_at: '2026-10-26T00:00:00Z',
  },
];

const mockSessions: SessionResponse[] = [
  {
    id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    conference_id: '11111111-1111-1111-1111-111111111111',
    title: 'Autonomous Multi-Agent Networks',
    abstract: 'Exploring real-time negotiation protocols and peer consensus in agent clusters.',
    start_time: '2026-11-10T17:00:00Z', // 09:00 AM PST
    end_time: '2026-11-10T18:00:00Z',   // 10:00 AM PST
    hall_room: 'Hall A',
    track_name: 'Architecture',
    is_cancelled: false,
    speaker_names: 'Dr. Alice Martin, Bob Vance',
    created_at: '2026-10-26T00:00:00Z',
    updated_at: '2026-10-26T00:00:00Z',
  },
  {
    id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    conference_id: '11111111-1111-1111-1111-111111111111',
    title: 'Zero-Trust Protocol Design',
    abstract: 'Securing agent communication over untrusted networks with hardware enclaves.',
    start_time: '2026-11-10T19:00:00Z', // 11:00 AM PST
    end_time: '2026-11-10T20:30:00Z',   // 12:30 PM PST
    hall_room: 'Hall B',
    track_name: 'Security',
    is_cancelled: true,
    speaker_names: 'Carol Danvers',
    created_at: '2026-10-26T00:00:00Z',
    updated_at: '2026-10-26T00:00:00Z',
  },
  {
    id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
    conference_id: '11111111-1111-1111-1111-111111111111',
    title: 'Decentralized Consensus in Practice',
    abstract: 'Lessons learned from deploying 10,000 nodes in enterprise environments.',
    start_time: '2026-11-11T16:00:00Z', // Day 2: 08:00 AM PST
    end_time: '2026-11-11T17:00:00Z',   // Day 2: 09:00 AM PST
    hall_room: 'Hall A',
    track_name: 'Architecture',
    is_cancelled: false,
    speaker_names: 'David Kim',
    created_at: '2026-10-26T00:00:00Z',
    updated_at: '2026-10-26T00:00:00Z',
  },
];

const mockBookmarks: BookmarkedSessionResponse[] = [
  {
    session_id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    bookmarked_at: '2026-10-26T08:00:00Z',
    session: mockSessions[0],
  },
];

describe('Agenda Route & Browsing Experience', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '99999999-9999-9999-9999-999999999999',
      username: 'alice_attendee',
      email: 'alice@example.com',
      full_name: 'Alice Attendee',
      is_active: true,
    });
    vi.spyOn(agendaApi, 'getConferences').mockResolvedValue(mockConferences);
    vi.spyOn(agendaApi, 'getSessions').mockResolvedValue(mockSessions);
    vi.spyOn(agendaApi, 'getMyBookmarks').mockResolvedValue(mockBookmarks);
  });

  it('renders conference banner and venue details', async () => {
    renderAgenda();

    expect(await screen.findByRole('heading', { name: 'Converge AI Global Summit 2026' })).toBeInTheDocument();
    expect(screen.getByText('Moscone Convention Center')).toBeInTheDocument();
    expect(screen.getByText(/America\/Los_Angeles/i)).toBeInTheDocument();
  });

  it('groups sessions by conference-local date correctly', async () => {
    renderAgenda();

    // Verify session titles are displayed
    expect(await screen.findByText('Autonomous Multi-Agent Networks')).toBeInTheDocument();
    expect(screen.getByText('Zero-Trust Protocol Design')).toBeInTheDocument();
    expect(screen.getByText('Decentralized Consensus in Practice')).toBeInTheDocument();

    // Day headers formatted in conference timezone
    expect(screen.getByRole('heading', { name: 'Tuesday, Nov 10, 2026' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Wednesday, Nov 11, 2026' })).toBeInTheDocument();
  });

  it('shows cancellation status for cancelled sessions', async () => {
    renderAgenda();

    const cancelledTitle = await screen.findByText('Zero-Trust Protocol Design');
    expect(cancelledTitle).toBeInTheDocument();

    // The cancelled badge should be rendered
    const cancelledBadges = screen.getAllByText(/Cancelled/i);
    expect(cancelledBadges.length).toBeGreaterThan(0);
  });

  it('opens and closes session detail modal with full details', async () => {
    renderAgenda();

    const sessionCard = await screen.findByText('Autonomous Multi-Agent Networks');
    fireEvent.click(sessionCard);

    // Modal should be open
    const modal = screen.getByRole('dialog');
    expect(modal).toBeInTheDocument();
    expect(within(modal).getByRole('heading', { name: 'Autonomous Multi-Agent Networks' })).toBeInTheDocument();
    expect(within(modal).getByText(/Exploring real-time negotiation protocols/i)).toBeInTheDocument();
    expect(within(modal).getByText(/Dr. Alice Martin, Bob Vance/i)).toBeInTheDocument();

    // Close via close button
    const closeBtn = screen.getByRole('button', { name: /close session details/i });
    fireEvent.click(closeBtn);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('closes session detail modal via Escape key', async () => {
    renderAgenda();

    const sessionCard = await screen.findByText('Autonomous Multi-Agent Networks');
    fireEvent.click(sessionCard);

    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('filters sessions by search term', async () => {
    renderAgenda();

    await screen.findByText('Autonomous Multi-Agent Networks');

    const searchInput = screen.getByPlaceholderText(/search session title/i);
    fireEvent.change(searchInput, { target: { value: 'Security' } });

    // Only Zero-Trust (Security track) matches
    expect(screen.getByText('Zero-Trust Protocol Design')).toBeInTheDocument();
    expect(screen.queryByText('Autonomous Multi-Agent Networks')).not.toBeInTheDocument();
    expect(screen.queryByText('Decentralized Consensus in Practice')).not.toBeInTheDocument();
  });

  it('filters sessions by track', async () => {
    renderAgenda();

    await screen.findByText('Autonomous Multi-Agent Networks');

    const trackSelect = screen.getByLabelText(/track category/i);
    fireEvent.change(trackSelect, { target: { value: 'Security' } });

    expect(screen.getByText('Zero-Trust Protocol Design')).toBeInTheDocument();
    expect(screen.queryByText('Autonomous Multi-Agent Networks')).not.toBeInTheDocument();
  });

  it('filters sessions by cancellation status', async () => {
    renderAgenda();

    await screen.findByText('Autonomous Multi-Agent Networks');

    const statusSelect = screen.getByLabelText(/^status$/i);
    fireEvent.change(statusSelect, { target: { value: 'CANCELLED_ONLY' } });

    expect(screen.getByText('Zero-Trust Protocol Design')).toBeInTheDocument();
    expect(screen.queryByText('Autonomous Multi-Agent Networks')).not.toBeInTheDocument();
    expect(screen.queryByText('Decentralized Consensus in Practice')).not.toBeInTheDocument();

    // Switch to active only
    fireEvent.change(statusSelect, { target: { value: 'ACTIVE_ONLY' } });
    expect(screen.queryByText('Zero-Trust Protocol Design')).not.toBeInTheDocument();
    expect(screen.getByText('Autonomous Multi-Agent Networks')).toBeInTheDocument();
  });

  it('toggles "My Bookmarks" filter to display saved sessions only', async () => {
    renderAgenda();

    await screen.findByText('Autonomous Multi-Agent Networks');

    const bookmarksFilterBtn = screen.getByRole('button', { name: /my bookmarks/i });
    fireEvent.click(bookmarksFilterBtn);

    // Only session 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa' is bookmarked
    expect(screen.getByText('Autonomous Multi-Agent Networks')).toBeInTheDocument();
    expect(screen.queryByText('Zero-Trust Protocol Design')).not.toBeInTheDocument();
    expect(screen.queryByText('Decentralized Consensus in Practice')).not.toBeInTheDocument();
  });

  it('toggles bookmark mutation for authenticated user', async () => {
    const createMock = vi.spyOn(agendaApi, 'createBookmark').mockResolvedValue({
      session_id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      user_id: '99999999-9999-9999-9999-999999999999',
      created_at: '2026-10-26T09:00:00Z',
    });

    renderAgenda();

    // Wait until session is loaded
    await screen.findByText('Decentralized Consensus in Practice');

    // Wait until authenticated user is populated
    await waitFor(() => {
      expect(authApi.getCurrentUser).toHaveBeenCalled();
    });

    const unsavedBtn = screen.getByRole('button', {
      name: 'Bookmark Decentralized Consensus in Practice',
    });
    expect(unsavedBtn).toBeInTheDocument();

    fireEvent.click(unsavedBtn);

    await waitFor(() => {
      expect(createMock).toHaveBeenCalledWith('cccccccc-cccc-cccc-cccc-cccccccccccc');
    });
  });

  it('shows empty state when no conferences are published', async () => {
    vi.spyOn(agendaApi, 'getConferences').mockResolvedValue([]);
    renderAgenda();

    expect(await screen.findByText('No Published Conferences')).toBeInTheDocument();
  });

  it('shows empty state when conference has no sessions', async () => {
    vi.spyOn(agendaApi, 'getSessions').mockResolvedValue([]);
    renderAgenda();

    expect(await screen.findByText('No Sessions Scheduled')).toBeInTheDocument();
  });

  it('renders rich public conference details with organizer host badge and clickable Google Maps link', async () => {
    vi.spyOn(agendaApi, 'getConferences').mockResolvedValue([
      {
        id: 'conf-pub-1',
        title: 'National Green Cement & LC3 Summit 2026',
        summary: 'Executive summit on decarbonizing heavy construction.',
        description: 'Three-day technical conference bringing together cement manufacturers and civil engineers.',
        category: 'Sustainable Materials',
        format: 'IN_PERSON',
        venue_name: 'Shalimar',
        formatted_address: 'Shalimar, Nashik, Maharashtra 422001, India',
        location_lat: 20.0000,
        location_lng: 73.7848,
        timezone: 'Asia/Kolkata',
        start_date: '2026-11-15',
        end_date: '2026-11-17',
        start_time: '11:00:00',
        end_time: '17:00:00',
        capacity: 1000,
        target_audience: 'Civil Engineers',
        website_url: 'https://www.ultratechcement.com/summit',
        banner_url: 'https://example.com/banner.jpg',
        status: 'PUBLISHED',
        is_active: true,
        organizer: {
          id: 'org-pub-1',
          representative_name: 'Dr. Rajesh Sharma',
          organization_name: 'UltraTech Cement Ltd',
          designation: 'Chief Sustainability Officer',
          city: 'Mumbai',
          country: 'India',
          verification_status: 'VERIFIED',
          website_url: 'https://www.ultratechcement.com',
        },
        created_at: '2026-10-28T12:00:00Z',
        updated_at: '2026-10-28T12:00:00Z',
      },
    ]);
    vi.spyOn(agendaApi, 'getSessions').mockResolvedValue([]);

    renderAgenda();

    expect(await screen.findByRole('heading', { name: 'National Green Cement & LC3 Summit 2026' })).toBeInTheDocument();

    // Verify Organizer host badge & verification pill
    expect(screen.getByText('Hosted by:')).toBeInTheDocument();
    expect(screen.getByText(/UltraTech Cement Ltd/)).toBeInTheDocument();
    expect(screen.getByText('✓ Verified')).toBeInTheDocument();

    // Verify Category and Format pills
    expect(screen.getByText(/Sustainable Materials/)).toBeInTheDocument();
    expect(screen.getByText(/In-Person/)).toBeInTheDocument();

    // Verify Executive Summary
    expect(screen.getByText('Executive summit on decarbonizing heavy construction.')).toBeInTheDocument();

    // Verify Clickable Google Maps location link
    const mapLink = screen.getByRole('link', { name: /Shalimar, Nashik/i });
    expect(mapLink).toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=20,73.7848');

    // Verify official website external link
    expect(screen.getByRole('link', { name: /Website ↗/i })).toHaveAttribute(
      'href',
      'https://www.ultratechcement.com/summit'
    );
  });
});
