import React from 'react';
import { ProposalStatus } from '@/types/proposal';

interface ProposalStatusBadgeProps {
  status: ProposalStatus;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const ProposalStatusBadge: React.FC<ProposalStatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  const getBadgeConfig = () => {
    switch (status) {
      case 'MUTUALLY_APPROVED':
        return {
          label: 'Mutually Approved',
          icon: '✓',
          classes:
            'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-300 dark:border-emerald-700',
        };
      case 'PENDING_REVIEW':
        return {
          label: 'Pending Review',
          icon: '⏳',
          classes:
            'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-300 dark:border-amber-700',
        };
      case 'REVISED':
        return {
          label: 'Counter-Offered',
          icon: '🔄',
          classes:
            'bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border-sky-300 dark:border-sky-700',
        };
      case 'REJECTED':
        return {
          label: 'Declined',
          icon: '✕',
          classes:
            'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-300 dark:border-rose-700',
        };
      case 'WITHDRAWN':
        return {
          label: 'Withdrawn',
          icon: '↩',
          classes:
            'bg-slate-100 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-700',
        };
      case 'EXPIRED':
        return {
          label: 'Expired',
          icon: '⌛',
          classes:
            'bg-zinc-100 dark:bg-zinc-800/50 text-zinc-500 dark:text-zinc-400 border-zinc-300 dark:border-zinc-700',
        };
      case 'DRAFT':
      default:
        return {
          label: 'Draft',
          icon: '📝',
          classes:
            'bg-canvas-elevated text-ink-muted border-canvas-border',
        };
    }
  };

  const { label, icon, classes } = getBadgeConfig();

  const sizeClasses = {
    sm: 'text-[10px] px-1.5 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border shadow-2xs select-none ${classes} ${sizeClasses} ${className}`}
      data-testid="proposal-status-badge"
    >
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
};
