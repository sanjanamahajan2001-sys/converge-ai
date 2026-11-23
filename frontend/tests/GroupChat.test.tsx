import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Conversations } from '@/routes/Conversations';
import { GroupConversationDetailRoute } from '@/routes/GroupConversationDetail';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import { conversationApi } from '@/lib/api/conversation';
import { groupConversationApi } from '@/lib/api/groupConversation';
import { GroupConversation, GroupConversationDetail } from '@/types/groupConversation';

const mockUser = {
  id: 'user-host-1111',
  username: 'sanjana_host',
  email: 'sanjana@example.com',
  full_name: 'Sanjana Maahi',
  is_active: true,
};

const mockCircles: GroupConversation[] = [
  {
    id: 'circle-1234',
    title: 'Low-Carbon Cement Standards Circle',
    topic_context: 'Harmonizing calcined clay and LC3 formulations for western corridor infrastructure.',
    host_id: 'user-host-1111',
    host_name: 'Sanjana Maahi',
    status: 'ACTIVE',
    max_turns: 25,
    current_turn: 5,
    ai_turns_budget: 4,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    concluded_at: null,
    members_count: 3,
    members: [
      {
        user_id: 'user-host-1111',
        username: 'sanjana_host',
        full_name: 'Sanjana Maahi',
        company_name: 'InfraTech EPC',
        job_title: 'Head of Sourcing',
        role: 'HOST',
        joined_at: new Date().toISOString(),
        last_read_turn: 5,
      },
      {
        user_id: 'user-peer-2222',
        username: 'vikram_singh',
        full_name: 'Vikram Singhania',
        company_name: 'Deccan Clinker Ltd',
        job_title: 'Chief Commercial Officer',
        role: 'MEMBER',
        joined_at: new Date().toISOString(),
        last_read_turn: 4,
      },
      {
        user_id: 'user-peer-3333',
        username: 'maahi_tech',
        full_name: 'Maahi Patel',
        company_name: 'GreenBind Pozzolans',
        job_title: 'Technical Director',
        role: 'MEMBER',
        joined_at: new Date().toISOString(),
        last_read_turn: 4,
      },
    ],
    last_message: {
      id: 'msg-turn-4',
      group_id: 'circle-1234',
      sender_id: 'user-host-1111',
      sender_username: 'sanjana_host',
      sender_full_name: 'Sanjana Maahi',
      sender_type: 'AGENT',
      turn_index: 4,
      content: 'Virtual Representative introductions complete. The room is now officially open for direct human discussion!',
      message_type: 'TEXT',
      created_at: new Date().toISOString(),
    },
  },
];

const mockCircleDetailActiveRoundtable: GroupConversationDetail = {
  ...mockCircles[0],
  current_turn: 2, // AI Roundtable active (turns <= N + 1 = 4)
  messages: [
    {
      id: 'msg-0',
      group_id: 'circle-1234',
      sender_id: null,
      sender_type: 'SYSTEM',
      turn_index: 0,
      content: "Thematic Networking Circle 'Low-Carbon Cement Standards Circle' initiated with 3 delegates. Discussion limit: 25 turns.",
      created_at: new Date().toISOString(),
    },
    {
      id: 'msg-1',
      group_id: 'circle-1234',
      sender_id: 'user-host-1111',
      sender_full_name: 'Sanjana Maahi',
      sender_type: 'AGENT',
      turn_index: 1,
      content: 'Hello everyone! I am the Virtual Representative for Sanjana Maahi. Welcome to our circle!',
      created_at: new Date().toISOString(),
    },
    {
      id: 'msg-2',
      group_id: 'circle-1234',
      sender_id: 'user-peer-2222',
      sender_full_name: 'Vikram Singhania',
      sender_type: 'AGENT',
      turn_index: 2,
      content: 'Greetings! Representing Vikram Singhania, Chief Commercial Officer at Deccan Clinker Ltd.',
      created_at: new Date().toISOString(),
    },
  ],
};

