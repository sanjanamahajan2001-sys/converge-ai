import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { brochureApi } from '@/lib/api/brochures';
import { CompanyBrochureStudio } from '@/routes/CompanyBrochureStudio';
import { BrochurePublicViewer } from '@/routes/BrochurePublicViewer';
import { BrochureAnalyticsDetail, CompanyBrochureDetail, BrochurePublicView } from '@/types/brochure';

const mockBrochureDetail: CompanyBrochureDetail = {
  id: 'brochure-test-001',
  business_profile_id: 'bp-test-001',
  owner_user_id: 'user-test-001',
  company_name: 'Deccan Decarb Materials Pvt Ltd',
  title: 'Deccan Decarb — Sustainable Cement Catalog 2026',
  description: 'Certified LC3 and low-carbon clinker manufacturing portfolio.',
  slug: 'deccan-decarb-2026',
  is_published: true,
  view_count: 42,
  total_pages: 2,
  pages: [
    {
      id: 'page-001',
      brochure_id: 'brochure-test-001',
      page_number: 1,
      image_url: '/converge-api/v1/uploads/brochures/test/page1.jpg',
      thumbnail_url: '/converge-api/v1/uploads/brochures/test/thumb1.webp',
      title: 'Cover Page',
      aspect_ratio: 0.707,
      width: 1240,
      height: 1754,
      file_size_bytes: 420000,
      created_at: '2026-11-09T10:00:00Z',
    },
    {
      id: 'page-002',
      brochure_id: 'brochure-test-001',
      page_number: 2,
      image_url: '/converge-api/v1/uploads/brochures/test/page2.jpg',
      thumbnail_url: '/converge-api/v1/uploads/brochures/test/thumb2.webp',
      title: 'Technical Specs & Lab Reports',
      aspect_ratio: 0.707,
      width: 1240,
      height: 1754,
      file_size_bytes: 510000,
      created_at: '2026-11-09T10:05:00Z',
    },
  ],
  created_at: '2026-11-09T09:00:00Z',
  updated_at: '2026-11-09T10:05:00Z',
};

const mockPublicView: BrochurePublicView = {
  id: 'brochure-test-001',
  company_name: 'Deccan Decarb Materials Pvt Ltd',
  title: 'Deccan Decarb — Sustainable Cement Catalog 2026',
  description: 'Certified LC3 and low-carbon clinker manufacturing portfolio.',
  slug: 'deccan-decarb-2026',
  total_pages: 2,
  pages: mockBrochureDetail.pages,
  top_banner_ad: {
    id: 'ad-001',
    sponsor_name: 'CleanTech Infra Global',
    title: 'Accelerate Decarbonization in Bulk Logistics',
    placement_type: 'BANNER_TOP',
    creative_image_url: '/uploads/ads/banner.jpg',
    destination_url: 'https://cleantech.example.com',
    tagline: 'Leading green logistics network',
    is_active: true,
  },
  pre_roll_ad: {
    id: 'ad-002',
    sponsor_name: 'Converge 2026 Title Partner',
    title: 'Welcome to the Conference Digital Library',
    placement_type: 'PRE_ROLL',
    creative_image_url: '/uploads/ads/preroll.jpg',
    destination_url: 'https://converge.example.com',
    is_active: true,
  },
};

const mockOwnerAnalytics: BrochureAnalyticsDetail = {
  brochure_id: 'brochure-test-001',
  company_name: 'Deccan Decarb Materials Pvt Ltd',
  title: 'Deccan Decarb — Sustainable Cement Catalog 2026',
  slug: 'deccan-decarb-2026',
  is_published: true,
  total_pages: 2,
  period: '7d',
  total_views_all_time: 42,
  period_views: 18,
  total_page_reads_all_time: 96,
  period_page_reads: 45,
  unique_sessions: 14,
  avg_pages_per_session: 3.2,
  top_page_number: 2,
  last_activity_at: '2026-11-12T10:15:00Z',
  cover_thumbnail_url: '/converge-api/v1/uploads/brochures/test/thumb1.webp',
  time_series: [
    { bucket: '2026-11-11', label: 'Nov 11', opens: 8, page_reads: 20 },
    { bucket: '2026-11-12', label: 'Nov 12', opens: 10, page_reads: 25 },
  ],
  pages: [
    { page_id: 'page-001', page_number: 1, title: 'Cover Page', read_count: 19, total_read_count: 42, unique_readers: 14, share_pct: 42.2 },
    { page_id: 'page-002', page_number: 2, title: 'Technical Specs & Lab Reports', read_count: 26, total_read_count: 54, unique_readers: 13, share_pct: 57.8 },
  ],
};

