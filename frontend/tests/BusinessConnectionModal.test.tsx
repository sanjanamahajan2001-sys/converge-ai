import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BusinessConnectionModal } from '@/components/matching/BusinessConnectionModal';
import { BusinessMatchCandidate } from '@/types/business';
import { conversationApi } from '@/lib/api/conversation';

const mockCandidate: BusinessMatchCandidate = {
  offering_id: '11111111-2222-3333-4444-555555555555',
  business_profile_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  supplier_user_id: '99999999-8888-7777-6666-555555555555',
  supplier_company_name: 'Maahi Decarb Materials Pvt Ltd',
  supplier_role: 'SUPPLIER',
  offering_title: 'LC3-50 Low Carbon Blend',
  product_code: 'CALCINED_CLAY_LC3',
  grade_code: 'LC3_50_STANDARD',
  composite_score: 95.0,
  score_breakdown: {
    product_relevance: 1.0,
    capacity_feasibility: 1.0,
    commitment_confidence: 1.0,
    delivery_feasibility: 1.0,
    verification_confidence: 1.0,
  },
  declared_monthly_capacity: 2500,
  capacity_unit: 'METRIC_TONNE',
  uncommitted_monthly_capacity: 1500,
  lead_time_days: 10,
  geographic_coverage: ['Pune'],
  offers_test_certificates: true,
  confidence_badges: ['✓ Verified Fresh'],
  price_currency: 'INR',
};

describe('BusinessConnectionModal Component (Phase 4)', () => {
  it('renders modal when open and displays candidate information', () => {
    const handleClose = vi.fn();
    const handleSuccess = vi.fn();

    render(
      <BusinessConnectionModal
        isOpen={true}
        onClose={handleClose}
        candidate={mockCandidate}
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByText('Send Commercial RFQ & Connection Request')).toBeInTheDocument();
    expect(screen.getByText('Maahi Decarb Materials Pvt Ltd')).toBeInTheDocument();
    expect(screen.getByText('Point-in-Time Immutable Commercial Brief (v1)')).toBeInTheDocument();
    expect(
      screen.getByText('Disclose Target Budget in RFQ Brief (Private by default)')
    ).toBeInTheDocument();
  });

  it('submits business context with private budget by default', async () => {
    const handleClose = vi.fn();
    const handleSuccess = vi.fn();

    const spyInitiate = vi.spyOn(conversationApi, 'initiateConversation').mockResolvedValue({
      id: 'conv-uuid-1234',
      initiator_id: 'init-uuid',
      target_id: mockCandidate.supplier_user_id,
      status: 'INVITED',
      match_score: null,
      terminal_outcome: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      concluded_at: null,
      other_participant_id: mockCandidate.supplier_user_id,
      other_participant_name: 'Maahi Decarb Materials Pvt Ltd',
      messages: [],
      message_count: 0,
    });

    render(
      <BusinessConnectionModal
        isOpen={true}
        onClose={handleClose}
        candidate={mockCandidate}
        onSuccess={handleSuccess}
      />
    );

    const submitBtn = screen.getByRole('button', { name: /Send RFQ Connection Request/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(spyInitiate).toHaveBeenCalledWith(
        mockCandidate.supplier_user_id,
        expect.objectContaining({
          inquiry_type: 'RFQ_PRODUCT',
          is_budget_public: false,
          target_price_indication: null,
        })
      );
      expect(handleSuccess).toHaveBeenCalledWith('conv-uuid-1234');
    });

    spyInitiate.mockRestore();
  });
});
