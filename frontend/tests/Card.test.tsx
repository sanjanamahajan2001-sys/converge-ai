import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Card } from '@/components/ui/Card';

describe('Card Component', () => {
  it('renders card with children content', () => {
    render(
      <Card title="System Information" subtitle="Live backend status">
        <p>Operational data here.</p>
      </Card>
    );

    expect(screen.getByText('System Information')).toBeInTheDocument();
    expect(screen.getByText('Live backend status')).toBeInTheDocument();
    expect(screen.getByText('Operational data here.')).toBeInTheDocument();
  });
});
