import React from 'react';
import { QuoteUrgency, VendorMatchStatus } from '@/types/quote';

interface QuoteStatusBadgeProps {
  status: VendorMatchStatus;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const QuoteStatusBadge: React.FC<QuoteStatusBadgeProps> = ({
  status,
  size = 'md',
  className = '',
}) => {
  let badgeColor = 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700';
  let label: string = status;
  let icon = '•';

  switch (status) {
    case 'PENDING_REVIEW':
      badgeColor = 'bg-amber-50 text-amber-800 border-amber-300 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-700';
      label = 'New Inquiry';
      icon = '⚡';
      break;
    case 'VIEWED':
      badgeColor = 'bg-sky-50 text-sky-800 border-sky-300 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-700';
      label = 'Under Review';
      icon = '👁️';
      break;
    case 'QUOTE_SENT':
      badgeColor = 'bg-emerald-50 text-emerald-800 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-700';
      label = 'Quoted via Email';
      icon = '✉️';
      break;
    case 'DECLINED':
      badgeColor = 'bg-rose-50 text-rose-700 border-rose-300 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800';
      label = 'Declined';
      icon = '✕';
      break;
    case 'EXPIRED':
      badgeColor = 'bg-slate-100 text-slate-600 border-slate-300 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700';
      label = 'Expired';
      icon = '⌛';
      break;
  }

  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5 gap-1',
    md: 'text-xs px-2.5 py-1 gap-1.5',
    lg: 'text-sm px-3 py-1.5 gap-2',
  }[size];

  return (
    <span
      className={`inline-flex items-center font-medium rounded-full border shadow-2xs ${sizeClasses} ${badgeColor} ${className}`}
      data-testid="quote-status-badge"
    >
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
};

export const QuoteUrgencyBadge: React.FC<{ urgency: QuoteUrgency; className?: string }> = ({
  urgency,
  className = '',
}) => {
  let color = 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300';
  let label: string = urgency;
  let icon = '•';

  switch (urgency) {
    case 'CRITICAL':
      color = 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/50 dark:text-rose-300 dark:border-rose-800';
      label = 'Critical';
      icon = '🔥';
      break;
    case 'HIGH':
      color = 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-700';
      label = 'High Priority';
      icon = '⚡';
      break;
    case 'PLANNED':
      color = 'bg-sky-100 text-sky-800 border-sky-300 dark:bg-sky-950/50 dark:text-sky-300 dark:border-sky-700';
      label = 'Planned';
      icon = '📅';
      break;
    case 'FLEXIBLE':
      color = 'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-800 dark:text-slate-400';
      label = 'Flexible';
      icon = '🌱';
      break;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${color} ${className}`}
      data-testid="quote-urgency-badge"
    >
      <span aria-hidden="true">{icon}</span>
      <span>{label}</span>
    </span>
  );
};
