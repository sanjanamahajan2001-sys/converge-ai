import React from 'react';

interface EmptyStateProps {
  emoji?: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  emoji = '🔍',
  title,
  description,
  action,
}) => {
  return (
    <div
      className="text-center py-12 px-4 rounded-lg border border-dashed border-canvas-border-strong bg-canvas-elevated/40"
      role="region"
      aria-label={title}
    >
      <div className="text-3xl mb-3" aria-hidden="true">
        {emoji}
      </div>
      <h4 className="font-serif text-base font-semibold text-ink-primary mb-1">
        {title}
      </h4>
      <p className="text-sm text-ink-secondary max-w-md mx-auto mb-4">
        {description}
      </p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
};
