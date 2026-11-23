import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatroomApi } from '@/lib/api/chatroom';
import { conversationApi } from '@/lib/api/conversation';
import { brochureApi } from '@/lib/api/brochures';
import { getConferences } from '@/lib/api/agenda';
import { useAuth } from '@/lib/auth/AuthContext';
import { ChatroomMessage } from '@/types/chatroom';

const AVATAR_PALETTES = [
  { bg: 'from-blue-600 to-indigo-700', text: 'text-white', border: 'border-blue-400', ring: 'ring-blue-400/30' },
  { bg: 'from-emerald-600 to-teal-700', text: 'text-white', border: 'border-emerald-400', ring: 'ring-emerald-400/30' },
  { bg: 'from-amber-600 to-orange-700', text: 'text-white', border: 'border-amber-400', ring: 'ring-amber-400/30' },
  { bg: 'from-purple-600 to-pink-700', text: 'text-white', border: 'border-purple-400', ring: 'ring-purple-400/30' },
  { bg: 'from-rose-600 to-red-700', text: 'text-white', border: 'border-rose-400', ring: 'ring-rose-400/30' },
  { bg: 'from-cyan-600 to-sky-700', text: 'text-white', border: 'border-cyan-400', ring: 'ring-cyan-400/30' },
  { bg: 'from-violet-600 to-purple-800', text: 'text-white', border: 'border-violet-400', ring: 'ring-violet-400/30' },
];

function getAvatarPalette(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % AVATAR_PALETTES.length;
  return AVATAR_PALETTES[index];
}

