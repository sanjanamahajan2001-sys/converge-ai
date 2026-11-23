import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as adminApi from '@/lib/api/admin';
import { AdminLogin } from '@/routes/admin/AdminLogin';
import { AdminDashboard } from '@/routes/admin/AdminDashboard';
import { AdminUsers } from '@/routes/admin/AdminUsers';
import { AdminUserDetail } from '@/routes/admin/AdminUserDetail';
import { AdminOrganizers } from '@/routes/admin/AdminOrganizers';
import { AdminConferencesQueue } from '@/routes/admin/AdminConferencesQueue';
import { AdminConferenceReviewDetail } from '@/routes/admin/AdminConferenceReviewDetail';
import { AdminLayout } from '@/components/admin/AdminLayout';
import { AdminAuthProvider } from '@/lib/auth/AdminAuthContext';
import { ApiClientError } from '@/lib/api/client';

describe('Admin Authentication & Dashboard Foundation (Phase 2)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithProviders = (ui: React.ReactElement, initialRoute = '/admin/login') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AdminAuthProvider>
          <MemoryRouter initialEntries={[initialRoute]}>
            {ui}
          </MemoryRouter>
        </AdminAuthProvider>
      </QueryClientProvider>
    );
  };

  it('renders dedicated admin login form with default admin username', () => {
    renderWithProviders(<AdminLogin />);

    expect(screen.getByRole('heading', { name: /Converge AI Admin Portal/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Administrator Username/i)).toHaveValue('admin');
    expect(screen.getByLabelText(/Administrator Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In as Administrator/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Return to Attendee Conference Site/i })).toBeInTheDocument();
  });

  it('displays access denied alert when non-admin credentials receive 403 Forbidden', async () => {
    vi.spyOn(adminApi, 'adminLogin').mockRejectedValue(
      new ApiClientError(403, 'User does not have administrative privileges.')
    );

    renderWithProviders(<AdminLogin />);

    fireEvent.change(screen.getByLabelText(/Administrator Password/i), {
      target: { value: 'Secret12345!' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In as Administrator/i }));

    expect(
      await screen.findByText(/Access Denied: This account does not possess administrative privileges/i)
    ).toBeInTheDocument();
  });

  it('renders administrative layout with Users and Organizers tabs', async () => {
    vi.spyOn(adminApi, 'getAdminMe').mockResolvedValue({
      id: 'admin-uuid-1234',
      username: 'admin',
      email: 'admin@converge.ai',
      full_name: 'Converge Administrator',
      is_active: true,
      is_admin: true,
    });

    renderWithProviders(
      <AdminLayout>
        <div data-testid="admin-content">Admin Content Viewport</div>
      </AdminLayout>,
      '/admin'
    );

    // Verify header branding and badge
    expect(screen.getByText('Admin Portal')).toBeInTheDocument();
    expect(screen.getByText('Conference Control Plane')).toBeInTheDocument();

    // Verify navigation tabs
    expect(screen.getAllByRole('link', { name: /Users Directory/i })[0]).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Organizers/i })[0]).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: /Review Queue/i })[0]).toBeInTheDocument();

    // Verify admin user pill and sign out
    expect(await screen.findByText('admin')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign Out/i })).toBeInTheDocument();
  });

  it('renders dashboard metrics querying admin overview API', async () => {
    vi.spyOn(adminApi, 'getAdminOverview').mockResolvedValue({
      total_users: 142,
      active_users: 138,
      profile_completion_pct: 84.5,
      active_users_today: 47,
      total_conversations: 89,
      admin_username: 'admin',
      generated_at: new Date().toISOString(),
    });

    renderWithProviders(<AdminDashboard />, '/admin');

    expect(await screen.findByText('142')).toBeInTheDocument();
    expect(screen.getByText('138')).toBeInTheDocument();
    expect(screen.getByText('84.5%')).toBeInTheDocument();
    expect(screen.getByText('47')).toBeInTheDocument();
    expect(screen.getByText('89')).toBeInTheDocument();

    expect(screen.getByRole('link', { name: /Manage Users/i })).toBeInTheDocument();
  });

  it('renders active organizers directory with audit and verification modal', async () => {
    vi.spyOn(adminApi, 'getAdminOrganizers').mockResolvedValue({
      items: [
        {
          id: 'org-test-1',
          user_id: 'user-test-1',
          username: 'rajesh_ultra',
          organizer_type: 'COMPANY',
          representative_name: 'Dr. Rajesh Sharma',
          organization_name: 'UltraTech Cement Ltd',
          designation: 'Chief Sustainability Officer',
          professional_email: 'rajesh@ultratech.com',
          contact_phone: '+91 98200 12345',
          city: 'Mumbai',
          state_province: 'Maharashtra',
          country: 'India',
          focus_areas: ['Green Cement'],
          verification_status: 'PENDING_REVIEW',
          conferences_count: 2,
          created_at: '2026-10-28T12:00:00Z',
          updated_at: '2026-10-28T12:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
      total_pages: 1,
      stats: {
        total_organizers: 1,
        verified_count: 0,
        pending_review_count: 1,
        total_conferences_managed: 2,
      },
    });

    renderWithProviders(<AdminOrganizers />, '/admin/organizers');

    expect(await screen.findByRole('heading', { name: /Organizers Directory/i })).toBeInTheDocument();
    expect(await screen.findByText('Dr. Rajesh Sharma')).toBeInTheDocument();
    expect(screen.getByText('UltraTech Cement Ltd')).toBeInTheDocument();
    expect(screen.getAllByText('Pending Review').length).toBeGreaterThan(0);

    // Open audit modal
    fireEvent.click(screen.getByRole('button', { name: /Audit & Verify/i }));
    expect(screen.getByText(/Audit Organizer Profile/i)).toBeInTheDocument();
  });

  it('renders conference review queue and decision workflow for admin', async () => {
    vi.spyOn(adminApi, 'getAdminConferences').mockResolvedValue({
      items: [
        {
          id: 'conf-aiims-1',
          organizer_id: 'org-uid-1',
          organizer: {
            id: 'prof-uid-1',
            user_id: 'org-uid-1',
            username: 'arun_aiims',
            representative_name: 'Prof. Dr. Arun Mukherjee',
            organization_name: 'AIIMS New Delhi',
            designation: 'Head of Urology',
            professional_email: 'arun@aiims.edu',
            contact_phone: '+91 98100 54321',
            city: 'New Delhi',
            country: 'India',
            verification_status: 'VERIFIED',
          },
          title: 'National Robotic Surgery Congress 2027',
          summary: 'Clinical surgical robotics congress.',
          category: 'Healthcare & MedTech',
          format: 'IN_PERSON',
          venue_name: 'AIIMS JLN Auditorium',
          timezone: 'Asia/Kolkata',
          start_date: '2027-01-22',
          end_date: '2027-01-24',
          city: 'New Delhi',
          country: 'India',
          capacity: 800,
          status: 'IN_REVIEW',
          sessions_count: 3,
          published_at: null,
          created_at: '2026-10-28T12:00:00Z',
          updated_at: '2026-10-28T12:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
      total_pages: 1,
      stats: {
        total_in_review: 1,
        total_published: 0,
        total_draft: 0,
        total_changes_requested: 0,
        total_rejected: 0,
      },
    });

    renderWithProviders(<AdminConferencesQueue />, '/admin/conferences');

    expect(await screen.findByRole('heading', { name: /Conference Approvals & Publication/i })).toBeInTheDocument();
    expect(await screen.findByText('National Robotic Surgery Congress 2027')).toBeInTheDocument();
    expect(screen.getByText('AIIMS New Delhi')).toBeInTheDocument();
    expect(screen.getByText('Under Review')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Inspect & Decide/i })).toBeInTheDocument();
  });

  it('renders users directory with server-side statistics, search bar, and user items', async () => {
    vi.spyOn(adminApi, 'getAdminUsers').mockResolvedValue({
      items: [
        {
          id: 'u-1',
          username: 'sarah_chen',
          email: 'sarah@example.com',
          full_name: 'Sarah Chen',
          company_name: 'RoboTech Labs',
          job_title: 'Lead Architect',
          phone_number: '+1-555-0199',
          is_active: true,
          is_admin: false,
          created_at: '2026-10-20T10:00:00Z',
          updated_at: '2026-10-21T10:00:00Z',
          has_profile: true,
          bio_summary: 'AI Systems Researcher exploring agentic coordination.',
          gender: 'Female',
          date_of_birth: '1990-05-15',
          location: 'Nashik, Maharashtra',
          intent: 'NETWORKING',
          availability: 'AVAILABLE',
          allow_agent_matching: true,
          current_mood: 'Curious',
          hobbies: ['Robotics', 'Hiking'],
          topics: ['Machine Learning', 'Autonomous Agents'],
          bookmarks_count: 5,
          attendance_count: 3,
          conversations_count: 2,
          activity_events_count: 14,
          last_active_at: '2026-10-28T09:30:00Z',
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
      total_pages: 1,
      stats: {
        total_users: 42,
        active_users: 38,
        inactive_users: 4,
        with_profile: 35,
        active_today: 19,
      },
    });

    renderWithProviders(<AdminUsers />, '/admin/users');

    // Verify statistics cards
    expect(await screen.findByText('42')).toBeInTheDocument();
    expect(screen.getByText('38')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('35')).toBeInTheDocument();
    expect(screen.getByText('19')).toBeInTheDocument();

    // Verify user row content
    expect(screen.getAllByText('Sarah Chen')[0]).toBeInTheDocument();
    expect(screen.getAllByText('@sarah_chen')[0]).toBeInTheDocument();
    expect(screen.getAllByText('sarah@example.com')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Nashik, Maharashtra')[0]).toBeInTheDocument();

    // Verify search input
    const searchInput = screen.getByPlaceholderText(/Search by full name/i);
    expect(searchInput).toBeInTheDocument();

    // Inspect user drawer
    fireEvent.click(screen.getAllByRole('button', { name: /Inspect/i })[0]);
    expect(await screen.findByText(/AI Systems Researcher exploring agentic coordination/i)).toBeInTheDocument();
    expect(screen.getAllByText('RoboTech Labs')[0]).toBeInTheDocument();
    expect(screen.getAllByText('Lead Architect')[0]).toBeInTheDocument();
  });

  it('renders comprehensive user detail view with all footprint tabs (Phase 4)', async () => {
    vi.spyOn(adminApi, 'getAdminUserDetail').mockResolvedValue({
      account: {
        id: 'u-detail-1234',
        username: 'sanjana_m',
        email: 'sanjana@converge.ai',
        full_name: 'Sanjana Mahajan',
        company_name: 'Converge Labs',
        job_title: 'Research Engineer',
        phone_number: '+91 99999 88888',
        is_active: true,
        is_admin: false,
        created_at: '2026-10-25T08:00:00Z',
        updated_at: '2026-10-28T08:00:00Z',
      },
      profile: {
        has_profile: true,
        bio_summary: 'Designing agent coordination protocols for industrial events.',
        gender: 'Female',
        date_of_birth: '1995-04-12',
        location: 'Jio World Convention Centre, Mumbai',
        location_lat: 19.0657,
        location_lng: 72.8687,
        intent: 'NETWORKING',
        availability: 'AVAILABLE',
        allow_agent_matching: true,
        current_mood: 'Ready to build',
        hobbies: ['Robotics', 'Chess'],
        topics: ['Agent Swarms', 'Conference Intelligence'],
      },
      sessions: {
        total_logins: 12,
        active_sessions_count: 2,
        recent_sessions: [
          {
            id: 'sess-1',
            created_at: '2026-10-28T07:00:00Z',
            expires_at: '2026-10-29T07:00:00Z',
            last_accessed_at: '2026-10-28T08:30:00Z',
            revoked_at: null,
            is_active: true,
            ip_address: '192.46.210.48',
            user_agent: 'Mozilla/5.0 Chrome',
          },
        ],
      },
      agenda: {
        bookmarks_count: 2,
        bookmarks: [
          {
            session_id: 'sess-item-1',
            title: 'Opening Keynote: Next-Gen Agent Networks',
            track_name: 'Keynotes',
            hall_room: 'Hall A',
            speaker_names: 'Dr. Evelyn Reed',
            start_time: '2026-10-29T09:00:00Z',
            end_time: '2026-10-29T10:00:00Z',
            created_at: '2026-10-26T12:00:00Z',
          },
        ],
        attendance_decisions: [
          {
            session_id: 'sess-item-1',
            title: 'Opening Keynote: Next-Gen Agent Networks',
            decision: 'ATTENDING',
            hall_room: 'Hall A',
            start_time: '2026-10-29T09:00:00Z',
            end_time: '2026-10-29T10:00:00Z',
          },
        ],
      },
      conversations: {
        total_count: 3,
        initiated_count: 2,
        participated_count: 1,
        history: [
          {
            conversation_id: 'conv-1',
            partner_id: 'partner-uuid-1',
            partner_name: 'Alex Rivera',
            partner_username: 'arivera',
            role: 'INITIATOR',
            status: 'CONCLUDED',
            outcome: 'PROPOSAL_GENERATED',
            message_count: 14,
            created_at: '2026-10-27T14:00:00Z',
            last_interaction_at: '2026-10-27T14:45:00Z',
          },
        ],
      },
      activity: {
        total_events: 28,
        recent_events: [
          {
            id: 1,
            event_type: 'FEATURE_CLICK',
            feature_name: 'AGENDA_BOOKMARK',
            target_resource_id: 'sess-item-1',
            created_at: '2026-10-28T08:15:00Z',
          },
        ],
      },
    });

    renderWithProviders(
      <Routes>
        <Route path="/admin/users/:userId" element={<AdminUserDetail />} />
      </Routes>,
      '/admin/users/u-detail-1234'
    );

    // Header identity
    expect(await screen.findByText('Sanjana Mahajan')).toBeInTheDocument();
    expect(screen.getAllByText(/@sanjana_m/i)[0]).toBeInTheDocument();
    expect(screen.getByText(/Active Account/i)).toBeInTheDocument();

    // Profile tab contents
    expect(screen.getByText('Designing agent coordination protocols for industrial events.')).toBeInTheDocument();
    expect(screen.getByText('Jio World Convention Centre, Mumbai')).toBeInTheDocument();
    expect(screen.getByText('#Agent Swarms')).toBeInTheDocument();
    expect(screen.getByText('Robotics')).toBeInTheDocument();

    // Tab switcher: Agenda
    fireEvent.click(screen.getByRole('button', { name: /Agenda & Intentions/i }));
    expect((await screen.findAllByText('Opening Keynote: Next-Gen Agent Networks'))[0]).toBeInTheDocument();
    expect(screen.getByText('Dr. Evelyn Reed')).toBeInTheDocument();
    expect(screen.getAllByText('Hall A')[0]).toBeInTheDocument();

    // Tab switcher: Dialogue History
    fireEvent.click(screen.getByRole('button', { name: /Dialogue History/i }));
    expect(await screen.findByText('Alex Rivera')).toBeInTheDocument();
    expect(screen.getByText('@arivera')).toBeInTheDocument();
    expect(screen.getByText('PROPOSAL_GENERATED')).toBeInTheDocument();
  });

  it('renders commercial profile, catalog offerings, and procurement requirements in AdminUserDetail (Phase B)', async () => {
    vi.spyOn(adminApi, 'getAdminUserDetail').mockResolvedValue({
      account: {
        id: 'u-maahi-1234',
        username: 'maahi',
        email: 'maahi@materials.com',
        full_name: 'Maahi Sharma',
        company_name: 'Maahi Decarb Materials Pvt Ltd',
        job_title: 'Commercial Director',
        phone_number: '+91 98765 43210',
        is_active: true,
        is_admin: false,
        created_at: '2026-10-25T10:00:00Z',
        updated_at: '2026-10-28T10:00:00Z',
      },
      profile: {
        has_profile: true,
        bio_summary: 'Decarbonized cement pioneer in Pune.',
        gender: 'Female',
        date_of_birth: '1990-05-15',
        location: 'Pune, Maharashtra',
        location_lat: 18.5204,
        location_lng: 73.8567,
        intent: 'BUSINESS_PARTNERSHIP',
        availability: 'AVAILABLE',
        allow_agent_matching: true,
        current_mood: 'Eager to partner',
        hobbies: ['Sustainable Design'],
        topics: ['LC3', 'Decarbonization'],
      },
      business_profile: {
        id: 'bp-maahi-1',
        user_id: 'u-maahi-1234',
        company_name: 'Maahi Decarb Materials Pvt Ltd',
        industry: 'Green Building Materials',
        business_website: 'https://maahidecarb.com',
        hq_city: 'Pune',
        hq_country: 'India',
        company_bio: 'Manufacturer and regional distributor of low-carbon LC3 cements.',
        is_buyer: false,
        is_supplier: true,
        is_vendor: false,
        is_distributor: true,
        is_partner: false,
        allow_business_matching: true,
        warehousing_capacity_sqft: 45000,
        retail_dealer_count: 180,
        distributor_territories: ['Pune', 'Mumbai', 'Western Maharashtra'],
        partnership_types: ['Supply Agreement', 'Distributor Alliance'],
        partnership_interests: ['Feedstock Synergy'],
        offerings: [
          {
            id: 'off-1',
            business_profile_id: 'bp-maahi-1',
            custom_product_title: 'Limestone Calcined Clay Cement (LC3)',
            product_code: 'LC3',
            grade_code: 'LC3-50',
            service_code: null,
            specifications_text: 'High durability low clinker binder conforming to draft standard.',
            declared_monthly_capacity: 2500,
            declared_committed_volume: 0,
            capacity_unit: 'METRIC TONNE',
            minimum_order_quantity: 100,
            lead_time_days: 5,
            geographic_coverage: ['Pune', 'Mumbai', 'Nashik'],
            offers_test_certificates: true,
            vendor_certifications: ['ISO 9001:2015', 'NABL Accredited'],
            open_to_distribution: true,
            target_distribution_regions: ['Western Maharashtra'],
            distributor_tier_preferred: 'Tier 1 Regional Stockist',
            is_public_indicative: true,
            indicative_price_min: 4900,
            indicative_price_max: 5100,
            price_currency: 'INR',
            pricing_basis: 'EX_WORKS',
            offers_delivered_pricing: false,
            quote_validity_days: 30,
            is_active: true,
            created_at: '2026-10-26T10:00:00Z',
            updated_at: '2026-10-26T10:00:00Z',
          },
        ],
        requirements: [
          {
            id: 'req-1',
            business_profile_id: 'bp-maahi-1',
            custom_requirement_title: 'High-Purity Clinker Feedstock',
            product_code: 'CLINKER_FEEDSTOCK',
            grade_code: null,
            service_code: null,
            required_quantity: 1200,
            quantity_unit: 'METRIC TONNE',
            delivery_city: 'Pune',
            delivery_country: 'India',
            target_timeline_days: 21,
            target_budget_indication: 3400,
            is_budget_public: false,
            urgency: 'IMMEDIATE',
            excluded_supplier_ids: [],
            allow_substitutes: true,
            required_certifications: ['IS 16415'],
            is_feedstock_procurement: true,
            notes: 'Requires 30-day delivery to Pune facility.',
            is_active: true,
            created_at: '2026-10-26T10:00:00Z',
            updated_at: '2026-10-26T10:00:00Z',
          },
        ],
        created_at: '2026-10-26T10:00:00Z',
        updated_at: '2026-10-26T10:00:00Z',
      },
      sessions: {
        total_logins: 5,
        active_sessions_count: 1,
        recent_sessions: [],
      },
      agenda: {
        bookmarks_count: 0,
        bookmarks: [],
        attendance_decisions: [],
      },
      conversations: {
        total_count: 0,
        initiated_count: 0,
        participated_count: 0,
        history: [],
      },
      activity: {
        total_events: 0,
        recent_events: [],
      },
    });

    renderWithProviders(
      <Routes>
        <Route path="/admin/users/:userId" element={<AdminUserDetail />} />
      </Routes>,
      '/admin/users/u-maahi-1234'
    );

    // Verify header banner contains commercial role badges and matching consent
    expect(await screen.findByText('Maahi Sharma')).toBeInTheDocument();
    expect(screen.getByText('Commercial Matching')).toBeInTheDocument();
    expect(screen.getByText('Supplier')).toBeInTheDocument();
    expect(screen.getByText('Distributor')).toBeInTheDocument();

    // Verify Commercial & Catalog tab button has count 2 (1 offering + 1 requirement)
    const commercialTab = screen.getByRole('button', { name: /Commercial & Catalog/i });
    expect(commercialTab).toBeInTheDocument();
    expect(commercialTab).toHaveTextContent('2');

    // Switch to Commercial tab
    fireEvent.click(commercialTab);

    // Verify Commercial Profile Overview
    expect((await screen.findAllByText('Maahi Decarb Materials Pvt Ltd')).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Green Building Materials/i)).toBeInTheDocument();
    expect(screen.getByText(/45,000 sq ft/i)).toBeInTheDocument();
    expect(screen.getByText(/180 retail outlets/i)).toBeInTheDocument();

    // Verify Catalog Offering details
    expect(screen.getByText('Limestone Calcined Clay Cement (LC3)')).toBeInTheDocument();
    expect(screen.getByText(/₹4,900/)).toBeInTheDocument();
    expect(screen.getByText(/₹5,100/)).toBeInTheDocument();
    expect(screen.getByText(/2,500 METRIC TONNE/)).toBeInTheDocument();
    expect(screen.getByText(/MTC \/ Test Certs/i)).toBeInTheDocument();

    // Verify Procurement Requirement details with budget privacy preserved
    expect(screen.getByText('High-Purity Clinker Feedstock')).toBeInTheDocument();
    expect(screen.getByText(/1,200 METRIC TONNE/)).toBeInTheDocument();
    expect(screen.getByText(/Private \/ Negotiated/i)).toBeInTheDocument();
    expect(screen.getByText(/Compatible Substitutes Accepted/i)).toBeInTheDocument();
    expect(screen.getByText(/Feedstock Sourcing/i)).toBeInTheDocument();
  });

  it('handles account suspension confirmation modal and status mutation (Phase 4)', async () => {
    vi.spyOn(adminApi, 'getAdminUserDetail').mockResolvedValue({
      account: {
        id: 'u-detail-suspend',
        username: 'troublemaker',
        email: 'bad@example.com',
        full_name: 'Test Attacker',
        company_name: null,
        job_title: null,
        phone_number: null,
        is_active: true,
        is_admin: false,
        created_at: '2026-10-25T08:00:00Z',
        updated_at: '2026-10-28T08:00:00Z',
      },
      profile: {
        has_profile: false,
        hobbies: [],
        topics: [],
      },
      sessions: { total_logins: 1, active_sessions_count: 1, recent_sessions: [] },
      agenda: { bookmarks_count: 0, bookmarks: [], attendance_decisions: [] },
      conversations: { total_count: 0, initiated_count: 0, participated_count: 0, history: [] },
      activity: { total_events: 0, recent_events: [] },
    });

    const statusSpy = vi.spyOn(adminApi, 'updateAdminUserStatus').mockResolvedValue({
      status: 'success',
      user_id: 'u-detail-suspend',
      is_active: false,
      revoked_sessions_count: 1,
      detail: 'User has been suspended.',
    });

    renderWithProviders(
      <Routes>
        <Route path="/admin/users/:userId" element={<AdminUserDetail />} />
      </Routes>,
      '/admin/users/u-detail-suspend'
    );

    expect(await screen.findByText('Test Attacker')).toBeInTheDocument();

    // Click suspend button to open modal
    fireEvent.click(screen.getByRole('button', { name: /Suspend Account/i }));
    expect(screen.getByText('Suspend Participant Account')).toBeInTheDocument();

    // Confirm suspension
    fireEvent.click(screen.getByRole('button', { name: /Confirm Suspension/i }));
    await waitFor(() => {
      expect(statusSpy).toHaveBeenCalledWith('u-detail-suspend', {
        is_active: false,
        reason: undefined,
      });
    });
  });

  it('renders conference review detail with clickable Google Maps location links and rich organizer credentials', async () => {
    vi.spyOn(adminApi, 'getAdminConferenceDetail').mockResolvedValue({
      id: 'conf-detail-1',
      organizer_id: 'org-1',
      organizer: {
        id: 'prof-1',
        user_id: 'org-1',
        username: 'ultratech_lead',
        representative_name: 'Dr. Rajesh Sharma',
        organization_name: 'UltraTech Cement Ltd',
        organizer_type: 'COMPANY',
        designation: 'Chief Sustainability Officer',
        professional_email: 'rajesh@ultratech.com',
        contact_phone: '+91 98200 12345',
        website_url: 'https://www.ultratechcement.com',
        city: 'Mumbai',
        state_province: 'Maharashtra',
        country: 'India',
        bio: 'Leading low-carbon binder manufacturing and sustainable cement research.',
        focus_areas: ['Green Cement', 'LC3 Technology'],
        experience_years: 15,
        verification_status: 'VERIFIED',
      },
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
      status: 'IN_REVIEW',
      sessions: [
        {
          id: 'sess-1',
          conference_id: 'conf-detail-1',
          title: 'Formulating LC3 Clays for BIS Compliance',
          abstract: 'Engineering analysis of compressive strength.',
          speaker_names: 'Dr. Rajesh Kumar Sharma',
          track_name: 'Keynote',
          hall_room: 'Grand Pavilion Hall A',
          start_time: '2026-11-15T15:45:00Z',
          end_time: '2026-11-15T17:30:00Z',
          is_cancelled: false,
          created_at: '2026-10-28T12:00:00Z',
        },
      ],
      review_logs: [
        {
          id: 1,
          reviewer_id: null,
          reviewer_username: null,
          from_status: 'DRAFT',
          to_status: 'IN_REVIEW',
          notes: 'Conference submitted by organizer.',
          created_at: '2026-10-28T12:30:00Z',
        },
      ],
      created_at: '2026-10-28T12:00:00Z',
      updated_at: '2026-10-28T12:30:00Z',
    });

    renderWithProviders(
      <Routes>
        <Route path="/admin/conferences/:id" element={<AdminConferenceReviewDetail />} />
      </Routes>,
      '/admin/conferences/conf-detail-1'
    );

    expect(await screen.findByRole('heading', { name: 'National Green Cement & LC3 Summit 2026' })).toBeInTheDocument();

    // Verify Google Maps location links exist with correct coordinates URL
    const mapLinks = screen.getAllByRole('link', { name: /Shalimar, Nashik|Open Map/i });
    expect(mapLinks.length).toBeGreaterThan(0);
    expect(mapLinks[0]).toHaveAttribute('href', 'https://www.google.com/maps/search/?api=1&query=20,73.7848');

    // Switch to Organizer tab and check rich entity fields
    fireEvent.click(screen.getByRole('button', { name: /Organizer Entity/i }));
    expect(await screen.findByText('UltraTech Cement Ltd')).toBeInTheDocument();
    expect(screen.getByText('COMPANY')).toBeInTheDocument();
    expect(screen.getByText(/15 years in event production/i)).toBeInTheDocument();
    expect(screen.getByText(/LC3 Technology/)).toBeInTheDocument();
    expect(screen.getByText(/Leading low-carbon binder manufacturing/i)).toBeInTheDocument();
  });
});
