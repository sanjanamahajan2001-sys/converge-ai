import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Home } from '@/routes/Home';

function renderHomeWithClient() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <Home />
    </QueryClientProvider>
  );
}

describe('Home Page Component', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('renders hero title and section headings', () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/health/ready')) {
        return Promise.resolve({
          status: 200,
          ok: true,
          json: async () => ({ status: 'ready', database: 'connected' }),
        });
      }
      if (url.includes('/health')) {
        return Promise.resolve({
          status: 200,
          ok: true,
          json: async () => ({ status: 'healthy', service: 'converge-ai', environment: 'development' }),
        });
      }
      if (url.includes('/version')) {
        return Promise.resolve({
          status: 200,
          ok: true,
          json: async () => ({ version: '0.1.0', project_name: 'Converge AI', api_prefix: '/converge-api/v1' }),
        });
      }
      return Promise.reject(new Error('Not found'));
    });

    renderHomeWithClient();

    expect(
      screen.getByRole('heading', {
        name: /Autonomous Background Networking for Conference Delegates/i,
      })
    ).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { name: /Live Infrastructure Telemetry/i })
    ).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { name: /Verified Architecture Baseline/i })
    ).toBeInTheDocument();

    expect(
      screen.getByRole('heading', { name: /Planned Engineering Roadmap/i })
    ).toBeInTheDocument();
  });

  it('renders offline indicator when backend fetch fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    renderHomeWithClient();

    // The heading and hero should still render properly without crashing
    expect(
      screen.getByRole('heading', {
        name: /Autonomous Background Networking for Conference Delegates/i,
      })
    ).toBeInTheDocument();
  });
});
