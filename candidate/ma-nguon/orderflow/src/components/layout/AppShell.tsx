import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu } from "lucide-react";
import Sidebar from "./Sidebar";
import OrderFlowLogo from "../ui/OrderFlowLogo";
import AppearanceMenu from "./AppearanceMenu";

export default function AppShell() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-full max-w-full overflow-hidden bg-[var(--background)]">
      <Sidebar
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <div className="min-w-0 flex-1 flex flex-col h-screen overflow-hidden">
        {/* Mobile top bar */}
        <div className="md:hidden flex h-14 w-full items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--surface)] shrink-0">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 -ml-1 text-[var(--text-secondary)] hover:text-[var(--text-primary)] rounded-[var(--radius-control)] cursor-pointer"
              aria-label="Open navigation menu"
            >
              <Menu size={20} />
            </button>
            <OrderFlowLogo context="mobile-header" className="h-6 w-auto" />
          </div>
          <div className="flex items-center gap-2">
            <AppearanceMenu compact={true} />
            <span className="text-[11px] font-mono text-[var(--text-muted)]">
              M3
            </span>
          </div>
        </div>

        {/* Scrollable Main Content Region */}
        <main className="flex-1 w-full min-w-0 overflow-y-auto">
          <div className="mx-auto w-full min-w-0 max-w-[var(--content-max-width)] px-4 sm:px-8 py-6 sm:py-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