function getInitials(name: string) {
  const clean = name.replace(/'s Representative/gi, '').replace(/\(.*\)/g, '').trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return (clean[0] || 'A').toUpperCase();
}

const AgentAvatar: React.FC<{
  name: string;
  isBot?: boolean;
  isHost?: boolean;
  size?: 'sm' | 'md' | 'lg';
  onClick?: () => void;
}> = ({ name, isBot, isHost, size = 'md', onClick }) => {
  const palette = getAvatarPalette(name);
  const initials = getInitials(name);
  const sizeClasses =
    size === 'sm'
      ? 'w-8 h-8 text-xs'
      : size === 'lg'
      ? 'w-14 h-14 text-base sm:text-lg'
      : 'w-9 h-9 sm:w-10 sm:h-10 text-xs sm:text-sm';

  if (isHost) {
    return (
      <div
        onClick={onClick}
        className={`${sizeClasses} rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 text-white font-bold flex items-center justify-center shrink-0 shadow-md ring-2 ring-amber-400/40 relative select-none ${
          onClick ? 'cursor-pointer hover:scale-105 transition-transform' : ''
        }`}
        title="Virtual Lounge Host"
      >
        <span>🎙️</span>
        <span className="absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 border-2 border-white dark:border-slate-900 animate-pulse shadow-2xs" />
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`${sizeClasses} rounded-2xl bg-gradient-to-br ${palette.bg} ${palette.text} font-bold flex items-center justify-center shrink-0 shadow-md ring-2 ${
        palette.ring
      } relative select-none ${onClick ? 'cursor-pointer hover:scale-105 transition-transform' : ''}`}
      title={name}
    >
      <span>{initials}</span>
      {isBot && (
        <span
          className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-violet-900 border border-violet-400 text-violet-100 flex items-center justify-center text-[9px] shadow-xs"
          title="Delegate AI Representative"
        >
          ⚡
        </span>
      )}
    </div>
  );
};

const STARTER_PROMPTS = [
  '☕ Who is grabbing tea at the counter right now?',
  '🎙️ What was your biggest takeaway from the keynote?',
  '🍪 Did anyone try the fresh cookies at the central foyer?',
  '🚗 How was the morning travel from the expressway corridors?',
  '🤝 Anyone sourcing fly ash, slag, or LC3 green binders?',
  '💡 Which session track are you heading to next?',
];

export const Lounge: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const conferenceId = searchParams.get('conference_id') || undefined;

  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isOnlineModalOpen, setIsOnlineModalOpen] = useState(false);
  const [selectedDelegate, setSelectedDelegate] = useState<{
    name: string;
    senderId?: string;
    isBot?: boolean;
    company?: string;
  } | null>(null);
  const [isInitiatingDm, setIsInitiatingDm] = useState(false);

  const [dmErrorMessage, setDmErrorMessage] = useState<string | null>(null);

  const { data: brochuresDirectory = [] } = useQuery({
    queryKey: ['brochuresDirectory'],
    queryFn: () => brochureApi.getDirectory(),
    staleTime: 60000,
  });

  const handleStartDirectMessage = async (targetId?: string) => {
    if (!targetId || targetId === user?.id) return;
    setIsInitiatingDm(true);
    setDmErrorMessage(null);
    try {
      const conv = await conversationApi.initiateConversation(targetId, null, true);
      setSelectedDelegate(null);
      setIsOnlineModalOpen(false);
      navigate(`/conversations/${conv.id}`);
    } catch (err: any) {
      if (err?.status === 403) {
        setDmErrorMessage(err?.detail || 'This delegate has disabled AI Representative 1-on-1 DMs in their privacy settings.');
      } else if (err?.status === 409) {
        setSelectedDelegate(null);
        setIsOnlineModalOpen(false);
        navigate('/conversations');
      } else {
        setSelectedDelegate(null);
        setIsOnlineModalOpen(false);
        navigate('/conversations');
      }
    } finally {
      setIsInitiatingDm(false);
    }
  };

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // 1. Fetch available conferences to allow conference-scoped navigation
  const { data: conferences } = useQuery({
    queryKey: ['activeConferencesList'],
    queryFn: () => getConferences({ is_active: true }),
    staleTime: 60000,
  });

  // 2. Fetch Conference-Wise Lounge state & context
  const {
    data: lounge,
    isLoading,
    isError,
    refetch: refetchLounge,
  } = useQuery({
    queryKey: ['activeLounge', conferenceId],
    queryFn: () => chatroomApi.getActiveLounge(conferenceId),
    refetchOnWindowFocus: true,
  });

  // 3. Poll messages periodically (every 5 seconds) for real-time human chat
  const { data: messages } = useQuery({
    queryKey: ['chatroomMessages', lounge?.id],
    queryFn: () => (lounge ? chatroomApi.getRecentMessages(lounge.id, 60) : Promise.resolve([])),
    enabled: !!lounge?.id,
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
  });

  // 3.5 Fetch online users in lounge
  const { data: onlineUsers, isLoading: isLoadingOnline } = useQuery({
    queryKey: ['onlineUsers', lounge?.id],
    queryFn: () => (lounge?.id ? chatroomApi.getOnlineUsers(lounge.id) : Promise.resolve([])),
    enabled: !!lounge?.id && isOnlineModalOpen,
    refetchInterval: isOnlineModalOpen ? 5000 : false,
  });

  // 4. Continuous ambient dialogue trigger (every 25 seconds for natural pacing)
  useEffect(() => {
    if (!lounge?.id) return;

    const interval = setInterval(async () => {
      try {
        const res = await chatroomApi.pollAmbientTick(lounge.id);
        if (res.message_generated) {
          queryClient.invalidateQueries({ queryKey: ['chatroomMessages', lounge.id] });
        }
      } catch (err) {
        // Silently skip failed ambient poll
      }
    }, 25000);

    return () => clearInterval(interval);
  }, [lounge?.id, queryClient]);

  // 5. Auto-scroll on new messages
  const messageList = messages || lounge?.recent_messages || [];
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messageList.length]);

  // 6. Send user message mutation
  const sendMessageMutation = useMutation({
    mutationFn: (content: string) => chatroomApi.postMessage(lounge!.id, content),
    onSuccess: (newMsg) => {
      setInputText('');
      queryClient.setQueryData<ChatroomMessage[]>(['chatroomMessages', lounge?.id], (old) => [
        ...(old || []),
        newMsg,
      ]);
      queryClient.invalidateQueries({ queryKey: ['chatroomMessages', lounge?.id] });
    },
    onSettled: () => {
      setIsSending(false);
    },
  });

  const handleSendMessage = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || isSending || !lounge?.id) return;
    setIsSending(true);
    sendMessageMutation.mutate(inputText.trim());
  };

  const handleChipClick = (prompt: string) => {
    setInputText(prompt);
  };

  const handleConferenceChange = (newConfId: string) => {
    if (newConfId) {
      setSearchParams({ conference_id: newConfId });
    } else {
      setSearchParams({});
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <div className="w-10 h-10 border-4 border-amber-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-medium text-ink-muted">Stepping into the Networking Lounge...</p>
      </div>
    );
  }

  if (isError || !lounge) {
    return (
      <div className="max-w-2xl mx-auto my-12 p-8 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900 rounded-xl text-center">
        <h2 className="text-lg font-bold text-red-800 dark:text-red-300">Unable to join Lounge</h2>
        <p className="text-sm text-red-600 dark:text-red-400 mt-2">
          Could not load the conference networking lounge. Please verify your connection.
        </p>
        <button
          onClick={() => refetchLounge()}
          className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg shadow-xs"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { context } = lounge;
  const weather = context?.weather;
  const traffic = context?.traffic;

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 py-6 flex flex-col h-[calc(100vh-6rem)] min-h-[620px]">
      {/* 1. Lounge Hero Banner (Fun place to connect) */}
      <div className="bg-gradient-to-r from-amber-50 via-orange-50 to-amber-100 dark:from-stone-900 dark:via-amber-950/40 dark:to-stone-900 border border-amber-200/80 dark:border-amber-800/60 rounded-2xl p-4 sm:p-5 shadow-sm mb-4 shrink-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-2xl shadow-inner shrink-0">
              ☕
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-serif font-bold text-ink-primary">
                  {lounge.name}
                </h1>
                {lounge.is_active ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Live Chatroom
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-stone-200 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-300 dark:border-stone-700">
                    <span className="w-2 h-2 rounded-full bg-stone-500" />
                    Lounge Closed
                  </span>
                )}
              </div>
              <p className="text-xs sm:text-sm text-ink-secondary mt-0.5">
                A casual, open town square for all conference delegates to connect, share thoughts & stay updated!
              </p>
            </div>
          </div>

          {/* Environmental Context & Conference Selector */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
            {/* Conference Selector Dropdown if multiple exist */}
            {conferences && conferences.length > 1 && (
              <select
                value={lounge.conference_id || conferenceId || ''}
                onChange={(e) => handleConferenceChange(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-white/90 dark:bg-stone-800/90 border border-amber-300 dark:border-stone-700 text-ink-primary text-xs font-semibold shadow-2xs focus:outline-hidden focus:border-amber-500"
                title="Switch Conference Lounge"
              >
                {conferences.map((c) => (
                  <option key={c.id} value={c.id}>
                    📍 {c.title} ({c.city || 'Venue'})
                  </option>
                ))}
              </select>
            )}

            {/* Live Presence Button */}
            <button
              type="button"
              onClick={() => setIsOnlineModalOpen(true)}
              className="px-3 py-1.5 rounded-lg bg-white/80 hover:bg-amber-100/70 dark:bg-stone-800/80 dark:hover:bg-stone-700 border border-amber-200 hover:border-amber-400 dark:border-stone-700 text-ink-primary flex items-center gap-1.5 shadow-2xs cursor-pointer transition-all hover:scale-105"
              title="Click to view online delegates and message 1-on-1"
            >
              <span>👥</span>
              <span>
                <strong>{lounge.online_count}</strong> online
              </span>
              <span className="text-[10px] text-amber-700 dark:text-amber-300 font-bold ml-0.5">▼</span>
            </button>

            {/* Conference Day Badge */}
            {context?.active_day && (
              <div
                className="px-3 py-1.5 rounded-lg bg-brass/15 dark:bg-brass/25 border border-brass/40 text-brass font-bold flex items-center gap-1.5 shadow-2xs"
                title={`Active Conference Day ${context.active_day}`}
              >
                <span>📅</span>
                <span>Day {context.active_day}</span>
              </div>
            )}

            {/* Weather Pill */}
            {weather && (
              <div
                className="px-3 py-1.5 rounded-lg bg-white/80 dark:bg-stone-800/80 border border-amber-200 dark:border-stone-700 text-ink-primary flex items-center gap-1.5 shadow-2xs"
                title={weather.summary}
              >
                <span>{weather.is_rainy ? '🌧️' : '☀️'}</span>
                <span>
                  {weather.temperature_c}°C {weather.condition}
                </span>
              </div>
            )}

            {/* Traffic Pill */}
            {traffic && (
              <div
                className="px-3 py-1.5 rounded-lg bg-white/80 dark:bg-stone-800/80 border border-amber-200 dark:border-stone-700 text-ink-primary flex items-center gap-1.5 shadow-2xs"
                title={traffic.summary}
              >
                <span>🚗</span>
                <span>
                  {traffic.congestion_level === 'NORMAL' ? (
                    <span className="text-emerald-700 dark:text-emerald-400">Traffic Normal</span>
                  ) : (
                    <span className="text-amber-700 dark:text-amber-400">
                      +{traffic.delay_mins}m Slowdown
                    </span>
                  )}
                </span>
              </div>
            )}

            {/* Active Break Banner Pill */}
            {context?.active_break && (
              <div className="px-3 py-1.5 rounded-lg bg-amber-500 text-white font-semibold flex items-center gap-1.5 shadow-xs">
                <span>☕</span>
                <span>{context.active_break.replace('_', ' ')}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pinned General Summit Announcement / Live Bulletin */}
      {context?.general_announcement && (
        <div
          className={`rounded-xl px-4 py-3 shadow-xs mb-3 flex items-center justify-between gap-3 shrink-0 animate-in fade-in border transition-all ${
            context.announcement_criticality === 'CRITICAL'
              ? 'bg-rose-50/95 dark:bg-rose-950/60 border-rose-300 dark:border-rose-700 shadow-rose-200/50 dark:shadow-rose-950/50 ring-1 ring-rose-400/30'
              : 'bg-indigo-50/90 dark:bg-indigo-950/50 border-indigo-200 dark:border-indigo-800'
          }`}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <span className={`text-xl shrink-0 ${context.announcement_criticality === 'CRITICAL' ? 'animate-pulse' : ''}`}>
              {context.announcement_criticality === 'CRITICAL' ? '🚨' : '📢'}
            </span>
            <div className="min-w-0">
              <span
                className={`text-[10px] uppercase tracking-wider block ${
                  context.announcement_criticality === 'CRITICAL'
                    ? 'text-rose-700 dark:text-rose-400 font-extrabold'
                    : 'text-indigo-700 dark:text-indigo-400 font-bold'
                }`}
              >
                {context.announcement_criticality === 'CRITICAL' ? '⚠️ Critical Safety Advisory' : 'Live Summit Bulletin'}
              </span>
              <p
                className={`text-xs sm:text-sm truncate sm:whitespace-normal ${
                  context.announcement_criticality === 'CRITICAL'
                    ? 'text-rose-950 dark:text-rose-100 font-bold'
                    : 'text-ink-primary font-semibold'
                }`}
              >
                {context.general_announcement}
              </p>
            </div>
          </div>
          <span
            className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-bold border ${
              context.announcement_criticality === 'CRITICAL'
                ? 'bg-rose-600 text-white border-rose-700 animate-pulse shadow-xs'
                : 'bg-indigo-100 dark:bg-indigo-900/60 text-indigo-800 dark:text-indigo-200 border-indigo-300 dark:border-indigo-700'
            }`}
          >
            {context.announcement_criticality === 'CRITICAL' ? 'Urgent Alert' : 'Active Notice'}
          </span>
        </div>
      )}

      {/* 2. Chat Feed Area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto p-4 sm:p-5 rounded-2xl bg-canvas-surface border border-canvas-border shadow-xs space-y-3.5 mb-3"
      >
        {messageList.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center p-6 text-ink-muted">
            <div className="text-3xl mb-2">☕</div>
            <p className="font-medium text-sm">The lounge is open and ready!</p>
            <p className="text-xs mt-1">Say hello or share what track you are most excited about today.</p>
          </div>
        ) : (
          messageList.map((msg) => {
            const isMe = msg.sender_id === user?.id && msg.sender_type === 'USER';
            const isHost = msg.sender_type === 'HOST';
            const isBot = msg.sender_type === 'REPRESENTATIVE';
            const isAnnouncement =
              isHost ||
              (['ANNOUNCEMENT', 'TRAFFIC_ALERT', 'WEATHER_UPDATE', 'TEA_ANNOUNCEMENT'].includes(msg.message_kind) &&
                !isBot);
            const isCommercialHandoff = msg.content.startsWith('🔒');

            // Special Card: Host Announcements / Traffic / Weather / Welcome
            if (isAnnouncement) {
              let cardBg =
                'bg-amber-50/80 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900/60 text-amber-900 dark:text-amber-200';
              let icon = '📢';

              if (msg.message_kind === 'WELCOME') {
                cardBg =
                  'bg-purple-50/70 dark:bg-purple-950/20 border-purple-200 dark:border-purple-900/50 text-purple-900 dark:text-purple-200';
                icon = '👋';
              } else if (msg.message_kind === 'TRAFFIC_ALERT') {
                cardBg =
                  'bg-blue-50/70 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900/50 text-blue-900 dark:text-blue-200';
                icon = '🚗';
              } else if (msg.message_kind === 'WEATHER_UPDATE') {
                cardBg =
                  'bg-emerald-50/70 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-900/50 text-emerald-900 dark:text-emerald-200';
                icon = '🌤️';
              } else if (msg.message_kind === 'TEA_ANNOUNCEMENT') {
                cardBg =
                  'bg-amber-100/60 dark:bg-amber-950/30 border-amber-300 dark:border-amber-800 text-amber-950 dark:text-amber-100';
                icon = '☕';
              }

              return (
                <div
                  key={msg.id}
                  className={`p-3 sm:p-4 rounded-xl border flex items-start gap-3 text-xs leading-relaxed ${cardBg}`}
                >
                  <AgentAvatar name={msg.sender_name} isHost={true} size="sm" />
                  <div className="flex-1">
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="font-bold text-xs uppercase tracking-wider opacity-90 flex items-center gap-1.5">
                        <span>{icon}</span>
                        <span>{msg.sender_name}</span>
                      </span>
                      <span className="text-[10px] opacity-60">
                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              );
            }

            // Representative Message (Delegate AI Avatar)
            if (isBot) {
              return (
                <div key={msg.id} className="flex items-start gap-2.5 max-w-2xl">
                  <AgentAvatar
                    name={msg.sender_name}
                    isBot={true}
                    size="md"
                    onClick={() =>
                      setSelectedDelegate({
                        name: msg.sender_name,
                        senderId: msg.sender_id || undefined,
                        isBot: true,
                      })
                    }
                  />
                  <div className="flex-1 bg-canvas-elevated border border-canvas-border rounded-2xl rounded-tl-sm p-3 sm:p-3.5 shadow-2xs">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <button
                          type="button"
                          onClick={() =>
                            setSelectedDelegate({
                              name: msg.sender_name,
                              senderId: msg.sender_id || undefined,
                              isBot: true,
                            })
                          }
                          className="text-xs font-bold text-violet-700 dark:text-violet-400 hover:underline flex items-center gap-1 text-left"
                        >
                          {msg.sender_name}
                        </button>
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-normal bg-violet-100 dark:bg-violet-950 text-violet-700 dark:text-violet-300 border border-violet-200 dark:border-violet-800 flex items-center gap-1">
                          ⚡ AI Representative
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {msg.sender_id && msg.sender_id !== user?.id && (
                          <button
                            type="button"
                            onClick={() => handleStartDirectMessage(msg.sender_id || undefined)}
                            className="text-[11px] font-medium text-amber-700 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 hover:underline flex items-center gap-1 shrink-0"
                            title="Start private 1-on-1 dialogue"
                          >
                            <span>💬 Message 1-on-1</span>
                          </button>
                        )}
                        <span className="text-[10px] text-ink-muted shrink-0">
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs sm:text-sm text-ink-primary leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </p>
                    {isCommercialHandoff && (
                      <div className="mt-2.5 pt-2 border-t border-canvas-border flex items-center justify-between gap-2">
                        <span className="text-[11px] font-medium text-amber-800 dark:text-amber-300 flex items-center gap-1">
                          🔒 Commercial Quotation Transferred
                        </span>
                        <button
                          type="button"
                          onClick={() => navigate('/conversations')}
                          className="px-2.5 py-1 text-[11px] font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded-lg shadow-2xs transition-colors flex items-center gap-1"
                        >
                          <span>Open in Messages</span>
                          <span>↗</span>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            }

            // Human Attendee Message
            return (
              <div
                key={msg.id}
                className={`flex items-start gap-2.5 max-w-2xl ${
                  isMe ? 'ml-auto flex-row-reverse' : 'mr-auto'
                }`}
              >
                <AgentAvatar
                  name={isMe ? (user?.full_name || 'You') : msg.sender_name}
                  size="md"
                  onClick={() =>
                    !isMe &&
                    setSelectedDelegate({
                      name: msg.sender_name,
                      senderId: msg.sender_id || undefined,
                      isBot: false,
                    })
                  }
                />
                <div className={`flex flex-col ${isMe ? 'items-end' : 'items-start'} flex-1`}>
                  <div className="flex items-center gap-1.5 mb-1 px-1 text-[11px] text-ink-muted">
                    <span className="font-semibold text-ink-secondary">
                      {isMe ? 'You' : msg.sender_name}
                    </span>
                    <span>•</span>
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <div
                    className={`p-3 sm:p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed shadow-2xs whitespace-pre-wrap ${
                      isMe
                        ? 'bg-amber-600 dark:bg-amber-700 text-white rounded-tr-sm'
                        : 'bg-canvas-elevated text-ink-primary border border-canvas-border rounded-tl-sm'
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 2.5 Lounge Closed Banner */}
      {!lounge.is_active && (
        <div className="mb-3 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-3 text-amber-900 dark:text-amber-200 text-xs sm:text-sm font-medium shrink-0 shadow-2xs">
          <span className="text-xl">🛑</span>
          <div>
            <span className="font-bold">The Live Networking Lounge is currently closed.</span>
            <span className="text-xs opacity-90 block">
              The organizer will reopen the floor during upcoming breaks or session tracks. Ambient messages and chat inputs are paused.
            </span>
          </div>
        </div>
      )}

      {/* 3. Quick Conversation Starter Chips */}
      <div className="mb-2.5 overflow-x-auto pb-1 flex items-center gap-1.5 shrink-0">
        <span className="text-[11px] font-bold text-ink-muted uppercase tracking-wider shrink-0 mr-1">
          💡 Jump in:
        </span>
        {STARTER_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            type="button"
            disabled={!lounge.is_active}
            onClick={() => handleChipClick(prompt)}
            className="px-2.5 py-1 rounded-full text-xs bg-canvas-elevated hover:bg-amber-100/60 dark:hover:bg-amber-950/40 border border-canvas-border hover:border-amber-300 dark:hover:border-amber-800 text-ink-secondary hover:text-amber-800 dark:hover:text-amber-300 whitespace-nowrap transition-colors shadow-2xs"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* 4. Chat Input Form */}
      <form onSubmit={handleSendMessage} className="flex items-center gap-2 shrink-0">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={
            lounge.is_active
              ? "Share a thought, say hi, or reply to fellow delegates..."
              : "Lounge is closed by the organizer..."
          }
          className="flex-1 px-4 py-2.5 rounded-xl border border-canvas-border bg-canvas-surface focus:outline-hidden focus:ring-2 focus:ring-amber-500/30 focus:border-amber-500 text-sm text-ink-primary placeholder:text-ink-muted shadow-2xs disabled:opacity-50 disabled:bg-canvas-subtle"
          disabled={isSending || !lounge.is_active}
        />
        <button
          type="submit"
          disabled={!inputText.trim() || isSending || !lounge.is_active}
          className="px-5 py-2.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-sm font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1.5 shrink-0"
        >
          {isSending ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <span>Send</span>
              <span aria-hidden="true">💬</span>
            </>
          )}
        </button>
      </form>

      {/* 5. Delegate Profile & 1-on-1 Action Modal */}
      {selectedDelegate && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setSelectedDelegate(null)}
        >
          <div
            className="bg-canvas-surface border border-canvas-border rounded-2xl p-5 max-w-sm w-full shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3.5">
              <AgentAvatar
                name={selectedDelegate.name}
                isBot={selectedDelegate.isBot}
                size="lg"
              />
              <div className="min-w-0 flex-1">
                <h4 className="text-base font-bold text-ink-primary truncate">
                  {selectedDelegate.name}
                </h4>
                <p className="text-xs text-ink-muted">
                  {selectedDelegate.isBot ? 'Delegate AI Representative' : 'Conference Delegate'}
                </p>
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-medium">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Active in Summit Lounge</span>
                </div>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border text-xs text-ink-secondary space-y-1">
              <p className="font-medium text-ink-primary">1-on-1 Direct Networking</p>
              <p className="text-[11px] text-ink-muted leading-relaxed">
                Connect directly under Messages to discuss bilateral initiatives, schedule off-stage meetups, or request commercial quotations.
              </p>
            </div>

            {dmErrorMessage && (
              <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
                {dmErrorMessage}
              </div>
            )}

            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => {
                  setSelectedDelegate(null);
                  setDmErrorMessage(null);
                }}
                className="flex-1 py-2 rounded-xl border border-canvas-border text-xs font-semibold text-ink-secondary hover:bg-canvas-elevated transition-colors"
              >
                Close
              </button>
              {selectedDelegate.senderId && selectedDelegate.senderId !== user?.id && (
                <button
                  type="button"
                  disabled={isInitiatingDm}
                  onClick={() => handleStartDirectMessage(selectedDelegate.senderId)}
                  className="flex-1 py-2 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold shadow-xs transition-colors flex items-center justify-center gap-1.5"
                >
                  {isInitiatingDm ? (
                    <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <span>Message 1-on-1</span>
                      <span>💬</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 6. Online Delegates Modal */}
      {isOnlineModalOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4"
          onClick={() => setIsOnlineModalOpen(false)}
        >
          <div
            className="bg-canvas-surface border border-canvas-border rounded-2xl p-5 max-w-md w-full shadow-xl space-y-4 animate-in fade-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-canvas-border pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">👥</span>
                <div>
                  <h4 className="text-base font-bold text-ink-primary">
                    Online in Networking Lounge
                  </h4>
                  <p className="text-xs text-ink-muted">
                    {onlineUsers?.length || lounge.online_count} delegates currently active
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsOnlineModalOpen(false);
                  setDmErrorMessage(null);
                }}
                className="w-8 h-8 rounded-full flex items-center justify-center text-ink-muted hover:bg-canvas-elevated hover:text-ink-primary transition-colors"
              >
                ✕
              </button>
            </div>

            {dmErrorMessage && (
              <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-300">
                {dmErrorMessage}
              </div>
            )}

            <div className="max-h-72 overflow-y-auto space-y-2.5 pr-1">
              {isLoadingOnline ? (
                <div className="py-8 text-center text-xs text-ink-muted">Loading active delegates...</div>
              ) : !onlineUsers || onlineUsers.length === 0 ? (
                <div className="py-8 text-center text-xs text-ink-muted">No other delegates online right now.</div>
              ) : (
                onlineUsers.map((del) => (
                  <div
                    key={del.id}
                    className="p-3 rounded-xl bg-canvas-elevated border border-canvas-border flex items-center justify-between gap-3 shadow-2xs hover:border-amber-300 dark:hover:border-amber-700 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <AgentAvatar name={del.full_name} size="sm" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-xs font-bold text-ink-primary truncate">
                            {del.full_name}
                          </span>
                          {del.is_me && (
                            <span className="text-[10px] font-semibold text-ink-muted bg-stone-200 dark:bg-stone-700 px-1.5 py-0.2 rounded-full">
                              You
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <p className="text-[11px] text-ink-muted truncate">
                            {del.company_name}
                          </p>
                          {(() => {
                            const delBrochure = brochuresDirectory.find(
                              (b) =>
                                (del.company_name &&
                                  b.company_name.toLowerCase() === del.company_name.toLowerCase()) ||
                                (del.id && b.owner_user_id === del.id)
                            );
                            if (!delBrochure) return null;
                            return (
                              <Link
                                to={`/brochures/${delBrochure.slug}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors shrink-0"
                                title={`View ${delBrochure.title} (Digital Flipbook)`}
                              >
                                <span>📖</span>
                                <span>Brochure ↗</span>
                              </Link>
                            );
                          })()}
                        </div>
                      </div>
                    </div>

                    {!del.is_me && (
                      del.allow_agent_dm_initiation === false ? (
                        <span
                          className="px-2 py-1 bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 text-stone-500 text-[11px] font-medium rounded-lg cursor-not-allowed shrink-0"
                          title="Delegate has disabled 1-on-1 DMs in their profile privacy settings"
                        >
                          DMs Disabled 🔒
                        </span>
                      ) : (
                        <button
                          type="button"
                          disabled={isInitiatingDm}
                          onClick={() => handleStartDirectMessage(del.id)}
                          className="px-2.5 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors flex items-center gap-1 shrink-0"
                        >
                          <span>Message</span>
                          <span>💬</span>
                        </button>
                      )
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 border-t border-canvas-border flex items-center justify-end">
              <button
                type="button"
                onClick={() => setIsOnlineModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-canvas-border text-xs font-semibold text-ink-secondary hover:bg-canvas-elevated transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Lounge;
