import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Conversations } from '@/routes/Conversations';
import { ConversationDetailRoute } from '@/routes/ConversationDetail';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import { conversationApi } from '@/lib/api/conversation';
import { Conversation, ConversationDetail, Message } from '@/types/conversation';

const mockUser = {
  id: '11111111-1111-1111-1111-111111111111',
  username: 'test_user',
  email: 'test@example.com',
  full_name: 'Test Attendee',
  is_active: true,
};

const mockConversations: Conversation[] = [
  {
    id: 'conv-1111-2222',
    initiator_id: '11111111-1111-1111-1111-111111111111',
    target_id: '22222222-2222-2222-2222-222222222222',
    status: 'ACTIVE',
    match_score: 0.88,
    terminal_outcome: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    concluded_at: null,
    other_participant_id: '22222222-2222-2222-2222-222222222222',
    other_participant_name: 'Dr. Sarah Connor',
    message_count: 5,
    last_message: {
      id: 'msg-5',
      conversation_id: 'conv-1111-2222',
      sender_id: '22222222-2222-2222-2222-222222222222',
      sender_type: 'PARTICIPANT',
      turn_index: 4,
      content: 'Looking forward to meeting at the CCUS keynote!',
      created_at: new Date().toISOString(),
    },
  },
  {
    id: 'conv-1111-3333',
    initiator_id: '33333333-3333-3333-3333-333333333333',
    target_id: '11111111-1111-1111-1111-111111111111',
    status: 'INVITED',
    match_score: 0.75,
    terminal_outcome: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    concluded_at: null,
    other_participant_id: '33333333-3333-3333-3333-333333333333',
    other_participant_name: 'Alex Rivera',
    message_count: 0,
    last_message: null,
  },
];

