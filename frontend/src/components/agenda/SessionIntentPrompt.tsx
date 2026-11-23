import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getRecommendedSessions, recordSessionIntent } from '@/lib/api/agenda';
import { trackFeatureClick } from '@/lib/api/analytics';
import { SessionIntentDecisionState, SessionRecommendationPrompt as RecommendationType } from '@/types/agenda';

interface SessionIntentPromptProps {
  conferenceId?: string;
}

export const SessionIntentPrompt: React.FC<SessionIntentPromptProps> = ({ conferenceId }) => {
  const queryClient = useQueryClient();
  const [feedbackMsg, setFeedbackMsg] = useState<{ [sessionId: string]: string }>({});
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  const { data: recommendations = [], isLoading } = useQuery({
    queryKey: ['recommended-sessions'],
    queryFn: getRecommendedSessions,
    staleTime: 15000,
  });

  const relevantRecommendations = React.useMemo(() => {
    if (!conferenceId) return recommendations;
    return recommendations.filter((rec) => rec.session.conference_id === conferenceId);
  }, [recommendations, conferenceId]);

  const mutation = useMutation({
    mutationFn: ({ sessionId, decision }: { sessionId: string; decision: SessionIntentDecisionState }) =>
      recordSessionIntent(sessionId, decision),
    onSuccess: (_data, variables) => {
      trackFeatureClick('SESSION_INTENT', variables.sessionId, { decision: variables.decision });
      queryClient.invalidateQueries({ queryKey: ['recommended-sessions'] });
      queryClient.invalidateQueries({ queryKey: ['my-session-intents'] });
      setFeedbackMsg((prev) => ({
        ...prev,
        [variables.sessionId]:
          variables.decision === 'ATTENDING'
            ? 'Attendance confirmed! Your representative will share your attendance when relevant.'
            : variables.decision === 'DECLINED'
            ? 'Declined. Your representative will not suggest this session.'
            : 'Marked for later consideration.',
      }));
    },
  });

  if (isLoading || relevantRecommendations.length === 0) {
    return null;
  }

  return (
    <div className="mb-6 space-y-3" data-testid="session-intent-prompts-container">
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <span className="text-sm">🤖</span>
          <span className="text-xs font-bold text-ink-primary">
            AI Representative Recommendations ({relevantRecommendations.length} for this conference)
          </span>
        </div>
        <button
          type="button"
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="text-xs font-semibold text-brass hover:text-brass-hover transition"
        >
          {isCollapsed ? 'Show Suggestions ▼' : 'Hide Suggestions ▲'}
        </button>
      </div>

      {!isCollapsed &&
        relevantRecommendations.map((rec: RecommendationType) => {
        const sessionId = rec.session.id;
        const currentDecision = rec.current_decision;
        const isPending = mutation.isPending && mutation.variables?.sessionId === sessionId;

        return (
          <div
            key={sessionId}
            data-testid={`session-intent-prompt-${sessionId}`}
            className="rounded-xl border border-indigo-200 bg-gradient-to-r from-indigo-50/80 via-blue-50/40 to-white p-4 sm:p-5 shadow-sm transition-all"
          >
            {/* Header: Title, Tags, and Status Badge */}
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 sm:h-9 sm:w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-sm">
                  <span className="text-sm sm:text-base" role="img" aria-label="Agent">
                    🤖
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                    <span className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-indigo-700">
                      Virtual Representative Recommendation
                    </span>
                    <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] sm:text-xs font-medium text-indigo-800">
                      {rec.matched_reason}
                    </span>
                  </div>
                  <p className="mt-1 text-sm font-medium text-slate-800 leading-snug sm:leading-normal" data-testid="intent-prompt-message">
                    {rec.prompt_message}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Room: {rec.session.hall_room} • Track: {rec.session.track_name || 'General'}
                  </p>
                </div>
              </div>

              {/* Status Badge: On mobile positioned inline or top-right */}
              {currentDecision && (
                <div className="self-start sm:self-auto shrink-0 pl-11 sm:pl-0">
                  <span
                    data-testid="current-decision-badge"
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 sm:py-1 text-xs font-medium ${
                      currentDecision === 'ATTENDING'
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : currentDecision === 'DECLINED'
                        ? 'bg-rose-100 text-rose-800 border border-rose-300'
                        : 'bg-amber-100 text-amber-800 border border-amber-300'
                    }`}
                  >
                    {currentDecision === 'ATTENDING'
                      ? 'Attending ✓'
                      : currentDecision === 'DECLINED'
                      ? 'Declined ✕'
                      : 'Decide later ⏳'}
                  </span>
                </div>
              )}
            </div>

            {/* Action Buttons: Responsive Wrap / Grid */}
            <div className="mt-3 sm:mt-4 pt-3 border-t border-indigo-100/60">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-2.5">
                <span className="text-xs font-semibold text-slate-600 shrink-0">Your Decision:</span>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    data-testid="btn-intent-attending"
                    disabled={isPending}
                    onClick={() => mutation.mutate({ sessionId, decision: 'ATTENDING' })}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                      currentDecision === 'ATTENDING'
                        ? 'bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-400'
                        : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
                    }`}
                  >
                    Yes, attending
                  </button>
                  <button
                    type="button"
                    data-testid="btn-intent-declined"
                    disabled={isPending}
                    onClick={() => mutation.mutate({ sessionId, decision: 'DECLINED' })}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                      currentDecision === 'DECLINED'
                        ? 'bg-rose-600 text-white shadow-sm ring-2 ring-rose-400'
                        : 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
                    }`}
                  >
                    No, not interested
                  </button>
                  <button
                    type="button"
                    data-testid="btn-intent-undecided"
                    disabled={isPending}
                    onClick={() => mutation.mutate({ sessionId, decision: 'UNDECIDED' })}
                    className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                      currentDecision === 'UNDECIDED'
                        ? 'bg-slate-700 text-white shadow-sm ring-2 ring-slate-400'
                        : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200'
                    }`}
                  >
                    Decide later
                  </button>
                </div>
              </div>

              {feedbackMsg[sessionId] && (
                <div className="mt-2 text-xs font-medium text-indigo-600 animate-fade-in pl-0 sm:pl-2">
                  {feedbackMsg[sessionId]}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};
