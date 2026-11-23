import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { BrochuresDirectory } from '@/routes/BrochuresDirectory';
import { brochureApi } from '@/lib/api/brochures';
import { BrochureDirectoryItem } from '@/types/brochure';

vi.mock('@/lib/api/brochures', () => ({
  brochureApi: {
    getDirectory: vi.fn(),
  },
}));

describe('Phase 6: Exhibitor Catalogs Directory & Ecosystem Discovery', () => {
  let queryClient: QueryClient;

  const mockBrochures: BrochureDirectoryItem[] = [
    {
      id: 'brochure-1-uuid',
      business_profile_id: 'bp-1-uuid',
      owner_user_id: 'user-1-uuid',
      company_name: 'InfraTech EPC Solutions Ltd',
      title: 'InfraTech EPC Solutions Ltd — Official Digital Brochure',
      description: 'High-speed rail, smart city flyovers, and green commercial buildings.',
      slug: 'infratech-epc-solutions-ltd',
      total_pages: 3,
      cover_image_url: '/converge-api/v1/uploads/brochures/page_1.jpg',
      cover_thumbnail_url: '/converge-api/v1/uploads/brochures/thumb_1.webp',
      view_count: 24,
      created_at: '2026-11-10T10:00:00Z',
    },
    {
      id: 'brochure-2-uuid',
      business_profile_id: 'bp-2-uuid',
      owner_user_id: 'user-2-uuid',
      company_name: 'UltraTech Cement Ltd',
      title: 'UltraTech Cement Ltd — Low-Carbon LC3 Solutions 2026',
      description: 'Certified LC3 clinker and green building materials catalog.',
      slug: 'ultratech-cement-ltd-aditya-birla-group-v1',
      total_pages: 2,
      cover_image_url: '/converge-api/v1/uploads/brochures/ultra_1.jpg',
      cover_thumbnail_url: '/converge-api/v1/uploads/brochures/ultra_thumb.webp',
      view_count: 15,
      created_at: '2026-11-10T10:15:00Z',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });
    vi.mocked(brochureApi.getDirectory).mockResolvedValue(mockBrochures);
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <BrochuresDirectory />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders directory hero, metric strip, and exhibitor brochure cards', async () => {
    renderComponent();

    // Verify hero title
    expect(screen.getByText('Exhibitor Catalogs & Summit Guides')).toBeInTheDocument();

    // Verify metrics strip (2 catalogs, 5 pages total, 39 views total)
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('39')).toBeInTheDocument();
    });

    // Verify company cards
    expect(screen.getByText('InfraTech EPC Solutions Ltd')).toBeInTheDocument();
    expect(screen.getByText('UltraTech Cement Ltd')).toBeInTheDocument();
    expect(screen.getByText('📄 3 Pages')).toBeInTheDocument();
    expect(screen.getByText('📄 2 Pages')).toBeInTheDocument();
  });

  it('supports search input query filter', async () => {
    renderComponent();

    const searchInput = screen.getByTestId('brochure-directory-search');
    fireEvent.change(searchInput, { target: { value: 'UltraTech' } });

    await waitFor(() => {
      expect(brochureApi.getDirectory).toHaveBeenCalledWith('UltraTech');
    });
  });

  it('renders empty state when no brochures match', async () => {
    vi.mocked(brochureApi.getDirectory).mockResolvedValue([]);
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('No Published Digital Brochures Found')).toBeInTheDocument();
    });
  });
});
