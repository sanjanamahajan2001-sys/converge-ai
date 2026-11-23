import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { quoteApi } from '@/lib/api/quote';
import { useAuth } from '@/lib/auth/AuthContext';
import { QuoteVendorPanelItem, QuoteVendorPanelResponse } from '@/types/quote';
import { QuoteStatusBadge, QuoteUrgencyBadge } from '@/components/quotes/QuoteStatusBadge';
import { AskSpecificationsDrawer } from '@/components/quotes/AskSpecificationsDrawer';
import { SendQuoteEmailModal } from '@/components/quotes/SendQuoteEmailModal';
import { formatQuantity, formatUnit, formatCurrencyValue } from '@/lib/proposalUtils';

export const Quotes: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [viewRole, setViewRole] = useState<'vendor' | 'buyer'>('vendor');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [page, setPage] = useState<number>(1);

  const [selectedAskForDrawer, setSelectedAskForDrawer] = useState<QuoteVendorPanelItem | null>(null);
  const [selectedAskForQuoteModal, setSelectedAskForQuoteModal] = useState<QuoteVendorPanelItem | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const {
    data: panelData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<QuoteVendorPanelResponse>({
    queryKey: ['quotes-panel', viewRole, statusFilter, debouncedSearch, page],
    queryFn: () =>
      viewRole === 'buyer'
        ? quoteApi.listBuyerAsksPanel({
            status: statusFilter,
            search: debouncedSearch || undefined,
            page,
            page_size: 20,
          })
        : quoteApi.listVendorQuotesPanel({
            status: statusFilter,
            search: debouncedSearch || undefined,
            page,
            page_size: 20,
          }),
    enabled: !user?.is_organizer,
    refetchInterval: 10000,
  });

  const counts = panelData?.counts || { all: 0, new_inquiries: 0, quoted: 0, declined: 0 };
  const items = panelData?.items || [];

  const handleDecline = async (item: QuoteVendorPanelItem) => {
    if (!window.confirm(`Decline inquiry "${item.title}"?`)) return;
    try {
      await quoteApi.declineQuote(item.match_id);
      setToastMessage('Inquiry declined successfully.');
      queryClient.invalidateQueries({ queryKey: ['vendor-quotes-panel'] });
    } catch (err: any) {
      alert(err.message || 'Failed to decline inquiry.');
    }
  };

  const handleQuoteSentSuccess = (res: any) => {
    setSelectedAskForQuoteModal(null);
    setToastMessage(`Quotation ${res.quote_reference_number} dispatched to ${res.recipient_email}!`);
    queryClient.invalidateQueries({ queryKey: ['vendor-quotes-panel'] });
  };

  if (user?.is_organizer) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center" data-testid="organizer-quotes-notice">
        <div className="bg-canvas-surface border border-canvas-border rounded-2xl p-8 sm:p-10 shadow-sm">
          <div className="w-16 h-16 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-3xl mx-auto mb-4 select-none">
            🎪
          </div>
          <h2 className="text-xl sm:text-2xl font-serif font-bold text-ink-primary">
            Organizer Console Notice
          </h2>
          <p className="text-sm text-ink-secondary mt-3 max-w-md mx-auto leading-relaxed">
            The Quotations &amp; RFQ Hub is designated exclusively for commercial buyers and vendor delegates conducting trade inquiries.
          </p>
          <p className="text-xs text-ink-muted mt-2 max-w-md mx-auto">
            As a conference organizer, your central hub for managing events, summits, and digital brochures is the Organizer Dashboard.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/organizer"
              className="px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg bg-brass text-white hover:bg-brass/90 transition-colors shadow-xs"
            >
              Go to Organizer Dashboard →
            </Link>
            <Link
              to="/company/brochure"
              className="px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg border border-canvas-border bg-canvas-elevated text-ink-primary hover:border-brass transition-colors"
            >
              Master Brochure Studio
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="vendor-quotes-hub">
      {/* Toast notification */}
      {toastMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-700 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <span>✓</span>
            <span className="font-semibold">{toastMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setToastMessage(null)}
            className="text-emerald-700 hover:text-emerald-900 dark:hover:text-emerald-100 text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Hero Header */}
      <div className="p-6 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl">{viewRole === 'buyer' ? '📢' : '📋'}</span>
            <h1 className="font-serif text-xl sm:text-2xl font-bold tracking-tight text-ink-primary">
              {viewRole === 'buyer' ? 'My Procurement Asks & RFQs' : 'Vendor Quotations & RFQ Hub'}
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary max-w-2xl">
            {viewRole === 'buyer'
              ? 'Inspect commercial procurement inquiries broadcasted to conference suppliers, review matched vendor counts, and track received quotation terms.'
              : 'Review incoming procurement asks matched by buyer delegate AI agents and dispatch off-platform commercial quotations via email directly to customer inboxes.'}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => refetch()}
            className="px-3.5 py-2 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary text-xs font-semibold transition-colors flex items-center gap-1.5"
            title="Refresh inquiry feeds"
          >
            <span>🔄</span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Role View Toggle: Vendor Inquiries vs Buyer RFQs */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-1.5 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => {
              setViewRole('vendor');
              setPage(1);
            }}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              viewRole === 'vendor'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>📥</span>
            <span>Incoming Inquiries (As Vendor)</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setViewRole('buyer');
              setPage(1);
            }}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 ${
              viewRole === 'buyer'
                ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <span>📢</span>
            <span>My Broadcasted RFQs (As Buyer)</span>
          </button>
        </div>
        <div className="text-xs text-ink-muted px-2">
          {viewRole === 'buyer'
            ? 'Showing asks you broadcasted as a buyer'
            : 'Showing asks where you were matched as a supplier'}
        </div>
      </div>

      {/* 4-Card Commercial Opportunity Metric Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Card 1: New Inquiries */}
        <div
          onClick={() => setStatusFilter('new')}
          className={`p-4 sm:p-5 rounded-2xl border transition-all cursor-pointer ${
            statusFilter === 'new'
              ? 'bg-amber-50/70 border-amber-300 dark:bg-amber-950/30 dark:border-amber-700 shadow-xs'
              : 'bg-canvas-surface border-canvas-border hover:bg-canvas-elevated'
          }`}
          data-testid="metric-new-inquiries"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs font-bold uppercase font-mono text-amber-800 dark:text-amber-400">
              New Inquiries
            </span>
            <span className="text-base sm:text-lg">⚡</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold font-serif text-ink-primary">
              {counts.new_inquiries}
            </span>
            <span className="text-[11px] text-ink-muted">Action needed</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">
            Buyer asks awaiting vendor quote submission
          </p>
        </div>

        {/* Card 2: Quoted via Email */}
        <div
          onClick={() => setStatusFilter('quoted')}
          className={`p-4 sm:p-5 rounded-2xl border transition-all cursor-pointer ${
            statusFilter === 'quoted'
              ? 'bg-emerald-50/70 border-emerald-300 dark:bg-emerald-950/30 dark:border-emerald-700 shadow-xs'
              : 'bg-canvas-surface border-canvas-border hover:bg-canvas-elevated'
          }`}
          data-testid="metric-quoted-email"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs font-bold uppercase font-mono text-emerald-800 dark:text-emerald-400">
              Quotes Sent via Email
            </span>
            <span className="text-base sm:text-lg">✉️</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold font-serif text-ink-primary">
              {counts.quoted}
            </span>
            <span className="text-[11px] text-ink-muted">Bids active</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">
            Commercial terms dispatched to buyer inboxes
          </p>
        </div>

        {/* Card 3: Declined */}
        <div
          onClick={() => setStatusFilter('declined')}
          className={`p-4 sm:p-5 rounded-2xl border transition-all cursor-pointer ${
            statusFilter === 'declined'
              ? 'bg-rose-50/60 border-rose-300 dark:bg-rose-950/30 dark:border-rose-700 shadow-xs'
              : 'bg-canvas-surface border-canvas-border hover:bg-canvas-elevated'
          }`}
          data-testid="metric-declined"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs font-bold uppercase font-mono text-rose-800 dark:text-rose-400">
              Declined
            </span>
            <span className="text-base sm:text-lg">✕</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold font-serif text-ink-primary">
              {counts.declined}
            </span>
            <span className="text-[11px] text-ink-muted">Archived</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">
            Asks passed due to capacity or scope limits
          </p>
        </div>

        {/* Card 4: Total Opportunities */}
        <div
          onClick={() => setStatusFilter('all')}
          className={`p-4 sm:p-5 rounded-2xl border transition-all cursor-pointer ${
            statusFilter === 'all'
              ? 'bg-purple-50/70 border-purple-300 dark:bg-purple-950/30 dark:border-purple-700 shadow-xs'
              : 'bg-canvas-surface border-canvas-border hover:bg-canvas-elevated'
          }`}
          data-testid="metric-total-opportunities"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] sm:text-xs font-bold uppercase font-mono text-purple-800 dark:text-purple-400">
              Total Opportunities
            </span>
            <span className="text-base sm:text-lg">💼</span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold font-serif text-ink-primary">
              {counts.all}
            </span>
            <span className="text-[11px] text-ink-muted">All-time</span>
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">
            Total procurement matches across conference
          </p>
        </div>
      </div>

      {/* Status Filter Tabs & Search Bar */}
      <div className="p-4 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 text-xs font-semibold">
          {[
            { id: 'all', label: 'All Asks', count: counts.all },
            { id: 'new', label: 'New (Action Needed)', count: counts.new_inquiries },
            { id: 'quoted', label: 'Quoted via Email', count: counts.quoted },
            { id: 'declined', label: 'Declined', count: counts.declined },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setStatusFilter(tab.id);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                statusFilter === tab.id
                  ? 'bg-brass text-white shadow-2xs'
                  : 'bg-canvas-elevated text-ink-secondary hover:text-ink-primary hover:bg-canvas-sunken border border-canvas-border'
              }`}
            >
              <span>{tab.label}</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${
                statusFilter === tab.id ? 'bg-white/25 text-white' : 'bg-canvas-surface text-ink-muted'
              }`}>
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[240px] md:w-72">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search commodity, buyer, city..."
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brass"
          />
          <span className="absolute left-2.5 top-2 text-ink-muted text-xs">🔍</span>
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm('')}
              className="absolute right-2.5 top-2 text-ink-muted hover:text-ink-primary text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Main Content: Desktop Table & Mobile Cards */}
      {isLoading ? (
        <div className="p-12 text-center rounded-2xl bg-canvas-surface border border-canvas-border space-y-2 text-xs text-ink-muted">
          <div className="animate-spin text-2xl">⏳</div>
          <p>Loading incoming procurement inquiries...</p>
        </div>
      ) : isError ? (
        <div className="p-6 rounded-2xl bg-rose-50 border border-rose-300 text-xs text-rose-700">
          Failed to load quote inquiries: {(error as any)?.message || 'Server connection error.'}
        </div>
      ) : items.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-canvas-surface border border-canvas-border space-y-3">
          <div className="text-4xl">📭</div>
          <h3 className="font-serif text-base font-bold text-ink-primary">
            No procurement asks found
          </h3>
          <p className="text-xs text-ink-muted max-w-sm mx-auto">
            {searchTerm
              ? `No inquiries match "${searchTerm}". Try adjusting your keywords.`
              : statusFilter !== 'all'
              ? `There are currently no asks in the "${statusFilter}" category.`
              : 'As conference participants and AI delegates formulate commercial needs, matching asks will appear here.'}
          </p>
          {(searchTerm || statusFilter !== 'all') && (
            <button
              type="button"
              onClick={() => {
                setSearchTerm('');
                setStatusFilter('all');
              }}
              className="px-4 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs font-semibold text-ink-primary hover:bg-canvas-sunken"
            >
              Clear Filters
            </button>
          )}
        </div>
      ) : (
        <>
          {/* Desktop Table View (>= 768px) */}
          <div className="hidden md:block rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs overflow-hidden">
            <table className="w-full text-left border-collapse text-xs" data-testid="vendor-quotes-table">
              <thead>
                <tr className="border-b border-canvas-border bg-canvas-elevated text-[11px] font-mono uppercase text-ink-muted">
                  <th className="py-3 px-4 font-bold">Ask & Commodity</th>
                  <th className="py-3 px-4 font-bold">Customer & AI Agent</th>
                  <th className="py-3 px-4 font-bold">Volume & Destination</th>
                  <th className="py-3 px-4 font-bold">Urgency & Timeline</th>
                  <th className="py-3 px-4 font-bold">Match Status</th>
                  <th className="py-3 px-4 font-bold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border/70">
                {items.map((item) => {
                  const unitLabel = formatUnit(item.quantity_unit || 'MT');
                  const rowId = item.match_id || item.quote_request_id;
                  return (
                    <tr
                      key={rowId}
                      className="hover:bg-canvas-elevated/40 transition-colors"
                      data-testid={`ask-row-${rowId}`}
                    >
                      {/* Ask Title & Commodity */}
                      <td className="py-3.5 px-4">
                        <button
                          type="button"
                          onClick={() => setSelectedAskForDrawer(item)}
                          className="font-serif font-bold text-ink-primary hover:text-brass transition-colors text-left block"
                        >
                          {item.title}
                        </button>
                        <div className="text-[11px] text-ink-secondary mt-0.5 flex items-center gap-1.5">
                          <span>{item.product_name}</span>
                          {item.product_code && (
                            <span className="font-mono text-ink-muted">({item.product_code})</span>
                          )}
                        </div>
                      </td>

                      {/* Customer & Persona */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-ink-primary">{item.customer.full_name}</div>
                        <div className="text-[11px] text-ink-muted">
                          {item.customer.company_name || 'Procurement Delegate'}
                        </div>
                        <div className="inline-flex items-center gap-1 text-[10px] text-purple-700 dark:text-purple-300 font-medium mt-0.5">
                          <span>🤖</span>
                          <span>{item.customer_agent_persona || 'Procurement AI Agent'}</span>
                        </div>
                      </td>

                      {/* Volume & Location */}
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-ink-primary font-mono">
                          {formatQuantity(item.quantity)} {unitLabel}
                        </div>
                        <div className="text-[11px] text-ink-secondary mt-0.5">
                          📍 {item.delivery_location || 'Not Specified'}
                        </div>
                      </td>

                      {/* Urgency & Timeline */}
                      <td className="py-3.5 px-4 space-y-1">
                        <QuoteUrgencyBadge urgency={item.urgency} />
                        <div className="text-[11px] text-ink-muted">
                          {item.timeline_days ? `${item.timeline_days} Calendar Days` : 'Standard Lead Time'}
                        </div>
                      </td>

                      {/* Match Status */}
                      <td className="py-3.5 px-4 space-y-1">
                        <QuoteStatusBadge status={item.status} size="sm" />
                        {item.latest_quoted_value && (
                          <div className="text-[11px] font-mono text-emerald-700 dark:text-emerald-400 font-semibold">
                            {formatCurrencyValue(item.latest_quoted_value, item.latest_quoted_currency || 'INR')}
                          </div>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <button
                            type="button"
                            onClick={() => setSelectedAskForDrawer(item)}
                            className="px-2.5 py-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary text-xs font-semibold transition-colors"
                          >
                            {viewRole === 'buyer' ? 'Specs & Bids →' : 'Specs →'}
                          </button>

                          {viewRole === 'vendor' && item.status !== 'DECLINED' && (
                            <button
                              type="button"
                              onClick={() => setSelectedAskForQuoteModal(item)}
                              className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-2xs transition-colors flex items-center gap-1"
                            >
                              <span>✉️</span>
                              <span>Quote</span>
                            </button>
                          )}

                          {viewRole === 'vendor' && item.status === 'PENDING_REVIEW' && (
                            <button
                              type="button"
                              onClick={() => handleDecline(item)}
                              className="p-1.5 rounded-lg border border-rose-200 dark:border-rose-900 text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 text-xs transition-colors"
                              title="Decline Inquiry"
                              aria-label="Decline inquiry"
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Mobile Card List (< 768px) */}
          <div className="md:hidden space-y-3" data-testid="vendor-quotes-mobile-list">
            {items.map((item) => {
              const unitLabel = formatUnit(item.quantity_unit || 'MT');
              const cardId = item.match_id || item.quote_request_id;
              return (
                <div
                  key={cardId}
                  className="p-4 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs space-y-3"
                  data-testid={`ask-mobile-card-${cardId}`}
                >
                  {/* Top Bar: Urgency & Status */}
                  <div className="flex items-center justify-between gap-2 border-b border-canvas-border/60 pb-2.5">
                    <div className="flex items-center gap-1.5">
                      <QuoteUrgencyBadge urgency={item.urgency} />
                      <QuoteStatusBadge status={item.status} size="sm" />
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-muted">
                      {typeof item.match_score === 'number' ? Math.round(item.match_score) : item.match_score}% Match
                    </span>
                  </div>

                  {/* Ask Title & Product */}
                  <div>
                    <h3
                      onClick={() => setSelectedAskForDrawer(item)}
                      className="font-serif font-bold text-sm text-ink-primary hover:text-brass cursor-pointer"
                    >
                      {item.title}
                    </h3>
                    <p className="text-xs text-ink-secondary mt-0.5">
                      Scope: <strong className="text-ink-primary">{item.product_name}</strong>
                    </p>
                  </div>

                  {/* Details Grid */}
                  <div className="grid grid-cols-2 gap-2 p-2.5 rounded-xl bg-canvas-elevated/80 border border-canvas-border text-xs">
                    <div>
                      <span className="text-[10px] text-ink-muted block">Volume</span>
                      <span className="font-bold text-ink-primary font-mono">
                        {formatQuantity(item.quantity)} {unitLabel}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-ink-muted block">Timeline</span>
                      <span className="font-semibold text-ink-primary">
                        {item.timeline_days ? `${item.timeline_days} Days` : 'Standard'}
                      </span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-[10px] text-ink-muted block">Customer</span>
                      <span className="font-semibold text-ink-primary">
                        {item.customer.full_name} ({item.customer.company_name || 'Buyer'})
                      </span>
                      <div className="text-[10px] text-purple-700 dark:text-purple-300 font-medium">
                        🤖 {item.customer_agent_persona || 'Procurement AI Agent'}
                      </div>
                    </div>
                  </div>

                  {/* Quoted status indicator if any */}
                  {item.latest_quoted_value && (
                    <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 flex items-center justify-between text-xs">
                      <span className="text-[10px] uppercase font-bold text-emerald-800 dark:text-emerald-300">
                        Quoted Consideration
                      </span>
                      <span className="font-mono font-bold text-ink-primary">
                        {formatCurrencyValue(item.latest_quoted_value, item.latest_quoted_currency || 'INR')}
                      </span>
                    </div>
                  )}

                  {/* Mobile Action Buttons */}
                  <div className="grid grid-cols-2 gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setSelectedAskForDrawer(item)}
                      className={`px-3 py-2 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-primary text-xs font-semibold text-center ${
                        viewRole === 'buyer' ? 'col-span-2' : ''
                      }`}
                    >
                      {viewRole === 'buyer' ? 'View Specs & Bids Received' : 'View Specs'}
                    </button>

                    {viewRole === 'vendor' && (
                      item.status !== 'DECLINED' ? (
                        <button
                          type="button"
                          onClick={() => setSelectedAskForQuoteModal(item)}
                          className="px-3 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold text-center flex items-center justify-center gap-1 shadow-xs"
                        >
                          <span>✉️</span>
                          <span>Send Quote</span>
                        </button>
                      ) : (
                        <button
                          type="button"
                          disabled
                          className="px-3 py-2 rounded-lg bg-canvas-elevated text-ink-muted text-xs font-semibold text-center"
                        >
                          Declined
                        </button>
                      )
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* Slide-out Drawer for Full Specifications */}
      {selectedAskForDrawer && (
        <AskSpecificationsDrawer
          item={selectedAskForDrawer}
          isOpen={true}
          onClose={() => setSelectedAskForDrawer(null)}
          onStatusUpdated={() => {
            queryClient.invalidateQueries({ queryKey: ['vendor-quotes-panel'] });
          }}
        />
      )}

      {/* Send Quote via Email Modal */}
      {selectedAskForQuoteModal && (
        <SendQuoteEmailModal
          ask={selectedAskForQuoteModal}
          onClose={() => setSelectedAskForQuoteModal(null)}
          onSuccess={handleQuoteSentSuccess}
        />
      )}
    </div>
  );
};
