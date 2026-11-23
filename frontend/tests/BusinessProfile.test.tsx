import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BusinessProfileSection } from '@/components/business/BusinessProfileSection';
import * as businessApi from '@/lib/api/business';

function renderBusinessProfileSection() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BusinessProfileSection />
    </QueryClientProvider>
  );
}

describe('BusinessProfileSection Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    vi.spyOn(businessApi, 'getMyBusinessProfile').mockResolvedValue({
      id: '22222222-2222-2222-2222-222222222222',
      user_id: '11111111-1111-1111-1111-111111111111',
      is_buyer: true,
      is_supplier: true,
      is_vendor: false,
      is_distributor: false,
      is_partner: false,
      allow_business_matching: true,
      company_name: 'Apex Materials Corp',
      industry: 'Building Materials',
      hq_city: 'Pune',
      hq_country: 'India',
      company_bio: 'Manufacturer and bulk supplier of green binders.',
      distributor_territories: [],
      warehousing_capacity_sqft: null,
      retail_dealer_count: null,
      partnership_types: [],
      partnership_interests: [],
      offerings: [
        {
          id: 'off-1',
          business_profile_id: '22222222-2222-2222-2222-222222222222',
          custom_product_title: 'OPC 53 Bulk Tankers',
          product_code: 'ORDINARY_PORTLAND_CEMENT',
          grade_code: 'OPC_53_IS_269',
          service_code: null,
          specifications_text: null,
          declared_monthly_capacity: 5000,
          declared_committed_volume: 1000,
          capacity_unit: 'METRIC_TONNE',
          minimum_order_quantity: 200,
          lead_time_days: 7,
          geographic_coverage: ['Pune', 'Mumbai'],
          offers_test_certificates: true,
          vendor_certifications: [],
          open_to_distribution: false,
          target_distribution_regions: [],
          distributor_tier_preferred: null,
          is_public_indicative: true,
          indicative_price_min: 5200,
          indicative_price_max: 5600,
          price_currency: 'INR',
          pricing_basis: 'EX_WORKS',
          offers_delivered_pricing: false,
          quote_validity_days: 30,
          is_active: true,
          price_last_confirmed_at: new Date().toISOString(),
          capacity_last_confirmed_at: new Date().toISOString(),
          is_capacity_stale: false,
          is_price_stale: false,
          reconfirmation_required: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      requirements: [
        {
          id: 'req-1',
          business_profile_id: '22222222-2222-2222-2222-222222222222',
          custom_requirement_title: 'Calcined Clay LC3 Bulk Procurement',
          product_code: 'CALCINED_CLAY_LC3',
          grade_code: 'LC3_50_STANDARD',
          service_code: null,
          required_quantity: 1000,
          quantity_unit: 'METRIC_TONNE',
          delivery_city: 'Pune',
          delivery_country: 'India',
          target_timeline_days: 45,
          target_budget_indication: 5400,
          is_budget_public: false,
          urgency: 'PLANNED',
          excluded_supplier_ids: [],
          allow_substitutes: true,
          required_certifications: [],
          is_feedstock_procurement: false,
          notes: 'Secondary supplier exploration',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      ],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });

    vi.spyOn(businessApi, 'getProductTaxonomies').mockResolvedValue([
      {
        category_code: 'BINDERS_AND_CEMENTITIOUS',
        sector_code: 'HEAVY_CONSTRUCTION_MATERIALS',
        canonical_name: 'Binders & Cementitious',
        standard_units: ['METRIC_TONNE'],
        canonical_products: [
          {
            product_code: 'ORDINARY_PORTLAND_CEMENT',
            category_code: 'BINDERS_AND_CEMENTITIOUS',
            canonical_name: 'Ordinary Portland Cement',
            substitute_product_codes: [],
            grades: [
              {
                grade_code: 'OPC_53_IS_269',
                product_code: 'ORDINARY_PORTLAND_CEMENT',
                grade_name: 'OPC 53 Grade',
                governing_standard: 'IS 269',
                aliases: [],
              },
            ],
          },
        ],
      },
    ]);

    vi.spyOn(businessApi, 'getServiceTaxonomies').mockResolvedValue([]);
  });

  it('renders commercial profile header and Mode B opt-in toggle', async () => {
    renderBusinessProfileSection();
    expect(await screen.findByText(/Commercial & Business Profile/i)).toBeInTheDocument();
    expect(screen.getByText(/Enable Commercial & Business Discovery/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Mode B/i).length).toBeGreaterThanOrEqual(1);
  });

  it('renders all 5 dynamic commercial role badges', async () => {
    renderBusinessProfileSection();
    expect(await screen.findByText(/Buyer \/ Sourcing/i)).toBeInTheDocument();
    expect(screen.getByText(/Supplier \/ Manufacturer/i)).toBeInTheDocument();
    expect(screen.getByText(/Vendor \/ Service Provider/i)).toBeInTheDocument();
    expect(screen.getByText(/Distributor \/ Channel Partner/i)).toBeInTheDocument();
    expect(screen.getByText(/Commercial Partner/i)).toBeInTheDocument();
  });

  it('renders catalog offerings with capacity, lead time, and freshness badge', async () => {
    renderBusinessProfileSection();
    expect(await screen.findByText('OPC 53 Bulk Tankers')).toBeInTheDocument();
    expect(screen.getByText(/5,000 METRIC_TONNE/i)).toBeInTheDocument();
    expect(screen.getByText(/7 days/i)).toBeInTheDocument();
    expect(screen.getByText(/✓ Verified Fresh/i)).toBeInTheDocument();
  });

  it('triggers 1-click re-confirmation when Re-confirm Freshness is clicked', async () => {
    const confirmSpy = vi.spyOn(businessApi, 'confirmOffering').mockResolvedValue({
      id: 'off-1',
    } as any);

    renderBusinessProfileSection();
    const reconfirmBtn = await screen.findByText(/Re-confirm Freshness/i);
    fireEvent.click(reconfirmBtn);

    await waitFor(() => {
      expect(confirmSpy).toHaveBeenCalledWith('off-1');
    });
  });

  it('renders active buyer procurement requirements with budget privacy indicator', async () => {
    renderBusinessProfileSection();
    expect(await screen.findByText(/Active Procurement Requirements/i)).toBeInTheDocument();
    expect(screen.getByText('LC3_50_STANDARD')).toBeInTheDocument();
    expect(screen.getByText(/1,000 METRIC_TONNE/i)).toBeInTheDocument();
    expect(screen.getByText(/Within 45 days/i)).toBeInTheDocument();
    expect(screen.getByText(/🔒 Budget Private/i)).toBeInTheDocument();
  });

  it('supports adding a dynamic custom offering with custom title and specifications', async () => {
    const createSpy = vi.spyOn(businessApi, 'createOffering').mockResolvedValue({
      id: 'off-custom-1',
    } as any);

    renderBusinessProfileSection();
    const openModalBtn = await screen.findByRole('button', { name: /\+ Add Offering/i });
    fireEvent.click(openModalBtn);

    // Switch to Custom Product / Service mode
    const customModeBtn = await screen.findByText(/Custom Product \/ Service/i);
    fireEvent.click(customModeBtn);

    // Fill offering display title
    const titleInput = screen.getByPlaceholderText(/Fe 550D TMT Steel Rebars/i);
    fireEvent.change(titleInput, { target: { value: 'High-Tensile Steel Wire Rods 8mm' } });

    // Submit offering via submit button
    const submitBtn = screen.getByRole('button', { name: /^Add Offering$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          custom_product_title: 'High-Tensile Steel Wire Rods 8mm',
          product_code: null,
          service_code: null,
        })
      );
    });
  });

  it('supports adding a dynamic custom procurement requirement with universal units', async () => {
    const createReqSpy = vi.spyOn(businessApi, 'createRequirement').mockResolvedValue({
      id: 'req-custom-1',
    } as any);

    renderBusinessProfileSection();
    const openReqBtn = await screen.findByRole('button', { name: /\+ Add Requirement/i });
    fireEvent.click(openReqBtn);

    // Switch to Custom Product / Service mode
    const customReqBtn = await screen.findByText(/Custom Product \/ Service/i);
    fireEvent.click(customReqBtn);

    // Fill requirement title
    const titleInput = screen.getByPlaceholderText(/1000 MT Structural Steel/i);
    fireEvent.change(titleInput, { target: { value: 'Interstate Refrigerated Cargo Fleet' } });

    // Fill quantity and city
    const qtyInput = screen.getByPlaceholderText('e.g. 1000');
    fireEvent.change(qtyInput, { target: { value: '15' } });

    const cityInputs = screen.getAllByPlaceholderText('e.g. Pune');
    fireEvent.change(cityInputs[cityInputs.length - 1], { target: { value: 'Mumbai' } });

    // Submit
    const submitBtn = screen.getByRole('button', { name: /^Add Requirement$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createReqSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          custom_requirement_title: 'Interstate Refrigerated Cargo Fleet',
          required_quantity: 15,
          delivery_city: 'Mumbai',
        })
      );
    });
  });

  it('allows in-place editing of an existing catalog offering', async () => {
    const updateOfferingSpy = vi.spyOn(businessApi, 'updateOffering').mockResolvedValue({
      id: 'off-1',
      business_profile_id: '22222222-2222-2222-2222-222222222222',
      custom_product_title: 'OPC 53 Bulk Tankers - Updated',
      declared_monthly_capacity: 7500,
      capacity_unit: 'METRIC_TONNE',
      lead_time_days: 5,
      geographic_coverage: ['Pune', 'Mumbai'],
      offers_test_certificates: true,
      vendor_certifications: [],
      open_to_distribution: false,
      target_distribution_regions: [],
      is_public_indicative: true,
      price_currency: 'INR',
      quote_validity_days: 30,
      is_active: true,
    } as any);

    renderBusinessProfileSection();

    // 1. Click Edit on offering card
    const editBtn = await screen.findByTitle('Edit offering');
    fireEvent.click(editBtn);

    // 2. Modal opens with pre-filled title and edit header
    expect(await screen.findByText('Edit Catalog Offering')).toBeInTheDocument();

    // 3. Update title and capacity
    const titleInput = screen.getByDisplayValue('OPC 53 Bulk Tankers');
    fireEvent.change(titleInput, { target: { value: 'OPC 53 Bulk Tankers - Updated' } });

    const capacityInput = screen.getByDisplayValue('5000');
    fireEvent.change(capacityInput, { target: { value: '7500' } });

    // 4. Submit update
    const updateBtn = screen.getByRole('button', { name: /^Update Offering$/i });
    fireEvent.click(updateBtn);

    await waitFor(() => {
      expect(updateOfferingSpy).toHaveBeenCalledWith(
        'off-1',
        expect.objectContaining({
          custom_product_title: 'OPC 53 Bulk Tankers - Updated',
          declared_monthly_capacity: 7500,
        })
      );
    });
  });

  it('allows in-place editing of an existing procurement requirement', async () => {
    const updateReqSpy = vi.spyOn(businessApi, 'updateRequirement').mockResolvedValue({
      id: 'req-1',
      business_profile_id: '22222222-2222-2222-2222-222222222222',
      custom_requirement_title: 'LC3-50 Low Carbon Blend',
      required_quantity: 1500,
      quantity_unit: 'METRIC_TONNE',
      delivery_city: 'Pune West',
      urgency: 'IMMEDIATE',
      is_budget_public: false,
      is_active: true,
    } as any);

    renderBusinessProfileSection();

    // 1. Click Edit on requirement card
    const editBtn = await screen.findByTitle('Edit requirement');
    fireEvent.click(editBtn);

    // 2. Modal opens with pre-filled title and edit header
    expect(await screen.findByText('Edit Procurement Requirement')).toBeInTheDocument();

    // 3. Update quantity
    const qtyInput = screen.getByDisplayValue('1000');
    fireEvent.change(qtyInput, { target: { value: '1500' } });

    // 4. Submit update
    const updateBtn = screen.getByRole('button', { name: /^Update Requirement$/i });
    fireEvent.click(updateBtn);

    await waitFor(() => {
      expect(updateReqSpy).toHaveBeenCalledWith(
        'req-1',
        expect.objectContaining({
          required_quantity: 1500,
        })
      );
    });
  });
});
