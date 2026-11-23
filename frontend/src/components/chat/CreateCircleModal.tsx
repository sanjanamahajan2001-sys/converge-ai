import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getCandidateMatches } from '@/lib/api/matching';
import { groupConversationApi } from '@/lib/api/groupConversation';
import { MatchEvaluationResult } from '@/types/matching';

interface CreateCircleModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialSelectedMemberIds?: string[];
}

export const CreateCircleModal: React.FC<CreateCircleModalProps> = ({
  isOpen,
  onClose,
  initialSelectedMemberIds = [],
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [topicContext, setTopicContext] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedMemberIds);
  const [formError, setFormError] = useState<string | null>(null);

  // Sync initialSelectedMemberIds when modal opens
  useEffect(() => {
    if (isOpen) {
      if (initialSelectedMemberIds && initialSelectedMemberIds.length > 0) {
        setSelectedIds(initialSelectedMemberIds);
      }
    }
  }, [initialSelectedMemberIds, isOpen]);

  // Fetch available candidates from Mode A matching
  const { data: matchResult, isLoading: isLoadingCandidates } = useQuery<MatchEvaluationResult>({
    queryKey: ['matching-candidates'],
    queryFn: () => getCandidateMatches({ filter_by_threshold: false }),
    enabled: isOpen,
  });

  const candidates = matchResult?.candidates || [];

  // Pre-fill suggested title & topic context from mutual interests
  useEffect(() => {
    if (isOpen && candidates.length > 0 && selectedIds.length >= 2 && !title) {
      const selectedCandidates = candidates.filter((c) => selectedIds.includes(c.candidate_id));
      const allTopics = selectedCandidates.flatMap((c) => c.common_topics || c.topics || []);
      const uniqueTopics = Array.from(new Set(allTopics)).filter(Boolean);
      if (uniqueTopics.length > 0) {
        setTitle(`${uniqueTopics.slice(0, 2).join(' & ')} Working Group`);
        if (!topicContext) {
          setTopicContext(
            `Collaborative exploration and operational synchronization around ${uniqueTopics.slice(0, 3).join(', ')}.`
          );
        }
      }
    }
  }, [isOpen, candidates, selectedIds, title, topicContext]);

  const createMutation = useMutation({
    mutationFn: groupConversationApi.createCircle,
    onSuccess: (newCircle) => {
      queryClient.invalidateQueries({ queryKey: ['group-circles'] });
      onClose();
      navigate(`/conversations/circles/${newCircle.id}`);
    },
    onError: (err: any) => {
      setFormError(err?.detail || err?.message || 'Failed to initiate circle. Please check active quotas.');
    },
  });

  if (!isOpen) return null;

  const handleToggleMember = (userId: string) => {
    setFormError(null);
    if (selectedIds.includes(userId)) {
      setSelectedIds(selectedIds.filter((id) => id !== userId));
    } else {
      if (selectedIds.length >= 4) {
        setFormError('You can select at most 4 peers (up to 5 delegates total including you).');
        return;
      }
      setSelectedIds([...selectedIds, userId]);
    }
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (selectedIds.length < 2) {
      setFormError('Please select at least 2 peers (circles require 3 to 5 total participants).');
      return;
    }
    if (!title.trim()) {
      setFormError('Please enter a circle title.');
      return;
    }
    if (!topicContext.trim()) {
      setFormError('Please describe the thematic discussion topic or focus.');
      return;
    }

    createMutation.mutate({
      title: title.trim(),
      topic_context: topicContext.trim(),
      member_ids: selectedIds,
    });
  };

  const totalMembers = selectedIds.length + 1; // including host
  const maxTurns = 30 + 5 * (totalMembers - 2);

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-2xl">⭕</span>
            <div>
              <h3 className="font-semibold text-lg text-slate-900 dark:text-white">
                Launch Thematic Networking Circle
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Mode A Attendee Discovery • Automated AI Representative Roundtable
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-lg p-1 rounded-md"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {formError && (
          <div className="p-3 text-xs bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 rounded-lg">
            {formError}
          </div>
        )}

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              Circle Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Decarbonization & Alternative Fuels Working Group"
              className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-brass"
              maxLength={120}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-1">
              Discussion Theme & Context
            </label>
            <textarea
              value={topicContext}
              onChange={(e) => setTopicContext(e.target.value)}
              placeholder="Outline the shared technical, regulatory, or operational themes for the AI representative to ground discussion upon..."
              rows={3}
              className="w-full px-3 py-2 text-sm bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-brass"
              maxLength={500}
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                Select Peers ({selectedIds.length}/4 selected)
              </label>
              <span className="text-[11px] text-slate-400">Requires 2 to 4 peers</span>
            </div>

            {isLoadingCandidates ? (
              <div className="p-4 text-center text-xs text-slate-500">Loading compatible attendees...</div>
            ) : (!candidates || candidates.length === 0) ? (
              <div className="p-4 text-center text-xs text-slate-500 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                No matching attendees found. Please ensure profiles are created.
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg p-2 bg-slate-50/50 dark:bg-slate-800/40">
                {candidates.map((cand) => {
                  const isChecked = selectedIds.includes(cand.candidate_id);
                  return (
                    <label
                      key={cand.candidate_id}
                      className={`flex items-center justify-between p-2 rounded-md cursor-pointer transition text-xs ${
                        isChecked
                          ? 'bg-brass/10 dark:bg-brass/20 border border-brass/40'
                          : 'hover:bg-slate-100 dark:hover:bg-slate-800 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => handleToggleMember(cand.candidate_id)}
                          className="rounded text-brass focus:ring-brass h-4 w-4"
                        />
                        <div className="min-w-0">
                          <p className="font-semibold text-slate-900 dark:text-white truncate">
                            {cand.full_name}
                          </p>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                            {cand.job_title ? `${cand.job_title} • ` : ''}{cand.company_name || 'Delegate'}
                          </p>
                        </div>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500 shrink-0 ml-2">
                        {Math.round(cand.composite_score * 100)}% match
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <div className="p-3 bg-amber-50/60 dark:bg-amber-950/30 border border-amber-200/50 dark:border-amber-900/50 rounded-lg flex items-center justify-between text-xs text-amber-800 dark:text-amber-200">
            <span>
              Dynamic Turn Limit: <strong>{maxTurns} turns</strong> ({totalMembers} delegates)
            </span>
            <span>
              AI Protocol: <strong>10 alignment turns</strong>
            </span>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <button
              type="button"
              onClick={onClose}
              disabled={createMutation.isPending}
              className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || selectedIds.length < 2}
              className="px-4 py-2 text-xs font-semibold text-white bg-brass hover:bg-brass/90 rounded-lg shadow-xs transition disabled:opacity-50"
            >
              {createMutation.isPending ? 'Launching Roundtable...' : 'Launch Circle ➜'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
