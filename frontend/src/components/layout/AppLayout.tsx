import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Header } from './Header';
import { Footer } from './Footer';

export const AppLayout: React.FC = () => {
  const location = useLocation();
  const isConversationDetail =
    location.pathname.startsWith('/conversations/') && location.pathname !== '/conversations';
  const isBrochureViewer = location.pathname.startsWith('/brochures/');

  if (isConversationDetail) {
    return (
      <div className="h-screen flex flex-col bg-canvas-base text-ink-primary font-sans antialiased overflow-hidden selection:bg-brass-light selection:text-brass">
        {/* Accessible skip link */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-3.5 focus:py-1.5 focus:bg-brass focus:text-white focus:rounded-md focus:shadow-md focus:outline-none focus:ring-2 focus:ring-brass-hover text-xs font-semibold"
        >
          Skip to main content
        </a>

        <Header />

        <main
          id="main-content"
          className="flex-1 w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-2 sm:px-4 lg:px-6 py-2 min-h-0 flex flex-col overflow-hidden"
          role="main"
        >
          <Outlet />
        </main>
      </div>
    );
  }

  if (isBrochureViewer) {
    return (
      <div className="min-h-screen flex flex-col bg-stone-900 text-stone-100 font-sans antialiased selection:bg-amber-500 selection:text-black">
        {/* Accessible skip link */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-3.5 focus:py-1.5 focus:bg-amber-600 focus:text-white focus:rounded-md focus:shadow-md focus:outline-none text-xs font-semibold print:hidden"
        >
          Skip to main content
        </a>

        <Header />

        <main
          id="main-content"
          className="flex-1 w-full flex flex-col min-h-0 print:p-0 print:m-0"
          role="main"
        >
          <Outlet />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-canvas-base text-ink-primary font-sans antialiased selection:bg-brass-light selection:text-brass print:bg-white print:p-0">
      {/* Accessible skip link */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-50 focus:px-3.5 focus:py-1.5 focus:bg-brass focus:text-white focus:rounded-md focus:shadow-md focus:outline-none focus:ring-2 focus:ring-brass-hover text-xs font-semibold print:hidden"
      >
        Skip to main content
      </a>

      <Header />

      <main
        id="main-content"
        className="flex-1 w-full max-w-[1600px] 2xl:max-w-[1720px] mx-auto px-4 sm:px-6 md:px-8 lg:px-12 py-6 sm:py-8 lg:py-10 print:max-w-none print:p-0 print:m-0"
        role="main"
      >
        <Outlet />
      </main>

      <Footer />
    </div>
  );
};

