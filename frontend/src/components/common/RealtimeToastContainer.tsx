import React from 'react';
import { useRealtimeSync } from '@/lib/events/RealtimeSyncContext';

export const RealtimeToastContainer: React.FC = () => {
  const { toasts, dismissToast } = useRealtimeSync();

  if (toasts.length === 0) return null;

  return (
    <aside
      aria-label="Real-time notifications"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none px-4 sm:px-0"
    >
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isWarning = toast.type === 'warning';
        const isAlert = toast.type === 'alert';

        const borderColor = isSuccess
          ? 'border-emerald-500/40 bg-emerald-950/20'
          : isWarning
          ? 'border-amber-500/40 bg-amber-950/20'
          : isAlert
          ? 'border-crimson/40 bg-crimson-light/20'
          : 'border-brass/30 bg-canvas-surface';

        const icon = isSuccess ? '🎉' : isWarning ? '📝' : isAlert ? '⚠️' : '🔔';

        return (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto p-3.5 rounded-xl border ${borderColor} backdrop-blur-md shadow-lg transition-all duration-200 animate-in fade-in slide-in-from-bottom-2 flex items-start gap-3 bg-canvas-surface/95 text-ink-primary`}
          >
            <span className="text-lg leading-none mt-0.5 select-none" aria-hidden="true">
              {icon}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2 mb-0.5">
                <h4 className="text-xs font-bold text-ink-primary truncate font-sans">{toast.title}</h4>
                <span className="text-[10px] font-mono text-ink-muted shrink-0">{toast.timestamp}</span>
              </div>
              <p className="text-xs text-ink-secondary leading-relaxed break-words">{toast.message}</p>
            </div>
            <button
              type="button"
              onClick={() => dismissToast(toast.id)}
              className="text-ink-muted hover:text-ink-primary p-1 -mr-1 rounded-md transition-colors"
              aria-label="Dismiss notification"
            >
              ✕
            </button>
          </div>
        );
      })}
    </aside>
  );
};