const mockConversationDetail: ConversationDetail = {
  ...mockConversations[0],
  messages: [
    {
      id: 'msg-1',
      conversation_id: 'conv-1111-2222',
      sender_id: '11111111-1111-1111-1111-111111111111',
      sender_type: 'PARTICIPANT',
      turn_index: 0,
      content: 'Hi Sarah, saw your profile on cement decarbonization!',
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
    {
      id: 'msg-2',
      conversation_id: 'conv-1111-2222',
      sender_id: '22222222-2222-2222-2222-222222222222',
      sender_type: 'PARTICIPANT',
      turn_index: 1,
      content: 'Looking forward to meeting at the CCUS keynote!',
      created_at: new Date().toISOString(),
    },
  ],
};

function renderComponent(ui: React.ReactElement, initialEntry = '/conversations') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[initialEntry]}>
          {ui}
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('Conversations and Messaging UX', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(mockUser);
    vi.spyOn(conversationApi, 'listConversations').mockResolvedValue(mockConversations);
    vi.spyOn(conversationApi, 'getConversation').mockResolvedValue(mockConversationDetail);
  });

  it('renders conversations list with attendee names, statuses, and quota badge', async () => {
    renderComponent(<Conversations />);

    expect(await screen.findByText('Conversations')).toBeInTheDocument();
    expect(screen.getByText('2 / 3')).toBeInTheDocument();
    expect(screen.getByText('Dr. Sarah Connor')).toBeInTheDocument();
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('Alex Rivera')).toBeInTheDocument();
    expect(screen.getByText('INVITED')).toBeInTheDocument();
    expect(screen.getByText(/Looking forward to meeting/)).toBeInTheDocument();
  });

  it('renders empty state when no conversations exist', async () => {
    vi.spyOn(conversationApi, 'listConversations').mockResolvedValue([]);
    renderComponent(<Conversations />);

    expect(await screen.findByText('No Conversations Yet')).toBeInTheDocument();
    expect(screen.getByText('0 / 3')).toBeInTheDocument();
  });

  it('renders chat detail view with partner name, messages, and turn count', async () => {
    renderComponent(
      <Routes>
        <Route path="/conversations/:conversationId" element={<ConversationDetailRoute />} />
      </Routes>,
      '/conversations/conv-1111-2222'
    );

    expect(await screen.findByText('Dr. Sarah Connor')).toBeInTheDocument();
    expect(screen.getByText('2 / 30 turns used')).toBeInTheDocument();
    expect(screen.getByText('Hi Sarah, saw your profile on cement decarbonization!')).toBeInTheDocument();
    expect(screen.getByText('Looking forward to meeting at the CCUS keynote!')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Type a message/)).toBeInTheDocument();
  });

  it('sends message turn successfully and displays in stream', async () => {
    const newMessage: Message = {
      id: 'msg-3',
      conversation_id: 'conv-1111-2222',
      sender_id: '11111111-1111-1111-1111-111111111111',
      sender_type: 'PARTICIPANT',
      turn_index: 2,
      content: 'Let us meet by Hall B at 3pm!',
      created_at: new Date().toISOString(),
    };
    const sendSpy = vi.spyOn(conversationApi, 'sendMessage').mockResolvedValue(newMessage);

    renderComponent(
      <Routes>
        <Route path="/conversations/:conversationId" element={<ConversationDetailRoute />} />
      </Routes>,
      '/conversations/conv-1111-2222'
    );

    const input = await screen.findByPlaceholderText(/Type a message/);
    fireEvent.change(input, { target: { value: 'Let us meet by Hall B at 3pm!' } });
    const sendButton = screen.getByRole('button', { name: 'Send' });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(sendSpy).toHaveBeenCalledWith('conv-1111-2222', 'Let us meet by Hall B at 3pm!');
    });
    expect(await screen.findByText('Let us meet by Hall B at 3pm!')).toBeInTheDocument();
  });

  it('renders distinct virtual representative badges and agent status banner when agent messages exist', async () => {
    const agentConversationDetail: ConversationDetail = {
      ...mockConversations[0],
      other_participant_mood: 'Ready to network',
      messages: [
        {
          id: 'agent-msg-1',
          conversation_id: 'conv-1111-2222',
          sender_id: '11111111-1111-1111-1111-111111111111',
          sender_type: 'AGENT',
          turn_index: 0,
          content: 'Hello Dr. Sarah Connor, I am representing Test Attendee. We noticed mutual interest in cement decarbonization.',
          created_at: new Date(Date.now() - 3600000).toISOString(),
        },
        {
          id: 'agent-msg-2',
          conversation_id: 'conv-1111-2222',
          sender_id: '22222222-2222-2222-2222-222222222222',
          sender_type: 'AGENT',
          turn_index: 1,
          content: 'Thank you for reaching out! Dr. Sarah Connor is focusing on CCUS initiatives.',
          created_at: new Date().toISOString(),
        },
      ],
    };
    vi.spyOn(conversationApi, 'getConversation').mockResolvedValue(agentConversationDetail);

    renderComponent(
      <Routes>
        <Route path="/conversations/:conversationId" element={<ConversationDetailRoute />} />
      </Routes>,
      '/conversations/conv-1111-2222'
    );

    // Verify Virtual Representative Badges
    expect(await screen.findByText("My Virtual Representative")).toBeInTheDocument();
    expect(screen.getByText("Dr. Sarah Connor's Virtual Representative")).toBeInTheDocument();

    // Verify Agent Status Banner
    expect(screen.getByText(/Virtual Representatives are aligning parameters/i)).toBeInTheDocument();

    // Verify Partner Mood Preference Chip
    expect(screen.getByText(/Dr\. Sarah Connor's Conversation Preference:/i)).toBeInTheDocument();
    expect(screen.getByText('"Ready to network"')).toBeInTheDocument();

    // Verify on-demand trigger button is rendered when turnCount < 5
    expect(screen.getByRole('button', { name: /Trigger Representative Turn/i })).toBeInTheDocument();
  });

  it('hides location button and renders plain text content when location sharing is kept in profile only', async () => {
    const locationConversationDetail: ConversationDetail = {
      ...mockConversations[0],
      messages: [
        {
          id: 'msg-loc-1',
          conversation_id: 'conv-1111-2222',
          sender_id: '22222222-2222-2222-2222-222222222222',
          sender_type: 'PARTICIPANT',
          turn_index: 0,
          content: '📍 Shared Location: Grand Ballroom Foyer',
          message_type: 'LOCATION',
          location_payload: {
            latitude: 19.076,
            longitude: 72.8777,
            name: 'Grand Ballroom Foyer',
            address: 'Jio World Convention Centre, BKC, Mumbai',
            map_url: 'https://www.google.com/maps/search/?api=1&query=19.076,72.8777',
          },
          created_at: new Date().toISOString(),
        },
      ],
    };
    vi.spyOn(conversationApi, 'getConversation').mockResolvedValue(locationConversationDetail);

    renderComponent(
      <Routes>
        <Route path="/conversations/:conversationId" element={<ConversationDetailRoute />} />
      </Routes>,
      '/conversations/conv-1111-2222'
    );

    // Verify plain text content is rendered without location card details
    expect(await screen.findByText('📍 Shared Location: Grand Ballroom Foyer')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Share Location/i })).not.toBeInTheDocument();
  });

  it('verifies zero internal development phase or workstream terminology is rendered', async () => {
    renderComponent(<Conversations />);
    await screen.findByText('Conversations');

    const html = document.body.innerHTML;
    expect(html).not.toMatch(/Phase\s*[1-5]/i);
    expect(html).not.toMatch(/P[1-5]-WS[1-5]/i);
    expect(html).not.toMatch(/GAP-0[1-9]/i);
    expect(html).not.toMatch(/Workstream/i);
  });
});
