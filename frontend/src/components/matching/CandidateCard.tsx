import { useQueryClient, useQuery } from '@tanstack/react-query';
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { CandidateMatchResponse } from '@/types/matching';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { conversationApi } from '@/lib/api/conversation';
import { brochureApi } from '@/lib/api/brochures';
import { ApiClientError } from '@/lib/api/client';

interface CandidateCardProps {
  candidate: CandidateMatchResponse;
  isSelected?: boolean;
  onToggleSelect?: (candidateId: string) => void;
  isSelectable?: boolean;
  disabledSelect?: boolean;
}

export const CandidateCard: React.FC<CandidateCardProps> = ({
  candidate,
  isSelected = false,
  onToggleSelect,
  isSelectable = false,
  disabledSelect = false,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [isStarting, setIsStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const { data: brochuresDirectory = [] } = useQuery({
    queryKey: ['brochuresDirectory'],
    queryFn: () => brochureApi.getDirectory(),
    staleTime: 60000,
  });

  const candidateBrochure = brochuresDirectory.find(
    (b) =>
      candidate.company_name &&
      b.company_name.toLowerCase() === candidate.company_name.toLowerCase()
  );

  const handleStartConversation = async () => {
    setIsStarting(true);
    setStartError(null);
    try {
      const conv = await conversationApi.initiateConversation(candidate.candidate_id);
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      navigate(`/conversations/${conv.id}`);
    } catch (err) {
      if (err instanceof ApiClientError) {
        if (err.status === 409) {
          navigate('/conversations');
          return;
        }
        setStartError(err.detail);
      } else {
        setStartError('Could not connect. Please try again.');
      }
      setIsStarting(false);
    }
  };

  // Availability badge mapping
  const availMap: Record<string, { label: string; emoji: string; variant: StatusVariant }> = {
    AVAILABLE: { label: 'Available', emoji: '🟢', variant: 'success' },
    IN_SESSION: { label: 'In Session', emoji: '🟡', variant: 'warning' },
    DO_NOT_DISTURB: { label: 'Do Not Disturb', emoji: '🔴', variant: 'danger' },
    OFFLINE: { label: 'Offline', emoji: '⚪', variant: 'neutral' },
  };
  const availInfo = availMap[candidate.availability] || {
    label: candidate.availability,
    emoji: '⚪',
    variant: 'neutral' as StatusVariant,
  };

  const scorePercent = Math.round(candidate.composite_score * 100);

  return (
    <article
      className={`bg-canvas-surface border rounded-lg p-4 sm:p-6 shadow-sm/30 transition-all flex flex-col justify-between ${
        isSelected
          ? 'border-brass ring-2 ring-brass/40 bg-amber-50/20 dark:bg-amber-950/20 shadow-md'
          : 'border-canvas-border hover:border-canvas-border-strong'
      }`}
      aria-labelledby={`candidate-title-${candidate.candidate_id}`}
    >
      <div className="space-y-4">
        {/* Top Header: Candidate Identity & Score Pill */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-canvas-border pb-3">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            {isSelectable && (
              <label
                className="mt-0.5 inline-flex items-center cursor-pointer p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition shrink-0"
                title={isSelected ? 'Remove from Circle selection' : 'Select for Thematic Circle'}
              >
                <input
                  type="checkbox"
                  checked={!!isSelected}
                  disabled={disabledSelect && !isSelected}
                  onChange={() => onToggleSelect?.(candidate.candidate_id)}
                  className="rounded text-brass focus:ring-brass h-4 w-4 cursor-pointer disabled:opacity-40"
                  aria-label={`Select ${candidate.full_name} for circle`}
                />
              </label>
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h3
                  id={`candidate-title-${candidate.candidate_id}`}
                  className="font-serif text-base sm:text-lg font-bold text-ink-primary truncate"
                >
                  {candidate.full_name}
                </h3>
                <StatusBadge
                  emoji={availInfo.emoji}
                  label={availInfo.label}
                  variant={availInfo.variant}
                />
              </div>
            {(candidate.job_title || candidate.company_name) && (
              <div className="flex items-center gap-x-2 gap-y-1 mt-0.5 flex-wrap">
                <div className="text-xs text-ink-muted flex items-center gap-1.5 flex-wrap">
                  {candidate.job_title && (
                    <span className="font-medium text-ink-secondary">{candidate.job_title}</span>
                  )}
                  {candidate.job_title && candidate.company_name && (
                    <span className="text-ink-muted/50 select-none" aria-hidden="true">·</span>
                  )}
                  {candidate.company_name && (
                    <span className="font-semibold text-ink-primary break-words">
                      {candidate.company_name}
                    </span>
                  )}
                </div>
                {candidateBrochure && (
                  <Link
                    to={`/brochures/${candidateBrochure.slug}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors shrink-0"
                    title={`View ${candidateBrochure.title} (Digital Flipbook)`}
                  >
                    <span>📖</span>
                    <span>Brochure ↗</span>
                  </Link>
                )}
              </div>
            )}
            <div className="mt-1 flex items-center gap-2 text-[11px] text-ink-secondary">
              <span className="font-mono text-[10px] uppercase tracking-wider text-ink-muted">
                Intent:
              </span>
              <span>
                {candidate.intent === 'NETWORKING' && '🤝 Professional Networking'}
                {candidate.intent === 'CASUAL' && '☕ Casual Discussions'}
                {candidate.intent === 'BOTH' && '🌟 Both Networking & Casual'}
              </span>
            </div>
          </div>
        </div>

          {/* Compatibility Score Display */}
          <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-1 bg-canvas-elevated sm:bg-transparent p-2.5 sm:p-0 rounded-md sm:rounded-none border sm:border-0 border-canvas-border">
            <div className="text-left sm:text-right">
              <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted block">
                Compatibility
              </span>
              <div className="flex items-baseline gap-1">
                <span className="font-serif text-xl sm:text-2xl font-bold text-brass leading-none">
                  {scorePercent}%
                </span>
                <span className="text-[11px] text-ink-muted">match</span>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setShowBreakdown(!showBreakdown)}
              className="text-[11px] font-semibold text-brass hover:text-brass-hover transition-colors underline underline-offset-2 focus:outline-none focus:ring-1 focus:ring-brass rounded px-1"
              aria-expanded={showBreakdown}
              aria-controls={`breakdown-${candidate.candidate_id}`}
            >
              {showBreakdown ? 'Hide Breakdown' : 'Explain Score'}
            </button>
          </div>
        </div>

        {/* Explainability Rationale */}
        {candidate.match_reasons && candidate.match_reasons.length > 0 && (
          <div className="bg-canvas-elevated/70 rounded-md p-3 border border-canvas-border text-xs text-ink-secondary space-y-1">
            <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted block font-semibold">
              Compatibility Highlights
            </span>
            <ul className="list-disc list-inside space-y-0.5 text-ink-primary">
              {candidate.match_reasons.map((reason, idx) => (
                <li key={idx} className="leading-snug">
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Overlapping Common Interests */}
        <div className="space-y-2 text-xs">
          {candidate.common_topics && candidate.common_topics.length > 0 && (
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted block mb-1">
                Shared Technical Topics ({candidate.common_topics.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {candidate.common_topics.map((topic) => (
                  <span
                    key={topic}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-canvas-elevated border border-canvas-border text-ink-primary"
                  >
                    <span aria-hidden="true">🏷️</span>
                    <span>{topic}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {candidate.common_hobbies && candidate.common_hobbies.length > 0 && (
            <div>
              <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted block mb-1">
                Shared Interests ({candidate.common_hobbies.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {candidate.common_hobbies.map((hobby) => (
                  <span
                    key={hobby}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-canvas-elevated border border-canvas-border text-ink-secondary"
                  >
                    <span aria-hidden="true">☕</span>
                    <span>{hobby}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {candidate.common_sessions_count > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-ink-secondary pt-1">
              <span aria-hidden="true">📅</span>
              <span className="font-medium text-ink-primary">
                {candidate.common_sessions_count} Mutually Bookmarked Session
                {candidate.common_sessions_count > 1 ? 's' : ''}
              </span>
            </div>
          )}
        </div>

        {/* Bio Summary (if present) */}
        {candidate.bio_summary && (
          <p className="text-xs text-ink-secondary line-clamp-2 italic pt-1 border-t border-canvas-border/50">
            "{candidate.bio_summary}"
          </p>
        )}

        {/* Expandable 4-Factor Score Breakdown */}
        {showBreakdown && (
          <div
            id={`breakdown-${candidate.candidate_id}`}
            className="pt-3 border-t border-canvas-border space-y-2.5 animate-in fade-in duration-150"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase font-mono tracking-wider text-ink-muted font-bold">
                Deterministic 4-Factor Breakdown
              </span>
              <span className="text-[10px] font-mono text-ink-muted">TST-007 Model</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
              {/* Intent */}
              <div className="bg-canvas-elevated p-2 rounded border border-canvas-border">
                <span className="text-[10px] uppercase font-mono text-ink-muted block">Intent</span>
                <span className="font-bold text-ink-primary block">
                  {Math.round(candidate.score_breakdown.intent.raw_similarity * 100)}%
                </span>
                <span className="text-[9px] text-ink-muted font-mono">
                  Weight: {Math.round(candidate.score_breakdown.intent.effective_weight * 100)}%
                </span>
              </div>

              {/* Topics */}
              <div className="bg-canvas-elevated p-2 rounded border border-canvas-border">
                <span className="text-[10px] uppercase font-mono text-ink-muted block">Topics</span>
                <span className="font-bold text-ink-primary block">
                  {candidate.score_breakdown.topics.is_active
                    ? `${Math.round(candidate.score_breakdown.topics.raw_similarity * 100)}%`
                    : 'N/A'}
                </span>
                <span className="text-[9px] text-ink-muted font-mono">
                  {candidate.score_breakdown.topics.is_active
                    ? `Weight: ${Math.round(candidate.score_breakdown.topics.effective_weight * 100)}%`
                    : 'Redistributed'}
                </span>
              </div>

              {/* Agenda */}
              <div className="bg-canvas-elevated p-2 rounded border border-canvas-border">
                <span className="text-[10px] uppercase font-mono text-ink-muted block">Agenda</span>
                <span className="font-bold text-ink-primary block">
                  {candidate.score_breakdown.agenda.is_active
                    ? `${Math.round(candidate.score_breakdown.agenda.raw_similarity * 100)}%`
                    : 'N/A'}
                </span>
                <span className="text-[9px] text-ink-muted font-mono">
                  {candidate.score_breakdown.agenda.is_active
                    ? `Weight: ${Math.round(candidate.score_breakdown.agenda.effective_weight * 100)}%`
                    : 'Redistributed'}
                </span>
              </div>

              {/* Hobbies */}
              <div className="bg-canvas-elevated p-2 rounded border border-canvas-border">
                <span className="text-[10px] uppercase font-mono text-ink-muted block">Hobbies</span>
                <span className="font-bold text-ink-primary block">
                  {candidate.score_breakdown.hobbies.is_active
                    ? `${Math.round(candidate.score_breakdown.hobbies.raw_similarity * 100)}%`
                    : 'N/A'}
                </span>
                <span className="text-[9px] text-ink-muted font-mono">
                  {candidate.score_breakdown.hobbies.is_active
                    ? `Weight: ${Math.round(candidate.score_breakdown.hobbies.effective_weight * 100)}%`
                    : 'Redistributed'}
                </span>
              </div>
            </div>

            <p className="text-[10px] text-ink-muted leading-tight">
              Scores represent mathematical overlap across declared profiles. Inactive dimensions redistribute their weight proportionally across active factors.
            </p>
          </div>
        )}
      </div>

      {startError && (
        <div className="pt-2 text-xs text-crimson font-medium">
          {startError}
        </div>
      )}

      {/* Card Action Footer */}
      <div className="pt-4 mt-4 border-t border-canvas-border flex flex-col sm:flex-row items-center justify-between gap-2.5">
        <Link
          to={`/profile/${candidate.candidate_id}`}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-canvas-elevated border border-canvas-border text-ink-primary hover:border-brass hover:text-brass transition-colors focus:outline-none focus:ring-2 focus:ring-brass"
          aria-label={`View public profile of ${candidate.full_name}`}
        >
          <span aria-hidden="true">👤</span>
          <span>View Public Profile</span>
        </Link>
        <div className="w-full sm:w-auto flex items-center gap-2">
          {isSelectable && (
            <button
              type="button"
              onClick={() => onToggleSelect?.(candidate.candidate_id)}
              disabled={disabledSelect && !isSelected}
              className={`w-full sm:w-auto inline-flex items-center justify-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
                isSelected
                  ? 'bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border-amber-300 dark:border-amber-800 hover:bg-amber-200'
                  : 'bg-canvas-elevated border-canvas-border text-ink-primary hover:border-brass hover:text-brass disabled:opacity-40 disabled:cursor-not-allowed'
              }`}
            >
              <span>{isSelected ? '✓ In Circle' : '⭕ Add to Circle'}</span>
            </button>
          )}
          <button
            type="button"
            onClick={handleStartConversation}
            disabled={isStarting}
            className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-brass text-white hover:bg-brass/90 transition-colors shadow-xs disabled:opacity-50"
          >
            <span aria-hidden="true">💬</span>
            <span>
              {isStarting ? 'Connecting...' : (
                <>
                  <span>Connect</span>
                  <span className="hidden sm:inline"> &amp; Message</span>
                </>
              )}
            </span>
          </button>
        </div>
      </div>
    </article>
  );
};
