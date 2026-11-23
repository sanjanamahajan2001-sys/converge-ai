import React, { useState, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { proposalApi } from '@/lib/api/proposal';
import { ProposalListItem } from '@/types/proposal';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import {
  formatQuantity,
  formatUnit,
  formatCurrencyValue,
  cleanProposalTitle,
} from '@/lib/proposalUtils';

export const Proposals: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'all';
  const [searchQuery, setSearchQuery] = useState('');

  const {
    data: proposals = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<ProposalListItem[]>({
    queryKey: ['proposals', currentTab],
    queryFn: () =>
      proposalApi.listProposals(
        currentTab !== 'all' ? { tab: currentTab } : undefined
      ),
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
  });

  const handleTabChange = (tab: string) => {
    if (tab === 'all') {
      setSearchParams({});
    } else {
      setSearchParams({ tab });
    }
  };

  // Metrics across all loaded or filtered items
  const actionRequiredCount = useMemo(
    () => proposals.filter((p) => p.requires_user_action).length,
    [proposals]
  );

  const approvedCount = useMemo(
    () => proposals.filter((p) => p.status === 'MUTUALLY_APPROVED').length,
    [proposals]
  );

  const awaitingCounterpartyCount = useMemo(
    () =>
      proposals.filter(
        (p) =>
          (p.status === 'PENDING_REVIEW' || p.status === 'REVISED') &&
          !p.requires_user_action
      ).length,
    [proposals]
  );

  // Filter proposals by search query
  const filteredProposals = useMemo(() => {
    if (!searchQuery.trim()) return proposals;
    const q = searchQuery.toLowerCase();
    return proposals.filter((p) => {
      const counterpartyName = p.user_is_proposer ? p.recipient_name : p.proposer_name;
      const counterpartyCompany = p.user_is_proposer
        ? p.recipient_company
        : p.proposer_company;
      return (
        p.current_title.toLowerCase().includes(q) ||
        p.product_name.toLowerCase().includes(q) ||
        (counterpartyName && counterpartyName.toLowerCase().includes(q)) ||
        (counterpartyCompany && counterpartyCompany.toLowerCase().includes(q))
      );
    });
  }, [proposals, searchQuery]);

  return (
    <div className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8 space-y-6">
      {/* Header Landmark */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-canvas-border pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl" aria-hidden="true">
              🤝
            </span>
            <h1 className="font-serif text-2xl sm:text-3xl font-bold tracking-tight text-ink-primary">
              Commercial Proposals Hub
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-ink-secondary">
            Bilateral commercial contract drafting, dual-sided consensus tracking, and cryptographically verified contact unlock.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            to="/conversations"
            className="w-full sm:w-auto px-4 py-2 rounded-lg bg-brass text-white text-xs sm:text-sm font-semibold hover:bg-brass/90 transition-colors shadow-xs flex items-center justify-center gap-1.5"
          >
            <span>💬</span>
            <span>Initiate from Messages</span>
          </Link>
        </div>
      </div>

      {/* Metric Strip (Responsive 2x2 on mobile, 4 columns on desktop) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div
          onClick={() => handleTabChange('action_required')}
          className={`p-4 rounded-xl border cursor-pointer transition-all ${
            currentTab === 'action_required'
              ? 'bg-amber-500/10 border-amber-500 ring-1 ring-amber-500/30'
              : 'bg-canvas-surface border-canvas-border hover:border-canvas-border-strong'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-secondary">Action Required</span>
            <span className="text-amber-500 text-sm">⚡</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold font-serif text-amber-600 dark:text-amber-400">
            {actionRequiredCount}
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Requires your review / response</p>
        </div>

        <div
          onClick={() => handleTabChange('all')}
          className={`p-4 rounded-xl border cursor-pointer transition-all ${
            currentTab === 'all'
              ? 'bg-sky-500/10 border-sky-500 ring-1 ring-sky-500/30'
              : 'bg-canvas-surface border-canvas-border hover:border-canvas-border-strong'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-secondary">Awaiting Counterparty</span>
            <span className="text-sky-500 text-sm">⏳</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold font-serif text-sky-600 dark:text-sky-400">
            {awaitingCounterpartyCount}
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Pending peer approval / counter</p>
        </div>

        <div
          onClick={() => handleTabChange('approved')}
          className={`p-4 rounded-xl border cursor-pointer transition-all ${
            currentTab === 'approved'
              ? 'bg-emerald-500/10 border-emerald-500 ring-1 ring-emerald-500/30'
              : 'bg-canvas-surface border-canvas-border hover:border-canvas-border-strong'
          }`}
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-secondary">Mutually Approved</span>
            <span className="text-emerald-500 text-sm">✓</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold font-serif text-emerald-600 dark:text-emerald-400">
            {approvedCount}
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Unlocked contact credentials</p>
        </div>

        <div
          onClick={() => handleTabChange('all')}
          className="p-4 rounded-xl bg-canvas-surface border border-canvas-border hover:border-canvas-border-strong cursor-pointer transition-all"
        >
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-ink-secondary">Total Portfolio</span>
            <span className="text-ink-muted text-sm">📑</span>
          </div>
          <div className="text-2xl sm:text-3xl font-bold font-serif text-ink-primary">
            {proposals.length}
          </div>
          <p className="text-[11px] text-ink-muted mt-1">Total bilateral agreements</p>
        </div>
      </div>

      {/* Segmented Filter Bar & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        {/* Horizontal Scrolling Segmented Tabs on Mobile */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar pb-1 sm:pb-0">
          <button
            type="button"
            onClick={() => handleTabChange('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              currentTab === 'all'
                ? 'bg-ink-primary text-canvas-surface shadow-xs'
                : 'bg-canvas-elevated text-ink-secondary hover:text-ink-primary border border-canvas-border'
            }`}
          >
            All Proposals
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('action_required')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              currentTab === 'action_required'
                ? 'bg-amber-600 text-white shadow-xs'
                : 'bg-canvas-elevated text-ink-secondary hover:text-ink-primary border border-canvas-border'
            }`}
          >
            <span>Action Required</span>
            {actionRequiredCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-500 text-white">
                {actionRequiredCount}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('approved')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors flex items-center gap-1.5 ${
              currentTab === 'approved'
                ? 'bg-emerald-600 text-white shadow-xs'
                : 'bg-canvas-elevated text-ink-secondary hover:text-ink-primary border border-canvas-border'
            }`}
          >
            <span>Mutually Approved</span>
            {approvedCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-emerald-500 text-white">
                {approvedCount}
              </span>
            )}
          </button>
          <button
            type="button"
            onClick={() => handleTabChange('archive')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
              currentTab === 'archive'
                ? 'bg-ink-primary text-canvas-surface shadow-xs'
                : 'bg-canvas-elevated text-ink-secondary hover:text-ink-primary border border-canvas-border'
            }`}
          >
            Archive / Concluded
          </button>
        </div>

        {/* Search Input */}
        <div className="w-full sm:w-64">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search proposals or counterparties..."
            className="w-full px-3 py-1.5 rounded-lg bg-canvas-surface border border-canvas-border text-xs text-ink-primary placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brass"
          />
        </div>
      </div>

      {/* Main Content Area */}
      {isLoading ? (
        <LoadingState message="Loading commercial proposals..." />
      ) : isError ? (
        <EmptyState
          emoji="⚠️"
          title="Error Loading Proposals"
          description={(error as any)?.message || 'Failed to communicate with proposal engine.'}
          action={
            <button
              onClick={() => refetch()}
              className="px-4 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs font-semibold text-ink-primary hover:bg-canvas-sunken"
            >
              Retry
            </button>
          }
        />
      ) : filteredProposals.length === 0 ? (
        <EmptyState
          emoji={currentTab === 'action_required' ? '✨' : currentTab === 'approved' ? '📜' : '📂'}
          title={
            currentTab === 'action_required'
              ? 'No Actions Pending'
              : currentTab === 'approved'
              ? 'No Mutually Approved Contracts Yet'
              : searchQuery
              ? 'No Matching Proposals'
              : 'No Commercial Proposals Found'
          }
          description={
            currentTab === 'action_required'
              ? 'All proposals are currently up-to-date or awaiting your counterparty.'
              : currentTab === 'approved'
              ? 'Once both parties agree to commercial terms, unlocked contact credentials will appear here.'
              : searchQuery
              ? `No proposals match "${searchQuery}". Try clearing search.`
              : 'You can initiate commercial agreements directly from active delegate conversations.'
          }
          action={
            <Link
              to="/conversations"
              className="px-4 py-2 rounded-lg bg-brass text-white text-xs font-semibold hover:bg-brass/90 transition-colors shadow-2xs"
            >
              Go to Messages
            </Link>
          }
        />
      ) : (
        <div className="space-y-4">
          {/* Mobile Card List (< md) */}
          <div className="grid grid-cols-1 gap-3 md:hidden">
            {filteredProposals.map((item) => {
              const counterpartyName = item.user_is_proposer
                ? item.recipient_name
                : item.proposer_name;
              const counterpartyCompany = item.user_is_proposer
                ? item.recipient_company
                : item.proposer_company;
              const counterpartyRole = item.user_is_proposer
                ? item.recipient_role
                : item.proposer_role;

              return (
                <div
                  key={item.id}
                  className={`p-4 rounded-xl border transition-all ${
                    item.requires_user_action
                      ? 'bg-amber-50/40 dark:bg-amber-950/20 border-amber-300 dark:border-amber-800 shadow-sm'
                      : 'bg-canvas-surface border-canvas-border'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <ProposalStatusBadge status={item.status} size="sm" />
                    <span className="text-[10px] font-mono text-ink-muted">
                      Rev {item.current_revision_number}
                    </span>
                  </div>

                  <h3 className="font-serif text-sm font-bold text-ink-primary mb-1">
                    {item.current_title}
                  </h3>

                  <div className="text-xs text-ink-secondary mb-3 flex items-center gap-1.5">
                    <span>With</span>
                    <span className="font-semibold text-ink-primary">{counterpartyName}</span>
                    {counterpartyCompany && (
                      <span className="text-ink-muted">({counterpartyCompany})</span>
                    )}
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-canvas-elevated border border-canvas-border text-ink-muted">
                      {counterpartyRole}
                    </span>
                  </div>

                  {/* Commercial Scope Pills */}
                  <div className="p-2.5 rounded-lg bg-canvas-elevated border border-canvas-border grid grid-cols-2 gap-2 text-xs mb-3">
                    <div>
                      <span className="block text-[10px] text-ink-muted">Product / Scope</span>
                      <span className="font-semibold text-ink-primary truncate block">
                        {item.product_name}
                      </span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-ink-muted">Quantity</span>
                      <span className="font-semibold text-ink-primary">
                        {item.quantity} {item.unit}
                      </span>
                    </div>
                    {item.total_value && (
                      <div className="col-span-2 pt-1 border-t border-canvas-border flex items-center justify-between">
                        <span className="text-[10px] text-ink-muted">Total Value:</span>
                        <span className="font-mono font-bold text-ink-primary">
                          {item.currency}{' '}
                          {item.total_value.toLocaleString(undefined, {
                            maximumFractionDigits: 2,
                          })}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* CTA Action Button */}
                  <Link
                    to={`/proposals/${item.id}`}
                    className={`w-full py-2 px-3 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 ${
                      item.requires_user_action
                        ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-xs'
                        : 'bg-canvas-elevated text-ink-primary hover:bg-canvas-sunken border border-canvas-border'
                    }`}
                  >
                    {item.requires_user_action ? (
                      <>
                        <span>⚡</span>
                        <span>Action Required — Review Contract</span>
                      </>
                    ) : (
                      <>
                        <span>View Contract Sheet</span>
                        <span>→</span>
                      </>
                    )}
                  </Link>
                </div>
              );
            })}
          </div>

          {/* Desktop Table View (>= md) */}
          <div className="hidden md:block overflow-hidden rounded-xl border border-canvas-border bg-canvas-surface shadow-xs">
            <table className="w-full text-left border-collapse" role="table">
              <thead>
                <tr className="bg-canvas-elevated border-b border-canvas-border text-[11px] font-bold uppercase tracking-wider text-ink-muted">
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Proposal / Product</th>
                  <th className="py-3 px-4">Counterparty</th>
                  <th className="py-3 px-4">Scope & Value</th>
                  <th className="py-3 px-4">Expires</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border text-xs">
                {filteredProposals.map((item) => {
                  const counterpartyName = item.user_is_proposer
                    ? item.recipient_name
                    : item.proposer_name;
                  const counterpartyCompany = item.user_is_proposer
                    ? item.recipient_company
                    : item.proposer_company;
                  const counterpartyRole = item.user_is_proposer
                    ? item.recipient_role
                    : item.proposer_role;

                  return (
                    <tr
                      key={item.id}
                      className={`hover:bg-canvas-elevated/50 transition-colors ${
                        item.requires_user_action ? 'bg-amber-50/20 dark:bg-amber-950/10' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1 items-start">
                          <ProposalStatusBadge status={item.status} size="sm" />
                          <span className="text-[10px] font-mono text-ink-muted">
                            Rev {item.current_revision_number}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-serif font-bold text-ink-primary">
                          {cleanProposalTitle(item.current_title)}
                        </div>
                        <div className="text-[11px] text-ink-muted mt-0.5">
                          {item.product_name}
                        </div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-medium text-ink-primary">
                          {counterpartyName}
                        </div>
                        <div className="text-[11px] text-ink-muted flex items-center gap-1.5 mt-0.5">
                          {counterpartyCompany && <span>{counterpartyCompany}</span>}
                          <span className="text-[9px] uppercase font-mono px-1 rounded bg-canvas-elevated border border-canvas-border">
                            {counterpartyRole}
                          </span>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <div className="font-semibold text-ink-primary">
                          {formatQuantity(item.quantity)} {formatUnit(item.unit)}
                        </div>
                        {item.total_value && (
                          <div className="font-mono text-[11px] text-ink-muted mt-0.5">
                            {formatCurrencyValue(item.total_value, item.currency)}
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-4 whitespace-nowrap text-ink-muted text-[11px]">
                        {new Date(item.expires_at).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </td>

                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <Link
                          to={`/proposals/${item.id}`}
                          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                            item.requires_user_action
                              ? 'bg-amber-600 text-white hover:bg-amber-700 shadow-2xs'
                              : 'bg-canvas-elevated text-ink-primary hover:bg-canvas-sunken border border-canvas-border'
                          }`}
                        >
                          {item.requires_user_action ? (
                            <>
                              <span>⚡</span>
                              <span>Review</span>
                            </>
                          ) : (
                            <>
                              <span>Contract</span>
                              <span>→</span>
                            </>
                          )}
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
