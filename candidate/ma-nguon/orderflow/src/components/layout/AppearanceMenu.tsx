import { useEffect, useRef, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { cn } from "../../lib/utils";
import { useAppearance, type Theme } from "../../lib/appearance";

interface AppearanceMenuProps {
  compact?: boolean;
  className?: string;
}

export default function AppearanceMenu({
  compact = false,
  className,
}: AppearanceMenuProps) {
  const { theme, resolvedTheme, setTheme } = useAppearance();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click and Escape key
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen]);

  const currentThemeIcon =
    theme === "system" ? (
      <Monitor size={compact ? 17 : 15} />
    ) : resolvedTheme === "dark" ? (
      <Moon size={compact ? 17 : 15} />
    ) : (
      <Sun size={compact ? 17 : 15} />
    );

  const themeOptions: { value: Theme; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ];

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        aria-label="Appearance"
        title="Appearance"
        className={cn(
          "flex items-center rounded-[var(--radius-control)] border border-[var(--border)]",
          "bg-[var(--surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]",
          "hover:bg-[var(--surface-hover)] focus-visible:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1 transition-colors cursor-pointer",
          compact
            ? "h-10 w-10 justify-center mx-auto"
            : "w-full justify-between gap-2 px-2.5 py-1.5 text-xs font-medium",
        )}
      >
        <span className="flex items-center gap-2">
          <span
            key={`${resolvedTheme}-${theme}`}
            className="theme-icon-animate inline-flex items-center justify-center"
          >
            {currentThemeIcon}
          </span>
          {!compact && <span>Appearance</span>}
        </span>
        {!compact && (
          <span className="text-[10px] font-mono text-[var(--text-muted)] uppercase tracking-wide">
            {theme}
          </span>
        )}
      </button>

      {/* Floating Popover Dropdown (Theme only) */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Appearance options"
          className={cn(
            "absolute z-50 rounded-[var(--radius-card)] border border-[var(--border-strong)]",
            "bg-[var(--surface-elevated)] p-2.5 shadow-md w-48 text-xs text-[var(--text-primary)]",
            "space-y-2.5 focus:outline-none select-none",
            compact ? "left-14 -bottom-1" : "bottom-full left-0 mb-2",
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
              Appearance
            </span>
            <span className="text-[10px] font-mono text-[var(--text-muted)]">
              {resolvedTheme.toUpperCase()}
            </span>
          </div>

          {/* Theme Section */}
          <div className="space-y-1">
            <span className="text-[10.5px] font-medium text-[var(--text-secondary)] block">
              Theme
            </span>
            <div
              role="radiogroup"
              aria-label="Color theme"
              className="grid grid-cols-3 gap-1 rounded-[var(--radius-control)] bg-[var(--surface-subtle)] p-1 border border-[var(--border)]"
            >
              {themeOptions.map((opt) => {
                const Icon = opt.icon;
                const isSelected = theme === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    onClick={(e) => {
                      setTheme(opt.value, {
                        clientX: e.clientX,
                        clientY: e.clientY,
                      });
                    }}
                    className={cn(
                      "flex flex-col items-center justify-center gap-1 rounded-[var(--radius-control)] py-1.5 text-[11px] font-medium transition-colors cursor-pointer",
                      isSelected
                        ? "bg-[var(--surface)] text-[var(--primary)] font-semibold shadow-xs border border-[var(--border)]"
                        : "text-[var(--text-muted)] hover:text-[var(--text-primary)]",
                    )}
                  >
                    <Icon size={14} />
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
