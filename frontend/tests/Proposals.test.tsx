import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Proposals } from '@/routes/Proposals';
import { ProposalDetailRoute } from '@/routes/ProposalDetail';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import { ProposalDiffViewer } from '@/components/proposal/ProposalDiffViewer';
import { ProposalDraftModal } from '@/components/proposal/ProposalDraftModal';
import { InChatProposalCard } from '@/components/chat/InChatProposalCard';
import { proposalApi } from '@/lib/api/proposal';
import {
  ProposalDetail,
  ProposalListItem,
  ProposalRevisionDiffResponse,
  ProposalStatus,
} from '@/types/proposal';

vi.mock('@/lib/api/proposal', () => ({
  proposalApi: {
    listProposals: vi.fn(),
    getProposal: vi.fn(),
    createProposal: vi.fn(),
    approveProposal: vi.fn(),
    counterProposal: vi.fn(),
    rejectProposal: vi.fn(),
    withdrawProposal: vi.fn(),
    getProposalDraftPrefill: vi.fn(),
    getProposalRevisionDiff: vi.fn(),
  },
}));

vi.mock('@/lib/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'usr-1111',
      full_name: 'Aditya Birla',
      email: 'aditya@birla.example.com',
      is_active: true,
    },
    isAuthenticated: true,
  }),
}));

