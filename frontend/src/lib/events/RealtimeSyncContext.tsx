import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

export type RealtimeSyncStatus = 'connected' | 'connecting' | 'disconnected';

export interface RealtimeToast {
  id: string;
  type: 'info' | 'success' | 'warning' | 'alert';
  title: string;
  message: string;
  timestamp: string;
}

interface RealtimeSyncContextValue {
  status: RealtimeSyncStatus;
  lastEvent: { event: string; data: any; timestamp: string } | null;
  toasts: RealtimeToast[];
  dismissToast: (id: string) => void;
}

const RealtimeSyncContext = createContext<RealtimeSyncContextValue>({
  status: 'disconnected',
  lastEvent: null,
  toasts: [],
  dismissToast: () => {},
});

export const useRealtimeSync = () => useContext(RealtimeSyncContext);

interface RealtimeSyncProviderProps {
  children: React.ReactNode;
}

export const RealtimeSyncProvider: React.FC<RealtimeSyncProviderProps> = ({ children }) => {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<RealtimeSyncStatus>('connecting');
  const [lastEvent, setLastEvent] = useState<{ event: string; data: any; timestamp: string } | null>(null);
  const [toasts, setToasts] = useState<RealtimeToast[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback((toast: Omit<RealtimeToast, 'id' | 'timestamp'>) => {
    const id = `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
    const newToast: RealtimeToast = {
      ...toast,
      id,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    };
    setToasts((prev) => [...prev.slice(-4), newToast]); // Keep max 5 toasts

    // Auto-dismiss after 6 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 6000);
  }, []);

  const handleIncomingEvent = useCallback(
    (eventType: string, data: any) => {
      const now = new Date().toISOString();
      setLastEvent({ event: eventType, data, timestamp: now });

      switch (eventType) {
        case 'conference:submitted':
          // Refresh Admin review queue and Organizer conferences
          queryClient.invalidateQueries({ queryKey: ['admin', 'conferences'] });
          queryClient.invalidateQueries({ queryKey: ['admin', 'overview'] });
          queryClient.invalidateQueries({ queryKey: ['organizer', 'conferences'] });
          addToast({
            type: 'info',
            title: 'Conference Submitted',
            message: `"${data?.title || 'A conference'}" was submitted for administrative review.`,
          });
          break;

        case 'conference:approved':
        case 'conference:decision':
          // Refresh across all 3 panels: Admin, Organizer, Attendee
          queryClient.invalidateQueries({ queryKey: ['admin', 'conferences'] });
          queryClient.invalidateQueries({ queryKey: ['organizer', 'conferences'] });
          if (data?.conference_id) {
            queryClient.invalidateQueries({ queryKey: ['organizer', 'conference', data.conference_id] });
          }
          queryClient.invalidateQueries({ queryKey: ['conferences'] });
          queryClient.invalidateQueries({ queryKey: ['sessions'] });

          if (data?.status === 'PUBLISHED' || eventType === 'conference:approved') {
            addToast({
              type: 'success',
              title: 'Conference Published 🎉',
              message: `"${data?.title || 'Conference'}" is now approved and live on the Public Agenda.`,
            });
          } else if (data?.status === 'CHANGES_REQUESTED') {
            addToast({
              type: 'warning',
              title: 'Changes Requested',
              message: `Review feedback provided for "${data?.title || 'Conference'}".`,
            });
          } else if (data?.status === 'REJECTED') {
            addToast({
              type: 'alert',
              title: 'Conference Submission Rejected',
              message: `"${data?.title || 'Conference'}" was rejected.`,
            });
          }
          break;

        case 'conference:created':
        case 'conference:updated':
          queryClient.invalidateQueries({ queryKey: ['organizer', 'conferences'] });
          if (data?.conference_id) {
            queryClient.invalidateQueries({ queryKey: ['organizer', 'conference', data.conference_id] });
          }
          queryClient.invalidateQueries({ queryKey: ['admin', 'conferences'] });
          break;

        case 'session:created':
        case 'session:updated':
        case 'session:deleted':
          if (data?.conference_id) {
            queryClient.invalidateQueries({ queryKey: ['organizer', 'conference', data.conference_id] });
          }
          queryClient.invalidateQueries({ queryKey: ['sessions'] });
          break;

        case 'organizer:verified':
          queryClient.invalidateQueries({ queryKey: ['admin', 'organizers'] });
          queryClient.invalidateQueries({ queryKey: ['organizer', 'me'] });
          addToast({
            type: 'info',
            title: 'Organizer Status Updated',
            message: `Verification status changed to ${data?.verification_status || 'updated'}.`,
          });
          break;

        case 'proposal:created':
          queryClient.invalidateQueries({ queryKey: ['proposals'] });
          queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          if (data?.conversation_id) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', data.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ['conversation', data.conversation_id] });
          }
          addToast({
            type: 'info',
            title: 'Commercial Proposal Submitted 📜',
            message: `"${data?.title || 'Commercial Agreement'}" has been submitted for review.`,
          });
          break;

        case 'proposal:approved':
        case 'proposal:reviewed':
          queryClient.invalidateQueries({ queryKey: ['proposals'] });
          queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          if (data?.proposal_id) {
            queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
          }
          if (data?.conversation_id) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', data.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ['conversation', data.conversation_id] });
          }
          if (data?.status === 'MUTUALLY_APPROVED' || eventType === 'proposal:approved') {
            addToast({
              type: 'success',
              title: 'Proposal Mutually Approved! 🎉',
              message: `"${data?.title || 'Agreement'}" is approved. Contact credentials unlocked!`,
            });
          } else {
            addToast({
              type: 'info',
              title: 'Proposal Approved by Counterparty ✓',
              message: `Approval committed for "${data?.title || 'Commercial Agreement'}".`,
            });
          }
          break;

        case 'proposal:countered':
          queryClient.invalidateQueries({ queryKey: ['proposals'] });
          queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          if (data?.proposal_id) {
            queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
          }
          if (data?.conversation_id) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', data.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ['conversation', data.conversation_id] });
          }
          addToast({
            type: 'warning',
            title: 'Counter-Offer Received 🔄',
            message: `New revision (Rev ${data?.revision_number || ''}) submitted for "${data?.title || 'Agreement'}".`,
          });
          break;

        case 'proposal:rejected':
          queryClient.invalidateQueries({ queryKey: ['proposals'] });
          queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          if (data?.proposal_id) {
            queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
          }
          if (data?.conversation_id) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', data.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ['conversation', data.conversation_id] });
          }
          addToast({
            type: 'alert',
            title: 'Proposal Declined ✕',
            message: `Proposal "${data?.title || 'Commercial Agreement'}" was declined.`,
          });
          break;

        case 'proposal:withdrawn':
          queryClient.invalidateQueries({ queryKey: ['proposals'] });
          queryClient.invalidateQueries({ queryKey: ['proposals', 'header-badge'] });
          if (data?.proposal_id) {
            queryClient.invalidateQueries({ queryKey: ['proposal', data.proposal_id] });
          }
          if (data?.conversation_id) {
            queryClient.invalidateQueries({ queryKey: ['proposals', 'conversation', data.conversation_id] });
            queryClient.invalidateQueries({ queryKey: ['conversation', data.conversation_id] });
          }
          addToast({
            type: 'info',
            title: 'Proposal Withdrawn ↩',
            message: `Proposal was withdrawn by the author.`,
          });
          break;

        case 'brochure:viewed':
        case 'brochure:page_read':
          queryClient.invalidateQueries({ queryKey: ['admin', 'brochure-analytics'] });
          queryClient.invalidateQueries({ queryKey: ['my-brochure', 'analytics'] });
          queryClient.invalidateQueries({ queryKey: ['my-brochure'] });
          break;

        default:
          break;
      }
    },
    [queryClient, addToast]
  );

  useEffect(() => {
    if (typeof window === 'undefined' || !('EventSource' in window)) {
      setStatus('disconnected');
      return;
    }

    let isMounted = true;

    const connectSSE = () => {
      if (!isMounted) return;

      try {
        setStatus('connecting');
        const sseUrl = '/converge-api/v1/events/stream';
        const es = new EventSource(sseUrl, { withCredentials: true });
        eventSourceRef.current = es;

        es.onopen = () => {
          if (isMounted) {
            setStatus('connected');
          }
        };

        es.addEventListener('connected', () => {
          if (isMounted) {
            setStatus('connected');
          }
        });

        // Register custom listeners for each event type
        const events = [
          'conference:submitted',
          'conference:approved',
          'conference:decision',
          'conference:changes_requested',
          'conference:rejected',
          'conference:created',
          'conference:updated',
          'session:created',
          'session:updated',
          'session:deleted',
          'organizer:verified',
          'proposal:created',
          'proposal:approved',
          'proposal:reviewed',
          'proposal:countered',
          'proposal:rejected',
          'proposal:withdrawn',
          'brochure:viewed',
          'brochure:page_read',
        ];

        events.forEach((evtName) => {
          es.addEventListener(evtName, (event: MessageEvent) => {
            if (!isMounted) return;
            try {
              const parsed = JSON.parse(event.data);
              handleIncomingEvent(evtName, parsed);
            } catch (err) {
              console.warn('Failed to parse SSE event data', err);
            }
          });
        });

        es.onerror = () => {
          if (!isMounted) return;
          setStatus('disconnected');
          es.close();

          // Exponential backoff reconnect
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMounted) connectSSE();
          }, 5000);
        };
      } catch (err) {
        if (isMounted) {
          setStatus('disconnected');
        }
      }
    };

    connectSSE();

    return () => {
      isMounted = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [handleIncomingEvent]);

  return (
    <RealtimeSyncContext.Provider value={{ status, lastEvent, toasts, dismissToast }}>
      {children}
    </RealtimeSyncContext.Provider>
  );
};
