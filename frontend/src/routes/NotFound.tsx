import React from 'react';
import { Link } from 'react-router-dom';
import { EmptyState } from '@/components/ui/EmptyState';

export const NotFound: React.FC = () => {
  return (
    <div className="py-12 max-w-lg mx-auto">
      <EmptyState
        emoji="🧭"
        title="Page Not Found"
        description="The conference section or screen you are looking for does not exist or has not yet been unlocked."
        action={
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-brass text-white text-xs font-semibold hover:bg-brass-hover transition-colors focus-visible:outline-2"
          >
            <span>←</span> Return to Overview
          </Link>
        }
      />
    </div>
  );
};
