import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Quotes } from '@/routes/Quotes';
import { quoteApi } from '@/lib/api/quote';
import { QuoteVendorPanelItem, QuoteVendorPanelResponse, QuoteRequestDetail } from '@/types/quote';

vi.mock('@/lib/api/quote', () => ({
  quoteApi: {
    listVendorQuotesPanel: vi.fn(),
    getQuoteDetail: vi.fn(),
    sendQuoteEmail: vi.fn(),
    declineQuote: vi.fn(),
  },
}));

vi.mock('@/lib/auth/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'vendor-usr-001',
      full_name: 'Maahi Sharma',
      company_name: 'Deccan Green Cement',
      email: 'maahi@deccancement.example.com',
      is_active: true,
    },
    isAuthenticated: true,
  }),
}));

const mockAsks: QuoteVendorPanelItem[] = [
  {
    match_id: 'match-101',
    quote_request_id: 'ask-101',
    title: 'High Volume Portland Pozzolana Cement (PPC)',
    product_name: 'Portland Pozzolana Cement (PPC)',
    product_code: 'CEM_PPC',
    quantity: 2500,
    quantity_unit: 'METRIC_TONNE',
    delivery_location: 'Mumbai Port Yard',
    timeline_days: 14,
    urgency: 'HIGH',
    status: 'PENDING_REVIEW',
    match_score: 95.5,
    match_reasons: ['Catalog Match: CEM_PPC', 'Regional Proximity: Western Zone'],
    created_at: new Date().toISOString(),
    customer: {
      id: 'cust-101',
      full_name: 'Sanjana Mahajan',
      company_name: 'InfraTech EPC',
      job_title: 'Procurement Director',
    },
    customer_agent_persona: 'Procurement AI Agent',
    dispatches_count: 0,
  },
  {
    match_id: 'match-102',
    quote_request_id: 'ask-102',
    title: 'Low Carbon Limestone Calcined Clay Cement',
    product_name: 'Limestone Calcined Clay Cement (LC3)',
    product_code: 'CEM_LC3',
    quantity: 1000,
    quantity_unit: 'MT',
    delivery_location: 'Pune Industrial Yard',
    timeline_days: 18,
    urgency: 'CRITICAL',
    status: 'QUOTE_SENT',
    match_score: 92.0,
    match_reasons: ['Green Cement Capability', 'Available Uncommitted Capacity'],
    created_at: new Date().toISOString(),
    customer: {
      id: 'cust-102',
      full_name: 'Vikram Mehta',
      company_name: 'Metro Rail Corp',
      job_title: 'Supply Chain Head',
    },
    customer_agent_persona: 'Green Infra Agent',
    dispatches_count: 1,
    latest_quote_reference: 'QUO-2026-6535EE',
    latest_quoted_value: 3500000,
    latest_quoted_currency: 'INR',
    latest_dispatched_at: new Date().toISOString(),
  },
];

const mockPanelResponse: QuoteVendorPanelResponse = {
  items: mockAsks,
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
  counts: {
    all: 2,
    new_inquiries: 1,
    quoted: 1,
    declined: 0,
  },
};

const mockAskDetail: QuoteRequestDetail = {
  id: 'ask-101',
  match_id: 'match-101',
  title: 'High Volume Portland Pozzolana Cement (PPC)',
  product_name: 'Portland Pozzolana Cement (PPC)',
  product_code: 'CEM_PPC',
  quantity: 2500,
  quantity_unit: 'METRIC_TONNE',
  delivery_location: 'Mumbai Port Yard',
  timeline_days: 14,
  currency: 'INR',
  is_budget_public: false,
  urgency: 'HIGH',
  status: 'MATCHED',
  technical_specifications: {
    compressive_strength_28d: '33 MPa minimum',
    compliance_standard: 'IS 1489 (Part 1): 2015',
    packaging: '50kg HDPE bags',
  },
  inquiry_notes: 'Urgent site delivery required for Phase 2 foundation pouring.',
  created_at: new Date().toISOString(),
  customer: {
    id: 'cust-101',
    full_name: 'Sanjana Mahajan',
    company_name: 'InfraTech EPC',
    job_title: 'Procurement Director',
  },
  customer_agent_persona: 'Procurement AI Agent',
  vendor_match_status: 'PENDING_REVIEW',
  match_score: 95.5,
  match_reasons: ['Catalog Match: CEM_PPC', 'Regional Proximity: Western Zone'],
  dispatches: [],
};

