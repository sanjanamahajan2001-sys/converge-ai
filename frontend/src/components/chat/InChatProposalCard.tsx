import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ProposalListItem, ProposalDetail } from '@/types/proposal';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import {
  formatQuantity,
  formatUnit,
  formatCurrencyValue,
  cleanProposalTitle,
} from '@/lib/proposalUtils';

interface InChatProposalCardProps {
  proposal: ProposalListItem | ProposalDetail;
  className?: string;
  defaultExpanded?: boolean;
}

export const InChatProposalCard: React.FC<InChatProposalCardProps> = ({
  proposal,
  className = '',
  defaultExpanded,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(() => {
    if (defaultExpanded !== undefined) return defaultExpanded;
    if (typeof window !== 'undefined') {
      return window.innerWidth >= 768;
    }
    return true;
  });

  const isDetail = 'active_revision' in proposal;
  const rawTitle = isDetail ? proposal.active_revision.title : proposal.current_title;
  const title = cleanProposalTitle(rawTitle);
  const productName = isDetail ? proposal.active_revision.product_name : proposal.product_name;
  const rawQty = isDetail ? proposal.active_revision.quantity : proposal.quantity;
  const rawUnit = isDetail ? proposal.active_revision.unit : proposal.unit;
  const quantityFormatted = formatQuantity(rawQty);
  const unitFormatted = formatUnit(rawUnit);
  const totalValue = isDetail ? proposal.active_revision.total_value : proposal.total_value;
  const currency = isDetail ? proposal.active_revision.currency : proposal.currency;
  const formattedTotalValue = formatCurrencyValue(totalValue, currency);
  const revisionNumber = proposal.current_revision_number;

  const isApproved = proposal.status === 'MUTUALLY_APPROVED';
  const isActionRequired = proposal.requires_user_action;

  let borderColor = 'border-canvas-border';
  let bgColor = 'bg-canvas-surface';
  let bannerText = 'Bilateral Commercial Agreement';
  let bannerIcon = '🤝';

  if (isApproved) {
    borderColor = 'border-emerald-500 shadow-xs';
    bgColor = 'bg-emerald-50/60 dark:bg-emerald-950/25';
    bannerText = 'Commercial Consensus Achieved • Contact Credentials Unlocked';
    bannerIcon = '🎉';
  } else if (isActionRequired) {
    borderColor = 'border-amber-400 dark:border-amber-700 shadow-xs ring-1 ring-amber-400/40';
    bgColor = 'bg-amber-50/70 dark:bg-amber-950/30';
    bannerText = 'Action Required: Your review and decision needed';
    bannerIcon = '⚡';
  } else if (proposal.status === 'PENDING_REVIEW' || proposal.status === 'REVISED') {
    borderColor = 'border-sky-300 dark:border-sky-800';
    bgColor = 'bg-sky-50/50 dark:bg-sky-950/20';
    bannerText = 'Awaiting counterparty review & signature';
    bannerIcon = '⏳';
  } else if (proposal.status === 'REJECTED') {
    borderColor = 'border-rose-300 dark:border-rose-800';
    bgColor = 'bg-rose-50/40 dark:bg-rose-950/20';
    bannerText = 'Proposal Declined';
    bannerIcon = '✕';
  } else if (proposal.status === 'WITHDRAWN') {
    borderColor = 'border-slate-300 dark:border-slate-700';
    bgColor = 'bg-slate-50/50 dark:bg-slate-800/30';
    bannerText = 'Proposal Withdrawn by Author';
    bannerIcon = '↩';
  }

  return (
    <div
      className={`rounded-2xl border ${borderColor} ${bgColor} transition-all overflow-hidden ${className}`}
      data-testid="in-chat-proposal-card"
    >
      {/* Top Banner & Status Header (Single instance of bannerText) */}
      <div className="p-3 sm:p-4 flex items-center justify-between gap-2.5 border-b border-canvas-border/60">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-base sm:text-lg shrink-0" aria-hidden="true">
            {bannerIcon}
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[11px] sm:text-xs font-semibold text-ink-primary truncate">
                {bannerText}
              </span>
              <ProposalStatusBadge status={proposal.status} size="sm" />
              <span className="text-[10px] font-mono px-1 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-muted">
                Rev {revisionNumber}
              </span>
            </div>
            {!isExpanded && (
              <Link
                to={`/proposals/${proposal.id}`}
                className="font-serif text-xs font-bold text-ink-primary hover:text-brass transition-colors truncate block mt-0.5"
              >
                {title}
              </Link>
            )}
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {!isExpanded && (
            <Link
              to={`/proposals/${proposal.id}`}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 shadow-2xs whitespace-nowrap ${
                isActionRequired
                  ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-xs'
                  : isApproved
                  ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                  : 'bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border text-ink-primary'
              }`}
            >
              {isActionRequired ? (
                <>
                  <span>⚡</span>
                  <span className="hidden sm:inline">Review & Sign</span>
                  <span className="sm:hidden">Review</span>
                </>
              ) : isApproved ? (
                <>
                  <span>🔓</span>
                  <span>Contacts</span>
                </>
              ) : (
                <span>Review →</span>
              )}
            </Link>
          )}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-lg border border-canvas-border bg-canvas-elevated hover:bg-canvas-sunken text-ink-secondary text-xs flex items-center gap-1"
            aria-label={isExpanded ? 'Collapse proposal details' : 'Expand proposal details'}
            data-testid="proposal-expand-toggle"
          >
            <span className="text-[10px] font-semibold hidden sm:inline">
              {isExpanded ? 'Hide' : 'Details'}
            </span>
            <span className="text-xs">{isExpanded ? '▴' : '▾'}</span>
          </button>
        </div>
      </div>

      {/* Expanded Commercial Specifications Details */}
      {isExpanded && (
        <div className="p-3 sm:p-4 pt-3 space-y-3.5">
          {/* Main Spec Info */}
          <div className="space-y-1">
            <Link
              to={`/proposals/${proposal.id}`}
              className="font-serif text-sm sm:text-base font-bold text-ink-primary hover:text-brass transition-colors block"
            >
              {title}
            </Link>
            <p className="text-xs text-ink-secondary">
              Scope:{' '}
              <strong className="text-ink-primary">
                {productName} ({quantityFormatted} {unitFormatted})
              </strong>
            </p>
          </div>

          {/* Commercial Terms Strip */}
          <div className="p-3 rounded-xl bg-canvas-elevated/80 border border-canvas-border grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
            <div>
              <span className="block text-[10px] text-ink-muted">Contracted Quantity</span>
              <span className="font-semibold text-ink-primary">
                {quantityFormatted} {unitFormatted}
              </span>
            </div>

            {totalValue && (
              <div>
                <span className="block text-[10px] text-ink-muted">Total Consideration</span>
                <span className="font-mono font-bold text-ink-primary">
                  {formattedTotalValue}
                </span>
              </div>
            )}

            <div className="col-span-2 sm:col-span-1">
              <span className="block text-[10px] text-ink-muted">Privacy Gate</span>
              <span
                className={`font-mono text-[11px] font-semibold flex items-center gap-1 ${
                  isApproved
                    ? 'text-emerald-700 dark:text-emerald-300'
                    : 'text-amber-700 dark:text-amber-400'
                }`}
              >
                <span>{isApproved ? '🔓' : '🔒'}</span>
                <span>{isApproved ? 'Credentials Unlocked' : 'Sealed until consensus'}</span>
              </span>
            </div>
          </div>

          {/* Responsive Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-1">
            <span className="text-[11px] text-ink-muted">
              Expires:{' '}
              {new Date(proposal.expires_at).toLocaleDateString(undefined, {
                month: 'short',
                day: 'numeric',
              })}
            </span>

            <div className="flex items-center gap-2">
              <Link
                to={`/proposals/${proposal.id}`}
                className={`w-full sm:w-auto px-4 py-2 rounded-lg text-xs font-semibold transition-colors flex items-center justify-center gap-1.5 shadow-2xs ${
                  isActionRequired
                    ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-xs'
                    : isApproved
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs'
                    : 'bg-canvas-elevated hover:bg-canvas-sunken border border-canvas-border text-ink-primary'
                }`}
              >
                {isActionRequired ? (
                  <>
                    <span>⚡</span>
                    <span>Review & Sign Contract →</span>
                  </>
                ) : isApproved ? (
                  <>
                    <span>🔓</span>
                    <span>View Direct Contact Info →</span>
                  </>
                ) : (
                  <>
                    <span>View Contract Sheet</span>
                    <span>→</span>
                  </>
                )}
              </Link>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
