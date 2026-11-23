import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { conversationApi } from '@/lib/api/conversation';
import { groupConversationApi } from '@/lib/api/groupConversation';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusBadge, StatusVariant } from '@/components/ui/StatusBadge';
import { Conversation, ConversationStatus } from '@/types/conversation';
import { GroupConversation } from '@/types/groupConversation';
import { CreateCircleModal } from '@/components/chat/CreateCircleModal';

function getStatusBadgeVariant(status: ConversationStatus | string): StatusVariant {
  switch (status) {
    case 'ACTIVE':
      return 'success';
    case 'INVITED':
      return 'warning';
    case 'COMPLETED':
      return 'neutral';
    case 'CANCELLED':
    case 'EXPIRED':
      return 'danger';
    default:
      return 'neutral';
  }
}

export const Conversations: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') === 'circles' ? 'circles' : 'direct';
  const [activeTab, setActiveTab] = useState<'direct' | 'circles'>(initialTab);
  const [isCreateCircleOpen, setIsCreateCircleOpen] = useState(false);

  const handleTabChange = (tab: 'direct' | 'circles') => {
    setActiveTab(tab);
    setSearchParams(tab === 'circles' ? { tab: 'circles' } : {});
  };

  // Direct 1-on-1 conversations query
  const {
    data: conversations,
    isLoading: isLoadingDirect,
    isError: isErrorDirect,
    error: errorDirect,
    refetch: refetchDirect,
  } = useQuery<Conversation[]>({
    queryKey: ['conversations'],
    queryFn: conversationApi.listConversations,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  // Networking circles query
  const {
    data: circles,
    isLoading: isLoadingCircles,
    isError: isErrorCircles,
    error: errorCircles,
    refetch: refetchCircles,
  } = useQuery<GroupConversation[]>({
    queryKey: ['group-circles'],
    queryFn: groupConversationApi.listCircles,
    refetchInterval: 3000,
    refetchIntervalInBackground: true,
  });

  if (activeTab === 'direct' && isLoadingDirect) {
    return <LoadingState message="Loading conversations..." />;
  }
  if (activeTab === 'circles' && isLoadingCircles) {
    return <LoadingState message="Loading networking circles..." />;
  }

  const directActiveCount =
    conversations?.filter((c) => c.status === 'INVITED' || c.status === 'ACTIVE').length || 0;
  const circlesActiveCount = circles?.filter((c) => c.status === 'ACTIVE').length || 0;

  return (
    <div className="w-full max-w-7xl mx-auto py-6 sm:py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header and Quota Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-5 border-b border-canvas-border dark:border-slate-800 gap-4">
        <div>
          <h1 className="font-serif text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white tracking-tight">
            Conversations
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
            One-to-one dialogue and multi-delegate Thematic Networking Circles with AI representative facilitation.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="bg-canvas-elevated dark:bg-slate-800/80 px-4 py-2 rounded-lg border border-canvas-border dark:border-slate-700 text-xs sm:text-sm">
            <span className="text-slate-500 dark:text-slate-400 font-medium">
              {activeTab === 'direct' ? 'Active 1-on-1: ' : 'Active Circles: '}
            </span>
            <span
              className={`font-semibold font-mono ${
                (activeTab === 'direct' ? directActiveCount : circlesActiveCount) >= 3
                  ? 'text-amber-600 dark:text-amber-400'
                  : 'text-slate-900 dark:text-white'
              }`}
            >
              {activeTab === 'direct' ? directActiveCount : circlesActiveCount} / 3
            </span>
          </div>

          {activeTab === 'circles' ? (
            <button
              onClick={() => setIsCreateCircleOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-brass hover:bg-brass/90 text-white font-medium rounded-lg text-xs sm:text-sm shadow-xs transition"
            >
              <span>+</span>
              <span>New Circle</span>
            </button>
          ) : (
            <Link
              to="/matching"
              className="inline-flex items-center px-4 py-2 bg-brass hover:bg-brass/90 text-white font-medium rounded-lg text-xs sm:text-sm shadow-xs transition"
            >
              Find Attendees
            </Link>
          )}
        </div>
      </div>

      {/* Mode Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={() => handleTabChange('direct')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'direct'
              ? 'border-brass text-brass'
              : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
          }`}
        >
          <span>💬</span>
          <span>Direct Messages (1-on-1)</span>
          {directActiveCount > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
              {directActiveCount}
            </span>
          )}
        </button>

        <button
          onClick={() => handleTabChange('circles')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-semibold border-b-2 transition -mb-px ${
            activeTab === 'circles'
              ? 'border-brass text-brass'
              : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
          }`}
        >
          <span>⭕</span>
          <span>Networking Circles (Group)</span>
          {circlesActiveCount > 0 && (
            <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 font-mono">
              {circlesActiveCount}
            </span>
          )}
        </button>
      </div>

      {/* Tab Content 1: Direct 1-on-1 Conversations */}
      {activeTab === 'direct' && (
        <>
          {isErrorDirect ? (
            <div className="w-full max-w-4xl mx-auto py-12 px-4">
              <EmptyState
                emoji="⚠️"
                title="Could Not Load Conversations"
                description={
                  errorDirect instanceof Error
                    ? errorDirect.message
                    : 'An error occurred while loading conversations.'
                }
                action={
                  <button
                    onClick={() => refetchDirect()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition"
                  >
                    Try Again
                  </button>
                }
              />
            </div>
          ) : !conversations || conversations.length === 0 ? (
            <EmptyState
              emoji="💬"
              title="No Conversations Yet"
              description="You have not started any 1-on-1 conversations. Discover compatible attendees and send an invite to connect!"
              action={
                <Link
                  to="/matching"
                  className="px-4 py-2 bg-brass hover:bg-brass/90 text-white font-medium rounded-lg shadow-xs transition inline-block text-xs"
                >
                  Discover Matches
                </Link>
              }
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {conversations.map((conv) => (
                <Link
                  key={conv.id}
                  to={`/conversations/${conv.id}`}
                  className="block bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-brass dark:hover:border-brass/70 rounded-xl p-5 shadow-xs transition hover:shadow-md group"
                >
                  <div className="flex flex-col justify-between h-full gap-3">
                    <div className="flex items-start gap-3.5">
                      <div className="w-12 h-12 rounded-full bg-brass/10 text-brass border border-brass/20 flex items-center justify-center font-bold text-lg shrink-0 group-hover:scale-105 transition-transform">
                        {(conv.other_participant_name || 'Attendee').charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 truncate">
                            <span className="font-semibold text-slate-900 dark:text-white text-base truncate">
                              {conv.other_participant_name || 'Participant'}
                            </span>
                            {conv.has_business_context && (
                              <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 px-2 py-0.5 rounded-md shrink-0">
                                <span>📜</span>
                                <span>RFQ Brief</span>
                              </span>
                            )}
                          </div>
                          <StatusBadge label={conv.status} variant={getStatusBadgeVariant(conv.status)} />
                        </div>

                        {conv.other_participant_mood && (
                          <div className="mt-1">
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-950/40 border border-amber-200/50 dark:border-amber-900/50 px-2 py-0.5 rounded-full">
                              <span>✨</span>
                              <span className="truncate">{conv.other_participant_mood}</span>
                            </span>
                          </div>
                        )}

                        <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                          {conv.last_message ? (
                            <span>
                              <span className="font-medium text-slate-700 dark:text-slate-300">
                                {conv.last_message.sender_id === conv.other_participant_id ? '' : 'You: '}
                              </span>
                              {conv.last_message.message_type === 'LOCATION' ||
                              conv.last_message.location_payload ? (
                                <span className="text-brass font-medium">📍 Shared a location</span>
                              ) : (
                                conv.last_message.content
                              )}
                            </span>
                          ) : (
                            <span className="italic text-slate-400 dark:text-slate-500">
                              {conv.status === 'INVITED' ? 'Invitation awaiting acceptance' : 'No messages yet'}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-400 dark:text-slate-500">
                      <span className="text-[11px]">
                        {new Date(conv.updated_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-600 dark:text-slate-400">
                          {conv.message_count} / 30 turns
                        </span>
                        <span className="text-brass group-hover:translate-x-0.5 transition-transform text-xs font-semibold">
                          Open →
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      {/* Tab Content 2: Thematic Networking Circles (Group) */}
      {activeTab === 'circles' && (
        <>
          {isErrorCircles ? (
            <div className="w-full max-w-4xl mx-auto py-12 px-4">
              <EmptyState
                emoji="⚠️"
                title="Could Not Load Networking Circles"
                description={
                  errorCircles instanceof Error
                    ? errorCircles.message
                    : 'An error occurred while loading your circles.'
                }
                action={
                  <button
                    onClick={() => refetchCircles()}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition"
                  >
                    Try Again
                  </button>
                }
              />
            </div>
          ) : !circles || circles.length === 0 ? (
            <EmptyState
              emoji="⭕"
              title="No Networking Circles Yet"
              description="Join or create a Thematic Networking Circle with 2 to 3 fellow delegates. Our AI Representatives will facilitate initial synergies!"
              action={
                <button
                  onClick={() => setIsCreateCircleOpen(true)}
                  className="px-4 py-2 bg-brass hover:bg-brass/90 text-white font-medium rounded-lg shadow-xs transition inline-block text-xs"
                >
                  Launch First Circle
                </button>
              }
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {circles.map((circle) => (
                <Link
                  key={circle.id}
                  to={`/conversations/circles/${circle.id}`}
                  className="block bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-brass dark:hover:border-brass/70 rounded-xl p-5 shadow-xs transition hover:shadow-md group"
                >
                  <div className="flex flex-col justify-between h-full gap-3">
                    <div className="flex items-start gap-3.5">
                      <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200/50 dark:border-amber-900/50 flex items-center justify-center font-bold text-xl shrink-0 group-hover:scale-105 transition-transform">
                        ⭕
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-semibold text-slate-900 dark:text-white text-base truncate">
                            {circle.title}
                          </h3>
                          <StatusBadge label={circle.status} variant={getStatusBadgeVariant(circle.status)} />
                        </div>

                        <div className="mt-1 flex items-center gap-2 flex-wrap">
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md">
                            <span>👥</span>
                            <span>{circle.members_count} Delegates</span>
                          </span>
                          <span className="text-[11px] text-slate-500 dark:text-slate-400">
                            Host: {circle.host_name || 'Host'}
                          </span>
                        </div>

                        <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                          {circle.last_message ? (
                            <span>
                              <span className="font-medium text-slate-700 dark:text-slate-300">
                                {circle.last_message.sender_type === 'AGENT'
                                  ? '🤖 Virtual Rep: '
                                  : circle.last_message.sender_full_name
                                  ? `${circle.last_message.sender_full_name}: `
                                  : ''}
                              </span>
                              {circle.last_message.content}
                            </span>
                          ) : (
                            <span className="italic text-slate-400 dark:text-slate-500">
                              {circle.topic_context}
                            </span>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-400 dark:text-slate-500">
                      <span className="text-[11px]">
                        {new Date(circle.updated_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[10px] bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded text-slate-600 dark:text-slate-400">
                          {circle.current_turn} / {circle.max_turns} turns
                        </span>
                        <span className="text-brass group-hover:translate-x-0.5 transition-transform text-xs font-semibold">
                          Join Circle →
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      {/* Launcher Modal */}
      <CreateCircleModal
        isOpen={isCreateCircleOpen}
        onClose={() => setIsCreateCircleOpen(false)}
      />
    </div>
  );
};