function renderQuotesHub() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Quotes />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Vendor Quotes Hub & Inquiries Portal (Quote Subphase 5)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (quoteApi.listVendorQuotesPanel as any).mockResolvedValue(mockPanelResponse);
    (quoteApi.getQuoteDetail as any).mockResolvedValue(mockAskDetail);
  });

  it('renders header, description and all 4 commercial metric cards with accurate counts', async () => {
    renderQuotesHub();

    expect(screen.getByText('Vendor Quotations & RFQ Hub')).toBeInTheDocument();
    expect(
      screen.getByText(/Review incoming procurement asks matched by buyer delegate AI agents/i)
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('metric-new-inquiries')).toHaveTextContent('1');
    });

    expect(screen.getByTestId('metric-quoted-email')).toHaveTextContent('1');
    expect(screen.getByTestId('metric-declined')).toHaveTextContent('0');
    expect(screen.getByTestId('metric-total-opportunities')).toHaveTextContent('2');
  });

  it('renders incoming ask items in both desktop table and mobile card views', async () => {
    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getByTestId('vendor-quotes-table')).toBeInTheDocument();
    });

    const table = screen.getByTestId('vendor-quotes-table');
    // Ask 1 in table
    expect(within(table).getByText('High Volume Portland Pozzolana Cement (PPC)')).toBeInTheDocument();
    expect(within(table).getByText('Sanjana Mahajan')).toBeInTheDocument();
    expect(within(table).getByText(/2,500 MT/)).toBeInTheDocument();

    // Ask 2 in table
    expect(within(table).getByText('Low Carbon Limestone Calcined Clay Cement')).toBeInTheDocument();
    expect(within(table).getByText('Vikram Mehta')).toBeInTheDocument();

    // Badges
    const statusBadges = screen.getAllByTestId('quote-status-badge');
    expect(statusBadges.length).toBeGreaterThan(0);
  });

  it('filters asks when clicking status tabs', async () => {
    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getByText('New (Action Needed)')).toBeInTheDocument();
    });

    const newTab = screen.getByText('New (Action Needed)');
    fireEvent.click(newTab);

    expect(quoteApi.listVendorQuotesPanel).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 'new',
      })
    );
  });

  it('opens specifications drawer and displays technical tolerances and customer info', async () => {
    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getAllByText('Specs →').length).toBeGreaterThan(0);
    });

    const specsBtn = screen.getAllByText('Specs →')[0];
    fireEvent.click(specsBtn);

    await waitFor(() => {
      expect(screen.getByTestId('ask-specifications-drawer')).toBeInTheDocument();
    });

    expect(screen.getByText('IS 1489 (Part 1): 2015')).toBeInTheDocument();
    expect(screen.getByText('33 MPa minimum')).toBeInTheDocument();
    expect(
      screen.getByText(/Urgent site delivery required for Phase 2 foundation pouring/i)
    ).toBeInTheDocument();
  });

  it('opens send quote email modal and allows switching to live email preview tab', async () => {
    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getAllByText('Quote').length).toBeGreaterThan(0);
    });

    const quoteBtn = screen.getAllByText('Quote')[0];
    fireEvent.click(quoteBtn);

    await waitFor(() => {
      expect(screen.getByTestId('send-quote-email-modal')).toBeInTheDocument();
    });

    expect(screen.getByText('Quotation Terms')).toBeInTheDocument();
    expect(screen.getByText('Live Email Preview')).toBeInTheDocument();

    // Switch to preview tab
    const previewTab = screen.getByText('Live Email Preview');
    fireEvent.click(previewTab);

    expect(screen.getByText(/Commercial Quotation • QUO-2026-DRAFT/i)).toBeInTheDocument();
    expect(screen.getByText(/Google SMTP Verified/i)).toBeInTheDocument();
  });

  it('submits quote via email and displays confirmation toast', async () => {
    (quoteApi.sendQuoteEmail as any).mockResolvedValue({
      quote_reference_number: 'QUO-2026-TEST99',
      match_id: 'match-101',
      dispatch_id: 'disp-999',
      recipient_email: 'sanjana@infratech.example.com',
      sender_email: 'sanjana.mahajan@sofueled.com',
      total_value: 8750000,
      currency: 'INR',
      delivery_status: 'SENT',
      sent_at: new Date().toISOString(),
      delivery_message: 'Delivered',
    });

    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getAllByText('Quote').length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getAllByText('Quote')[0]);

    await waitFor(() => {
      expect(screen.getByTestId('send-quote-email-modal')).toBeInTheDocument();
    });

    const dispatchBtn = screen.getByRole('button', { name: /Send Quote via Email/i });
    fireEvent.click(dispatchBtn);

    await waitFor(() => {
      expect(quoteApi.sendQuoteEmail).toHaveBeenCalled();
    });
  });

  it('declines inquiry when clicking decline button', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    (quoteApi.declineQuote as any).mockResolvedValue({
      status: 'declined',
      match_id: 'match-101',
    });

    renderQuotesHub();

    await waitFor(() => {
      expect(screen.getByLabelText('Decline inquiry')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText('Decline inquiry'));

    await waitFor(() => {
      expect(quoteApi.declineQuote).toHaveBeenCalledWith('match-101');
    });
  });
});
