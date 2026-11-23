import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth/AuthContext';
import { groupConversationApi } from '@/lib/api/groupConversation';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { GroupConversationDetail, GroupMessage } from '@/types/groupConversation';
import { GroupRosterModal } from '@/components/chat/GroupRosterModal';

function getStatusBadgeVariant(status: string): StatusVariant {
  switch (status) {
    case 'ACTIVE':
      return 'success';
    case 'COMPLETED':
      return 'neutral';
    default:
      return 'neutral';
  }
}

export const GroupConversationDetailRoute: React.FC = () => {
  const { circleId } = useParams<{ circleId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [messages, setMessages] = useState<GroupMessage[]>([]);
  const [content, setContent] = useState<string>('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [isRosterOpen, setIsRosterOpen] = useState<boolean>(false);
  const [isTopicExpanded, setIsTopicExpanded] = useState<boolean>(false);
  const [showLeaveModal, setShowLeaveModal] = useState<boolean>(false);
  const [showCloseModal, setShowCloseModal] = useState<boolean>(false);
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false);

  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    data: circle,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<GroupConversationDetail>({
    queryKey: ['group-circle', circleId],
    queryFn: () => groupConversationApi.getCircle(circleId!),
    enabled: !!circleId,
    refetchInterval: (query) => {
      const data = query.state.data as GroupConversationDetail | undefined;
      if (!data) return 2000;
      const aiLimit = data.ai_turns_budget || 10;
      // If AI roundtable is currently generating (turns <= aiLimit), poll frequently (1s)
      if (data.status === 'ACTIVE' && data.current_turn <= aiLimit) {
        return 1000;
      }
      return 3000;
    },
  });

  useEffect(() => {
    if (circle?.messages) {
      setMessages(circle.messages);
    }
  }, [circle?.messages]);

  useEffect(() => {
    // Scroll only the message feed container without shifting outer windows/headers
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMutation = useMutation({
    mutationFn: (msgText: string) => groupConversationApi.sendMessage(circleId!, msgText),
    onSuccess: (newMsg) => {
      setMessages((prev) => [...prev, newMsg]);
      setContent('');
      setSendError(null);
      queryClient.invalidateQueries({ queryKey: ['group-circle', circleId] });
      queryClient.invalidateQueries({ queryKey: ['group-circles'] });
    },
    onError: (err: any) => {
      setSendError(err?.detail || err?.message || 'Failed to send message.');
    },
  });

  const leaveMutation = useMutation({
    mutationFn: () => groupConversationApi.leaveCircle(circleId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-circles'] });
      navigate('/conversations?tab=circles');
    },
    onError: (err: any) => {
      setSendError(err?.detail || err?.message || 'Failed to leave circle.');
      setShowLeaveModal(false);
    },
  });

  const closeMutation = useMutation({
    mutationFn: () => groupConversationApi.closeCircle(circleId!),
    onSuccess: () => {
      setShowCloseModal(false);
      queryClient.invalidateQueries({ queryKey: ['group-circle', circleId] });
      queryClient.invalidateQueries({ queryKey: ['group-circles'] });
    },
    onError: (err: any) => {
      setSendError(err?.detail || err?.message || 'Failed to conclude circle.');
      setShowCloseModal(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => groupConversationApi.deleteCircle(circleId!),
    onSuccess: () => {
      setShowDeleteModal(false);
      queryClient.invalidateQueries({ queryKey: ['group-circles'] });
      navigate('/conversations?tab=circles');
    },
    onError: (err: any) => {
      setSendError(err?.detail || err?.message || 'Failed to delete circle.');
      setShowDeleteModal(false);
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || sendMutation.isPending) return;
    setSendError(null);
    sendMutation.mutate(content.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  if (isLoading) {
    return <LoadingState message="Connecting to Networking Circle..." />;
  }

  if (isError || !circle) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-4">
        <EmptyState
          emoji="⚠️"
          title="Could Not Join Circle"
          description={
            error instanceof Error ? error.message : 'You may not have permission or this circle was removed.'
          }
          action={
            <div className="flex items-center gap-2">
              <button
                onClick={() => refetch()}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-xs transition"
              >
                Try Again
              </button>
              <Link
                to="/conversations?tab=circles"
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-800 dark:text-slate-200 font-medium rounded-lg text-xs transition"
              >
                Back to Conversations
              </Link>
            </div>
          }
        />
      </div>
    );
  }

  const aiLimit = circle.ai_turns_budget || 10;
  const isAiRoundtableActive = circle.status === 'ACTIVE' && circle.current_turn <= aiLimit;
  const isCircleActive = circle.status === 'ACTIVE';
  const isHost = circle.host_id === user?.id;
  const turnsRemaining = Math.max(0, circle.max_turns - circle.current_turn);
  const turnPercentage = Math.min(100, Math.round((circle.current_turn / circle.max_turns) * 100));

  return (
    <div className="w-full max-w-6xl mx-auto h-full flex flex-col min-h-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
      {/* Top Header Section */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 p-3 sm:p-4 flex-shrink-0 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2.5 pb-2 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2.5 min-w-0">
            <Link
              to="/conversations?tab=circles"
              className="p-1 sm:p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition shrink-0 text-xs font-semibold"
              title="Back to Networking Circles"
            >
              ← Back
            </Link>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-lg">⭕</span>
                <h1 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white truncate">
                  {circle.title}
                </h1>
                <StatusBadge label={circle.status} variant={getStatusBadgeVariant(circle.status)} />
                {isHost && (
                  <span className="px-2 py-0.5 rounded-md bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-300 font-semibold text-[10px] uppercase tracking-wider">
                    👑 Host
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                Host: <span className="font-medium text-slate-700 dark:text-slate-300">{circle.host_name || 'Host'}</span>
              </p>
            </div>
          </div>

          {/* Action Controls */}
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setIsTopicExpanded(!isTopicExpanded)}
              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-medium flex items-center gap-1 transition"
            >
              <span>🎯</span>
              <span>{isTopicExpanded ? 'Hide Theme' : 'Theme'}</span>
            </button>
            <button
              type="button"
              onClick={() => setIsRosterOpen(true)}
              className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition"
            >
              <span>👥</span>
              <span>{circle.members_count} Delegates</span>
            </button>

            {/* Host-Exclusive Actions */}
            {isHost ? (
              <>
                {isCircleActive && (
                  <button
                    type="button"
                    onClick={() => setShowCloseModal(true)}
                    className="px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-xs font-semibold transition"
                    title="Conclude circle discussion (preserves transcript)"
                  >
                    🛑 Close Circle
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(true)}
                  className="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900 text-xs font-semibold transition"
                  title="Permanently disband and delete circle"
                >
                  🗑️ Delete Circle
                </button>
              </>
            ) : (
              /* Non-Host Member Action */
              isCircleActive && (
                <button
                  type="button"
                  onClick={() => setShowLeaveModal(true)}
                  className="px-2.5 py-1 rounded-lg border border-rose-200 dark:border-rose-900/50 hover:bg-rose-50 dark:hover:bg-rose-950/30 text-rose-600 dark:text-rose-400 text-xs font-medium transition"
                >
                  Leave Circle
                </button>
              )
            )}
          </div>
        </div>

        {/* Topic Context Drawer (collapsible) */}
        {isTopicExpanded && (
          <div className="bg-slate-50 dark:bg-slate-800/40 rounded-lg p-2.5 border border-slate-100 dark:border-slate-800 text-xs text-slate-600 dark:text-slate-300 leading-relaxed animate-in fade-in duration-150">
            <span className="font-semibold text-slate-800 dark:text-slate-200">Thematic Focus: </span>
            {circle.topic_context}
          </div>
        )}

        {/* Turn Tracker & Progress Bar */}
        <div className="space-y-1">
          <div className="flex items-center justify-between text-[11px] sm:text-xs text-slate-600 dark:text-slate-400">
            <span className="font-medium">
              {isAiRoundtableActive ? (
                <>Roundtable Progress: <span className="text-amber-700 dark:text-amber-400 font-medium">Representative discussion in progress</span></>
              ) : (
                <>Roundtable Progress: <strong className="text-slate-900 dark:text-white font-mono">{circle.current_turn}</strong> / {circle.max_turns} turns</>
              )}
            </span>
            <span className="font-mono text-slate-500">
              {isAiRoundtableActive ? 'Representative Alignment' : `${turnsRemaining} human turns left`}
            </span>
          </div>
          <div className="w-full h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 rounded-full ${
                turnPercentage >= 90
                  ? 'bg-rose-500'
                  : turnPercentage >= 70
                  ? 'bg-amber-500'
                  : 'bg-brass'
              }`}
              style={{ width: `${turnPercentage}%` }}
            />
          </div>
        </div>

        {/* Facilitator Protocol Status Banner */}
        {isAiRoundtableActive ? (
          <div className="px-3 py-2 bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg flex items-center gap-2.5 text-xs text-amber-900 dark:text-amber-200">
            <span className="animate-pulse text-base">🤖</span>
            <span className="font-medium truncate">
              Virtual Roundtable Protocol Active • Representatives are discussing priorities. Open discussion will unlock shortly.
            </span>
          </div>
        ) : isCircleActive ? (
          <div className="px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 rounded-lg flex items-center justify-between text-xs text-emerald-800 dark:text-emerald-200">
            <div className="flex items-center gap-1.5">
              <span>💬</span>
              <span className="font-medium">
                Roundtable Introductions Complete • Floor is open for manual discussion
              </span>
            </div>
            <span className="text-[11px] font-mono opacity-80">{circle.members_count} participants active</span>
          </div>
        ) : (
          <div className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800/90 rounded-lg text-center text-xs text-slate-600 dark:text-slate-300 font-medium">
            🛑 Circle discussion is concluded. The transcript is preserved below for reference.
          </div>
        )}
      </div>

      {/* Messages Feed (Scrollable, takes all remaining space) */}
      <div
        ref={messagesContainerRef}
        className="flex-1 min-h-0 bg-slate-50 dark:bg-slate-950 p-3 sm:p-5 overflow-y-auto space-y-3"
      >
        {messages.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs">
            Initiating circle dialogue...
          </div>
        ) : (
          messages.map((msg) => {
            const isSystem = msg.sender_type === 'SYSTEM';
            const isAgent = msg.sender_type === 'AGENT';
            const isSelf = msg.sender_id === user?.id;

            if (isSystem) {
              return (
                <div key={msg.id} className="flex justify-center my-3">
                  <div className="bg-slate-100 dark:bg-slate-850 border border-slate-200 dark:border-slate-700/60 px-3.5 py-1.5 rounded-full text-[11px] text-slate-600 dark:text-slate-300 font-medium text-center max-w-lg shadow-xs">
                    <span>⚡ {msg.content}</span>
                  </div>
                </div>
              );
            }

            if (isAgent) {
              return (
                <div key={msg.id} className="flex flex-col items-start space-y-1 max-w-2xl my-3">
                  <div className="flex items-center gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                    <span className="inline-flex items-center gap-1 font-semibold text-brass bg-brass/10 px-2 py-0.5 rounded-md border border-brass/20">
                      <span>🤖</span>
                      <span>{msg.sender_full_name || 'Delegate'}'s Virtual Representative</span>
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">Turn #{msg.turn_index}</span>
                  </div>
                  <div className="bg-gradient-to-br from-amber-50/70 to-slate-50 dark:from-slate-800 dark:to-slate-800/80 border border-amber-200/50 dark:border-slate-700 rounded-2xl rounded-tl-xs p-4 shadow-xs text-xs sm:text-sm text-slate-800 dark:text-slate-100 leading-relaxed font-serif">
                    {msg.content}
                  </div>
                </div>
              );
            }

            // Human Participant message
            return (
              <div
                key={msg.id}
                className={`flex flex-col space-y-1 max-w-xl ${isSelf ? 'ml-auto items-end' : 'mr-auto items-start'}`}
              >
                <div className="flex items-center gap-2 text-[11px] text-slate-400 px-1">
                  <span className="font-semibold text-slate-700 dark:text-slate-300">
                    {isSelf ? 'You' : msg.sender_full_name || msg.sender_username || 'Participant'}
                  </span>
                  <span className="font-mono text-[10px]">
                    {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                <div
                  className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed ${
                    isSelf
                      ? 'bg-brass text-white rounded-tr-xs shadow-xs'
                      : 'bg-white dark:bg-slate-800 text-slate-900 dark:text-white rounded-tl-xs border border-slate-200/80 dark:border-slate-700 shadow-xs'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            );
          })
        )}
        {isCircleActive && isAiRoundtableActive && (
          <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs text-amber-800 dark:text-amber-300 shadow-2xs">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-600 animate-ping shrink-0" />
            <span className="font-medium">
              Virtual Representative Roundtable in progress. Next representative exchange is arriving shortly...
            </span>
          </div>
        )}
      </div>

      {/* Input Box Bar */}
      <div className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-2.5 sm:p-3 flex-shrink-0">
        {sendError && (
          <div className="mb-2 p-2 text-xs bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 rounded-lg">
            {sendError}
          </div>
        )}
        <form onSubmit={handleSendMessage} className="flex items-center gap-2">
          <input
            type="text"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={!isCircleActive || isAiRoundtableActive || sendMutation.isPending}
            placeholder={
              !isCircleActive
                ? 'Circle discussion concluded. Transcript preserved.'
                : isAiRoundtableActive
                ? 'Manual messaging locked during AI Representative roundtable...'
                : 'Contribute to the circle discussion...'
            }
            maxLength={1000}
            className="flex-1 px-4 py-2.5 text-xs sm:text-sm bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-brass disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!content.trim() || !isCircleActive || isAiRoundtableActive || sendMutation.isPending}
            className="px-4 py-2.5 bg-brass hover:bg-brass/90 text-white font-semibold text-xs sm:text-sm rounded-xl transition shadow-xs disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          >
            {sendMutation.isPending ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>

      {/* Roster Modal */}
      <GroupRosterModal
        isOpen={isRosterOpen}
        onClose={() => setIsRosterOpen(false)}
        members={circle.members}
        hostId={circle.host_id}
      />

      {/* Leave Circle Confirmation Modal (Non-Host Member) */}
      {showLeaveModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl text-rose-500">🚪</span>
              <h3 className="font-semibold text-base text-slate-900 dark:text-white">
                Leave Networking Circle?
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              Are you sure you want to exit this circle? Other delegates will be notified, and you will lose access to post further messages.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowLeaveModal(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
              >
                Stay
              </button>
              <button
                type="button"
                onClick={() => leaveMutation.mutate()}
                disabled={leaveMutation.isPending}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition disabled:opacity-50"
              >
                {leaveMutation.isPending ? 'Exiting...' : 'Confirm Exit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Close Circle Confirmation Modal (Host Only) */}
      {showCloseModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl text-amber-500">🛑</span>
              <h3 className="font-semibold text-base text-slate-900 dark:text-white">
                Conclude Networking Circle?
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              As host, concluding this circle will complete the session. All delegates will still be able to review the full transcript, but no further turns can be posted. Circle quota will be freed immediately for all members.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowCloseModal(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => closeMutation.mutate()}
                disabled={closeMutation.isPending}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition disabled:opacity-50"
              >
                {closeMutation.isPending ? 'Concluding...' : '🛑 Conclude Circle'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Circle Confirmation Modal (Host Only) */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <span className="text-2xl text-rose-600">🗑️</span>
              <h3 className="font-semibold text-base text-slate-900 dark:text-white">
                Permanently Delete Circle?
              </h3>
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              Are you sure you want to permanently disband and delete this networking circle? All discussion history and messages will be permanently deleted for all delegates. This cannot be undone.
            </p>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-3 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting...' : '🗑️ Delete Permanently'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
