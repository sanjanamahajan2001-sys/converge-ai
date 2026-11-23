import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getMyProfile, updateMyProfile, getPublicProfile, getHobbiesCatalog } from '@/lib/api/profile';
import { ApiClientError } from '@/lib/api/client';

describe('Profile API Client', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('getMyProfile fetches /profile/me with credentials and custom header', async () => {
    const mockProfile = {
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Process specialist',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: ['Tea / Coffee'],
      topics: ['Kiln Automation'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockProfile,
    });

    const result = await getMyProfile();
    expect(result).toEqual(mockProfile);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/converge-api/v1/profile/me',
      expect.objectContaining({
        method: 'GET',
        credentials: 'same-origin',
        headers: expect.objectContaining({
          'X-Requested-With': 'XMLHttpRequest',
        }),
      })
    );
  });

  it('updateMyProfile sends PUT request with serialized payload', async () => {
    const updatePayload = {
      intent: 'CASUAL' as const,
      bio_summary: 'Updated bio',
      availability: 'AVAILABLE' as const,
      allow_agent_matching: true,
      hobbies: ['Tea / Coffee'],
      topics: ['Decarbonization'],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ...updatePayload, user_id: '1111', created_at: '', updated_at: '' }),
    });

    await updateMyProfile(updatePayload);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/converge-api/v1/profile/me',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify(updatePayload),
        credentials: 'same-origin',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        }),
      })
    );
  });

  it('getPublicProfile fetches /profile/{id} with URI encoding', async () => {
    const sampleId = '22222222-2222-2222-2222-222222222222';
    const mockPublic = {
      user_id: sampleId,
      full_name: 'Dr. Jane Miller',
      company_name: 'CemTech',
      job_title: 'Chief Chemist',
      intent: 'NETWORKING',
      bio_summary: 'Refractory research',
      availability: 'IN_SESSION',
      hobbies: ['Technical Deep-dives'],
      topics: ['Aluminate Cements'],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockPublic,
    });

    const result = await getPublicProfile(sampleId);
    expect(result.full_name).toBe('Dr. Jane Miller');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      `/converge-api/v1/profile/${sampleId}`,
      expect.anything()
    );
  });

  it('getHobbiesCatalog fetches /profile/catalog/hobbies', async () => {
    const catalog = ['Tea / Coffee', 'Technical Deep-dives'];
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => catalog,
    });

    const result = await getHobbiesCatalog();
    expect(result).toEqual(catalog);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/converge-api/v1/profile/catalog/hobbies',
      expect.anything()
    );
  });

  it('propagates ApiClientError on 404 uninitialized profile', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Participant profile not found. Please initialize your profile.' }),
    });

    await expect(getMyProfile()).rejects.toThrow(ApiClientError);
  });
});