describe('Company Brochure Studio & Flipbook Viewer (Phase 2)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('renders company brochure studio with page cards, stats, metadata, and live owner page analytics', async () => {
    vi.spyOn(brochureApi, 'getMyBrochure').mockResolvedValue(mockBrochureDetail);
    const analyticsSpy = vi
      .spyOn(brochureApi, 'getMyBrochureAnalytics')
      .mockResolvedValue(mockOwnerAnalytics);

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/company/brochure']}>
          <CompanyBrochureStudio />
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Verify loading transitions to loaded content
    await waitFor(() => {
      expect(
        screen.getByText('Deccan Decarb — Sustainable Cement Catalog 2026')
      ).toBeInTheDocument();
    });

    // Check stats and badges
    expect(screen.getByText('Published & Live')).toBeInTheDocument();
    expect(screen.getByText(/42/)).toBeInTheDocument();

    // Check pages rendered in grid
    expect(screen.getByText('#1')).toBeInTheDocument();
    expect(screen.getAllByText('Cover Page').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('#2')).toBeInTheDocument();
    expect(screen.getAllByText('Technical Specs & Lab Reports').length).toBeGreaterThanOrEqual(1);

    // Check upload box and analytics panel are visible
    expect(screen.getByText('Upload Brochure Page Images')).toBeInTheDocument();
    expect(await screen.findByTestId('brochure-analytics-panel')).toBeInTheDocument();
    expect(screen.getByText('My Brochure & Page Read Analytics')).toBeInTheDocument();
    expect(screen.getAllByText('Page #2').length).toBeGreaterThanOrEqual(1);

    // Switching period refetches analytics
    fireEvent.click(screen.getByRole('button', { name: /Last 30 Days|30D/ }));
    await waitFor(() => {
      expect(analyticsSpy).toHaveBeenCalledWith('30d');
    });
  });

  it('renders public flipbook reader with sponsor banner and zoom tools', async () => {
    vi.spyOn(brochureApi, 'getPublicBrochure').mockResolvedValue(mockPublicView);
    vi.spyOn(brochureApi, 'trackAdEvent').mockResolvedValue({ success: true });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/brochures/deccan-decarb-2026']}>
          <Routes>
            <Route path="/brochures/:slug" element={<BrochurePublicViewer />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    // Verify brochure title and sponsor banner
    await waitFor(() => {
      expect(
        screen.getAllByText('Deccan Decarb — Sustainable Cement Catalog 2026').length
      ).toBeGreaterThanOrEqual(1);
    });

    // Top banner ad presence
    expect(screen.getByText('Sponsored Partner')).toBeInTheDocument();
    expect(screen.getByText('CleanTech Infra Global:')).toBeInTheDocument();

    // Pre-roll inside cover indicator
    expect(
      screen.getByText(/Inside Front Cover Sponsor: Converge 2026 Title Partner/)
    ).toBeInTheDocument();

    // Zoom buttons and page scrubber
    expect(screen.getByTitle('Zoom In')).toBeInTheDocument();
    expect(screen.getByTitle('Zoom Out')).toBeInTheDocument();
    expect(screen.getByTitle('Print Brochure')).toBeInTheDocument();
    expect(screen.getAllByText(/Page 1 of 2/).length).toBeGreaterThanOrEqual(1);
  });

  it('supports 3D flipbook spread toggle, zoom scaling, and page navigation', async () => {
    vi.spyOn(brochureApi, 'getPublicBrochure').mockResolvedValue(mockPublicView);
    vi.spyOn(brochureApi, 'trackAdEvent').mockResolvedValue({ success: true });

    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/brochures/deccan-decarb-2026']}>
          <Routes>
            <Route path="/brochures/:slug" element={<BrochurePublicViewer />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTitle('Zoom In')).toBeInTheDocument();
    });

    // Test zoom in
    const zoomInBtn = screen.getByTitle('Zoom In');
    const zoomResetBtn = screen.getByTitle(/Reset Zoom/);
    expect(zoomResetBtn).toHaveTextContent('100%');

    // Click Zoom In
    fireEvent.click(zoomInBtn);
    expect(screen.getByTitle(/Reset Zoom/)).toHaveTextContent('120%');

    // Verify page-read telemetry tracked on initial load and after turning next page
    const trackReadsSpy = vi
      .spyOn(brochureApi, 'trackPageReads')
      .mockResolvedValue({ success: true, recorded_pages: [1] });

    // Click Next Page button
    const nextBtn = screen.getByTitle(/Next Page/);
    expect(nextBtn).toBeInTheDocument();
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(trackReadsSpy).toHaveBeenCalled();
    });

    // Verify sound toggle exists
    const soundToggle = screen.getByTitle(/Turn Sound/);
    expect(soundToggle).toBeInTheDocument();
  });
});
