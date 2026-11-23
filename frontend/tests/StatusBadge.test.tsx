import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { StatusBadge } from '@/components/ui/StatusBadge';

describe('StatusBadge Component', () => {
  it('renders label and emoji correctly with accessible role', () => {
    render(<StatusBadge emoji="☕" label="Tea / Coffee" variant="neutral" />);

    const badge = screen.getByRole('status');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent('☕');
    expect(badge).toHaveTextContent('Tea / Coffee');
  });

  it('applies variant classes correctly', () => {
    const { rerender } = render(<StatusBadge label="Ready" variant="success" />);
    expect(screen.getByRole('status')).toHaveClass('text-status-success');

    rerender(<StatusBadge label="Offline" variant="danger" />);
    expect(screen.getByRole('status')).toHaveClass('text-status-danger');

    rerender(<StatusBadge label="Pending" variant="warning" />);
    expect(screen.getByRole('status')).toHaveClass('text-status-warning');
  });
});
