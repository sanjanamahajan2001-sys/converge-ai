import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Matching } from '@/routes/Matching';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import * as businessApi from '@/lib/api/business';
import * as matchingApi from '@/lib/api/matching';
import { BusinessMatchSearchResponse } from '@/types/business';

function renderMatching() {
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
        <MemoryRouter initialEntries={['/matching']}>
          <Matching />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

const mockCommercialSearchResponse: BusinessMatchSearchResponse = {
  total_candidates: 1,
  query_summary: {
    raw_query: 'Need 1000 MT LC3-50 low-carbon cement delivered to Pune within 45 days',
    item_name: 'Calcined Clay LC3',
    matched_product_code: 'CALCINED_CLAY_LC3',
    matched_grade_code: 'LC3_50_STANDARD',
    quantity: 1000,
    quantity_unit: 'MT',
    destination_city: 'Pune',
    target_timeline_days: 45,
    inquiry_type: 'RFQ_PRODUCT',
    confidence: 1.0,
  },
  candidates: [
    {
      offering_id: '11111111-2222-3333-4444-555555555555',
      business_profile_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      supplier_user_id: '99999999-8888-7777-6666-555555555555',
      supplier_company_name: 'Maahi Decarb Materials Pvt Ltd',
      supplier_industry: 'Heavy Materials & Green Cement',
      supplier_hq_city: 'Pune',
      supplier_role: 'SUPPLIER',
      offering_title: 'LC3-50 Low Carbon Blend',
      product_code: 'CALCINED_CLAY_LC3',
      grade_code: 'LC3_50_STANDARD',
      composite_score: 95.5,
      score_breakdown: {
        product_relevance: 1.0,
        capacity_feasibility: 0.95,
        commitment_confidence: 0.85,
        delivery_feasibility: 1.0,
        verification_confidence: 1.0,
      },
      declared_monthly_capacity: 2500,
      capacity_unit: 'MT',
      uncommitted_monthly_capacity: 1500,
      lead_time_days: 10,
      geographic_coverage: ['Pune', 'Mumbai', 'Western Maharashtra'],
      offers_test_certificates: true,
      confidence_badges: ['✓ Verified Fresh (<30d)'],
      indicative_price_display: '₹5,400 / MT',
      pricing_basis: 'F.O.R. Delivered',
      price_currency: 'INR',
    },
  ],
};

describe('Mode B Commercial RFQ & Sourcing UX (Phase 3)', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: 'usr-123',
      email: 'buyer@test.com',
      username: 'sanjanamaahi',
      full_name: 'Sanjana Maahi',
      is_active: true,
    });

    vi.spyOn(matchingApi, 'getCandidateMatches').mockResolvedValue({
      requester_id: 'usr-123',
      candidates: [],
      matched_count: 0,
      total_evaluated: 0,
      eligible_count: 0,
      limit: 10,
      offset: 0,
    });

    vi.spyOn(businessApi, 'getMyActiveRequirements').mockResolvedValue([
      {
        id: 'req-1',
        business_profile_id: 'prof-1',
        custom_requirement_title: 'Bulk LC3 Procurement',
        product_code: 'CALCINED_CLAY_LC3',
        grade_code: 'LC3_50_STANDARD',
        required_quantity: 1000,
        quantity_unit: 'MT',
        delivery_city: 'Pune',
        target_timeline_days: 45,
        target_budget_indication: 5400,
        is_budget_public: false,
        urgency: 'PLANNED',
        excluded_supplier_ids: [],
        allow_substitutes: false,
        required_certifications: [],
        is_feedstock_procurement: false,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);

    vi.spyOn(businessApi, 'searchBusinessMatches').mockResolvedValue(mockCommercialSearchResponse);
  });

  it('switches between Mode A and Mode B using tabs', async () => {
    renderMatching();

    await waitFor(() => {
      expect(screen.getByText('Participant Discovery & Matching')).toBeInTheDocument();
    });

    // Default: Attendee Discovery Mode A tab is active
    expect(screen.getByText('Attendee Discovery (Mode A)')).toBeInTheDocument();
    expect(screen.getByText('Commercial RFQ & Sourcing (Mode B)')).toBeInTheDocument();

    // Click Mode B
    fireEvent.click(screen.getByText('Commercial RFQ & Sourcing (Mode B)'));

    // Mode B header should appear
    await waitFor(() => {
      expect(screen.getByText('Commercial RFQ & Multi-Dimensional Sourcing')).toBeInTheDocument();
      expect(screen.getByText('Mode B Active')).toBeInTheDocument();
    });
  });

  it('renders active requirements dropdown and executes commercial search with 5-D scoring', async () => {
    renderMatching();

    await waitFor(() => {
      expect(screen.getByText('Participant Discovery & Matching')).toBeInTheDocument();
    });

    // Switch to Mode B
    fireEvent.click(screen.getByText(/Commercial RFQ & Sourcing/i));

    await waitFor(() => {
      expect(screen.getByText('Commercial RFQ & Multi-Dimensional Sourcing')).toBeInTheDocument();
    });

    // Verify saved requirement appears in dropdown
    await waitFor(() => {
      expect(screen.getByText(/Bulk LC3 Procurement/)).toBeInTheDocument();
    });

    // Select the requirement to trigger match search
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: 'req-1' } });

    // Verify candidate card appears with 5-D score and details
    await waitFor(() => {
      expect(screen.getByText('Maahi Decarb Materials Pvt Ltd')).toBeInTheDocument();
      expect(screen.getByText('LC3-50 Low Carbon Blend')).toBeInTheDocument();
      expect(screen.getByText('96% Match')).toBeInTheDocument();
      expect(screen.getByText('✓ Verified Fresh (<30d)')).toBeInTheDocument();
      expect(screen.getByText('📜 Mill / NABL Certs')).toBeInTheDocument();
    });

    // Verify toggle for 5-D score breakdown
    const breakdownBtn = screen.getByText('View 5-D Breakdown');
    fireEvent.click(breakdownBtn);

    await waitFor(() => {
      expect(screen.getByText('Product Match:')).toBeInTheDocument();
      expect(screen.getByText('Capacity Run-Rate:')).toBeInTheDocument();
      expect(screen.getByText('Uncommitted Volume:')).toBeInTheDocument();
      expect(screen.getByText('Delivery Feasibility:')).toBeInTheDocument();
      expect(screen.getByText('Data Freshness:')).toBeInTheDocument();
    });

    // Verify private buyer budget is protected
    expect(screen.getByText('🔒 Private Buyer Budget Preserved')).toBeInTheDocument();
    expect(screen.queryByText('5400')).not.toBeInTheDocument();
  });
});
