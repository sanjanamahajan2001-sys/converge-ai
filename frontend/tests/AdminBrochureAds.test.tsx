import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AdminBrochureAds } from '@/routes/admin/AdminBrochureAds';
import { adminBrochureApi } from '@/lib/api/adminBrochures';
import {
  AdminBrochureAdsListResponse,
  AdminBrochureAnalyticsOverview,
  AdminCompanyBrochureOption,
} from '@/types/brochure';

vi.mock('@/lib/api/adminBrochures', () => ({
  adminBrochureApi: {
    listAds: vi.fn(),
    listCompanyBrochures: vi.fn(),
    getBrochureAnalytics: vi.fn(),
    createAd: vi.fn(),
    updateAd: vi.fn(),
    deleteAd: vi.fn(),
    assignTargets: vi.fn(),
    uploadCreative: vi.fn(),
  },
}));

describe('Phase 4: Admin Sponsored Ad Campaign Manager', () => {
  let queryClient: QueryClient;

  const mockAdsResponse: AdminBrochureAdsListResponse = {
    total_active_ads: 2,
    total_impressions: 1450,
    total_clicks: 87,
    average_ctr: 6.0,
    items: [
      {
        id: 'ad-uuid-1',
        sponsor_name: 'UltraTech Cement Ltd',
        title: 'Low-Carbon LC3 Clinker Solutions',
        placement_type: 'BANNER_TOP',
        creative_image_url: '/converge-api/v1/uploads/brochures/ads/ad_1.jpg',
        destination_url: 'https://ultratechcement.com/green-solutions',
        tagline: 'Leading Sustainable Construction Across India',
        is_active: true,
        is_global: true,
        assigned_brochure_ids: [],
        assigned_brochures: [],
        impression_count: 1200,
        click_count: 75,
        ctr: 6.25,
        created_at: '2026-11-09T10:00:00Z',
        updated_at: '2026-11-09T10:00:00Z',
      },
      {
        id: 'ad-uuid-2',
        sponsor_name: 'Siemens Industrial Automation',
        title: 'Smart Grid Infrastructure 2026',
        placement_type: 'PRE_ROLL',
        creative_image_url: '/converge-api/v1/uploads/brochures/ads/ad_2.jpg',
        destination_url: 'https://siemens.com/energy-2026',
        tagline: 'Empowering India’s High-Speed Rail & Metro Hubs',
        is_active: true,
        is_global: false,
        assigned_brochure_ids: ['brochure-epc-1'],
        assigned_brochures: [
          {
            brochure_id: 'brochure-epc-1',
            company_name: 'InfraTech EPC Solutions Ltd',
            title: 'Official Digital Brochure',
            slug: 'infratech-epc-solutions-ltd',
          },
        ],
        impression_count: 250,
        click_count: 12,
        ctr: 4.8,
        created_at: '2026-11-09T11:00:00Z',
        updated_at: '2026-11-09T11:00:00Z',
      },
    ],
  };

  const mockCompaniesResponse: AdminCompanyBrochureOption[] = [
    {
      id: 'brochure-epc-1',
      company_name: 'InfraTech EPC Solutions Ltd',
      title: 'Official Digital Brochure',
      slug: 'infratech-epc-solutions-ltd',
      total_pages: 3,
      is_published: true,
    },
    {
      id: 'brochure-maahi-2',
      company_name: 'Deccan Green Cement & Binders Ltd',
      title: 'Catalog 2026',
      slug: 'deccan-green-cement',
      total_pages: 5,
      is_published: true,
    },
  ];

  const mockAnalyticsResponse: AdminBrochureAnalyticsOverview = {
    period: '7d',
    generated_at: '2026-11-12T10:00:00Z',
    total_magazines: 2,
    published_magazines: 2,
    total_views_all_time: 185,
    period_views: 64,
    total_page_reads_all_time: 420,
    period_page_reads: 155,
    unique_sessions: 41,
    combined_time_series: [
      { bucket: '2026-11-11', label: 'Nov 11', opens: 22, page_reads: 58 },
      { bucket: '2026-11-12', label: 'Nov 12', opens: 42, page_reads: 97 },
    ],
    magazines: [
      {
        brochure_id: 'brochure-epc-1',
        company_name: 'InfraTech EPC Solutions Ltd',
        title: 'Official Digital Brochure',
        slug: 'infratech-epc-solutions-ltd',
        is_published: true,
        total_pages: 3,
        period: '7d',
        total_views_all_time: 120,
        period_views: 40,
        total_page_reads_all_time: 260,
        period_page_reads: 100,
        unique_sessions: 25,
        avg_pages_per_session: 4.0,
        top_page_number: 2,
        last_activity_at: '2026-11-12T09:58:00Z',
        cover_thumbnail_url: '/uploads/epc_cover.webp',
        time_series: [
          { bucket: '2026-11-11', label: 'Nov 11', opens: 15, page_reads: 35 },
          { bucket: '2026-11-12', label: 'Nov 12', opens: 25, page_reads: 65 },
        ],
        pages: [
          { page_id: 'p1', page_number: 1, title: 'Cover', read_count: 30, total_read_count: 80, unique_readers: 22, share_pct: 30.0 },
          { page_id: 'p2', page_number: 2, title: 'EPC Specs', read_count: 45, total_read_count: 110, unique_readers: 24, share_pct: 45.0 },
          { page_id: 'p3', page_number: 3, title: 'Projects', read_count: 25, total_read_count: 70, unique_readers: 18, share_pct: 25.0 },
        ],
      },
      {
        brochure_id: 'brochure-maahi-2',
        company_name: 'Deccan Green Cement & Binders Ltd',
        title: 'Catalog 2026',
        slug: 'deccan-green-cement',
        is_published: true,
        total_pages: 5,
        period: '7d',
        total_views_all_time: 65,
        period_views: 24,
        total_page_reads_all_time: 160,
        period_page_reads: 55,
        unique_sessions: 16,
        avg_pages_per_session: 3.4,
        top_page_number: 1,
        last_activity_at: '2026-11-12T09:30:00Z',
        cover_thumbnail_url: '/uploads/deccan_cover.webp',
        time_series: [
          { bucket: '2026-11-11', label: 'Nov 11', opens: 7, page_reads: 23 },
          { bucket: '2026-11-12', label: 'Nov 12', opens: 17, page_reads: 32 },
        ],
        pages: [
          { page_id: 'd1', page_number: 1, title: 'LC3 Brochure', read_count: 35, total_read_count: 90, unique_readers: 15, share_pct: 63.6 },
        ],
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.mocked(adminBrochureApi.listAds).mockResolvedValue(mockAdsResponse);
    vi.mocked(adminBrochureApi.listCompanyBrochures).mockResolvedValue(mockCompaniesResponse);
    vi.mocked(adminBrochureApi.getBrochureAnalytics).mockResolvedValue(mockAnalyticsResponse);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminBrochureAds />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders dashboard with metric strip, placement tabs, and ad cards', async () => {
    renderComponent();

    expect(await screen.findByText('Master Brochure Ads & Sponsorship Engine')).toBeInTheDocument();

    // Check metric cards
    expect(screen.getByText('Active Campaigns')).toBeInTheDocument();
    expect(screen.getByText('Total Impressions')).toBeInTheDocument();
    expect(screen.getByText('Total Clicks')).toBeInTheDocument();
    expect(screen.getByText('Average CTR')).toBeInTheDocument();

    // Check ad cards
    expect(await screen.findByText('UltraTech Cement Ltd')).toBeInTheDocument();
    expect(screen.getByText('Low-Carbon LC3 Clinker Solutions')).toBeInTheDocument();
    expect(screen.getByText('📌 Top Banner')).toBeInTheDocument();
    expect(screen.getByText('Global (All Brochures)')).toBeInTheDocument();

    expect(screen.getByText('Siemens Industrial Automation')).toBeInTheDocument();
    expect(screen.getByText('Smart Grid Infrastructure 2026')).toBeInTheDocument();
    expect(screen.getByText('📖 Pre-Roll Inside Cover')).toBeInTheDocument();
    expect(screen.getByText('1 Companies Target')).toBeInTheDocument();
  });

  it('opens Create Ad Campaign modal and allows configuring new sponsor campaign', async () => {
    renderComponent();

    const newAdBtn = await screen.findByTestId('create-ad-button');
    fireEvent.click(newAdBtn);

    expect(screen.getByText('Create New Sponsor Ad Campaign')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. UltraTech Cement / Siemens')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. Decarbonized Concrete Infrastructure 2026')).toBeInTheDocument();
    expect(screen.getByText('📌 Top Leaderboard Banner (Above PDF)')).toBeInTheDocument();
    expect(screen.getByText('📖 Pre-Roll Inside Cover Spread (Before Page 1)')).toBeInTheDocument();
  });

  it('opens Targeting Matrix modal and displays company brochure checklist', async () => {
    renderComponent();

    // Wait for the ad cards to appear
    expect(await screen.findByText('Siemens Industrial Automation')).toBeInTheDocument();

    // Click the targeting button for the Siemens ad
    const targetBtn = screen.getByTestId('target-ad-btn-ad-uuid-2');
    fireEvent.click(targetBtn);

    expect(await screen.findByText('Targeting Matrix')).toBeInTheDocument();
    expect(screen.getByText('Global Conference-Wide Fallback')).toBeInTheDocument();

    // Check if company options are loaded
    await waitFor(() => {
      expect(screen.getAllByText('InfraTech EPC Solutions Ltd').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Deccan Green Cement & Binders Ltd').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders Summit Flipbook Sensory Studio, updates paired animations on Play Test, and shows Converge demo leaf overlay', async () => {
    renderComponent();

    expect(await screen.findByTestId('admin-flipbook-acoustics')).toBeInTheDocument();
    expect(screen.getByTestId('admin-play-test-stage')).toBeInTheDocument();

    // Selecting BOOK_SNAP card pairs HARDCOVER_SWING and triggers the 3D leaf overlay
    const bookSnapCard = screen.getByTestId('sound-preset-card-BOOK_SNAP');
    fireEvent.click(bookSnapCard);

    expect(screen.getByTestId('flip-3d-leaf-overlay')).toBeInTheDocument();
    expect(screen.getByTestId('animation-preset-btn-HARDCOVER_SWING')).toHaveAttribute('aria-pressed', 'true');

    // Auditioning GLOSSY_MAGAZINE via Play Test shows the leaf overlay without altering active selection
    fireEvent.click(screen.getByTestId('play-test-sound-GLOSSY_MAGAZINE'));
    expect(screen.getByTestId('flip-3d-leaf-overlay')).toBeInTheDocument();
    expect(screen.getByTestId('animation-preset-btn-HARDCOVER_SWING')).toHaveAttribute('aria-pressed', 'true');

    // Independent animation selection switches active motion preset
    const glossyAnimBtn = screen.getByTestId('animation-preset-btn-GLOSSY_GLIDE');
    fireEvent.click(glossyAnimBtn);
    expect(glossyAnimBtn).toHaveAttribute('aria-pressed', 'true');

    // Triggering active combo flips the live Converge AI demo stage
    fireEvent.click(screen.getByTestId('play-active-combo-btn'));
    expect(screen.getByTestId('flip-3d-leaf-overlay')).toBeInTheDocument();

    // Selecting FlipHTML5 Crisp Page pairs REAL_PAGE_FLIP and activates RealPageFlipBook (StPageFlip)
    const flipHtmlSoundCard = screen.getByTestId('sound-preset-card-REALISTIC_BOOK_FLIP');
    fireEvent.click(flipHtmlSoundCard);
    expect(screen.getByTestId('animation-preset-btn-REAL_PAGE_FLIP')).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByTestId('real-page-flipbook')).toBeInTheDocument();
  });

  it('displays all magazines analytics overview, supports switching selected magazine and time period', async () => {
    renderComponent();

    const section = await screen.findByTestId('admin-magazine-analytics-section');
    expect(section).toBeInTheDocument();
    expect(screen.getByText('All Available Magazines — Live Readership & Page Engagement')).toBeInTheDocument();
    expect(screen.getByTestId('magazine-analytics-card-infratech-epc-solutions-ltd')).toBeInTheDocument();
    expect(screen.getByTestId('magazine-analytics-card-deccan-green-cement')).toBeInTheDocument();

    // First magazine's per-page breakdown is shown initially
    expect(screen.getByText('EPC Specs')).toBeInTheDocument();

    // Click second magazine card to inspect its pages
    fireEvent.click(screen.getByTestId('magazine-analytics-card-deccan-green-cement'));
    expect(await screen.findByText('LC3 Brochure')).toBeInTheDocument();

    // Switch time window to Last 24 Hours and verify API refetch
    fireEvent.click(screen.getByRole('button', { name: /Last 24 Hours|24H/ }));
    await waitFor(() => {
      expect(adminBrochureApi.getBrochureAnalytics).toHaveBeenCalledWith('24h');
    });
  });
});
