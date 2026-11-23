import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { OrganizerDashboard } from '@/routes/organizer/OrganizerDashboard';
import { OrganizerRegister } from '@/routes/organizer/OrganizerRegister';

vi.mock('@/lib/api/auth', () => ({
  getCurrentUser: vi.fn().mockResolvedValue({
    id: 'org-user-1',
    username: 'apex_organizer',
    email: 'apex@summit.org',
    full_name: 'Apex Host',
    is_organizer: true,
  }),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
}));

vi.mock('@/lib/api/organizer', () => ({
  getMyOrganizerProfile: vi.fn().mockResolvedValue({
    id: 'org-profile-1',
    user_id: 'org-user-1',
    organizer_type: 'COMPANY',
    representative_name: 'Prajyot Mainkar',
    organization_name: 'Apex Decarbonization Summits Ltd',
    designation: 'Managing Director',
    professional_email: 'prajyot@apexsummit.com',
    contact_phone: '+91 98200 12345',
    city: 'Mumbai',
    country: 'India',
    bio: 'Apex Summits curates premier decarbonization expos and industrial forums across India.',
    focus_areas: ['Green Cement', 'Decarbonization'],
    verification_status: 'VERIFIED',
    conferences_count: 3,
    created_at: '2026-11-01T10:00:00Z',
  }),
  registerOrganizer: vi.fn().mockResolvedValue({
    status: 'registered',
    organizer: { id: 'new-org-id', organization_name: 'New Apex Ltd' },
  }),
}));

vi.mock('@/lib/api/brochures', () => ({
  brochureApi: {
    uploadPage: vi.fn().mockResolvedValue({
      id: 'page-1',
      page_number: 1,
      image_url: '/uploads/page_001.jpg',
    }),
  },
}));

describe('Organizer Onboarding & Summit Brochure Integration (Phase 3.5)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    vi.clearAllMocks();
  });

  it('renders OrganizerDashboard with Summit Brochure Studio card and action buttons', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/organizer']}>
            <Routes>
              <Route path="/organizer" element={<OrganizerDashboard />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Apex Decarbonization Summits Ltd')).toBeInTheDocument();

    // Verify Brochure Studio in top action buttons
    const studioLinks = screen.getAllByRole('link', { name: /Brochure Studio/i });
    expect(studioLinks.length).toBeGreaterThan(0);
    expect(studioLinks[0]).toHaveAttribute('href', '/company/brochure');

    // Verify Master Digital Brochure card in dashboard body
    expect(screen.getByText('Master Digital Brochure & Floor Guide')).toBeInTheDocument();
    expect(screen.getByText(/Upload your organization's official summit handbook/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open Studio/i })).toHaveAttribute('href', '/company/brochure');
  });

  it('displays Step 2 optional brochure onboarding upon successful organizer registration', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/register/organizer']}>
            <Routes>
              <Route path="/register/organizer" element={<OrganizerRegister />} />
              <Route path="/organizer" element={<div>Organizer Dashboard Mock</div>} />
              <Route path="/company/brochure" element={<div>Brochure Studio Mock</div>} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Fill registration fields
    fireEvent.change(screen.getByLabelText(/Account Username \*/i), { target: { value: 'apex_host' } });
    fireEvent.change(screen.getByLabelText(/^Password \*/i), { target: { value: 'SecurePass123!' } });
    fireEvent.change(screen.getByLabelText(/Account Full Name \*/i), { target: { value: 'Prajyot Mainkar' } });
    fireEvent.change(screen.getByLabelText(/Account Email \*/i), { target: { value: 'host@apex.org' } });
    fireEvent.change(screen.getByLabelText(/Organization \/ Company \/ Institution Name/i), { target: { value: 'Global Green Summits' } });
    fireEvent.change(screen.getByLabelText(/Authorized Representative Name \*/i), { target: { value: 'Prajyot Mainkar' } });
    fireEvent.change(screen.getByLabelText(/Professional Work Email \*/i), { target: { value: 'prajyot@apex.org' } });
    fireEvent.change(screen.getByLabelText(/Contact Phone Number \*/i), { target: { value: '+91 9988776655' } });
    fireEvent.change(screen.getByLabelText(/City \*/i), { target: { value: 'Mumbai' } });
    fireEvent.change(screen.getByLabelText(/Organizer Biography \/ Mission Overview \*/i), { target: { value: 'Organizing green cement events and exhibitions across western India.' } });

    // Submit registration form
    const submitBtn = screen.getByRole('button', { name: /Create Organizer Profile/i });
    fireEvent.click(submitBtn);

    // Verify Step 2: Optional Brochure Setup renders
    await waitFor(() => {
      expect(screen.getByText(/Step 2 of 2 \(Optional\)/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Upload Brochure \/ Summit Guide Pages/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Skip for now, I'll add this later/i })).toBeInTheDocument();

    // Clicking Skip for now navigates to organizer dashboard
    fireEvent.click(screen.getByRole('button', { name: /Skip for now, I'll add this later/i }));
    await waitFor(() => {
      expect(screen.getByText('Organizer Dashboard Mock')).toBeInTheDocument();
    });
  });
});
