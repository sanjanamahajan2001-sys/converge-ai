import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProfileEdit } from '@/routes/ProfileEdit';
import * as profileApi from '@/lib/api/profile';
import { AuthProvider } from '@/lib/auth/AuthContext';
import * as authApi from '@/lib/api/auth';

function renderProfileEdit() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter>
          <ProfileEdit />
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe('ProfileEdit Component', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(authApi, 'getCurrentUser').mockResolvedValue({
      id: '11111111-1111-1111-1111-111111111111',
      username: 'maria_rossi',
      email: 'maria@example.com',
      full_name: 'Maria Rossi',
      company_name: 'Italcementi',
      job_title: 'Plant Manager',
      is_active: true,
    });
    vi.spyOn(profileApi, 'getHobbiesCatalog').mockResolvedValue([
      'Tea / Coffee',
      'Casual Conversations',
      'Technical Deep-dives',
      'Sustainability & Decarbonization Policy',
      'Equipment & Exhibition Walking Tours',
    ]);
    vi.spyOn(profileApi, 'getMoodsCatalog').mockResolvedValue([
      'Ready to network',
      'Open to casual conversation',
      'Conference-focused',
    ]);
  });

  it('renders form and loads catalog options', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Existing bio summary',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: ['Tea / Coffee'],
      topics: ['Kiln Decarbonization'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    await waitFor(() => {
      expect(screen.getByLabelText(/participation intent/i)).toBeInTheDocument();
      expect(screen.getByDisplayValue('Existing bio summary')).toBeInTheDocument();
      expect(screen.getAllByText('Tea / Coffee').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/🏷️ Kiln Decarbonization/i)).toBeInTheDocument();
    });
  });

  it('toggles catalog hobbies and adds custom topic keyword', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'CASUAL',
      bio_summary: 'Updated bio',
      availability: 'IN_SESSION',
      allow_agent_matching: true,
      hobbies: ['Tea / Coffee'],
      topics: ['Alternative Fuels'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Tea \/ Coffee/i })).toBeInTheDocument();
    });

    // 1. Toggle catalog hobby
    const hobbyBtn = screen.getByRole('button', { name: /Tea \/ Coffee/i });
    fireEvent.click(hobbyBtn);

    // 2. Add topic keyword
    const topicInput = screen.getByPlaceholderText(/e\.g\. Kiln Automation/i);
    fireEvent.change(topicInput, { target: { value: 'Alternative Fuels' } });
    fireEvent.click(screen.getByRole('button', { name: /add keyword/i }));

    // 3. Toggle consent checkbox
    const consentCheckbox = screen.getByLabelText(/consent to autonomous agent matching/i);
    expect(consentCheckbox).not.toBeChecked();
    fireEvent.click(consentCheckbox);
    expect(consentCheckbox).toBeChecked();

    // 4. Update bio
    const bioInput = screen.getByPlaceholderText(/brief professional background/i);
    fireEvent.change(bioInput, { target: { value: 'Updated bio' } });

    // 5. Submit
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          job_title: 'Plant Manager',
          company_name: 'Italcementi',
          intent: 'NETWORKING',
          bio_summary: 'Updated bio',
          availability: 'AVAILABLE',
          allow_agent_matching: true,
          hobbies: ['Tea / Coffee'],
          topics: ['Alternative Fuels'],
        })
      );
      // Verify no prohibited fields sent
      const callArg = updateSpy.mock.calls[0][0];
      expect(callArg).not.toHaveProperty('user_id');
      expect(callArg).not.toHaveProperty('id');
      expect(callArg).not.toHaveProperty('role');
    });
  });

  it('splits comma-separated keywords and auto-flushes uncommitted inputs on form submit', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: ['Badminton', 'Cycling'],
      topics: ['tea', 'tech', 'system', 'timepass'],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/e\.g\. Kiln Automation/i)).toBeInTheDocument();
    });

    // Type comma-separated custom hobby and click Add
    const hobbyInput = screen.getByPlaceholderText(/e\.g\. Architectural Concrete/i);
    fireEvent.change(hobbyInput, { target: { value: 'Badminton, Cycling' } });
    fireEvent.click(screen.getByRole('button', { name: /^add$/i }));

    // Verify both hobby badges rendered
    expect(screen.getByText('Badminton')).toBeInTheDocument();
    expect(screen.getByText('Cycling')).toBeInTheDocument();

    // Type comma-separated topic in input and submit form directly (WITHOUT clicking Add Keyword)
    const topicInput = screen.getByPlaceholderText(/e\.g\. Kiln Automation/i);
    fireEvent.change(topicInput, { target: { value: 'tea, tech, system, timepass' } });

    // Click Save Profile
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          hobbies: ['Badminton', 'Cycling'],
          topics: ['tea', 'tech', 'system', 'timepass'],
        })
      );
    });
  });

  it('displays character counter for bio summary and warns on length', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Short bio',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    await waitFor(() => {
      expect(screen.getByText('9 / 500')).toBeInTheDocument();
    });
  });

  it('selects informal mood and submits current_mood preference', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      current_mood: null,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      current_mood: 'Ready to network',
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Ready to network/i })).toBeInTheDocument();
    });

    // Click curated mood button
    fireEvent.click(screen.getByRole('button', { name: /Ready to network/i }));

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          current_mood: 'Ready to network',
        })
      );
    });
  });

  it('validates DD-MM-YYYY date of birth and submits gender and date_of_birth', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Bio',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      gender: 'Female',
      date_of_birth: '15-08-1995',
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: 'Bio',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      gender: 'Male',
      date_of_birth: '24-12-1990',
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    // 1. Verify prepopulation of existing profile fields
    await waitFor(() => {
      expect(screen.getByLabelText(/gender/i)).toHaveValue('Female');
      expect(screen.getByLabelText(/date of birth/i)).toHaveValue('15-08-1995');
    });

    // 2. Test invalid date format validation
    const dobInput = screen.getByLabelText(/date of birth/i);
    fireEvent.change(dobInput, { target: { value: '1995-08-15' } }); // YYYY-MM-DD instead of DD-MM-YYYY
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(screen.getByText(/Date of birth must be in DD-MM-YYYY format/i)).toBeInTheDocument();
      expect(updateSpy).not.toHaveBeenCalled();
    });

    // 3. Update with valid DD-MM-YYYY date and change gender
    fireEvent.change(dobInput, { target: { value: '24-12-1990' } });
    fireEvent.change(screen.getByLabelText(/gender/i), { target: { value: 'Male' } });
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          gender: 'Male',
          date_of_birth: '24-12-1990',
        })
      );
    });
  });

  it('updates and saves user location with venue name and coordinates', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      location: null,
      location_lat: null,
      location_lng: null,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });
    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      location: 'Jio World Convention Centre, Mumbai',
      location_lat: 19.0657,
      location_lng: 72.8688,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();
    await waitFor(() => {
      expect(screen.getByLabelText(/Conference Venue \/ City Location/i)).toBeInTheDocument();
    });

    const locationInput = screen.getByLabelText(/Conference Venue \/ City Location/i);
    fireEvent.change(locationInput, { target: { value: 'Jio World Convention Centre, Mumbai' } });

    // Verify pick on map button is rendered and device GPS is removed
    expect(screen.getByRole('button', { name: /Pick on Map/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Current GPS/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          location: 'Jio World Convention Centre, Mumbai',
        })
      );
    });
  });

  it('allows editing professional title, company name, and natural language mood up to 255 chars', async () => {
    vi.spyOn(profileApi, 'getMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      job_title: 'Procurement Specialist',
      company_name: 'InfraTech Solutions',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    const updateSpy = vi.spyOn(profileApi, 'updateMyProfile').mockResolvedValue({
      user_id: '11111111-1111-1111-1111-111111111111',
      job_title: 'Procurement Director',
      company_name: 'InfraTech EPC Solutions Ltd',
      intent: 'NETWORKING',
      bio_summary: '',
      availability: 'AVAILABLE',
      allow_agent_matching: false,
      current_mood: 'Connecting with project contractors for dedicated fleet haulage contracts.',
      hobbies: [],
      topics: [],
      created_at: '2026-10-23T10:00:00Z',
      updated_at: '2026-10-23T10:00:00Z',
    });

    renderProfileEdit();

    // 1. Edit Job Title and Company
    const jobTitleInput = await screen.findByLabelText(/Professional Title \/ Position/i);
    const companyInput = screen.getByLabelText(/Company \/ Organization Name/i);
    fireEvent.change(jobTitleInput, { target: { value: 'Procurement Director' } });
    fireEvent.change(companyInput, { target: { value: 'InfraTech EPC Solutions Ltd' } });

    // 2. Set long natural language mood (74 characters)
    const moodInput = screen.getByPlaceholderText(/Connecting with project contractors/i);
    fireEvent.change(moodInput, {
      target: { value: 'Connecting with project contractors for dedicated fleet haulage contracts.' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Set Custom/i }));

    // 3. Save
    fireEvent.click(screen.getByRole('button', { name: /save profile/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          job_title: 'Procurement Director',
          company_name: 'InfraTech EPC Solutions Ltd',
          current_mood: 'Connecting with project contractors for dedicated fleet haulage contracts.',
        })
      );
    });
  });
});
