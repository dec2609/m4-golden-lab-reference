import { useState, useRef, useEffect } from "react";
import { ChevronDown, Filter } from "lucide-react";

export interface OrderFiltersProps {
  status: "all" | "pending";
  onStatusChange: (status: "all" | "pending") => void;
  pendingCount?: number;
}

export default function OrderFilters({
  status,
  onStatusChange,
  pendingCount,
}: OrderFiltersProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="inline-flex h-9 items-center gap-2 rounded-[var(--radius-button)] border border-[var(--border)] bg-[var(--surface)] px-3 text-xs font-medium text-[var(--text-secondary)] shadow-xs hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)] hover:border-[var(--border-strong)] cursor-pointer transition-all"
        aria-haspopup="true"
        aria-expanded={open}
      >
        <Filter size={13} className="text-[var(--text-muted)]" />
        <span>Status: <strong className="font-semibold text-[var(--text-primary)]">{status === "all" ? "All Statuses" : "Pending"}</strong></span>
        <ChevronDown size={13} className="text-[var(--text-muted)] ml-0.5" />
      </button>

      {open && (
        <div className="absolute right-0 top-10.5 z-20 w-44 rounded-[var(--radius-card)] border border-[var(--border)] bg-[var(--surface)] p-1 shadow-md">
          <button
            type="button"
            onClick={() => {
              onStatusChange("all");
              setOpen(false);
            }}
            className={`flex items-center justify-between w-full rounded px-2.5 py-1.5 text-xs transition-colors cursor-pointer ${
              status === "all"
                ? "bg-[var(--primary-soft)] text-[var(--primary)] font-semibold"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]"
            }`}
          >
            <span>All Statuses</span>
          </button>

          <button
            type="button"
            onClick={() => {
              onStatusChange("pending");
              setOpen(false);
            }}
            className={`flex items-center justify-between w-full rounded px-2.5 py-1.5 text-xs transition-colors cursor-pointer ${
              status === "pending"
                ? "bg-[var(--primary-soft)] text-[var(--primary)] font-semibold"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-subtle)] hover:text-[var(--text-primary)]"
            }`}
          >
            <span>Pending</span>
            {pendingCount !== undefined && (
              <span className="font-mono text-[10px] text-[var(--text-muted)]">({pendingCount})</span>
            )}
          </button>
        </div>
      )}
    </div>
  );
}
