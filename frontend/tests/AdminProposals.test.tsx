import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as adminApi from '@/lib/api/admin';
import { AdminProposalsQueue } from '@/routes/admin/AdminProposalsQueue';
import { AdminLayout } from '@/components/admin/AdminLayout';
import { AdminAuthProvider } from '@/lib/auth/AdminAuthContext';
import { AdminProposalListResponse, ProposalDetail } from '@/types/proposal';

const mockAdminProposalsList: AdminProposalListResponse = {
  items: [
    {
      id: 'prop-admin-001',
      conversation_id: 'conv-001',
      proposer_id: 'user-001',
      proposer_name: 'Mahajan Sanjana',
      proposer_company: 'InfraTech Solutions',
      proposer_role: 'BUYER',
      recipient_id: 'user-002',
      recipient_name: 'Maahi Sharma',
      recipient_company: 'Deccan Green Cements',
      recipient_role: 'SUPPLIER',
      proposal_type: 'SUPPLY_CONTRACT',
      status: 'PENDING_REVIEW',
      current_revision_number: 1,
      total_revisions_count: 1,
      current_title: 'Strategic Partnership: 1,000 MT Slag Cement',
      product_name: 'Ground Granulated Blast-Furnace Slag',
      total_value: 3200000,
      currency: 'INR',
      expires_at: '2026-11-15T00:00:00Z',
      created_at: '2026-11-05T10:00:00Z',
      updated_at: '2026-11-05T10:00:00Z',
      concluded_at: null,
      approvals_count: 1,
    },
    {
      id: 'prop-admin-002',
      conversation_id: 'conv-002',
      proposer_id: 'user-002',
      proposer_name: 'Maahi Sharma',
      proposer_company: 'Deccan Green Cements',
      proposer_role: 'SUPPLIER',
      recipient_id: 'user-001',
      recipient_name: 'Mahajan Sanjana',
      recipient_company: 'InfraTech Solutions',
      recipient_role: 'BUYER',
      proposal_type: 'SERVICE_MOU',
      status: 'MUTUALLY_APPROVED',
      current_revision_number: 2,
      total_revisions_count: 2,
      current_title: 'Engineering Consultancy MOU',
      product_name: 'Concrete Mix Design Consulting',
      total_value: 450000,
      currency: 'INR',
      expires_at: '2026-11-20T00:00:00Z',
      created_at: '2026-11-04T08:00:00Z',
      updated_at: '2026-11-05T11:00:00Z',
      concluded_at: '2026-11-05T11:00:00Z',
      approvals_count: 2,
    },
  ],
  total: 2,
  page: 1,
  page_size: 15,
  total_pages: 1,
  status_counts: {
    total: 2,
    PENDING_REVIEW: 1,
    MUTUALLY_APPROVED: 1,
    REVISED: 0,
    REJECTED: 0,
    WITHDRAWN: 0,
    EXPIRED: 0,
    DRAFT: 0,
  },
};