const mockCircleDetailOpenDiscussion: GroupConversationDetail = {
  ...mockCircles[0],
  current_turn: 5, // Turns > N + 1 (4), human discussion unlocked!
  messages: [
    ...mockCircleDetailActiveRoundtable.messages,
    {
      id: 'msg-3',
      group_id: 'circle-1234',
      sender_id: 'user-peer-3333',
      sender_full_name: 'Maahi Patel',
      sender_type: 'AGENT',
      turn_index: 3,
      content: 'Greetings! Representing Maahi Patel, Technical Director at GreenBind Pozzolans.',
      created_at: new Date().toISOString(),
    },
    {
      id: 'msg-4',
      group_id: 'circle-1234',
      sender_id: 'user-host-1111',
      sender_full_name: 'Sanjana Maahi',
      sender_type: 'AGENT',
      turn_index: 4,
      content: 'Thank you representatives! Floor is now officially open for direct human discussion.',
      created_at: new Date().toISOString(),
    },
  ],
};

describe('Group Chat UI & Networking Circles (Phase 4)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks();
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(mockUser);
    vi.spyOn(conversationApi, 'listConversations').mockResolvedValue([]);
    vi.spyOn(groupConversationApi, 'listCircles').mockResolvedValue(mockCircles);
    vi.spyOn(groupConversationApi, 'getCircle').mockResolvedValue(mockCircleDetailOpenDiscussion);
    vi.spyOn(groupConversationApi, 'sendMessage').mockResolvedValue({
      id: 'msg-turn-5',
      group_id: 'circle-1234',
      sender_id: mockUser.id,
      sender_username: mockUser.username,
      sender_full_name: mockUser.full_name,
      sender_type: 'PARTICIPANT',
      turn_index: 5,
      content: 'Hello Vikram and Maahi, glad to connect in this working circle.',
      created_at: new Date().toISOString(),
    });
    vi.spyOn(groupConversationApi, 'closeCircle').mockResolvedValue({
      ...mockCircleDetailOpenDiscussion,
      status: 'COMPLETED',
      concluded_at: new Date().toISOString(),
    });
    vi.spyOn(groupConversationApi, 'deleteCircle').mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders Conversations tab navigation with Direct Messages and Networking Circles', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations']}>
            <Conversations />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    expect(await screen.findByText('Conversations')).toBeInTheDocument();
    expect(screen.getByText('Direct Messages (1-on-1)')).toBeInTheDocument();
    expect(screen.getByText('Networking Circles (Group)')).toBeInTheDocument();

    // Switch to Networking Circles tab
    fireEvent.click(screen.getByText('Networking Circles (Group)'));

    // Verify Circle card is rendered
    expect(await screen.findByText('Low-Carbon Cement Standards Circle')).toBeInTheDocument();
    expect(screen.getByText('3 Delegates')).toBeInTheDocument();
    expect(screen.getByText('Host: Sanjana Maahi')).toBeInTheDocument();
    expect(screen.getByText('Join Circle →')).toBeInTheDocument();
  });

  it('renders Group Chat Room with member roster, AI introduction transcripts, and turn progress', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Verify Title and Roster pill
    expect(await screen.findByText('Low-Carbon Cement Standards Circle')).toBeInTheDocument();
    expect(screen.getByText('3 Delegates')).toBeInTheDocument();

    // Verify Progress bar indicator
    expect(screen.getByText(/Roundtable Progress:/)).toBeInTheDocument();
    expect(screen.getByText(/20 human turns left/)).toBeInTheDocument();

    // Verify System and AI representative transcripts
    expect(screen.getByText(/Discussion limit: 25 turns/)).toBeInTheDocument();
    expect(screen.getAllByText(/Sanjana Maahi's Virtual Representative/).length).toBe(2);
    expect(screen.getByText(/Vikram Singhania's Virtual Representative/)).toBeInTheDocument();

    // Verify Open floor banner is shown when current_turn > N+1
    expect(screen.getByText(/Roundtable Introductions Complete • Floor is open for manual discussion/)).toBeInTheDocument();
  });

  it('enforces lockout while AI Representative roundtable is active (turns <= N+1)', async () => {
    vi.spyOn(groupConversationApi, 'getCircle').mockResolvedValue(mockCircleDetailActiveRoundtable);

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Verify active AI Protocol banner
    expect(await screen.findByText(/Virtual Roundtable Protocol Active/)).toBeInTheDocument();

    // Verify input is disabled
    const input = screen.getByPlaceholderText(/Manual messaging locked during AI Representative roundtable/);
    expect(input).toBeDisabled();
    expect(screen.getByRole('button', { name: /Send/i })).toBeDisabled();
  });

  it('allows human messaging once AI roundtable synthesis is complete', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Input should be enabled
    const input = await screen.findByPlaceholderText('Contribute to the circle discussion...');
    expect(input).not.toBeDisabled();

    // Type and send message
    fireEvent.change(input, { target: { value: 'Hello Vikram and Maahi, glad to connect in this working circle.' } });
    const sendBtn = screen.getByRole('button', { name: /Send/i });
    expect(sendBtn).not.toBeDisabled();
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(groupConversationApi.sendMessage).toHaveBeenCalledWith(
        'circle-1234',
        'Hello Vikram and Maahi, glad to connect in this working circle.'
      );
    });
  });

  it('opens participant roster modal when clicking delegate count pill', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    const rosterBtn = await screen.findByRole('button', { name: /3 Delegates/i });
    fireEvent.click(rosterBtn);

    // Verify Roster modal content
    expect(await screen.findByText('Circle Participants (3)')).toBeInTheDocument();
    expect(screen.getByText('Vikram Singhania')).toBeInTheDocument();
    expect(screen.getAllByText(/Deccan Clinker Ltd/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Maahi Patel')).toBeInTheDocument();
    expect(screen.getAllByText(/GreenBind Pozzolans/).length).toBeGreaterThanOrEqual(1);
  });

  it('renders host-exclusive action buttons (Close Circle and Delete Circle) for the circle host', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Host should see Host badge and action controls
    expect(await screen.findByText('👑 Host')).toBeInTheDocument();
    const closeBtn = screen.getByRole('button', { name: /🛑 Close Circle/i });
    const deleteBtn = screen.getByRole('button', { name: /🗑️ Delete Circle/i });
    expect(closeBtn).toBeInTheDocument();
    expect(deleteBtn).toBeInTheDocument();

    // Leave Circle should NOT be visible to host
    expect(screen.queryByRole('button', { name: /Leave Circle/i })).not.toBeInTheDocument();

    // Clicking Close Circle opens confirmation modal
    fireEvent.click(closeBtn);
    expect(await screen.findByText('Conclude Networking Circle?')).toBeInTheDocument();
    const confirmCloseBtn = screen.getByRole('button', { name: /🛑 Conclude Circle/i });
    fireEvent.click(confirmCloseBtn);

    await waitFor(() => {
      expect(groupConversationApi.closeCircle).toHaveBeenCalledWith('circle-1234');
    });
  });

  it('renders Leave Circle button for non-host members', async () => {
    const nonHostUser = {
      id: 'user-peer-2222',
      username: 'vikram_singh',
      email: 'vikram@example.com',
      full_name: 'Vikram Singhania',
      is_active: true,
    };
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(nonHostUser);

    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter initialEntries={['/conversations/circles/circle-1234']}>
            <Routes>
              <Route path="/conversations/circles/:circleId" element={<GroupConversationDetailRoute />} />
            </Routes>
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

    // Non-host should see Leave Circle button
    const leaveBtn = await screen.findByRole('button', { name: /Leave Circle/i });
    expect(leaveBtn).toBeInTheDocument();

    // Close and Delete buttons should NOT be visible
    expect(screen.queryByRole('button', { name: /🛑 Close Circle/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /🗑️ Delete Circle/i })).not.toBeInTheDocument();
  });
});
