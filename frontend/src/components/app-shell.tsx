"use client";

import { useState } from "react";
import { AuthGate } from "@/components/auth-gate";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { DemoBanner } from "@/components/demo-banner";
import { useAuth } from "@/components/auth-provider";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();

  return (
    <AuthGate>
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:border focus:border-signal focus:bg-ink focus:px-4 focus:py-2 focus:text-[13px] focus:text-mist"
      >
        Skip to content
      </a>
      <div className="min-h-screen">
        <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
        <div className="lg:ml-[248px]">
          <Topbar onMenu={() => setMobileOpen(true)} />
          {user?.is_demo && <DemoBanner />}
          <main
            id="main-content"
            className="mx-auto w-full max-w-[1520px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9"
          >
            {children}
          </main>
          <footer className="mx-auto flex w-full max-w-[1520px] flex-col justify-between gap-1.5 border-t border-line px-4 py-5 text-[11.5px] text-dim sm:px-6 lg:flex-row lg:px-8">
            <p>POLIS 0.1.0 / Experimental research platform / Not a medical device</p>
            <p>No diagnosis. No prescribing. Evidence and uncertainty made visible.</p>
          </footer>
        </div>
      </div>
    </AuthGate>
  );
}