const mockAdminProposalDetail: ProposalDetail = {
  id: 'prop-admin-002',
  conversation_id: 'conv-002',
  proposer: {
    user_id: 'user-002',
    full_name: 'Maahi Sharma',
    company_name: 'Deccan Green Cements',
    role: 'SUPPLIER',
  },
  recipient: {
    user_id: 'user-001',
    full_name: 'Mahajan Sanjana',
    company_name: 'InfraTech Solutions',
    role: 'BUYER',
  },
  proposal_type: 'SERVICE_MOU',
  status: 'MUTUALLY_APPROVED',
  current_revision_number: 2,
  expires_at: '2026-11-20T00:00:00Z',
  created_at: '2026-11-04T08:00:00Z',
  updated_at: '2026-11-05T11:00:00Z',
  concluded_at: '2026-11-05T11:00:00Z',
  user_is_proposer: false,
  requires_user_action: false,
  contacts_disclosed: true,
  disclosed_credentials: {
    user_id: 'user-002',
    full_name: 'Maahi Sharma',
    company_name: 'Deccan Green Cements',
    designation: 'Head of Institutional Sales',
    email: 'maahi@deccan.com',
    phone_number: '+91 98765 00000',
    hq_city: 'Hyderabad, India',
    corporate_website: 'https://deccancement.com',
    tax_id_or_registration: 'GSTIN36AAACD1234F1Z5',
    verification_receipt_hash: 'sha256:7b5cf88921abcdef0123456789receipt',
    disclosed_at: '2026-11-05T11:00:00Z',
  },
  active_revision: {
    id: 'rev-002',
    proposal_id: 'prop-admin-002',
    revision_number: 2,
    author_id: 'user-001',
    author_name: 'Mahajan Sanjana',
    author_company: 'InfraTech Solutions',
    title: 'Engineering Consultancy MOU (Final Agreement)',
    proposal_type: 'SERVICE_MOU',
    product_name: 'Concrete Mix Design Consulting',
    product_code: 'CONSULT_MIX_01',
    quantity: 10,
    unit: 'Sessions',
    unit_price: 45000,
    currency: 'INR',
    total_value: 450000,
    payment_terms: '50% Advance, 50% on Final Report Delivery',
    delivery_location: 'Pune Regional Design Center',
    incoterm: 'DDP',
    delivery_timeline_days: 21,
    governing_standards: ['IS 10262:2019', 'ASTM C39'],
    special_conditions: 'Certified high-performance concrete mix formulas.',
    notes: 'Agreed after commercial negotiation.',
    revision_summary: 'Revised scope to 10 consultation sessions.',
    created_at: '2026-11-05T10:30:00Z',
  },
  revisions: [
    {
      id: 'rev-001',
      proposal_id: 'prop-admin-002',
      revision_number: 1,
      author_id: 'user-002',
      author_name: 'Maahi Sharma',
      author_company: 'Deccan Green Cements',
      title: 'Initial Engineering Consultancy MOU',
      proposal_type: 'SERVICE_MOU',
      product_name: 'Concrete Mix Design Consulting',
      quantity: 5,
      unit: 'Sessions',
      unit_price: 50000,
      currency: 'INR',
      total_value: 250000,
      payment_terms: '100% Post Completion',
      delivery_location: 'Pune',
      delivery_timeline_days: 14,
      governing_standards: ['IS 10262'],
      created_at: '2026-11-04T08:00:00Z',
    },
  ],
  approvals: [
    {
      id: 'app-001',
      proposal_id: 'prop-admin-002',
      revision_id: 'rev-002',
      revision_number: 2,
      user_id: 'user-001',
      user_name: 'Mahajan Sanjana',
      action: 'APPROVED',
      notes: 'Terms verified and accepted.',
      ip_address: '192.168.1.50',
      created_at: '2026-11-05T10:45:00Z',
    },
    {
      id: 'app-002',
      proposal_id: 'prop-admin-002',
      revision_id: 'rev-002',
      revision_number: 2,
      user_id: 'user-002',
      user_name: 'Maahi Sharma',
      action: 'APPROVED',
      notes: 'Agreed and signed.',
      ip_address: '10.0.0.99',
      created_at: '2026-11-05T11:00:00Z',
    },
  ],
};

