import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EmptyState } from '@/components/ui/EmptyState';

describe('EmptyState Component', () => {
  it('renders title, description and emoji icon', () => {
    render(
      <EmptyState
        title="No Proposals Found"
        description="There are currently no proposals awaiting your review."
        emoji="🤝"
      />
    );

    expect(screen.getByText('No Proposals Found')).toBeInTheDocument();
    expect(screen.getByText('There are currently no proposals awaiting your review.')).toBeInTheDocument();
    expect(screen.getByText('🤝')).toBeInTheDocument();
  });

  it('renders action element when provided', () => {
    render(
      <EmptyState
        title="Empty List"
        description="Nothing here."
        action={<button>Refresh List</button>}
      />
    );

    expect(screen.getByRole('button', { name: /refresh list/i })).toBeInTheDocument();
  });
});
