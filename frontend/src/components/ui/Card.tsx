import React from 'react';

interface CardProps {
  title?: string;
  subtitle?: string;
  badge?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  title,
  subtitle,
  badge,
  children,
  className = '',
  hoverable = false,
}) => {
  return (
    <div
      className={`editorial-card rounded-lg p-6 ${
        hoverable ? 'editorial-card-hover' : ''
      } ${className}`}
    >
      {(title || subtitle || badge) && (
        <div className="flex items-start justify-between gap-4 mb-4 border-b border-canvas-border pb-3">
          <div>
            {title && (
              <h3 className="font-serif text-lg font-semibold text-ink-primary">
                {title}
              </h3>
            )}
            {subtitle && (
              <p className="text-xs text-ink-muted mt-0.5">{subtitle}</p>
            )}
          </div>
          {badge && <div>{badge}</div>}
        </div>
      )}
      <div>{children}</div>
    </div>
  );
};
