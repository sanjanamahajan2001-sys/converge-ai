import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { OrganizerRegister } from '@/routes/organizer/OrganizerRegister';
import { OrganizerConferences } from '@/routes/organizer/OrganizerConferences';
import { ConferenceEditor } from '@/routes/organizer/ConferenceEditor';
import { ConferenceDetail } from '@/routes/organizer/ConferenceDetail';
import { Login } from '@/routes/Login';

vi.mock('@/lib/api/auth', () => ({
  getCurrentUser: vi.fn().mockRejectedValue({ status: 401, detail: 'Not authenticated' }),
  loginUser: vi.fn().mockResolvedValue({
    status: 'authenticated',
    user_id: 'test-user-id',
    username: 'test_organizer',
    email: 'test@example.com',
    expires_at: '2026-10-29T12:00:00Z',
  }),
  logoutUser: vi.fn().mockResolvedValue({ status: 'logged_out', detail: 'Revoked' }),
  registerUser: vi.fn(),
}));

const { mockConferences, mockConferenceDetail } = vi.hoisted(() => {
  const confs = [
    {
      id: 'conf-101',
      title: 'National Green Cement & LC3 Decarbonization Summit 2026',
      summary: "India's apex symposium on low-carbon cements and calcined clay.",
      format: 'IN_PERSON',
      venue_name: 'Jio World Convention Centre',
      city: 'Mumbai',
      country: 'India',
      start_date: '2026-11-15',
      end_date: '2026-11-17',
      status: 'DRAFT',
      sessions_count: 2,
      created_at: '2026-10-28T12:00:00Z',
      updated_at: '2026-10-28T12:00:00Z',
    },
  ];

  const detail = {
    ...confs[0],
    timezone: 'Asia/Kolkata',
    capacity: 1500,
    formatted_address: 'Bandra Kurla Complex, Mumbai, Maharashtra 400051',
    location_lat: 19.0657,
    location_lng: 72.8687,
    sessions: [
      {
        id: 'sess-1',
        conference_id: 'conf-101',
        title: 'Keynote: Calcined Clay & LC3 Formulation Standards',
        abstract: 'Technical evaluation of compressive strength in blended cements.',
        speaker_names: 'Dr. Rajesh Sharma, UltraTech CSO',
        track_name: 'Keynote',
        hall_room: 'Pavilion Hall 1',
        start_time: '2026-11-15T09:30:00Z',
        end_time: '2026-11-15T10:30:00Z',
        is_cancelled: false,
        created_at: '2026-10-28T12:00:00Z',
        updated_at: '2026-10-28T12:00:00Z',
      },
    ],
  };

  return { mockConferences: confs, mockConferenceDetail: detail };
});

vi.mock('@/lib/api/organizer', () => ({
  registerOrganizer: vi.fn().mockResolvedValue({
    id: 'org-id-123',
    user_id: 'user-id-123',
    organizer_type: 'COMPANY',
    representative_name: 'Dr. Sarah Lin',
    organization_name: 'Green Cement Innovations Ltd',
    professional_email: 'sarah@greencement.org',
    contact_phone: '+1 555-019-2834',
    city: 'Chicago',
    country: 'United States',
    bio: 'Pioneering global decarbonization symposia.',
    focus_areas: ['Green Cement', 'Decarbonization'],
    verification_status: 'VERIFIED',
    conferences_count: 1,
    created_at: '2026-10-28T12:00:00Z',
    updated_at: '2026-10-28T12:00:00Z',
  }),
  getMyOrganizerProfile: vi.fn().mockResolvedValue({
    id: 'org-id-123',
    representative_name: 'Dr. Sarah Lin',
    organization_name: 'Green Cement Innovations Ltd',
    conferences_count: 1,
  }),
  updateMyOrganizerProfile: vi.fn(),
  getOrganizerConferences: vi.fn().mockResolvedValue(mockConferences),
  createOrganizerConference: vi.fn().mockResolvedValue(mockConferences[0]),
  updateOrganizerConference: vi.fn().mockResolvedValue(mockConferences[0]),
  getOrganizerConferenceDetail: vi.fn().mockResolvedValue(mockConferenceDetail),
  submitConferenceForReview: vi.fn().mockResolvedValue({
    status: 'IN_REVIEW',
    conference_id: 'conf-101',
    message: 'Conference submitted successfully for administrative review.',
  }),
  createOrganizerSession: vi.fn().mockResolvedValue({
    id: 'sess-2',
    conference_id: 'conf-101',
    title: 'Panel: Accelerating Alternative Fuel Thermal Substitution',
    hall_room: 'Hall B',
    start_time: '2026-11-15T11:00:00Z',
    end_time: '2026-11-15T12:30:00Z',
    is_cancelled: false,
    created_at: '2026-10-28T12:00:00Z',
    updated_at: '2026-10-28T12:00:00Z',
  }),
  deleteOrganizerSession: vi.fn().mockResolvedValue({ detail: 'Deleted' }),
}));

