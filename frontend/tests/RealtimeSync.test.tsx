import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RealtimeSyncProvider } from '@/lib/events/RealtimeSyncContext';
import { LiveSyncIndicator } from '@/components/common/LiveSyncIndicator';
import { RealtimeToastContainer } from '@/components/common/RealtimeToastContainer';

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  listeners: Record<string, ((event: any) => void)[]> = {};
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 10);
  }

  addEventListener(event: string, callback: (event: any) => void) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  removeEventListener(event: string, callback: (event: any) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((cb) => cb !== callback);
    }
  }

  emit(event: string, data: any) {
    const eventPayload = { data: JSON.stringify(data) };
    if (this.listeners[event]) {
      this.listeners[event].forEach((cb) => cb(eventPayload));
    }
  }

  close() {
    MockEventSource.instances = MockEventSource.instances.filter((i) => i !== this);
  }
}

describe('Real-Time Synchronization (Phase 6)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    MockEventSource.instances = [];
    // @ts-ignore
    global.EventSource = MockEventSource;
  });

  it('renders LiveSyncIndicator and establishes connection', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <LiveSyncIndicator />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    // Initial state is connecting or connected
    expect(screen.getByRole('status')).toBeInTheDocument();

    // Wait for mock open event
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });

    expect(screen.getByText('Live Sync')).toBeInTheDocument();
  });

  it('handles conference:approved event, invalidates queries and displays toast', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    // Wait for mock connection
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    expect(es).toBeDefined();

    // Emit conference:approved event
    await act(async () => {
      es.emit('conference:approved', {
        conference_id: 'conf-123',
        title: 'Net-Zero Concrete 2026',
        status: 'PUBLISHED',
      });
    });

    // Verify TanStack Query cache was invalidated for public agenda and organizer
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['conferences'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['sessions'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['organizer', 'conferences'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'conferences'] });

    // Verify Toast notification appeared
    expect(screen.getByText('Conference Published 🎉')).toBeInTheDocument();
    expect(screen.getByText(/"Net-Zero Concrete 2026" is now approved and live on the Public Agenda\./)).toBeInTheDocument();
  });

  it('handles conference:submitted event and alerts admin queue', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit('conference:submitted', {
        conference_id: 'conf-sub-456',
        title: 'Autonomous Multi-Agent Summit',
        status: 'IN_REVIEW',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'conferences'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'overview'] });
    expect(screen.getByText('Conference Submitted')).toBeInTheDocument();
  });

  it('allows dismissing a toast notification manually', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit('organizer:verified', {
        organizer_id: 'org-1',
        verification_status: 'VERIFIED',
      });
    });

    expect(screen.getByText('Organizer Status Updated')).toBeInTheDocument();

    const dismissBtn = screen.getByLabelText('Dismiss notification');
    fireEvent.click(dismissBtn);

    expect(screen.queryByText('Organizer Status Updated')).not.toBeInTheDocument();
  });

  it('handles proposal:created event and invalidates proposal caches with notification toast', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit('proposal:created', {
        proposal_id: 'prop-123',
        conversation_id: 'conv-999',
        title: 'Supply Agreement for Green Hydrogen',
        status: 'PENDING_REVIEW',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['proposals'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['proposals', 'header-badge'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['proposals', 'conversation', 'conv-999'] });
    expect(screen.getByText('Commercial Proposal Submitted 📜')).toBeInTheDocument();
  });

  it('handles proposal:approved event and displays mutual consensus celebration toast', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit('proposal:approved', {
        proposal_id: 'prop-123',
        conversation_id: 'conv-999',
        title: 'Supply Agreement for Green Hydrogen',
        status: 'MUTUALLY_APPROVED',
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['proposals'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['proposal', 'prop-123'] });
    expect(screen.getByText('Proposal Mutually Approved! 🎉')).toBeInTheDocument();
  });

  it('handles brochure:viewed and brochure:page_read events by invalidating admin and owner analytics queries silently', async () => {
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    render(
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <RealtimeToastContainer />
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20));
    });

    const es = MockEventSource.instances[0];
    await act(async () => {
      es.emit('brochure:page_read', {
        brochure_id: 'broch-1',
        slug: 'maahi-decarb',
        page_numbers: [2, 3],
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['admin', 'brochure-analytics'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['my-brochure', 'analytics'] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['my-brochure'] });
  });
});
