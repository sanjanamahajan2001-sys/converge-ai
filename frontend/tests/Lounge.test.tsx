import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Lounge } from '@/routes/Lounge';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';
import { chatroomApi } from '@/lib/api/chatroom';
import { ChatroomDetail } from '@/types/chatroom';

const mockUser = {
  id: 'user-1111',
  username: 'sanjana_m',
  email: 'sanjana@example.com',
  full_name: 'Sanjana Mahajan',
  is_active: true,
};

const mockLoungeData: ChatroomDetail = {
  id: 'lounge-1234',
  conference_id: 'conf-5678',
  name: 'The Networking Lounge',
  slug: 'networking-lounge',
  description: 'Open public lounge for all delegates to hang out, share thoughts, and stay updated during breaks.',
  is_active: true,
  ambient_interval_seconds: 20,
  online_count: 14,
  context: {
    weather: {
      city: 'Mumbai',
      temperature_c: 34,
      condition: 'Clear sky',
      summary: '☀️ Mumbai Weather: Warm 34°C, clear sky.',
      is_live: true,
    },
    traffic: {
      origin: 'Mumbai Airport',
      destination: 'Bandra Kurla Complex',
      duration_mins: 18,
      delay_mins: 4,
      congestion_level: 'MODERATE',
      summary: '🚗 Moderate traffic slowdown (+4m delay) towards venue.',
      is_live: true,
    },
    active_break: 'TEA_BREAK',
    break_location: 'East Concourse Foyer',
  },
  recent_messages: [
    {
      id: 'msg-1',
      chatroom_id: 'lounge-1234',
      sender_id: null,
      sender_type: 'HOST',
      sender_name: 'Virtual Lounge Host',
      content: '🎉 Welcome to the Converge AI Networking Lounge!',
      message_kind: 'WELCOME',
      turn_index: 0,
      metadata_json: null,
      created_at: new Date().toISOString(),
    },
    {
      id: 'msg-2',
      chatroom_id: 'lounge-1234',
      sender_id: 'user-2222',
      sender_type: 'USER',
      sender_name: 'Vikram Patel',
      content: 'Hey everyone, great keynote this morning!',
      message_kind: 'CHAT',
      turn_index: 1,
      metadata_json: null,
      created_at: new Date().toISOString(),
    },
  ],
};

describe('Common Open Lounge Component', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: 0 },
      },
    });

    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue(mockUser);
    vi.spyOn(chatroomApi, 'getActiveLounge').mockResolvedValue(mockLoungeData);
    vi.spyOn(chatroomApi, 'getRecentMessages').mockResolvedValue(mockLoungeData.recent_messages);
    vi.spyOn(chatroomApi, 'pollAmbientTick').mockResolvedValue({
      message_generated: false,
      reason: null,
      message: null,
    });
    vi.spyOn(chatroomApi, 'postMessage').mockImplementation(async (chatroomId, content) => ({
      id: 'msg-new',
      chatroom_id: chatroomId,
      sender_id: mockUser.id,
      sender_type: 'USER',
      sender_name: mockUser.full_name,
      content,
      message_kind: 'CHAT',
      turn_index: 2,
      metadata_json: null,
      created_at: new Date().toISOString(),
    }));

    // Mock scrollIntoView
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderLounge = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <MemoryRouter>
            <Lounge />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    );

  it('renders the lounge hero banner and title', async () => {
    renderLounge();

    await waitFor(() => {
      expect(screen.getByText('The Networking Lounge')).toBeInTheDocument();
    });

    expect(screen.getByText(/A casual, open town square/)).toBeInTheDocument();
    expect(screen.getByText('Live Chatroom')).toBeInTheDocument();
  });

  it('displays environmental context pills: online count, weather, and traffic', async () => {
    renderLounge();

    await waitFor(() => {
      expect(screen.getByText('14')).toBeInTheDocument();
      expect(screen.getByText(/34°C Clear sky/)).toBeInTheDocument();
      expect(screen.getByText(/\+4m Slowdown/)).toBeInTheDocument();
      expect(screen.getByText('TEA BREAK')).toBeInTheDocument();
    });
  });

  it('renders starter prompt chips and populates input when clicked', async () => {
    renderLounge();

    await waitFor(() => {
      expect(screen.getByText(/Who is grabbing tea/)).toBeInTheDocument();
    });

    const chip = screen.getByText(/Who is grabbing tea/);
    fireEvent.click(chip);

    const input = screen.getByPlaceholderText(/Share a thought/i) as HTMLInputElement;
    expect(input.value).toContain('Who is grabbing tea');
  });

  it('dispatches user message when sending from input form', async () => {
    renderLounge();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Share a thought/i)).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Share a thought/i);
    fireEvent.change(input, { target: { value: 'Excited to be here at the lounge!' } });

    const sendBtn = screen.getByRole('button', { name: /Send/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(chatroomApi.postMessage).toHaveBeenCalledWith(
        'lounge-1234',
        'Excited to be here at the lounge!'
      );
    });
  });
});
