import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { proposalApi } from '@/lib/api/proposal';
import { ProposalDetail as ProposalDetailType } from '@/types/proposal';
import { ProposalStatusBadge } from '@/components/proposal/ProposalStatusBadge';
import { ProposalDiffViewer } from '@/components/proposal/ProposalDiffViewer';
import { ProposalDraftModal } from '@/components/proposal/ProposalDraftModal';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import {
  formatQuantity,
  formatUnit,
  formatCurrencyValue,
  cleanProposalTitle,
} from '@/lib/proposalUtils';

export const ProposalDetailRoute: React.FC = () => {
  const { proposalId } = useParams<{ proposalId: string }>();
  const queryClient = useQueryClient();

  // Modals & Action States
  const [isCounterModalOpen, setIsCounterModalOpen] = useState(false);
  const [isApproveDialogOpen, setIsApproveDialogOpen] = useState(false);
  const [approvalNotes, setApprovalNotes] = useState('');
  const [isRejectDialogOpen, setIsRejectDialogOpen] = useState(false);
  const [rejectionReason, setRejectionReason] = useState('');
  const [diffFromRev, setDiffFromRev] = useState<number>(1);
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedPhone, setCopiedPhone] = useState(false);
  const [copiedEmail, setCopiedEmail] = useState(false);

  const {
    data: proposal,
    isLoading,
    isError,
    error,
  } = useQuery<ProposalDetailType>({
    queryKey: ['proposal', proposalId],
    queryFn: () => proposalApi.getProposal(proposalId!),
    enabled: Boolean(proposalId),
    refetchInterval: 4000,
  });

  const hasMultipleRevisions = Boolean(
    proposal?.revisions && proposal.revisions.length > 1
  );

  const { data: diffData, isLoading: isDiffLoading } = useQuery({
    queryKey: ['proposal-diff', proposalId, diffFromRev, proposal?.current_revision_number],
    queryFn: () =>
      proposalApi.getProposalRevisionDiff(
        proposalId!,
        diffFromRev,
        proposal?.current_revision_number
      ),
    enabled: Boolean(proposalId && hasMultipleRevisions),
  });

  // Approval Mutation
  const approveMutation = useMutation({
    mutationFn: (notes?: string) =>
      proposalApi.approveProposal(proposalId!, { notes: notes || undefined }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['proposal', proposalId], updated);
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
      setIsApproveDialogOpen(false);
      setApprovalNotes('');
    },
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: (reason: string) =>
      proposalApi.rejectProposal(proposalId!, { reason }),
    onSuccess: (updated) => {
      queryClient.setQueryData(['proposal', proposalId], updated);
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
      setIsRejectDialogOpen(false);
      setRejectionReason('');
    },
  });

  // Withdraw Mutation
  const withdrawMutation = useMutation({
    mutationFn: () => proposalApi.withdrawProposal(proposalId!),
    onSuccess: (updated) => {
      queryClient.setQueryData(['proposal', proposalId], updated);
      queryClient.invalidateQueries({ queryKey: ['proposals'] });
    },
  });

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <LoadingState message="Loading commercial contract sheet..." />
      </div>
    );
  }

  if (isError || !proposal) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <EmptyState
          emoji="⚠️"
          title="Proposal Not Found"
          description={(error as any)?.message || 'Unable to retrieve agreement record.'}
          action={
            <Link
              to="/proposals"
              className="px-4 py-2 rounded-lg bg-brass text-white text-xs font-semibold"
            >
              Back to Proposals Hub
            </Link>
          }
        />
      </div>
    );
  }

  const activeRev = proposal.active_revision;
  const isMutuallyApproved = proposal.status === 'MUTUALLY_APPROVED';

  // Check if each party has approved the active revision
  const proposerApproved = proposal.approvals.some(
    (a) =>
      a.user_id === proposal.proposer.user_id &&
      a.revision_number === proposal.current_revision_number &&
      a.action === 'APPROVED'
  );

  const recipientApproved = proposal.approvals.some(
    (a) =>
      a.user_id === proposal.recipient.user_id &&
      a.revision_number === proposal.current_revision_number &&
      a.action === 'APPROVED'
  );

  const handleCopy = (text: string, setCopied: (v: boolean) => void) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8 space-y-6 pb-24 lg:pb-8">
      {/* Top Navigation & Breadcrumb */}
      <div className="flex items-center justify-between gap-3 text-xs text-ink-muted">
        <Link
          to="/proposals"
          className="hover:text-ink-primary flex items-center gap-1.5 transition-colors font-medium"
        >
          <span>←</span>
          <span>Back to Proposals Hub</span>
        </Link>
        {proposal.conversation_id && (
          <Link
            to={`/conversations/${proposal.conversation_id}`}
            className="text-brass hover:underline flex items-center gap-1 font-medium"
          >
            <span>💬</span>
            <span>View Dialogue Context</span>
          </Link>
        )}
      </div>

      {/* Main Contract Header & Desktop Actions */}
      <div className="p-5 sm:p-6 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <ProposalStatusBadge status={proposal.status} size="md" />
            <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-secondary">
              Revision {proposal.current_revision_number} of {proposal.revisions.length}
            </span>
            <span className="text-xs font-mono text-ink-muted px-2 py-0.5 rounded bg-canvas-elevated">
              {activeRev.proposal_type.replace(/_/g, ' ')}
            </span>
          </div>

          <h1 className="font-serif text-xl sm:text-2xl lg:text-3xl font-bold tracking-tight text-ink-primary">
            {cleanProposalTitle(activeRev.title)}
          </h1>

          <p className="text-xs text-ink-secondary flex flex-wrap items-center gap-2">
            <span>Product: <strong className="text-ink-primary">{activeRev.product_name}</strong></span>
            <span>•</span>
            <span>
              Expires:{' '}
              <strong className="text-ink-primary">
                {new Date(proposal.expires_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </strong>
            </span>
          </p>
        </div>

        {/* Desktop Header Action Buttons */}
        <div className="hidden lg:flex items-center gap-2.5 shrink-0">
          {proposal.requires_user_action && (
            <>
              <button
                type="button"
                onClick={() => setIsRejectDialogOpen(true)}
                className="px-4 py-2 rounded-lg border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              >
                ✕ Decline
              </button>
              <button
                type="button"
                onClick={() => setIsCounterModalOpen(true)}
                className="px-4 py-2 rounded-lg border border-sky-300 dark:border-sky-800 text-sky-700 dark:text-sky-300 text-xs font-semibold hover:bg-sky-50 dark:hover:bg-sky-950/30 transition-colors flex items-center gap-1.5"
              >
                <span>🔄</span>
                <span>Counter-Offer</span>
              </button>
              <button
                type="button"
                onClick={() => setIsApproveDialogOpen(true)}
                className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition-colors shadow-2xs flex items-center gap-1.5"
              >
                <span>✓</span>
                <span>Accept & Approve</span>
              </button>
            </>
          )}

          {proposal.user_is_proposer &&
            proposal.status === 'PENDING_REVIEW' &&
            !proposal.requires_user_action && (
              <button
                type="button"
                onClick={() => withdrawMutation.mutate()}
                disabled={withdrawMutation.isPending}
                className="px-4 py-2 rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 text-xs font-semibold hover:bg-canvas-elevated transition-colors"
              >
                {withdrawMutation.isPending ? 'Withdrawing...' : 'Withdraw Proposal'}
              </button>
            )}
        </div>
      </div>

      {/* Dual-Sided Consensus Bar (Visual Progress Tracker) */}
      <div className="p-5 sm:p-6 rounded-2xl bg-canvas-elevated border border-canvas-border space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted flex items-center gap-1.5">
            <span>⚖️</span>
            <span>Dual-Sided Commercial Consensus Tracker</span>
          </h3>
          <span className="text-[11px] font-mono text-ink-muted">
            {isMutuallyApproved ? 'Consensus Achieved' : 'Pending Bilateral Agreement'}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative">
          {/* Proposer Party Card */}
          <div
            className={`p-4 rounded-xl border transition-all ${
              proposerApproved
                ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-800'
                : 'bg-canvas-surface border-canvas-border'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted">
                Originator / Proposer
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                  proposerApproved
                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                    : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                }`}
              >
                {proposerApproved ? '✓ Approved Rev ' + proposal.current_revision_number : '⏳ Awaiting'}
              </span>
            </div>
            <div className="font-serif font-bold text-ink-primary text-sm sm:text-base">
              {proposal.proposer.full_name}
            </div>
            <div className="text-xs text-ink-secondary mt-0.5">
              {proposal.proposer.company_name || 'Independent Delegate'}
              {proposal.proposer.designation && ` • ${proposal.proposer.designation}`}
            </div>
            <div className="mt-2 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-muted inline-block">
              Role: {proposal.proposer.role}
            </div>
          </div>

          {/* Recipient Party Card */}
          <div
            className={`p-4 rounded-xl border transition-all ${
              recipientApproved
                ? 'bg-emerald-50/50 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-800'
                : 'bg-canvas-surface border-canvas-border'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-muted">
                Counterparty / Recipient
              </span>
              <span
                className={`text-xs font-semibold px-2 py-0.5 rounded-full flex items-center gap-1 ${
                  recipientApproved
                    ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300'
                    : 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                }`}
              >
                {recipientApproved ? '✓ Approved Rev ' + proposal.current_revision_number : '⏳ Awaiting'}
              </span>
            </div>
            <div className="font-serif font-bold text-ink-primary text-sm sm:text-base">
              {proposal.recipient.full_name}
            </div>
            <div className="text-xs text-ink-secondary mt-0.5">
              {proposal.recipient.company_name || 'Independent Delegate'}
              {proposal.recipient.designation && ` • ${proposal.recipient.designation}`}
            </div>
            <div className="mt-2 text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border text-ink-muted inline-block">
              Role: {proposal.recipient.role}
            </div>
          </div>
        </div>

        {/* Security / Leakage Invariant Guarantee Banner */}
        <div className="text-xs rounded-xl p-3 bg-canvas-surface border border-canvas-border flex items-center gap-2.5">
          <span className="text-lg">{isMutuallyApproved ? '🔓' : '🔒'}</span>
          <span className="text-ink-secondary leading-relaxed">
            {isMutuallyApproved ? (
              <strong className="text-emerald-700 dark:text-emerald-300">
                Mutual commercial consent verified. Direct contact coordinates, corporate credentials, and cryptographic audit receipts are unlocked below.
              </strong>
            ) : (
              <span>
                Zero Contact Leakage Enforcement: Direct email and phone coordinates remain cryptographically sealed until both delegates sign off on the active terms.
              </span>
            )}
          </span>
        </div>
      </div>

      {/* Unlocked Contact Credentials Card (Displayed Only If Mutually Approved) */}
      {isMutuallyApproved && proposal.disclosed_credentials && (
        <div className="p-5 sm:p-6 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/20 border-2 border-emerald-500 shadow-md space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-emerald-200 dark:border-emerald-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="text-xl">🔓</span>
              <div>
                <h3 className="font-serif text-base sm:text-lg font-bold text-emerald-900 dark:text-emerald-200">
                  Verified Counterparty Contact Credentials
                </h3>
                <p className="text-xs text-emerald-700 dark:text-emerald-400">
                  Unlocked upon mutual agreement on {new Date(proposal.disclosed_credentials.disclosed_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-1 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-200 border border-emerald-300 dark:border-emerald-700 font-semibold self-start sm:self-auto">
              ✓ Cryptographically Verified
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
            {/* Phone */}
            <div className="p-3.5 rounded-xl bg-canvas-surface border border-emerald-200 dark:border-emerald-800">
              <span className="block text-[10px] uppercase font-mono text-ink-muted mb-1">
                Direct Phone / WhatsApp
              </span>
              <div className="flex items-center justify-between gap-2">
                <a
                  href={`tel:${proposal.disclosed_credentials.phone_number}`}
                  className="font-mono text-sm font-bold text-ink-primary hover:text-emerald-600 transition-colors"
                >
                  {proposal.disclosed_credentials.phone_number}
                </a>
                <button
                  type="button"
                  onClick={() =>
                    handleCopy(proposal.disclosed_credentials!.phone_number, setCopiedPhone)
                  }
                  className="text-[11px] text-ink-muted hover:text-ink-primary px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border"
                >
                  {copiedPhone ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* Email */}
            <div className="p-3.5 rounded-xl bg-canvas-surface border border-emerald-200 dark:border-emerald-800">
              <span className="block text-[10px] uppercase font-mono text-ink-muted mb-1">
                Corporate Email
              </span>
              <div className="flex items-center justify-between gap-2">
                <a
                  href={`mailto:${proposal.disclosed_credentials.email}`}
                  className="font-mono text-sm font-bold text-ink-primary hover:text-emerald-600 transition-colors truncate"
                >
                  {proposal.disclosed_credentials.email}
                </a>
                <button
                  type="button"
                  onClick={() =>
                    handleCopy(proposal.disclosed_credentials!.email, setCopiedEmail)
                  }
                  className="text-[11px] text-ink-muted hover:text-ink-primary px-1.5 py-0.5 rounded bg-canvas-elevated border border-canvas-border"
                >
                  {copiedEmail ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </div>

            {/* Entity & Tax ID */}
            <div className="p-3.5 rounded-xl bg-canvas-surface border border-emerald-200 dark:border-emerald-800">
              <span className="block text-[10px] uppercase font-mono text-ink-muted mb-1">
                Registration / Tax ID
              </span>
              <div className="font-mono text-sm font-bold text-ink-primary">
                {proposal.disclosed_credentials.tax_id_or_registration || 'Verified Business Entity'}
              </div>
              <div className="text-[11px] text-ink-muted mt-0.5">
                HQ: {proposal.disclosed_credentials.hq_city || 'Registered Jurisdiction'}
              </div>
            </div>
          </div>

          {/* Cryptographic SHA-256 Receipt */}
          {proposal.disclosed_credentials.verification_receipt_hash && (
            <div className="p-3 rounded-xl bg-canvas-surface border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-mono text-[10px] uppercase font-bold text-ink-muted">
                  Receipt Hash:
                </span>
                <span className="font-mono text-[11px] text-emerald-800 dark:text-emerald-300 break-all">
                  {proposal.disclosed_credentials.verification_receipt_hash}
                </span>
              </div>
              <button
                type="button"
                onClick={() =>
                  handleCopy(
                    proposal.disclosed_credentials!.verification_receipt_hash!,
                    setCopiedHash
                  )
                }
                className="self-end sm:self-auto text-[11px] px-2 py-1 rounded bg-canvas-elevated border border-canvas-border text-ink-secondary hover:text-ink-primary shrink-0"
              >
                {copiedHash ? '✓ Copied' : 'Copy Hash'}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Official Commercial Contract Sheet */}
      <div className="p-5 sm:p-7 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs space-y-6">
        <div className="border-b border-canvas-border pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="font-serif text-lg sm:text-xl font-bold text-ink-primary">
              Commercial Contract Specification
            </h2>
            <p className="text-xs text-ink-muted">
              Governing commercial terms for Revision {proposal.current_revision_number}
            </p>
          </div>
          {activeRev.revision_summary && (
            <div className="px-3 py-1.5 rounded-lg bg-sky-50 dark:bg-sky-950/30 border border-sky-300 dark:border-sky-800 text-xs text-sky-800 dark:text-sky-300">
              <span className="font-bold">
                {proposal.current_revision_number > 1 ? 'Counter Summary:' : 'Proposal Summary:'}
              </span>{' '}
              {activeRev.revision_summary}
            </div>
          )}
        </div>

        {/* Section 1: Scope & Pricing */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
            1. Goods, Services & Commercial Consideration
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 p-4 rounded-xl bg-canvas-elevated border border-canvas-border text-xs">
            <div>
              <span className="block text-[10px] text-ink-muted">Product / Material</span>
              <span className="font-bold text-ink-primary text-sm sm:text-base">
                {activeRev.product_name}
              </span>
              {activeRev.product_code && (
                <span className="block text-[10px] font-mono text-ink-muted">
                  SKU: {activeRev.product_code}
                </span>
              )}
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Contracted Quantity</span>
              <span className="font-bold text-ink-primary text-sm sm:text-base">
                {formatQuantity(activeRev.quantity)} {formatUnit(activeRev.unit)}
              </span>
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Unit Consideration</span>
              <span className="font-bold text-ink-primary text-sm sm:text-base">
                {activeRev.unit_price != null
                  ? formatCurrencyValue(activeRev.unit_price, activeRev.currency)
                  : 'Negotiated / Market'}
              </span>
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Total Contract Value</span>
              <span className="font-mono font-bold text-ink-primary text-sm sm:text-base">
                {activeRev.total_value != null
                  ? formatCurrencyValue(activeRev.total_value, activeRev.currency)
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Section 2: Fulfillment & Logistics */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
            2. Logistics, Incoterms & Payment Settlement
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 p-4 rounded-xl bg-canvas-elevated border border-canvas-border text-xs">
            <div>
              <span className="block text-[10px] text-ink-muted">Delivery Location / Port</span>
              <span className="font-semibold text-ink-primary">{activeRev.delivery_location}</span>
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Incoterm Classification</span>
              <span className="font-mono font-bold text-ink-primary">
                {activeRev.incoterm || 'FOB / Destination'}
              </span>
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Delivery Timeline</span>
              <span className="font-semibold text-ink-primary">
                {activeRev.delivery_timeline_days} Calendar Days
              </span>
            </div>

            <div>
              <span className="block text-[10px] text-ink-muted">Payment Terms</span>
              <span className="font-semibold text-ink-primary">{activeRev.payment_terms}</span>
            </div>
          </div>
        </div>

        {/* Section 3: Standards & Caveats */}
        <div className="space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
            3. Governing Standards, Covenants & Notes
          </h3>
          <div className="p-4 rounded-xl bg-canvas-elevated border border-canvas-border space-y-3 text-xs">
            {activeRev.governing_standards && activeRev.governing_standards.length > 0 && (
              <div>
                <span className="block text-[10px] text-ink-muted mb-1">
                  Compliance & Quality Standards
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {activeRev.governing_standards.map((std, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-canvas-surface border border-canvas-border text-ink-primary font-mono text-[11px]"
                    >
                      {std}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {activeRev.special_conditions && (
              <div>
                <span className="block text-[10px] text-ink-muted mb-0.5">Special Conditions</span>
                <p className="text-ink-secondary bg-canvas-surface p-2.5 rounded-lg border border-canvas-border">
                  {activeRev.special_conditions}
                </p>
              </div>
            )}

            {activeRev.notes && (
              <div>
                <span className="block text-[10px] text-ink-muted mb-0.5">Contract Caveats & Notes</span>
                <p className="text-ink-secondary bg-canvas-surface p-2.5 rounded-lg border border-canvas-border">
                  {activeRev.notes}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Revision Diff & History Section */}
      {hasMultipleRevisions && (
        <div className="p-5 sm:p-7 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-canvas-border pb-3">
            <div>
              <h3 className="font-serif text-base sm:text-lg font-bold text-ink-primary">
                Commercial Revision Comparison
              </h3>
              <p className="text-xs text-ink-muted">
                Compare parameter adjustments across negotiation rounds
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-ink-muted">Compare Baseline:</span>
              <select
                value={diffFromRev}
                onChange={(e) => setDiffFromRev(Number(e.target.value))}
                className="px-2.5 py-1 rounded-lg bg-canvas-elevated border border-canvas-border text-ink-primary font-semibold"
              >
                {proposal.revisions
                  .filter((r) => r.revision_number < proposal.current_revision_number)
                  .map((r) => (
                    <option key={r.revision_number} value={r.revision_number}>
                      Revision {r.revision_number}
                    </option>
                  ))}
              </select>
              <span className="text-ink-muted">against Active (Rev {proposal.current_revision_number})</span>
            </div>
          </div>

          <ProposalDiffViewer
            diff={diffData || null}
            isLoading={isDiffLoading}
          />
        </div>
      )}

      {/* Audit Trail & Action History */}
      <div className="p-5 sm:p-6 rounded-2xl bg-canvas-surface border border-canvas-border space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-ink-muted">
          Consensus & Revision Timeline
        </h3>
        <div className="space-y-2 text-xs">
          {proposal.revisions.map((rev) => (
            <div
              key={rev.id}
              className="p-3 rounded-lg bg-canvas-elevated border border-canvas-border flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div>
                <span className="font-bold text-ink-primary">
                  Revision {rev.revision_number}
                </span>{' '}
                <span className="text-ink-muted">
                  created by {rev.author_name || 'Author'}
                </span>
                {rev.revision_summary && (
                  <p className="text-[11px] text-ink-secondary mt-0.5">
                    "{rev.revision_summary}"
                  </p>
                )}
              </div>
              <span className="text-[11px] font-mono text-ink-muted">
                {new Date(rev.created_at).toLocaleString()}
              </span>
            </div>
          ))}

          {proposal.approvals.map((appr) => (
            <div
              key={appr.id}
              className="p-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div>
                <span className="font-bold text-emerald-700 dark:text-emerald-300">
                  ✓ {appr.action}
                </span>{' '}
                <span className="text-ink-secondary">
                  for Revision {appr.revision_number} by {appr.user_name || 'Delegate'}
                </span>
                {appr.notes && (
                  <p className="text-[11px] text-ink-muted mt-0.5">Note: "{appr.notes}"</p>
                )}
              </div>
              <span className="text-[11px] font-mono text-ink-muted">
                {new Date(appr.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile Sticky Thumb Action Bar (< lg) */}
      {proposal.requires_user_action && (
        <div className="fixed bottom-0 inset-x-0 z-40 bg-canvas-surface/95 backdrop-blur-md border-t border-canvas-border p-3 flex gap-2 lg:hidden shadow-lg">
          <button
            type="button"
            onClick={() => setIsRejectDialogOpen(true)}
            className="flex-1 py-2.5 rounded-xl border border-rose-300 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold hover:bg-rose-50"
          >
            ✕ Decline
          </button>
          <button
            type="button"
            onClick={() => setIsCounterModalOpen(true)}
            className="flex-1 py-2.5 rounded-xl border border-sky-300 dark:border-sky-800 text-sky-700 dark:text-sky-300 text-xs font-semibold hover:bg-sky-50"
          >
            🔄 Counter
          </button>
          <button
            type="button"
            onClick={() => setIsApproveDialogOpen(true)}
            className="flex-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md"
          >
            ✓ Accept & Sign
          </button>
        </div>
      )}

      {/* Counter-Proposal Modal */}
      {isCounterModalOpen && (
        <ProposalDraftModal
          isOpen={isCounterModalOpen}
          onClose={() => setIsCounterModalOpen(false)}
          mode="counter_proposal"
          proposalId={proposal.id}
          baseRevision={activeRev}
          onSuccess={(updated) => {
            queryClient.setQueryData(['proposal', proposal.id], updated);
            queryClient.invalidateQueries({ queryKey: ['proposals'] });
          }}
        />
      )}

      {/* Approve Confirmation Modal */}
      {isApproveDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/70 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-2xl bg-canvas-surface border border-canvas-border p-5 space-y-4 shadow-xl">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl">✓</span>
              <div>
                <h3 className="font-serif text-base font-bold text-ink-primary">
                  Sign & Accept Commercial Proposal
                </h3>
                <p className="text-xs text-ink-secondary">
                  Revision {proposal.current_revision_number}: {activeRev.product_name}
                </p>
              </div>
            </div>

            <p className="text-xs text-ink-secondary leading-relaxed">
              By confirming, you commit your non-repudiable approval to this contract revision. Once both parties approve, verified contact coordinates will be immediately unlocked.
            </p>

            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Optional Approval Note / Comments
              </label>
              <input
                type="text"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="e.g. Terms agreed, looking forward to fulfillment"
                className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-brass"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsApproveDialogOpen(false)}
                className="px-3 py-1.5 rounded-lg border border-canvas-border text-xs font-semibold text-ink-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => approveMutation.mutate(approvalNotes)}
                disabled={approveMutation.isPending}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-2xs flex items-center gap-1.5"
              >
                {approveMutation.isPending ? 'Signing...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reject Confirmation Modal */}
      {isRejectDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-primary/70 backdrop-blur-xs"
          role="dialog"
          aria-modal="true"
        >
          <div className="w-full max-w-md rounded-2xl bg-canvas-surface border border-canvas-border p-5 space-y-4 shadow-xl">
            <div className="flex items-center gap-2.5">
              <span className="text-2xl text-rose-500">✕</span>
              <div>
                <h3 className="font-serif text-base font-bold text-ink-primary">
                  Decline Proposal
                </h3>
                <p className="text-xs text-ink-secondary">
                  Please provide a reason for declining this commercial proposal.
                </p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-ink-secondary mb-1">
                Mandatory Reason <span className="text-crimson">*</span>
              </label>
              <textarea
                rows={3}
                required
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
                placeholder="e.g. Unit pricing exceeds our quarterly procurement budget."
                className="w-full px-3 py-2 rounded-lg bg-canvas-elevated border border-canvas-border text-xs text-ink-primary focus:outline-none focus:ring-1 focus:ring-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setIsRejectDialogOpen(false)}
                className="px-3 py-1.5 rounded-lg border border-canvas-border text-xs font-semibold text-ink-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => rejectMutation.mutate(rejectionReason)}
                disabled={!rejectionReason.trim() || rejectMutation.isPending}
                className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold shadow-2xs flex items-center gap-1.5 disabled:opacity-50"
              >
                {rejectMutation.isPending ? 'Declining...' : 'Confirm Decline'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