describe('Admin Proposals Portal & Governance (Subphase 8)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderWithProviders = (ui: React.ReactElement, initialRoute = '/admin/proposals') => {
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

  it('renders admin proposals directory with metric cards and proposal rows', async () => {
    vi.spyOn(adminApi, 'getAdminProposals').mockResolvedValue(mockAdminProposalsList);

    renderWithProviders(<AdminProposalsQueue />);

    expect(screen.getByText('Commercial Proposals Directory & Audit')).toBeInTheDocument();

    await waitFor(() => {
      expect(
        screen.getAllByText(/Strategic Partnership: 1,000 MT Slag Cement/i).length
      ).toBeGreaterThan(0);
      expect(
        screen.getAllByText(/Engineering Consultancy MOU/i).length
      ).toBeGreaterThan(0);
    });

    // Check metric cards
    expect(screen.getByText('Total Proposals')).toBeInTheDocument();
    expect(screen.getByText('Under Review / Negotiation')).toBeInTheDocument();
    expect(screen.getByText('Consensus Achieved')).toBeInTheDocument();

    // Check table elements
    expect(screen.getByTestId('admin-proposals-table')).toBeInTheDocument();
    expect(screen.getAllByText('Inspect').length).toBeGreaterThan(0);
  });

  it('triggers search and filters when admin interacts with search and dropdown controls', async () => {
    const getProposalsSpy = vi
      .spyOn(adminApi, 'getAdminProposals')
      .mockResolvedValue(mockAdminProposalsList);

    renderWithProviders(<AdminProposalsQueue />);

    await waitFor(() => {
      expect(
        screen.getAllByText(/Strategic Partnership: 1,000 MT Slag Cement/i).length
      ).toBeGreaterThan(0);
    });

    // Change status dropdown
    const statusSelect = screen.getByLabelText(/Filter by proposal lifecycle status/i);
    fireEvent.change(statusSelect, { target: { value: 'MUTUALLY_APPROVED' } });

    await waitFor(() => {
      expect(getProposalsSpy).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'MUTUALLY_APPROVED' })
      );
    });

    // Search input
    const searchInput = screen.getByPlaceholderText(/Search by proposer, counterparty/i);
    fireEvent.change(searchInput, { target: { value: 'Deccan' } });

    await waitFor(() => {
      expect(getProposalsSpy).toHaveBeenCalledWith(
        expect.objectContaining({ search: 'Deccan' })
      );
    });
  });

  it('opens forensic inspection modal displaying audit ledger, IPs, and disclosed credentials', async () => {
    vi.spyOn(adminApi, 'getAdminProposals').mockResolvedValue(mockAdminProposalsList);
    vi.spyOn(adminApi, 'getAdminProposalDetail').mockResolvedValue(mockAdminProposalDetail);

    renderWithProviders(<AdminProposalsQueue />);

    await waitFor(() => {
      expect(
        screen.getAllByText(/Engineering Consultancy MOU/i).length
      ).toBeGreaterThan(0);
    });

    const inspectButtons = screen.getAllByRole('button', { name: /Inspect/i });
    fireEvent.click(inspectButtons[1]);

    await waitFor(() => {
      expect(screen.getByText('Forensic Proposal Audit Sheet')).toBeInTheDocument();
      expect(screen.getByText('Non-Repudiable Approval Audit Trail')).toBeInTheDocument();
    });

    // Verify non-repudiable approval audit with IP addresses
    expect(screen.getByText('IP: 192.168.1.50')).toBeInTheDocument();
    expect(screen.getByText('IP: 10.0.0.99')).toBeInTheDocument();

    // Verify cryptographic contact disclosure receipt
    expect(screen.getByText(/Verified Contact Credentials Unlocked/i)).toBeInTheDocument();
    expect(screen.getByText('maahi@deccan.com')).toBeInTheDocument();
    expect(screen.getByText('+91 98765 00000')).toBeInTheDocument();
    expect(
      screen.getByText('sha256:7b5cf88921abcdef0123456789receipt')
    ).toBeInTheDocument();

    // Close modal
    fireEvent.click(screen.getByRole('button', { name: /Close Inspector/i }));
    await waitFor(() => {
      expect(screen.queryByText('Forensic Proposal Audit Sheet')).not.toBeInTheDocument();
    });
  });

  it('renders Proposals navigation tab in AdminLayout', () => {
    renderWithProviders(
      <AdminLayout>
        <div>Admin child content</div>
      </AdminLayout>
    );

    // Desktop nav link
    expect(screen.getByRole('link', { name: /Proposals Queue/i })).toHaveAttribute(
      'href',
      '/admin/proposals'
    );
  });
});