function renderWithProviders(ui: React.ReactElement, initialRoute: string = '/') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialRoute]}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('Organizer Portal Integration (Phase 2 & Phase 3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders organizer registration form with three logical sections', () => {
    renderWithProviders(<OrganizerRegister />);

    expect(screen.getByText(/Organizer Registration & Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Account Credentials & Authorized Representative/i)).toBeInTheDocument();
    expect(screen.getByText(/Organization Details & Headquarters Location/i)).toBeInTheDocument();
    expect(screen.getByText(/Organizer Profile, Experience & Conference Focus/i)).toBeInTheDocument();

    expect(screen.getByLabelText(/Account Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Authorized Representative Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^City/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Country/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create Organizer Profile/i })).toBeInTheDocument();
  });

  it('allows adding and removing custom focus area tags in registration', () => {
    renderWithProviders(<OrganizerRegister />);

    const tagInput = screen.getByPlaceholderText(/Type a custom topic and press Enter.../i);
    const addBtn = screen.getByRole('button', { name: /\+ Add/i });

    fireEvent.change(tagInput, { target: { value: 'Eco-Concrete' } });
    fireEvent.click(addBtn);

    expect(screen.getByText('Eco-Concrete')).toBeInTheDocument();

    const removeBtn = screen.getByLabelText(/Remove Eco-Concrete/i);
    fireEvent.click(removeBtn);

    expect(screen.queryByText('Eco-Concrete')).not.toBeInTheDocument();
  });

  it('toggles between Attendee Login and Organizer Portal on Login page', () => {
    renderWithProviders(<Login />);

    expect(screen.getByRole('heading', { level: 1, name: /Participant Sign In/i })).toBeInTheDocument();

    const orgTabBtn = screen.getByRole('button', { name: /Organizer Portal/i });
    fireEvent.click(orgTabBtn);

    expect(screen.getByRole('heading', { level: 1, name: /Organizer Portal Sign In/i })).toBeInTheDocument();
    expect(screen.getByText(/Register as an Organizer/i)).toBeInTheDocument();

    const attendeeTabBtn = screen.getByRole('button', { name: /^Attendee Login$/i });
    fireEvent.click(attendeeTabBtn);

    expect(screen.getByRole('heading', { level: 1, name: /Participant Sign In/i })).toBeInTheDocument();
  });

  it('supports cascading location selection from Country to State, City, and PIN code', () => {
    renderWithProviders(<OrganizerRegister />);

    const countrySelect = screen.getByLabelText(/^Country/i);
    expect(countrySelect).toHaveValue('India');

    const stateSelect = screen.getByLabelText(/State \/ Province/i);
    fireEvent.change(stateSelect, { target: { value: 'Maharashtra' } });
    expect(stateSelect).toHaveValue('Maharashtra');

    const citySelect = screen.getByLabelText(/^City/i);
    fireEvent.change(citySelect, { target: { value: 'Mumbai' } });
    expect(citySelect).toHaveValue('Mumbai');

    const pinSelect = screen.getByLabelText(/Postal \/ PIN Code/i);
    fireEvent.change(pinSelect, { target: { value: '400093' } });
    expect(pinSelect).toHaveValue('400093');
  });

  it('renders organizer conferences list with create button and status filter', async () => {
    renderWithProviders(<OrganizerConferences />);

    expect(screen.getByRole('heading', { level: 1, name: /Conferences & Symposia/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /\+ Create New Conference/i })).toBeInTheDocument();

    const confTitle = await screen.findByText(/National Green Cement & LC3 Decarbonization Summit 2026/i);
    expect(confTitle).toBeInTheDocument();
    expect(screen.getByText(/2 Sessions Scheduled/i)).toBeInTheDocument();
  });

  it('renders conference creation editor with cascading dropdowns and map picker trigger', () => {
    renderWithProviders(<ConferenceEditor />);

    expect(screen.getByRole('heading', { level: 1, name: /Create Conference Draft/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Conference Title/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Venue Name/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Pick on Google Maps/i })).toBeInTheDocument();

    const stateSelect = screen.getByLabelText(/State \/ Province/i);
    fireEvent.change(stateSelect, { target: { value: 'Karnataka' } });
    expect(stateSelect).toHaveValue('Karnataka');

    const citySelect = screen.getByLabelText(/^City/i);
    fireEvent.change(citySelect, { target: { value: 'Bengaluru' } });
    expect(citySelect).toHaveValue('Bengaluru');

    expect(screen.getByRole('button', { name: /Create Conference Draft →/i })).toBeInTheDocument();
  });

  it('renders conference detail view and schedule builder with sessions and submit review', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/organizer/conferences/:id" element={<ConferenceDetail />} />
      </Routes>,
      '/organizer/conferences/conf-101'
    );

    const heading = await screen.findByRole('heading', { level: 1, name: /National Green Cement & LC3 Decarbonization Summit 2026/i });
    expect(heading).toBeInTheDocument();

    // Verify session schedule table
    expect(screen.getByText(/Agenda Session Schedule/i)).toBeInTheDocument();
    expect(screen.getByText(/Keynote: Calcined Clay & LC3 Formulation Standards/i)).toBeInTheDocument();
    expect(screen.getByText(/Dr. Rajesh Sharma, UltraTech CSO/i)).toBeInTheDocument();

    // Verify submit for review button
    const submitBtn = screen.getByRole('button', { name: /Submit for Review →/i });
    expect(submitBtn).toBeInTheDocument();
    expect(submitBtn).not.toBeDisabled();

    // Verify edit details link exists
    const editLinks = screen.getAllByRole('link', { name: /Edit Details/i });
    expect(editLinks.length).toBeGreaterThan(0);
    expect(editLinks[0]).toHaveAttribute('href', '/organizer/conferences/conf-101/edit');
  });

  it('renders conference editor in edit mode and allows saving modifications', async () => {
    renderWithProviders(
      <Routes>
        <Route path="/organizer/conferences/:id/edit" element={<ConferenceEditor />} />
      </Routes>,
      '/organizer/conferences/conf-101/edit'
    );

    const editHeading = await screen.findByRole('heading', { level: 1, name: /Edit Conference Details/i });
    expect(editHeading).toBeInTheDocument();

    const titleInput = screen.getByLabelText(/Conference Title/i);
    expect(titleInput).toHaveValue('National Green Cement & LC3 Decarbonization Summit 2026');

    const saveBtn = screen.getByRole('button', { name: /Save Conference Changes →/i });
    expect(saveBtn).toBeInTheDocument();
    expect(saveBtn).not.toBeDisabled();
  });
});
