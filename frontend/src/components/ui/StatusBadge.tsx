import React from 'react';

export type StatusVariant = 'success' | 'warning' | 'danger' | 'neutral';

interface StatusBadgeProps {
  emoji?: string;
  label: string;
  variant?: StatusVariant;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  emoji,
  label,
  variant = 'neutral',
  className = '',
}) => {
  const variantStyles: Record<StatusVariant, string> = {
    success: 'bg-sage-light text-status-success border-sage/30',
    warning: 'bg-brass-light text-status-warning border-brass/30',
    danger: 'bg-terracotta-light text-status-danger border-terracotta/30',
    neutral: 'bg-canvas-elevated text-ink-secondary border-canvas-border',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]} ${className}`}
      role="status"
    >
      {emoji && <span aria-hidden="true">{emoji}</span>}
      <span>{label}</span>
    </span>
  );
};
