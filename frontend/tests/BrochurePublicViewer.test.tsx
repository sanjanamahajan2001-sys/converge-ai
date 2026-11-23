import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { BrochurePublicViewer } from '@/routes/BrochurePublicViewer';
import { brochureApi } from '@/lib/api/brochures';
import { BrochurePublicView } from '@/types/brochure';

vi.mock('@/lib/api/brochures', () => ({
  brochureApi: {
    getPublicBrochure: vi.fn(),
    trackAdEvent: vi.fn(),
  },
}));

describe('Phase 5: Dynamic Ad Injection & Flipbook Viewer Integration', () => {
  let queryClient: QueryClient;

  const mockPublicBrochure: BrochurePublicView = {
    id: 'brochure-epc-uuid',
    company_name: 'InfraTech EPC Solutions Ltd',
    title: 'InfraTech EPC Solutions Ltd — Official Digital Brochure',
    description: 'Leading EPC contractor executing high-speed rail and smart cities.',
    slug: 'infratech-epc-solutions-ltd',
    total_pages: 3,
    pages: [
      {
        id: 'page-1-uuid',
        brochure_id: 'brochure-epc-uuid',
        page_number: 1,
        image_url: '/converge-api/v1/uploads/brochures/page_1.jpg',
        thumbnail_url: '/converge-api/v1/uploads/brochures/thumb_1.webp',
        title: 'Front Cover & Executive Summary',
        aspect_ratio: 0.707,
        width: 1240,
        height: 1754,
        created_at: '2026-11-10T10:00:00Z',
      },
      {
        id: 'page-2-uuid',
        brochure_id: 'brochure-epc-uuid',
        page_number: 2,
        image_url: '/converge-api/v1/uploads/brochures/page_2.jpg',
        thumbnail_url: '/converge-api/v1/uploads/brochures/thumb_2.webp',
        title: 'Mega Infrastructure Projects',
        aspect_ratio: 0.707,
        width: 1240,
        height: 1754,
        created_at: '2026-11-10T10:00:00Z',
      },
      {
        id: 'page-3-uuid',
        brochure_id: 'brochure-epc-uuid',
        page_number: 3,
        image_url: '/converge-api/v1/uploads/brochures/page_3.jpg',
        thumbnail_url: '/converge-api/v1/uploads/brochures/thumb_3.webp',
        title: 'Sustainability Credentials',
        aspect_ratio: 0.707,
        width: 1240,
        height: 1754,
        created_at: '2026-11-10T10:00:00Z',
      },
    ],
    top_banner_ad: {
      id: 'ad-top-uuid',
      sponsor_name: 'UltraTech Cement Ltd',
      title: 'Low-Carbon LC3 Solutions 2026',
      placement_type: 'BANNER_TOP',
      creative_image_url: '/converge-api/v1/uploads/brochures/ads/ad_top.jpg',
      destination_url: 'https://ultratechcement.com/green-solutions',
      tagline: 'Official Sustainability Sponsor of Converge Summit',
      is_active: true,
    },
    pre_roll_ad: {
      id: 'ad-preroll-uuid',
      sponsor_name: 'Siemens Industrial Automation',
      title: 'Smart Grid Infrastructure 2026',
      placement_type: 'PRE_ROLL',
      creative_image_url: '/converge-api/v1/uploads/brochures/ads/ad_preroll.jpg',
      destination_url: 'https://siemens.com/energy-2026',
      tagline: 'Powering India’s High-Speed Rail Hubs',
      is_active: true,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.mocked(brochureApi.getPublicBrochure).mockResolvedValue(mockPublicBrochure);
    vi.mocked(brochureApi.trackAdEvent).mockResolvedValue({ success: true });
    window.open = vi.fn();
  });

  const renderViewer = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/brochures/infratech-epc-solutions-ltd']}>
          <Routes>
            <Route path="/brochures/:slug" element={<BrochurePublicViewer />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders brochure metadata, pages, and logs ad impressions on load', async () => {
    renderViewer();

    // Verify brochure title and company (matching elements in print and screen layouts)
    await waitFor(() => {
      expect(screen.getAllByText('InfraTech EPC Solutions Ltd — Official Digital Brochure').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('InfraTech EPC Solutions Ltd').length).toBeGreaterThanOrEqual(1);
    });

    // Verify top sponsor banner is injected
    expect(screen.getByTestId('brochure-top-banner-ad')).toBeInTheDocument();
    expect(screen.getByText(/UltraTech Cement Ltd/)).toBeInTheDocument();
    expect(screen.getAllByText('Low-Carbon LC3 Solutions 2026').length).toBeGreaterThanOrEqual(1);

    // Verify impression telemetry was triggered for both top banner and pre-roll ads
    await waitFor(() => {
      expect(brochureApi.trackAdEvent).toHaveBeenCalledWith('ad-top-uuid', 'IMPRESSION', 'brochure-epc-uuid');
      expect(brochureApi.trackAdEvent).toHaveBeenCalledWith('ad-preroll-uuid', 'IMPRESSION', 'brochure-epc-uuid');
    });
  });

  it('renders Pre-Roll inside front cover ad spread and triggers outbound click tracking', async () => {
    renderViewer();

    // In spread mode on page 0 (cover), pre-roll inside cover spread is shown
    expect(await screen.findByTestId('pre-roll-spread-ad')).toBeInTheDocument();
    expect(screen.getByText(/Inside Front Cover Sponsor/)).toBeInTheDocument();
    expect(screen.getByText('Siemens Industrial Automation')).toBeInTheDocument();
    expect(screen.getByText('Smart Grid Infrastructure 2026')).toBeInTheDocument();

    // Click the top sponsor banner to test outbound visit & click telemetry
    const topBanner = screen.getByTestId('brochure-top-banner-ad');
    fireEvent.click(topBanner);

    expect(brochureApi.trackAdEvent).toHaveBeenCalledWith('ad-top-uuid', 'CLICK', 'brochure-epc-uuid');
    expect(window.open).toHaveBeenCalledWith('https://ultratechcement.com/green-solutions', '_blank', 'noopener,noreferrer');
  });

  it('supports page navigation, scrubber tray, and zoom controls', async () => {
    renderViewer();

    await waitFor(() => {
      expect(screen.getAllByText('InfraTech EPC Solutions Ltd — Official Digital Brochure').length).toBeGreaterThanOrEqual(1);
    });

    // Test Scrubber buttons
    const nextBtn = screen.getByTitle('Next Page (→)');
    expect(nextBtn).toBeInTheDocument();
    fireEvent.click(nextBtn);

    // Zoom buttons
    const zoomInBtn = screen.getByTitle('Zoom In');
    fireEvent.click(zoomInBtn);
    expect(screen.getByTitle('Reset Zoom (Double click canvas to zoom)')).toHaveTextContent('120%');
  });
});
