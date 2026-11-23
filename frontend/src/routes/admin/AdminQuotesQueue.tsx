import React, { useState, useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAdminQuotes, getAdminQuoteDetail } from '@/lib/api/admin';
import { AdminQuoteDispatchItem, AdminQuoteDetailResponse } from '@/types/quote';
import { AdminQuoteInspectorModal } from '@/components/admin/AdminQuoteInspectorModal';
import { formatCurrencyValue, formatQuantity, formatUnit } from '@/lib/proposalUtils';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';

export const AdminQuotesQueue: React.FC = () => {
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  const [inspectingQuoteId, setInspectingQuoteId] = useState<string | null>(null);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['adminQuotes', deferredSearch, statusFilter, page, pageSize],
    queryFn: () =>
      getAdminQuotes({
        search: deferredSearch.trim() || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        page,
        page_size: pageSize,
      }),
    refetchInterval: 10000,
  });

  const {
    data: detailQuote,
    isLoading: isDetailLoading,
  } = useQuery<AdminQuoteDetailResponse | null>({
    queryKey: ['adminQuoteDetail', inspectingQuoteId],
    queryFn: () => (inspectingQuoteId ? getAdminQuoteDetail(inspectingQuoteId) : null),
    enabled: Boolean(inspectingQuoteId),
  });

  const quotes: AdminQuoteDispatchItem[] = data?.items || [];
  const metrics = data?.metrics || {
    total_dispatched: 0,
    total_quoted_value: 0,
    unique_vendors: 0,
    unique_customers: 0,
    sent_count: 0,
    failed_count: 0,
    delivery_rate_percent: 100,
  };
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-8 space-y-6" data-testid="admin-quotes-queue">
      {/* Header Landmark */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brass">
            <span>🛡️</span>
            <span>Administrative Governance</span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-ink-primary mt-1">
            Commercial Quotations Directory & Audit
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1 max-w-2xl">
            Inspect platform-wide commercial quotation transmissions, track SMTP email delivery success rates, and monitor conference procurement deal flow.
          </p>
        </div>

        <button
          type="button"
          onClick={() => refetch()}
          className="px-3.5 py-2 rounded-lg text-xs font-semibold bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border text-ink-primary transition-colors flex items-center gap-1.5 self-start sm:self-auto shadow-2xs"
        >
          <span>🔄</span>
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Metric Summary Strip (Responsive 2x2 grid on mobile, 4-col on desktop) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Quotes Dispatched */}
        <div className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-muted uppercase tracking-wider font-mono">
              Total Quotes
            </span>
            <span className="text-base">✉️</span>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-ink-primary">
            {metrics.total_dispatched}
          </div>
          <p className="mt-1 text-[11px] text-ink-secondary">
            Dispatched via conference relay
          </p>
        </div>

        {/* Total Commercial Value Quoted */}
        <div className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-muted uppercase tracking-wider font-mono">
              Total Quoted GMV
            </span>
            <span className="text-base text-emerald-600">💰</span>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-emerald-700 dark:text-emerald-400">
            {formatCurrencyValue(metrics.total_quoted_value, 'INR')}
          </div>
          <p className="mt-1 text-[11px] text-ink-secondary">
            Cumulative commercial consideration
          </p>
        </div>

        {/* Delivery Success Rate */}
        <div className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-muted uppercase tracking-wider font-mono">
              Delivery Success
            </span>
            <span className="text-base text-emerald-500">✓</span>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-ink-primary">
            {metrics.delivery_rate_percent}%
          </div>
          <p className="mt-1 text-[11px] text-ink-secondary">
            {metrics.sent_count} delivered / {metrics.failed_count} failed
          </p>
        </div>

        {/* Active Parties */}
        <div className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-ink-muted uppercase tracking-wider font-mono">
              Active Delegates
            </span>
            <span className="text-base">👥</span>
          </div>
          <div className="mt-2 text-2xl font-bold tracking-tight text-ink-primary">
            {metrics.unique_vendors} / {metrics.unique_customers}
          </div>
          <p className="mt-1 text-[11px] text-ink-secondary">
            Unique suppliers / buyers participating
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        <div className="flex-1 max-w-md relative">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setPage(1);
            }}
            placeholder="Search reference #, commodity, vendor, customer, email..."
            className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-canvas-base border border-canvas-border text-ink-primary placeholder:text-ink-muted focus:outline-hidden focus:border-brass focus:ring-1 focus:ring-brass"
          />
          <span className="absolute left-3 top-2.5 text-xs text-ink-muted pointer-events-none">
            🔍
          </span>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 bg-canvas-base p-1 rounded-lg border border-canvas-border overflow-x-auto shrink-0">
          {[
            { id: 'all', label: 'All Dispatches' },
            { id: 'SENT', label: 'Delivered (SENT)' },
            { id: 'FAILED', label: 'Failed (FAILED)' },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold whitespace-nowrap transition-colors ${
                statusFilter === tab.id
                  ? 'bg-canvas-elevated text-ink-primary shadow-2xs border border-canvas-border'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Data Presentation */}
      {isLoading ? (
        <LoadingState message="Loading platform commercial quotes..." />
      ) : isError ? (
        <div className="p-6 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs">
          Failed to load commercial quotations: {(error as any)?.message || 'Unknown error'}
        </div>
      ) : quotes.length === 0 ? (
        <EmptyState
          title="No Commercial Quotations Found"
          description={
            searchInput.trim() || statusFilter !== 'all'
              ? 'No quotation transmissions match your active search and filter parameters.'
              : 'As conference suppliers dispatch commercial quotations to delegates, records will appear here.'
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Table View */}
          <div className="hidden md:block rounded-xl border border-canvas-border bg-canvas-surface overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs divide-y divide-canvas-border">
                <thead className="bg-canvas-elevated text-ink-muted font-mono uppercase text-[10px] tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Reference #</th>
                    <th className="py-3 px-4">Commodity & Volume</th>
                    <th className="py-3 px-4">Vendor (Seller)</th>
                    <th className="py-3 px-4">Customer (Buyer)</th>
                    <th className="py-3 px-4">Quoted Consideration</th>
                    <th className="py-3 px-4">Delivery Status</th>
                    <th className="py-3 px-4">Sent At</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-canvas-border">
                  {quotes.map((q) => (
                    <tr
                      key={q.id}
                      className="hover:bg-canvas-base/60 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-ink-primary">
                        <span className="px-2 py-0.5 rounded bg-brass/10 border border-brass/25 text-brass">
                          {q.quote_reference_number}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-ink-primary">{q.product_name}</div>
                        <div className="text-[11px] text-ink-muted">
                          {formatQuantity(q.quantity)} {formatUnit(q.quantity_unit || 'MT')} • {q.incoterm}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-ink-primary">{q.vendor_name}</div>
                        <div className="text-[11px] text-ink-muted">{q.vendor_company || q.sender_email}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-ink-primary">{q.customer_name}</div>
                        <div className="text-[11px] text-ink-muted">{q.recipient_email}</div>
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-emerald-700 dark:text-emerald-400">
                        {formatCurrencyValue(q.total_value, q.currency)}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                            q.delivery_status === 'SENT'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                          }`}
                        >
                          {q.delivery_status === 'SENT' ? '✓ SENT' : `✕ ${q.delivery_status}`}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-ink-muted text-[11px] whitespace-nowrap">
                        {new Date(q.sent_at).toLocaleDateString()}{' '}
                        {new Date(q.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => setInspectingQuoteId(q.id)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-md border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary transition shadow-2xs"
                        >
                          Inspect →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Card View (< 768px) */}
          <div className="md:hidden space-y-3">
            {quotes.map((q) => (
              <div
                key={q.id}
                className="p-4 rounded-xl bg-canvas-surface border border-canvas-border shadow-2xs space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-brass/10 border border-brass/25 text-brass">
                    {q.quote_reference_number}
                  </span>
                  <span
                    className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                      q.delivery_status === 'SENT'
                        ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                        : 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                    }`}
                  >
                    {q.delivery_status === 'SENT' ? '✓ SENT' : `✕ ${q.delivery_status}`}
                  </span>
                </div>

                <div>
                  <h3 className="font-bold text-sm text-ink-primary">{q.product_name}</h3>
                  <p className="text-xs text-ink-secondary">
                    {formatQuantity(q.quantity)} {formatUnit(q.quantity_unit || 'MT')} • {q.incoterm} • {q.lead_time_days}d Lead
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-canvas-border">
                  <div>
                    <span className="text-[10px] text-ink-muted block uppercase font-mono">Vendor</span>
                    <span className="font-medium text-ink-primary">{q.vendor_name}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block uppercase font-mono">Customer</span>
                    <span className="font-medium text-ink-primary">{q.customer_name}</span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block uppercase font-mono">Quoted GMV</span>
                    <span className="font-mono font-bold text-emerald-700 dark:text-emerald-400">
                      {formatCurrencyValue(q.total_value, q.currency)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[10px] text-ink-muted block uppercase font-mono">Sent</span>
                    <span className="text-[11px] text-ink-secondary">
                      {new Date(q.sent_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setInspectingQuoteId(q.id)}
                  className="w-full py-2 text-xs font-semibold rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary transition shadow-2xs flex items-center justify-center gap-1.5"
                >
                  <span>🔍</span>
                  <span>Inspect Audit & Email Payload</span>
                </button>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between p-3 rounded-xl bg-canvas-surface border border-canvas-border text-xs">
              <span className="text-ink-secondary">
                Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total} quotations
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-1 rounded-md border border-canvas-border bg-canvas-elevated disabled:opacity-40 text-ink-primary font-semibold"
                >
                  ← Prev
                </button>
                <span className="font-mono text-ink-muted">
                  {page} / {totalPages}
                </span>
                <button
                  type="button"
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-1 rounded-md border border-canvas-border bg-canvas-elevated disabled:opacity-40 text-ink-primary font-semibold"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Forensic Inspector Modal */}
      {inspectingQuoteId && (
        <AdminQuoteInspectorModal
          quote={detailQuote || null}
          isLoading={isDetailLoading}
          onClose={() => setInspectingQuoteId(null)}
        />
      )}
    </div>
  );
};
