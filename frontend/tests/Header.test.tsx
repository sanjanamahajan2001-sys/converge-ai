import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from '@/components/layout/Header';

const testQueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

describe('Header Component', () => {
  it('renders branding title and banner landmark', () => {
    render(
      <QueryClientProvider client={testQueryClient}>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByText('Converge AI')).toBeInTheDocument();
    expect(screen.getByText('Conference Agent Network')).toBeInTheDocument();
  });

  it('renders main navigation landmark with links', () => {
    render(
      <QueryClientProvider client={testQueryClient}>
        <MemoryRouter>
          <Header />
        </MemoryRouter>
      </QueryClientProvider>
    );

    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
    expect(screen.getByText('Overview')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /agenda/i })).toBeInTheDocument();
  });
});
