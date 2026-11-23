import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/lib/auth/AuthContext';
import { conversationApi, getConversationWebSocketUrl } from '@/lib/api/conversation';
import { ApiClientError } from '@/lib/api/client';
import { EmptyState } from '@/components/ui/EmptyState';
import { LoadingState } from '@/components/ui/LoadingState';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { ConversationDetail, Message, ConversationOutcome, LocationPayload } from '@/types/conversation';
import { proposalApi } from '@/lib/api/proposal';
import { InChatProposalCard } from '@/components/chat/InChatProposalCard';
import { ProposalDraftModal } from '@/components/proposal/ProposalDraftModal';
import { SendQuoteEmailModal } from '@/components/quotes/SendQuoteEmailModal';
import { quoteApi } from '@/lib/api/quote';
import { brochureApi } from '@/lib/api/brochures';
import { SendQuoteEmailResponse } from '@/types/quote';
// import { LocationCard } from '@/components/chat/LocationCard';
// import { LocationPickerModal } from '@/components/chat/LocationPickerModal';

// Helper to cleanly render markdown bold (**) and code (`) and interactive brochure cards
const renderFormattedContent = (content: string, isMeBubble: boolean) => {
  if (!content) return null;

  // Extract brochure slug if present in message
  const brochureMatch = content.match(/\/brochures\/([a-zA-Z0-9_-]+)/);

  const renderText = () => {
    if (!content.includes('**') && !content.includes('`')) {
      return <span className="whitespace-pre-wrap leading-relaxed">{content}</span>;
    }

    const lines = content.split('\n');
    return (
      <div className="whitespace-pre-wrap leading-relaxed space-y-0.5">
        {lines.map((line, lIdx) => {
          if (!line.trim()) {
            return <div key={lIdx} className="h-1.5" />;
          }
          const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g);
          return (
            <div key={lIdx}>
              {parts.map((part, pIdx) => {
                if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
                  return (
                    <strong
                      key={pIdx}
                      className={`font-bold ${isMeBubble ? 'text-white' : 'text-slate-900 dark:text-white'}`}
                    >
                      {part.slice(2, -2)}
                    </strong>
                  );
                }
                if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
                  return (
                    <code
                      key={pIdx}
                      className={`font-mono text-[11px] px-1.5 py-0.5 rounded font-semibold ${
                        isMeBubble
                          ? 'bg-indigo-700/80 text-white'
                          : 'bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200'
                      }`}
                    >
                      {part.slice(1, -1)}
                    </code>
                  );
                }
                return <span key={pIdx}>{part}</span>;
              })}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="space-y-2">
      {renderText()}
      {brochureMatch && (
        <div className="pt-1">
          <Link
            to={`/brochures/${brochureMatch[1]}`}
            target="_blank"
            rel="noopener noreferrer"
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold shadow-xs transition-colors ${
              isMeBubble
                ? 'bg-amber-400 text-stone-950 hover:bg-amber-300'
                : 'bg-amber-600 hover:bg-amber-700 text-white'
            }`}
          >
            <span>📖</span>
            <span>Open Interactive 3D Flipbook ↗</span>
          </Link>
        </div>
      )}
    </div>
  );
};

export const ConversationDetailRoute: React.FC = () => {
  const { conversationId } = useParams<{ conversationId: string }>();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [messages, setMessages] = useState<Message[]>([]);
  const [content, setContent] = useState<string>('');
  const [sendError, setSendError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
  const [showConcludeModal, setShowConcludeModal] = useState<boolean>(false);
  const [isBriefExpanded, setIsBriefExpanded] = useState<boolean>(true);
  const [isDraftProposalOpen, setIsDraftProposalOpen] = useState<boolean>(false);
  const [isSendQuoteModalOpen, setIsSendQuoteModalOpen] = useState<boolean>(false);
  const [isBroadcastingRfq, setIsBroadcastingRfq] = useState<boolean>(false);
  const [quoteToast, setQuoteToast] = useState<string | null>(null);

  // Linked commercial proposals for this bilateral conversation
  const { data: conversationProposals = [] } = useQuery({
    queryKey: ['proposals', 'conversation', conversationId],
    queryFn: () => proposalApi.listProposals({ conversation_id: conversationId }),
    enabled: Boolean(conversationId),
    refetchInterval: 5000,
  });
  // const [showLocationModal, setShowLocationModal] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const { data: conversation, isLoading, isError, error, refetch } = useQuery<ConversationDetail>({
    queryKey: ['conversation', conversationId],
    queryFn: () => conversationApi.getConversation(conversationId!),
    enabled: !!conversationId,
    refetchInterval: (query) => {
      const data = query.state.data as ConversationDetail | undefined;
      // If conversation is active and fewer than 5 turns completed, poll every 1s
      if (data?.status === 'ACTIVE' && (data?.messages?.length ?? data?.message_count ?? 0) < 10) {
        return 1000;
      }
      return false;
    },
  });

  // User's own brochure for in-chat sharing
  const { data: myBrochure } = useQuery({
    queryKey: ['myBrochure'],
    queryFn: brochureApi.getMyBrochure,
    staleTime: 60000,
  });

  // Brochures directory for partner lookup
  const { data: brochuresDirectory = [] } = useQuery({
    queryKey: ['brochuresDirectory'],
    queryFn: () => brochureApi.getDirectory(),
    staleTime: 60000,
  });

  const otherBrochure = brochuresDirectory.find(
    (b) =>
      conversation?.other_participant_id &&
      b.owner_user_id === conversation.other_participant_id
  );

  // Sync initial messages when conversation loads
  useEffect(() => {
    if (conversation?.messages) {
      setMessages(conversation.messages);
    }
    if (conversation?.status) {
      setIsBriefExpanded(conversation.status === 'INVITED');
    }
  }, [conversation?.messages, conversation?.status]);

  // Scroll to bottom on message updates
  useEffect(() => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // WebSocket lifecycle management
  useEffect(() => {
    if (!conversationId) return;

    let isSubscribed = true;
    let reconnectTimeout: ReturnType<typeof setTimeout>;

    function connectWs() {
      setWsStatus('connecting');
      const wsUrl = getConversationWebSocketUrl(conversationId!);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!isSubscribed) return;
        setWsStatus('connected');
      };

      ws.onmessage = (event) => {
        if (!isSubscribed) return;
        try {
          const payload = JSON.parse(event.data);
          if (payload.event === 'message:new' && payload.data) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === payload.data.id)) {
                return prev;
              }
              return [...prev, payload.data];
            });
            if (payload.conversation_status) {
              queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
              queryClient.invalidateQueries({ queryKey: ['conversations'] });
            }
          } else if (payload.event === 'conversation:status') {
            queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
            queryClient.invalidateQueries({ queryKey: ['conversations'] });
          } else if (payload.event === 'proposal:update' || payload.event?.startsWith('proposal:')) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', conversationId] });
            queryClient.invalidateQueries({ queryKey: ['proposals'] });
            queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          }
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
        }
      };

      ws.onclose = () => {
        if (!isSubscribed) return;
        setWsStatus('disconnected');
        reconnectTimeout = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connectWs();

    return () => {
      isSubscribed = false;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [conversationId, queryClient]);

  // Send message mutation (supports string or location message payload)
  const sendMutation = useMutation({
    mutationFn: (args: string | { content: string; messageType?: string; locationPayload?: LocationPayload }) => {
      if (typeof args === 'string') {
        return conversationApi.sendMessage(conversationId!, args);
      }
      return conversationApi.sendMessage(
        conversationId!,
        args.content,
        args.messageType || 'LOCATION',
        args.locationPayload
      );
    },
    onSuccess: (newMsg) => {
      setContent('');
      setSendError(null);
      setMessages((prev) => {
        if (prev.some((m) => m.id === newMsg.id)) return prev;
        return [...prev, newMsg];
      });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
    onError: (err) => {
      if (err instanceof ApiClientError) {
        setSendError(err.detail);
      } else {
        setSendError('Failed to send message. Please try again.');
      }
    },
  });

  // Location sharing in conversations is hidden/commented out for now
  // const handleSendLocation = (payload: LocationPayload) => {
  //   setShowLocationModal(false);
  //   sendMutation.mutate({
  //     content: `📍 Shared Location: ${payload.name || 'Current Location'}`,
  //     messageType: 'LOCATION',
  //     locationPayload: payload,
  //   });
  // };

  // Action mutations (Accept, Cancel, Conclude, Trigger Agent)
  const acceptMutation = useMutation({
    mutationFn: (triggerAgent: boolean = true) =>
      conversationApi.acceptConversation(conversationId!, triggerAgent),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const triggerAgentMutation = useMutation({
    mutationFn: () => conversationApi.triggerAgentDialogue(conversationId!),
    onSuccess: (updatedConv) => {
      if (updatedConv?.messages) {
        setMessages(updatedConv.messages);
      }
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      refetch();
    },
    onError: (err) => {
      if (err instanceof ApiClientError) {
        setSendError(err.detail);
      } else {
        setSendError('Unable to generate representative turn at this time.');
      }
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => conversationApi.cancelConversation(conversationId!),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const concludeMutation = useMutation({
    mutationFn: (outcome: ConversationOutcome) =>
      conversationApi.concludeConversation(conversationId!, outcome),
    onSuccess: () => {
      refetch();
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || sendMutation.isPending) return;
    sendMutation.mutate(content.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  if (isLoading) {
    return (
      <div className="py-16">
        <LoadingState message="Loading conversation dialogue..." />
      </div>
    );
  }

  if (isError || !conversation) {
    return (
      <div className="w-full max-w-4xl mx-auto py-12 px-4">
        <EmptyState
          emoji="⚠️"
          title="Conversation Not Found"
          description={error instanceof Error ? error.message : 'You do not have access to this conversation.'}
          action={
            <Link
              to="/conversations"
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition inline-block"
            >
              Back to Conversations
            </Link>
          }
        />
      </div>
    );
  }

  const isInitiator = conversation.initiator_id === user?.id;
  const isTarget = conversation.target_id === user?.id;
  const isInvited = conversation.status === 'INVITED';
  const isActive = conversation.status === 'ACTIVE';
  const isConcluded = conversation.status === 'COMPLETED' || conversation.status === 'CANCELLED' || conversation.status === 'EXPIRED';
  const turnCount = messages.length;

  const handleBroadcastRfq = async () => {
    if (!conversationId) return;
    try {
      setIsBroadcastingRfq(true);
      const ask = await quoteApi.broadcastAskFromConversation(conversationId);
      setQuoteToast(`Procurement ask "${ask.title}" broadcasted to matching vendors! Check the Quotes Hub.`);
      queryClient.invalidateQueries({ queryKey: ['vendor-quotes-panel'] });
      queryClient.invalidateQueries({ queryKey: ['quotes'] });
      queryClient.invalidateQueries({ queryKey: ['quote-pending-count'] });
    } catch (err: any) {
      alert(err.message || 'Failed to broadcast procurement ask.');
    } finally {
      setIsBroadcastingRfq(false);
    }
  };

  const handleDirectQuoteSuccess = (res: SendQuoteEmailResponse) => {
    setIsSendQuoteModalOpen(false);
    setQuoteToast(`Commercial quotation ${res.quote_reference_number} dispatched to ${res.recipient_email}!`);
    queryClient.invalidateQueries({ queryKey: ['conversation', conversationId] });
    queryClient.invalidateQueries({ queryKey: ['vendor-quotes-panel'] });
    queryClient.invalidateQueries({ queryKey: ['quotes'] });
    queryClient.invalidateQueries({ queryKey: ['quote-pending-count'] });
  };

  const directQuoteAskItem = {
    match_id: '',
    quote_request_id: conversationId || '',
    title: conversation?.business_context?.product_name
      ? `Procurement Inquiry: ${conversation.business_context.product_name}`
      : 'Commercial Quotation',
    product_name: conversation?.business_context?.product_name || 'Limestone Calcined Clay Cement (LC3)',
    product_code: conversation?.business_context?.product_code,
    quantity: conversation?.business_context?.quantity || 1000,
    quantity_unit: conversation?.business_context?.unit || 'MT',
    delivery_location: conversation?.business_context?.delivery_location || 'Pune Industrial Yard',
    timeline_days: conversation?.business_context?.timeline_days || 18,
    currency: 'INR',
    customer: {
      id: conversation?.initiator_id === user?.id ? conversation?.target_id : conversation?.initiator_id,
      full_name: conversation?.other_participant_name || 'Customer Delegate',
      company_name: (conversation as any)?.other_participant_company || 'Buyer Organization',
      email: '',
    },
  };

  return (
    <div className="w-full max-w-7xl mx-auto h-full flex flex-col min-h-0">
      <div className="lg:grid lg:grid-cols-12 gap-3 flex-1 min-h-0 h-full">
        {/* Desktop Left Sidebar: Partner Card, Turn Quota & Quick Actions */}
        <aside className="lg:col-span-4 xl:col-span-3 hidden lg:flex flex-col gap-3 overflow-y-auto pr-1 h-full min-h-0">
          {/* Partner Identity Card */}
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-xs space-y-4">
            <div className="flex items-start gap-3.5">
              <div className="w-12 h-12 rounded-full bg-brass/10 border border-brass/20 text-brass flex items-center justify-center font-bold text-lg shrink-0">
                {(conversation.other_participant_name || 'Participant').charAt(0).toUpperCase()}
              </div>
              <div className="min-w-0">
                <h3 className="font-bold text-slate-900 dark:text-white text-base truncate">
                  Attendee Profile
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Connected with {conversation.other_participant_name || 'Participant'}
                </p>
                <div className="mt-1">
                  <StatusBadge
                    label={conversation.status}
                    variant={
                      conversation.status === 'ACTIVE'
                        ? 'success'
                        : conversation.status === 'INVITED'
                        ? 'warning'
                        : 'neutral'
                    }
                  />
                </div>
              </div>
            </div>

            {/* Mood preference */}
            {conversation.other_participant_mood && (
              <div className="p-2.5 rounded-lg bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-900/40 text-xs">
                <span className="text-[10px] uppercase font-mono text-amber-700 dark:text-amber-400 block mb-0.5">
                  Declared Mood
                </span>
                <span className="font-semibold text-amber-900 dark:text-amber-200">
                  ✨ "{conversation.other_participant_mood}"
                </span>
              </div>
            )}

            {/* Turn limit counter */}
            <div className="p-3 bg-slate-50 dark:bg-slate-850 rounded-lg border border-slate-200 dark:border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Turn Quota</span>
                <span className="font-mono font-bold text-slate-900 dark:text-white">
                  {turnCount} / 30
                </span>
              </div>
              <div className="w-full bg-slate-200 dark:bg-slate-700 h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    turnCount >= 30 ? 'bg-rose-500' : turnCount >= 22 ? 'bg-amber-500' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${Math.min(100, (turnCount / 30) * 100)}%` }}
                />
              </div>
              <p className="text-[10px] text-slate-400">
                {30 - turnCount > 0 ? `${30 - turnCount} turns remaining` : 'Turn boundary reached'}
              </p>
            </div>

            {/* Connection Information */}
            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2 text-xs text-slate-500 dark:text-slate-400">
              <span className="text-[10px] uppercase font-mono text-slate-400 block font-semibold">
                Dialogue Information
              </span>
              <ul className="space-y-1.5 text-[11px] leading-relaxed">
                <li className="flex items-start gap-1.5">
                  <span className="text-purple-600">🤖</span>
                  <span>Autonomous AI representative exchange.</span>
                </li>
                <li className="flex items-start gap-1.5">
                  <span className="text-indigo-600">🔒</span>
                  <span>Consent-preserving direct messaging up to 30 total turns.</span>
                </li>
              </ul>
            </div>

            {/* Commercial Context Sidebar Badge (Phase 4 / GAP-06) */}
            {conversation.business_context && (
              <div className="p-3 bg-amber-50/60 dark:bg-amber-950/20 rounded-lg border border-amber-200/60 dark:border-amber-900/40 space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-amber-900 dark:text-amber-200 text-[11px]">
                    Commercial Brief v{conversation.business_context.version}
                  </span>
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-200 border border-emerald-200 dark:border-emerald-800 font-bold">
                    VERIFIED
                  </span>
                </div>
                <p className="text-slate-800 dark:text-slate-200 text-[11px] font-medium truncate">
                  {conversation.business_context.product_name}
                </p>
                <p className="text-slate-500 dark:text-slate-400 text-[10px] font-mono truncate" title={conversation.business_context.snapshot_hash}>
                  SHA-256: {conversation.business_context.snapshot_hash.slice(0, 12)}...
                </p>
              </div>
            )}
          </div>
        </aside>

        {/* Main Chat Stream & Input Area */}
        <div className="col-span-12 lg:col-span-8 xl:col-span-9 flex flex-col h-full min-h-0 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs overflow-hidden">
          {/* Top Bar: Compact & Responsive */}
          <div className="border-b border-slate-200 dark:border-slate-800 p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-3 bg-white dark:bg-slate-900 flex-shrink-0">
            <div className="flex items-center gap-2.5 sm:gap-3">
              <Link
                to="/conversations"
                className="p-1 sm:p-1.5 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition"
                title="Back to Conversations"
              >
                ←
              </Link>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-bold text-slate-900 dark:text-white text-base sm:text-lg leading-tight">
                    {conversation.other_participant_name || 'Participant'}
                  </h2>
                  <StatusBadge
                    label={conversation.status}
                    variant={
                      conversation.status === 'ACTIVE'
                        ? 'success'
                        : conversation.status === 'INVITED'
                        ? 'warning'
                        : 'neutral'
                    }
                  />
                </div>
                <div className="flex items-center gap-2 text-[11px] sm:text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  <span>{turnCount} / 30 turns used</span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        wsStatus === 'connected'
                          ? 'bg-emerald-500'
                          : wsStatus === 'connecting'
                          ? 'bg-amber-500 animate-pulse'
                          : 'bg-rose-500'
                      }`}
                    />
                    {wsStatus === 'connected' ? 'Live' : wsStatus === 'connecting' ? 'Connecting...' : 'Offline'}
                  </span>
                </div>
              </div>
            </div>

            {/* Mobile / Tablet Action Controls */}
            <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
              {otherBrochure && (
                <Link
                  to={`/brochures/${otherBrochure.slug}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1.5 bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 rounded-lg text-xs font-bold transition flex items-center gap-1 shadow-2xs shrink-0"
                  title={`View ${otherBrochure.company_name}'s Digital Brochure & Flipbook`}
                >
                  <span>📖</span>
                  <span className="hidden sm:inline">Partner Brochure ↗</span>
                </Link>
              )}
              {isInvited && isTarget && (
                <>
                  <button
                    onClick={() => acceptMutation.mutate(true)}
                    disabled={acceptMutation.isPending}
                    className="px-2.5 sm:px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition"
                  >
                    {acceptMutation.isPending ? 'Accepting...' : 'Accept Invite'}
                  </button>
                  <button
                    onClick={() => acceptMutation.mutate(true)}
                    disabled={acceptMutation.isPending}
                    className="px-2.5 sm:px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1"
                    title="Accept invitation and immediately launch virtual representative greeting"
                  >
                    <span>🤖</span>
                    <span>Accept & Start Exchange</span>
                  </button>
                  <button
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="px-2.5 sm:px-3 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-xs font-semibold transition"
                  >
                    Decline
                  </button>
                </>
              )}

              {isInvited && isInitiator && (
                <button
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                  className="px-2.5 sm:px-3 py-1.5 bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900 rounded-lg text-xs font-semibold transition"
                >
                  Cancel Invitation
                </button>
              )}

              {isActive && (
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                  {turnCount < 10 && (
                    <button
                      type="button"
                      onClick={() => triggerAgentMutation.mutate()}
                      disabled={triggerAgentMutation.isPending}
                      className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1"
                    >
                      <span className="shrink-0">🤖</span>
                      <span>
                        {triggerAgentMutation.isPending ? (
                          'Generating...'
                        ) : (
                          <>
                            <span className="hidden sm:inline">Trigger Representative Turn</span>
                            <span className="sm:hidden">Agent Turn</span>
                          </>
                        )}
                      </span>
                    </button>
                  )}
                  {isActive && (
                    <button
                      type="button"
                      onClick={() => setIsSendQuoteModalOpen(true)}
                      className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold transition text-center flex items-center gap-1 shadow-2xs"
                      title="Send formal commercial quotation via email directly to partner delegate"
                    >
                      <span className="shrink-0">✉️</span>
                      <span className="hidden sm:inline">Send Quote via Email</span>
                      <span className="sm:hidden">Send Quote</span>
                    </button>
                  )}
                  {isActive && (
                    <button
                      type="button"
                      onClick={handleBroadcastRfq}
                      disabled={isBroadcastingRfq}
                      className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-semibold transition text-center flex items-center gap-1 shadow-2xs"
                      title="Broadcast technical specifications to all qualified vendors across conference"
                    >
                      <span className="shrink-0">📢</span>
                      <span>
                        {isBroadcastingRfq ? (
                          'Broadcasting...'
                        ) : (
                          <>
                            <span className="hidden sm:inline">Broadcast RFQ</span>
                            <span className="sm:hidden">Broadcast</span>
                          </>
                        )}
                      </span>
                    </button>
                  )}
                  {isActive && (
                    <button
                      type="button"
                      onClick={() => setIsDraftProposalOpen(true)}
                      className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-brass text-white hover:bg-brass/90 rounded-lg text-xs font-semibold transition text-center flex items-center gap-1 shadow-2xs"
                      title="Initiate binding commercial contract proposal"
                    >
                      <span className="shrink-0">🤝</span>
                      <span className="hidden sm:inline">Draft Proposal</span>
                      <span className="sm:hidden">Proposal</span>
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => setShowConcludeModal(true)}
                    disabled={concludeMutation.isPending}
                    className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800 rounded-lg text-xs font-semibold transition text-center"
                  >
                    Conclude
                  </button>
                  <button
                    type="button"
                    onClick={() => cancelMutation.mutate()}
                    disabled={cancelMutation.isPending}
                    className="whitespace-nowrap shrink-0 px-2 sm:px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg text-xs font-semibold transition text-center"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Quote Toast Notification */}
          {quoteToast && (
            <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border-b border-emerald-300 dark:border-emerald-700 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <span>✓</span>
                <span className="font-semibold">{quoteToast}</span>
              </div>
              <button
                type="button"
                onClick={() => setQuoteToast(null)}
                className="text-emerald-700 hover:text-emerald-900 dark:hover:text-emerald-100 text-xs"
              >
                ✕
              </button>
            </div>
          )}

          {/* Verified Commercial Brief Snapshot (Phase 4 / GAP-06) */}
          {conversation.business_context && (
            <div className="bg-amber-50/50 dark:bg-amber-950/20 border-b border-amber-200/70 dark:border-amber-900/40 flex-shrink-0 transition-all">
              {/* Sleek Summary Strip with Collapsible Toggle */}
              <div className="px-3 sm:px-4 py-2 flex flex-wrap items-center justify-between gap-2 text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-base shrink-0">📜</span>
                  <span className="font-bold text-slate-800 dark:text-slate-100 truncate">
                    Commercial Brief v{conversation.business_context.version}: {conversation.business_context.product_name}
                  </span>
                  {conversation.business_context.quantity != null && (
                    <span className="text-slate-600 dark:text-slate-300 hidden md:inline truncate">
                      ({conversation.business_context.quantity.toLocaleString()} {(conversation.business_context.unit || '').replace(/_/g, ' ')})
                    </span>
                  )}
                  {conversation.business_context.delivery_location && (
                    <span className="text-slate-500 dark:text-slate-400 hidden lg:inline">
                      → {conversation.business_context.delivery_location}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className="font-mono text-[10px] text-slate-500 dark:text-slate-400 hidden sm:inline px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 cursor-help"
                    title={`Full Cryptographic SHA-256 Digest: ${conversation.business_context.snapshot_hash}`}
                  >
                    ✓ SHA-256: {conversation.business_context.snapshot_hash.slice(0, 8)}...
                  </span>
                  <button
                    type="button"
                    onClick={() => setIsBriefExpanded(!isBriefExpanded)}
                    className="text-xs font-semibold text-brass hover:underline flex items-center gap-0.5"
                  >
                    <span>{isBriefExpanded ? 'Hide Details ▴' : 'View Full Brief ▾'}</span>
                  </button>
                </div>
              </div>

              {/* Expanded Full Details */}
              {isBriefExpanded && (
                <div className="px-3 sm:px-4 pb-3 pt-1 max-h-[25vh] overflow-y-auto">
                  <div className="p-3 sm:p-3.5 rounded-xl bg-white dark:bg-slate-850 border border-amber-200/60 dark:border-amber-900/40 shadow-xs space-y-2.5">
                    {/* Brief Parameters Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 text-xs">
                      <div className="col-span-2">
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Product / Service</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.product_name}
                        </span>
                        {conversation.business_context.product_code && (
                          <span className="text-[10px] text-slate-500 block font-mono">
                            Code: {conversation.business_context.product_code}
                          </span>
                        )}
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Volume / Unit</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.quantity != null
                            ? `${conversation.business_context.quantity.toLocaleString()} ${(conversation.business_context.unit || 'Units').replace(/_/g, ' ')}`
                            : 'On Request'}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Destination</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.delivery_location || 'Not Specified'}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Timeline</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.timeline_days != null
                            ? `${conversation.business_context.timeline_days} Days`
                            : 'Standard'}
                        </span>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Urgency</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.urgency || 'Planned'}
                        </span>
                      </div>

                      <div className="col-span-2">
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Target Budget Indication</span>
                        <span className="font-semibold text-slate-900 dark:text-white">
                          {conversation.business_context.target_price_indication != null ? (
                            <span className="text-emerald-700 dark:text-emerald-300 font-bold">
                              ₹{conversation.business_context.target_price_indication.toLocaleString()} (Disclosed by Buyer)
                            </span>
                          ) : (
                            <span className="text-slate-400 dark:text-slate-500 font-normal italic">
                              🔒 Private Buyer Budget (Preserved)
                            </span>
                          )}
                        </span>
                      </div>
                    </div>

                    {/* Inquiry Notes */}
                    {conversation.business_context.inquiry_notes && (
                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800 text-xs">
                        <span className="text-[10px] text-slate-400 dark:text-slate-500 block uppercase font-mono">Inquiry Notes</span>
                        <p className="text-slate-700 dark:text-slate-300 mt-0.5 italic">
                          "{conversation.business_context.inquiry_notes}"
                        </p>
                      </div>
                    )}

                    {/* Recipient Pending Acceptance Banner */}
                    {isInvited && isTarget && (
                      <div className="mt-2.5 p-2.5 sm:p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="text-xs text-amber-950 dark:text-amber-200">
                          <span className="font-bold block">⚠️ Incoming Commercial RFQ Connection Request</span>
                          <span className="text-[11px] text-amber-800 dark:text-amber-300">
                            Inspect this verified brief before accepting. Accepting will open commercial negotiation and direct messaging.
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => acceptMutation.mutate(true)}
                            disabled={acceptMutation.isPending}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition"
                          >
                            {acceptMutation.isPending ? 'Accepting...' : 'Accept RFQ Connection'}
                          </button>
                          <button
                            type="button"
                            onClick={() => acceptMutation.mutate(true)}
                            disabled={acceptMutation.isPending}
                            className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-semibold shadow-xs transition flex items-center gap-1"
                            title="Accept and trigger representative negotiation"
                          >
                            <span>🤖</span>
                            <span>Accept & Start Exchange</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => cancelMutation.mutate()}
                            disabled={cancelMutation.isPending}
                            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-semibold transition"
                          >
                            Decline RFQ
                          </button>
                        </div>
                      </div>
                    )}

                    {/* Initiator Pending Status Banner */}
                    {isInvited && isInitiator && (
                      <div className="mt-2 p-2 rounded-lg bg-indigo-50/80 dark:bg-indigo-950/30 border border-indigo-200/60 dark:border-indigo-900/40 text-xs text-indigo-950 dark:text-indigo-200 flex items-center justify-between">
                        <span>⏳ Outgoing RFQ Brief delivered. Awaiting recipient review & acceptance.</span>
                        <button
                          type="button"
                          onClick={() => cancelMutation.mutate()}
                          disabled={cancelMutation.isPending}
                          className="text-rose-600 dark:text-rose-400 hover:underline font-semibold text-[11px]"
                        >
                          Cancel RFQ
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Partner Mood Preference Chip */}
          {(isActive || isConcluded) && conversation.other_participant_mood && (
            <div className="bg-amber-50/90 dark:bg-amber-950/30 border-b border-amber-200/70 dark:border-amber-900/40 px-3 sm:px-4 py-1.5 flex flex-wrap items-center justify-between gap-1 text-[11px] sm:text-xs text-amber-900 dark:text-amber-200 flex-shrink-0">
              <div className="flex items-center gap-1.5 sm:gap-2">
                <span className="text-xs sm:text-sm">✨</span>
                <span className="font-semibold text-amber-800 dark:text-amber-300">
                  {conversation.other_participant_name || 'Partner'}'s Conversation Preference:
                </span>
                <span className="px-1.5 sm:px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/50 text-amber-900 dark:text-amber-100 font-medium">
                  "{conversation.other_participant_mood}"
                </span>
              </div>
              <span className="text-[10px] text-amber-700 dark:text-amber-400 font-mono">
                Active preference
              </span>
            </div>
          )}

          {/* Agent Status Banner */}
          {isActive && (
            <div className="bg-slate-100/90 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 px-3 sm:px-4 py-1.5 flex items-center justify-between text-[11px] sm:text-xs text-slate-700 dark:text-slate-300 flex-shrink-0">
              <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
                <span className="inline-flex items-center justify-center w-4 h-4 sm:w-5 sm:h-5 rounded-full bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300 text-[10px] sm:text-xs shrink-0">
                  🤖
                </span>
                <span className="font-medium truncate">
                  {turnCount < 10
                    ? `Virtual Representatives are aligning parameters. You can listen in or type anytime to take over.`
                    : `Representative Alignment Complete • Open for direct delegate discussion.`}
                </span>
              </div>
            </div>
          )}

          {/* Invitation Pending Banner */}
          {isInvited && (
            <div className="bg-amber-50 dark:bg-amber-950/30 border-b border-amber-200 dark:border-amber-900/50 p-2 sm:p-2.5 text-xs text-amber-800 dark:text-amber-200 text-center flex-shrink-0">
              {isInitiator
                ? 'Invitation sent. Messages can be exchanged once your partner accepts.'
                : 'You have been invited to connect! Click "Accept Invite" above to start messaging.'}
            </div>
          )}

          {/* Concluded Banner */}
          {isConcluded && (
            <div className="bg-slate-100 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700 p-2 sm:p-2.5 text-xs text-slate-700 dark:text-slate-300 text-center flex-shrink-0">
              This conversation is {conversation.status.toLowerCase()} ({conversation.terminal_outcome || 'ended'}). No further messages can be sent.
            </div>
          )}

          {/* Active Commercial Proposals Strip */}
          {conversationProposals.length > 0 && (
            <div className="bg-canvas-surface border-b border-canvas-border p-2 sm:p-3 flex-shrink-0 max-h-[30vh] sm:max-h-[35vh] overflow-y-auto">
              <div className="max-w-3xl mx-auto space-y-2">
                {conversationProposals.map((prop) => (
                  <InChatProposalCard key={prop.id} proposal={prop} />
                ))}
              </div>
            </div>
          )}

          {/* Message Stream: Generous height on mobile and desktop */}
          <div className="flex-1 min-h-0 bg-slate-50 dark:bg-slate-950 p-3 sm:p-4 overflow-y-auto space-y-3">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-400 dark:text-slate-500">
                {isActive ? (
                  <>
                    <span className="text-3xl mb-2 animate-bounce">🤖</span>
                    <p className="text-sm font-semibold text-purple-700 dark:text-purple-300">
                      Virtual Representatives are initiating dialogue...
                    </p>
                    <p className="text-xs text-slate-500 mt-1">
                      {conversation?.business_context
                        ? 'Verifying procurement specifications, run-rate capacity, and compliance.'
                        : 'Exploring shared session interests and conference networking.'}
                    </p>
                  </>
                ) : (
                  <>
                    <span className="text-3xl mb-2">💬</span>
                    <p className="text-sm font-medium">No messages exchanged yet.</p>
                    <p className="text-xs mt-1">Start the dialogue by accepting the invitation!</p>
                  </>
                )}
              </div>
            ) : (
              messages.map((msg) => {
                const isMe = msg.sender_id === user?.id;
                const isAgent = msg.sender_type === 'AGENT';
                const speakerName = isMe ? (user?.full_name || 'You') : (conversation.other_participant_name || 'Participant');
                // const isLocation = msg.message_type === 'LOCATION' || !!msg.location_payload;

                if (isAgent) {
                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`max-w-[92%] sm:max-w-[78%] rounded-2xl p-3 sm:p-3.5 shadow-xs text-xs sm:text-sm break-words border ${
                          isMe
                            ? 'bg-purple-50/90 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800/70 text-slate-900 dark:text-slate-100 rounded-br-none'
                            : 'bg-emerald-50/90 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800/70 text-slate-900 dark:text-slate-100 rounded-bl-none'
                        }`}
                      >
                        {/* Agent Header Badge */}
                        <div className="flex items-center justify-between gap-2 mb-1.5 pb-1 border-b border-purple-200/50 dark:border-purple-800/50">
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs">🤖</span>
                            <span className="text-xs font-semibold text-purple-900 dark:text-purple-200">
                              {isMe ? 'My' : `${speakerName}'s`} Virtual Representative
                            </span>
                          </div>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-100 dark:bg-purple-900/60 text-purple-700 dark:text-purple-300">
                            Turn #{msg.turn_index + 1}
                          </span>
                        </div>

                        {renderFormattedContent(msg.content, false)}

                        <div className="flex items-center justify-end gap-1.5 mt-2 text-[10px] text-slate-500 dark:text-slate-400">
                          <span>Representative Dialogue</span>
                          <span>•</span>
                          <span>
                            {new Date(msg.created_at).toLocaleTimeString([], {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                }

                // Human Attendee Message
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isMe ? 'items-end' : 'items-start'}`}
                  >
                    <div
                      className={`max-w-[90%] sm:max-w-[75%] rounded-2xl p-3 sm:p-3.5 shadow-xs text-xs sm:text-sm break-words ${
                        isMe
                          ? 'bg-indigo-600 text-white rounded-br-none'
                          : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 rounded-bl-none'
                      }`}
                    >
                      <div className="flex items-center justify-end gap-2 mb-1">
                        <span className={`text-[10px] font-mono ${isMe ? 'text-indigo-200' : 'text-slate-400'}`}>
                          Turn #{msg.turn_index + 1}
                        </span>
                      </div>

                      {/* Location Card hidden for now - location kept in profile only */}
                      {renderFormattedContent(msg.content, isMe)}

                      <div className="flex items-center justify-end gap-1.5 mt-1.5 text-[10px]">
                        <span className={isMe ? 'text-indigo-200' : 'text-slate-400'}>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            {isActive && messages.length > 0 && messages.length < 10 && (
              <div className="flex items-center gap-2.5 p-2.5 sm:p-3 rounded-xl bg-purple-50/90 dark:bg-purple-950/40 border border-purple-200 dark:border-purple-800 text-xs text-purple-800 dark:text-purple-300 shadow-2xs">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-600 animate-ping shrink-0" />
                <span className="font-medium">
                  Virtual representative is drafting a response... You can type anytime to take over immediately.
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Message Input Box: With Location Sharing & Touch Optimization */}
          <div className="bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800 p-2.5 sm:p-3 shadow-xs flex-shrink-0">
            {sendError && (
              <div className="mb-2 p-2 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded text-rose-700 dark:text-rose-300 text-xs">
                {sendError}
              </div>
            )}

            <form onSubmit={handleSendMessage} className="flex gap-2 items-end">
              {myBrochure && myBrochure.is_published && myBrochure.pages.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    const brochureLink = `📖 Check out our official digital brochure & catalog: ${window.location.origin}/converge/brochures/${myBrochure.slug}`;
                    setContent((prev) => (prev ? `${prev}\n\n${brochureLink}` : brochureLink));
                  }}
                  disabled={!isActive || turnCount >= 30 || sendMutation.isPending}
                  className="p-2 sm:px-3 sm:py-2 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50/80 dark:bg-amber-950/40 hover:bg-amber-100 dark:hover:bg-amber-900/40 text-amber-900 dark:text-amber-200 text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 disabled:cursor-not-allowed shrink-0 h-[44px] sm:h-[48px]"
                  title="Insert your company's digital flipbook brochure into message"
                  data-testid="share-brochure-btn"
                >
                  <span className="text-sm" aria-hidden="true">📖</span>
                  <span className="hidden sm:inline">Brochure</span>
                </button>
              )}

              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!isActive || turnCount >= 30 || sendMutation.isPending}
                placeholder={
                  !isActive
                    ? 'Conversation must be active to send messages'
                    : turnCount >= 30
                    ? 'Turn limit reached (30/30)'
                    : 'Type a message... (Press Enter to send)'
                }
                rows={2}
                className="flex-1 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-lg p-2 sm:p-2.5 text-xs sm:text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
              />
              <button
                type="submit"
                disabled={!isActive || !content.trim() || turnCount >= 30 || sendMutation.isPending}
                className="px-4 sm:px-5 py-2 sm:py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-lg text-xs sm:text-sm shadow-xs transition flex items-center justify-center min-w-[60px] sm:min-w-[70px] h-[44px] sm:h-[48px]"
              >
                {sendMutation.isPending ? '...' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Location Picker Modal commented out for now - kept in profile only
      <LocationPickerModal
        isOpen={showLocationModal}
        onClose={() => setShowLocationModal(false)}
        onSendLocation={handleSendLocation}
        isSending={sendMutation.isPending}
      />
      */}

      {/* Conclude Dialog Modal */}
      {showConcludeModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 max-w-md w-full shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div>
              <h3 className="font-bold text-slate-900 dark:text-white text-base">
                Conclude Conversation
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Select how you would like to conclude this dialogue:
              </p>
            </div>

            <div className="space-y-2">
              <button
                type="button"
                onClick={() => {
                  setShowConcludeModal(false);
                  concludeMutation.mutate('PROPOSAL_GENERATED');
                }}
                disabled={concludeMutation.isPending}
                className="w-full text-left p-3 rounded-lg border border-indigo-200 dark:border-indigo-900/60 bg-indigo-50/60 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-indigo-900 dark:text-indigo-200">
                    🤝 Conclude with Proposal
                  </span>
                  <span className="text-[10px] font-mono text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900 px-1.5 py-0.5 rounded">
                    72h Cooldown
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 mt-1">
                  You reached alignment on a formal meeting or collaboration outcome.
                </p>
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowConcludeModal(false);
                  concludeMutation.mutate('COMPLETED_WITHOUT_PROPOSAL');
                }}
                disabled={concludeMutation.isPending}
                className="w-full text-left p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-xs text-slate-800 dark:text-slate-200">
                    💬 Conclude without Proposal
                  </span>
                  <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400 bg-slate-200 dark:slate-700 px-1.5 py-0.5 rounded">
                    48h Cooldown
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                  General discussion finished naturally without creating a formal proposal.
                </p>
              </button>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100 dark:border-slate-800">
              <button
                type="button"
                onClick={() => setShowConcludeModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Commercial Proposal Draft Modal */}
      {isDraftProposalOpen && conversation && (
        <ProposalDraftModal
          isOpen={isDraftProposalOpen}
          onClose={() => setIsDraftProposalOpen(false)}
          mode="initial_draft"
          conversationId={conversationId}
          recipientId={conversation.other_participant_id || undefined}
          recipientName={conversation.other_participant_name || undefined}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', conversationId] });
            queryClient.invalidateQueries({ queryKey: ['proposals'] });
            queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          }}
        />
      )}

      {/* Send Official Commercial Quote Modal */}
      {isSendQuoteModalOpen && conversation && (
        <SendQuoteEmailModal
          ask={directQuoteAskItem}
          conversationId={conversationId}
          onClose={() => setIsSendQuoteModalOpen(false)}
          onSuccess={handleDirectQuoteSuccess}
        />
      )}
    </div>
  );
};
