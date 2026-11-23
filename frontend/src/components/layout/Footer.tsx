import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api/client';

export const Footer: React.FC = () => {
  const { data: version } = useQuery({
    queryKey: ['version'],
    queryFn: api.getVersion,
    staleTime: 60000,
    refetchOnWindowFocus: false,
  });

  return (
    <footer className="bg-canvas-surface border-t border-canvas-border mt-auto py-6 sm:py-8 print:hidden" role="contentinfo">
      <div className="w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 text-xs text-ink-muted">
          <div className="flex items-center gap-2">
            <span aria-hidden="true" className="text-base select-none">🤝</span>
            <span>
              <strong className="font-semibold text-ink-secondary">Converge AI</strong> — Physical Conference Background Agent Network
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 sm:gap-4 font-mono text-[11px]">
            <span>
              Gateway:{' '}
              <code className="bg-canvas-elevated px-1.5 py-0.5 rounded text-ink-secondary border border-canvas-border">
                {version?.api_prefix || '/converge-api/v1'}
              </code>
            </span>
            <span>
              Subpath:{' '}
              <code className="bg-canvas-elevated px-1.5 py-0.5 rounded text-ink-secondary border border-canvas-border">
                /converge/
              </code>
            </span>
            <span>
              Design:{' '}
              <span className="text-ink-secondary">Native System Stack</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
};
