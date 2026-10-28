import { NavLink } from "react-router-dom";
import {
  ClipboardList,
  LayoutDashboard,
  ShieldCheck,
  PanelLeftClose,
  X,
} from "lucide-react";
import OrderFlowLogo from "../ui/OrderFlowLogo";
import AppearanceMenu from "./AppearanceMenu";
import { useAppearance } from "../../lib/appearance";
import { cn } from "../../lib/utils";

interface SidebarProps {
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

const navigation = [
  {
    label: "Dashboard",
    to: "/dashboard",
    icon: LayoutDashboard,
    description: "Operational overview",
  },
  {
    label: "Orders",
    to: "/orders",
    icon: ClipboardList,
    description: "Manage & track orders",
  },
  {
    label: "Release Console",
    to: "/release",
    icon: ShieldCheck,
    description: "Pipeline security & trust",
  },
];

export default function Sidebar({
  mobileOpen = false,
  onCloseMobile,
}: SidebarProps) {
  const { sidebarMode, setSidebarMode } = useAppearance();

  const renderSidebarContent = (compact: boolean) => (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-[var(--border)] bg-[var(--surface)] select-none transition-[width] duration-[var(--duration-fast)]",
        compact ? "w-16" : "w-[var(--sidebar-width)]",
      )}
    >
      {/* Brand Header */}
      <div
        className={cn(
          "flex border-b border-[var(--border)] shrink-0",
          compact
            ? "h-[72px] items-center justify-center px-2"
            : "h-[72px] items-center justify-between pl-6 pr-3",
        )}
      >
        {compact ? (
          <button
            type="button"
            onClick={() => setSidebarMode("expanded")}
            aria-label="Expand sidebar"
            title="Expand sidebar"
            className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-control)] hover:bg-[var(--surface-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] transition-colors cursor-pointer"
          >
            <OrderFlowLogo
              context="sidebar-compact"
              className="h-7 w-7"
            />
          </button>
        ) : (
          <>
            <div className="flex items-center">
              <OrderFlowLogo
                context="sidebar-expanded"
                className="h-[36px] w-auto translate-y-[3px]"
              />
            </div>

            <div className="flex items-center gap-1">
              {/* Direct Desktop Collapse Button */}
              <button
                type="button"
                onClick={() => setSidebarMode("compact")}
                title="Collapse sidebar"
                aria-label="Collapse sidebar"
                className="hidden md:flex h-8 w-8 items-center justify-center rounded-[var(--radius-control)] text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)] transition-colors cursor-pointer"
              >
                <PanelLeftClose size={18} />
              </button>

              {/* Mobile drawer close button */}
              {onCloseMobile && (
                <button
                  type="button"
                  onClick={onCloseMobile}
                  className="md:hidden h-8 w-8 flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-hover)] rounded-[var(--radius-control)] cursor-pointer"
                  aria-label="Close menu"
                >
                  <X size={18} />
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {/* Navigation Area (Middle - flex-1) */}
      <nav
        aria-label="Main navigation"
        className={cn(
          "flex-1 min-h-0 py-4 overflow-y-auto",
          compact ? "space-y-2 px-2" : "space-y-6 px-3",
        )}
      >
        {compact ? (
          <div className="space-y-2">
            {navigation.map((item) => {
              const Icon = item.icon;

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onCloseMobile}
                  title={item.label}
                  aria-label={item.label}
                  className={({ isActive }) =>
                    cn(
                      "group flex h-10 w-10 mx-auto items-center justify-center rounded-[var(--radius-control)] transition-all duration-[var(--duration-fast)]",
                      isActive
                        ? "bg-[var(--nav-active-bg)] text-[var(--nav-active-fg)] font-semibold shadow-xs"
                        : "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        size={18}
                        strokeWidth={isActive ? 2.2 : 1.8}
                        className={
                          isActive
                            ? "text-[var(--nav-active-icon)]"
                            : "text-[var(--text-muted)] group-hover:text-[var(--text-primary)]"
                        }
                      />
                      <span className="sr-only">{item.label}</span>
                    </>
                  )}
                </NavLink>
              );
            })}
          </div>
        ) : (
          <div>
            <div className="px-3 mb-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                Core Workspace
              </span>
            </div>
            <div className="space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;

                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={onCloseMobile}
                    title={item.label}
                    aria-label={item.label}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center rounded-[var(--radius-control)] transition-all duration-[var(--duration-fast)] gap-3 px-3 py-2 text-[13px] font-medium",
                        isActive
                          ? "bg-[var(--nav-active-bg)] text-[var(--nav-active-fg)] font-semibold shadow-xs"
                          : "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon
                          size={17}
                          strokeWidth={isActive ? 2.2 : 1.8}
                          className={
                            isActive
                              ? "text-[var(--nav-active-icon)]"
                              : "text-[var(--text-muted)] group-hover:text-[var(--text-primary)]"
                          }
                        />
                        <span className="truncate">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        )}
      </nav>

      {/* Bottom Controls (Footer - Bottom-Pinned via mt-auto) */}
      <div
        className={cn(
          "mt-auto shrink-0 border-t border-[var(--border)]",
          compact
            ? "p-2 flex justify-center"
            : "bg-[var(--surface-subtle)]/50 p-3.5",
        )}
      >
        <AppearanceMenu compact={compact} />
      </div>
    </aside>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden md:block shrink-0 h-screen">
        {renderSidebarContent(sidebarMode === "compact")}
      </div>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/40 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <div className="relative z-10 h-full">
            {renderSidebarContent(false)}
          </div>
        </div>
      )}
    </>
  );
}
