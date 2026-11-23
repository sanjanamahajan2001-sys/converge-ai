import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import * as adminApi from '@/lib/api/admin';
import { AdminQuotesQueue } from '@/routes/admin/AdminQuotesQueue';
import { AdminQuoteListResponse, AdminQuoteDetailResponse } from '@/types/quote';

const mockQuotesResponse: AdminQuoteListResponse = {
  items: [
    {
      id: 'quote-dispatch-001',
      quote_reference_number: 'QUO-2026-TEST01',
      quote_request_id: 'quote-req-001',
      quote_vendor_match_id: 'match-001',
      product_name: 'Limestone Calcined Clay Cement (LC3)',
      product_code: 'LC3_500',
      quantity: 500,
      quantity_unit: 'MT',
      unit_price: 3500,
      total_value: 1750000,
      currency: 'INR',
      incoterm: 'EXW',
      lead_time_days: 14,
      validity_days: 15,
      payment_terms: '20% Advance, 80% on Delivery',
      commercial_notes: 'Third party test certificate included per 50 MT batch.',
      vendor_id: 'vendor-user-001',
      vendor_name: 'Maahi Sharma',
      vendor_company: 'Deccan Decarb Materials Pvt Ltd',
      sender_email: 'maahi@deccan.com',
      customer_id: 'customer-user-001',
      customer_name: 'Mahajan Sanjana',
      customer_company: 'InfraBuild Corp',
      recipient_email: 'sanjana@infrabuild.com',
      email_subject: 'Commercial Quotation: Limestone Calcined Clay Cement (LC3)',
      delivery_status: 'SENT',
      external_message_id: 'msg-smtp-test-999',
      sent_at: '2026-11-09T08:00:00Z',
    },
  ],
  total: 1,
  page: 1,
  page_size: 15,
  total_pages: 1,
  metrics: {
    total_dispatched: 1,
    total_quoted_value: 1750000,
    unique_vendors: 1,
    unique_customers: 1,
    sent_count: 1,
    failed_count: 0,
    delivery_rate_percent: 100,
  },
};

const mockQuoteDetail: AdminQuoteDetailResponse = {
  ...mockQuotesResponse.items[0],
  email_body_html: '<html><body><h1>Commercial Quotation - QUO-2026-TEST01</h1></body></html>',
};

describe('Admin Commercial Quotes & RFQ Governance', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const renderComponent = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <AdminQuotesQueue />
        </MemoryRouter>
      </QueryClientProvider>
    );

  it('renders header, metrics strip, and quotation records', async () => {
    vi.spyOn(adminApi, 'getAdminQuotes').mockResolvedValue(mockQuotesResponse);

    renderComponent();

    expect(screen.getByText(/Commercial Quotations Directory & Audit/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText('QUO-2026-TEST01')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Limestone Calcined Clay Cement (LC3)')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Maahi Sharma')[0]).toBeInTheDocument();
      expect(screen.getAllByText('Mahajan Sanjana')[0]).toBeInTheDocument();
    });

    // Check metric counters
    expect(screen.getByText('Total Quotes')).toBeInTheDocument();
    expect(screen.getByText('Delivery Success')).toBeInTheDocument();
  });

  it('opens inspector modal when clicking Inspect', async () => {
    vi.spyOn(adminApi, 'getAdminQuotes').mockResolvedValue(mockQuotesResponse);
    vi.spyOn(adminApi, 'getAdminQuoteDetail').mockResolvedValue(mockQuoteDetail);

    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText('QUO-2026-TEST01')[0]).toBeInTheDocument();
    });

    // Click inspect button (table view)
    const inspectBtn = screen.getAllByRole('button', { name: /Inspect →/i })[0];
    fireEvent.click(inspectBtn);

    await waitFor(() => {
      expect(screen.getByText(/Commercial Terms & Audit/i)).toBeInTheDocument();
      expect(screen.getByText(/Delivered Email HTML/i)).toBeInTheDocument();
      expect(screen.getByText(/Third party test certificate included per 50 MT batch/i)).toBeInTheDocument();
    });

    // Switch to HTML preview tab
    const emailTab = screen.getByRole('button', { name: /Delivered Email HTML/i });
    fireEvent.click(emailTab);

    expect(screen.getByTitle('Rendered Commercial Quote Email')).toBeInTheDocument();
  });
});
