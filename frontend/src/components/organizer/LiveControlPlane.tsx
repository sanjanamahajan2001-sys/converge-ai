import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { chatroomApi } from '@/lib/api/chatroom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getConferenceLiveState,
  setConferenceLiveState,
  resetConferenceLiveState,
  hostConferenceLounge,
  closeConferenceLounge,
  resetConferenceLounge,
  ConferenceLiveStateUpdatePayload,
} from '@/lib/api/organizer';

interface LiveControlPlaneProps {
  conferenceId: string;
  conferenceTitle: string;
}

export const LiveControlPlane: React.FC<LiveControlPlaneProps> = ({
  conferenceId,
  conferenceTitle,
}) => {
  const queryClient = useQueryClient();

  const [stateType, setStateType] = useState<string>('TEA_BREAK');
  const [breakType, setBreakType] = useState<string>('TEA_COFFEE');
  const [designatedLocation, setDesignatedLocation] = useState<string>('Central Concourse & Exhibition Foyer');
  const [durationMinutes, setDurationMinutes] = useState<number>(25);
  const [delayMinutes, setDelayMinutes] = useState<number | undefined>(undefined);
  const [weatherOverride, setWeatherOverride] = useState<string>('');
  const [announcementBanner, setAnnouncementBanner] = useState<string>('');
  const [criticality, setCriticality] = useState<'NORMAL' | 'CRITICAL'>('NORMAL');
  const [amenitiesNote, setAmenitiesNote] = useState<string>('');
  const [activeDay, setActiveDay] = useState<number | undefined>(undefined);

  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // 1. Fetch live temporal state
  const { data: liveState } = useQuery({
    queryKey: ['conference-live-state', conferenceId],
    queryFn: () => getConferenceLiveState(conferenceId),
    refetchInterval: 10000,
  });

  // Sync initial live state values when loaded
  React.useEffect(() => {
    if (liveState?.amenities_note && !amenitiesNote) {
      setAmenitiesNote(liveState.amenities_note);
    }
    if (liveState?.active_day !== undefined && activeDay === undefined) {
      setActiveDay(liveState.active_day);
    }
  }, [liveState?.amenities_note, liveState?.active_day]);

  const getErrorMessage = (err: any, fallback: string): string => {
    if (typeof err?.detail === 'string') return err.detail;
    if (Array.isArray(err?.detail)) {
      return err.detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ');
    }
    return err?.message || fallback;
  };

  // 2. Set live state mutation
  const setLiveStateMutation = useMutation({
    mutationFn: (payload: ConferenceLiveStateUpdatePayload) =>
      setConferenceLiveState(conferenceId, payload),
    onSuccess: (updated) => {
      queryClient.setQueryData(['conference-live-state', conferenceId], updated);
      queryClient.invalidateQueries({ queryKey: ['activeLounge'] });
      setFeedback({
        type: 'success',
        message: `Live State updated to ${updated.current_state.replace('_', ' ')}! Broadcast sent to lounge.`,
      });
      setTimeout(() => setFeedback(null), 5000);
    },
    onError: (err: any) => {
      setFeedback({
        type: 'error',
        message: getErrorMessage(err, 'Failed to update live conference state.'),
      });
    },
  });

  // 3. Reset live state mutation
  const resetLiveStateMutation = useMutation({
    mutationFn: () => resetConferenceLiveState(conferenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conference-live-state', conferenceId] });
      setFeedback({
        type: 'success',
        message: 'Live override cleared. Reverted to automatic schedule clock.',
      });
      setTimeout(() => setFeedback(null), 4000);
    },
    onError: (err: any) => {
      setFeedback({
        type: 'error',
        message: getErrorMessage(err, 'Failed to reset live conference state.'),
      });
    },
  });

  // 4. Fetch Conference-wise Lounge state
  const { data: lounge, refetch: refetchLounge } = useQuery({
    queryKey: ['activeLounge', conferenceId],
    queryFn: () => chatroomApi.getActiveLounge(conferenceId),
    refetchInterval: 8000,
  });

  // 5. Host / Reopen lounge kick-off mutation
  const hostLoungeMutation = useMutation({
    mutationFn: () => hostConferenceLounge(conferenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activeLounge', conferenceId] });
      queryClient.invalidateQueries({ queryKey: ['chatroomMessages'] });
      refetchLounge();
      setFeedback({
        type: 'success',
        message: '🚀 Live Networking Lounge hosted & opened! Kick-off announcement and intro question broadcasted.',
      });
      setTimeout(() => setFeedback(null), 6000);
    },
    onError: (err: any) => {
      setFeedback({
        type: 'error',
        message: getErrorMessage(err, 'Failed to host live lounge.'),
      });
    },
  });

  // 6. Close lounge mutation
  const closeLoungeMutation = useMutation({
    mutationFn: () => closeConferenceLounge(conferenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activeLounge', conferenceId] });
      queryClient.invalidateQueries({ queryKey: ['chatroomMessages'] });
      refetchLounge();
      setFeedback({
        type: 'success',
        message: '🛑 Live Networking Lounge closed. Ambient messaging paused and delegates notified.',
      });
      setTimeout(() => setFeedback(null), 6000);
    },
    onError: (err: any) => {
      setFeedback({
        type: 'error',
        message: getErrorMessage(err, 'Failed to close live lounge.'),
      });
    },
  });

    // 5. Reset lounge history mutation
  const resetLoungeMutation = useMutation({
    mutationFn: () => resetConferenceLounge(conferenceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['activeLounge'] });
      queryClient.invalidateQueries({ queryKey: ['chatroomMessages'] });
      setFeedback({
        type: 'success',
        message: '🗑️ Lounge chat history cleared! Re-initialized to clean Turn #0.',
      });
      setTimeout(() => setFeedback(null), 4000);
    },
    onError: (err: any) => {
      setFeedback({
        type: 'error',
        message: getErrorMessage(err, 'Failed to reset lounge history.'),
      });
    },
  });

  const handleQuickTrigger = (
    cState: string,
    bType: string,
    defaultDuration: number,
    defaultLocation: string,
    banner: string,
    crit: 'NORMAL' | 'CRITICAL' = 'NORMAL'
  ) => {
    const effectiveState = cState === 'GENERAL_ANNOUNCEMENT' ? 'FREE_TIME' : cState;
    const effectiveLabel = cState === 'GENERAL_ANNOUNCEMENT' ? 'Floor Announcement' : undefined;

    setStateType(effectiveState);
    setBreakType(bType);
    setDurationMinutes(defaultDuration);
    setDesignatedLocation(defaultLocation);
    setAnnouncementBanner(banner);
    setCriticality(crit);

    setLiveStateMutation.mutate({
      current_state: effectiveState,
      custom_state_label: effectiveLabel,
      break_type: bType,
      duration_minutes: defaultDuration,
      designated_location: defaultLocation,
      announcement_banner: banner,
      criticality: crit,
      active_day: activeDay,
      delay_minutes: delayMinutes,
      weather_override: weatherOverride.trim() || undefined,
      amenities_note: amenitiesNote.trim() || undefined,
    });
  };

  const handleCustomBroadcast = (e: React.FormEvent) => {
    e.preventDefault();
    const effectiveState = stateType === 'GENERAL_ANNOUNCEMENT' ? 'FREE_TIME' : stateType;
    const effectiveLabel = stateType === 'GENERAL_ANNOUNCEMENT' ? 'Floor Announcement' : undefined;

    setLiveStateMutation.mutate({
      current_state: effectiveState,
      custom_state_label: effectiveLabel,
      break_type: breakType,
      duration_minutes: durationMinutes,
      designated_location: designatedLocation.trim() || undefined,
      announcement_banner: announcementBanner.trim() || undefined,
      criticality: criticality,
      active_day: activeDay,
      delay_minutes: delayMinutes,
      weather_override: weatherOverride.trim() || undefined,
      amenities_note: amenitiesNote.trim() || undefined,
    });
  };

  return (
    <div className="bg-canvas-elevated border border-canvas-border rounded-2xl p-6 sm:p-7 space-y-6 shadow-sm">
      {/* Header & Live Pulse */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-canvas-border pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🎛️</span>
            <h2 className="font-serif text-lg font-bold text-ink-primary">
              Live Conference Control Plane
            </h2>
            <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-brass/10 text-brass border border-brass/30 uppercase tracking-wide">
              Temporal Phase 5
            </span>
          </div>
          <p className="text-xs text-ink-secondary mt-1">
            Real-time live control for {conferenceTitle}. Triggers breaks, schedule delays, and indoor weather adjustments.
          </p>
        </div>

        {/* Active Conference Day Toggle & Live Status Badge */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1 bg-canvas-base border border-canvas-border rounded-xl p-1 shadow-2xs text-xs">
            <span className="text-[11px] font-bold text-ink-muted px-2">📅 Conference Day:</span>
            <button
              type="button"
              onClick={() => {
                setActiveDay(undefined);
                setLiveStateMutation.mutate({
                  current_state: stateType === 'GENERAL_ANNOUNCEMENT' ? 'FREE_TIME' : stateType,
                  custom_state_label: stateType === 'GENERAL_ANNOUNCEMENT' ? 'Floor Announcement' : undefined,
                  active_day: 0,
                  delay_minutes: delayMinutes,
                  weather_override: weatherOverride.trim() || undefined,
                  amenities_note: amenitiesNote.trim() || undefined,
                });
              }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition ${
                !liveState?.active_day ? 'bg-brass text-white shadow-xs font-bold' : 'text-ink-secondary hover:text-ink-primary'
              }`}
              title="Automatically follow live clock and conference calendar"
            >
              Auto
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveDay(1);
                setLiveStateMutation.mutate({
                  current_state: stateType === 'GENERAL_ANNOUNCEMENT' ? 'FREE_TIME' : stateType,
                  custom_state_label: stateType === 'GENERAL_ANNOUNCEMENT' ? 'Floor Announcement' : undefined,
                  active_day: 1,
                  delay_minutes: delayMinutes,
                  weather_override: weatherOverride.trim() || undefined,
                  amenities_note: amenitiesNote.trim() || undefined,
                });
              }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition ${
                liveState?.active_day === 1 ? 'bg-brass text-white shadow-xs font-bold' : 'text-ink-secondary hover:text-ink-primary'
              }`}
              title="Force Day 1: Keynotes, BIS codes, calcined clay standards"
            >
              Day 1
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveDay(2);
                setLiveStateMutation.mutate({
                  current_state: stateType === 'GENERAL_ANNOUNCEMENT' ? 'FREE_TIME' : stateType,
                  custom_state_label: stateType === 'GENERAL_ANNOUNCEMENT' ? 'Floor Announcement' : undefined,
                  active_day: 2,
                  delay_minutes: delayMinutes,
                  weather_override: weatherOverride.trim() || undefined,
                  amenities_note: amenitiesNote.trim() || undefined,
                });
              }}
              className={`px-2.5 py-1 rounded-lg font-semibold transition ${
                liveState?.active_day === 2 ? 'bg-brass text-white shadow-xs font-bold' : 'text-ink-secondary hover:text-ink-primary'
              }`}
              title="Force Day 2: Site execution, 3-day strength vs demoulding, commercial trials"
            >
              Day 2
            </button>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-canvas-base border border-canvas-border shadow-2xs text-xs">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                liveState?.current_state === 'TEA_BREAK'
                  ? 'bg-amber-500 animate-pulse'
                  : liveState?.current_state === 'LUNCH_BREAK'
                  ? 'bg-emerald-500 animate-pulse'
                  : liveState?.current_state === 'NETWORKING_RECEPTION'
                  ? 'bg-purple-500 animate-pulse'
                  : 'bg-blue-500'
              }`}
            />
            <span className="font-bold text-ink-primary">
              {liveState?.current_state ? liveState.current_state.replace('_', ' ') : 'IN SESSION'}
            </span>
            {liveState?.designated_location && (
              <span className="text-ink-muted text-[11px] truncate max-w-[140px]">
                • {liveState.designated_location}
              </span>
            )}
          </div>

          {liveState?.is_active && (
            <button
              type="button"
              onClick={() => resetLiveStateMutation.mutate()}
              disabled={resetLiveStateMutation.isPending}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-canvas-base border border-canvas-border text-ink-secondary hover:text-rose-600 hover:border-rose-300 transition-colors shadow-2xs"
              title="Return to regular scheduled agenda clock"
            >
              Reset to Schedule
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div
          role="status"
          className={`p-3.5 rounded-xl text-xs font-medium border ${
            feedback.type === 'success'
              ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-200 border-emerald-300'
              : 'bg-rose-50 dark:bg-rose-950/30 text-rose-800 dark:text-rose-200 border-rose-300'
          }`}
        >
          {feedback.message}
        </div>
      )}

      {/* Live Networking Lounge Operations (Hosting, Closing & Kickoff) */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2 text-xs font-bold text-amber-900 dark:text-amber-200">
            <span>🎪</span>
            <span>Live Networking Lounge Operations</span>
            {lounge?.is_active ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Lounge Open
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300 border border-stone-300 dark:border-stone-700">
                <span className="w-1.5 h-1.5 rounded-full bg-stone-500" />
                Lounge Closed
              </span>
            )}
          </div>
          <p className="text-[11px] text-amber-800 dark:text-amber-300">
            {lounge?.is_active
              ? 'The lounge floor is currently OPEN. Ambient messages and delegate chat are actively running.'
              : 'The lounge floor is currently CLOSED. Ambient messages and attendee chat inputs are paused until reopened.'}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          {lounge?.is_active ? (
            <button
              type="button"
              onClick={() => {
                if (
                  window.confirm(
                    'Are you sure you want to close the Live Lounge? Ambient dialogue and attendee posting will pause.'
                  )
                ) {
                  closeLoungeMutation.mutate();
                }
              }}
              disabled={closeLoungeMutation.isPending}
              className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5"
            >
              <span>🛑</span>
              <span>{closeLoungeMutation.isPending ? 'Closing...' : 'Close Live Lounge'}</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => hostLoungeMutation.mutate()}
              disabled={hostLoungeMutation.isPending}
              className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-1.5"
            >
              <span>🚀</span>
              <span>{hostLoungeMutation.isPending ? 'Hosting...' : 'Host Live Lounge (Reopen Floor)'}</span>
            </button>
          )}

          <Link
            to={`/lounge?conference_id=${conferenceId}`}
            className="px-3 py-1.5 rounded-lg bg-canvas-base border border-amber-300 dark:border-amber-800 hover:border-amber-500 text-ink-primary text-xs font-semibold shadow-2xs transition-colors flex items-center gap-1"
          >
            <span>↗️ Open Lounge</span>
          </Link>

          <button
            type="button"
            onClick={() => {
              if (window.confirm('Are you sure you want to clear all chatroom messages and reset to Turn #0?')) {
                resetLoungeMutation.mutate();
              }
            }}
            disabled={resetLoungeMutation.isPending}
            className="px-2.5 py-1.5 rounded-lg bg-canvas-base border border-canvas-border hover:border-rose-400 text-ink-muted hover:text-rose-600 text-xs font-medium transition-colors shadow-2xs"
            title="Wipe test messages and restart lounge afresh"
          >
            {resetLoungeMutation.isPending ? 'Clearing...' : '🗑️ Reset History'}
          </button>
        </div>
      </div>

      {/* Quick Action One-Click Presets */}
      <div className="space-y-2">
        <label className="text-xs font-bold text-ink-secondary uppercase tracking-wider block">
          ⚡ One-Click Break Triggers
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
          <button
            type="button"
            onClick={() =>
              handleQuickTrigger(
                'TEA_BREAK',
                'TEA_COFFEE',
                20,
                'Central Concourse & Hall A Foyer',
                '☕ Coffee & High Tea Break is active! Fresh refreshments served at the Central Concourse.'
              )
            }
            disabled={setLiveStateMutation.isPending}
            className="p-3 rounded-xl bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/30 dark:hover:bg-amber-900/40 border border-amber-200 dark:border-amber-800 text-left transition-all shadow-2xs group"
          >
            <div className="text-lg mb-1">☕</div>
            <div className="text-xs font-bold text-amber-900 dark:text-amber-200">20m Tea Break</div>
            <div className="text-[10px] text-amber-700 dark:text-amber-400 mt-0.5">Central Concourse</div>
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickTrigger(
                'LUNCH_BREAK',
                'LUNCH',
                45,
                'Dining Concourse & Lawn Pavilion',
                '🍽️ Conference Lunch Buffet is now open at Dining Concourse! Next tracks resume in 45m.'
              )
            }
            disabled={setLiveStateMutation.isPending}
            className="p-3 rounded-xl bg-emerald-50 hover:bg-emerald-100 dark:bg-emerald-950/30 dark:hover:bg-emerald-900/40 border border-emerald-200 dark:border-emerald-800 text-left transition-all shadow-2xs group"
          >
            <div className="text-lg mb-1">🍽️</div>
            <div className="text-xs font-bold text-emerald-900 dark:text-emerald-200">45m Lunch Break</div>
            <div className="text-[10px] text-emerald-700 dark:text-emerald-400 mt-0.5">Dining Pavilion</div>
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickTrigger(
                'NETWORKING_RECEPTION',
                'CASUAL_NETWORKING',
                30,
                'Exhibition Floor & Lounge',
                '🤝 Open Networking Reception underway! Connect with exhibitors and delegates across Hall B.'
              )
            }
            disabled={setLiveStateMutation.isPending}
            className="p-3 rounded-xl bg-purple-50 hover:bg-purple-100 dark:bg-purple-950/30 dark:hover:bg-purple-900/40 border border-purple-200 dark:border-purple-800 text-left transition-all shadow-2xs group"
          >
            <div className="text-lg mb-1">🤝</div>
            <div className="text-xs font-bold text-purple-900 dark:text-purple-200">30m Networking</div>
            <div className="text-[10px] text-purple-700 dark:text-purple-400 mt-0.5">Exhibition Floor</div>
          </button>

          <button
            type="button"
            onClick={() =>
              handleQuickTrigger(
                'IN_SESSION',
                'NONE',
                60,
                'Main Auditorium',
                '🔔 Delegates, please proceed to your designated session halls. Technical presentations are commencing!'
              )
            }
            disabled={setLiveStateMutation.isPending}
            className="p-3 rounded-xl bg-blue-50 hover:bg-blue-100 dark:bg-blue-950/30 dark:hover:bg-blue-900/40 border border-blue-200 dark:border-blue-800 text-left transition-all shadow-2xs group"
          >
            <div className="text-lg mb-1">▶️</div>
            <div className="text-xs font-bold text-blue-900 dark:text-blue-200">Resume In-Session</div>
            <div className="text-[10px] text-blue-700 dark:text-blue-400 mt-0.5">Auditorium Tracks</div>
          </button>

          <button
            type="button"
            onClick={() => {
              const msg = '📢 Live Floor Notice: Keynote tracks resume promptly in Auditorium. Please check agenda.';
              handleQuickTrigger(
                'FREE_TIME',
                'NONE',
                30,
                'Main Concourse & Auditorium',
                msg,
                'NORMAL'
              );
            }}
            disabled={setLiveStateMutation.isPending}
            className="p-3 rounded-xl bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/30 dark:hover:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-800 text-left transition-all shadow-2xs group"
          >
            <div className="text-lg mb-1">📢</div>
            <div className="text-xs font-bold text-indigo-900 dark:text-indigo-200">Floor Notice</div>
            <div className="text-[10px] text-indigo-700 dark:text-indigo-400 mt-0.5">Live Announcement</div>
          </button>
        </div>
      </div>

      {/* Advanced Control Form: Delays, Weather & Custom Announcements */}
      <form onSubmit={handleCustomBroadcast} className="bg-canvas-base border border-canvas-border rounded-xl p-4 sm:p-5 space-y-4">
        <div className="text-xs font-bold text-ink-primary flex items-center justify-between">
          <span>🛠️ Schedule Delays & Environmental Overrides</span>
          <span className="text-[11px] font-normal text-ink-muted">Optional fine-tuning</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* State & Type */}
          <div>
            <label className="block text-[11px] font-semibold text-ink-secondary mb-1">
              Active State
            </label>
            <select
              value={stateType}
              onChange={(e) => setStateType(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-lg border border-canvas-border bg-canvas-surface text-ink-primary focus:outline-hidden focus:border-brass"
            >
              <option value="TEA_BREAK">☕ TEA BREAK</option>
              <option value="LUNCH_BREAK">🍽️ LUNCH BREAK</option>
              <option value="NETWORKING_RECEPTION">🤝 NETWORKING RECEPTION</option>
              <option value="FREE_TIME">✨ FREE TIME</option>
              <option value="IN_SESSION">▶️ IN SESSION</option>
              <option value="GENERAL_ANNOUNCEMENT">📢 GENERAL ANNOUNCEMENT</option>
            </select>
          </div>

          {/* Location */}
          <div>
            <label className="block text-[11px] font-semibold text-ink-secondary mb-1">
              Designated Location
            </label>
            <input
              type="text"
              value={designatedLocation}
              onChange={(e) => setDesignatedLocation(e.target.value)}
              placeholder="e.g. Central Concourse, Hall B"
              className="w-full px-3 py-2 text-xs rounded-lg border border-canvas-border bg-canvas-surface text-ink-primary focus:outline-hidden focus:border-brass"
            />
          </div>

          {/* Duration Slider */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-semibold text-ink-secondary">
                Duration
              </label>
              <span className="text-[11px] font-mono font-bold text-brass">
                {durationMinutes} mins
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={90}
              step={5}
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(Number(e.target.value))}
              className="w-full accent-brass cursor-pointer"
            />
          </div>
        </div>

        {/* Schedule Delay Quick Buttons */}
        <div>
          <label className="block text-[11px] font-semibold text-ink-secondary mb-1.5">
            ⏱️ Session Delay Adjustment (Broadcast to Agenda & Matching)
          </label>
          <div className="flex flex-wrap items-center gap-2">
            {[10, 15, 30].map((mins) => (
              <button
                key={mins}
                type="button"
                onClick={() => setDelayMinutes(delayMinutes === mins ? undefined : mins)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold border transition-all ${
                  delayMinutes === mins
                    ? 'bg-amber-600 text-white border-amber-600 shadow-2xs'
                    : 'bg-canvas-elevated text-ink-secondary border-canvas-border hover:border-amber-400'
                }`}
              >
                +{mins}m Delay
              </button>
            ))}
            {delayMinutes !== undefined && (
              <button
                type="button"
                onClick={() => setDelayMinutes(undefined)}
                className="px-2 py-1 text-xs text-ink-muted hover:text-rose-600 transition"
              >
                ✕ Clear Delay
              </button>
            )}
          </div>
        </div>

        {/* Weather & Indoor Relocation Override */}
        <div>
          <label className="block text-[11px] font-semibold text-ink-secondary mb-1">
            🌧️ Weather / Indoor Relocation Note
          </label>
          <input
            type="text"
            value={weatherOverride}
            onChange={(e) => setWeatherOverride(e.target.value)}
            placeholder="e.g. Rain showers: Outdoor patio networking relocated to Central Concourse"
            className="w-full px-3 py-2 text-xs rounded-lg border border-canvas-border bg-canvas-surface text-ink-primary focus:outline-hidden focus:border-brass placeholder:text-ink-muted"
          />
        </div>

        {/* Venue Amenities & Charging Station Location Note */}
        <div>
          <label className="block text-[11px] font-semibold text-ink-secondary mb-1">
            🔌 Venue Amenities & Charging Sockets Note (Editable for Lounge Tips)
          </label>
          <input
            type="text"
            value={amenitiesNote}
            onChange={(e) => setAmenitiesNote(e.target.value)}
            placeholder="e.g. High-speed charging docks located near Central Concourse, Hall B Pillar 4"
            className="w-full px-3 py-2 text-xs rounded-lg border border-canvas-border bg-canvas-surface text-ink-primary focus:outline-hidden focus:border-brass placeholder:text-ink-muted"
          />
        </div>

        {/* Custom Announcement Banner with Criticality Selection */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="block text-[11px] font-semibold text-ink-secondary">
              📢 Live Summit Announcement & News Bulletin
            </label>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] text-ink-muted font-medium">Criticality:</span>
              <button
                type="button"
                onClick={() => setCriticality('NORMAL')}
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all border ${
                  criticality === 'NORMAL'
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-2xs'
                    : 'bg-canvas-surface text-ink-muted border-canvas-border hover:border-indigo-300'
                }`}
              >
                📢 Normal Notice
              </button>
              <button
                type="button"
                onClick={() => setCriticality('CRITICAL')}
                className={`px-2 py-0.5 rounded-md text-[10px] font-bold transition-all border ${
                  criticality === 'CRITICAL'
                    ? 'bg-rose-600 text-white border-rose-600 shadow-2xs animate-pulse'
                    : 'bg-canvas-surface text-ink-muted border-canvas-border hover:border-rose-300'
                }`}
              >
                🚨 Critical / Safety
              </button>
              {announcementBanner && (
                <button
                  type="button"
                  onClick={() => setAnnouncementBanner('')}
                  className="text-[10px] text-rose-600 hover:underline font-medium ml-1"
                >
                  ✕ Clear
                </button>
              )}
            </div>
          </div>
          <input
            type="text"
            value={announcementBanner}
            onChange={(e) => {
              const val = e.target.value;
              setAnnouncementBanner(val);
              const lower = val.toLowerCase();
              if (['thunder', 'storm', 'lightning', 'rain', 'danger', 'warning', 'emergency'].some((w) => lower.includes(w))) {
                setCriticality('CRITICAL');
              }
            }}
            placeholder="e.g. ⛈️ Severe thunderstorm warning: Outdoor pavilion networking relocated to Central Concourse."
            className={`w-full px-3 py-2 text-xs rounded-lg border bg-canvas-surface text-ink-primary focus:outline-hidden transition-all placeholder:text-ink-muted ${
              criticality === 'CRITICAL'
                ? 'border-rose-400 focus:border-rose-600 ring-1 ring-rose-400/30'
                : 'border-canvas-border focus:border-brass'
            }`}
          />
          {/* Quick Presets */}
          <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
            <span className="text-[10px] text-ink-muted font-medium">Quick Presets:</span>
            {[
              { label: '⛈️ Severe Thunderstorm', text: 'Severe thunderstorm warning: Outdoor pavilion networking relocated to Central Concourse immediately.', crit: 'CRITICAL' as const },
              { label: '🌧️ Heavy Rain', text: 'Heavy rain detected: Please use covered skywalks between Exhibition Hall A & Hall B.', crit: 'CRITICAL' as const },
              { label: '📍 Keynote Shift', text: 'Keynote session with Dr. Rajesh Sharma rescheduled to 3:30 PM in Hall A.', crit: 'NORMAL' as const },
              { label: '🏆 Awards Ceremony', text: 'Green Cement Innovation Awards ceremony starts at 5:00 PM in Main Auditorium.', crit: 'NORMAL' as const },
              { label: '⚡ Charging Hub', text: 'High-speed device charging dock and Wi-Fi hub active at Central Concourse.', crit: 'NORMAL' as const },
            ].map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => {
                  setAnnouncementBanner(preset.text);
                  setCriticality(preset.crit);
                }}
                className={`px-2 py-0.5 rounded-md text-[10px] font-medium border transition-colors ${
                  preset.crit === 'CRITICAL'
                    ? 'bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800 hover:border-rose-500'
                    : 'bg-canvas-surface text-ink-secondary border-canvas-border hover:border-brass hover:text-brass'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Submit Broadcast Button */}
        <div className="flex items-center justify-end pt-2 border-t border-canvas-border">
          <button
            type="submit"
            disabled={setLiveStateMutation.isPending}
            className="px-5 py-2.5 rounded-xl bg-brass hover:bg-brass/90 disabled:opacity-50 text-white text-xs font-bold shadow-xs transition-all flex items-center gap-2"
          >
            {setLiveStateMutation.isPending ? (
              <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <span>📢 Broadcast Live Override</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
