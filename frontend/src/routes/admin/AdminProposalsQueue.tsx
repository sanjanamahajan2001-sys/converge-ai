import React, { useState, useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { getAdminProposals, getAdminProposalDetail } from '@/lib/api/admin';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  formatQuantity,
  formatUnit,
  formatCurrencyValue,
  cleanProposalTitle,
} from '@/lib/proposalUtils';
import { AdminProposalListItem } from '@/types/proposal';

export const AdminProposalsQueue: React.FC = () => {
  const [searchInput, setSearchInput] = useState<string>('');
  const deferredSearch = useDeferredValue(searchInput);

  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [page, setPage] = useState<number>(1);
  const pageSize = 15;

  // Forensic Inspection Drawer / Modal State
  const [inspectingProposalId, setInspectingProposalId] = useState<string | null>(null);

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['adminProposals', deferredSearch, statusFilter, typeFilter, page, pageSize],
    queryFn: () =>
      getAdminProposals({
        search: deferredSearch.trim() || undefined,
        status: statusFilter !== 'all' ? statusFilter : undefined,
        proposal_type: typeFilter !== 'all' ? typeFilter : undefined,
        page,
        page_size: pageSize,
      }),
    refetchInterval: 10000,
  });

  const {
    data: detailProposal,
    isLoading: isDetailLoading,
  } = useQuery({
    queryKey: ['adminProposalDetail', inspectingProposalId],
    queryFn: () => (inspectingProposalId ? getAdminProposalDetail(inspectingProposalId) : null),
    enabled: Boolean(inspectingProposalId),
  });

  const proposals: AdminProposalListItem[] = data?.items || [];
  const statusCounts = data?.status_counts || {};
  const total = data?.total || 0;
  const totalPages = data?.total_pages || 1;

  // Metric aggregates
  const totalProposals = statusCounts.total || 0;
  const pendingReviewCount =
    (statusCounts.PENDING_REVIEW || 0) + (statusCounts.REVISED || 0);
  const mutuallyApprovedCount = statusCounts.MUTUALLY_APPROVED || 0;
  const terminatedCount =
    (statusCounts.REJECTED || 0) +
    (statusCounts.WITHDRAWN || 0) +
    (statusCounts.EXPIRED || 0);

  return (
    <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-8 space-y-6">
      {/* Header Landmark */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-brass">
            <span>🛡️</span>
            <span>Administrative Governance</span>
          </div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-ink-primary mt-1">
            Commercial Proposals Directory & Audit
          </h1>
          <p className="text-xs sm:text-sm text-ink-secondary mt-1">
            Supervise platform-wide commercial contract negotiations, dual-sided consensus receipts, and cryptographic contact disclosures.
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
        {/* Total Platform Proposals */}
        <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border shadow-2xs">
          <div className="flex items-center justify-between text-xs text-ink-muted">
            <span className="font-medium">Total Proposals</span>
            <span className="text-base" aria-hidden="true">📜</span>
          </div>
          <div className="font-serif text-2xl sm:text-3xl font-bold text-ink-primary mt-2">
            {totalProposals}
          </div>
          <p className="text-[11px] text-ink-secondary mt-1">
            Platform commercial negotiations
          </p>
        </div>

        {/* Pending Review / Active */}
        <div
          onClick={() => {
            setStatusFilter('PENDING_REVIEW');
            setPage(1);
          }}
          className={`p-4 rounded-xl border transition-all cursor-pointer shadow-2xs ${
            statusFilter === 'PENDING_REVIEW'
              ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-400 ring-1 ring-amber-400'
              : 'bg-canvas-elevated border-canvas-border hover:border-amber-400/50'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-amber-700 dark:text-amber-300">
            <span className="font-medium">Under Review / Negotiation</span>
            <span className="text-base" aria-hidden="true">⏳</span>
          </div>
          <div className="font-serif text-2xl sm:text-3xl font-bold text-amber-900 dark:text-amber-100 mt-2">
            {pendingReviewCount}
          </div>
          <p className="text-[11px] text-amber-800/80 dark:text-amber-200/80 mt-1">
            Awaiting counterparty decision
          </p>
        </div>

        {/* Mutually Approved */}
        <div
          onClick={() => {
            setStatusFilter('MUTUALLY_APPROVED');
            setPage(1);
          }}
          className={`p-4 rounded-xl border transition-all cursor-pointer shadow-2xs ${
            statusFilter === 'MUTUALLY_APPROVED'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-500 ring-1 ring-emerald-500'
              : 'bg-canvas-elevated border-canvas-border hover:border-emerald-400/50'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-emerald-700 dark:text-emerald-300">
            <span className="font-medium">Consensus Achieved</span>
            <span className="text-base" aria-hidden="true">🤝</span>
          </div>
          <div className="font-serif text-2xl sm:text-3xl font-bold text-emerald-900 dark:text-emerald-100 mt-2">
            {mutuallyApprovedCount}
          </div>
          <p className="text-[11px] text-emerald-800/80 dark:text-emerald-200/80 mt-1">
            Bilateral sign-off & contacts released
          </p>
        </div>

        {/* Terminated / Concluded */}
        <div
          onClick={() => {
            setStatusFilter('REJECTED');
            setPage(1);
          }}
          className={`p-4 rounded-xl border transition-all cursor-pointer shadow-2xs ${
            statusFilter === 'REJECTED'
              ? 'bg-rose-50 dark:bg-rose-950/30 border-rose-400 ring-1 ring-rose-400'
              : 'bg-canvas-elevated border-canvas-border hover:border-rose-400/50'
          }`}
        >
          <div className="flex items-center justify-between text-xs text-rose-700 dark:text-rose-300">
            <span className="font-medium">Terminated / Declined</span>
            <span className="text-base" aria-hidden="true">✕</span>
          </div>
          <div className="font-serif text-2xl sm:text-3xl font-bold text-rose-900 dark:text-rose-100 mt-2">
            {terminatedCount}
          </div>
          <p className="text-[11px] text-rose-800/80 dark:text-rose-200/80 mt-1">
            Declined, withdrawn, or expired
          </p>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-2xs">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-ink-muted text-xs">
            🔍
          </span>
          <input
            type="text"
            placeholder="Search by proposer, counterparty, product scope, or headline..."
            value={searchInput}
            onChange={(e) => {
              setSearchInput(e.target.value);
              setPage(1);
            }}
            className="w-full pl-8 pr-4 py-2 text-xs rounded-lg bg-canvas-surface border border-canvas-border text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
          />
          {searchInput && (
            <button
              type="button"
              onClick={() => {
                setSearchInput('');
                setPage(1);
              }}
              className="absolute inset-y-0 right-0 pr-3 flex items-center text-ink-muted hover:text-ink-primary text-xs"
            >
              ✕
            </button>
          )}
        </div>

        {/* Filter Selects */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Status Dropdown */}
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-xs rounded-lg bg-canvas-surface border border-canvas-border text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
            aria-label="Filter by proposal lifecycle status"
          >
            <option value="all">All Lifecycle States</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="REVISED">Counter-Offered (Revised)</option>
            <option value="MUTUALLY_APPROVED">Mutually Approved</option>
            <option value="REJECTED">Declined / Rejected</option>
            <option value="WITHDRAWN">Withdrawn by Author</option>
            <option value="EXPIRED">Expired</option>
            <option value="DRAFT">Local Draft</option>
          </select>

          {/* Proposal Type Dropdown */}
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-xs rounded-lg bg-canvas-surface border border-canvas-border text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
            aria-label="Filter by contract category"
          >
            <option value="all">All Contract Types</option>
            <option value="SUPPLY_CONTRACT">Supply Contract</option>
            <option value="SERVICE_AGREEMENT">Service Agreement</option>
            <option value="DISTRIBUTION_AGREEMENT">Distribution Agreement</option>
            <option value="STRATEGIC_PARTNERSHIP">Strategic Partnership</option>
            <option value="PILOT_TRIAL">Pilot Trial</option>
          </select>

          {(statusFilter !== 'all' || typeFilter !== 'all' || searchInput) && (
            <button
              type="button"
              onClick={() => {
                setStatusFilter('all');
                setTypeFilter('all');
                setSearchInput('');
                setPage(1);
              }}
              className="px-2.5 py-2 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:underline"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <LoadingState message="Loading administrative proposals queue..." />
      ) : isError ? (
        <div className="p-6 rounded-xl bg-rose-50 dark:bg-rose-950/20 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-xs">
          <p className="font-bold">Failed to load platform proposals.</p>
          <p className="mt-1">{(error as any)?.message || 'Please check your connection or credentials.'}</p>
        </div>
      ) : proposals.length === 0 ? (
        <EmptyState
          title="No Commercial Proposals Found"
          description={
            searchInput || statusFilter !== 'all' || typeFilter !== 'all'
              ? 'No proposals matched your administrative search criteria.'
              : 'No commercial proposals have been transacted on the platform yet.'
          }
          emoji="📜"
        />
      ) : (
        <div className="space-y-4">
          {/* Desktop Proposals Table (Hidden on small mobile screens) */}
          <div className="hidden md:block rounded-xl bg-canvas-surface border border-canvas-border overflow-hidden shadow-2xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse" data-testid="admin-proposals-table">
                <thead>
                  <tr className="bg-canvas-elevated border-b border-canvas-border text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                    <th className="py-3 px-4">Status & Rev</th>
                    <th className="py-3 px-4">Proposal / Product Scope</th>
                    <th className="py-3 px-4">Proposer (Author)</th>
                    <th className="py-3 px-4">Counterparty</th>
                    <th className="py-3 px-4">Commercial Value</th>
                    <th className="py-3 px-4">Approvals</th>
                    <th className="py-3 px-4">Created / Expires</th>
                    <th className="py-3 px-4 text-right">Audit Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-canvas-border text-xs">
                  {proposals.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-canvas-elevated/60 transition-colors"
                    >
                      {/* Status & Rev */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1 items-start">
                          <ProposalStatusBadge status={item.status} size="sm" />
                          <span className="text-[10px] font-mono text-ink-muted">
                            Rev {item.current_revision_number} of {item.total_revisions_count}
                          </span>
                        </div>
                      </td>

                      {/* Proposal / Scope */}
                      <td className="py-3.5 px-4">
                        <div className="font-serif font-bold text-ink-primary max-w-xs truncate" title={item.current_title}>
                          {cleanProposalTitle(item.current_title)}
                        </div>
                        <div className="text-[11px] text-ink-muted mt-0.5">
                          {item.product_name}
                        </div>
                        <span className="inline-block mt-1 text-[9px] uppercase font-mono px-1.5 py-0.2 rounded bg-canvas-elevated border border-canvas-border text-ink-secondary">
                          {item.proposal_type.replace(/_/g, ' ')}
                        </span>
                      </td>

                      {/* Proposer */}
                      <td className="py-3.5 px-4">
                        <Link
                          to={`/admin/users/${item.proposer_id}`}
                          className="font-medium text-ink-primary hover:text-brass transition-colors block truncate"
                        >
                          {item.proposer_name}
                        </Link>
                        <div className="text-[11px] text-ink-muted flex items-center gap-1 mt-0.5">
                          {item.proposer_company && <span className="truncate">{item.proposer_company}</span>}
                          <span className="text-[9px] uppercase font-mono px-1 rounded bg-canvas-elevated border border-canvas-border shrink-0">
                            {item.proposer_role}
                          </span>
                        </div>
                      </td>

                      {/* Recipient */}
                      <td className="py-3.5 px-4">
                        <Link
                          to={`/admin/users/${item.recipient_id}`}
                          className="font-medium text-ink-primary hover:text-brass transition-colors block truncate"
                        >
                          {item.recipient_name}
                        </Link>
                        <div className="text-[11px] text-ink-muted flex items-center gap-1 mt-0.5">
                          {item.recipient_company && <span className="truncate">{item.recipient_company}</span>}
                          <span className="text-[9px] uppercase font-mono px-1 rounded bg-canvas-elevated border border-canvas-border shrink-0">
                            {item.recipient_role}
                          </span>
                        </div>
                      </td>

                      {/* Value */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-mono font-bold text-ink-primary">
                          {item.total_value != null
                            ? formatCurrencyValue(item.total_value, item.currency)
                            : 'Unspecified'}
                        </div>
                      </td>

                      {/* Approvals */}
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-bold ${
                            item.approvals_count >= 2
                              ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border border-emerald-300'
                              : item.approvals_count === 1
                              ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-200 border border-amber-300'
                              : 'bg-canvas-base border border-canvas-border text-ink-muted'
                          }`}
                        >
                          <span>{item.approvals_count >= 2 ? '✓✓' : item.approvals_count === 1 ? '✓' : '○'}</span>
                          <span>{item.approvals_count} / 2</span>
                        </span>
                      </td>

                      {/* Created / Expires */}
                      <td className="py-3.5 px-4 whitespace-nowrap text-[11px] text-ink-muted">
                        <div>
                          Created: {new Date(item.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                        </div>
                        <div className="mt-0.5">
                          Expires: {new Date(item.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => setInspectingProposalId(item.id)}
                            className="px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-canvas-elevated hover:bg-brass hover:text-white border border-canvas-border transition-colors flex items-center gap-1 shadow-2xs"
                          >
                            <span>🔍</span>
                            <span>Inspect</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile High-Contrast Cards List (Visible on screens < 768px) */}
          <div className="md:hidden space-y-3" data-testid="admin-proposals-mobile-list">
            {proposals.map((item) => (
              <div
                key={item.id}
                className="p-4 rounded-xl bg-canvas-surface border border-canvas-border space-y-3 shadow-2xs"
              >
                {/* Header: Status, Rev, Category */}
                <div className="flex items-center justify-between gap-2 border-b border-canvas-border pb-2">
                  <div className="flex items-center gap-1.5">
                    <ProposalStatusBadge status={item.status} size="sm" />
                    <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-muted">
                      Rev {item.current_revision_number}
                    </span>
                  </div>
                  <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-secondary">
                    {item.proposal_type.replace(/_/g, ' ')}
                  </span>
                </div>

                {/* Title & Product */}
                <div>
                  <h3 className="font-serif font-bold text-ink-primary text-sm">
                    {cleanProposalTitle(item.current_title)}
                  </h3>
                  <p className="text-xs text-ink-secondary mt-0.5">
                    Product: <strong className="text-ink-primary">{item.product_name}</strong>
                  </p>
                </div>

                {/* Counterparties & Commercial Consideration Strip */}
                <div className="p-2.5 rounded-lg bg-canvas-elevated border border-canvas-border grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="block text-[10px] text-ink-muted">Proposer</span>
                    <span className="font-semibold text-ink-primary truncate block">
                      {item.proposer_name}
                    </span>
                    <span className="text-[10px] text-ink-muted">({item.proposer_role})</span>
                  </div>
                  <div>
                    <span className="block text-[10px] text-ink-muted">Recipient</span>
                    <span className="font-semibold text-ink-primary truncate block">
                      {item.recipient_name}
                    </span>
                    <span className="text-[10px] text-ink-muted">({item.recipient_role})</span>
                  </div>
                  <div className="col-span-2 pt-1 border-t border-canvas-border/50 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] text-ink-muted block">Contract Value</span>
                      <span className="font-mono font-bold text-ink-primary text-xs">
                        {item.total_value != null
                          ? formatCurrencyValue(item.total_value, item.currency)
                          : 'Unspecified'}
                      </span>
                    </div>
                    <div>
                      <span className="text-[10px] text-ink-muted block text-right">Approvals</span>
                      <span className="font-mono text-xs font-bold text-ink-primary text-right block">
                        {item.approvals_count} / 2
                      </span>
                    </div>
                  </div>
                </div>

                {/* 1-Click Action */}
                <button
                  type="button"
                  onClick={() => setInspectingProposalId(item.id)}
                  className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border text-ink-primary flex items-center justify-center gap-1.5 shadow-2xs"
                >
                  <span>🔍</span>
                  <span>Inspect Forensic Audit Sheet</span>
                </button>
              </div>
            ))}
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-canvas-border text-xs text-ink-muted">
            <div>
              Showing <span className="font-bold text-ink-primary">{(page - 1) * pageSize + 1}</span> to{' '}
              <span className="font-bold text-ink-primary">{Math.min(page * pageSize, total)}</span> of{' '}
              <span className="font-bold text-ink-primary">{total}</span> proposals
            </div>

            <div className="flex items-center gap-2 self-center sm:self-auto">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1.5 rounded-lg bg-canvas-surface border border-canvas-border font-semibold text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed hover:bg-canvas-elevated transition-colors"
              >
                ← Previous
              </button>
              <span className="px-2 font-mono">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1.5 rounded-lg bg-canvas-surface border border-canvas-border font-semibold text-ink-primary disabled:opacity-40 disabled:cursor-not-allowed hover:bg-canvas-elevated transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Forensic Inspection Modal / Side Drawer */}
      {inspectingProposalId && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-ink-primary/70 backdrop-blur-xs overflow-hidden"
          role="dialog"
          aria-modal="true"
          aria-labelledby="audit-modal-title"
        >
          <div className="flex flex-col w-full h-full sm:h-auto sm:max-h-[92vh] sm:max-w-4xl sm:rounded-2xl bg-canvas-surface border-0 sm:border border-canvas-border shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 sm:px-6 py-4 bg-canvas-elevated border-b border-canvas-border shrink-0">
              <div className="flex items-center gap-2 sm:gap-3 min-w-0">
                <span className="text-xl sm:text-2xl" aria-hidden="true">
                  🛡️
                </span>
                <div className="min-w-0">
                  <h3 id="audit-modal-title" className="font-serif text-base sm:text-lg font-bold text-ink-primary truncate">
                    Forensic Proposal Audit Sheet
                  </h3>
                  <p className="text-[11px] font-mono text-ink-muted truncate">
                    ID: {inspectingProposalId}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  to={`/proposals/${inspectingProposalId}`}
                  target="_blank"
                  rel="noreferrer"
                  className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-canvas-surface border border-canvas-border text-ink-primary hover:text-brass transition-colors"
                >
                  <span>Open Live Contract Sheet</span>
                  <span>↗</span>
                </Link>
                <button
                  type="button"
                  onClick={() => setInspectingProposalId(null)}
                  className="p-1 rounded-lg text-ink-muted hover:text-ink-primary hover:bg-canvas-sunken transition-colors"
                  aria-label="Close forensic inspector"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
              {isDetailLoading || !detailProposal ? (
                <LoadingState message="Fetching cryptographic ledger & audit trails..." />
              ) : (
                <>
                  {/* Status & Headline Banner */}
                  <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <ProposalStatusBadge status={detailProposal.status} size="md" />
                        <span className="text-xs font-mono px-2 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-muted">
                          Revision {detailProposal.current_revision_number} of {detailProposal.revisions.length}
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-ink-secondary">
                        Type: {detailProposal.active_revision.proposal_type.replace(/_/g, ' ')}
                      </span>
                    </div>

                    <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
                      {cleanProposalTitle(detailProposal.active_revision.title)}
                    </h2>
                    <p className="text-xs text-ink-secondary">
                      Commercial Scope:{' '}
                      <strong className="text-ink-primary">
                        {detailProposal.active_revision.product_name} (
                        {formatQuantity(detailProposal.active_revision.quantity)}{' '}
                        {formatUnit(detailProposal.active_revision.unit)})
                      </strong>
                    </p>
                  </div>

                  {/* Dual-Sided Parties Overview */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                    {/* Proposer */}
                    <div className="p-3.5 rounded-xl bg-canvas-surface border border-canvas-border space-y-1 text-xs">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted block">
                        Originator / Proposer
                      </span>
                      <div className="font-bold text-sm text-ink-primary">
                        {detailProposal.proposer.full_name}
                      </div>
                      <div className="text-ink-secondary">
                        {detailProposal.proposer.company_name || 'Independent Enterprise'}
                      </div>
                      <div className="pt-1 flex items-center justify-between text-[11px] text-ink-muted">
                        <span>Role: <strong className="text-ink-primary">{detailProposal.proposer.role}</strong></span>
                        <Link
                          to={`/admin/users/${detailProposal.proposer.user_id}`}
                          className="text-brass hover:underline"
                        >
                          View User Profile →
                        </Link>
                      </div>
                    </div>

                    {/* Recipient */}
                    <div className="p-3.5 rounded-xl bg-canvas-surface border border-canvas-border space-y-1 text-xs">
                      <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted block">
                        Counterparty / Recipient
                      </span>
                      <div className="font-bold text-sm text-ink-primary">
                        {detailProposal.recipient.full_name}
                      </div>
                      <div className="text-ink-secondary">
                        {detailProposal.recipient.company_name || 'Independent Enterprise'}
                      </div>
                      <div className="pt-1 flex items-center justify-between text-[11px] text-ink-muted">
                        <span>Role: <strong className="text-ink-primary">{detailProposal.recipient.role}</strong></span>
                        <Link
                          to={`/admin/users/${detailProposal.recipient.user_id}`}
                          className="text-brass hover:underline"
                        >
                          View User Profile →
                        </Link>
                      </div>
                    </div>
                  </div>

                  {/* Active Commercial Terms Grid */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                      Governing Commercial Terms (Active Revision)
                    </h4>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 p-3.5 rounded-xl bg-canvas-elevated border border-canvas-border text-xs">
                      <div>
                        <span className="block text-[10px] text-ink-muted">Contracted Quantity</span>
                        <span className="font-semibold text-ink-primary">
                          {formatQuantity(detailProposal.active_revision.quantity)}{' '}
                          {formatUnit(detailProposal.active_revision.unit)}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-ink-muted">Unit Consideration</span>
                        <span className="font-semibold text-ink-primary">
                          {detailProposal.active_revision.unit_price != null
                            ? formatCurrencyValue(detailProposal.active_revision.unit_price, detailProposal.active_revision.currency)
                            : 'Negotiated'}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-ink-muted">Total Consideration</span>
                        <span className="font-mono font-bold text-ink-primary">
                          {detailProposal.active_revision.total_value != null
                            ? formatCurrencyValue(detailProposal.active_revision.total_value, detailProposal.active_revision.currency)
                            : 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="block text-[10px] text-ink-muted">Incoterm</span>
                        <span className="font-mono font-bold text-ink-primary">
                          {detailProposal.active_revision.incoterm || 'EXW'}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="block text-[10px] text-ink-muted">Delivery Destination</span>
                        <span className="font-semibold text-ink-primary">
                          {detailProposal.active_revision.delivery_location}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="block text-[10px] text-ink-muted">Payment Terms</span>
                        <span className="font-semibold text-ink-primary">
                          {detailProposal.active_revision.payment_terms}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Non-Repudiable Approval Audit Trail */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted flex items-center justify-between">
                      <span>Non-Repudiable Approval Audit Trail</span>
                      <span className="text-[11px] font-mono text-ink-muted">
                        Total Records: {detailProposal.approvals.length}
                      </span>
                    </h4>
                    {detailProposal.approvals.length === 0 ? (
                      <div className="p-3 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-muted text-center">
                        No formal approval decisions recorded yet.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {detailProposal.approvals.map((app) => (
                          <div
                            key={app.id}
                            className="p-3 rounded-lg bg-canvas-elevated border border-canvas-border flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
                          >
                            <div className="flex items-center gap-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
                                  app.action === 'APPROVED'
                                    ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 border border-emerald-300'
                                    : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-200 border border-rose-300'
                                }`}
                              >
                                {app.action} (Rev {app.revision_number})
                              </span>
                              <span className="font-semibold text-ink-primary">
                                {app.user_name || 'Participant'}
                              </span>
                            </div>

                            <div className="flex items-center gap-3 text-[11px] text-ink-muted">
                              {app.ip_address && (
                                <span className="font-mono bg-canvas-surface px-1.5 py-0.5 rounded border border-canvas-border">
                                  IP: {app.ip_address}
                                </span>
                              )}
                              <span>
                                {new Date(app.created_at).toLocaleString(undefined, {
                                  dateStyle: 'medium',
                                  timeStyle: 'short',
                                })}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Cryptographic Contact Disclosure Receipt */}
                  {detailProposal.disclosed_credentials && (
                    <div className="p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-300 dark:border-emerald-800 space-y-2 text-xs">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-emerald-800 dark:text-emerald-200 flex items-center gap-1.5">
                          <span>🔓</span>
                          <span>Verified Contact Credentials Unlocked</span>
                        </span>
                        <span className="text-[10px] font-mono text-emerald-700 dark:text-emerald-300">
                          Consensus Verified
                        </span>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                        <div>
                          <span className="text-[10px] text-ink-muted block uppercase font-mono">Full Name & Designation</span>
                          <span className="font-semibold text-ink-primary">
                            {detailProposal.disclosed_credentials.full_name}{' '}
                            {detailProposal.disclosed_credentials.designation
                              ? `(${detailProposal.disclosed_credentials.designation})`
                              : ''}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-ink-muted block uppercase font-mono">Company</span>
                          <span className="font-semibold text-ink-primary">
                            {detailProposal.disclosed_credentials.company_name}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-ink-muted block uppercase font-mono">Direct Email</span>
                          <a
                            href={`mailto:${detailProposal.disclosed_credentials.email}`}
                            className="font-mono text-brass hover:underline"
                          >
                            {detailProposal.disclosed_credentials.email}
                          </a>
                        </div>
                        <div>
                          <span className="text-[10px] text-ink-muted block uppercase font-mono">Direct Phone</span>
                          <span className="font-mono text-ink-primary">
                            {detailProposal.disclosed_credentials.phone_number || 'Not provided'}
                          </span>
                        </div>
                        {(detailProposal.disclosed_credentials.verification_receipt_hash ||
                          (detailProposal.disclosed_credentials as any).transaction_receipt_hash) && (
                          <div className="col-span-1 sm:col-span-2 pt-1 border-t border-emerald-200 dark:border-emerald-900/60">
                            <span className="text-[10px] text-ink-muted block uppercase font-mono">
                              Cryptographic SHA-256 Receipt Hash
                            </span>
                            <span className="font-mono text-[10px] text-emerald-900 dark:text-emerald-200 break-all">
                              {detailProposal.disclosed_credentials.verification_receipt_hash ||
                                (detailProposal.disclosed_credentials as any).transaction_receipt_hash}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Revision Ledger History */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
                      Revision Version Ledger ({detailProposal.revisions.length} total)
                    </h4>
                    <div className="divide-y divide-canvas-border rounded-xl bg-canvas-elevated border border-canvas-border overflow-hidden">
                      {detailProposal.revisions.map((rev) => (
                        <div key={rev.id} className="p-3 text-xs space-y-1">
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono font-bold px-1.5 py-0.2 rounded bg-canvas-surface border border-canvas-border text-[10px]">
                                Rev {rev.revision_number}
                              </span>
                              <span className="font-semibold text-ink-primary">
                                {cleanProposalTitle(rev.title)}
                              </span>
                            </div>
                            <span className="text-[10px] text-ink-muted">
                              {new Date(rev.created_at).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 text-[11px] text-ink-secondary">
                            <span>Author: <strong className="text-ink-primary">{rev.author_name}</strong></span>
                            <span>Scope: {rev.product_name} ({formatQuantity(rev.quantity)} {formatUnit(rev.unit)})</span>
                            {rev.total_value && (
                              <span>Value: {formatCurrencyValue(rev.total_value, rev.currency)}</span>
                            )}
                          </div>
                          {rev.revision_summary && (
                            <p className="text-[11px] text-ink-muted italic pt-0.5">
                              Summary: {rev.revision_summary}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="px-4 sm:px-6 py-3 bg-canvas-elevated border-t border-canvas-border flex items-center justify-between shrink-0">
              <span className="text-[11px] text-ink-muted">
                Converge AI • Forensic Audit Governance Engine
              </span>
              <button
                type="button"
                onClick={() => setInspectingProposalId(null)}
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-canvas-surface border border-canvas-border text-ink-primary hover:bg-canvas-sunken transition-colors"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
