import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query/client';
import { RealtimeSyncProvider } from '@/lib/events/RealtimeSyncContext';
import { RealtimeToastContainer } from '@/components/common/RealtimeToastContainer';
import { AuthProvider } from '@/lib/auth/AuthContext';
import { AdminAuthProvider } from '@/lib/auth/AdminAuthContext';
import { AppLayout } from '@/components/layout/AppLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { OrganizerProtectedRoute } from '@/components/organizer/OrganizerProtectedRoute';
import { AdminLayout } from '@/components/admin/AdminLayout';
import { AdminProtectedRoute } from '@/components/admin/AdminProtectedRoute';
import { Home } from '@/routes/Home';
import { Login } from '@/routes/Login';
import { Register } from '@/routes/Register';
import { Profile } from '@/routes/Profile';
import { ProfileEdit } from '@/routes/ProfileEdit';
import { PublicProfile } from '@/routes/PublicProfile';
import { Agenda } from '@/routes/Agenda';
import { Matching } from '@/routes/Matching';
import { Conversations } from '@/routes/Conversations';
import { ConversationDetailRoute } from '@/routes/ConversationDetail';
import { GroupConversationDetailRoute } from '@/routes/GroupConversationDetail';
import { Lounge } from '@/routes/Lounge';
import { Proposals } from '@/routes/Proposals';
import { ProposalDetailRoute } from '@/routes/ProposalDetail';
import { Quotes } from '@/routes/Quotes';
import { CompanyBrochureStudio } from '@/routes/CompanyBrochureStudio';
import { BrochurePublicViewer } from '@/routes/BrochurePublicViewer';
import { BrochuresDirectory } from '@/routes/BrochuresDirectory';
import { OrganizerRegister } from '@/routes/organizer/OrganizerRegister';
import { OrganizerDashboard } from '@/routes/organizer/OrganizerDashboard';
import { OrganizerProfilePage } from '@/routes/organizer/OrganizerProfile';
import { OrganizerConferences } from '@/routes/organizer/OrganizerConferences';
import { ConferenceEditor } from '@/routes/organizer/ConferenceEditor';
import { ConferenceDetail } from '@/routes/organizer/ConferenceDetail';
import { AdminLogin } from '@/routes/admin/AdminLogin';
import { AdminDashboard } from '@/routes/admin/AdminDashboard';
import { AdminUsers } from '@/routes/admin/AdminUsers';
import { AdminUserDetail } from '@/routes/admin/AdminUserDetail';
import { AdminOrganizers } from '@/routes/admin/AdminOrganizers';
import { AdminConferencesQueue } from '@/routes/admin/AdminConferencesQueue';
import { AdminConferenceReviewDetail } from '@/routes/admin/AdminConferenceReviewDetail';
import { AdminProposalsQueue } from '@/routes/admin/AdminProposalsQueue';
import { AdminQuotesQueue } from '@/routes/admin/AdminQuotesQueue';
import { AdminBrochureAds } from '@/routes/admin/AdminBrochureAds';
import { NotFound } from '@/routes/NotFound';

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <RealtimeSyncProvider>
        <AuthProvider>
          <AdminAuthProvider>
            <BrowserRouter
              basename="/converge"
              future={{
                v7_startTransition: true,
                v7_relativeSplatPath: true,
              }}
            >
              <RealtimeToastContainer />
              <Routes>
              {/* Dedicated Administrative Control Portal (Phase 2) */}
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route
                path="/admin"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminDashboard />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/users"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminUsers />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/users/:userId"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminUserDetail />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/organizers"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminOrganizers />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/conferences"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminConferencesQueue />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/conferences/:id"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminConferenceReviewDetail />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/proposals"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminProposalsQueue />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/quotes"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminQuotesQueue />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/brochures/ads"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminBrochureAds />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />
              <Route
                path="/admin/brochures"
                element={
                  <AdminProtectedRoute>
                    <AdminLayout>
                      <AdminBrochureAds />
                    </AdminLayout>
                  </AdminProtectedRoute>
                }
              />

              {/* Regular Attendee Application Layout */}
              <Route element={<AppLayout />}>
                <Route path="/" element={<Home />} />
                <Route path="/agenda" element={<Agenda />} />
                <Route
                  path="/matching"
                  element={
                    <ProtectedRoute>
                      <Matching />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/conversations"
                  element={
                    <ProtectedRoute>
                      <Conversations />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/conversations/:conversationId"
                  element={
                    <ProtectedRoute>
                      <ConversationDetailRoute />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/conversations/circles/:circleId"
                  element={
                    <ProtectedRoute>
                      <GroupConversationDetailRoute />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/lounge"
                  element={
                    <ProtectedRoute>
                      <Lounge />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/proposals"
                  element={
                    <ProtectedRoute>
                      <Proposals />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/proposals/:proposalId"
                  element={
                    <ProtectedRoute>
                      <ProposalDetailRoute />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/quotes"
                  element={
                    <ProtectedRoute>
                      <Quotes />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/company/brochure"
                  element={
                    <ProtectedRoute>
                      <CompanyBrochureStudio />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/brochure"
                  element={<Navigate to="/company/brochure" replace />}
                />
                <Route path="/brochures" element={<BrochuresDirectory />} />
                <Route path="/brochures/:slug" element={<BrochurePublicViewer />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/organizer/register" element={<OrganizerRegister />} />
                <Route path="/organizer/login" element={<Navigate to="/login?role=organizer" replace />} />
                <Route
                  path="/organizer"
                  element={
                    <OrganizerProtectedRoute>
                      <OrganizerDashboard />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/organizer/profile"
                  element={
                    <OrganizerProtectedRoute>
                      <OrganizerProfilePage />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/organizer/conferences"
                  element={
                    <OrganizerProtectedRoute>
                      <OrganizerConferences />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/organizer/conferences/new"
                  element={
                    <OrganizerProtectedRoute>
                      <ConferenceEditor />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/organizer/conferences/:id/edit"
                  element={
                    <OrganizerProtectedRoute>
                      <ConferenceEditor />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/organizer/conferences/:id"
                  element={
                    <OrganizerProtectedRoute>
                      <ConferenceDetail />
                    </OrganizerProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile/edit"
                  element={
                    <ProtectedRoute>
                      <ProfileEdit />
                    </ProtectedRoute>
                  }
                />
                <Route path="/profile/:id" element={<PublicProfile />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AdminAuthProvider>
      </AuthProvider>
    </RealtimeSyncProvider>
  </QueryClientProvider>
  );
};

export default App;