const mockProposalsList: ProposalListItem[] = [
  {
    id: 'prop-001',
    conversation_id: 'conv-101',
    proposer_id: 'usr-2222',
    proposer_name: 'Vikram Solar',
    proposer_company: 'Tata Power Solar',
    proposer_role: 'SUPPLIER',
    recipient_id: 'usr-1111',
    recipient_name: 'Aditya Birla',
    recipient_company: 'Birla Renewables',
    recipient_role: 'BUYER',
    proposal_type: 'SUPPLY_CONTRACT',
    status: 'PENDING_REVIEW',
    current_revision_number: 1,
    current_title: 'Supply Agreement for Bifacial Solar Modules 540W',
    product_name: 'Bifacial Solar PV Modules 540W',
    quantity: 500,
    unit: 'kW',
    total_value: 12500000,
    currency: 'INR',
    expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    concluded_at: null,
    user_is_proposer: false,
    requires_user_action: true,
    contacts_disclosed: false,
  },
  {
    id: 'prop-002',
    conversation_id: 'conv-102',
    proposer_id: 'usr-1111',
    proposer_name: 'Aditya Birla',
    proposer_company: 'Birla Renewables',
    proposer_role: 'BUYER',
    recipient_id: 'usr-3333',
    recipient_name: 'Suresh Raina',
    recipient_company: 'Jindal Steel',
    recipient_role: 'SUPPLIER',
    proposal_type: 'PROCUREMENT_ORDER',
    status: 'MUTUALLY_APPROVED',
    current_revision_number: 2,
    current_title: 'Procurement Order: Galvanized Mounting Structures',
    product_name: 'Galvanized Solar Mounting Structures',
    quantity: 120,
    unit: 'MT',
    total_value: 8400000,
    currency: 'INR',
    expires_at: new Date(Date.now() + 14 * 86400000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    concluded_at: new Date().toISOString(),
    user_is_proposer: true,
    requires_user_action: false,
    contacts_disclosed: true,
  },
];

const mockProposalDetailPending: ProposalDetail = {
  id: 'prop-001',
  conversation_id: 'conv-101',
  proposer: {
    user_id: 'usr-2222',
    full_name: 'Vikram Solar',
    company_name: 'Tata Power Solar',
    designation: 'VP Commercial',
    role: 'SUPPLIER',
  },
  recipient: {
    user_id: 'usr-1111',
    full_name: 'Aditya Birla',
    company_name: 'Birla Renewables',
    designation: 'Procurement Director',
    role: 'BUYER',
  },
  proposal_type: 'SUPPLY_CONTRACT',
  status: 'PENDING_REVIEW',
  current_revision_number: 1,
  active_revision: {
    id: 'rev-001',
    proposal_id: 'prop-001',
    revision_number: 1,
    author_id: 'usr-2222',
    author_name: 'Vikram Solar',
    author_company: 'Tata Power Solar',
    title: 'Supply Agreement for Bifacial Solar Modules 540W',
    proposal_type: 'SUPPLY_CONTRACT',
    product_name: 'Bifacial Solar PV Modules 540W',
    product_code: 'TP-540-BF',
    quantity: 500,
    unit: 'kW',
    unit_price: 25000,
    currency: 'INR',
    total_value: 12500000,
    payment_terms: '20% Advance, 80% against BL',
    delivery_location: 'Mundra Port, Gujarat',
    incoterm: 'CIF',
    delivery_timeline_days: 21,
    governing_standards: ['IEC 61215', 'BIS IS 14286'],
    special_conditions: 'Flash test data required for all lots.',
    notes: 'Warranty 25 years linear performance.',
    revision_summary: null,
    created_at: new Date().toISOString(),
  },
  revisions: [
    {
      id: 'rev-001',
      proposal_id: 'prop-001',
      revision_number: 1,
      author_id: 'usr-2222',
      author_name: 'Vikram Solar',
      author_company: 'Tata Power Solar',
      title: 'Supply Agreement for Bifacial Solar Modules 540W',
      proposal_type: 'SUPPLY_CONTRACT',
      product_name: 'Bifacial Solar PV Modules 540W',
      product_code: 'TP-540-BF',
      quantity: 500,
      unit: 'kW',
      unit_price: 25000,
      currency: 'INR',
      total_value: 12500000,
      payment_terms: '20% Advance, 80% against BL',
      delivery_location: 'Mundra Port, Gujarat',
      incoterm: 'CIF',
      delivery_timeline_days: 21,
      governing_standards: ['IEC 61215', 'BIS IS 14286'],
      special_conditions: 'Flash test data required for all lots.',
      notes: 'Warranty 25 years linear performance.',
      revision_summary: null,
      created_at: new Date().toISOString(),
    },
  ],
  approvals: [
    {
      id: 'appr-001',
      proposal_id: 'prop-001',
      revision_id: 'rev-001',
      revision_number: 1,
      user_id: 'usr-2222',
      user_name: 'Vikram Solar',
      action: 'APPROVED',
      notes: 'Initial formal contract proposal submitted.',
      created_at: new Date().toISOString(),
    },
  ],
  expires_at: new Date(Date.now() + 7 * 86400000).toISOString(),
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  concluded_at: null,
  user_is_proposer: false,
  requires_user_action: true,
  contacts_disclosed: false,
  disclosed_credentials: null,
};

const mockProposalDetailApproved: ProposalDetail = {
  ...mockProposalDetailPending,
  id: 'prop-002',
  status: 'MUTUALLY_APPROVED',
  contacts_disclosed: true,
  requires_user_action: false,
  concluded_at: new Date().toISOString(),
  approvals: [
    ...mockProposalDetailPending.approvals,
    {
      id: 'appr-002',
      proposal_id: 'prop-002',
      revision_id: 'rev-001',
      revision_number: 1,
      user_id: 'usr-1111',
      user_name: 'Aditya Birla',
      action: 'APPROVED',
      notes: 'Terms approved. Direct coordinates unlocked.',
      created_at: new Date().toISOString(),
    },
  ],
  disclosed_credentials: {
    user_id: 'usr-2222',
    full_name: 'Vikram Solar',
    company_name: 'Tata Power Solar Systems Ltd',
    designation: 'VP Commercial',
    email: 'vikram.solar@tatapower.example.com',
    phone_number: '+91 98765 43210',
    hq_city: 'Mumbai, India',
    corporate_website: 'https://tatapowersolar.example.com',
    tax_id_or_registration: 'GSTIN27AAACT2727Q1ZB',
    verification_receipt_hash:
      'c89f2e3a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e',
    disclosed_at: new Date().toISOString(),
  },
};

const mockDiffResponse: ProposalRevisionDiffResponse = {
  proposal_id: 'prop-001',
  from_revision_number: 1,
  to_revision_number: 2,
  from_author_name: 'Vikram Solar',
  to_author_name: 'Aditya Birla',
  from_created_at: new Date().toISOString(),
  to_created_at: new Date().toISOString(),
  changes: [
    {
      field: 'unit_price',
      field_label: 'Unit Price',
      old_value: 25000,
      new_value: 24200,
      change_type: 'MODIFIED',
      numeric_delta: -800,
      formatted_change: '-₹ 800',
    },
    {
      field: 'quantity',
      field_label: 'Quantity',
      old_value: 500,
      new_value: 650,
      change_type: 'MODIFIED',
      numeric_delta: 150,
      formatted_change: '+150 kW',
    },
    {
      field: 'delivery_timeline_days',
      field_label: 'Delivery Timeline (Days)',
      old_value: 21,
      new_value: 14,
      change_type: 'MODIFIED',
      numeric_delta: -7,
      formatted_change: '-7 Days',
    },
  ],
  has_price_change: true,
  has_quantity_change: true,
  has_timeline_change: true,
  has_delivery_change: false,
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Commercial Proposals Hub & Contract Sheet (Subphase 6)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. ProposalStatusBadge Component', () => {
    it('renders all statuses with respective labels and variants', () => {
      const statuses: ProposalStatus[] = [
        'MUTUALLY_APPROVED',
        'PENDING_REVIEW',
        'REVISED',
        'REJECTED',
        'WITHDRAWN',
        'EXPIRED',
        'DRAFT',
      ];

      statuses.forEach((status) => {
        const { unmount } = renderWithClient(<ProposalStatusBadge status={status} />);
        const badge = screen.getByTestId('proposal-status-badge');
        expect(badge).toBeTruthy();
        unmount();
      });
    });
  });

  describe('2. ProposalDiffViewer Component', () => {
    it('renders structured commercial parameters diff correctly', () => {
      renderWithClient(<ProposalDiffViewer diff={mockDiffResponse} />);

      expect(screen.getByText(/Revision Comparison/i)).toBeTruthy();
      expect(screen.getByText(/Price Modified/i)).toBeTruthy();
      expect(screen.getByText(/Volume Changed/i)).toBeTruthy();
      expect(screen.getAllByText('-₹ 800').length).toBeGreaterThan(0);
      expect(screen.getAllByText('+150 kW').length).toBeGreaterThan(0);
      expect(screen.getAllByText('-7 Days').length).toBeGreaterThan(0);
    });

    it('renders loading and empty states cleanly', () => {
      const { rerender } = renderWithClient(<ProposalDiffViewer diff={null} isLoading={true} />);
      expect(screen.getByText(/Computing parameter diff/i)).toBeTruthy();

      rerender(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter>
            <ProposalDiffViewer diff={null} isLoading={false} />
          </MemoryRouter>
        </QueryClientProvider>
      );
      expect(screen.getByText(/Select revisions to view comparative diff/i)).toBeTruthy();
    });
  });

  describe('3. ProposalDraftModal Component', () => {
    it('handles AI auto-fill and form submission in initial draft mode', async () => {
      vi.mocked(proposalApi.getProposalDraftPrefill).mockResolvedValue({
        conversation_id: 'conv-101',
        recipient_id: 'usr-2222',
        proposer_role: 'BUYER',
        recipient_role: 'SUPPLIER',
        suggested_revision: {
          title: 'AI Synthesized Agreement: Bifacial Solar Panels',
          proposal_type: 'SUPPLY_CONTRACT',
          product_name: 'Bifacial Solar Panels',
          quantity: 750,
          unit: 'kW',
          unit_price: 24500,
          currency: 'INR',
          payment_terms: '100% LC at sight',
          delivery_location: 'Kandla Port',
          incoterm: 'CIF',
          delivery_timeline_days: 15,
          governing_standards: ['IEC 61215'],
        },
        grounding_source: 'Dialogue & Catalog Analysis',
        confidence_score: 0.94,
      });

      vi.mocked(proposalApi.createProposal).mockResolvedValue(mockProposalDetailPending);

      const onSuccess = vi.fn();
      const onClose = vi.fn();

      renderWithClient(
        <ProposalDraftModal
          isOpen={true}
          onClose={onClose}
          mode="initial_draft"
          conversationId="conv-101"
          recipientId="usr-2222"
          recipientName="Vikram Solar"
          onSuccess={onSuccess}
        />
      );

      expect(screen.getByText(/Draft Commercial Proposal/i)).toBeTruthy();
      expect(screen.getByText(/Auto-fill from Dialogue/i)).toBeTruthy();

      // Trigger AI Auto-fill
      fireEvent.click(screen.getByText(/Auto-fill from Dialogue/i));

      await waitFor(() => {
        expect(proposalApi.getProposalDraftPrefill).toHaveBeenCalledWith({
          conversation_id: 'conv-101',
          recipient_id: 'usr-2222',
        });
      });

      await waitFor(() => {
        expect(screen.getByText(/94% Confidence/i)).toBeTruthy();
      });

      // Submit the form
      const submitBtn = screen.getByRole('button', { name: /Submit Formal Proposal/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(proposalApi.createProposal).toHaveBeenCalled();
        expect(onSuccess).toHaveBeenCalled();
        expect(onClose).toHaveBeenCalled();
      });
    });
  });

  describe('4. Proposals Hub Route (/proposals)', () => {
    it('renders metric cards, proposals list and handles search', async () => {
      vi.mocked(proposalApi.listProposals).mockResolvedValue(mockProposalsList);

      renderWithClient(<Proposals />);

      await waitFor(() => {
        expect(
          screen.getAllByText('Supply Agreement for Bifacial Solar Modules 540W').length
        ).toBeGreaterThan(0);
      });

      // Metric Strip values
      expect(screen.getAllByText('Action Required').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Mutually Approved').length).toBeGreaterThan(0);

      // Proposals items displayed
      expect(
        screen.getAllByText('Supply Agreement for Bifacial Solar Modules 540W').length
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText('Procurement Order: Galvanized Mounting Structures').length
      ).toBeGreaterThan(0);

      // Search input filtering
      const searchInput = screen.getByPlaceholderText(/Search proposals or counterparties/i);
      fireEvent.change(searchInput, { target: { value: 'Mounting Structures' } });

      expect(
        screen.queryByText('Supply Agreement for Bifacial Solar Modules 540W')
      ).toBeNull();
      expect(
        screen.getAllByText('Procurement Order: Galvanized Mounting Structures').length
      ).toBeGreaterThan(0);
    });
  });

  describe('5. ProposalDetail Route (/proposals/:proposalId)', () => {
    it('gates direct contact credentials when status is pending review', async () => {
      vi.mocked(proposalApi.getProposal).mockResolvedValue(mockProposalDetailPending);

      render(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={['/proposals/prop-001']}>
            <Routes>
              <Route path="/proposals/:proposalId" element={<ProposalDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(
          screen.getByText('Supply Agreement for Bifacial Solar Modules 540W')
        ).toBeTruthy();
      });

      // Invariant: Direct phone and email must NOT be visible
      expect(screen.queryByText('+91 98765 43210')).toBeNull();
      expect(screen.queryByText('vikram.solar@tatapower.example.com')).toBeNull();

      // Dual consensus tracker cards
      expect(screen.getByText(/Dual-Sided Commercial Consensus Tracker/i)).toBeTruthy();
      expect(screen.getByText(/Tata Power Solar/i)).toBeTruthy();
      expect(screen.getByText(/Birla Renewables/i)).toBeTruthy();

      // Action required buttons visible across desktop and mobile responsive views
      expect(screen.getAllByRole('button', { name: /Accept/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole('button', { name: /Counter/i }).length).toBeGreaterThan(0);
      expect(screen.getAllByRole('button', { name: /Decline/i }).length).toBeGreaterThan(0);
    });

    it('unlocks direct contact credentials and cryptographic verification hash when mutually approved', async () => {
      vi.mocked(proposalApi.getProposal).mockResolvedValue(mockProposalDetailApproved);

      render(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={['/proposals/prop-002']}>
            <Routes>
              <Route path="/proposals/:proposalId" element={<ProposalDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText(/Verified Counterparty Contact Credentials/i)).toBeTruthy();
      });

      // Contact credentials verified visible
      expect(screen.getByText('+91 98765 43210')).toBeTruthy();
      expect(screen.getByText('vikram.solar@tatapower.example.com')).toBeTruthy();
      expect(screen.getByText('GSTIN27AAACT2727Q1ZB')).toBeTruthy();
      expect(screen.getByText(/c89f2e3a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e/i)).toBeTruthy();
    });

    it('submits approval when user confirms approval modal', async () => {
      vi.mocked(proposalApi.getProposal).mockResolvedValue(mockProposalDetailPending);
      vi.mocked(proposalApi.approveProposal).mockResolvedValue(mockProposalDetailApproved);

      render(
        <QueryClientProvider client={new QueryClient()}>
          <MemoryRouter initialEntries={['/proposals/prop-001']}>
            <Routes>
              <Route path="/proposals/:proposalId" element={<ProposalDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getAllByRole('button', { name: /Accept/i }).length).toBeGreaterThan(0);
      });

      // Click Accept & Approve button in desktop header
      fireEvent.click(screen.getAllByRole('button', { name: /Accept/i })[0]);

      // Confirm approval modal pops up
      expect(screen.getByText(/Sign & Accept Commercial Proposal/i)).toBeTruthy();

      const confirmBtn = screen.getByRole('button', { name: /Confirm Approval/i });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(proposalApi.approveProposal).toHaveBeenCalledWith('prop-001', {
          notes: undefined,
        });
      });
    });
  });

  describe('6. InChatProposalCard Component (Subphase 7 Real-Time Card)', () => {
    it('renders commercial proposal card with action required banner', () => {
      renderWithClient(<InChatProposalCard proposal={mockProposalsList[0]} />);

      expect(screen.getByTestId('in-chat-proposal-card')).toBeTruthy();
      expect(screen.getByText('Action Required: Your review and decision needed')).toBeTruthy();
      expect(
        screen.getByText('Supply Agreement for Bifacial Solar Modules 540W')
      ).toBeTruthy();
      expect(screen.getByText('500 kW')).toBeTruthy();
      expect(screen.getByText(/INR 12,500,000/i)).toBeTruthy();
      expect(screen.getByText(/Sealed until consensus/i)).toBeTruthy();
      expect(screen.getByText(/Review & Sign Contract →/i)).toBeTruthy();
    });

    it('renders mutually approved consensus card with unlocked credentials CTA', () => {
      renderWithClient(<InChatProposalCard proposal={mockProposalsList[1]} />);

      expect(
        screen.getByText(/Commercial Consensus Achieved • Contact Credentials Unlocked/i)
      ).toBeTruthy();
      expect(
        screen.getByText('Procurement Order: Galvanized Mounting Structures')
      ).toBeTruthy();
      expect(screen.getAllByText(/Credentials Unlocked/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/View Direct Contact Info →/i)).toBeTruthy();
    });
  });
});
