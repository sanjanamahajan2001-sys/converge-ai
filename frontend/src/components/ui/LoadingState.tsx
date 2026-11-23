import React from 'react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading conference data...',
}) => {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 px-4"
      role="status"
      aria-live="polite"
    >
      <div
        className="w-8 h-8 rounded-full border-2 border-canvas-border-strong border-t-brass animate-spin mb-3"
        aria-hidden="true"
      />
      <p className="text-xs text-ink-secondary font-mono tracking-wide">
        {message}
      </p>
    </div>
  );
};
