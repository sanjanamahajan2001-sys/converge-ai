import React from 'react';
import { ProposalRevisionDiffResponse, ProposalDiffFieldChange } from '@/types/proposal';

interface ProposalDiffViewerProps {
  diff: ProposalRevisionDiffResponse | null;
  isLoading?: boolean;
}

export const ProposalDiffViewer: React.FC<ProposalDiffViewerProps> = ({ diff, isLoading }) => {
  if (isLoading) {
    return (
      <div className="p-6 bg-canvas-surface border border-canvas-border rounded-xl flex items-center justify-center gap-3 text-ink-muted text-sm">
        <span className="animate-spin text-lg">⏳</span>
        <span>Computing parameter diff between revisions...</span>
      </div>
    );
  }

  if (!diff) {
    return (
      <div className="p-6 bg-canvas-surface border border-canvas-border rounded-xl text-center text-ink-muted text-sm">
        Select revisions to view comparative diff.
      </div>
    );
  }

  const {
    from_revision_number,
    to_revision_number,
    from_author_name,
    to_author_name,
    changes,
    has_price_change,
    has_quantity_change,
    has_timeline_change,
    has_delivery_change,
  } = diff;

  return (
    <div className="bg-canvas-surface border border-canvas-border rounded-xl shadow-xs overflow-hidden">
      {/* Diff Header */}
      <div className="p-4 bg-canvas-elevated border-b border-canvas-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-base">⚖️</span>
            <h4 className="font-serif font-bold text-ink-primary text-sm sm:text-base">
              Revision Comparison: V{from_revision_number} → V{to_revision_number}
            </h4>
          </div>
          <p className="text-xs text-ink-muted mt-0.5">
            Baseline: <strong>{from_author_name || `V${from_revision_number}`}</strong> • Counter-Offer: <strong>{to_author_name || `V${to_revision_number}`}</strong>
          </p>
        </div>

        {/* Change Indicators */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          {has_quantity_change && (
            <span className="px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700 font-semibold">
              📦 Volume Changed
            </span>
          )}
          {has_price_change && (
            <span className="px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700 font-semibold">
              💰 Price Modified
            </span>
          )}
          {has_timeline_change && (
            <span className="px-2 py-0.5 rounded-full bg-sky-50 dark:bg-sky-950/40 text-sky-700 dark:text-sky-300 border border-sky-300 dark:border-sky-700 font-semibold">
              ⏱️ Lead Time Adjusted
            </span>
          )}
          {has_delivery_change && (
            <span className="px-2 py-0.5 rounded-full bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-300 dark:border-purple-700 font-semibold">
              📍 Logistics / Incoterm
            </span>
          )}
        </div>
      </div>

      {/* Changes Body */}
      {changes.length === 0 ? (
        <div className="p-8 text-center text-ink-muted text-sm">
          <p className="text-2xl mb-1">🤝</p>
          <p className="font-medium text-ink-primary">Identical Commercial Terms</p>
          <p className="text-xs text-ink-secondary mt-1">
            No parameter modifications detected between Revision V{from_revision_number} and Revision V{to_revision_number}.
          </p>
        </div>
      ) : (
        <>
          {/* Mobile Stacked Card View (< md) */}
          <div className="block md:hidden divide-y divide-canvas-border">
            {changes.map((change) => (
              <MobileDiffCard key={change.field} change={change} />
            ))}
          </div>

          {/* Desktop Side-by-Side Comparison Table (>= md) */}
          <div className="hidden md:block overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-canvas-base border-b border-canvas-border text-ink-muted uppercase font-mono tracking-wider text-[10px]">
                  <th className="py-2.5 px-4 font-semibold w-1/4">Commercial Parameter</th>
                  <th className="py-2.5 px-4 font-semibold w-1/3">Revision V{from_revision_number}</th>
                  <th className="py-2.5 px-4 font-semibold w-1/3">Revision V{to_revision_number}</th>
                  <th className="py-2.5 px-4 font-semibold text-right">Adjustment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-canvas-border text-ink-primary">
                {changes.map((change) => (
                  <tr key={change.field} className="hover:bg-canvas-elevated/40 transition-colors">
                    <td className="py-3 px-4 font-medium text-ink-secondary">
                      {change.field_label}
                    </td>
                    <td className="py-3 px-4 font-mono text-ink-muted line-through bg-rose-50/20 dark:bg-rose-950/10">
                      {formatValue(change.old_value)}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold text-ink-primary bg-emerald-50/20 dark:bg-emerald-950/10">
                      {formatValue(change.new_value)}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {change.formatted_change ? (
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                            change.formatted_change.startsWith('+')
                              ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-200'
                              : 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-200'
                          }`}
                        >
                          {change.formatted_change}
                        </span>
                      ) : (
                        <span className="text-[10px] uppercase font-mono text-ink-muted">
                          {change.change_type}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};

const MobileDiffCard: React.FC<{ change: ProposalDiffFieldChange }> = ({ change }) => {
  return (
    <div className="p-3.5 space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-ink-primary">{change.field_label}</span>
        {change.formatted_change ? (
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
              change.formatted_change.startsWith('+')
                ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-200'
                : 'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-200'
            }`}
          >
            {change.formatted_change}
          </span>
        ) : (
          <span className="text-[9px] uppercase font-mono text-ink-muted px-1.5 py-0.5 rounded bg-canvas-base border border-canvas-border">
            {change.change_type}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div className="p-2 rounded bg-rose-50/40 dark:bg-rose-950/20 border border-rose-200/50 dark:border-rose-900/30">
          <span className="text-[9px] uppercase tracking-wider text-rose-600 dark:text-rose-400 block font-sans">
            Baseline
          </span>
          <span className="line-through text-ink-muted break-words">
            {formatValue(change.old_value)}
          </span>
        </div>
        <div className="p-2 rounded bg-emerald-50/40 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-900/30">
          <span className="text-[9px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 block font-sans font-bold">
            Counter-Offer
          </span>
          <span className="font-bold text-ink-primary break-words">
            {formatValue(change.new_value)}
          </span>
        </div>
      </div>
    </div>
  );
};

function formatValue(val: any): string {
  if (val === null || val === undefined || val === '') return '—';
  if (Array.isArray(val)) return val.length ? val.join(', ') : 'None';
  if (typeof val === 'number') return val.toLocaleString();
  return String(val);
}
