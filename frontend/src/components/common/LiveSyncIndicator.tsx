import React from 'react';
import { useRealtimeSync } from '@/lib/events/RealtimeSyncContext';

interface LiveSyncIndicatorProps {
  className?: string;
  showText?: boolean;
}

export const LiveSyncIndicator: React.FC<LiveSyncIndicatorProps> = ({ className = '', showText = true }) => {
  const { status } = useRealtimeSync();

  const isConnected = status === 'connected';
  const isConnecting = status === 'connecting';

  const dotColor = isConnected
    ? 'bg-emerald-500'
    : isConnecting
    ? 'bg-amber-500 animate-pulse'
    : 'bg-zinc-400';

  const label = isConnected ? 'Live Sync' : isConnecting ? 'Connecting' : 'Sync Paused';

  return (
    <div
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-mono border transition-colors select-none ${
        isConnected
          ? 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/25'
          : isConnecting
          ? 'bg-amber-500/10 text-amber-800 dark:text-amber-300 border-amber-500/25'
          : 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-400/20'
      } ${className}`}
      title={`Real-Time Event Broker: ${isConnected ? 'Connected & listening for updates' : status}`}
      role="status"
      aria-label={`Real-time sync status: ${label}`}
    >
      <span className="relative flex h-2 w-2">
        {isConnected && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColor}`} />
      </span>
      {showText && <span className="font-semibold tracking-tight">{label}</span>}
    </div>
  );
};
